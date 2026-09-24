"""Command-line entry point for Fantasy Agent.

Run the full director workflow from a prompt and print the resulting build plan.

Examples:
    python -m fantasy_agent --prompt "a 2D platformer where a cat collects fish"
    python -m fantasy_agent --prompt "..." --llm --minutes 8 --engine "Godot 4"

The --llm flag opts into the LLM backend for gameplay design; without it (the
default) the deterministic generator is used. When --llm is set but the backend
is unavailable, generation falls back to deterministic output automatically.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from fantasy_agent.contracts import PromptRequest
from fantasy_agent.gdd import render_gdd
from fantasy_agent.generation import design_from_prompt
from fantasy_agent.pipeline_state import (
    GODOT_STAGE_ORDER,
    REWORK_TARGET_STAGES,
)
from fantasy_agent.workflows import run_director_workflow


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fantasy-agent",
        description="Generate a gameplay-first build plan from a game idea.",
    )
    parser.add_argument("--prompt", help="Raw game idea (min 8 chars).")
    parser.add_argument(
        "--spec-file",
        default=None,
        help="Load an existing ProductionSpecBundle YAML/JSON as the execution authority.",
    )
    parser.add_argument(
        "--minutes", type=int, default=10, help="Target session length, 5-15 (default 10)."
    )
    parser.add_argument(
        "--engine", default="UE5", help='Target engine, e.g. "UE5" or "Godot 4" (default UE5).'
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Use the LLM backend for gameplay design (falls back if unavailable).",
    )
    parser.add_argument(
        "--format",
        choices=["summary", "json", "gdd", "specs"],
        default="summary",
        help="Output format (default summary).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="After planning, run the Godot executor to produce a runnable project.",
    )
    parser.add_argument(
        "--godot-exe",
        default=None,
        help="Path to the Godot executable (defaults to auto-detection).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the execution confirmation gate and run side effects immediately.",
    )
    parser.add_argument(
        "--no-import",
        action="store_true",
        help="With --execute, stop after validation (do not launch Godot).",
    )
    parser.add_argument(
        "--with-assets",
        action="store_true",
        help="With --execute, run Blender to export glb assets and copy them into the project.",
    )
    parser.add_argument(
        "--blender-exe",
        default=None,
        help="Path to the Blender executable (defaults to auto-detection).",
    )
    parser.add_argument(
        "--approval-manifest-path",
        default=None,
        help="Workspace-relative approval manifest for gated Godot asset copy.",
    )
    parser.add_argument(
        "--with-visuals",
        action="store_true",
        help="With --execute, run ComfyUI to generate visual references and copy them in.",
    )
    parser.add_argument(
        "--with-gameplay",
        action="store_true",
        help="With --execute, generate real playable GDScript (mechanics + win/fail). "
        "Plans with a production spec bundle compile scripts deterministically from it; "
        "legacy bundle-less plans try the LLM first and fall back to deterministic "
        "templates if the Godot import fails.",
    )
    parser.add_argument(
        "--comfyui-endpoint",
        default=None,
        help="ComfyUI endpoint override (defaults to auto-detection).",
    )
    parser.add_argument(
        "--agent",
        default=None,
        metavar="GOAL",
        help=(
            "Run the bounded planning agent loop on this goal instead of the "
            "fixed pipeline. Tool calling runs on whichever provider is "
            "configured (anthropic, openai_compatible or openai_responses)."
        ),
    )
    parser.add_argument(
        "--agent-max-turns",
        type=int,
        default=8,
        help="Hard ceiling on agent round-trips (default 8).",
    )
    parser.add_argument(
        "--agent-engine-tools",
        action="store_true",
        help=(
            "Also expose the Godot/Unreal/Blender/ComfyUI tools. Read-only "
            "checks are offered either way; writing or launching needs the "
            "matching grant below."
        ),
    )
    parser.add_argument(
        "--agent-allow-write",
        action="store_true",
        help="Let the agent write generated files (WRITE-tier tools).",
    )
    parser.add_argument(
        "--agent-allow-execute",
        action="store_true",
        help="Let the agent launch Godot/Unreal/Blender/ComfyUI (EXECUTE tier).",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Reuse an existing session id instead of starting a new one.",
    )
    parser.add_argument(
        "--from-stage",
        default=None,
        help=(
            "With --execute and --session-id, resume the Godot chain at this node and "
            "skip the earlier ones that already succeeded. Accepts a stage ("
            + ", ".join(GODOT_STAGE_ORDER)
            + ") or a re-work target from the pre-flight gate ("
            + ", ".join(sorted(REWORK_TARGET_STAGES))
            + ")."
        ),
    )
    parser.add_argument(
        "--unreal-exe",
        default=None,
        help="Path to UnrealEditor-Cmd (defaults to auto-detection) for --engine UE5.",
    )
    return parser


def _run_agent(args) -> int:
    """Run the bounded planning loop and print what it did."""

    from fantasy_agent.agent_loop import run_agent

    result = run_agent(
        args.agent,
        max_turns=max(1, args.agent_max_turns),
        include_engine_tools=args.agent_engine_tools,
        allow_write=args.agent_allow_write,
        allow_execute=args.agent_allow_execute,
    )

    print(f"[{result.status}] {result.tool_calls} tool call(s)")
    for step in result.steps:
        for call in step.calls:
            marker = "!" if call["status"] != "ok" else "-"
            print(f"  {marker} {call['name']}: {call['status']}")
            if call["status"] != "ok":
                print(f"      {call['content']}")
    if result.refusals:
        print(f"  refused (needs confirmation): {', '.join(result.refusals)}")
    if result.error:
        print(f"  error: {result.error}", file=sys.stderr)
    print()
    print(result.answer or "(no answer)")
    return 0 if result.ok else 1


def _print_summary(plan) -> None:
    spec = plan.gameplay_spec
    print(f"# {spec.title}")
    print(f"  {spec.logline}\n")
    print(f"  Session target : {spec.target_session_minutes} min")
    print(f"  Core verbs     : {', '.join(spec.core_verbs)}")
    print(f"  Core loop      : {len(spec.core_loop)} steps")
    print(f"  Systems        : {', '.join(s.name for s in spec.systems)}")
    print(f"  Win state      : {spec.win_state}")
    print(f"  Level beats    : {', '.join(b.name for b in spec.level_beats)}")
    print(f"  Asset needs    : {len(spec.asset_needs)} items")
    print()
    print(f"  Godot plan     : {plan.godot_plan.project_name}")
    print(f"  Unreal plan    : {plan.unreal_plan.project_name}")
    print(f"  Blender jobs   : {len(plan.blender_plan.jobs)}")
    print(f"  QA checks      : {len(plan.qa_plan.smoke_tests)} smoke tests")
    print("\n  Next actions:")
    for action in plan.next_actions:
        print(f"    - {action}")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.agent:
        return _run_agent(args)

    if args.spec_file:
        from fantasy_agent.production_spec_runtime import (
            director_plan_from_production_spec_bundle,
            load_production_spec_bundle,
        )
        from fantasy_agent.spec_validation import validate_production_spec_bundle

        try:
            bundle = load_production_spec_bundle(args.spec_file, workspace_root=Path.cwd())
        except Exception as exc:  # noqa: BLE001 - surface validation errors cleanly
            print(f"Invalid production spec bundle: {exc}", file=sys.stderr)
            return 2
        if not args.execute and args.format == "specs":
            print(bundle.model_dump_json(indent=2))
            return 0
        report = validate_production_spec_bundle(bundle)
        if report.status == "failed":
            print("Invalid production spec bundle:", file=sys.stderr)
            for issue in report.issues:
                if issue.severity == "error":
                    print(f"  - [{issue.spec}] {issue.field}: {issue.message}", file=sys.stderr)
            return 2
        bundle = bundle.model_copy(update={"validation": report})
        try:
            plan = director_plan_from_production_spec_bundle(
                bundle,
                engine_version=args.engine,
            )
        except Exception as exc:  # noqa: BLE001 - surface validation errors cleanly
            print(f"Invalid production spec bundle: {exc}", file=sys.stderr)
            return 2
        if args.execute:
            return _run_executor(plan, args)
        if args.format == "json":
            print(plan.model_dump_json(indent=2))
        elif args.format == "gdd":
            print(plan.gdd.markdown)
        else:
            _print_summary(plan)
        return 0

    if not args.prompt:
        print("Invalid request: provide --prompt or --spec-file.", file=sys.stderr)
        return 2

    try:
        request = PromptRequest(
            prompt=args.prompt,
            target_minutes=args.minutes,
            engine_version=args.engine,
        )
    except Exception as exc:  # noqa: BLE001 - surface validation errors cleanly
        print(f"Invalid request: {exc}", file=sys.stderr)
        return 2

    if args.format == "gdd":
        # GDD only needs the spec, not the full plan.
        spec = design_from_prompt(request, use_llm=args.llm)
        print(render_gdd(spec).markdown)
        return 0

    # run_director_workflow calls design_from_prompt internally (with default,
    # env-driven behavior). Opt into the LLM path for the whole workflow by
    # setting the flag in-process, so every downstream plan derives from the
    # same gameplay spec rather than swapping one field after the fact.
    if args.llm:
        os.environ["FANTASY_AGENT_USE_LLM"] = "1"

    plan = run_director_workflow(request)

    if args.execute:
        return _run_executor(plan, args)

    if args.format == "specs":
        print(plan.production_spec_bundle.model_dump_json(indent=2))
    elif args.format == "json":
        print(plan.model_dump_json(indent=2))
    else:
        _print_summary(plan)
    return 0


def _run_executor(plan, args) -> int:
    from fantasy_agent.demo_launch import (
        DemoLaunch,
        DemoLaunchError,
        infer_demo_engine,
        launch_demo,
        resolve_demo_executables,
    )
    from fantasy_agent.executor import format_execution_report

    engine = infer_demo_engine(plan, args.engine or "")
    tools = resolve_demo_executables(
        godot_exe=args.godot_exe,
        blender_exe=args.blender_exe,
        unreal_cmd=args.unreal_exe,
    )
    run_import = not args.no_import
    if engine == "unreal" and (args.with_assets or args.with_visuals):
        print(
            "[note] --with-assets/--with-visuals are not applied on the Unreal path in M4 "
            "(project generation + DataValidation only); ignoring.",
            file=sys.stderr,
        )
    if engine == "godot" and args.execute and run_import and not tools.godot_found:
        print(
            "No Godot executable found. Pass --godot-exe PATH or use --no-import "
            "to stop after validation.",
            file=sys.stderr,
        )
        return 2
    if engine == "godot" and args.with_assets and not tools.blender_found:
        print(
            "No Blender executable found. Pass --blender-exe PATH or drop "
            "--with-assets to build a greybox-only demo.",
            file=sys.stderr,
        )
        return 2
    if engine == "unreal" and run_import and not tools.unreal_found:
        print(
            "No Unreal executable found. Pass --unreal-exe PATH or use --no-import "
            "to stop after project generation.",
            file=sys.stderr,
        )
        return 2

    try:
        result = launch_demo(
            DemoLaunch(
                plan=plan,
                engine=args.engine or "",
                confirmed=args.yes,
                session_id=args.session_id or "",
                resume_from=args.from_stage,
                with_assets=args.with_assets,
                with_visuals=args.with_visuals,
                with_gameplay=args.with_gameplay,
                approval_manifest_path=args.approval_manifest_path,
                run_import=run_import,
                comfyui_endpoint=args.comfyui_endpoint,
                resolved=tools,
            )
        )
    except DemoLaunchError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(format_execution_report(result))
    if result.status == "confirmation_required":
        return 0
    return 0 if result.ok else 1
