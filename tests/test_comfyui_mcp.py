import json
from pathlib import Path

from fantasy_agent.comfyui_mcp import ComfyUIMCPBridge, call_comfyui_mcp_tool, tool_descriptors
from fantasy_agent.contracts import (
    ComfyUIMCPExecuteRequest,
    ComfyUIMCPGenerateRequest,
    ComfyUIPromptJob,
    ComfyUIVisualPlan,
)


def _template(root: Path) -> None:
    template_dir = root / "templates" / "comfyui"
    template_dir.mkdir(parents=True)
    (template_dir / "readability-reference.json").write_text(
        json.dumps(
            {
                "inputs": {
                    "positive_prompt": "{{ prompt }}",
                    "negative_prompt": "{{ negative_prompt }}",
                    "seed": "{{ seed }}",
                    "output_path": "{{ output_path }}",
                }
            }
        ),
        encoding="utf-8",
    )


def _plan(endpoint: str = "http://127.0.0.1:8188") -> ComfyUIVisualPlan:
    return ComfyUIVisualPlan(
        plan_name="Comfy MCP Smoke",
        endpoint=endpoint,
        workflow_templates=["templates/comfyui/readability-reference.json"],
        handoff_artifacts=[],
        usage_rules=["Generated images require review."],
        jobs=[
            ComfyUIPromptJob(
                job_id="concept_readability_reference",
                purpose="concept_reference",
                prompt="Readable objective and hazard reference.",
                negative_prompt="decorative-only composition",
                workflow_template="templates/comfyui/readability-reference.json",
                output_path="generated/comfyui/smoke/concept.png",
                gameplay_constraint="Must clarify objective, hazard, route, or feedback.",
            )
        ],
    )


class FakeComfyUIClient:
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint

    def queue_prompt(self, workflow: dict, client_id: str = "fantasy-agent") -> dict:
        return {"prompt_id": f"prompt-{client_id}", "workflow": workflow}


def test_comfyui_mcp_descriptors_expose_prepare_and_run_tools():
    names = {tool["name"] for tool in tool_descriptors()}

    assert {"prepare_visual_reference_workflows", "run_visual_reference_workflow"}.issubset(names)


def test_prepare_visual_reference_workflows_can_write_files(tmp_path: Path):
    _template(tmp_path)
    bridge = ComfyUIMCPBridge(tmp_path)

    result = bridge.prepare_visual_reference_workflows(
        ComfyUIMCPGenerateRequest(plan=_plan(), write_files=True)
    )

    assert result.status == "written"
    assert "generated/comfyui/workflows/comfy_mcp_smoke/concept_readability_reference.json" in (
        result.workflow_files
    )
    assert (tmp_path / "generated/comfyui/run-manifest.json").exists()
    workflow = json.loads(
        (tmp_path / "generated/comfyui/workflows/comfy_mcp_smoke/concept_readability_reference.json")
        .read_text(encoding="utf-8")
    )
    assert workflow["inputs"]["positive_prompt"] == "Readable objective and hazard reference."


def test_run_visual_reference_workflow_blocks_without_confirmation(tmp_path: Path):
    _template(tmp_path)
    bridge = ComfyUIMCPBridge(tmp_path)

    result = bridge.run_visual_reference_workflow(
        ComfyUIMCPExecuteRequest(plan=_plan(), confirmed_side_effects=False)
    )

    assert result.status == "blocked"
    assert "confirmed_side_effects=true" in result.risks[-1]


def test_run_visual_reference_workflow_queues_with_fake_client(tmp_path: Path):
    _template(tmp_path)
    bridge = ComfyUIMCPBridge(tmp_path, client_factory=FakeComfyUIClient)

    result = bridge.run_visual_reference_workflow(
        ComfyUIMCPExecuteRequest(plan=_plan(), confirmed_side_effects=True)
    )

    assert result.status == "queued"
    assert result.prompt_ids == ["prompt-fantasy-agent-concept_readability_reference"]
    assert (tmp_path / "generated/logs/comfyui/comfy_mcp_smoke.stdout.log").exists()


def test_comfyui_mcp_rejects_remote_endpoint_by_default(tmp_path: Path):
    _template(tmp_path)
    result = call_comfyui_mcp_tool(
        "prepare_visual_reference_workflows",
        {"plan": _plan(endpoint="https://example.com").model_dump(mode="json")},
        workspace_root=tmp_path,
    )

    assert result["isError"] is True
    assert "endpoint must be local" in result["content"][0]["text"]


def test_comfyui_mcp_rejects_templates_outside_allowlist(tmp_path: Path):
    plan = _plan().model_copy(
        update={
            "jobs": [
                _plan().jobs[0].model_copy(update={"workflow_template": "templates/other.json"})
            ]
        }
    )

    result = call_comfyui_mcp_tool(
        "prepare_visual_reference_workflows",
        {"plan": plan.model_dump(mode="json")},
        workspace_root=tmp_path,
    )

    assert result["isError"] is True
    assert "templates/comfyui" in result["content"][0]["text"]

