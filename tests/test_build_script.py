from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_build_script_prefers_python_before_py_launcher():
    script_text = (REPO_ROOT / "build_windows_exe.bat").read_text()
    command_pairs = [
        (
            r'python\s+-c\s+"import PyInstaller"\s+>nul\s+2>nul',
            r'if not errorlevel 1 python\s+-m PyInstaller --noconfirm "%SPEC%"',
        ),
        (
            r'py\s+-3\s+-c\s+"import PyInstaller"\s+>nul\s+2>nul',
            r'if not errorlevel 1 py\s+-3\s+-m PyInstaller --noconfirm "%SPEC%"',
        ),
        (
            r'py\s+-c\s+"import PyInstaller"\s+>nul\s+2>nul',
            r'if not errorlevel 1 py\s+-m PyInstaller --noconfirm "%SPEC%"',
        ),
    ]

    positions = []
    for probe_pattern, build_pattern in command_pairs:
        probe_match = re.search(probe_pattern, script_text)
        build_match = re.search(build_pattern, script_text)

        assert probe_match is not None
        assert build_match is not None
        assert probe_match.start() < build_match.start()

        positions.append(build_match.start())

    assert positions == sorted(positions)
