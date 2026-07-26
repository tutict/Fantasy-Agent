import json
from pathlib import Path

from fantasy_agent.comfyui_mcp import ComfyUIMCPBridge, call_comfyui_mcp_tool, tool_descriptors
from fantasy_agent.contracts import (
    ComfyUICapabilityProbeRequest,
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
                "1": {
                    "class_type": "CheckpointLoaderSimple",
                    "inputs": {"ckpt_name": "{{ checkpoint_name }}"},
                },
                "2": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"text": "{{ prompt }}", "clip": ["1", 1]},
                },
                "3": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"text": "{{ negative_prompt }}", "clip": ["1", 1]},
                },
                "4": {
                    "class_type": "EmptyLatentImage",
                    "inputs": {"width": 512, "height": 512, "batch_size": 1},
                },
                "5": {
                    "class_type": "KSampler",
                    "inputs": {
                        "model": ["1", 0],
                        "positive": ["2", 0],
                        "negative": ["3", 0],
                        "latent_image": ["4", 0],
                        "seed": "{{ seed }}",
                        "steps": 4,
                        "cfg": 5,
                        "sampler_name": "euler",
                        "scheduler": "normal",
                        "denoise": 1,
                    },
                },
                "6": {
                    "class_type": "VAEDecode",
                    "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
                },
                "7": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "images": ["6", 0],
                        "filename_prefix": "{{ filename_prefix }}",
                    },
                },
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

    def system_stats(self) -> dict:
        return {
            "system": {
                "comfyui_version": "test",
                "python_version": "test",
                "pytorch_version": "test",
            },
            "devices": [{"name": "cuda:test"}],
        }

    def object_info(self) -> dict:
        return {
            "CheckpointLoaderSimple": {
                "input": {"required": {"ckpt_name": [["fake-model.safetensors"]]}}
            },
            "CLIPTextEncode": {},
            "EmptyLatentImage": {},
            "KSampler": {},
            "VAEDecode": {},
            "SaveImage": {},
        }

    def models(self, folder: str) -> list[str]:
        return ["fake-model.safetensors"] if folder == "checkpoints" else []

    def queue_prompt(self, workflow: dict, client_id: str = "fantasy-agent") -> dict:
        return {"prompt_id": f"prompt-{client_id}", "workflow": workflow}


def test_comfyui_mcp_descriptors_expose_prepare_and_run_tools():
    names = {tool["name"] for tool in tool_descriptors()}

    assert {
        "probe_comfyui_capabilities",
        "prepare_visual_reference_workflows",
        "run_visual_reference_workflow",
    }.issubset(names)


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
    assert workflow["2"]["inputs"]["text"] == "Readable objective and hazard reference."
    assert workflow["1"]["inputs"]["ckpt_name"] == "__FANTASY_AGENT_CHECKPOINT_REQUIRED__"


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
    assert result.manifest.endpoint == "http://127.0.0.1:8188"
    assert result.manifest.jobs[0].workflow["1"]["inputs"]["ckpt_name"] == "fake-model.safetensors"


def test_probe_comfyui_capabilities_reports_checkpoint(tmp_path: Path):
    bridge = ComfyUIMCPBridge(tmp_path, client_factory=FakeComfyUIClient)

    result = bridge.probe_comfyui_capabilities(ComfyUICapabilityProbeRequest())

    assert result.status == "ready"
    assert result.selected_checkpoint == "fake-model.safetensors"


def test_probe_rejects_endpoint_credentials_before_client_creation(tmp_path: Path):
    client_endpoints: list[str] = []

    def recording_client_factory(endpoint: str):
        client_endpoints.append(endpoint)
        raise AssertionError("credential-bearing endpoint reached the client factory")

    secret = "exp007-probe-secret"
    bridge = ComfyUIMCPBridge(tmp_path, client_factory=recording_client_factory)
    result = bridge.probe_comfyui_capabilities(
        ComfyUICapabilityProbeRequest(
            endpoint=f"http://worker:{secret}@localhost:8188",
            auto_discover_endpoint=False,
        )
    )

    diagnostics = " ".join([*result.blockers, *result.warnings])
    assert result.status == "unavailable"
    assert client_endpoints == []
    assert "credentials" in diagnostics
    assert secret not in diagnostics


class NoCheckpointComfyUIClient(FakeComfyUIClient):
    def object_info(self) -> dict:
        info = super().object_info()
        info["CheckpointLoaderSimple"] = {"input": {"required": {"ckpt_name": [[]]}}}
        return info

    def models(self, folder: str) -> list[str]:
        return []


def test_run_visual_reference_workflow_blocks_without_checkpoint(tmp_path: Path):
    _template(tmp_path)
    bridge = ComfyUIMCPBridge(tmp_path, client_factory=NoCheckpointComfyUIClient)

    result = bridge.run_visual_reference_workflow(
        ComfyUIMCPExecuteRequest(plan=_plan(), confirmed_side_effects=True)
    )

    assert result.status == "blocked"
    assert "No local checkpoint models" in result.stderr_tail


def test_comfyui_mcp_rejects_remote_endpoint_by_default(tmp_path: Path):
    _template(tmp_path)
    result = call_comfyui_mcp_tool(
        "prepare_visual_reference_workflows",
        {"plan": _plan(endpoint="https://example.com").model_dump(mode="json")},
        workspace_root=tmp_path,
    )

    assert result["isError"] is True
    assert "endpoint must be local" in result["content"][0]["text"]


def test_comfyui_mcp_rejects_endpoint_credentials_without_echo(tmp_path: Path):
    _template(tmp_path)
    secret = "exp007-secret"
    result = call_comfyui_mcp_tool(
        "prepare_visual_reference_workflows",
        {
            "plan": _plan(
                endpoint=f"http://worker:{secret}@localhost:8188"
            ).model_dump(mode="json"),
            "write_files": True,
        },
        workspace_root=tmp_path,
    )

    message = result["content"][0]["text"]
    assert result["isError"] is True
    assert "credentials" in message
    assert secret not in message
    assert not (tmp_path / "generated").exists()


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
