"""
Tests for the GUI launcher (gui.py).

webview is mocked before the module is imported so these tests run in any
environment, including headless CI, without needing a physical display.
"""

import socket
import sys
import threading
from types import SimpleNamespace
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


class TestWindowsHelpers:

    def test_set_windows_app_id_calls_shell32_on_windows(self, monkeypatch):
        shell32 = MagicMock()
        monkeypatch.setattr(gui.sys, "platform", "win32")
        monkeypatch.setattr(
            gui.ctypes,
            "windll",
            SimpleNamespace(shell32=shell32),
            raising=False,
        )

        gui._set_windows_app_id()

        shell32.SetCurrentProcessExplicitAppUserModelID.assert_called_once_with(
            gui.APP_ID
        )

    def test_show_error_dialog_uses_message_box_on_windows(self, monkeypatch):
        user32 = MagicMock()
        monkeypatch.setattr(gui.sys, "platform", "win32")
        monkeypatch.setattr(
            gui.ctypes,
            "windll",
            SimpleNamespace(user32=user32),
            raising=False,
        )

        gui._show_error_dialog("Boom")

        user32.MessageBoxW.assert_called_once_with(
            None, "Boom", gui.APP_TITLE, 0x10
        )


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

class TestMain:

    def setup_method(self):
        _webview_mock.reset_mock()

    def test_creates_window_with_correct_title(self):
        with patch.object(gui, "_set_windows_app_id"), \
             patch.object(gui, "_start_flask"), \
             patch.object(gui, "_wait_for_flask"):
            gui.main()
        _webview_mock.create_window.assert_called_once()
        args, kwargs = _webview_mock.create_window.call_args
        title = args[0] if args else kwargs.get("title")
        assert title == "Nightmare AI Music Maker"

    def test_calls_webview_start(self):
        with patch.object(gui, "_set_windows_app_id"), \
             patch.object(gui, "_start_flask"), \
             patch.object(gui, "_wait_for_flask"):
            gui.main()
        _webview_mock.start.assert_called_once()

    def test_window_meets_minimum_size(self):
        with patch.object(gui, "_set_windows_app_id"), \
             patch.object(gui, "_start_flask"), \
             patch.object(gui, "_wait_for_flask"):
            gui.main()
        _, kwargs = _webview_mock.create_window.call_args
        assert kwargs.get("width", 0) >= 640
        assert kwargs.get("height", 0) >= 600

    def test_url_points_to_localhost(self):
        with patch.object(gui, "_set_windows_app_id"), \
             patch.object(gui, "_start_flask"), \
             patch.object(gui, "_wait_for_flask"):
            gui.main()
        _, kwargs = _webview_mock.create_window.call_args
        url = kwargs.get("url", "")
        assert url.startswith("http://127.0.0.1:")

    def test_flask_thread_is_started(self):
        """_start_flask should be called exactly once (in a thread)."""
        with patch.object(gui, "_set_windows_app_id"), \
             patch.object(gui, "_start_flask") as mock_flask, \
             patch.object(gui, "_wait_for_flask"):
            gui.main()
        mock_flask.assert_called_once()

    def test_sets_windows_app_id_before_creating_window(self):
        with patch.object(gui, "_set_windows_app_id") as mock_set_app_id, \
             patch.object(gui, "_start_flask"), \
             patch.object(gui, "_wait_for_flask"):
            gui.main()
        mock_set_app_id.assert_called_once()


class TestLaunch:

    def test_returns_zero_when_main_succeeds(self):
        with patch.object(gui, "main") as mock_main:
            assert gui.launch() == 0
        mock_main.assert_called_once()

    def test_returns_one_and_shows_dialog_when_main_fails(self):
        with patch.object(gui, "main", side_effect=RuntimeError("boom")), \
             patch.object(gui, "_show_error_dialog") as mock_dialog:
            assert gui.launch() == 1

        mock_dialog.assert_called_once()
        assert "Unable to start" in mock_dialog.call_args.args[0]
        assert "boom" in mock_dialog.call_args.args[0]
