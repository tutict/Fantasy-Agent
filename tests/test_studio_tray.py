"""Guards for the tray behaviour in apps/studio/tray.py.

The behaviour under test is a decision, not a rendering: clicking the window's
X hides the window and leaves the app running, and only the tray menu quits.
Getting that backwards produces the two worst outcomes a tray app can have --
quitting when the user meant to minimise, or refusing to quit at all.

Everything here runs without a display and without pystray installed. The tray
icon is a stub, so what is asserted is "which window operation did we ask for,
and what did the closing handler return".

The closing handler's return value is the mechanism in full: pywebview's
`Event.set()` collects handler return values and the platform cancels the close
when any of them is `False`. So `False` means "cancel and hide" and `True` means
"let the window close".
"""

from __future__ import annotations

import importlib.util
import sys
import threading
import types
from pathlib import Path
from typing import Self

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TRAY_PATH = REPO_ROOT / "apps" / "studio" / "tray.py"


def _load_tray():
    """Import apps/studio/tray.py by path, registering it before exec.

    Same reason as the launcher tests: without the sys.modules entry, resolving
    string annotations fails.
    """
    module_name = "fantasy_agent_studio_tray"
    spec = importlib.util.spec_from_file_location(module_name, TRAY_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module


class _FakeEvents:
    def __init__(self) -> None:
        # An event that is already set, so the worker thread does not wait.
        self.shown = threading.Event()
        self.shown.set()
        self.closing = _FakeClosing([])


class _FakeClosing:
    """Stands in for `Event`, which supports the `+=` subscription form."""

    def __init__(self, handlers: list[object]) -> None:
        self._handlers = handlers

    @property
    def handlers(self) -> list[object]:
        return self._handlers

    def __iadd__(self, handler: object) -> Self:
        self._handlers.append(handler)
        return self

    def __add__(self, handler: object) -> Self:
        self._handlers.append(handler)
        return self

    def __isub__(self, handler: object) -> Self:
        if handler in self._handlers:
            self._handlers.remove(handler)
        return self


class _FakeWindow:
    def __init__(self) -> None:
        self.events = _FakeEvents()
        self.calls: list[str] = []

    def hide(self) -> None:
        self.calls.append("hide")

    def show(self) -> None:
        self.calls.append("show")

    def restore(self) -> None:
        self.calls.append("restore")

    def destroy(self) -> None:
        self.calls.append("destroy")


class _FakeIcon:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.stopped = False
        self.ran_detached = False

    def run_detached(self, setup: object = None) -> None:
        self.ran_detached = True

    def stop(self) -> None:
        self.stopped = True


def _install_pystray_stub(records: list[_FakeIcon]) -> types.ModuleType:
    """A pystray module that records icons instead of creating them."""

    class _MenuItem:
        def __init__(self, text: str, action: object, **kwargs: object) -> None:
            self.text = text
            self.action = action
            self.kwargs = kwargs

    class _Menu:
        SEPARATOR = object()

        def __init__(self, *items: object) -> None:
            self.items = items

    stub = types.ModuleType("pystray")
    stub.Icon = lambda *args, **kwargs: _collect(records, *args, **kwargs)  # type: ignore[attr-defined]
    stub.Menu = _Menu  # type: ignore[attr-defined]
    stub.MenuItem = _MenuItem  # type: ignore[attr-defined]
    return stub


def _collect(records: list[_FakeIcon], *args: object, **kwargs: object) -> _FakeIcon:
    icon = _FakeIcon(**kwargs)
    records.append(icon)
    return icon


def _wait_for(predicate, timeout: float = 5.0) -> bool:
    """Window operations run on a worker thread, so they need a join."""
    deadline = threading.Event()
    step = 0.02
    waited = 0.0
    while waited < timeout:
        if predicate():
            return True
        deadline.wait(step)
        waited += step
    return predicate()


# ---------------------------------------------------------------------------
# close interception
# ---------------------------------------------------------------------------


def test_closing_the_window_hides_it_instead_of_quitting():
    """The core promise of a tray app: X is not quit."""

    tray = _load_tray()
    controller = tray.TrayController()
    window = _FakeWindow()
    controller.attach_window(window)

    cancel = controller.close_requested()

    assert cancel is False, "returning False is what cancels the close"
    assert _wait_for(lambda: "hide" in window.calls), window.calls
    assert controller.is_quitting is False
    assert controller.is_hidden is True


def test_an_explicit_quit_lets_the_close_through():
    """The asymmetry that makes the app killable.

    If the handler cancelled unconditionally, the tray menu's quit would set the
    flag, destroy the window, and then the teardown would be cancelled too --
    leaving an app with no window and no way to quit it.
    """

    tray = _load_tray()
    controller = tray.TrayController()
    window = _FakeWindow()
    controller.attach_window(window)

    controller.request_quit()
    assert controller.close_requested() is True


def test_the_closing_event_is_cancellable_exactly_once_per_close():
    """A close must not be double-handled into a hide after a quit."""

    tray = _load_tray()
    controller = tray.TrayController()
    window = _FakeWindow()
    controller.attach_window(window)

    assert controller.close_requested() is False
    controller.request_quit()
    assert controller.close_requested() is True


def test_attaching_the_window_subscribes_to_the_close_event():
    tray = _load_tray()
    controller = tray.TrayController()
    window = _FakeWindow()

    controller.attach_window(window)

    assert list(window.events.closing.handlers) == [controller.close_requested]
    assert controller.window is window


# ---------------------------------------------------------------------------
# showing again
# ---------------------------------------------------------------------------


def test_showing_restores_before_showing():
    """`show()` alone leaves a minimised window minimised.

    The user may have minimised rather than closed before reaching for the tray,
    so restore() has to come first. Order is the assertion here, not presence.
    """

    tray = _load_tray()
    controller = tray.TrayController()
    window = _FakeWindow()
    controller.attach_window(window)

    controller.show_window()

    assert _wait_for(lambda: "show" in window.calls), window.calls
    assert window.calls.index("restore") < window.calls.index("show")
    assert controller.is_hidden is False


def test_window_operations_do_not_run_on_the_gui_thread():
    """The reason for the worker thread.

    Window calls block on the `shown` event, which the GUI thread sets. Waiting
    on the GUI thread would deadlock, so hide() must be dispatched elsewhere.
    """

    tray = _load_tray()
    controller = tray.TrayController()
    window = _FakeWindow()
    window.events.shown.clear()  # never ready -> the worker would block
    controller.attach_window(window)

    # Returns promptly instead of hanging: proof it is not running inline.
    controller.hide_window()
    assert window.calls == []

    # ...and the real work is queued behind the event, not lost.
    window.events.shown.set()
    assert _wait_for(lambda: "hide" in window.calls), window.calls


# ---------------------------------------------------------------------------
# the icon
# ---------------------------------------------------------------------------


def test_setup_starts_the_icon_detached_with_a_quit_item():
    tray = _load_tray()
    records: list[_FakeIcon] = []
    sys.modules["pystray"] = _install_pystray_stub(records)
    try:
        controller = tray.TrayController()
        window = _FakeWindow()
        icon = controller.setup(window, icon_dir=REPO_ROOT / "generated" / "desktop" / "icons")
    finally:
        del sys.modules["pystray"]

    assert icon.ran_detached, "run() would block the GUI thread; use run_detached()"
    assert controller.icon is icon
    assert icon.kwargs["title"] == tray.TRAY_TOOLTIP

    labels = [getattr(item, "text", None) for item in icon.kwargs["menu"].items]
    assert tray.TRAY_MENU_QUIT in labels
    assert tray.TRAY_MENU_SHOW in labels


def test_the_quit_menu_item_stops_the_icon_and_destroys_the_window():
    """Stopping the icon is what lets the process exit.

    pystray runs its own thread; without stop() it outlives the window and the
    interpreter never reaches the end of main().
    """

    tray = _load_tray()
    records: list[_FakeIcon] = []
    sys.modules["pystray"] = _install_pystray_stub(records)
    try:
        controller = tray.TrayController()
        window = _FakeWindow()
        controller.setup(window, icon_dir=REPO_ROOT / "generated" / "desktop" / "icons")
    finally:
        del sys.modules["pystray"]

    controller._on_quit_selected()

    assert controller.is_quitting is True
    assert controller.icon is not None
    assert controller.icon.stopped is True
    assert _wait_for(lambda: "destroy" in window.calls), window.calls


def test_request_quit_is_safe_before_the_icon_exists():
    """The launcher's finally-block calls this on every exit path."""

    tray = _load_tray()
    controller = tray.TrayController()
    controller.request_quit()  # must not raise
    assert controller.is_quitting is True


def test_a_failed_icon_leaves_no_close_hook_behind():
    """A half-set-up tray must not turn the fallback window into a trap.

    ``setup()`` subscribes the close hook *before* the icon exists; if the
    icon then fails, the shell falls back to a plain window while the hook
    still hides on close. No tray icon means nothing can ever show or quit
    the hidden window again -- the user's only way out is the task manager.
    The failure has to undo the subscription it already made.
    """

    tray = _load_tray()
    boom = types.ModuleType("pystray")

    # Menu/MenuItem must exist: setup() evaluates them as arguments before it
    # reaches Icon(), and this test is about the Icon() failure specifically.
    boom.Menu = lambda *items: items  # type: ignore[attr-defined]
    boom.MenuItem = lambda *args, **kwargs: (args, kwargs)  # type: ignore[attr-defined]
    boom.Menu.SEPARATOR = object()  # type: ignore[attr-defined]

    def _explode(*args: object, **kwargs: object) -> object:
        raise RuntimeError("no notification area in this session")

    boom.Icon = _explode  # type: ignore[attr-defined]
    sys.modules["pystray"] = boom
    try:
        controller = tray.TrayController()
        window = _FakeWindow()
        with pytest.raises(RuntimeError):
            controller.setup(window, icon_dir=REPO_ROOT / "generated" / "desktop" / "icons")
    finally:
        del sys.modules["pystray"]

    assert window.events.closing.handlers == [], (
        "a failed tray must not leave the close hook subscribed"
    )
    assert controller.window is None
    # The real window keeps no reference to the controller either way: the hook
    # lived on the window's event, and that subscription is what was undone.
    # (Calling close_requested() here would be meaningless -- it is the
    # *window's* event that decides close-vs-hide, not the bare controller.)


def test_the_tray_image_is_generated_not_committed():
    """Icons come from icons.py, so there is no binary in the repository."""

    source = TRAY_PATH.read_text(encoding="utf-8")
    assert "ensure_icons" in source
    assert ".png" not in source.replace("window_png", ""), (
        "the tray must load the generated icon through ensure_icons rather than "
        "naming a binary asset"
    )


def test_the_tray_does_not_import_pystray_at_module_scope():
    """Importing the module must not require the optional extra.

    The launcher imports TrayController unconditionally, so a module-scope
    pystray import would make the whole desktop shell unimportable on a machine
    without it -- including the smoke test and the test suite.
    """

    source = TRAY_PATH.read_text(encoding="utf-8")
    header = source.split('"""', 2)[2]
    assert "\nimport pystray" not in header
    assert "\nfrom pystray" not in header
