"""
Tests for the GUI launcher (gui.py).

webview is mocked before the module is imported so these tests run in any
environment, including headless CI, without needing a physical display.
"""

import socket
import sys
import threading
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Install a module-level mock for 'webview' so that ``import gui`` succeeds
# in environments where pywebview is not installed / no display is available.
# ---------------------------------------------------------------------------
_webview_mock = MagicMock()
sys.modules["webview"] = _webview_mock

import gui  # noqa: E402 – must come after the mock is registered


# ---------------------------------------------------------------------------
# _find_free_port
# ---------------------------------------------------------------------------

class TestFindFreePort:

    def test_returns_integer(self):
        port = gui._find_free_port()
        assert isinstance(port, int)

    def test_port_in_valid_range(self):
        port = gui._find_free_port()
        assert 1024 < port < 65536

    def test_port_is_bindable(self):
        """The returned port must actually be free (bindable)."""
        port = gui._find_free_port()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))  # must not raise


# ---------------------------------------------------------------------------
# _start_flask
# ---------------------------------------------------------------------------

class TestWaitForFlask:

    def test_returns_once_port_is_open(self):
        """_wait_for_flask should return as soon as a listener appears."""
        port = gui._find_free_port()
        # Open a listener on that port so _wait_for_flask can connect.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.bind(("127.0.0.1", port))
            srv.listen(1)
            gui._wait_for_flask(port, timeout=2.0)  # must not raise or timeout

    def test_raises_on_timeout(self):
        """_wait_for_flask should raise RuntimeError if nothing ever starts."""
        port = gui._find_free_port()
        with pytest.raises(RuntimeError, match="did not start"):
            gui._wait_for_flask(port, timeout=0.1)


class TestStartFlask:

    def test_flask_responds_on_allocated_port(self):
        """Flask should serve HTTP 200 on the port we hand it."""
        import urllib.request

        port = gui._find_free_port()
        t = threading.Thread(target=gui._start_flask, args=(port,), daemon=True)
        t.start()
        gui._wait_for_flask(port, timeout=10.0)  # wait until Flask is ready

        response = urllib.request.urlopen(f"http://127.0.0.1:{port}/")
        assert response.status == 200


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

class TestMain:

    def setup_method(self):
        _webview_mock.reset_mock()

    def test_creates_window_with_correct_title(self):
        with patch.object(gui, "_start_flask"), \
             patch.object(gui, "_wait_for_flask"):
            gui.main()
        _webview_mock.create_window.assert_called_once()
        args, kwargs = _webview_mock.create_window.call_args
        title = args[0] if args else kwargs.get("title")
        assert title == "Nightmare AI Music Maker Dubstep Edition"

    def test_calls_webview_start(self):
        with patch.object(gui, "_start_flask"), \
             patch.object(gui, "_wait_for_flask"):
            gui.main()
        _webview_mock.start.assert_called_once()

    def test_window_meets_minimum_size(self):
        with patch.object(gui, "_start_flask"), \
             patch.object(gui, "_wait_for_flask"):
            gui.main()
        _, kwargs = _webview_mock.create_window.call_args
        assert kwargs.get("width", 0) >= 640
        assert kwargs.get("height", 0) >= 600

    def test_url_points_to_localhost(self):
        with patch.object(gui, "_start_flask"), \
             patch.object(gui, "_wait_for_flask"):
            gui.main()
        _, kwargs = _webview_mock.create_window.call_args
        url = kwargs.get("url", "")
        assert url.startswith("http://127.0.0.1:")

    def test_flask_thread_is_started(self):
        """_start_flask should be called exactly once (in a thread)."""
        with patch.object(gui, "_start_flask") as mock_flask, \
             patch.object(gui, "_wait_for_flask"):
            gui.main()
        mock_flask.assert_called_once()
