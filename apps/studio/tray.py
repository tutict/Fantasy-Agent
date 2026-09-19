"""系统托盘：关闭窗口后应用留在托盘继续服务。

Why the tray lives in its own module
------------------------------------
The tray is a *policy* layer on top of the window, not part of it. Keeping it
separate means ``desktop.py`` stays a plain launcher that tests can drive
without a display, and the "what happens when the user clicks X" decision is in
one readable place.

The close button hides, it does not quit
----------------------------------------
Clicking the window's X hides the window and leaves the backend running; the
only ways out are the tray menu's "退出" item or an explicit
``request_quit()``. That is the behaviour Windows users expect from a tray app,
and for this tool it has a concrete payoff: the backend that took up to 90
seconds to become healthy stays warm instead of being rebuilt on every close.

Cancelling the close is the part that has teeth. pywebview's ``closing`` event
is an :class:`~webview.event.Event` whose handler return values decide whether
the platform cancels the close -- returning ``False`` cancels. The edge case
that bit: when the shell *itself* is quitting (tray menu, Ctrl+C, shutdown) the
event must be allowed to proceed, so :func:`TrayController.close_requested`
checks the quitting flag before it returns ``False``. Without that check the
app would hide itself instead of exiting and could never be shut down.

Threading model
---------------
``setup()`` runs on the GUI thread (it must -- it needs the window first), the
pystray icon owns a thread of its own, and the menu callbacks arrive on that
thread while the window functions must run on the GUI thread. Window calls are
therefore handed to a background thread: they block on the ``shown`` event,
which the GUI thread sets, so waiting on the GUI thread would deadlock.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any, Protocol

logger = logging.getLogger(__name__)

TRAY_TOOLTIP = "灵构工坊"
TRAY_MENU_SHOW = "打开主界面"
TRAY_MENU_QUIT = "退出"


class TrayIcon(Protocol):
    """The slice of ``pystray.Icon`` this module uses.

    Narrowing the dependency this far is what lets the tests pass a stub: the
    decisions worth testing are all "what did we ask the icon to do", and none
    of them need a real notification area.
    """

    def run_detached(self, setup: Callable[[Any], None] | None = None) -> None: ...

    def stop(self) -> None: ...


class TrayController:
    """Owns the window, the tray icon, and the quitting flag between them."""

    def __init__(self, tooltip: str = TRAY_TOOLTIP) -> None:
        self.tooltip = tooltip
        self._window: Any | None = None
        self._icon: TrayIcon | None = None
        self._quitting = False
        self._hidden = False

    # -- state ---------------------------------------------------------------

    @property
    def window(self) -> Any | None:
        """The webview window, once :meth:`attach_window` has run."""
        return self._window

    @property
    def icon(self) -> TrayIcon | None:
        """The tray icon, once :meth:`setup` has run."""
        return self._icon

    @property
    def is_quitting(self) -> bool:
        """True once the user has chosen to exit rather than hide."""
        return self._quitting

    @property
    def is_hidden(self) -> bool:
        """True while the window is hidden in the tray."""
        return self._hidden

    # -- wiring --------------------------------------------------------------

    def attach_window(self, window: Any) -> None:
        """Bind the window and subscribe to its close event."""
        self._window = window
        window.events.closing += self.close_requested

    def setup(self, window: Any, *, icon_dir: Any | None = None) -> TrayIcon:
        """Attach the window, build the icon, and start it on its own thread.

        Must be called after ``webview.start()`` has begun, because creating a
        window only registers it -- ``webview.start()`` is what binds the GUI
        and fires ``shown``. Called any earlier, the window calls below would
        sit and wait for an event that cannot fire yet.
        """
        # Imported here so importing this module (in tests, or on a machine
        # without the optional extra) stays cheap and dependency-free.
        import pystray

        if self._window is None:
            self.attach_window(window)

        self._icon = pystray.Icon(
            "fantasy-agent",
            icon=_tray_image(icon_dir),
            title=self.tooltip,
            menu=pystray.Menu(
                pystray.MenuItem(self.tooltip, None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(TRAY_MENU_SHOW, self._on_show_selected, default=True),
                pystray.MenuItem(TRAY_MENU_QUIT, self._on_quit_selected),
            ),
        )
        self._icon.run_detached()
        logger.info("tray icon started")
        return self._icon

    # -- close interception --------------------------------------------------

    def close_requested(self, *_: Any) -> bool:
        """Return ``False`` to cancel a window close and hide instead.

        Returning ``False`` is the cancel signal (see the module docstring).
        When the shell is already quitting this returns ``True`` so the close
        goes through, otherwise the app would be unkillable from its own menu.
        """
        if self._quitting:
            return True

        self.hide_window()
        return False

    def hide_window(self) -> None:
        """Hide the window without blocking the GUI thread."""
        self._hidden = True
        self._run_on_worker(self._do_hide)

    def show_window(self) -> None:
        """Bring the window back to the foreground."""
        self._hidden = False
        self._run_on_worker(self._do_show)

    # -- quitting ------------------------------------------------------------

    def request_quit(self) -> None:
        """Mark the shell as quitting and tear the tray icon down.

        Setting the flag first is load-bearing: every later close event will
        pass through instead of being cancelled. ``stop()`` matters for the same
        reason -- without it the tray icon's thread would keep the process
        alive after the window is gone.
        """
        self._quitting = True
        if self._icon is not None:
            self._icon.stop()
            logger.info("tray icon stopped")

    # -- pystray callbacks (run on the tray thread) --------------------------

    def _on_show_selected(self, *_: Any) -> None:
        self.show_window()

    def _on_quit_selected(self, *_: Any) -> None:
        self.request_quit()
        self._run_on_worker(self._do_destroy)

    # -- window operations (run on a worker thread) --------------------------

    def _do_hide(self) -> None:
        if self._window is None:
            return
        self._window.events.shown.wait(20)
        self._window.hide()

    def _do_show(self) -> None:
        if self._window is None:
            return
        self._window.events.shown.wait(20)
        # restore() first: a minimised window stays minimised through show().
        self._window.restore()
        self._window.show()

    def _do_destroy(self) -> None:
        if self._window is None:
            return
        self._window.events.shown.wait(20)
        self._window.destroy()

    @staticmethod
    def _run_on_worker(target: Callable[[], None]) -> None:
        threading.Thread(target=target, daemon=True).start()


def _tray_image(icon_dir: Any | None = None) -> Any:
    """The tray icon image, generated rather than shipped as a binary."""
    from PIL import Image

    from apps.studio.icons import ensure_icons

    paths = ensure_icons(icon_dir)
    return Image.open(paths["window_png"])
