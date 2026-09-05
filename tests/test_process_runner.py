"""Tests for the streaming subprocess runner."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from fantasy_agent import process_runner


def _spawn_children_script() -> str:
    """A script that starts a long-lived child, prints its pid, then sleeps."""

    return (
        "import subprocess, sys, time\n"
        f"child = subprocess.Popen([{sys.executable!r}, '-c', 'import time; time.sleep(120)'])\n"
        "print(child.pid, flush=True)\n"
        "time.sleep(120)\n"
    )


def _slow_script(count: int = 100, delay: float = 0.5) -> str:
    return (
        "import time\n"
        f"for i in range({count}):\n"
        "    print(i, flush=True)\n"
        f"    time.sleep({delay})\n"
    )


def _pid_alive(pid: int) -> bool:
    if os.name == "nt":
        # tasklist prints in the console codepage; replace so a stray
        # multi-byte glyph cannot blow up the probe on zh-CN Windows.
        listed = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        ).stdout or ""
        columns = (line.split() for line in listed.splitlines())
        return any(len(parts) > 1 and parts[1] == str(pid) for parts in columns)
    return Path(f"/proc/{pid}").exists()


def test_streams_logs_before_the_process_exits(tmp_path: Path):
    """The whole point: log content exists while the tool is still running."""

    stdout_path = tmp_path / "out.log"
    script = (
        "import time\n"
        "print('first-line', flush=True)\n"
        "time.sleep(3)\n"
        "print('second-line', flush=True)\n"
    )
    captured: dict[str, subprocess.CompletedProcess[str]] = {}

    def worker() -> None:
        captured["result"] = process_runner.run_streaming(
            [sys.executable, "-c", script],
            stdout_path=stdout_path,
            timeout=60,
        )

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    time.sleep(1.5)
    partial = stdout_path.read_text(encoding="utf-8")
    thread.join(timeout=60)

    assert "first-line" in partial, "log must be written while the process runs"
    assert "second-line" not in partial
    assert "second-line" in captured["result"].stdout


def test_returns_completed_process_contract(tmp_path: Path):
    result = process_runner.run_streaming(
        [sys.executable, "-c", "print('hello', flush=True)"],
        stdout_path=tmp_path / "out.log",
        stderr_path=tmp_path / "err.log",
        timeout=60,
    )

    assert result.returncode == 0
    assert "hello" in result.stdout
    assert (tmp_path / "out.log").read_text(encoding="utf-8").strip() == "hello"


def test_mirrors_stderr_to_its_own_file(tmp_path: Path):
    result = process_runner.run_streaming(
        [sys.executable, "-c", "import sys; print('bad', file=sys.stderr, flush=True)"],
        stdout_path=tmp_path / "out.log",
        stderr_path=tmp_path / "err.log",
        timeout=60,
    )

    assert "bad" in result.stderr
    assert "bad" in (tmp_path / "err.log").read_text(encoding="utf-8")


def test_timeout_raises_and_keeps_partial_output(tmp_path: Path):
    stdout_path = tmp_path / "out.log"
    started = time.monotonic()

    with pytest.raises(subprocess.TimeoutExpired) as excinfo:
        process_runner.run_streaming(
            [sys.executable, "-c", _slow_script()],
            stdout_path=stdout_path,
            timeout=1.5,
        )

    elapsed = time.monotonic() - started
    assert elapsed < 25, "timeout must actually kill the tree, not wait it out"
    assert excinfo.value.output, "partial stdout must survive a timeout"
    assert (tmp_path / "out.log").read_text(encoding="utf-8").strip()


def test_cancel_stops_the_run_early(tmp_path: Path):
    event = threading.Event()
    threading.Timer(1.2, event.set).start()
    started = time.monotonic()

    with pytest.raises(process_runner.ProcessCancelled) as excinfo:
        process_runner.run_streaming(
            [sys.executable, "-c", _slow_script()],
            stdout_path=tmp_path / "out.log",
            cancel_event=event,
            timeout=120,
        )

    elapsed = time.monotonic() - started
    assert elapsed < 25, f"cancel should return quickly, took {elapsed:.1f}s"
    assert excinfo.value.output


def test_cancel_is_picked_up_from_the_context(tmp_path: Path):
    """Workers never receive a cancel flag; they read it from context."""

    event = threading.Event()
    threading.Timer(1.0, event.set).start()

    with pytest.raises(process_runner.ProcessCancelled):
        with process_runner.cancel_scope(event):
            process_runner.run_streaming(
                [sys.executable, "-c", _slow_script()],
                stdout_path=tmp_path / "out.log",
                timeout=120,
            )


def test_cancel_scope_restores_the_previous_binding():
    sentinel = threading.Event()
    token = process_runner.bind_cancel_event(sentinel)
    with process_runner.cancel_scope(None):
        assert process_runner.current_cancel_event() is None
    assert process_runner.current_cancel_event() is sentinel
    process_runner.reset_cancel_event(token)
    assert process_runner.current_cancel_event() is None


def test_terminate_process_tree_kills_children():
    process = subprocess.Popen(
        [sys.executable, "-c", _spawn_children_script()],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    child_pid = int(process.stdout.readline().strip())

    process_runner.terminate_process_tree(process)
    process.wait(timeout=10)
    assert process.poll() is not None, "process must be reaped after termination"

    time.sleep(0.5)
    assert not _pid_alive(child_pid), "child process must die with its parent"


def test_is_streaming_runner_detects_the_streaming_flag():
    def fake(*args, **kwargs):  # noqa: ARG001 - shape of a test double
        return subprocess.CompletedProcess(args=args[0] if args else [], returncode=0)

    assert process_runner.is_streaming_runner(process_runner.run_streaming)
    assert not process_runner.is_streaming_runner(fake)
    assert not process_runner.is_streaming_runner(subprocess.run)


def test_on_line_receives_every_stream(tmp_path: Path):
    seen: list[tuple[str, str]] = []
    process_runner.run_streaming(
        [
            sys.executable,
            "-c",
            "import sys; print('out'); print('err', file=sys.stderr)",
        ],
        stdout_path=tmp_path / "out.log",
        stderr_path=tmp_path / "err.log",
        on_line=lambda stream, line: seen.append((stream, line)),
        timeout=60,
    )

    assert (process_runner.STDOUT, "out") in seen
    assert (process_runner.STDERR, "err") in seen


def test_broken_on_line_is_reported_not_swallowed(tmp_path: Path):
    """A sink with the wrong arity must surface, not look like 'no output'."""

    result = process_runner.run_streaming(
        [sys.executable, "-c", "print('hello')"],
        on_line=[] .append,  # one-argument sink; the API passes (stream, line)
        timeout=60,
    )

    assert result.returncode == 0, "the run itself must still succeed"
    assert "hello" in (result.stdout or "")
    assert "output sink failed" in (result.stdout or ""), (
        "a broken sink must be visible in the captured output"
    )


def test_log_files_are_truncated_between_runs(tmp_path: Path):
    stdout_path = tmp_path / "out.log"
    stdout_path.write_text("stale content from a previous run\n", encoding="utf-8")

    process_runner.run_streaming(
        [sys.executable, "-c", "print('fresh')"],
        stdout_path=stdout_path,
        timeout=60,
    )

    content = stdout_path.read_text(encoding="utf-8")
    assert "stale" not in content
    assert "fresh" in content


def _bridge_factory(root: Path) -> Any:
    from fantasy_agent.blender_mcp import BlenderMCPBridge
    from fantasy_agent.godot_mcp import GodotMCPBridge
    from fantasy_agent.unreal_mcp import UnrealMCPBridge

    return BlenderMCPBridge(root), GodotMCPBridge(root), UnrealMCPBridge(root)


@pytest.mark.parametrize("index", [0, 1, 2])
def test_local_tool_bridges_default_to_the_streaming_runner(tmp_path: Path, index: int):
    """Regression guard: defaulting back to subprocess.run loses all progress."""

    bridge = _bridge_factory(tmp_path)[index]
    assert process_runner.is_streaming_runner(bridge.runner)


def test_run_tool_streams_for_streaming_runners(tmp_path: Path):
    bridge = _bridge_factory(tmp_path)[1]
    stdout_path = tmp_path / "tool.stdout.log"
    stderr_path = tmp_path / "tool.stderr.log"

    result = bridge._run_tool(
        [sys.executable, "-c", "print('tool output')"],
        cwd=tmp_path,
        env={},
        timeout=60,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )

    assert result.returncode == 0
    assert "tool output" in stdout_path.read_text(encoding="utf-8")


def test_run_tool_hides_streaming_kwargs_from_legacy_runners(tmp_path: Path):
    """Injected fakes must never see keywords they cannot accept."""

    seen: list[dict[str, Any]] = []

    def legacy(command, **kwargs):
        seen.append(kwargs)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")

    bridge = _bridge_factory(tmp_path)[1]
    bridge.runner = legacy
    bridge._run_tool(
        ["cmd"],
        cwd=tmp_path,
        env={},
        timeout=5,
        stdout_path=tmp_path / "out.log",
        stderr_path=tmp_path / "err.log",
    )

    assert seen
    assert "stdout_path" not in seen[0]
    assert "cancel_event" not in seen[0]
    assert seen[0]["timeout"] == 5
