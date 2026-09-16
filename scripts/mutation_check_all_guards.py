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
        b"    return candidate if candidate.is_absolute() else workspace / candidate",
        b"    return candidate",
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
        (
            b'    target = {"status": "ready", "target": "http://127.0.0.1:8188",'
            b' "metadata": {}}\n'
        ),
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
            b"        payload = json.loads(manifest.read_text(encoding=\"utf-8-sig\"))\n"
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
        (
            b"        for argument in hidden:\n"
            b"            args.pop(argument, None)\n"
        ),
        (
            b"        for argument in hidden:\n"
            b"            pass  # mutation: the model's value is kept\n"
        ),
        "tests/test_agent_loop.py::test_a_hidden_argument_the_model_sent_is_discarded",
    ),
    (
        "D17 a spec's own words go into a GDScript literal unescaped",
        "fantasy_agent/gameplay_codegen.py",
        (
            b"    return \" \".join(text.split()).replace(\"\\\\\", \"\\\\\\\\\")"
            b".replace('\"', \"'\")\n"
        ),
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
        (
            b"    for index, stage in enumerate(stages, start=1):\n"
            b"        stage.order = index\n"
        ),
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
        if not options.only
        or any(token.casefold() in case[0].casefold() for token in options.only)
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
    excused = (
        f"; not applicable here (no engine): {not_applicable}" if not_applicable else ""
    )
    print(f"{proven}{excused}; every source restored byte-identically")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
