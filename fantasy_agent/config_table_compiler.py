from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import yaml

from fantasy_agent.contracts import (
    CompiledSpecArtifact,
    ConfigTable,
    ConfigTableSpec,
    SpecCompileResult,
    SpecTraceRecord,
)


def compile_config_tables(
    spec: ConfigTableSpec,
    *,
    output_prefix: str = "generated/config",
) -> SpecCompileResult:
    """Compile config tables deterministically without writing files."""

    artifacts: list[CompiledSpecArtifact] = []
    traces: list[SpecTraceRecord] = []
    for table in sorted(spec.tables, key=lambda item: item.table_id):
        _validate_table(table)
        rows = sorted(table.rows, key=lambda row: str(row.get(table.primary_key, "")))
        suffix = {"yaml": ".yaml", "json": ".json", "csv-ready": ".csv"}[table.format]
        declared_name = Path(table.export_path.replace("\\", "/")).name
        filename = f"{Path(declared_name).stem}{suffix}"
        path = (Path(output_prefix) / filename).as_posix()
        content, media_type = _render_table(table, rows)
        artifacts.append(CompiledSpecArtifact(path=path, media_type=media_type, content=content))
        traces.append(
            SpecTraceRecord(
                spec_field=f"config_tables.tables.{table.table_id}",
                artifact_path=path,
                consumer="config-table-compiler",
            )
        )
    return SpecCompileResult(target="config", artifacts=artifacts, traces=traces)


def _validate_table(table: ConfigTable) -> None:
    path = Path(table.export_path.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe config export path: {table.export_path}")
    seen: set[str] = set()
    for row in table.rows:
        value = str(row.get(table.primary_key, ""))
        if not value:
            raise ValueError(f"Table {table.table_id} row is missing {table.primary_key}")
        if value in seen:
            raise ValueError(f"Table {table.table_id} has duplicate {table.primary_key}: {value}")
        seen.add(value)


def _render_table(
    table: ConfigTable,
    rows: list[dict[str, str | int | float | bool]],
) -> tuple[str, str]:
    payload = {"table_id": table.table_id, "primary_key": table.primary_key, "rows": rows}
    if table.format == "json":
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "application/json"
    if table.format == "csv-ready":
        fields = {key for row in rows for key in row}
        fieldnames = [table.primary_key, *sorted(fields - {table.primary_key})]
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue(), "text/csv"
    return (
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        "application/yaml",
    )