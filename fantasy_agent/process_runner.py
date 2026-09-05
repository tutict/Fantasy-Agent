"""Streaming subprocess helpers for long-running local tools.

Blender, Godot and Unreal runs take tens of seconds to minutes. Driving them
with ``subprocess.run(capture_output=True)`` buffers every byte until the
process exits, which leaves the UI with no progress and no way to stop a
runaway job.

This module keeps the familiar ``CompletedProcess`` return contract but
streams output to disk line by line and supports cooperative cancellation
through a context-local event, so no worker signature has to change to carry
a cancel flag down to the process boundary.
"""

from __future__ import annotations

import contextlib
import contextvars
import os
import signal
import subprocess
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path

LineSink = Callable[[str, str], None]

DEFAULT_POLL_INTERVAL = 0.2
TERMINATE_GRACE_SECONDS = 5.0
PUMP_JOIN_TIMEOUT = 5.0

STDOUT = "stdout"
STDERR = "stderr"


class ProcessCancelled(RuntimeError):
    """Raised when a streaming run is cancelled before the process exits."""

    def __init__(self, command: object, output: str = "", stderr: str = "") -> None:
        super().__init__(f"Process cancelled: {command}")
        self.command = command
        self.output = output
        self.stderr = stderr


_cancel_event: contextvars.ContextVar[threading.Event | None] = contextvars.ContextVar(
    "fantasy_agent_cancel_event", default=None
)


def bind_cancel_event(event: threading.Event | None) -> contextvars.Token:
    """Attach a cancel event to the current execution context."""

    return _cancel_event.set(event)


def current_cancel_event() -> threading.Event | None:
    """Return the cancel event for the current job, if any."""

    return _cancel_event.get()


def reset_cancel_event(token: contextvars.Token) -> None:
    """Restore the previous cancel event binding."""

    _cancel_event.reset(token)


@contextlib.contextmanager
def cancel_scope(event: threading.Event | None) -> Iterator[threading.Event | None]:
    """Bind ``event`` for the duration of the block."""

    token = bind_cancel_event(event)
    try:
        yield event
    finally:
        reset_cancel_event(token)


def terminate_process_tree(
    process: subprocess.Popen[str],
    *,
    grace_seconds: float = TERMINATE_GRACE_SECONDS,
) -> None:
    """Kill a process and every child it spawned.

    Windows has no process groups in the POSIX sense, so ``taskkill /T`` is
    used to walk the child tree. POSIX gets a graceful SIGTERM to the group
    first, escalating to SIGKILL only if it refuses to die.
    """

    if process.poll() is not None:
        return

    if os.name == "nt":
        _terminate_windows(process, grace_seconds=grace_seconds)
    else:
        _terminate_posix(process, grace_seconds=grace_seconds)

    if process.poll() is None:
        with contextlib.suppress(subprocess.TimeoutExpired, OSError):
            process.wait(timeout=grace_seconds)
    if process.poll() is None:
        with contextlib.suppress(OSError):
            process.kill()


def _terminate_windows(process: subprocess.Popen[str], *, grace_seconds: float) -> None:
    with contextlib.suppress(OSError, subprocess.SubprocessError):
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            check=False,
            timeout=max(grace_seconds, 1.0),
        )


def _terminate_posix(process: subprocess.Popen[str], *, grace_seconds: float) -> None:
    try:
        pgid = os.getpgid(process.pid)
    except OSError:
        pgid = None

    if pgid is None:
        with contextlib.suppress(OSError):
            process.terminate()
    else:
        with contextlib.suppress(OSError):
            os.killpg(pgid, signal.SIGTERM)

    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline and process.poll() is None:
        time.sleep(min(DEFAULT_POLL_INTERVAL, grace_seconds))

    if process.poll() is None:
        if pgid is None:
            with contextlib.suppress(OSError):
                process.kill()
        else:
            with contextlib.suppress(OSError):
                os.killpg(pgid, signal.SIGKILL)


def _truncate(path: Path | None) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def _join_lines(lines: list[str]) -> str:
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def _pump(
    stream: str,
    handle: object,
    path: Path | None,
    sink: list[str],
    lock: threading.Lock,
    on_line: LineSink | None,
) -> None:
    """Read one stream to completion, mirroring every line to disk."""

    log_file = None
    if path is not None:
        try:
            log_file = path.open("a", encoding="utf-8")
        except OSError:
            log_file = None
    sink_error: BaseException | None = None
    try:
        for line in handle:  # type: ignore[union-attr]
            text = line.rstrip("\n")
            with lock:
                sink.append(text)
            if log_file is not None:
                try:
                    log_file.write(text + "\n")
                    log_file.flush()
                except OSError:
                    log_file = None
            # A misbehaving sink must never abort the run, but it must not fail
            # silently either: a wrong-arity callback would otherwise look like
            # "the tool produced no output". Surface it once, then drop it.
            if sink_error is None and on_line is not None:
                try:
                    on_line(stream, text)
                except Exception as exc:  # noqa: BLE001 - sink must not break the run
                    sink_error = exc
                    with lock:
                        sink.append(f"[{stream}] output sink failed: {exc!r}")
    except (ValueError, OSError):
        pass
    finally:
        if log_file is not None:
            with contextlib.suppress(OSError):
                log_file.close()
        with contextlib.suppress(OSError, ValueError):
            handle.close()  # type: ignore[union-attr]


def run_streaming(
    command: Sequence[str],
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
    on_line: LineSink | None = None,
    cancel_event: threading.Event | None = None,
    encoding: str = "utf-8",
    errors: str = "replace",
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    capture_output: bool = True,
    text: bool = True,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run ``command`` while streaming its output to disk line by line.

    Returns the same ``CompletedProcess`` shape as ``subprocess.run``, so
    existing call sites keep working. Log files are truncated up front and
    written incrementally, which means ``tail -f`` shows progress while the
    tool is still running.

    Raises:
        FileNotFoundError: if the executable does not exist.
        subprocess.TimeoutExpired: if ``timeout`` elapses; carries whatever
            output was captured before the tree was killed.
        ProcessCancelled: if ``cancel_event`` is set before the process exits.
    """

    del capture_output, text, check  # accepted so this can replace subprocess.run

    _truncate(stdout_path)
    _truncate(stderr_path)

    process = subprocess.Popen(
        list(command),
        cwd=str(cwd) if cwd is not None else None,
        env=dict(env) if env is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding=encoding,
        errors=errors,
        bufsize=1,
    )

    lock = threading.Lock()
    captured: dict[str, list[str]] = {STDOUT: [], STDERR: []}
    pumps = [
        threading.Thread(
            target=_pump,
            args=(STDOUT, process.stdout, stdout_path, captured[STDOUT], lock, on_line),
            daemon=True,
        ),
        threading.Thread(
            target=_pump,
            args=(STDERR, process.stderr, stderr_path, captured[STDERR], lock, on_line),
            daemon=True,
        ),
    ]
    for pump in pumps:
        pump.start()

    event = cancel_event if cancel_event is not None else current_cancel_event()
    exited = _wait_for_exit(
        process,
        timeout=timeout,
        cancel_event=event,
        poll_interval=poll_interval,
    )

    cancelled = False
    timed_out = False
    if not exited:
        if event is not None and event.is_set():
            cancelled = True
        else:
            timed_out = True
        terminate_process_tree(process)

    for pump in pumps:
        pump.join(timeout=PUMP_JOIN_TIMEOUT)

    with lock:
        stdout_text = _join_lines(captured[STDOUT])
        stderr_text = _join_lines(captured[STDERR])

    if cancelled:
        raise ProcessCancelled(command, output=stdout_text, stderr=stderr_text)
    if timed_out:
        raise subprocess.TimeoutExpired(
            list(command),
            timeout if timeout is not None else 0,
            output=stdout_text,
            stderr=stderr_text,
        )

    return subprocess.CompletedProcess(
        args=list(command),
        returncode=int(process.returncode or 0),
        stdout=stdout_text,
        stderr=stderr_text,
    )


def _wait_for_exit(
    process: subprocess.Popen[str],
    *,
    timeout: float | None,
    cancel_event: threading.Event | None,
    poll_interval: float,
) -> bool:
    """Poll until the process exits, is cancelled, or times out.

    Returns True when the process exited on its own.
    """

    deadline = time.monotonic() + timeout if timeout is not None else None
    while process.poll() is None:
        if cancel_event is not None and cancel_event.is_set():
            return False
        if deadline is not None and time.monotonic() >= deadline:
            return False
        time.sleep(poll_interval)
    return True


run_streaming.fa_streaming = True  # type: ignore[attr-defined]


def is_streaming_runner(runner: object) -> bool:
    """True when ``runner`` supports the streaming keyword arguments.

    Tests inject plain ``(*args, **kwargs)`` fakes that return a
    ``CompletedProcess``; those must keep taking the legacy path untouched.
    """

    return bool(getattr(runner, "fa_streaming", False))
