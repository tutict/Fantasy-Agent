"""Mutation check for the guards this project relies on to catch regressions.

For each case: apply one mutation to the source, run the guard that is supposed
to catch it, and require that guard to go red. Restores every file byte-for-byte
and verifies the restore.

    python scripts/mutation_check_all_guards.py

A green suite says the guards pass. It does not say they would *fail* if the
behaviour they describe were removed -- a guard can be green and vacuous at the
same time. Each mutation here is a *realistic* regression: the shape the code
had before the fix, or the plausible mistake a later edit would make.

The verdict comes from the runner's own counts, never from its exit code,
because exit codes are wrong in both directions here:

- a guard whose node id no longer exists collects **nothing** and the runner
  exits 2 -- which "non-zero means caught" would read as a live guard;
- a guard that skips itself exits 0 with a green report -- which reads as a
  missed mutation, and is how a Godot-side regression once shipped unnoticed.

So two outcomes are reported as *unproven* rather than either pass or fail:
``NO RUN`` (nothing collected) and ``SKIPPED`` (the guard declined). Cases whose
guard needs a local engine declare it in ``ENGINE_REQUIREMENTS``; where that
engine is absent they are ``N/A`` instead, which is what lets this run on a
machine -- or a CI runner -- with no engines installed.

One hazard is the harness's own: the only moment a mutated file is on disk is
the guard run, which is the long, interruptible part of a case. A run killed
there leaves the mutation behind (``finally`` does not run on a kill), and the
next run reports it as some *other* case whose needle "appears 0x". That is a
stale-needle report for a file nobody edited, so both places say so.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

#: (label, file, needle, mutant, test id)
CASES: tuple[tuple[str, str, bytes, bytes, str], ...] = (
    (
        "G1 main.gd indexes the const manifest",
        "fantasy_agent/godot_mcp.py",
        b'HANDOFF.get("gameplay", {{}}) as Dictionary',
        b'HANDOFF["gameplay"] as Dictionary',
        "tests/test_godot_mcp.py::test_generated_main_script_never_indexes_the_handoff_literal",
    ),
    (
        "G2 same, caught by real Godot",
        "fantasy_agent/godot_mcp.py",
        b'HANDOFF.get("gameplay", {{}}) as Dictionary',
        b'HANDOFF["gameplay"] as Dictionary',
        "tests/test_gdscript_godot_check.py::test_the_registry_built_project_survives_a_real_godot",
    ),
    (
        "G3 the guard only looks on PATH",
        "tests/test_gdscript_godot_check.py",
        # Line endings are matched against the file on disk by _as_eol().
        b'        local_tools._find_godot() or "",\n',
        b"",
        "tests/test_godot_mcp.py::test_the_godot_guard_module_does_not_silently_skip_here",
    ),
    (
        "R1 run dir back inside the repo",
        "scripts/run_tests.py",
        b'TEMP_ROOT = Path(tempfile.gettempdir()) / "fantasy-agent-pytest"',
        b'TEMP_ROOT = REPO_ROOT / "generated" / "test-tmp" / "runs"',
        "tests/test_run_tests_runner.py::test_the_run_directory_is_outside_the_repo_and_under_the_os_temp_root",
    ),
    (
        "R2 parent directory never created",
        "scripts/run_tests.py",
        b"    TEMP_ROOT.mkdir(parents=True, exist_ok=True)\n",
        b"",
        "tests/test_run_tests_runner.py::test_main_creates_the_run_directory_parent",
    ),
    (
        "P1 probe addresses a stale tool name",
        "scripts/verify_engine_links.py",
        b'    "generate_asset_batch",\n    "probe_comfyui_capabilities",',
        b'    "generate_asset_batch_v2",\n    "probe_comfyui_capabilities",',
        "tests/test_workbench_tool_coverage.py::test_every_tool_the_engine_probe_addresses_is_registered",
    ),
    (
        "P3 reported paths resolved against the cwd",
        "scripts/verify_engine_links.py",
        b"    return workspace / path",
        b"    return Path(path)",
        "tests/test_workbench_tool_coverage.py::test_the_probe_resolves_reported_paths_against_its_own_workspace",
    ),
    (
        "P2 probe stops granting the write it needs",
        "scripts/verify_engine_links.py",
        b'        "create_project_structure",\n        {"write_files": True},\n        allow_write=True,\n',
        b'        "create_project_structure",\n        {"write_files": True},\n',
        "tests/test_workbench_tool_coverage.py::test_the_engine_probe_reports_every_link_without_any_engine_installed",
    ),
    (
        "L1 openai_responses falls through to the anthropic branch",
        "fantasy_agent/llm.py",
        b'if resolved["provider"] == OPENAI_RESPONSES:\n',
        b"if False:\n",
        "tests/test_llm_tool_calling.py::test_json_generation_refuses_the_responses_provider",
    ),
    (
        "L2 responses tool turn stops checking for a key",
        "fantasy_agent/llm.py",
        b'        raise LLMError("No API key configured for the OpenAI Responses provider.")\n',
        b"        pass  # mutation: key guard removed\n",
        # Pinned to the provider the guard is about. The bare id would collect a
        # test per provider, and whichever leg failed first would be reported as
        # this mutation being caught.
        (
            "tests/test_llm_tool_calling.py"
            "::test_a_missing_key_is_a_loud_failure_not_a_degraded_run[openai_responses]"
        ),
    ),
    (
        "L3 the openai_compatible tool turn stops being dispatched",
        "fantasy_agent/llm.py",
        (
            b"    if provider == OPENAI_COMPATIBLE:\n"
            b"        return _openai_chat_tool_turn(\n"
            b"            instructions=instructions,"
        ),
        (
            b'    if provider == "never":\n'
            b"        return _openai_chat_tool_turn(\n"
            b"            instructions=instructions,"
        ),
        # Pinned to the provider whose dispatch the mutation removes.
        (
            "tests/test_llm_tool_calling.py"
            "::test_the_loop_accepts_a_tool_call_on_every_provider[openai_compatible]"
        ),
    ),
    (
        "L4 the chat transcript relabels a tool result as an assistant turn",
        "fantasy_agent/llm.py",
        b'                    "role": "tool",\n                    "tool_call_id": _call_id(item),',
        b'                    "role": "assistant",\n                    "tool_call_id": _call_id(item),',
        "tests/test_llm_tool_calling.py::test_openai_chat_nests_tools_under_function_and_keys_results_by_call_id",
    ),
    (
        "R3 run id loses its uniqueness",
        "scripts/run_tests.py",
        b'return f"{stamp}-{os.getpid()}-{token_hex(4)}"\n',
        b"return stamp\n",
        "tests/test_run_tests_runner.py::test_two_runs_cannot_be_handed_the_same_directory",
    ),
    (
        "U1 Unreal discovery stops reading the Launcher manifest",
        "fantasy_agent/local_tools.py",
        b"        *_unreal_launcher_installs(),\n",
        b"",
        "tests/test_unreal_mcp.py::test_unreal_is_found_through_the_launcher_manifest",
    ),
    (
        "U2 a plugin row answers for an engine",
        "fantasy_agent/local_tools.py",
        b'        if not str(entry.get("ArtifactId") or "").startswith("UE_"):\n            continue\n',
        b"",
        "tests/test_unreal_mcp.py::test_unreal_is_found_through_the_launcher_manifest",
    ),
    (
        "D1 the local DDC path length check is dropped",
        "fantasy_agent/unreal_mcp.py",
        b"        if len(local_ddc.as_posix()) <= MAX_LOCAL_DDC_PATH:\n            return local_ddc\n",
        b"        return local_ddc  # mutation: length check removed\n",
        "tests/test_unreal_mcp.py::test_a_long_workspace_moves_the_local_ddc_out_of_the_project",
    ),
    (
        "D2 every long-path project shares one relocated cache",
        "fantasy_agent/unreal_mcp.py",
        b'        return Path(tempfile.gettempdir()) / "fantasy-agent-ue-ddc" / digest[:16]\n',
        b'        return Path(tempfile.gettempdir()) / "fantasy-agent-ue-ddc"\n',
        "tests/test_unreal_mcp.py::test_two_long_path_projects_get_different_caches",
    ),
    (
        "S1 the panel stops asking the shared resolver",
        "apps/studio/app/main.py",
        b"    editor = local_tools._find_unreal()\n",
        b"    editor = None\n",
        "tests/test_studio_app.py::test_the_unreal_panel_reports_the_binary_a_run_would_launch",
    ),
    (
        "S2 the panel names the editor, not the -Cmd build",
        "apps/studio/app/main.py",
        b"            target=local_tools._unreal_cmd_executable(editor) or editor,\n",
        b"            target=editor,\n",
        "tests/test_studio_app.py::test_the_unreal_panel_reports_the_binary_a_run_would_launch",
    ),
    (
        "C1 the ComfyUI panel answers for itself instead of asking the resolver",
        "apps/studio/app/main.py",
        b"    target = local_tools._comfyui_target()\n",
        (b'    target = {"status": "ready", "target": "http://127.0.0.1:8188", "metadata": {}}\n'),
        "tests/test_studio_app.py::test_the_comfyui_panel_asks_the_shared_resolver_instead_of_probing_again",
    ),
    (
        "C2 the local-endpoint check stops rejecting non-local hosts",
        "fantasy_agent/local_tools.py",
        (
            b"def _is_local_http_endpoint(endpoint: str) -> bool:\n"
            b"    parsed = parse.urlparse(endpoint)\n"
            b'    return parsed.scheme in {"http", "https"} and parsed.hostname in {\n'
            b'        "127.0.0.1",\n'
            b'        "localhost",\n'
            b'        "::1",\n'
            b"    }\n"
        ),
        b"def _is_local_http_endpoint(endpoint: str) -> bool:\n    return True\n",
        "tests/test_studio_app.py::test_a_remote_comfyui_endpoint_is_never_probed_by_the_panel",
    ),
    (
        "C3 the local-endpoint check stops reading the scheme",
        "fantasy_agent/local_tools.py",
        b'    return parsed.scheme in {"http", "https"} and parsed.hostname in {\n',
        b"    return parsed.hostname in {\n",
        "tests/test_comfyui_mcp.py::test_comfyui_mcp_rejects_a_non_http_scheme_on_a_local_host",
    ),
    (
        "C4 the ComfyUI panel dials the endpoint itself as well as asking",
        "apps/studio/app/main.py",
        b"    target = local_tools._comfyui_target()\n",
        (
            b"    try:\n"
            b'        local_tools._http_json("http://127.0.0.1:8188/system_stats")\n'
            b"    except OSError:\n"
            b"        pass\n"
            b"    target = local_tools._comfyui_target()\n"
        ),
        "tests/test_studio_app.py::test_the_comfyui_panel_opens_no_socket_of_its_own",
    ),
    (
        "C5 the ComfyUI probe goes back to one candidate at a time",
        "fantasy_agent/local_tools.py",
        b"        pool = ThreadPoolExecutor(max_workers=len(probed))\n",
        b"        pool = ThreadPoolExecutor(max_workers=1)\n",
        "tests/test_studio_app.py::test_the_comfyui_probe_queries_candidates_at_the_same_time",
    ),
    (
        "C6 the ComfyUI probe reads the candidates in the wrong order",
        "fantasy_agent/local_tools.py",
        b"            for index in range(len(probed)):\n",
        b"            for index in range(len(probed) - 1, -1, -1):\n",
        "tests/test_studio_app.py::test_the_comfyui_probe_still_prefers_a_configured_endpoint",
    ),
    (
        "U3 the manifest reader stops tolerating a truncated file",
        "fantasy_agent/local_tools.py",
        (
            b"    try:\n"
            b'        payload = json.loads(manifest.read_text(encoding="utf-8-sig"))\n'
            b"    except (OSError, ValueError):\n"
            b"        return []\n"
        ),
        b'    payload = json.loads(manifest.read_text(encoding="utf-8-sig"))\n',
        "tests/test_unreal_mcp.py::test_unreal_discovery_reports_nothing_rather_than_raising",
    ),
    (
        "U4 the version key goes back to every digit in the path",
        "fantasy_agent/local_tools.py",
        (
            b"    match = _UNREAL_VERSION_IN_PATH.search(path)\n"
            b'    version = tuple(int(part) for part in match.group(1).split(".")) if match else ()\n'
        ),
        b'    version = tuple(int(part) for part in re.findall(r"\\d+", path))\n',
        "tests/test_unreal_mcp.py::test_the_version_sorting_ignores_digits_that_are_not_the_version",
    ),
    (
        "U5 a relative PROGRAMDATA root is followed again",
        "fantasy_agent/local_tools.py",
        b"        if candidate.is_absolute():\n            return candidate\n",
        b"        return candidate\n",
        "tests/test_unreal_mcp.py::test_a_relative_program_data_root_is_not_followed",
    ),
    # ── the harness's own guards ────────────────────────────────────────────
    # A harness that quietly stops mutating anything is worse than no harness:
    # it reports "all caught" while checking nothing. `tests/test_mutation_harness.py`
    # guards these inputs statically, and these cases hold that guard file to the
    # same standard it enforces -- each one has to make it go red.
    (
        "H1 a needle drifting away from its target goes unnoticed",
        "fantasy_agent/local_tools.py",
        b"        *_unreal_launcher_installs(),",
        b"        *_unreal_launcher_installs_v2(),",
        "tests/test_mutation_harness.py::test_every_needle_still_matches_exactly_once",
    ),
    (
        "H2 line endings stop being normalised",
        "scripts/mutation_check_all_guards.py",
        b'    return needle.replace(b"\\r\\n", b"\\n").replace(b"\\n", eol)\n',
        b"    return needle\n",
        "tests/test_mutation_harness.py::test_line_endings_are_normalised_to_the_file_on_disk",
    ),
    (
        "H3 an engine-requirement key stops matching a case",
        "scripts/mutation_check_all_guards.py",
        b'    "G2 same, caught by real Godot": "godot",\n',
        b'    "G2 same, caught by real Godot ": "godot",\n',
        "tests/test_mutation_harness.py::test_engine_requirements_name_cases_that_still_exist",
    ),
    (
        "H4 a case names a guard that does not exist",
        "scripts/mutation_check_all_guards.py",
        b'        "tests/test_run_tests_runner.py::test_main_creates_the_run_directory_parent",\n',
        b'        "tests/test_run_tests_runner.py::test_main_creates_the_run_dir_parent",\n',
        "tests/test_mutation_harness.py::test_every_named_guard_exists",
    ),
    (
        "H5 an engine requirement names something unprobeable",
        "scripts/mutation_check_all_guards.py",
        b'    "G3 the guard only looks on PATH": "godot",\n',
        b'    "G3 the guard only looks on PATH": "godot4",\n',
        "tests/test_mutation_harness.py::test_engine_requirements_name_engines_the_harness_can_probe",
    ),
    (
        "C7 the Godot key goes back to every digit in the path",
        "fantasy_agent/local_tools.py",
        # Spans the match and the version line together: `_unreal_candidate_key`
        # carries the identical version line, so it is not unique on its own.
        (
            b"    match = _GODOT_VERSION_IN_NAME.search(candidate.name)"
            b" or _GODOT_VERSION_IN_NAME.search(\n"
            b"        candidate.parent.name\n"
            b"    )\n"
            b'    version = tuple(int(part) for part in match.group(1).split("."))'
            b" if match else ()\n"
        ),
        b'    version = tuple(int(part) for part in re.findall(r"\\d+", path))\n',
        (
            "tests/test_local_tools.py"
            "::test_a_digit_in_the_install_path_does_not_outrank_the_engine_version"
        ),
    ),
    (
        "C8 naming a directory satisfies the executable check again",
        "fantasy_agent/local_tools.py",
        b"        if value and Path(value).is_file():\n",
        b"        if value and Path(value).exists():\n",
        (
            "tests/test_local_tools.py"
            "::test_a_directory_named_as_the_executable_does_not_answer_a_probe"
        ),
    ),
    (
        "C9 the open path stops catching an unlaunchable target",
        "fantasy_agent/local_tools.py",
        b"    except OSError as exc:\n",
        b"    except FileNotFoundError as exc:\n",
        "tests/test_local_tools.py::test_the_open_path_reports_a_target_it_cannot_launch",
    ),
    (
        "C10 a backend detail key is renamed without the dictionary",
        "fantasy_agent/local_tools.py",
        b'            "detail_key": "manualOpenUnavailable",\n',
        b'            "detail_key": "manualOpenUnavailableRenamed",\n',
        (
            "tests/test_local_tools.py"
            "::test_every_detail_key_the_open_path_returns_exists_in_the_frontend"
        ),
    ),
    # ── the generated prototype ──────────────────────────────────────────
    # Every one of these ships a project that imports, parses and pumps frames
    # cleanly. The cases whose guard says "godot" end in a real playtest.
    (
        "D1 the beat marker is a solid body again",
        "fantasy_agent/godot_mcp.py",
        b"    return _prop(node_name, origin, size, color)\n",
        b"    return _box(node_name, origin, size, color)\n",
        "tests/test_godot_mcp.py::test_route_props_carry_no_collision",
    ),
    (
        "D2 the exit trigger is a child of its own gate again",
        "fantasy_agent/godot_mcp.py",
        b"            add_child(area)\n",
        b"            exit.add_child(area)\n",
        "tests/test_godot_mcp.py::test_the_exit_trigger_is_not_a_child_of_its_own_gate",
    ),
    (
        "D3 the same, caught by a real playtest",
        "fantasy_agent/godot_mcp.py",
        b"            add_child(area)\n",
        b"            exit.add_child(area)\n",
        (
            "tests/test_gdscript_godot_check.py"
            "::test_the_generated_prototype_can_actually_be_played[parkour]"
        ),
    ),
    (
        "D4 the player spawns on a hardcoded coordinate again",
        "fantasy_agent/godot_mcp.py",
        b"        player.position = _player_spawn_position()\n",
        b"        player.position = Vector3(-6.0, 1.0, 0.0)\n",
        "tests/test_godot_mcp.py::test_the_player_spawns_where_the_route_actually_starts",
    ),
    (
        "D5 the same, caught by a real playtest",
        "fantasy_agent/godot_mcp.py",
        b"        player.position = _player_spawn_position()\n",
        b"        player.position = Vector3(-6.0, 1.0, 0.0)\n",
        (
            "tests/test_gdscript_godot_check.py"
            "::test_the_generated_prototype_can_actually_be_played[parkour]"
        ),
    ),
    (
        "D6 the route is laid out across the player again",
        "fantasy_agent/godot_mcp.py",
        b"            f'    _box(\"{floor_name}\", Vector3(0.0, 0.0, {z:.1f}), '\n",
        b"            f'    _box(\"{floor_name}\", Vector3({z:.1f}, 0.0, 0.0), '\n",
        "tests/test_godot_mcp.py::test_the_route_runs_along_the_axis_move_forward_moves[True]",
    ),
    (
        "D7 the tiles are a stride apart again",
        "fantasy_agent/godot_mcp.py",
        b"    spacing = 5.0\n",
        b"    spacing = 6.0\n",
        "tests/test_godot_mcp.py::test_the_route_has_no_gap_between_tiles",
    ),
    (
        "D8 the same gap, caught by a real playtest",
        "fantasy_agent/godot_mcp.py",
        b"    spacing = 5.0\n",
        b"    spacing = 6.0\n",
        (
            "tests/test_gdscript_godot_check.py"
            "::test_the_generated_prototype_can_actually_be_played[parkour]"
        ),
    ),
    (
        "D9 the pipeline stops supplying the gameplay spec",
        "fantasy_agent/tool_registry.py",
        b'        for key in ("gameplay_spec", "production_spec_bundle"):\n',
        b'        for key in ("production_spec_bundle",):\n',
        "tests/test_godot_mcp.py::test_a_tool_call_builds_a_project_that_can_be_played",
    ),
    (
        "D10 the burst verbs are one-frame impulses again",
        "fantasy_agent/gameplay_codegen.py",
        # One frame of burst: the timer is set to a single delta instead of the
        # verb's own duration, so the impulse survives exactly one frame.
        b"        _dash_time = dash_duration\n",
        b"        _dash_time = delta\n",
        (
            "tests/test_gameplay_codegen_axis.py"
            "::test_burst_verbs_last_longer_than_one_frame[mobility]"
        ),
    ),
    (
        "D11 the dash stops moving the player",
        "fantasy_agent/gameplay_codegen.py",
        # The line lives inside a template string, so its trailing newline is the
        # two characters ``\`` and ``n``, not a byte break -- written as such
        # because the harness rewrites real line endings to the file's own.
        b"@export var dash_impulse := 9.0     # [DASH_IMPULSE]\\n",
        b"@export var dash_impulse := 0.0     # [DASH_IMPULSE]\\n",
        (
            "tests/test_gdscript_godot_check.py"
            "::test_the_generated_prototype_can_actually_be_played[mobility]"
        ),
    ),
    (
        "D12 a fall off the route stops ending the run",
        "fantasy_agent/gameplay_codegen.py",
        (
            b"    var player := _find_player()\n"
            b"    if player != null and player.global_position.y < fall_limit:\n"
            b'        _fail("{boundary}")\n'
        ),
        b"",
        "tests/test_gameplay_codegen_axis.py::test_losing_the_route_ends_the_run",
    ),
    (
        "D13 the patrol walks across the route again",
        "fantasy_agent/gameplay_codegen.py",
        (
            b"    position.z += _direction * move_speed * delta\n"
            b"    if abs(position.z - _origin.z) >= patrol_radius:\n"
        ),
        (
            b"    position.x += _direction * move_speed * delta\n"
            b"    if abs(position.x - _origin.x) >= patrol_radius:\n"
        ),
        (
            "tests/test_gdscript_godot_check.py"
            "::test_the_generated_prototype_can_actually_be_played[stealth]"
        ),
    ),
    (
        "D14 the enemies pile back onto the exit tile",
        "fantasy_agent/godot_mcp.py",
        b"    var interior := floors.slice(1, floors.size() - 1)\n",
        b"    var interior := floors.slice(1, floors.size())\n",
        (
            "tests/test_gdscript_godot_check.py"
            "::test_the_generated_prototype_can_actually_be_played[stealth]"
        ),
    ),
    (
        "D15 two enemies share a spawn point again",
        "fantasy_agent/godot_mcp.py",
        (
            b"    var lane: float = lanes[floori(float(index) / float(interior.size()))"
            b" % lanes.size()]\n"
        ),
        b"    var lane: float = 1.15 if index % 2 == 0 else -1.15\n",
        (
            "tests/test_gdscript_godot_check.py"
            "::test_the_generated_prototype_can_actually_be_played[stealth]"
        ),
    ),
    (
        "D16 a hidden argument the model sent is kept",
        "fantasy_agent/tool_registry.py",
        (b"        for argument in hidden:\n            args.pop(argument, None)\n"),
        (
            b"        for argument in hidden:\n"
            b"            pass  # mutation: the model's value is kept\n"
        ),
        "tests/test_agent_loop.py::test_a_hidden_argument_the_model_sent_is_discarded",
    ),
    (
        "D17 a spec's own words go into a GDScript literal unescaped",
        "fantasy_agent/gameplay_codegen.py",
        (b'    return " ".join(text.split()).replace("\\\\", "\\\\\\\\").replace(\'"\', "\'")\n'),
        b"    return text.replace('\"', \"'\")\n",
        "tests/test_gameplay_codegen_axis.py::test_spec_text_cannot_break_the_generated_literal",
    ),
    (
        "H6 the parametrised-guard check stops recognising parametrisation",
        "tests/test_mutation_harness.py",
        (
            b'    r"@pytest\\.mark\\.parametrize\\(.*?\\)\\s*\\n(?:\\s*@[^\\n]*\\n)'
            b'*\\s*def (\\w+)\\(", re.DOTALL\n'
        ),
        (
            b'    r"@pytest\\.mark\\.parametrize_MUTANT\\(.*?\\)\\s*\\n(?:\\s*@[^\\n]*\\n)'
            b'*\\s*def (\\w+)\\(", re.DOTALL\n'
        ),
        "tests/test_mutation_harness.py::test_a_bare_id_for_a_parametrised_guard_is_rejected",
    ),
    # ── the orchestration table ─────────────────────────────────────────────
    # `tests/test_pipeline_contract.py` holds the production pipeline to what
    # the orchestrator is about to read off it: an agent stage names its tools,
    # a human stage names none, every name resolves, every edge points backwards
    # and `order` is dense. These cases hold that guard file to the same promise.
    (
        "T1 an agent stage loses the tools it declares",
        "fantasy_agent/workflows.py",
        (
            b"            mcp_tools=[\n"
            b'                "extract_idea_seed",\n'
            b'                "generate_game_production_plan",\n'
            b'                "decompose_production_tasks",\n'
            b'                "render_gdd",\n'
            b"            ],\n"
        ),
        b"",
        "tests/test_pipeline_contract.py::test_every_stage_an_agent_drives_names_the_tools_it_uses",
    ),
    (
        "T2 the human gate is handed a tool",
        "fantasy_agent/workflows.py",
        b'            kind="human",\n',
        b'            kind="human",\n            mcp_tools=["validate_godot_project"],\n',
        "tests/test_pipeline_contract.py::test_a_human_stage_names_no_tools",
    ),
    (
        "T3 the creative review goes back to being an agent stage",
        "fantasy_agent/workflows.py",
        b'            kind="human",\n',
        b"",
        "tests/test_pipeline_contract.py::test_the_creative_review_is_the_pipelines_human_gate",
    ),
    (
        "T4 the stage kind defaults to human",
        "fantasy_agent/contracts.py",
        b'    kind: ProductionStageKind = "agent"\n',
        b'    kind: ProductionStageKind = "human"\n',
        "tests/test_pipeline_contract.py::test_a_stage_written_before_the_kind_field_still_loads_as_an_agent_stage",
    ),
    (
        "T5 a commandlet name goes back in where a tool name belongs",
        "fantasy_agent/workflows.py",
        b'            mcp_tools=["generate_blender_script"],\n',
        b'            mcp_tools=["generate_blender_script", "DataValidation"],\n',
        "tests/test_pipeline_contract.py::test_every_declared_tool_is_one_the_registry_can_resolve",
    ),
    (
        "T6 the declared orders stop being renumbered",
        "fantasy_agent/workflows.py",
        (b"    for index, stage in enumerate(stages, start=1):\n        stage.order = index\n"),
        b"",
        "tests/test_pipeline_contract.py::test_the_order_is_a_dense_sequence_covering_every_stage_once",
    ),
    (
        "T7 a stage waits for one that runs after it",
        "fantasy_agent/workflows.py",
        b'            depends_on=["creative_review"],\n',
        b'            depends_on=["optimization_testing"],\n',
        "tests/test_pipeline_contract.py::test_a_stage_only_depends_on_stages_that_come_before_it",
    ),
    (
        "T8 the next stage is one this route throws away",
        "fantasy_agent/workflows.py",
        b'        next_stage="comfyui_visual_production",\n',
        b'        next_stage="unreal_production",\n',
        "tests/test_pipeline_contract.py::test_the_pipeline_references_only_stages_a_route_actually_builds",
    ),
    (
        # The default value, not a construction site. This case *moved guards*
        # when G-02 landed: ``_pipeline_stage()`` now passes ``exit_checks``
        # (as ``exit_checks or []``) to every stage it builds, so the default no
        # longer reaches any stage of either route and the pipeline-wide scan
        # cannot observe it -- the mutation was equivalent there, and the
        # harness correctly reported MISSED. What still reads the default is a
        # stage payload written before the field existed (an old plan JSON, a
        # hand-built stage), so that is the guard that has to catch a dangerous
        # one. Same shape as T4 -- a field whose default is the only thing
        # standing between an undeclared stage and an unreviewed engine launch.
        "T9 the exit checks default to a tool that launches a process",
        "fantasy_agent/contracts.py",
        b"    exit_checks: list[str] = Field(default_factory=list)\n",
        b'    exit_checks: list[str] = Field(default_factory=lambda: ["run_godot_import"])\n',
        "tests/test_pipeline_contract.py::test_a_stage_written_before_the_exit_checks_field_still_loads",
    ),
    (
        "T10 a failing exit check stops failing the stage",
        "fantasy_agent/orchestrator.py",
        b'            if check.status != "ok":\n',
        b"            if False:\n",
        "tests/test_orchestrator.py::test_an_exit_check_that_reports_a_problem_makes_the_stage_failed",
    ),
    (
        # A check nobody can run is a check that verified nothing, so skipping
        # an unresolvable name turns a typo in the table into a stage that
        # reports itself verified.
        #
        # The mutation `continue`s rather than deleting the branch. An earlier
        # version of this case replaced the condition with `False`, and the
        # guard stayed green -- correctly: `ToolRegistry.call` answers an unknown
        # name with an `error` outcome, so the stage still failed and the test's
        # assertion (`the name is in the detail`) still held. That is an
        # equivalent mutation, not a missed one: behaviour did not change, so
        # there was nothing for a behavioural guard to catch. Only the *skip*
        # is a regression the guard is about.
        "T11 an unresolvable exit check is skipped instead of failing the stage",
        "fantasy_agent/orchestrator.py",
        (
            b"            if self._registry.get(name) is None:\n"
            b"                outcome.status = FAILED\n"
            b"                outcome.detail = (\n"
            b'                    f"exit check {name} is not a registered tool, so this stage "\n'
            b'                    "would have been reported verified without being checked"\n'
            b"                )\n"
            b"                return\n"
        ),
        b"            if self._registry.get(name) is None:\n                continue\n",
        "tests/test_orchestrator.py::test_an_exit_check_that_names_nothing_fails_the_stage_instead_of_being_skipped",
    ),
    (
        # The check has to go through the *full* registry: routing it through
        # the stage's slice looks harmless and then silently skips every check
        # the stage does not also offer the model.
        "T12 the exit check is looked up in the model's whitelist",
        "fantasy_agent/orchestrator.py",
        b"            check = self._registry.call(name, {})\n",
        (b"            check = self._registry.scoped(outcome.tools).call(name, {})\n"),
        "tests/test_orchestrator.py::test_an_exit_check_runs_even_when_it_is_not_in_the_stages_whitelist",
    ),
    (
        # The contract's own Literal is the source of truth for "which stage ids
        # exist", so a stage nobody translated is a rework path that dead-ends.
        "T13 an orchestration stage loses its translation",
        "fantasy_agent/pipeline_state.py",
        b'    "optimization_testing": ("validate",),\n',
        b"",
        "tests/test_pipeline_state.py::test_every_orchestration_stage_has_a_translation_entry",
    ),
    (
        "T14 the reverse lookup stops finding anything",
        "fantasy_agent/pipeline_state.py",
        b"        if executor_stage in executor_stages\n",
        b"        if executor_stage == executor_stages\n",
        "tests/test_pipeline_state.py::test_a_translation_is_readable_in_both_directions",
    ),
    (
        # `>=` is what makes the target itself re-run; with `>` a rework would
        # drop everything *after* the node and leave the broken node finished.
        "T15 the rewind spares the stage it was aimed at",
        "fantasy_agent/orchestrator.py",
        b"                if position >= cutoff and other in self._outcomes\n",
        b"                if position > cutoff and other in self._outcomes\n",
        "tests/test_orchestrator.py::test_rewinding_from_a_stage_makes_the_next_pass_redo_it",
    ),
    (
        # `resume_stage_for` refuses unknown targets so a typo surfaces; a
        # default here would undo that one layer later and rewind a stage the
        # hint never named.
        "T16 an unknown rework target silently rewinds `create`",
        "fantasy_agent/orchestrator.py",
        (
            b"        executor_stage = resume_stage_for(rework_target, code)\n"
            b"        if executor_stage is None:\n"
            b"            return None\n"
        ),
        b'        executor_stage = resume_stage_for(rework_target, code) or "create"\n',
        "tests/test_orchestrator.py::test_an_unrecognised_hint_leaves_the_run_alone",
    ),
    (
        # An unknown stage id and "this stage owns no process step" are two
        # different answers, and only the second one is empty.
        "T17 an unknown orchestration stage translates to no steps",
        "fantasy_agent/pipeline_state.py",
        (
            b"    except KeyError:\n"
            b'        known = ", ".join(sorted(ORCHESTRATION_TO_EXECUTOR_STAGES))\n'
            b"        raise ValueError(\n"
            b'            f"unknown orchestration stage {stage_id!r}; known stages: {known}"\n'
            b"        ) from None\n"
        ),
        b"    except KeyError:\n        return ()\n",
        "tests/test_pipeline_state.py::test_translating_an_unknown_orchestration_stage_fails_loudly",
    ),
    (
        # The stage-level gate. Without it `requires_confirmation` is a badge,
        # and a global grant would authorise every stage in the plan.
        "T18 a stage that asks for confirmation runs anyway",
        "fantasy_agent/orchestrator.py",
        b"        if stage.requires_confirmation and stage.id not in self._confirmed:\n",
        b"        if False:\n",
        "tests/test_orchestrator.py::test_a_stage_that_asks_for_confirmation_waits_for_a_person",
    ),
    (
        # The approval is a user action that arrives with the request; dropping
        # it means "approve stage 3" is silently ignored and the stage waits
        # forever with a live button in front of it.
        "T19 an approval never reaches the orchestrator",
        "fantasy_agent/orchestrator.py",
        b"        self.confirm(confirm_stages)\n",
        b"        self.confirm(())\n",
        "tests/test_orchestrator.py::test_confirming_the_stage_lets_it_run",
    ),
    (
        # A human gate is waiting for a decision, not for an approval that would
        # let it run, so listing it offers the operator a dead control.
        "T20 the human gate is offered as an approve-able stage",
        "fantasy_agent/orchestrator.py",
        b"            and stage.kind != HUMAN_STAGE_KIND\n",
        b"",
        "tests/test_orchestrator.py::test_the_result_lists_who_is_still_waiting_on_a_person",
    ),
    (
        "T21 an unknown stage can be confirmed into the session",
        "fantasy_agent/orchestrator.py",
        b"            executor_stages_for(stage_id)  # raises ValueError for an unknown id\n",
        b"            pass  # mutation: the id is stored without being checked\n",
        "tests/test_orchestrator.py::test_confirming_an_unknown_stage_is_a_loud_error",
    ),
    (
        # The request model has the field and the handler ignores it -- the
        # "call site written, request model not" shape, one layer over.
        "T22 the orchestration endpoint drops the approvals it was sent",
        "apps/studio/app/main.py",
        b"            confirm_stages=req.confirm_stages,\n",
        b"            confirm_stages=(),\n",
        "tests/test_studio_app.py::test_a_second_request_reuses_the_session_it_was_given",
    ),
    (
        "Y1 the close button quits instead of hiding",
        "apps/studio/tray.py",
        (b"        self.hide_window()\n        return False\n"),
        (b"        self.hide_window()\n        return True\n"),
        "tests/test_studio_tray.py::test_closing_the_window_hides_it_instead_of_quitting",
    ),
    (
        "Y2 quitting is cancelled too, so the app cannot be shut down",
        "apps/studio/tray.py",
        b"        if self._quitting:\n            return True\n",
        b"        if False:\n            return True\n",
        "tests/test_studio_tray.py::test_an_explicit_quit_lets_the_close_through",
    ),
    (
        "Y3 showing a minimised window leaves it minimised",
        "apps/studio/tray.py",
        (b"        self._window.restore()\n        self._window.show()\n"),
        (b"        self._window.show()\n        self._window.restore()\n"),
        "tests/test_studio_tray.py::test_showing_restores_before_showing",
    ),
    (
        "Y4 window calls run on the GUI thread and deadlock",
        "apps/studio/tray.py",
        b"        threading.Thread(target=target, daemon=True).start()",
        b"        target()",
        "tests/test_studio_tray.py::test_window_operations_do_not_run_on_the_gui_thread",
    ),
    (
        "Y5 the tray icon thread is never stopped",
        "apps/studio/tray.py",
        (b"        if self._icon is not None:\n            self._icon.stop()\n"),
        b"        if False and self._icon is not None:\n            self._icon.stop()\n",
        "tests/test_studio_tray.py::test_the_quit_menu_item_stops_the_icon_and_destroys_the_window",
    ),
    (
        # Swallowing the tray error is what keeps the window alive; turning the
        # handler into `finally:` logs the same line but re-raises, so a missing
        # notification area or pystray install takes the whole app down.
        #
        # Why this shape and not "delete the try/except": deleting it leaves the
        # comment body and the logger line over-indented under a `try:` that is
        # gone, so the module dies with IndentationError at import. That does
        # turn the guard red, but every other test touching desktop.py turns red
        # with it -- the mutation proves the file is broken, not that this guard
        # is what catches the regression. `finally:` keeps the file importable.
        # An earlier needle covering only `except Exception:` was paired with a
        # byte-identical mutant -- a no-op reported as MISSED. Check both ends.
        "Y6 a missing tray takes the whole window down",
        "apps/studio/desktop.py",
        b"        except Exception:\n",
        b"        finally:\n",
        "tests/test_desktop_launcher.py::test_a_failing_tray_does_not_take_the_window_down_with_it",
    ),
    # ── F4: one document, one owner ─────────────────────────────────────────
    # The console, the workbench and the shell were three documents inside
    # iframes. That made three writers of `document.documentElement` harmless
    # (three `<html>` elements) and let the locale cross the boundary as
    # `?locale=` in a frame's `src`. Inlined into one document, every
    # document-level global needs exactly one writer -- otherwise the winner is
    # whoever's effect runs last, which is decided by mount order.
    #
    # `tests/test_studio_app.py` reads the shipped source and pins that. These
    # cases hold that pin to its promise. There is no engine here, only a text
    # read, which is exactly why the guard can exist at all: React state races
    # do not reproduce in pytest.
    (
        # The shape F4 removed. `panelHref` is still in the file for the routed
        # links, so this mutant compiles -- a broken import would prove the file
        # is broken rather than that the guard has teeth.
        "F4-1 the shell puts a view back inside a frame",
        "apps/frontend/src/studio/StudioShell.tsx",
        b"              <PlanningWorkbench />\n",
        b'              <iframe src={panelHref("workbench") ?? ""} title="workbench" />\n',
        "tests/test_studio_app.py::test_studio_shell_includes_bilingual_ui_controls",
    ),
    (
        # The starting panel goes back to a constant. A deep link to
        # `/web-console` then opens the workbench instead, silently.
        "F4-2 the shell stops deriving the panel from the path",
        "apps/frontend/src/studio/StudioShell.tsx",
        b"  const [activePanel, setActivePanel] = useState<PanelKey>(panelFromPathname);\n",
        b'  const [activePanel, setActivePanel] = useState<PanelKey>("console");\n',
        "tests/test_studio_app.py::test_studio_shell_includes_bilingual_ui_controls",
    ),
    (
        # The first step of a second copy of the locale, and a shape that is
        # valid TypeScript on its own -- the import is all the guard needs to
        # see, which is the point: the key must have one home.
        "F4-3 the shell grows a second copy of the locale key",
        "apps/frontend/src/studio/StudioShell.tsx",
        (
            b'import { STUDIO_SIDEBAR_COLLAPSED_KEY, STUDIO_SIDEBAR_WIDTH_KEY, '
            b'readHandoffPlan } from "../shared/storage";\n'
        ),
        (
            b"import {\n"
            b"  STUDIO_SIDEBAR_COLLAPSED_KEY,\n"
            b"  STUDIO_SIDEBAR_WIDTH_KEY,\n"
            b"  STUDIO_LOCALE_KEY,\n"
            b"  readHandoffPlan,\n"
            b'} from "../shared/storage";\n'
        ),
        "tests/test_studio_app.py::test_studio_shell_includes_bilingual_ui_controls",
    ),
    (
        # `selectedEngineVersion`'s second implementation, restored. The loose
        # `HANDOFF_KEY`-by-literal decode is what the shell used to do; the
        # guard pins the call, so the identifier can no longer satisfy it.
        "F4-4 the engine version is decoded out of localStorage again",
        "apps/frontend/src/studio/StudioShell.tsx",
        b"  return selectedEngineVersion(readHandoffPlan());\n",
        (
            b'  const raw = JSON.parse(localStorage.getItem("fantasy-agent-planning-handoff") || "null");\n'
            b'  return raw?.engine_version ?? "godot";\n'
        ),
        "tests/test_studio_app.py::test_studio_shell_includes_bilingual_ui_controls",
    ),
    (
        # The provider stops being the one writer of the document element. A
        # comment keeps the file parseable; deleting the line outright would
        # leave the second effect body over-indented under a `useEffect` that is
        # still there, and the harness would be reporting a syntax error.
        #
        # This case earned its keep before it ever went green: the guard it
        # targets read `"document.documentElement.lang" in locale_theme_source`,
        # and the module's own docstring names that expression while explaining
        # what the three old documents each did. The substring survived the
        # assignment being deleted, so the case came back MISSED and the assertion
        # is now pinned to `... = locale`. A name-only scan is not a writer scan.
        "F4-5 the provider stops putting the locale on the document",
        "apps/frontend/src/shared/localeTheme.tsx",
        b"    document.documentElement.lang = locale;\n",
        b"    void locale;  // mutation: the locale no longer reaches the document\n",
        "tests/test_studio_app.py::test_studio_shell_includes_bilingual_ui_controls",
    ),
    (
        # Same guard, the other effect. Kept separate from F4-5 because the two
        # assignments are independent lines: one mutation cannot prove both, and
        # the theme half is the one whose substring happened to be unique -- it
        # would have gone vacuous the moment anyone named it in a comment.
        "F4-6 the provider stops putting the theme on the document",
        "apps/frontend/src/shared/localeTheme.tsx",
        b"    document.documentElement.dataset.theme = theme;\n",
        b"    void theme;  // mutation: the theme no longer reaches the document\n",
        "tests/test_studio_app.py::test_studio_shell_includes_bilingual_ui_controls",
    ),
    (
        # Distinct from F4-3: that one is caught by the shell-source pin, this
        # one by the store-key guard, which scans every source file for a key
        # spelled outside `shared/storage.ts`. A rename would otherwise cut the
        # shell off from the handoff with nothing going red.
        "F4-7 the handoff key is spelled out a second time",
        "apps/frontend/src/studio/StudioShell.tsx",
        (
            b'import { STUDIO_SIDEBAR_COLLAPSED_KEY, STUDIO_SIDEBAR_WIDTH_KEY, '
            b'readHandoffPlan } from "../shared/storage";\n'
        ),
        (
            b'import { STUDIO_SIDEBAR_COLLAPSED_KEY, STUDIO_SIDEBAR_WIDTH_KEY, '
            b'readHandoffPlan } from "../shared/storage";\n'
            b'\nconst MIRRORED_HANDOFF_KEY = "fantasy-agent-planning-handoff";\n'
        ),
        "tests/test_studio_app.py::test_store_keys_are_defined_once_and_imported_everywhere",
    ),
    (
        "F3-a the console takes the stage rows back",
        "apps/frontend/src/console/FlowConsole.tsx",
        # The console used to render `production_pipeline`'s stage strip. F3 moved
        # the rows to the orchestration board and pinned the console as an
        # *absence*; this is that absence's realistic regression -- the strip
        # comes back under its old id, next to the log.
        b'className="activity-log"',
        b'className="activity-log" id="stage-strip"',
        "tests/test_web_console_app.py::test_web_console_ui_exposes_flow_console_sections",
    ),
    (
        "F3-b the card root drops the plan status",
        # The card root moved into `StageCard.tsx` when the card was split out
        # of the board (2026-10-17); the needle followed it. A needle left on
        # the old file matches 0x and proves nothing -- which is exactly what
        # `test_every_needle_still_matches_exactly_once` reported for this case.
        "apps/frontend/src/orchestration/StageCard.tsx",
        # One vocabulary for both statuses is the plausible simplification, and it
        # is what makes a card claim "running" off a value the plan wrote once.
        b"data-stage={card.id} data-status={card.status} data-plan-status={card.plan_status}",
        b"data-stage={card.id} data-status={card.status}",
        "tests/test_web_console_app.py::test_orchestration_board_owns_the_stage_rows",
    ),
    (
        "S2 an oversized skill brief stops being cut",
        "fantasy_agent/agent_skills.py",
        # This is not a hypothetical mutant: it is the code as it stood before
        # the ceiling was applied. `MAX_BRIEF_CHARS` was exported with a comment
        # promising it bounds every turn's system prompt, and nothing read it --
        # so the promise held only while no skill happened to grow, and the
        # neighbouring size test passed off today's sizes rather than the cut.
        # The guard that fails here feeds in a brief that does not fit.
        b"    return _strip_sections(text)[:MAX_BRIEF_CHARS]\n",
        b"    return _strip_sections(text)\n",
        "tests/test_agent_skills.py::test_an_oversized_brief_is_cut_to_the_ceiling",
    ),
    (
        "PT1 the playtest counts runs instead of outcomes",
        "fantasy_agent/godot_playtest.py",
        # Counting the per-run counters rather than the outcome is the obvious
        # simplification, and it is silently wrong: a sample built from a raw
        # payload carries outcome="fail" with failures=0, so an all-failure run
        # aggregates to zero failures and no finding ever names the win path.
        (
            b'    wins = sum(1 for s in samples if s.outcome == "win")\n'
            b'    failures = sum(1 for s in samples if s.outcome == "fail")\n'
        ),
        (
            b"    wins = sum(s.wins for s in samples)\n"
            b"    failures = sum(s.failures for s in samples)\n"
        ),
        "tests/test_playtest.py::test_failures_without_a_win_block_the_verdict",
    ),
    (
        "PT2 a script error stops blocking",
        "fantasy_agent/godot_playtest.py",
        b'                "script_error",\n                "blocking",\n',
        b'                "script_error",\n                "warning",\n',
        "tests/test_playtest.py::test_script_errors_block_the_verdict",
    ),
    (
        "PT3 an unobservable run stops blocking",
        "fantasy_agent/godot_playtest.py",
        # The whole point of the degraded path: if the probe cannot see the
        # loop, the report must not be allowed to look merely warn-ish.
        b'                "not_playable",\n                "blocking",\n',
        b'                "not_playable",\n                "warning",\n',
        "tests/test_playtest.py::test_degraded_runs_block_and_name_a_rework_target",
    ),
    (
        "PT4 unmeasured runs collect playtest assertions",
        "fantasy_agent/unreal_spec_adapter.py",
        # The most tempting regression in the whole module: adding the playtest
        # assertions unconditionally makes every QA report look measured, and an
        # empty report passes them. A prototype nobody played would then answer
        # "playtest_runs >= 1" off a zero that came from nothing.
        (
            b"    if playtest is not None:\n"
            b"        assertions.extend(_playtest_assertions())\n"
            b"        actuals.update(_playtest_actuals(playtest))\n"
        ),
        (
            b"    if True:\n"
            b"        assertions.extend(_playtest_assertions())\n"
            b"        actuals.update(_playtest_actuals(playtest or PlaytestReport()))\n"
        ),
        "tests/test_playtest.py::test_static_qa_stays_silent_when_nobody_ran_the_prototype",
    ),
    (
        "PT5 a blocking playtest finding stops failing the run",
        "fantasy_agent/executor.py",
        # The G-03 gate. Before it, a prototype whose win path was never
        # reachable finished "done" with a warning nobody acted on -- five runs,
        # five failures, win_rate 0.0, status "warning". The mutant keeps the
        # stage row honest (it still says "failed") and flips only the run
        # verdict, which is exactly the regression: a chain that reports success
        # while its own stage says the loop is unreachable.
        (
            b"        if blocking:\n"
            b'            return ExecutionResult("failed", session_id, project_dir, stages, planned)\n'
        ),
        (
            b"        if blocking:\n"
            b'            return ExecutionResult("done", session_id, project_dir, stages, planned)\n'
        ),
        "tests/test_executor.py::test_a_blocking_playtest_finding_fails_the_run",
    ),
    (
        "PT6 an unmeasured playtest stops blocking",
        "fantasy_agent/godot_playtest.py",
        # Found by running the real engine against the 2026-07-13 golden slice:
        # its game_manager never joined the group, so the probe recorded zero
        # runs across 60 scene restarts and spent the whole wall budget. Every
        # other finding is guarded by ``aggregate.runs``, so demoting this one
        # puts the gate back to answering "done" for a slice it never saw.
        (
            b'                "playtest_unmeasured",\n'
            b'                "blocking",\n'
        ),
        (
            b'                "playtest_unmeasured",\n'
            b'                "warning",\n'
        ),
        "tests/test_playtest.py::test_a_slice_nobody_could_measure_is_not_a_pass",
    ),
    (
        "PT7 an unreadable outcome stops blocking",
        "fantasy_agent/godot_playtest.py",
        # Same shape as PT6, one layer down: the run ended and the probe cannot
        # tell a win from a failure, so the aggregate counts it as neither and
        # the slice passes by not being counted. Measured on this machine
        # against the 2026-07-13 golden slice, which was winning every run on
        # frame 2 through an exit trigger that overlapped its own gate body.
        (
            b'                "outcome_unreadable",\n'
            b'                "blocking",\n'
        ),
        (
            b'                "outcome_unreadable",\n'
            b'                "warning",\n'
        ),
        "tests/test_playtest.py::test_an_unreadable_outcome_is_not_a_run_that_passed",
    ),
    (
        # The G-03 chain's session-id threading. ``playtest_project`` passes the
        # caller's session id down; drop it and ``run_playtest`` mints its own
        # timestamp, so the executor records
        # ``generated/playtest/<session>/playtest-report.json`` as the stage
        # artifact while the report lands in a directory nobody named. That is
        # not a hypothetical: it is what the end-to-end run did before
        # ``playtest_project``'s docstring recorded it.
        "PT8 the playtest mints its own session id",
        "fantasy_agent/godot_mcp.py",
        b"            session_id=session_id or None,\n",
        b"            session_id=None,\n",
        "tests/test_executor.py::test_the_playtest_stage_runs_the_real_bridge_chain",
    ),
    (
        # The other half of that test: the executor always passes a *relative*
        # project dir, so resolving it against anything but the workspace root
        # measures a directory that was never written and answers
        # ``project_missing`` for a project that exists.
        "PT9 the playtest resolves a relative project against the CWD",
        "fantasy_agent/godot_playtest.py",
        b"        project_dir = Path(workspace_root) / project_dir\n",
        b"        project_dir = project_dir\n",
        "tests/test_executor.py::test_the_playtest_stage_runs_the_real_bridge_chain",
    ),
    (
        "CR1 drift detection trusts the file instead of the recorded hash",
        "fantasy_agent/corrections.py",
        # Without this comparison every artifact is reported as changed, and a
        # report that always says "everything drifted" is a report nobody reads.
        # The mutation makes the hash check vacuously true, which is exactly the
        # shape of the bug: the scan still runs, it just stops being evidence.
        (
            b"        if current and current != expected:\n"
            b"            drifted.append(\n"
        ),
        (
            b"        if current and current == expected:\n"
            b"            drifted.append(\n"
        ),
        "tests/test_corrections.py::test_an_untouched_project_reports_nothing",
    ),
    (
        "CR2 a hand edit is reported from the file hash alone",
        "fantasy_agent/corrections.py",
        # Dropping the value comparison makes every anchor in an edited script
        # look edited -- fifty neighbours burying the one number the operator
        # actually changed. The test that pins this edits exactly one value.
        (
            b"            if only_changed and generated_value is not None "
            b"and _same_number(value, generated_value):\n"
            b"                continue\n"
        ),
        b"",
        "tests/test_corrections.py::test_editing_one_value_does_not_report_its_neighbours",
    ),
    (
        "CR3 an anchor with no baseline is called unchanged",
        "fantasy_agent/corrections.py",
        # Silently skipping an anchor the manifest has no baseline for is the
        # same mistake as calling a missing hash "no drift": it reports
        # "unchanged" on the strength of nothing. The test that pins this adds
        # an anchor the manifest never recorded.
        (
            b"            if only_changed and generated_value is not None "
            b"and _same_number(value, generated_value):\n"
            b"                continue\n"
        ),
        (
            b"            if generated_value is None:\n"
            b"                continue\n"
            b"            if only_changed and _same_number(value, generated_value):\n"
            b"                continue\n"
        ),
        "tests/test_corrections.py::test_an_anchor_with_no_recorded_baseline_is_reported_as_unverified",
    ),
    (
        "CR4 a manifest without hashes is called unchanged",
        "fantasy_agent/corrections.py",
        # A project generated before hashing existed has no evidence either way.
        # Skipping those artifacts reads as "nothing changed", which is the one
        # answer this report must never give without proof.
        b"        if not expected:\n",
        b"        if not expected:\n            continue\n",
        "tests/test_corrections.py::test_a_project_without_a_recorded_hash_is_not_called_unchanged",
    ),
    (
        "CR5 an unrecoverable edit stops saying so",
        "fantasy_agent/corrections.py",
        # Dropping the engine-only note leaves the operator thinking a change to
        # a DSL-less constant is safe. It is not: the next run overwrites it.
        (
            b'        report.notes.append(\n'
            b'            f"{len(engine_only)} edited value(s) are engine constants '
            b'with no field in the "\n'
        ),
        (
            b"        if False:\n"
            b"            report.notes.append(\n"
            b'                f"{len(engine_only)} edited value(s) are engine constants '
            b'with no field in the "\n'
        ),
        "tests/test_corrections.py::test_a_value_with_no_dsl_home_is_reported_as_unrecoverable",
    ),
    (
        # A write that skips the rename and truncates in place. `load_state`
        # answers an unreadable file with None, which means "replay the whole
        # chain" -- ComfyUI, Blender, headless import. So this is the mutation
        # that turns one interrupted write into a re-run of every minute-scale
        # node that had already succeeded.
        "A1 the state file is published by rename",
        "fantasy_agent/atomic_write.py",
        b"        os.replace(tmp, path)\n",
        b"        path.write_text(text, encoding=encoding)\n",
        "tests/test_atomic_write.py::test_a_failed_publish_leaves_the_previous_file_intact",
    ),
    (
        # Flush-after-rename: the name would point at bytes still in the cache.
        # This is the weakest guard in the file -- it pins a call, not an
        # observable result, because the effect of fsync is not visible from
        # inside a test without a crash. Kept anyway, and labelled, rather than
        # dressed up as behavioural.
        "A2 the temporary file is fsynced before the rename",
        "fantasy_agent/atomic_write.py",
        b"            os.fsync(stream.fileno())\n",
        b"            pass  # mutation: not flushed\n",
        "tests/test_atomic_write.py::test_the_publish_goes_through_a_rename",
    ),
    (
        # A half-written temp file left beside the target: the one visible sign
        # that a write failed, and the residue a reader sees in a listing.
        "A3 a failed write cleans up its temporary file",
        "fantasy_agent/atomic_write.py",
        b"            tmp.unlink()\n",
        b"            pass  # mutation: residue left behind\n",
        "tests/test_atomic_write.py::test_a_failed_publish_leaves_the_previous_file_intact",
    ),
    (
        # The stage ledger itself goes back to an in-place write. See A1 for
        # what that costs. The mutant has to be a *working* plain write, not a
        # broken call: a mutant that dies with a TypeError turns the guard red
        # for the wrong reason, which is a false proof rather than evidence.
        "A4 the pipeline state is written atomically",
        "fantasy_agent/pipeline_state.py",
        b"    write_atomic(\n        path,\n",
        b"    path.write_text(\n",
        "tests/test_pipeline_state.py::test_a_crash_midway_leaves_the_previous_state_readable",
    ),
    (
        # The credentials file. `load_settings` answers a parse failure with
        # *defaults*, so a torn write does not look like a failed save -- it
        # looks like the user's API key was never configured.
        "A5 the credentials file is written atomically",
        "fantasy_agent/api_settings.py",
        b"    write_atomic(path, payload)\n",
        b"    path.write_text(payload, encoding='utf-8')\n",
        "tests/test_api_settings.py::test_an_interrupted_save_keeps_the_previous_credentials",
    ),
    (
        # The other half of durability: making the degradation audible again.
        # `None` from `load_state` is not a neutral answer, it is an expensive
        # one, and a silent version of it is indistinguishable from a first run.
        # The mutant keeps the arguments matched -- dropping one makes the
        # logging call itself raise, which is a broken mutant, not a quiet one.
        "A6 a degraded state file is silent again",
        "fantasy_agent/pipeline_state.py",
        (
            b"        logger.warning(\n"
            b'            "pipeline state at %r is not valid JSON (schema_version %r): %s",\n'
            b"            path,\n"
            b"            peek_schema_version(raw),\n"
            b"            exc,\n"
            b"        )\n"
        ),
        b"        peek_schema_version(raw)  # mutation: degraded, but silently\n",
        "tests/test_pipeline_state.py::test_load_state_says_so_when_it_degrades",
    ),
    (
        # The sweep this repository has to survive: someone tidying "all the
        # writes" onto the new helper. `_pump` holds engine logs open with
        # `open("a")` for the life of the subprocess and the bridges write the
        # same two paths afterwards, so on Windows this raises
        # PermissionError [WinError 5] and a slow log write becomes a failed
        # tool call. The mutant adds the mistake; the guard must refuse it.
        "A7 the engine log writes are moved onto the atomic helper",
        "fantasy_agent/mcp_bridge.py",
        b'        path.write_text(text, encoding="utf-8")\n',
        (
            b"        from fantasy_agent.atomic_write import write_atomic\n"
            b"        write_atomic(path, text)\n"
        ),
        "tests/test_mcp_bridge.py::test_bridges_keep_their_log_writes_off_the_atomic_helper",
    ),
    (
        # The read endpoint stops rebuilding a session from its snapshot. The
        # mutant leaves the syntax valid and the endpoint answering, so what
        # goes red is the assertion that five fields came back -- not an
        # exception.
        #
        # The needle carries the `if session is None:` guard above the call
        # because the call alone is no longer unique: the decision endpoint
        # answers a restarted Studio the same way, at the same indent, and a
        # one-line needle there would match twice -- the harness would refuse
        # to guess which one it mutated. The guard is what tells them apart:
        # only the read endpoint calls restore with no comment between the
        # check and the call.
        "B1 the board read stops rebuilding the session",
        "apps/studio/app/main.py",
        (
            b"\n    if session is None:\n"
            b"        session = _restore_orchestration(session_id, engine)\n"
        ),
        (
            b"\n    if session is None:\n"
            b"        session = None  # mutation: no snapshot on the read path\n"
        ),
        "tests/test_studio_app.py::test_a_restored_board_shows_the_five_fields_that_used_to_vanish",
    ),
    (
        # Restore stops redeeming stored approvals through `confirm()`. This is
        # the AGENTS.md gate: the assignment installs whatever the file names.
        # `test_restore_rejects_a_confirmation_for_an_unknown_stage` is the
        # guard that fails, because only the validating path raises.
        "B2 a restored approval skips the confirmation gate",
        "fantasy_agent/orchestrator.py",
        b"        self.confirm(snapshot.confirmed)\n",
        b"        self._confirmed = set(snapshot.confirmed)  # mutation: no gate\n",
        "tests/test_orchestrator.py::test_restore_rejects_a_confirmation_for_an_unknown_stage",
    ),
    (
        # The run endpoint stops restoring. Subtle on purpose: it still works,
        # it just starts every pass from an empty outcome map, which is the
        # "confirm stage 5 replays stages 1-4" waste.
        #
        # The guard is NOT the status comparison in
        # `test_both_orchestration_endpoints_adopt_a_snapshot_the_same_way`.
        # That one was measured surviving this mutant: with no provider
        # configured a pass from empty lands on the same all-failed statuses as
        # a restored one, so the two worlds are indistinguishable from outside.
        # The guard here posts `confirm_stages=[]` after an approval and demands
        # the approval still be redeemed -- something only a restore can do.
        "B3 the run endpoint stops restoring the session",
        "apps/studio/app/main.py",
        b"            session = _restore_orchestration(session_id, engine)\n",
        b"            session = None  # mutation: every pass starts empty\n",
        "tests/test_studio_app.py::test_an_approval_survives_a_restart_all_the_way_into_the_next_pass",
    ),
    (
        # One field short of the dataclass it mirrors. The restored board shows
        # an empty answer and every test that checks "something came back"
        # still passes -- which is why the field-set guard names the dataclass
        # rather than counting fields.
        "B4 the snapshot drops a field the outcome carries",
        "fantasy_agent/orchestration_state.py",
        b'    answer: str = ""\n',
        b"    # mutation: answer dropped from the mirror\n",
        "tests/test_orchestration_state.py::test_the_snapshot_carries_exactly_the_outcome_fields",
    ),
    (
        # The plan narrowing is removed, so an approval for a stage this route
        # does not contain survives into a session about a different plan.
        "B5 a restored approval is kept for a stage the plan lacks",
        "fantasy_agent/orchestrator.py",
        b"        self._confirmed &= in_plan\n",
        b"        # mutation: no narrowing to the restored plan\n",
        "tests/test_orchestrator.py::test_restore_drops_a_confirmation_the_restored_plan_does_not_have",
    ),
    (
        # G-01, the human gate. Before it a ``kind="human"`` stage could only
        # ever answer ``awaiting_human``: nothing assigned ``done`` to one and
        # nothing on the REST surface could write the decision that would
        # unblock the three stages behind ``creative_review``. The cases below
        # pin the pieces that took the deadlock apart, in the order a revert
        # would take them apart again.
        #
        # HG1/HG2 share a needle on purpose. The lookup line alone is not
        # unique -- ``_stamp_plan`` has the same statement at the same indent --
        # so both carry the ``if decision is None:`` that only ``_advance``
        # has. Counting that as one anchor is what keeps a rename of either
        # method from silently matching the other's mutation.
        #
        # HG1 -- the deadlock itself, as a revert rather than a deletion: the
        # branch stops consulting the decision map, so a gate somebody decided
        # answers ``awaiting_human`` again and everything behind it stays
        # blocked. The guard is the acceptance test for the task, because a
        # "the gate is still waiting" assertion somewhere else would also pass
        # on a session where the dependent never ran at all.
        "HG1 the gate asks again after a decision",
        "fantasy_agent/orchestrator.py",
        (
            b"            decision = self._human_decisions.get(stage.id)\n"
            b"            if decision is None:\n"
        ),
        (
            b"            decision = None  # mutation: the map is never consulted\n"
            b"            if decision is None:\n"
        ),
        "tests/test_orchestrator_human_gate.py::test_a_resolved_human_stage_reaches_done_and_unblocks_dependents",
    ),
    (
        # HG2 -- the plan's ``human_resolution`` field opens the gate. This is
        # the AGENTS.md line one field over from ``confirmed``: a plan is
        # posted by the browser, and a browser that writes the decision into
        # the plan it posts has manufactured an approval nobody gave. The
        # stamp is what the snapshot carries; the runtime map is what decides.
        # The mutant reads the field first, which is the plausible refactor --
        # "the decision is right there on the stage" -- and the guard is the
        # one that posts a plan with the field already filled.
        # HG2 -- the decision is not stamped at the moment it is given. This
        # slot used to guard "the live pass reads the map, not the field", and
        # that mutation is now *unobservable*: HG10's reconcile makes the field
        # a pure function of the map, so an `_advance` that read the field
        # would behave identically to one that reads the map. Retired rather
        # than left running green for a reason that no longer holds -- a guard
        # that cannot go red is worse than no guard, because it reads as proof.
        # What replaces it is the other half of the same property: the stamp
        # has to exist at decide time, because the endpoint saves a snapshot
        # immediately after the click, and a board rebuilt from disk is the
        # path that most needs it.
        "HG2 the decision is not stamped when it is given",
        "fantasy_agent/orchestrator.py",
        (
            b"        self._human_decisions[stage_id] = decision\n"
            b"        self._stamp_plan()\n"
        ),
        (
            b"        self._human_decisions[stage_id] = decision\n"
            b"        pass  # mutation: the stamp waits for the next pass\n"
        ),
        "tests/test_orchestrator_human_gate.py::test_a_decision_given_on_a_restored_board_survives_the_next_restart",
    ),
    (
        # HG3 -- the two-way branch collapses into "a decision was given", so a
        # ``rejected`` gate opens like an approved one. Refusing a review has
        # to have consequences: without them a rework hint is the only thing
        # between a sent-back gate and production. ``if decision:`` is the
        # shape this takes, because every vocabulary word is a non-empty
        # string and the distinction lives only in the comparison.
        "HG3 a refused gate opens like an approved one",
        "fantasy_agent/orchestrator.py",
        b'            if decision == "approved":\n',
        b"            if decision:\n",
        "tests/test_orchestrator_human_gate.py::test_a_rejected_gate_fails_and_what_depends_on_it_stays_blocked",
    ),
    (
        # HG4 -- the decision record stops being written, and the stage still
        # reads ``done``. That is the artifact-honesty shape G-03 spent on the
        # playtest report, one field over: the stage's ``artifacts`` name this
        # file, so a board showing ``done`` next to a file nobody wrote is
        # lying about what exists. Deleting the call rather than moving it is
        # the realistic edit -- the write lives in the orchestrator because a
        # gate runs no tools, and "the stage's own tool list will handle it"
        # is how it goes missing.
        "HG4 the record stops being written",
        "fantasy_agent/orchestrator.py",
        b"            self._record_decision(stage, decision)\n",
        b"",
        "tests/test_orchestrator_human_gate.py::test_the_decision_record_is_written_before_the_stage_counts_as_done",
    ),
    (
        # HG5 -- the vocabulary check is dropped, so ``"maybe"`` is stored as a
        # decision. A stored typo leaves the gate waiting forever with nothing
        # to show for the click, which is the same failure ``confirm`` raises
        # for instead. ``if False:`` rather than deleting the block: the raise
        # stays in the file where a reader can see it was meant to run.
        "HG5 a decision outside the vocabulary is stored",
        "fantasy_agent/orchestrator.py",
        b"        if decision not in HUMAN_DECISIONS:\n",
        b"        if False:  # mutation: any string is a decision\n",
        "tests/test_orchestrator_human_gate.py::test_a_decision_outside_the_vocabulary_is_a_loud_error",
    ),
    (
        # HG6 -- restore stops redeeming the decisions the snapshot carries, so
        # a restart asks the operator to decide again. The stamps are read off
        # the plan the snapshot carries rather than off the browser's copy,
        # which is what makes redeeming them not the same thing as trusting a
        # posted field (HG2). Same property as B2 for ``confirmed``, one map
        # over, and the same reason the guard is the round-trip rather than a
        # "the map is empty" assertion.
        "HG6 a restart asks for the decision again",
        "fantasy_agent/orchestrator.py",
        b"            self.resolve_human_stage(stage.id, stage.human_resolution)\n",
        b"",
        "tests/test_orchestrator_human_gate.py::test_restoring_redeems_a_decision_the_operator_actually_gave",
    ),
    (
        # HG9 -- the board's pending list stops shrinking. A gate somebody
        # decided keeps its row in "waiting for you", which is the summary line
        # that sends the operator back to a card that no longer needs them.
        # Dropping the second condition is the edit: the kind filter alone
        # still lists every human stage, decided or not.
        "HG9 the pending list stops shrinking",
        "fantasy_agent/orchestrator.py",
        (
            b"            if stage.kind == HUMAN_STAGE_KIND\n"
            b"            and stage.id not in self._human_decisions\n"
        ),
        b"            if stage.kind == HUMAN_STAGE_KIND\n",
        "tests/test_orchestrator_human_gate.py::test_pending_human_gates_lists_only_gates_nobody_has_decided",
    ),
    (
        # HG7 -- the endpoint takes a decision for a stage that is not a gate.
        # Accepting one for an agent stage reads as "the operator settled this"
        # on a card a decision cannot move -- the dead-end control the endpoint
        # exists to replace, wearing the opposite hat. The cards stay attached
        # either way, so what goes red is the refusal, not the payload shape.
        "HG7 a stage that is not a gate takes a decision",
        "apps/studio/app/main.py",
        b"    if stage.kind != HUMAN_STAGE_KIND:\n",
        b"    if False:  # mutation: any stage takes a decision\n",
        "tests/test_studio_app.py::test_a_decision_for_a_stage_that_is_not_a_gate_is_reported",
    ),
    (
        # HG8 -- the endpoint stops persisting the decision, so it lives only
        # until the process does. A restart between the click and the next pass
        # would ask the operator to decide again -- an approval that never
        # takes effect, one verb over from the one AGENTS.md names. The guard
        # drops the registry the way a Studio restart does and reads the board
        # back, which only the snapshot can answer.
        "HG8 the endpoint stops persisting the decision",
        "apps/studio/app/main.py",
        (
            b"        save_state(\n"
            b'            session["orchestrator"].snapshot(plan), workspace_root=REPO_ROOT\n'
            b"        )\n"
        ),
        b"        pass  # mutation: the decision lives only in memory\n",
        "tests/test_studio_app.py::test_the_decision_endpoint_resolves_a_gate_and_survives_a_restart",
    ),
    (
        # HG10 -- a forged stamp laundered through the snapshot. This is the
        # half of "a plan that arrives with the field filled does not open a
        # gate" that a live pass cannot show: `_advance` reads the map, so the
        # forgery is inert until a restart, and `restore` redeems whatever the
        # plan dump carries. Measured on the first cut -- a posted
        # `human_resolution: "approved"` rode into the dump and the gate came
        # back `done` with no decision anywhere. The fix is reconciliation
        # rather than overlay: the dump is a pure function of the map, which is
        # what the restore docstring's "backend-written state" claim needs.
        # Same reason `snapshot` writes `confirmed` from the set instead of
        # reading it off the plan.
        "HG10 a forged stamp is laundered through the snapshot",
        "fantasy_agent/orchestrator.py",
        (
            b"            stage.human_resolution = self._human_decisions.get(stage.id)\n"
        ),
        (
            b"            decision = self._human_decisions.get(stage.id)\n"
            b"            if decision is not None:\n"
            b"                stage.human_resolution = decision\n"
        ),
        "tests/test_orchestrator_human_gate.py::test_a_forged_field_does_not_survive_the_snapshot_either",
    ),
    (
        # HG11 -- the restored board loses the next click. A restarted Studio
        # rebuilds the session from the snapshot and renders a board from it,
        # so the operator's click lands on an instance holding no plan, and
        # `resolve_human_stage` has nothing to stamp. The endpoint's explicit
        # save then persists a dump that predates the click. Measured: a second
        # restart asked the operator to decide again, on the exact path the
        # save exists to protect. Adopting the snapshot's plan fills the window
        # without touching the map's authority.
        "HG11 a decision on a restored board is lost",
        "fantasy_agent/orchestrator.py",
        (
            b"        self._plan = plan\n"
            b"        for entry in snapshot.stages:\n"
        ),
        (
            b"        pass  # mutation: the plan is not adopted\n"
            b"        for entry in snapshot.stages:\n"
        ),
        "tests/test_orchestrator_human_gate.py::test_a_decision_given_on_a_restored_board_survives_the_next_restart",
    ),
    (
        # HG12 -- a rewound gate does not ask again. `rewind_from` drops the
        # outcome and the confirmation so a reworked stage runs what was
        # approved rather than what was; a decision is the same shape of state
        # and was left out. Measured: the earlier refusal replayed as `failed`
        # on the very next pass with no question asked, and because a decided
        # gate is absent from `pending_human_gates` the board had no button
        # either -- unreachable from the UI, unresettable from the API.
        "HG12 a rewound gate does not ask again",
        "fantasy_agent/orchestrator.py",
        b"            self._human_decisions.pop(name, None)\n",
        b"            pass  # mutation: the decision survives the rewind\n",
        "tests/test_orchestrator_human_gate.py::test_rewinding_a_decided_gate_asks_again",
    ),
    (
        # HG13 -- restore redeems a stamp on a stage that is not a gate. Three
        # layers answer "may this stage be decided": the endpoint refuses, the
        # pass only looks at human stages, and restore took whatever the dump
        # carried. A plan hand-edited to stamp an agent stage therefore had a
        # decision installed for it that no live path could ever read -- inert
        # today, and the shape that makes the next reader wrong.
        "HG13 restore redeems a stamp on a stage that is not a gate",
        "fantasy_agent/orchestrator.py",
        (
            b"            if stage.kind != HUMAN_STAGE_KIND:\n"
            b"                continue\n"
        ),
        (
            b"            if False:  # mutation: any kind of stage is redeemed\n"
            b"                continue\n"
        ),
        "tests/test_orchestrator_human_gate.py::test_restore_redeems_only_gate_stamps",
    ),
    (
        # The name rule loses its trailing-dot clause. `victim.` and `victim`
        # are one directory on Windows, so a snapshot written under the aliased
        # id lands on another session's directory -- overwriting the approvals
        # stored there. Containment cannot see it: `resolve_workspace_path`
        # resolves the path fine and reports success.
        "K1 a session id may end with a dot again",
        "fantasy_agent/path_safety.py",
        (
            b'_SAFE_SEGMENT = re.compile(r"\\A[A-Za-z0-9][A-Za-z0-9._-]{0,62}'
            b'[A-Za-z0-9_-]\\Z|\\A[A-Za-z0-9]\\Z")'
        ),
        (
            b'_SAFE_SEGMENT = re.compile(r"\\A[A-Za-z0-9][A-Za-z0-9._-]{0,63}\\Z")'
            b'  # mutation: trailing dot allowed again'
        ),
        "tests/test_orchestration_state.py::test_a_session_id_that_the_filesystem_would_rewrite_is_refused",
    ),
    (
        # The engine key stops being checked as a name. It reaches the same path
        # template and the GET endpoint takes it as a query parameter, so it is
        # caller-controlled today -- and the prefix rule alone lets
        # `engine=godot/../unreal` out of the sandbox.
        "K2 the engine key is no longer checked as a name",
        "fantasy_agent/orchestration_state.py",
        b'    assert_safe_path_segment(engine_key, label="engine_key")\n',
        b"    # mutation: engine_key unchecked\n",
        "tests/test_orchestration_state.py::test_the_engine_key_is_checked_as_a_name_too",
    ),
    (
        # A cold session starts logging again. The rule is the whole value of
        # the degradation warnings: one line on every first run, and the real
        # one -- a file that exists and cannot be used -- is the line nobody
        # reads any more.
        "K3 a session that never ran reports a fault again",
        "fantasy_agent/pipeline_state.py",
        (
            b"    except FileNotFoundError:\n"
            b"        # A session that has not run yet, not a fault: reporting it would put\n"
            b"        # a warning in the log of every first run and bury the one that matters.\n"
            b"        return None\n"
        ),
        (
            b"    except FileNotFoundError as exc:\n"
            b"        logger.warning("
            b'"pipeline state at %r is missing: %s", path, exc)  # mutation: cold start warns\n'
            b"        return None\n"
        ),
        "tests/test_pipeline_state.py::test_a_cold_session_does_not_claim_to_have_degraded",
    ),
    (
        # The read handler narrows back to OSError, letting a non-UTF-8 file
        # through as `UnicodeDecodeError`. That is the regression this handler
        # split introduced: one `except (OSError, ValueError)` around
        # read-and-parse caught it for free, and `executor.resume_stages` calls
        # `load_state` with no handler at all.
        "K4 a state file that is not text crashes the resume",
        "fantasy_agent/pipeline_state.py",
        b"    except (OSError, ValueError) as exc:\n",
        b"    except OSError as exc:  # mutation: UnicodeDecodeError escapes\n",
        "tests/test_pipeline_state.py::test_a_state_file_that_is_not_text_degrades_instead_of_raising",
    ),
    (
        # Same narrowing in the credentials file, where the consequence is a
        # Studio panel that says "not configured" instead of a failed read --
        # and, before the split, a live decode error escaping to the caller.
        "K5 a credentials file that is not text crashes the panel",
        "fantasy_agent/api_settings.py",
        b"    except (OSError, ValueError) as exc:\n",
        b"    except OSError as exc:  # mutation: UnicodeDecodeError escapes\n",
        "tests/test_api_settings.py::test_a_settings_file_that_is_not_text_degrades_instead_of_raising",
    ),
    # ── exit checks: the vacuous gate, closed from both ends ──────────────────
    #
    # X1/X2 are the same guard seen twice on purpose. A single "every stage
    # declares checks" case would be satisfied by the one stage nobody edited;
    # mutating two different stages' entries proves the guard walks the table
    # rather than spot-checking a row it happens to know.
    (
        "X1 a stage is added with no exit check",
        "fantasy_agent/workflows.py",
        b'            exit_checks=["verify_gameplay_spec"],\n',
        b"",
        "tests/test_pipeline_contract.py::test_every_agent_stage_on_the_godot_route_declares_exit_checks",
    ),
    (
        "X2 the Godot stage loses its project check",
        "fantasy_agent/workflows.py",
        b'            exit_checks=["validate_godot_project"],\n',
        b"",
        "tests/test_pipeline_contract.py::test_every_agent_stage_on_the_godot_route_declares_exit_checks",
    ),
    (
        # The check reverts to needing a path from a caller, which is the state
        # the code was in before: an exit check is called with no arguments, so
        # this turns the Godot chain's only machine check into one that can
        # never run.
        "X3 the project check stops finding its own project",
        "fantasy_agent/godot_mcp.py",
        (
            b'                f"{_default_project_dir(request.plan)}/project.godot"\n'
            b"                if request.plan is not None\n"
            b'                else ""\n'
        ),
        b'                ""\n',
        "tests/test_exit_checks_wired.py::test_a_generated_project_passes_the_godot_check",
    ),
    (
        # The realistic mistake, not a deleted guard: count the loop steps
        # instead of the distinct decisions. ``GameplaySpec`` already enforces
        # ``min_length=3``, so the mutated rule is satisfied by construction and
        # the check passes a loop with one decision written three times.
        "X4 the spec check counts steps instead of decisions",
        "fantasy_agent/plan_checks.py",
        b"    if len(distinct) < MIN_TESTABLE_DECISIONS:\n",
        b"    if len(spec.core_loop) < MIN_TESTABLE_DECISIONS:\n",
        "tests/test_exit_checks_wired.py::test_the_gameplay_spec_check_fails_a_spec_nobody_could_test",
    ),
    (
        # A check that reports a problem without naming it sends the rework to
        # the wrong node, and the stage detail is where the reason lands.
        "X5 a failed validation stops saying what is wrong",
        "fantasy_agent/godot_mcp.py",
        b'            return f"Godot MCP found project validation issues: {issues}{suffix}"\n',
        b'            return "Godot MCP found project validation issues."\n',
        "tests/test_exit_checks_wired.py::test_a_broken_project_fails_the_godot_check_with_the_reason",
    ),
    (
        # The Unreal hole is enumerated so it cannot grow silently. The realistic
        # mistake is "fixing" the asymmetry by giving the Unreal route the same
        # check -- which would validate a *Godot* project on a Unreal run, since
        # the artifact store carries both sub-plans.
        "X6 an Unreal stage gains a check nobody can run",
        "fantasy_agent/workflows.py",
        b'            exit_checks=(["validate_godot_project"] if primary_is_godot else []),\n',
        b'            exit_checks=["validate_godot_project"],\n',
        "tests/test_pipeline_contract.py::test_the_unreal_route_stages_without_a_check_are_the_named_ones",
    ),
    (
        "PK1 the bundle loses the frontend it ships",
        "scripts/package_desktop.py",
        # The existence half of the guard skips build outputs, so this line is
        # caught by the split-honesty assertion and the explicit name check --
        # which is the pair that replaced "dist must exist on disk".
        b'    "apps/frontend/dist",\n',
        b"",
        "tests/test_packaging.py::test_every_payload_entry_exists",
    ),
)


#: Cases whose guard launches a local engine, mapped to the engine it needs.
#:
#: Where that engine is absent the guard skips itself (``pytest.mark.skipif``),
#: and a skip proves nothing either way -- so the case is reported as *not
#: applicable* rather than as a failure. Most of the cases below execute a real
#: Godot, which is why a machine without one cannot run them: pinning them as
#: failures would make this harness unrunnable on any CI runner. That is a real
#: hole in what CI proves, so the run prints the list rather than a count --
#: counting it here is how this comment came to claim two cases when seven had
#: needed an engine for a while.
#:
#: Keyed by label because the case tuple stays the shape it always was, and a
#: label is the only stable name a reader has. ``tests/test_mutation_harness.py``
#: checks every key still matches a case, so a renamed label cannot silently
#: excuse a case instead of running it.
ENGINE_REQUIREMENTS: dict[str, str] = {
    "G2 same, caught by real Godot": "godot",
    "G3 the guard only looks on PATH": "godot",
    "D3 the same, caught by a real playtest": "godot",
    "D5 the same, caught by a real playtest": "godot",
    "D8 the same gap, caught by a real playtest": "godot",
    "D11 the dash stops moving the player": "godot",
    "D13 the patrol walks across the route again": "godot",
    "D14 the enemies pile back onto the exit tile": "godot",
    "D15 two enemies share a spawn point again": "godot",
}

#: counts line of scripts/run_tests.py: `tests=1 passed=0 failed=1 errors=0 skipped=0`
_SUMMARY = re.compile(r"tests=(\d+) passed=(\d+) failed=(\d+) errors=(\d+) skipped=(\d+)")

#: How each outcome is printed. "unproven" outcomes are listed separately in
#: the summary so a reader can never mistake them for proof.
OUTCOMES: dict[str, str] = {
    "caught": "RED (caught)",
    "missed": "GREEN (MISSED!)",
    "skipped": "SKIPPED (unproven)",
    "no-run": "NO RUN (unproven)",
}


class Verdict(NamedTuple):
    """What one guard run actually proved."""

    outcome: str  # caught | missed | skipped | no-run
    detail: str


def _engine_probes() -> dict[str, Callable[[], str | None]]:
    """How to ask whether each engine is installed, by requirement name.

    Imported lazily: the harness has to keep running when the module under
    mutation is one of the bridges, and it would be self-defeating for the tool
    that reports a broken import to be the one that cannot start.
    """

    from fantasy_agent import local_tools

    return {
        "godot": local_tools._find_godot,
        "blender": local_tools._find_blender,
        "unreal": local_tools._find_unreal,
    }


def _engine_installed(engine: str) -> bool:
    """Whether the engine a case needs is on this machine."""

    probe = _engine_probes().get(engine)
    if probe is None:  # reported by main() before any case runs
        raise KeyError(f"no probe for engine {engine!r}")
    return probe() is not None


def _classify(status: int, summary: str) -> Verdict:
    """Read the verdict out of the runner's counts, not out of its exit code.

    See the module docstring: both a dead node id and a skipping guard produce
    an exit code that means the opposite of what it looks like.
    """

    match = _SUMMARY.search(summary)
    if match is None:
        return Verdict("no-run", f"no junit report was produced (runner exited {status})")

    tests, _passed, failed, errors, skipped = (int(value) for value in match.groups())
    if tests == 0:
        return Verdict("no-run", "the runner collected no test for this node id")
    if skipped == tests:
        return Verdict("skipped", "the guard skipped itself")
    if failed or errors:
        return Verdict("caught", summary)
    return Verdict("missed", summary)


def _as_eol(needle: bytes, eol: bytes) -> bytes:
    """Rewrite a probe's line endings to the ones the file on disk actually has.

    The working tree is not uniform -- ``.gitattributes`` stores LF in the index,
    so ``core.autocrlf`` hands most files back as CRLF while a file a tool wrote
    directly stays LF. A byte-exact needle then silently matches nothing, and the
    harness reports "not caught" for a guard that is in fact perfectly alive. The
    probes are written with ``\\n``; matching whatever the file uses is the point.
    """

    return needle.replace(b"\r\n", b"\n").replace(b"\n", eol)


def run(test: str) -> tuple[int, str]:
    """Run one guard through the real runner and report (exit code, its output).

    The output, not just the counts line, is returned: ``_classify`` searches it
    for the counts and treats their absence as "nothing ran", which is the one
    verdict an exit code cannot express.
    """

    # check=False: the guard is *supposed* to exit non-zero here. Letting the
    # call raise would abort the case with the mutated file still on disk.
    completed = subprocess.run(
        [sys.executable, "scripts/run_tests.py", test, "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout + completed.stderr


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prove each guard goes red when the behaviour it describes is removed."
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="SUBSTRING",
        help=(
            "run only the cases whose label contains SUBSTRING (repeatable, "
            "case-insensitive). For iterating on one guard -- a full run launches "
            "pytest once per case. A filtered run proves nothing about the cases it "
            "skipped, so the summary says how many it left out."
        ),
    )
    parser.add_argument("--list", action="store_true", help="print every case and exit")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    options = _parse_args(sys.argv[1:] if argv is None else argv)

    if options.list:
        for label, relative, _needle, _mutant, test in CASES:
            print(f"{label:44} {relative} :: {test}")
        return 0

    selected = [
        case
        for case in CASES
        if not options.only or any(token.casefold() in case[0].casefold() for token in options.only)
    ]
    if not selected:
        # Silently running nothing would exit 0 and read as "all proven".
        print(f"no case label matches {options.only}; try --list")
        return 1

    failures: list[str] = []
    not_applicable: list[str] = []
    caught = 0

    known = {case[0] for case in CASES}
    stale = sorted(set(ENGINE_REQUIREMENTS) - known)
    if stale:
        # A key here is how a case gets excused, so an orphan key means a case
        # was renamed and its guard silently stopped running.
        print(f"ENGINE_REQUIREMENTS names cases that no longer exist: {stale}")
        failures.extend(stale)

    unprobeable = sorted(set(ENGINE_REQUIREMENTS.values()) - set(_engine_probes()))
    if unprobeable:
        # A typo here would otherwise raise mid-run, with a mutated file still
        # on disk, instead of reporting anything at all.
        print(f"ENGINE_REQUIREMENTS names engines this harness cannot probe: {unprobeable}")
        failures.extend(unprobeable)

    for label, relative, needle, mutant, test in selected:
        engine = ENGINE_REQUIREMENTS.get(label)
        if engine and not _engine_installed(engine):
            print(f"{label:44} {'N/A':14} needs {engine}, which is not installed here")
            not_applicable.append(label)
            continue

        target = ROOT / relative
        original = target.read_bytes()
        eol = b"\r\n" if b"\r\n" in original else b"\n"
        needle, mutant = _as_eol(needle, eol), _as_eol(mutant, eol)

        if original.count(needle) != 1:
            print(f"{label:44} {'SKIP':14} needle appears {original.count(needle)}x in {relative}")
            # Said here because the reader's instinct is to edit the needle, and
            # for a file that was never edited the needle is not what is wrong.
            print(f"{'':45}0 matches is a rename, or the residue of a run killed mid-case;")
            print(f"{'':45}check `git diff {relative}` before touching the needle.")
            failures.append(label)
            continue

        try:
            target.write_bytes(original.replace(needle, mutant))
            verdict = _classify(*run(test))
            print(f"{label:44} {OUTCOMES[verdict.outcome]:24} {verdict.detail}")
            if verdict.outcome == "caught":
                caught += 1
            else:
                failures.append(label)
        finally:
            target.write_bytes(original)
            if target.read_bytes() != original:
                print(f"{label:44} RESTORE FAILED for {relative}")
                failures.append(label)

    print()
    if failures:
        print(f"UNPROVEN OR FAILED: {failures}")
        return 1

    proven = f"{caught}/{len(selected)} mutations caught"
    if len(selected) != len(CASES):
        proven += f" (--only: {len(CASES) - len(selected)} of {len(CASES)} cases not run)"
    excused = f"; not applicable here (no engine): {not_applicable}" if not_applicable else ""
    print(f"{proven}{excused}; every source restored byte-identically")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
