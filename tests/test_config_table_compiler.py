import csv
import io

from fantasy_agent.config_table_compiler import compile_config_tables
from fantasy_agent.contracts import PromptRequest
from fantasy_agent.workflows import run_director_workflow


def _tables():
    plan = run_director_workflow(PromptRequest(prompt="a combat arena with guards and turrets"))
    assert plan.production_spec_bundle is not None
    return plan.production_spec_bundle.config_tables


def test_config_table_compiler_emits_declared_formats_deterministically():
    tables = _tables()
    enemies = next(table for table in tables.tables if table.table_id == "enemies")
    mixed = tables.model_copy(
        update={
            "tables": [
                enemies.model_copy(update={"format": "csv-ready", "export_path": "generated/config/enemies.csv"}),
                *[table for table in tables.tables if table.table_id != "enemies"],
            ]
        }
    )

    first = compile_config_tables(mixed, output_prefix="data/config")
    second = compile_config_tables(mixed, output_prefix="data/config")
    enemy_artifact = next(item for item in first.artifacts if item.path.endswith("enemies.csv"))

    assert first == second
    assert enemy_artifact.media_type == "text/csv"
    rows = list(csv.DictReader(io.StringIO(enemy_artifact.content)))
    assert rows
    assert "enemy_id" in rows[0]
    assert any(trace.spec_field.startswith("config_tables.tables.enemies") for trace in first.traces)

