from fantasy_agent.contracts import PromptRequest
from fantasy_agent.unreal_spec_adapter import compile_unreal_spec_bundle, evaluate_executable_qa
from fantasy_agent.workflows import run_director_workflow


def _bundle():
    plan = run_director_workflow(
        PromptRequest(prompt="a combat arena with guards and ranged turrets", engine_version="UE5")
    )
    assert plan.production_spec_bundle is not None
    return plan.production_spec_bundle


def test_unreal_adapter_emits_datatable_and_dataasset_artifacts():
    result = compile_unreal_spec_bundle(_bundle())
    paths = {artifact.path for artifact in result.artifacts}

    assert "Content/FantasyAgent/Data/DT_Enemies.json" in paths
    assert "Content/FantasyAgent/Data/DT_Encounters.json" in paths
    assert "Content/FantasyAgent/Data/DA_ProductionSpec.json" in paths
    assert any(trace.artifact_path.endswith("DT_Enemies.json") for trace in result.traces)


def test_machine_executable_qa_reports_static_spec_results():
    report = evaluate_executable_qa(_bundle())

    assert report.status in {"passed", "warning"}
    assert report.assertions
    assert all(result.assertion_id for result in report.results)
    assert any(result.metric_key == "target_session_minutes" for result in report.results)


def test_executable_qa_degrades_on_warning_validation_and_fails_on_failed():
    from fantasy_agent.contracts import SpecValidationReport

    bundle = _bundle()
    warned = bundle.model_copy(
        update={"validation": SpecValidationReport(status="warning", issues=[], coverage={})}
    )
    failed = bundle.model_copy(
        update={"validation": SpecValidationReport(status="failed", issues=[], coverage={})}
    )

    warned_report = evaluate_executable_qa(warned)
    failed_report = evaluate_executable_qa(failed)

    # Warning-level validation degrades QA but must not block execution
    # (executor aborts only on QA status "failed").
    assert warned_report.status == "warning"
    assert failed_report.status == "failed"
    not_failed = next(
        result
        for result in warned_report.results
        if result.assertion_id == "spec_validation_not_failed"
    )
    assert not_failed.passed
    assert not_failed.severity == "error"
