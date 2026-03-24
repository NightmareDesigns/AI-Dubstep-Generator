"""GUI launcher for the Nightmare AI Music Maker.

Starts the Flask server in a background thread and opens a native desktop
window via pywebview so the app runs as a proper Windows desktop application.

Usage
-----
Double-click this file in Windows Explorer, or run::

    python gui.py
"""

import ctypes
import socket
import sys
import threading
import time

import webview

from app import app as flask_app

APP_TITLE = "Nightmare AI Music Maker"
APP_ID = "NightmareDesigns.AIDubstepGenerator"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_free_port() -> int:
    """Return an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_flask(port: int) -> None:
    """Run Flask in a background daemon thread (no reloader, no debug output)."""
    flask_app.run(host="127.0.0.1", port=port, use_reloader=False, debug=False)


def _wait_for_flask(port: int, timeout: float = 10.0) -> None:
    """Block until Flask is accepting connections or *timeout* seconds elapse."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"Flask did not start within {timeout:.0f}s")


def _set_windows_app_id() -> None:
    """Register an explicit AppUserModelID so Windows treats this as a GUI app."""
    if sys.platform != "win32":
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except (AttributeError, OSError):
        pass


def _show_error_dialog(message: str) -> None:
    """Display a native error dialog on Windows, falling back to stderr."""
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.MessageBoxW(None, message, APP_TITLE, 0x10)
            return
        except (AttributeError, OSError):
            pass

    print(message, file=sys.stderr)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    _set_windows_app_id()

    port = _find_free_port()

    server_thread = threading.Thread(
        target=_start_flask, args=(port,), daemon=True
    )
    server_thread.start()

    # Wait until Flask is ready before the window tries to load.
    _wait_for_flask(port)

    webview.create_window(
        title=APP_TITLE,
        url=f"http://127.0.0.1:{port}/",
        width=1040,
        height=860,
        resizable=True,
        min_size=(640, 600),
    )
    webview.start()


def launch() -> int:
    """Launch the desktop app and return a process exit code."""
    try:
        main()
        return 0
    except Exception as exc:  # noqa: BLE001
        _show_error_dialog(f"Unable to start {APP_TITLE}.\n\n{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(launch())
