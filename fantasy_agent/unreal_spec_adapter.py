from __future__ import annotations

import json

from fantasy_agent.contracts import (
    CompiledSpecArtifact,
    ExecutableQAAssertion,
    ExecutableQAReport,
    ExecutableQAResult,
    ProductionSpecBundle,
    SpecCompileResult,
    SpecTraceRecord,
)


def compile_unreal_spec_bundle(bundle: ProductionSpecBundle) -> SpecCompileResult:
    tables = {table.table_id: table for table in bundle.config_tables.tables}
    enemy_path = "Content/FantasyAgent/Data/DT_Enemies.json"
    encounter_path = "Content/FantasyAgent/Data/DT_Encounters.json"
    data_asset_path = "Content/FantasyAgent/Data/DA_ProductionSpec.json"
    artifacts = [
        _json_artifact(enemy_path, _datatable_payload(tables.get("enemies"))),
        _json_artifact(encounter_path, _datatable_payload(tables.get("encounters"))),
        _json_artifact(
            data_asset_path,
            {
                "schema_version": bundle.schema_version,
                "combat": bundle.combat.model_dump(mode="json") if bundle.combat else None,
                "level": bundle.level.model_dump(mode="json"),
                "numeric": bundle.numeric.model_dump(mode="json"),
                "narrative": bundle.narrative.model_dump(mode="json"),
                "resource_pipeline": bundle.resource_pipeline.model_dump(mode="json"),
            },
        ),
    ]
    traces = [
        SpecTraceRecord(
            spec_field="config_tables.tables.enemies",
            artifact_path=enemy_path,
            consumer="unreal-datatable-adapter",
        ),
        SpecTraceRecord(
            spec_field="config_tables.tables.encounters",
            artifact_path=encounter_path,
            consumer="unreal-datatable-adapter",
        ),
        *[
            SpecTraceRecord(
                spec_field=field,
                artifact_path=data_asset_path,
                consumer="unreal-dataasset-adapter",
            )
            for field in ("combat", "level", "numeric", "narrative", "resource_pipeline")
        ],
    ]
    return SpecCompileResult(target="unreal", artifacts=artifacts, traces=traces)


def evaluate_executable_qa(bundle: ProductionSpecBundle) -> ExecutableQAReport:
    assertions = [
        ExecutableQAAssertion(
            assertion_id="session_target_range",
            metric_key="target_session_minutes",
            operator="between",
            expected=[5, 15],
        ),
        ExecutableQAAssertion(
            assertion_id="objective_gate_coverage",
            metric_key="objective_gates",
            operator="non_empty",
        ),
        # Only a failed validation blocks execution (error severity); a
        # warning-status report degrades the QA verdict but keeps the run
        # alive, matching the spec_validation gate and the Godot path.
        ExecutableQAAssertion(
            assertion_id="spec_validation_not_failed",
            metric_key="validation_status",
            operator="neq",
            expected="failed",
        ),
        ExecutableQAAssertion(
            assertion_id="spec_validation_passed",
            metric_key="validation_status",
            operator="eq",
            expected="passed",
            severity="warning",
        ),
        ExecutableQAAssertion(
            assertion_id="approved_assets_only",
            metric_key="resource_approval",
            operator="all_approved",
            severity="warning",
        ),
    ]
    actuals = {
        "target_session_minutes": bundle.numeric.target_session_minutes,
        "objective_gates": bundle.level.objective_gates,
        "validation_status": bundle.validation.status if bundle.validation else "missing",
        "resource_approval": [asset.approval_status for asset in bundle.resource_pipeline.assets],
    }
    results = [_evaluate(assertion, actuals[assertion.metric_key]) for assertion in assertions]
    has_errors = any(not result.passed and result.severity == "error" for result in results)
    has_warnings = any(not result.passed for result in results)
    status = "failed" if has_errors else "warning" if has_warnings else "passed"
    return ExecutableQAReport(status=status, assertions=assertions, results=results)


def _datatable_payload(table) -> dict:
    if table is None:
        return {"RowStruct": "FantasyAgentRow", "Rows": {}}
    return {
        "RowStruct": f"FantasyAgent{table.table_id.title()}Row",
        "PrimaryKey": table.primary_key,
        "Rows": {str(row[table.primary_key]): row for row in table.rows},
    }


def _json_artifact(path: str, payload: dict) -> CompiledSpecArtifact:
    return CompiledSpecArtifact(
        path=path,
        media_type="application/json",
        content=json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )


def _evaluate(assertion: ExecutableQAAssertion, actual) -> ExecutableQAResult:
    expected = assertion.expected
    if assertion.operator == "between":
        lower, upper = expected or [0, 0]
        passed = lower <= actual <= upper
    elif assertion.operator == "non_empty":
        passed = bool(actual)
    elif assertion.operator == "all_approved":
        passed = all(item == "approved" for item in actual)
    elif assertion.operator == "gte":
        passed = actual >= expected
    elif assertion.operator == "lte":
        passed = actual <= expected
    elif assertion.operator == "neq":
        passed = actual != expected
    else:
        passed = actual == expected
    return ExecutableQAResult(
        assertion_id=assertion.assertion_id,
        metric_key=assertion.metric_key,
        passed=passed,
        actual=actual,
        expected=expected,
        severity=assertion.severity,
        message="passed" if passed else f"{assertion.metric_key} did not satisfy {assertion.operator}",
    )