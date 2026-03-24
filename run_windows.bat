@echo off
cd /d "%~dp0"
pyw -3 run_windows.pyw 2>nul
if not errorlevel 1 goto :eof
pythonw run_windows.pyw 2>nul
if not errorlevel 1 goto :eof
python run_windows.pyw
if errorlevel 1 pause
