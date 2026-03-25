@echo off
cd /d "%~dp0"
py -3 "%~dp0run_windows.pyw" 2>nul
if not errorlevel 1 goto :eof
py "%~dp0run_windows.pyw" 2>nul
if not errorlevel 1 goto :eof
pythonw "%~dp0run_windows.pyw" 2>nul
if not errorlevel 1 goto :eof
python "%~dp0run_windows.pyw"
if errorlevel 1 pause
