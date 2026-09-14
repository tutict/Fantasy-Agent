#!/usr/bin/env python
"""Probe the engine links on this machine and print what they actually did.

The test suite pins the *code paths*; it cannot tell you whether Godot, Blender,
Unreal or ComfyUI actually answer on the machine in front of you. This can. Every
call goes through ``combined_registry`` -- the same registry, permission gate and
executable probe a model tool call goes through -- and each step prints the
engine's own status, command line and output, so "the link works" is something
you can read instead of something you have to believe.

    python scripts/verify_engine_links.py
    python scripts/verify_engine_links.py --workspace generated/my-probe

The engines are launched for real, so this is a manual probe, not a test: it
writes under ``generated/`` and takes as long as the engines take. On a machine
without an engine the step still reports, as *degraded* rather than broken --
the plan and the generated files are produced either way, and only the launch
half is missing. That distinction is the reason to run it: "Unreal is not
installed" and "the Unreal link is broken" look identical from the outside.

Exit code is 0 as long as every step produced a result. A non-zero exit means
the probe itself failed, not that an engine is missing.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from fantasy_agent import local_tools
from fantasy_agent.tool_registry import ToolOutcome, combined_registry

#: Tool names this probe addresses. Declared so a rename in a bridge shows up
#: here rather than as a probe that quietly stops covering a link; the test
#: suite asserts every one of them is still registered.
TOOLS = (
    "generate_game_production_plan",
    "create_godot_project_structure",
    "validate_godot_project",
    "run_godot_import",
    "generate_blender_script",
    "generate_asset_batch",
    "probe_comfyui_capabilities",
    "prepare_visual_reference_workflows",
    "run_visual_reference_workflow",
    "create_project_structure",
)

PROMPT = "rooftop parkour chase across neon towers"


@dataclass
class Step:
    """One tool call the probe made, kept for the summary."""

    label: str
    outcome: ToolOutcome

    @property
    def status(self) -> str:
        return self.outcome.status


def _structured(outcome: ToolOutcome) -> dict[str, Any]:
    """The bridge's own result object, whichever envelope it arrived in."""

    data = outcome.data
    nested = data.get("structuredContent")
    return nested if isinstance(nested, dict) else data


def _show(step: Step) -> None:
    print(f"\n=== {step.label} ===")
    print("status :", step.status)
    print("content:", step.outcome.content)
    body = json.dumps(step.outcome.data, ensure_ascii=False)
    print("data   :", body[:1200] + ("..." if len(body) > 1200 else ""))


def _pick(outcome: ToolOutcome, *names: str) -> dict[str, Any]:
    structured = _structured(outcome)
    return {name: structured.get(name) for name in names}


def _seed_templates(workspace: Path) -> None:
    """Copy the shipped ComfyUI templates into the workspace.

    The bridge resolves ``templates/comfyui/*.json`` against the *workspace*,
    not the repo, so a probe run in a throwaway directory would otherwise fail
    on a missing template -- an artefact of where the probe writes, not
    anything about the ComfyUI link.
    """

    source = REPO_ROOT / "templates" / "comfyui"
    target = workspace / "templates" / "comfyui"
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.glob("*.json")):
        (target / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def _resolve(workspace: Path, path: str) -> Path:
    """Bridges report workspace-relative paths; resolve them against the workspace.

    Checking them against the current directory instead judges *this* run by
    whatever an older run left in the repo: the Blender step once reported
    ``exists=True`` for .fbx files four months old, while the run's own output
    sat untouched under the workspace. A false green is the worst thing a probe
    can print.
    """

    candidate = Path(path)
    return candidate if candidate.is_absolute() else workspace / candidate


def _engine_paths() -> dict[str, str | None]:
    return {
        "godot": local_tools._find_godot(),
        "blender": local_tools._find_blender(),
        "unreal": local_tools._find_unreal(),
    }


def probe(workspace: Path) -> list[Step]:
    """Exercise every link, in the order a real run would."""

    steps: list[Step] = []
    combined = combined_registry(workspace)

    def call(label: str, name: str, arguments: dict[str, Any], **grants: bool) -> Step:
        step = Step(label, combined.call(name, arguments, **grants))
        _show(step)
        steps.append(step)
        return step

    print("engine binaries:")
    for engine, found in _engine_paths().items():
        print(f"  {engine:8}-> {found or '(not installed)'}")

    planned = call(
        "generate_game_production_plan",
        "generate_game_production_plan",
        {"prompt": PROMPT, "target_minutes": 10},
    )
    # Engine tools read the plan from the registry's store, exactly as the loop
    # arranges it -- the model never constructs one.
    combined.remember_plan(planned.outcome.data)
    print("plans harvested:", sorted(combined.artifacts))

    # ── Godot ────────────────────────────────────────────────────────────────
    created = call(
        "create_godot_project_structure",
        "create_godot_project_structure",
        {"write_files": True},
        allow_write=True,
    )
    project_file = _structured(created.outcome)["artifact"]["project_file"]
    call("validate_godot_project", "validate_godot_project", {"project_file": project_file})
    imported = call(
        "run_godot_import",
        "run_godot_import",
        {"project_file": project_file, "confirmed_side_effects": True, "timeout_seconds": 300},
        allow_execute=True,
    )
    godot = _pick(imported.outcome, "command", "return_code", "stdout_tail", "stderr_tail")
    print("godot command    :", godot["command"])
    print("godot return_code:", godot["return_code"])
    print("godot stderr     :", repr((godot["stderr_tail"] or "")[-600:]))

    # ── Blender ──────────────────────────────────────────────────────────────
    call(
        "generate_blender_script",
        "generate_blender_script",
        {"write_files": True},
        allow_write=True,
    )
    batch = call(
        "generate_asset_batch",
        "generate_asset_batch",
        {"confirmed_side_effects": True, "timeout_seconds": 600},
        allow_execute=True,
    )
    blender = _pick(batch.outcome, "command", "return_code", "exported_assets", "stderr_tail")
    print("blender command    :", blender["command"])
    print("blender return_code:", blender["return_code"])
    print("blender stderr     :", repr((blender["stderr_tail"] or "")[-600:]))
    exported = blender["exported_assets"] or []
    print(f"blender exported   : {len(exported)} asset(s)")
    for asset in exported:
        print(f"  {asset}  exists={_resolve(workspace, asset).exists()}")

    # ── ComfyUI ──────────────────────────────────────────────────────────────
    # Unlike the engines above, ComfyUI is a long-running local service rather
    # than a binary to launch. There is nothing to auto-start: if it is not
    # already listening, the probe reports it as unavailable and every step
    # below degrades on its own.
    _seed_templates(workspace)
    probe = call("probe_comfyui_capabilities", "probe_comfyui_capabilities", {})
    comfy = _structured(probe.outcome)
    print("comfyui status    :", comfy.get("status"))
    print("comfyui endpoint  :", comfy.get("endpoint"))
    print("comfyui checkpoint:", comfy.get("selected_checkpoint"))
    print("comfyui blockers  :", comfy.get("blockers"))

    call(
        "prepare_visual_reference_workflows",
        "prepare_visual_reference_workflows",
        {"write_files": True},
        allow_write=True,
    )
    run = call(
        "run_visual_reference_workflow",
        "run_visual_reference_workflow",
        {
            "confirmed_side_effects": True,
            "wait_for_completion": True,
            "timeout_seconds": 300,
        },
        allow_execute=True,
    )
    images = _pick(run.outcome, "prompt_ids", "generated_images", "stderr_tail")
    print("comfyui prompt_ids:", images["prompt_ids"])
    print("comfyui stderr    :", repr((images["stderr_tail"] or "")[-600:]))
    for path in images["generated_images"] or []:
        print(f"  {path}  exists={_resolve(workspace, path).exists()}")

    # ── Unreal: expected degraded, reported either way ───────────────────────
    call(
        "create_project_structure",
        "create_project_structure",
        {"write_files": True},
        allow_write=True,
    )
    return steps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--workspace",
        default="generated/engine-link-check",
        help="Where the probe writes (default generated/engine-link-check).",
    )
    args = parser.parse_args(argv)

    workspace = (REPO_ROOT / args.workspace).resolve()
    steps = probe(workspace)

    print("\n=== summary ===")
    for step in steps:
        print(f"  {step.status:8} {step.label}")
    print(f"\nprobe wrote under {workspace}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
