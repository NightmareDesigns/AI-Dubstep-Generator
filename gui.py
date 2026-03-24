"""GUI launcher for the AI Dubstep Generator.

Starts the Flask server in a background thread and opens a native desktop
window via pywebview so the app runs as a proper Windows desktop application.

Usage
-----
Double-click this file in Windows Explorer, or run::

    python gui.py
"""

import socket
import threading
import time

import webview

from app import app as flask_app

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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    port = _find_free_port()

    server_thread = threading.Thread(
        target=_start_flask, args=(port,), daemon=True
    )
    server_thread.start()

    # Wait until Flask is ready before the window tries to load.
    _wait_for_flask(port)

    webview.create_window(
        title="AI Dubstep Generator",
        url=f"http://127.0.0.1:{port}/",
        width=1040,
        height=860,
        resizable=True,
        min_size=(640, 600),
    )
    webview.start()


if __name__ == "__main__":
    main()
