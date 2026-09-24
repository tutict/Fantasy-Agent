from __future__ import annotations

import importlib.util
import socket
import threading
import time
from pathlib import Path

import pytest
from pydantic import BaseModel

from fantasy_agent.contracts import PromptRequest


def _load_studio_app():
    module_path = Path("apps/studio/app/main.py").resolve()
    spec = importlib.util.spec_from_file_location("fantasy_agent_studio_app", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _materialize_review_artifacts(review, root: Path, *, target: str = 'unreal'):
    for item in review.items:
        artifact_path = Path(item.asset_path)
        if (
            target == 'godot'
            and item.source == 'blender'
            and artifact_path.suffix.casefold() == '.fbx'
        ):
            artifact_path = artifact_path.with_suffix('.glb')
        artifact_path = root / artifact_path
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(f'reviewed-{item.asset_id}'.encode())
    return review


def test_studio_serves_combined_desktop_panel():
    module = _load_studio_app()
    paths = {route.path for route in module.app.routes}

    assert module.health()["agent"] == "fantasy-agent-studio"
    assert module.health()["mode"] == "standalone"
    assert {
        "/",
        "/web-console",
        "/workbench",
        "/health",
        "/api/plan",
        "/api/tasks",
        "/api/design",
        "/api/gdd",
        "/api/pipeline",
        "/api/idea-seed",
        "/api/qa",
        "/api/tool-contracts",
        "/api/tool-catalog",
        "/api/unreal/plan",
        "/api/godot/plan",
        "/api/blender/plan",
        "/api/comfyui/plan",
        "/api/creative-review",
        "/api/tool-status",
        "/api/manual-correction/targets",
        "/api/manual-correction/open",
        "/api/tools/{tool_name}",
    } <= paths
    # The standalone workbench must not expose an inbound MCP endpoint.
    assert "/mcp" not in paths
    assert "/debug/tool/{tool_name}" not in paths
    # The hand-written pages are gone -- not just superseded, deleted -- and so
    # are the mounts that used to serve them. Leaving either in place is how a
    # second UI survives a migration: the server keeps answering 200 with a page
    # nobody maintains, and the two views drift without anyone noticing.
    assert not module.APP_DIR.joinpath("static").exists()
    assert "/studio-static" not in paths
    assert "/assets" not in paths
    assert module.REPO_ROOT.joinpath("apps/frontend/src/workbench/PlanningWorkbench.tsx").exists()
    assert module.REPO_ROOT.joinpath("apps/frontend/src/console/FlowConsole.tsx").exists()
    status = module.mcp_status()
    assert status["engine_kind"] == "unreal"
    assert status["required_total"] >= 3
    assert 0 <= status["required_ready"] <= status["required_total"]
    services = {service["id"]: service for service in status["services"]}
    service_ids = set(services)
    assert {"comfyui", "blender", "unreal", "godot", "github"} <= service_ids
    assert "studio-mcp" not in service_ids
    for service in services.values():
        assert service["detail_key"].startswith("mcp")
        assert service["next_action_key"].startswith("mcp")
        assert isinstance(service["detail_args"], dict)
        assert isinstance(service["next_action_args"], dict)
    assert services["unreal"]["required"] is True
    assert services["godot"]["required"] is False
    godot_status = module.mcp_status(engine="Godot 4")
    godot_services = {service["id"]: service for service in godot_status["services"]}
    assert godot_status["engine_kind"] == "godot"
    assert godot_services["unreal"]["required"] is False
    assert godot_services["godot"]["required"] is True
    correction_targets = module.correction_targets(engine="Godot 4")
    assert correction_targets["engine_kind"] == "godot"
    assert "godot" in {target["id"] for target in correction_targets["targets"]}
    blocked = module.correction_open(
        module.ManualCorrectionOpenRequest(target_id="godot", confirmed_side_effects=False)
    )
    assert blocked["status"] == "blocked"


def test_studio_detects_downloaded_godot_install(monkeypatch, tmp_path):
    """The panel reports whatever the shared resolver returns.

    The downloaded-install search this used to run locally still exists -- in
    ``local_tools``, where the executor reads it too. Stubbing the resolver is
    what proves the panel has no second copy: this module no longer knows the
    Downloads glob at all, so the only way it can find Godot is by asking.
    """

    module = _load_studio_app()
    godot = tmp_path / "Godot_v4.6.3-stable_win64" / "Godot_v4.6.3-stable_win64_console.exe"
    godot.parent.mkdir(parents=True)
    godot.write_text("", encoding="utf-8")

    monkeypatch.setattr(module.local_tools, "_find_godot", lambda: str(godot))

    status = module.mcp_status(engine="Godot 4.6")
    services = {service["id"]: service for service in status["services"]}

    assert services["godot"]["status"] == "ready"
    assert services["godot"]["target"] == str(godot)


def test_the_unreal_panel_reports_the_binary_a_run_would_launch(monkeypatch, tmp_path):
    """A "ready" panel has to name the process the executor actually starts.

    ``local_tools._find_unreal`` returns ``UnrealEditor.exe``, but headless
    commandlets run through the sibling ``-Cmd`` build. Reporting the editor
    would let the panel agree with the disk and disagree with the run -- the
    same failure mode, one level down.
    """

    module = _load_studio_app()
    win64 = tmp_path / "Engine" / "Binaries" / "Win64"
    win64.mkdir(parents=True)
    (win64 / "UnrealEditor.exe").write_text("", encoding="utf-8")
    (win64 / "UnrealEditor-Cmd.exe").write_text("", encoding="utf-8")

    monkeypatch.setattr(
        module.local_tools, "_find_unreal", lambda: (win64 / "UnrealEditor.exe").as_posix()
    )

    status = module.mcp_status("UE5")
    unreal = next(service for service in status["services"] if service["id"] == "unreal")

    assert unreal["status"] == "ready"
    # The panel reports the path the way the shared resolver spells it: the
    # sibling lookup goes through pathlib, which normalises to backslashes here.
    assert unreal["target"] == str(win64 / "UnrealEditor-Cmd.exe")


def test_a_missing_engine_is_reported_unavailable(monkeypatch):
    """The "no engine" branch has to stay reachable and actionable.

    Plumbed straight through to a resolver, the ready branch is the easy one;
    a machine with nothing installed is where the panel earns its keep, so the
    status, the required-ness and the recovery hint are all pinned.
    """

    module = _load_studio_app()
    for resolver in ("_find_unreal", "_find_blender", "_find_godot"):
        monkeypatch.setattr(module.local_tools, resolver, lambda: None)

    status = module.mcp_status("UE5")
    services = {service["id"]: service for service in status["services"]}

    assert services["unreal"]["status"] == "unavailable"
    assert services["unreal"]["required"] is True
    assert services["unreal"]["next_action_key"] == "mcpNextUnrealMissing"
    assert services["blender"]["status"] == "unavailable"
    assert status["status"] == "degraded"
    assert status["required_ready"] < status["required_total"]


def test_the_comfyui_panel_asks_the_shared_resolver_instead_of_probing_again(monkeypatch):
    """ComfyUI was the last target the panel probed a second time.

    The panel built its own candidate list from ``COMFYUI_URL`` /
    ``COMFYUI_ENDPOINT`` and skipped the local-only check
    ``local_tools._comfyui_target`` applies, so pointed at a remote endpoint
    it reported ``ready`` while every run refused the same endpoint -- the
    drift ``_probe_executable`` takes a resolver to prevent.

    Stubbing the resolver is what makes this load-bearing: a panel that probes
    on its own never reads the stub, so both verdicts below go red.
    """

    module = _load_studio_app()

    monkeypatch.setattr(
        module.local_tools,
        "_comfyui_target",
        lambda: {
            "id": "comfyui",
            "status": "ready",
            "target": "http://127.0.0.1:9999",
            "openable": True,
            "detail_key": "manualComfyReady",
            "metadata": {"version": "9.9.9"},
        },
    )
    services = {s["id"]: s for s in module.mcp_status("UE5")["services"]}

    assert services["comfyui"]["status"] == "ready"
    assert services["comfyui"]["target"] == "http://127.0.0.1:9999"
    assert services["comfyui"]["metadata"]["version"] == "9.9.9"
    assert services["comfyui"]["detail_args"] == {"version": "9.9.9"}

    monkeypatch.setattr(
        module.local_tools,
        "_comfyui_target",
        lambda: {
            "id": "comfyui",
            "status": "ready",
            "target": "http://127.0.0.1:9999",
            "openable": True,
            "detail_key": "manualComfyReady",
            "metadata": {},
        },
    )
    services = {s["id"]: s for s in module.mcp_status("UE5")["services"]}

    assert services["comfyui"]["status"] == "ready"
    assert services["comfyui"]["metadata"]["version"] == "reachable"

    monkeypatch.setattr(
        module.local_tools,
        "_comfyui_target",
        lambda: {
            "id": "comfyui",
            "status": "degraded",
            "target": "http://127.0.0.1:8188",
            "openable": True,
            "detail_key": "manualComfyMissing",
            "metadata": {"failures": ["http://127.0.0.1:8188: timed out"]},
        },
    )
    services = {s["id"]: s for s in module.mcp_status("UE5")["services"]}

    assert services["comfyui"]["status"] == "unavailable"
    assert services["comfyui"]["next_action_key"] == "mcpNextComfyMissing"
    assert services["comfyui"]["metadata"]["failures"] == ["http://127.0.0.1:8188: timed out"]


def test_a_remote_comfyui_endpoint_is_never_probed_by_the_panel(monkeypatch):
    """A non-local ``COMFYUI_ENDPOINT`` must not reach the panel's sockets.

    Runs refuse remote endpoints unless ``allow_remote_endpoint`` is set, so a
    panel that probes one advertises a service no run will use -- and makes an
    outbound request the design gates behind that flag. Recording what the
    shared resolver actually dials pins both halves: the panel consulted the
    resolver at all, and the only hosts it touched were local ones.
    """

    module = _load_studio_app()
    monkeypatch.setenv("COMFYUI_ENDPOINT", "http://comfyui.remote.invalid:8188")

    seen: list[str] = []

    def recording_http_json(url, timeout=0.45):
        seen.append(url)
        raise OSError("offline for the test")

    monkeypatch.setattr(module.local_tools, "_http_json", recording_http_json)

    services = {s["id"]: s for s in module.mcp_status("UE5")["services"]}
    comfyui = services["comfyui"]

    assert seen, "the panel never asked the shared resolver to find ComfyUI"
    for url in seen:
        assert "remote.invalid" not in url, url
        assert "127.0.0.1" in url or "localhost" in url, url
    assert comfyui["status"] == "unavailable"
    assert all(
        "remote.invalid" not in failure for failure in comfyui["metadata"]["failures"]
    ), comfyui["metadata"]["failures"]


def test_the_comfyui_panel_opens_no_socket_of_its_own(monkeypatch):
    """Consulting the resolver is not the same as consulting it *only*.

    The guard above proves the panel asks the shared resolver; it would still
    pass if the panel asked and then also dialled the endpoint itself, since
    the resolver's answer is what gets reported either way. Recording
    ``socket.create_connection`` closes that half: a panel that opens its own
    connection is caught even if it swallows the resulting error.
    """

    module = _load_studio_app()
    opened: list[tuple] = []

    def record(*args, **kwargs):
        opened.append(args[:2])
        raise OSError("offline for the test")

    monkeypatch.setattr(socket, "create_connection", record)
    monkeypatch.setattr(
        module.local_tools,
        "_comfyui_target",
        lambda: {
            "id": "comfyui",
            "status": "degraded",
            "target": "http://127.0.0.1:8188",
            "openable": True,
            "detail_key": "manualComfyMissing",
            "metadata": {"failures": []},
        },
    )

    item = module._probe_comfyui()

    assert item["status"] == "unavailable"
    assert opened == [], f"the panel opened its own connection(s): {opened}"


def test_the_comfyui_probe_queries_candidates_at_the_same_time(monkeypatch):
    """A stalled endpoint must not cost one timeout per candidate.

    Probing one candidate at a time means several stalled endpoints cost
    several timeouts before the panel can say anything at all. A rendezvous
    makes that structural rather than a timing assertion: every stub call
    waits for all the others to arrive before it returns, so a serial
    implementation trips the barrier's own timeout on any machine, fast or
    slow, instead of passing by being quick enough.
    """

    module = _load_studio_app()
    monkeypatch.delenv("COMFYUI_URL", raising=False)
    monkeypatch.delenv("COMFYUI_ENDPOINT", raising=False)
    candidates = [f"http://127.0.0.1:{port}" for port in (29401, 29402, 29403, 29404)]
    monkeypatch.setattr(
        module.local_tools,
        "default_comfyui_endpoint_candidates",
        lambda: list(candidates),
    )

    rendezvous = threading.Barrier(len(candidates), timeout=5)

    def stalled(url, timeout=0.45):
        rendezvous.wait()
        raise OSError("offline for the test")

    monkeypatch.setattr(module.local_tools, "_http_json", stalled)

    item = module._probe_comfyui()

    assert item["status"] == "unavailable"


def test_the_comfyui_probe_still_prefers_a_configured_endpoint(monkeypatch):
    """Concurrency must not turn "first candidate wins" into "first reply wins".

    The configured endpoint answers last here, so an implementation that
    took whichever future completed first would report a default endpoint
    instead.
    """

    module = _load_studio_app()
    monkeypatch.setenv("COMFYUI_URL", "http://127.0.0.1:29411")
    monkeypatch.delenv("COMFYUI_ENDPOINT", raising=False)
    monkeypatch.setattr(
        module.local_tools,
        "default_comfyui_endpoint_candidates",
        lambda: ["http://127.0.0.1:29412", "http://127.0.0.1:29413"],
    )

    def answer(url, timeout=0.45):
        if "29411" in url:
            time.sleep(0.05)
        return {"system": {"comfyui_version": "0.34.0"}}

    monkeypatch.setattr(module.local_tools, "_http_json", answer)

    item = module._probe_comfyui()

    assert item["status"] == "ready"
    assert item["target"] == "http://127.0.0.1:29411"


def test_studio_shell_includes_bilingual_ui_controls():
    module = _load_studio_app()
    frontend_source = module.REPO_ROOT.joinpath("apps/frontend/src/studio/StudioShell.tsx").read_text(encoding="utf-8")
    frontend_i18n = module.REPO_ROOT.joinpath("apps/frontend/src/shared/i18n.ts").read_text(encoding="utf-8")
    locale_theme_source = module.REPO_ROOT.joinpath("apps/frontend/src/shared/localeTheme.tsx").read_text(
        encoding="utf-8"
    )
    workbench_source = module.REPO_ROOT.joinpath(
        "apps/frontend/src/workbench/PlanningWorkbench.tsx"
    ).read_text(encoding="utf-8")

    # Every assertion below used to read `... in html or ... in frontend_source`,
    # where `html` was the deleted static shell. The "or" let the dead page
    # satisfy half of each check, so the React source was never strictly pinned.
    # The static page is gone: what remains is the source that actually ships.
    assert 'data-locale="en"' in frontend_source
    assert 'data-locale="zh-CN"' in frontend_source
    assert "sidebar-resizer" in frontend_source
    assert 'id="sidebar-toggle"' in frontend_source
    # The panel nav is generated from a map, so the target is bound, not
    # spelled out: `data-target={key}`. Pin the binding *and* the map entries --
    # asserting the literal `data-target="console"` would pin a string the
    # component never contains (the old "or" hid that behind the deleted page).
    assert "data-target={key}" in frontend_source
    assert "activePanel, setActivePanel] = useState<PanelKey>(" in frontend_source
    for panel in ("workbench", "console"):
        assert f'{panel}: {{ titleKey:' in frontend_source
    assert 'id="mcp-refresh"' in frontend_source
    assert 'id="mcp-status-grid"' in frontend_source
    assert "getMcpStatus" in frontend_source
    assert "mcpStatusTitle" in frontend_i18n
    # The starting panel comes from the pathname, not from a hardcoded default,
    # and both views are rendered inline: `<iframe>` is gone, so the frame-title
    # keys that only labelled the frames are gone with it.
    assert "useState<PanelKey>(panelFromPathname)" in frontend_source
    assert "<iframe" not in frontend_source
    assert "FrameTitle" not in frontend_i18n
    # ... but the nav labels are what a person reads, so pin those instead.
    assert 'workbench: "\u7b56\u5212\u5de5\u4f5c\u53f0"' in frontend_i18n
    assert 'console: "\u6d41\u7a0b\u63a7\u5236\u53f0"' in frontend_i18n
    # Locale used to be the shell's own state, read here from `STUDIO_LOCALE_KEY`.
    # A single provider owns it now and is the only reader of the key, so the
    # shell must not have grown a copy back -- and the provider must be the one
    # touching the document element.
    assert "STUDIO_LOCALE_KEY" not in frontend_source
    assert "initialLocale(STUDIO_LOCALE_KEY)" in locale_theme_source
    # Pinned as the *assignment*, not as the member expression. The module's own
    # docstring names `document.documentElement.lang` while explaining what the
    # three old documents each did, so the bare substring stayed true with the
    # assignment deleted -- the guard was vacuous and the mutation caught it.
    assert "document.documentElement.lang = locale" in locale_theme_source
    assert "document.documentElement.dataset.theme = theme" in locale_theme_source
    # Engine version used to have a second implementation here, parsing the
    # handoff out of localStorage itself. It reads the shared plan now.
    #
    # Pinned as the *call* rather than as the two identifiers: the shell also
    # imports `readHandoffPlan`, so `"readHandoffPlan" in frontend_source` stays
    # true after the call is swapped back out for a hand-rolled decoder. The
    # mutation that reintroduces one proved it -- only the `JSON.parse` line
    # below went red, this one sat green with the import satisfying it.
    assert "selectedEngineVersion(readHandoffPlan())" in frontend_source
    assert "JSON.parse(localStorage.getItem" not in frontend_source
    # The workbench hands its plan to the console through this localStorage key.
    assert "savePlanningHandoff" in workbench_source


def test_store_keys_are_defined_once_and_imported_everywhere():
    """The shared localStorage keys must have exactly one definition.

    `StudioShell.selectedEngineVersion()` reads the planning handoff straight out
    of `localStorage` to pick a default engine version. It used to spell the key
    out as a string literal while `shared/storage.ts` exported `HANDOFF_KEY` for
    the workbench and console -- so the key had two definitions and the shell's
    copy was invisible to a rename. Renaming the export would have silently cut
    the shell off from the handoff, with no test failing.
    """

    module = _load_studio_app()
    src = module.REPO_ROOT.joinpath("apps/frontend/src")
    storage = src.joinpath("shared/storage.ts").read_text(encoding="utf-8")

    for key in (
        "fantasy-agent-planning-handoff",
        "fantasy-agent-theme",
        "fantasy-agent-studio-locale",
        "fantasy-agent-studio-sidebar-width",
        "fantasy-agent-studio-sidebar-collapsed",
        "fantasy-agent-orchestration-session",
    ):
        assert storage.count(key) == 1, f"{key} must be defined exactly once, in shared/storage.ts"

    offenders = []
    for path in src.rglob("*.ts*"):
        if path.name in {"storage.ts"} or path.name.endswith(".test.ts") or path.name.endswith(".test.tsx"):
            continue
        text = path.read_text(encoding="utf-8")
        for key in ("fantasy-agent-planning-handoff", "fantasy-agent-studio-locale"):
            if key in text:
                offenders.append(f"{path.relative_to(module.REPO_ROOT)}: {key}")

    assert offenders == [], f"import the key from shared/storage instead: {offenders}"


def test_workbench_serves_the_react_app_when_dist_exists(monkeypatch, tmp_path):
    """``/workbench`` no longer points at a hand-written page.

    It used to be an unconditional ``FileResponse`` around the 2359-line
    ``planning-workbench.html`` -- the one legacy page that was genuinely
    alive. The workbench is now a React route inside the SPA bundle, so this
    pins the routing change rather than the old behaviour: whoever reverts
    ``apps/studio/app/main.py::workbench`` to a bare ``FileResponse`` will see
    this fail.
    """

    module = _load_studio_app()
    built = tmp_path / "index.html"
    built.write_text("<!doctype html><div id=root></div>", encoding="utf-8")
    monkeypatch.setattr(module, "FRONTEND_INDEX_PATH", built)

    assert Path(module.workbench().path) == built


def test_workbench_route_is_not_a_legacy_page():
    """Guards the retirement: the old page must not come back."""

    module = _load_studio_app()
    source = Path(module.__file__).read_text(encoding="utf-8")

    assert "WORKBENCH_PATH" not in source
    assert "planning-workbench.html" not in source


def test_studio_routes_plan_and_workbench_tools_through_one_server():
    module = _load_studio_app()
    request = PromptRequest(
        prompt="a rooftop parkour demo with wall-runs, vaults, slides, boost pads, and checkpoints",
        target_minutes=10,
    )

    plan = module.plan(request)
    assert plan.production_pipeline is not None
    assert plan.production_pipeline.next_stage == "comfyui_visual_production"

    tool = module._workbench_tool(
        "prepare_production_pipeline", request.model_dump(mode="json")
    )
    assert tool["structuredContent"]["kind"] == "production_pipeline"

    unknown = module._workbench_tool("does_not_exist", request.model_dump(mode="json"))
    assert unknown["isError"] is True


def test_execute_confirmation_gate_runs_no_job():
    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )
    req = module.ExecuteDemoRequest(plan=plan, engine="Godot 4", confirmed=False)
    result = module.execute_demo(req)

    assert result["status"] == "confirmation_required"
    assert result["engine"] == "godot"
    assert result["planned_side_effects"]
    # No job was registered.
    assert "job_id" not in result


def test_execute_starts_job_and_polls(monkeypatch):
    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.executor import ExecutionResult, StageResult
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )

    # Stub the executor so no real engine runs.
    def fake_godot(plan_arg, **kwargs):
        if not kwargs.get("confirmed"):
            return ExecutionResult(
                status="confirmation_required", session_id="x", planned_side_effects=["write project"]
            )
        return ExecutionResult(
            status="done",
            session_id="x",
            project_dir="generated/godot/sessions/x/demo",
            stages=[StageResult("create", "done"), StageResult("import", "done")],
        )

    def fake_launch(request):
        return fake_godot(request.plan, confirmed=request.confirmed)

    monkeypatch.setattr(module, "launch_demo", fake_launch)

    started = module.execute_demo(module.ExecuteDemoRequest(plan=plan, engine="Godot 4", confirmed=True))
    assert started["status"] == "running"
    job_id = started["job_id"]

    # Drain the single-worker pool so the background job completes.
    module._EXECUTE_POOL.shutdown(wait=True)

    status = module.execute_status(job_id)
    assert status["status"] == "done"
    assert status["result"]["project_dir"].endswith("demo")
    assert [s["name"] for s in status["result"]["stages"]] == ["create", "import"]


def test_execute_returns_and_reuses_a_session_id(monkeypatch):
    """Node-level rework needs the session id back, or nothing can be resumed."""

    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.executor import ExecutionResult
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )
    seen: list[str] = []

    def fake_launch(request):
        seen.append(request.session_id)
        if not request.confirmed:
            return ExecutionResult(
                status="confirmation_required",
                session_id=request.session_id,
                planned_side_effects=["write project"],
            )
        return ExecutionResult(status="done", session_id=request.session_id)

    monkeypatch.setattr(module, "launch_demo", fake_launch)

    preview = module.execute_demo(
        module.ExecuteDemoRequest(plan=plan, engine="Godot 4", confirmed=False)
    )
    assert preview["session_id"], "the UI needs the session id to resume later"

    started = module.execute_demo(
        module.ExecuteDemoRequest(
            plan=plan,
            engine="Godot 4",
            confirmed=True,
            session_id="sess-42",
            resume_from="create",
        )
    )
    module._EXECUTE_POOL.shutdown(wait=True)

    assert started["session_id"] == "sess-42"
    assert seen[-1] == "sess-42"


def test_session_state_endpoint_reads_persisted_stages(monkeypatch, tmp_path):
    """The rework panel reads this to offer one node to re-run."""

    from fantasy_agent.pipeline_state import StageState, record_stage

    module = _load_studio_app()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    record_stage(
        "sess-1", StageState(name="blender", status="failed"), workspace_root=tmp_path
    )
    record_stage(
        "sess-1", StageState(name="create", status="done"), workspace_root=tmp_path
    )

    state = module.session_state("sess-1", engine="godot")
    assert state["found"]
    assert state["done"] == ["create"]
    assert state["failed"] == ["blender"]
    assert "import" in state["stage_order"]

    missing = module.session_state("nope", engine="godot")
    assert missing["found"] is False
    assert missing["stages"] == []


def test_execute_status_unknown_job():
    module = _load_studio_app()
    assert module.execute_status("nope")["status"] == "unknown"


def test_write_approval_manifest_api_writes_generated_yaml(monkeypatch, tmp_path):
    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.workflows import run_director_workflow

    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )
    review = _materialize_review_artifacts(
        plan.creative_review,
        tmp_path,
        target='godot',
    )
    first = review.items[0].asset_id
    second = review.items[1].asset_id
    blender_item = next(item for item in review.items if item.source == 'blender')
    req = module.ApprovalManifestRequest(
        review=review,
        target='godot',
        decisions={
            first: "approved",
            second: "needs_revision",
            blender_item.asset_id: "approved",
        },
    )
    assert req.target == 'godot'

    response = module.write_approval_manifest(req)

    assert response.status == "written"
    assert response.manifest_path == "generated/asset-approval-manifest.yaml"
    output = tmp_path / response.manifest_path
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "approved_asset_ids:" in text
    assert first in text
    assert second in response.manifest.revision_asset_ids
    blender_decision = next(
        decision
        for decision in response.manifest.decisions
        if decision.asset_id == blender_item.asset_id
    )
    assert blender_item.asset_path.endswith('.fbx')
    assert blender_decision.asset_path == Path(blender_item.asset_path).with_suffix(
        '.glb'
    ).as_posix()
    assert blender_decision.artifact_identity is not None


@pytest.mark.parametrize(
    ("case", "detail_part"),
    [
        ("missing", "Reviewed artifact is missing"),
        ("outside", "escapes workspace"),
        ("traversal", "Parent traversal"),
        ("symlink", "escapes workspace"),
    ],
)
def test_write_approval_manifest_api_rejects_invalid_public_blender_glb(
    case,
    detail_part,
    monkeypatch,
    tmp_path: Path,
):
    from fastapi import HTTPException

    from fantasy_agent.workflows import run_director_workflow

    module = _load_studio_app()
    workspace_root = tmp_path / 'workspace'
    workspace_root.mkdir()
    outside_glb = tmp_path / 'outside.glb'
    outside_glb.write_bytes(b'outside-secret')
    monkeypatch.setattr(module, 'REPO_ROOT', workspace_root)
    plan = run_director_workflow(
        PromptRequest(prompt='rooftop parkour chase', target_minutes=10)
    )
    blender_item = next(
        item for item in plan.creative_review.items if item.source == 'blender'
    )
    if case == 'outside':
        review_item = blender_item.model_copy(
            update={'asset_path': (tmp_path / 'outside.fbx').as_posix()}
        )
    elif case == 'traversal':
        review_item = blender_item.model_copy(update={'asset_path': '../outside.fbx'})
    elif case == 'symlink':
        linked_glb = workspace_root / 'linked.glb'
        linked_glb.symlink_to(outside_glb)
        review_item = blender_item.model_copy(update={'asset_path': 'linked.fbx'})
    else:
        review_item = blender_item
    invalid_review = plan.creative_review.model_copy(update={'items': [review_item]})

    with pytest.raises(HTTPException) as rejected:
        module.write_approval_manifest(
            module.ApprovalManifestRequest(
                review=invalid_review,
                target="godot",
                decisions={review_item.asset_id: "approved"},
            )
        )
    assert rejected.value.status_code == 400
    assert detail_part in str(rejected.value.detail)
    assert not (workspace_root / 'generated' / 'asset-approval-manifest.yaml').exists()


def test_asset_execute_confirmation_gate_runs_no_job():
    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )
    req = module.AssetExecutionRequest(plan=plan, with_assets=True, with_visuals=True, confirmed=False)
    result = module.execute_assets(req)

    assert result["status"] == "confirmation_required"
    assert any("Blender" in effect for effect in result["planned_side_effects"])
    assert any("ComfyUI" in effect for effect in result["planned_side_effects"])
    assert "job_id" not in result


def test_asset_execute_starts_job_and_polls(monkeypatch):
    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.executor import ExecutionResult, StageResult
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )

    def fake_assets(req, *, confirmed):
        if not confirmed:
            return ExecutionResult(
                status="confirmation_required", session_id="a", planned_side_effects=["run assets"]
            )
        return ExecutionResult(
            status="done",
            session_id="a",
            stages=[StageResult("comfyui", "done"), StageResult("blender", "done")],
        )

    monkeypatch.setattr(module, "_build_asset_execution_result", fake_assets)

    started = module.execute_assets(
        module.AssetExecutionRequest(plan=plan, with_assets=True, with_visuals=True, confirmed=True)
    )
    second = module.execute_assets(
        module.AssetExecutionRequest(plan=plan, with_assets=True, with_visuals=True, confirmed=True)
    )
    assert started["status"] == "running"
    assert second["status"] == "running"
    assert started["job_id"] != second["job_id"]
    job_id = started["job_id"]

    module._EXECUTE_POOL.shutdown(wait=True)

    status = module.asset_execute_status(job_id)
    assert status["status"] == "done"
    assert [s["name"] for s in status["result"]["stages"]] == ["comfyui", "blender"]


def test_execute_demo_job_ids_do_not_collide(monkeypatch):
    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.executor import ExecutionResult
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )

    def fake_launch(request):
        return ExecutionResult(status="done", session_id=request.session_id or "x")

    monkeypatch.setattr(module, "launch_demo", fake_launch)
    first = module.execute_demo(module.ExecuteDemoRequest(plan=plan, engine="godot", confirmed=True))
    second = module.execute_demo(module.ExecuteDemoRequest(plan=plan, engine="godot", confirmed=True))

    assert first["job_id"] != second["job_id"]
    module._EXECUTE_POOL.shutdown(wait=True)


def test_asset_execute_status_unknown_job():
    module = _load_studio_app()
    assert module.asset_execute_status("nope")["status"] == "unknown"


def test_approval_manifest_api_returns_synchronized_bundle(monkeypatch, tmp_path):
    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="a stealth courier escapes a haunted station")
    )
    assert plan.production_spec_bundle is not None
    review = _materialize_review_artifacts(plan.creative_review, tmp_path)
    item = review.items[0]
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    response = module.write_approval_manifest(
        module.ApprovalManifestRequest(
            review=review,
            decisions={item.asset_id: "approved"},
            production_spec_bundle=plan.production_spec_bundle,
        )
    )

    assert response.production_spec_bundle is not None
    synced = next(
        asset
        for asset in response.production_spec_bundle.resource_pipeline.assets
        if asset.asset_id == item.asset_id
    )
    assert synced.approval_status == "approved"
    assert synced.blocked_reason is None
    assert (tmp_path / "generated" / "specs" / "production-spec-bundle.yaml").exists()

def test_spec_bundle_preview_api_returns_validation_artifacts_and_traces():
    module = _load_studio_app()
    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="a combat arena with guards and ranged turrets")
    )
    assert plan.production_spec_bundle is not None

    response = module.preview_spec_bundle(
        module.SpecBundlePreviewRequest(
            production_spec_bundle=plan.production_spec_bundle,
            target="godot",
        )
    )

    assert response.validation.status in {"passed", "warning"}
    assert response.artifacts
    assert response.traces
    # The godot preview must report the same artifact set execution writes:
    # the adapter runtime plus the per-table config exports.
    assert any(artifact.path == "data/production-spec-runtime.json" for artifact in response.artifacts)
    assert any(artifact.path.startswith("data/config/") for artifact in response.artifacts)
    assert any(trace.spec_field.startswith("config_tables.tables.") for trace in response.traces)
    assert response.executable_qa.results
    assert "/api/specs/preview" in {route.path for route in module.app.routes}


def test_studio_exposes_job_cancel_endpoints():
    module = _load_studio_app()
    routes = {route.path for route in module.app.routes}

    assert "/api/execute/{job_id}/cancel" in routes
    assert "/api/assets/execute/{job_id}/cancel" in routes
    assert module.execute_cancel("nope") == {"status": "unknown", "job_id": "nope"}
    assert module.asset_execute_cancel("nope") == {"status": "unknown", "job_id": "nope"}


def test_cancel_endpoint_stops_a_running_job(monkeypatch):
    module = _load_studio_app()
    from fantasy_agent import process_runner
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )
    running = threading.Event()

    def slow_launch(request):
        running.set()
        while True:
            event = process_runner.current_cancel_event()
            if event is not None and event.is_set():
                raise process_runner.ProcessCancelled("godot import")
            time.sleep(0.05)

    monkeypatch.setattr(module, "launch_demo", slow_launch)

    started = module.execute_demo(
        module.ExecuteDemoRequest(plan=plan, engine="Godot 4", confirmed=True)
    )
    job_id = started["job_id"]
    assert running.wait(timeout=5)

    assert module.execute_cancel(job_id) == {"job_id": job_id, "status": "cancelling"}

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and module.execute_status(job_id)["status"] != "cancelled":
        time.sleep(0.05)

    assert module.execute_status(job_id)["status"] == "cancelled"
    module._EXECUTE_POOL.shutdown(wait=True)


def test_request_models_reject_unknown_fields():
    """A lenient request model turns a misspelled field into a silent no-op.

    FastAPI drops fields the model never declared without complaining, so a
    caller that sends ``resume_from`` against a model lacking it gets a
    successful response and no resume. That has bitten this project twice.
    """

    module = _load_studio_app()
    models = [
        obj
        for name, obj in vars(module).items()
        if name.endswith("Request") and isinstance(obj, type) and issubclass(obj, BaseModel)
    ]

    assert models, "no request models found -- the naming convention changed"
    for model in models:
        assert model.model_config.get("extra") == "forbid", f"{model.__name__} accepts extras"


def test_frontend_includes_spec_bundle_panel():
    module = _load_studio_app()
    flow_source = module.REPO_ROOT.joinpath(
        "apps/frontend/src/console/FlowConsole.tsx"
    ).read_text(encoding="utf-8")
    rendering_source = module.REPO_ROOT.joinpath(
        "apps/frontend/src/console/rendering.tsx"
    ).read_text(encoding="utf-8")

    assert '["specs", "tabSpecs"]' in flow_source
    assert "SpecBundlePanel" in flow_source
    assert "spec-trace-list" in rendering_source


def test_agent_run_forwards_the_permission_grants(monkeypatch):
    """The panel's toggles must reach the loop.

    Guards a real failure: the call site passed include_engine_tools while the
    request model lacked the field, so Pydantic silently dropped it and every
    run came back as an AttributeError instead of running.
    """

    module = _load_studio_app()
    captured: dict = {}

    def fake_run(goal, **kwargs):
        captured["goal"] = goal
        captured.update(kwargs)
        from fantasy_agent.agent_loop import AgentRunResult

        return AgentRunResult(status="done", answer="ok")

    monkeypatch.setattr("fantasy_agent.agent_loop.run_agent", fake_run)

    response = module.run_planning_agent(
        module.AgentRunRequest(
            goal="build it",
            max_turns=3,
            include_engine_tools=True,
            allow_write=True,
            allow_execute=True,
        )
    )

    assert response["status"] == "done", response.get("error")
    assert captured["include_engine_tools"] is True
    assert captured["allow_write"] is True
    assert captured["allow_execute"] is True


def test_agent_run_rejects_an_empty_goal():
    module = _load_studio_app()

    response = module.run_planning_agent(module.AgentRunRequest(goal="   "))

    assert response["status"] == "error"


def test_execute_wires_the_whole_request_through_the_real_builder(monkeypatch):
    """At least one test must run the real ``launch_demo``.

    The other execute tests replace it wholesale, so a request field that never
    reaches the executor would still be green. This one stubs only
    ``execute_godot_demo`` and asserts every field actually arrives.
    """
    from fantasy_agent import executor, local_tools
    from fantasy_agent.executor import ExecutionResult
    from fantasy_agent.workflows import run_director_workflow

    module = _load_studio_app()
    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )
    captured: dict = {}

    def fake_execute_godot_demo(_plan, **kwargs):
        captured.update(kwargs)
        return ExecutionResult(status="done", session_id=kwargs["session_id"])

    monkeypatch.setattr(local_tools, "_find_godot", lambda: "C:/fake/godot.exe")
    monkeypatch.setattr(local_tools, "_find_blender", lambda: "C:/fake/blender.exe")
    monkeypatch.setattr(executor, "execute_godot_demo", fake_execute_godot_demo)

    started = module.execute_demo(
        module.ExecuteDemoRequest(
            plan=plan,
            engine="Godot 4",
            confirmed=True,
            session_id="sess-99",
            with_assets=True,
            with_visuals=True,
            with_gameplay=True,
            approval_manifest_path="generated/asset-approval-manifest.yaml",
            resume_from="create",
        )
    )
    module._EXECUTE_POOL.shutdown(wait=True)

    assert started["status"] == "running"
    assert captured["confirmed"] is True
    assert captured["session_id"] == "sess-99"
    assert captured["godot_exe"] == "C:/fake/godot.exe"
    assert captured["blender_exe"] == "C:/fake/blender.exe"
    assert captured["with_assets"] is True
    assert captured["with_visuals"] is True
    assert captured["with_gameplay"] is True
    assert captured["approval_manifest_path"] == "generated/asset-approval-manifest.yaml"
    assert captured["resume_from"] == "create"


def _offline_http_json(*_args, **_kwargs):
    raise OSError("offline")


def test_correction_targets_report_probe_results_not_just_ids(monkeypatch):
    """correction_targets() must reflect what the probes actually found.

    The previous assertion only checked target ids, so it stayed green while
    the probes did real urlopen calls and real shutil.which/glob scans. Pinning
    both the ready and the degraded outcome makes the status meaningful.
    """
    from fantasy_agent import local_tools

    module = _load_studio_app()
    monkeypatch.setattr(
        local_tools,
        "_http_json",
        lambda url, timeout=0.45: {"system": {"comfyui_version": "1.2.3"}},
    )
    monkeypatch.setattr(local_tools, "_find_blender", lambda: "C:/blender.exe")
    monkeypatch.setattr(local_tools, "_find_godot", lambda: "C:/godot.exe")

    ready = module.correction_targets(engine="Godot 4")
    ready_status = {target["id"]: target["status"] for target in ready["targets"]}
    assert ready_status["comfyui"] == "ready"
    assert ready_status["blender"] == "ready"
    assert ready_status["godot"] == "ready"

    monkeypatch.setattr(local_tools, "_http_json", _offline_http_json)
    monkeypatch.setattr(local_tools, "_find_blender", lambda: None)
    monkeypatch.setattr(local_tools, "_find_godot", lambda: None)

    degraded = module.correction_targets(engine="Godot 4")
    degraded_status = {target["id"]: target["status"] for target in degraded["targets"]}
    assert degraded_status["comfyui"] != "ready"
    assert degraded_status["blender"] == "unavailable"
    assert degraded_status["godot"] == "unavailable"


def test_frontend_includes_agent_panel():
    module = _load_studio_app()
    shell = module.REPO_ROOT.joinpath(
        "apps/frontend/src/studio/StudioShell.tsx"
    ).read_text(encoding="utf-8")
    api = module.REPO_ROOT.joinpath("apps/frontend/src/shared/api.ts").read_text(encoding="utf-8")

    assert "AgentPanel" in shell
    assert 'data-panel="agent"' in shell
    assert "runAgent" in api
    assert "/api/agent/run" in api


def test_tool_catalog_endpoint_serves_the_registry_view():
    """The route must return ``tool_catalog()``, not the declared contract dump.

    The two are easy to conflate -- ``/api/tool-contracts`` already exists and
    returns a list of contracts -- so a route that reached for the wrong helper
    would still return 200 with plausible JSON. The distinguishing field is
    ``permission_counts``: the contract dump has no notion of tiers, because
    tiers come from the MCP annotations the registry derives them from.
    """

    module = _load_studio_app()
    payload = module.tool_catalog_endpoint()

    assert isinstance(payload, dict), "the catalog is an object, not a bare list"
    assert payload["tools"], "catalog listed no tools"
    assert "permission_counts" in payload, (
        "the catalog must report permission_counts; without it this payload is "
        "indistinguishable from the contract dump at /api/tool-contracts"
    )
    assert set(payload["permission_counts"]) >= {"read_only", "write", "execute"}
    # Every entry must name its tier, since that is the field the panel renders.
    assert all("permission" in entry for entry in payload["tools"])

    # And the endpoint the panel calls is the one the frontend actually fetches.
    api = module.REPO_ROOT.joinpath("apps/frontend/src/shared/api.ts").read_text(encoding="utf-8")
    assert '"/api/tool-catalog"' in api


def test_frontend_includes_the_spec_regen_and_blender_script_panels():
    """A wired endpoint with no mounted panel would still pass the coverage guard.

    ``tests/test_frontend_endpoint_coverage.py`` only sees the URL string in
    ``api.ts``; it cannot tell a function that nothing renders from one an
    operator can reach. These two panels are the call sites, so they are pinned
    by name here.
    """

    module = _load_studio_app()
    src = module.REPO_ROOT.joinpath("apps/frontend/src")

    flow_console = src.joinpath("console/FlowConsole.tsx").read_text(encoding="utf-8")
    rendering = src.joinpath("console/rendering.tsx").read_text(encoding="utf-8")
    build_panel = src.joinpath("shared/panels/PlanPanels.tsx").read_text(encoding="utf-8")
    blender_panel = src.joinpath("shared/panels/BlenderScriptPanel.tsx")

    assert "SpecRegenPanel" in rendering, "the spec regen panel is not defined"
    assert "<SpecRegenPanel" in flow_console, "the spec tab never mounts the spec regen panel"
    assert blender_panel.exists(), "the Blender script panel is not defined"
    assert "BlenderScriptPanel" in build_panel, "the build panel never mounts the Blender script panel"

# ── the orchestration board ─────────────────────────────────────────────────


def _studio(tmp_path: Path):
    """A loaded Studio whose sandbox is `tmp_path`, not the repository.

    `REPO_ROOT` is what the orchestrator writes session state under, so
    re-pointing it keeps a test run from leaving `generated/<engine>/sessions/`
    directories behind. Each `_load_studio_app()` returns a fresh module, so
    this does not touch the other tests' view of the repo.
    """

    module = _load_studio_app()
    module.REPO_ROOT = tmp_path
    module._ORCHESTRATION_SESSIONS.clear()
    return module


PROMPT = "a stealth courier escapes a haunted train station in ten minutes"


def _plan():
    """The plan the board would be showing, built deterministically.

    `use_llm=False` on purpose: the board posts a plan rather than a prompt, so
    a test of the board's endpoint should not need a provider to *produce* the
    plan. It still needs the run itself to fail without one -- that is what the
    stage outcomes below are read for.

    `engine_version="Godot 4"` picks the Godot route, which is what the stage
    ids below name. The Unreal route swaps `godot_quick_play` for
    `unreal_production` and the board treats them the same way, so only one of
    the two needs pinning down here.
    """

    from fantasy_agent.contracts import PromptRequest
    from fantasy_agent.workflows import run_director_workflow

    plan = run_director_workflow(
        PromptRequest(prompt=PROMPT, engine_version="Godot 4"), use_llm=False
    )
    assert plan.production_pipeline is not None
    return plan


def test_the_orchestration_endpoints_are_served():
    module = _load_studio_app()
    paths = {route.path for route in module.app.routes}

    assert "/api/orchestration/run" in paths
    assert "/api/orchestration/{session_id}" in paths
    # The board is a whole view, so it has a URL of its own rather than being
    # reachable only from the sidebar.
    assert "/pipeline" in paths


def test_a_run_reports_every_card_and_where_a_person_is_needed(tmp_path: Path):
    """The board's contract: one entry per stage, and a list of who to ask.

    The measured plan puts no confirmation gate on stage 1 (planning is
    read-only), so a first pass really does dispatch it -- and in a test run
    there is no provider configured, so it fails and everything downstream reads
    `blocked`. Both halves matter: the cards get real runtime states, and the
    five gated stages are still listed as waiting on a person even though the
    dependency chain has not reached them yet.
    """

    module = _studio(tmp_path)

    payload = module.run_orchestration(module.OrchestrationRunRequest(plan=_plan()))

    assert payload["status"] == "error"
    assert payload["error"].startswith("gameplay_orchestration")
    assert payload["session_id"]
    assert len(payload["stages"]) == 7

    by_id = {stage["stage_id"]: stage for stage in payload["stages"]}
    assert by_id["gameplay_orchestration"]["dispatched"] is True
    assert by_id["gameplay_orchestration"]["status"] == "failed"
    assert by_id["creative_review"]["kind"] == "human"

    # Not offered as an approve-able item: approving a human gate would not make
    # it run, so a button for it would be a control that does nothing.
    assert "creative_review" not in payload["pending_confirmations"]
    assert set(payload["pending_confirmations"]) == {
        "comfyui_visual_production",
        "blender_modeling",
        "asset_integration",
        "godot_quick_play",
        "optimization_testing",
    }

    # A dependency that has not finished comes first: nobody should be asked to
    # approve a stage whose inputs do not exist, and no gated stage was
    # dispatched just because the plan reached it.
    for stage in payload["stages"]:
        if stage["stage_id"] == "gameplay_orchestration":
            continue
        assert stage["status"] == "blocked", stage
        assert stage["dispatched"] is False, stage


def test_a_card_carries_the_plan_fields_it_is_drawn_from(tmp_path: Path):
    """The board draws a card from the plan, so the plan has to travel with it.

    These six fields are what F0's field-coverage work was about: the console's
    stage row showed `risks` and the workbench's did not, and neither showed
    `depends_on` -- the one field the orchestrator actually gates on. The board
    is now the only stage renderer, so it is the only thing that can lose them,
    and this is the test that says it has them.
    """

    module = _studio(tmp_path)

    payload = module.run_orchestration(module.OrchestrationRunRequest(plan=_plan()))
    card = next(
        entry for entry in payload["stages"] if entry["stage_id"] == "blender_modeling"
    )

    for field in ("purpose", "owner_agent", "depends_on", "mcp_tools", "quality_gates", "risks"):
        assert field in card, field
    assert card["depends_on"] == ["gameplay_orchestration"]
    assert card["owner_agent"] == "blender-worker"
    assert card["quality_gates"], "the measured plan declares quality gates for this stage"


def test_the_plan_time_status_and_the_runtime_one_are_both_carried(tmp_path: Path):
    """`ProductionTaskStatus` is written once at authoring time and never moves.

    A card that read only that field would render `pending` forever, no matter
    how far the run got -- so both are sent and the runtime one is what the
    board colours.
    """

    module = _studio(tmp_path)

    payload = module.run_orchestration(module.OrchestrationRunRequest(plan=_plan()))
    stage = next(
        entry for entry in payload["stages"] if entry["stage_id"] == "comfyui_visual_production"
    )

    assert stage["plan_status"] in {"pending", "ready", "blocked", "done"}
    assert stage["status"] == "blocked"
    # The two vocabularies are kept apart: no runtime status leaks into the
    # plan-time field. A board reading the wrong one would show a finished run
    # as `pending`, or a card waiting on a person as `ready`.
    assert stage["plan_status"] not in {
        "awaiting_confirmation",
        "awaiting_human",
        "running",
        "failed",
    }


def test_the_board_can_drill_from_a_card_into_the_process_steps(tmp_path: Path):
    """F3's drill-down reads this table, so it has to reach the client."""

    module = _studio(tmp_path)

    payload = module.run_orchestration(module.OrchestrationRunRequest(plan=_plan()))
    by_id = {stage["stage_id"]: stage for stage in payload["stages"]}

    assert by_id["blender_modeling"]["executor_stages"] == ["blender"]
    assert "import" in by_id["godot_quick_play"]["executor_stages"]
    # The whole table travels too, so the board can label a node it is not
    # currently showing without a second round trip.
    assert payload["stage_translation"]["creative_review"] == []


def test_a_plan_with_no_pipeline_is_an_error_status_not_an_exception(tmp_path: Path):
    module = _studio(tmp_path)
    plan = _plan()
    plan.production_pipeline = None

    payload = module.run_orchestration(module.OrchestrationRunRequest(plan=plan))

    assert payload["status"] == "error"
    assert "no production_pipeline" in payload["error"]
    assert payload["stages"] == []


def test_the_run_advances_the_plan_it_was_given_not_a_rebuilt_one(tmp_path: Path):
    """The card and the run must describe the same plan.

    This is why the request carries a plan instead of a prompt. Rebuilding from
    a prompt would let the board render one plan while the pass advanced
    another, and the mismatch would be invisible -- the cards would still
    populate, from the wrong plan.
    """

    module = _studio(tmp_path)
    plan = _plan()
    # Hand the board a two-stage slice of the measured plan. A rebuilt plan
    # would have seven stages again.
    plan.production_pipeline.stages = [
        stage
        for stage in plan.production_pipeline.stages
        if stage.id in {"gameplay_orchestration", "creative_review"}
    ]

    payload = module.run_orchestration(module.OrchestrationRunRequest(plan=plan))

    assert [entry["stage_id"] for entry in payload["stages"]] == [
        "gameplay_orchestration",
        "creative_review",
    ]


def test_a_bad_rework_confirmation_is_reported_rather_than_raising(tmp_path: Path):
    module = _studio(tmp_path)

    payload = module.run_orchestration(
        module.OrchestrationRunRequest(plan=_plan(), confirm_stages=["blender_modelingg"])
    )

    assert payload["status"] == "error"
    assert "unknown orchestration stage" in payload["error"]


def test_rewinding_a_card_forgets_it_and_everything_after_it(tmp_path: Path):
    """The rework button. Not a fresh session -- that replay is what 编排 exists to avoid."""

    module = _studio(tmp_path)
    plan = _plan()

    first = module.run_orchestration(module.OrchestrationRunRequest(plan=plan))
    session_id = first["session_id"]
    assert first["rewound"] == []

    second = module.run_orchestration(
        module.OrchestrationRunRequest(
            plan=plan,
            session_id=session_id,
            rewind_stage="blender_modeling",
        )
    )

    assert second["session_id"] == session_id
    # Read off the plan rather than listed by hand: the plan's `order` is what
    # the cutoff is computed from, and a hand-written list would only be
    # checking that the two orders happen to agree today.
    run_order = [
        stage.id for stage in sorted(plan.production_pipeline.stages, key=lambda s: s.order)
    ]
    assert second["rewound"] == run_order[run_order.index("blender_modeling") :]
    assert second["stages"][0]["status"] == "failed", "the first card kept its outcome"


def test_rewinding_an_unknown_card_is_reported_with_the_cards_still_there(tmp_path: Path):
    """A mistyped card id is a user mistake, so the board keeps its stages.

    The contrast with the empty-plan branch is the point: that one has no cards
    to lose, this one does, and answering with an empty stage list would blank
    the board over a typo.
    """

    module = _studio(tmp_path)

    first = module.run_orchestration(module.OrchestrationRunRequest(plan=_plan()))
    session_id = first["session_id"]

    payload = module.run_orchestration(
        module.OrchestrationRunRequest(
            plan=_plan(), session_id=session_id, rewind_stage="blender_modelling"
        )
    )

    assert payload["status"] == "error"
    assert "blender_modelling" in payload["error"]
    assert payload["rewound"] == []
    assert len(payload["stages"]) == 7


def test_orchestration_state_is_readable_without_advancing(tmp_path: Path):
    module = _studio(tmp_path)

    missing = module.orchestration_state("no-such-session")
    assert missing["found"] is False
    assert missing["stages"] == []
    assert missing["status"] == "pending"
    # The drill-down table is route metadata, not session state: the eight card
    # ids and the steps each owns do not depend on anything having run. An empty
    # table here would say the route has no execution steps at all.
    assert missing["stage_translation"]["blender_modeling"] == ["blender"]

    started = module.run_orchestration(module.OrchestrationRunRequest(plan=_plan()))
    session_id = started["session_id"]

    state = module.orchestration_state(session_id)

    assert state["found"] is True
    assert state["session_id"] == session_id
    # The board renders `[status]` in its summary line; a payload without the
    # field made a reload show the literal string "undefined".
    assert state["status"] == started["status"]
    assert state["stage_translation"] == missing["stage_translation"]
    assert [stage["status"] for stage in state["stages"]] == [
        stage["status"] for stage in started["stages"]
    ]


def test_a_second_request_reuses_the_session_it_was_given(tmp_path: Path):
    """Approving a stage is a second request against the same session.

    Keeping the session is what makes staging usable at all: a fresh
    orchestrator would forget the approval it was just given and ask again.

    The approval does not jump the dependency queue -- the stage still reads
    `blocked` because stage 1 failed -- and that is the assertion: an approval
    answers one question (may this stage start) without answering another (are
    its inputs ready).
    """

    module = _studio(tmp_path)

    first = module.run_orchestration(module.OrchestrationRunRequest(plan=_plan()))
    session_id = first["session_id"]
    assert "blender_modeling" in first["pending_confirmations"]

    second = module.run_orchestration(
        module.OrchestrationRunRequest(
            plan=_plan(),
            session_id=session_id,
            confirm_stages=["blender_modeling"],
        )
    )

    assert second["session_id"] == session_id
    assert "blender_modeling" in second["confirmed"]
    assert "blender_modeling" not in second["pending_confirmations"]
    blender = next(e for e in second["stages"] if e["stage_id"] == "blender_modeling")
    assert blender["status"] == "blocked"
    assert blender["dispatched"] is False


def test_unknown_workbench_tool_names_the_planning_list():
    from fantasy_agent.planning_actions import PLANNING_TOOL_NAMES

    module = _load_studio_app()
    request = PromptRequest(
        prompt="rooftop parkour chase with wall-runs and checkpoints",
        target_minutes=10,
    )
    unknown = module._workbench_tool("does_not_exist", request.model_dump(mode="json"))
    available = ", ".join(PLANNING_TOOL_NAMES)
    assert unknown["isError"] is True
    assert unknown["content"][0]["text"] == (
        f"Unknown Studio planning tool 'does_not_exist'. Available tools: {available}."
    )


def test_workbench_slice_keeps_snake_and_camel_case():
    module = _load_studio_app()
    request = PromptRequest(
        prompt="rooftop parkour chase with wall-runs and checkpoints",
        target_minutes=10,
        engine_version="Godot 4.6",
    )
    tool = module._workbench_tool("prepare_godot_plan", request.model_dump(mode="json"))
    structured = tool["structuredContent"]
    meta = tool["_meta"]
    assert structured["kind"] == "godot_project_plan"
    assert structured["godot_plan"]["engine_version"] == "Godot 4.6"
    assert meta["godotPlan"] == structured["godot_plan"]
    assert meta["activePanel"] == "build"
    assert meta["toolName"] == "prepare_godot_plan"
    assert tool["content"][0]["text"].startswith("Prepared Godot quick-play handoff")

    pipeline = module._workbench_tool(
        "prepare_production_pipeline", request.model_dump(mode="json")
    )
    assert pipeline["structuredContent"]["kind"] == "production_pipeline"
    assert pipeline["_meta"]["activePanel"] == "pipeline"
    assert pipeline["_meta"]["productionPipeline"] == pipeline["structuredContent"]["production_pipeline"]


def test_execute_resume_errors_stay_http_400():
    import pytest
    from fastapi import HTTPException

    from fantasy_agent.workflows import run_director_workflow

    module = _load_studio_app()
    plan = run_director_workflow(
        PromptRequest(prompt="rooftop parkour chase", target_minutes=10, engine_version="Godot 4")
    )
    with pytest.raises(HTTPException) as missing:
        module.execute_demo(
            module.ExecuteDemoRequest(plan=plan, engine="Godot 4", resume_from="create")
        )
    assert missing.value.status_code == 400
    assert missing.value.detail == "resume_from 需要同时提供 session_id，否则无法复用已完成的节点"

    with pytest.raises(HTTPException) as unreal:
        module.execute_demo(
            module.ExecuteDemoRequest(
                plan=plan,
                engine="UE5",
                session_id="sess-1",
                resume_from="create",
                confirmed=True,
            )
        )
    assert unreal.value.status_code == 400
    assert unreal.value.detail == "Unreal 续跑还没接线，不能在 Unreal 上静默忽略 resume_from"

    with pytest.raises(HTTPException) as bad:
        module.execute_demo(
            module.ExecuteDemoRequest(
                plan=plan,
                engine="Godot 4",
                session_id="sess-1",
                resume_from="not-a-stage",
            )
        )
    assert bad.value.status_code == 400
    assert "未知的续跑节点" in bad.value.detail
