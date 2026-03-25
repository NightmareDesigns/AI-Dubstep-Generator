from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_build_script_prefers_python_before_py_launcher():
    script = (REPO_ROOT / "build_windows_exe.bat").read_text().splitlines()
    script_text = "\n".join(script)

    python_index = script_text.index(
        'if not errorlevel 1 python -m PyInstaller --noconfirm "%SPEC%"'
    )
    py3_index = script_text.index(
        'if not errorlevel 1 py -3 -m PyInstaller --noconfirm "%SPEC%"'
    )
    py_index = script_text.index(
        'if not errorlevel 1 py -m PyInstaller --noconfirm "%SPEC%"'
    )

    assert python_index < py3_index < py_index
