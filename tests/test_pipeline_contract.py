"""The production pipeline is the contract the orchestrator will run on.

`docs/superpowers/plans/2026-09-16-internal-pi-task-orchestration.md` adds an
orchestrator that walks `ProductionPipeline.stages` by `order`, refuses to start
a stage whose `depends_on` has not finished, and hands that stage its own
`mcp_tools` through a scoped registry. None of those fields had a reader, and
they did not hold:

- two stages declared no tools at all, for two completely different reasons;
- two Unreal stages listed `DataValidation`, which is the *commandlet* the
  `run_editor_commandlet` tool runs -- a name that reads like a tool and
  resolves to nothing;
- nothing checked that a dependency points backwards rather than forwards.

A table the orchestrator obeys without complaining is a table that has to be
right, so every property it relies on is pinned here.
"""

from __future__ import annotations

from functools import lru_cache
from typing import get_args

from fantasy_agent.contracts import (
    ProductionPipeline,
    ProductionPipelineStage,
    ProductionPipelineStageId,
    PromptRequest,
)
from fantasy_agent.tool_registry import combined_registry
from fantasy_agent.workflows import run_director_workflow

#: Both routes are built by the same function and ship a different stage list:
#: the Unreal route swaps `unreal_production` for `godot_quick_play`. Reading the
#: table off one route is how a dangling tool name survived -- it only ever
#: appeared on the other one.
ROUTES: tuple[str, ...] = ("Godot 4", "Unreal Engine 5")

PROMPT = "a stealth courier escapes a haunted train station in ten minutes"


@lru_cache(maxsize=1)
def _pipelines() -> dict[str, ProductionPipeline]:
    """What each engine route produces, built once for the whole module."""

    return {
        route: run_director_workflow(PromptRequest(prompt=PROMPT, engine_version=route)).production_pipeline
        for route in ROUTES
    }


def _stage(pipeline: ProductionPipeline, stage_id: str) -> ProductionPipelineStage:
    return next(stage for stage in pipeline.stages if stage.id == stage_id)


def test_every_stage_an_agent_drives_names_the_tools_it_uses():
    """An agent stage with no tools is a stage the orchestrator can only idle on."""

    for route, pipeline in _pipelines().items():
        for stage in pipeline.stages:
            if stage.kind != "agent":
                continue
            assert stage.mcp_tools, f"{route}: {stage.id} is driven by an agent but names no tool"


def test_a_human_stage_names_no_tools():
    """`kind="human"` means only the user can move the stage.

    Both directions are asserted: a human stage carrying tools is one the
    orchestrator could run without the decision, and a pipeline with no human
    stage at all would leave the field untested.
    """

    for route, pipeline in _pipelines().items():
        human = [stage for stage in pipeline.stages if stage.kind == "human"]
        assert human, f"{route}: nothing in this pipeline waits on a user decision"
        for stage in human:
            assert not stage.mcp_tools, f"{route}: {stage.id} is a human stage that names tools"


def test_the_creative_review_is_the_pipelines_human_gate():
    """Pinned by id: `kind` here is a reading of the table, not a new claim.

    The stage's own side effect says it asks the user for asset approval
    decisions, which is why it is the one stage an agent cannot drive.
    """

    for route, pipeline in _pipelines().items():
        review = _stage(pipeline, "creative_review")
        assert review.kind == "human", f"{route}: creative_review is not a human gate"
        assert not review.mcp_tools, route
        assert any("user" in effect for effect in review.side_effects), (
            f"{route}: creative_review is called a human gate but its side effects "
            f"never mention the user: {review.side_effects}"
        )


def test_every_declared_tool_is_one_the_registry_can_resolve():
    """A tool name the registry does not have is a stage that cannot start."""

    registered = set(combined_registry().names())
    for route, pipeline in _pipelines().items():
        for stage in pipeline.stages:
            unknown = sorted(set(stage.mcp_tools) - registered)
            assert not unknown, f"{route}: {stage.id} names tools that do not exist: {unknown}"


def test_a_stage_only_depends_on_stages_that_come_before_it():
    """Backwards-only edges are what let the orchestrator walk the list once."""

    for route, pipeline in _pipelines().items():
        by_id = {stage.id: stage for stage in pipeline.stages}
        for stage in pipeline.stages:
            for dependency in stage.depends_on:
                assert dependency in by_id, f"{route}: {stage.id} depends on unknown {dependency}"
                assert by_id[dependency].order < stage.order, (
                    f"{route}: {stage.id} (order {stage.order}) waits for {dependency} "
                    f"(order {by_id[dependency].order})"
                )


def test_the_order_is_a_dense_sequence_covering_every_stage_once():
    """`order` is reassigned at the end of the builder; this pins that result."""

    for route, pipeline in _pipelines().items():
        orders = [stage.order for stage in pipeline.stages]
        assert orders == list(range(1, len(orders) + 1)), f"{route}: {orders}"
        ids = [stage.id for stage in pipeline.stages]
        assert len(set(ids)) == len(ids), f"{route}: duplicate stage ids in {ids}"


def test_the_pipeline_references_only_stages_a_route_actually_builds():
    """Covers the current/next pointers and the stage-id literal in one pass."""

    built = {stage.id for pipeline in _pipelines().values() for stage in pipeline.stages}
    for route, pipeline in _pipelines().items():
        ids = {stage.id for stage in pipeline.stages}
        assert pipeline.current_stage in ids, f"{route}: current_stage is not a stage here"
        assert pipeline.next_stage in ids, f"{route}: next_stage is not a stage here"
    never_built = sorted(set(get_args(ProductionPipelineStageId)) - built)
    assert not never_built, f"the contract declares stage ids no route builds: {never_built}"


def test_a_stage_written_before_the_kind_field_still_loads_as_an_agent_stage():
    """The field is an addition: plans serialised before it must keep loading."""

    payload = _stage(_pipelines()["Godot 4"], "blender_modeling").model_dump(mode="json")
    assert payload["kind"] == "agent", "the field must reach the frontend"
    payload.pop("kind")
    assert ProductionPipelineStage.model_validate(payload).kind == "agent"
