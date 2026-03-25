@echo off
cd /d "%~dp0"
set "SPEC=NightmareAIMusicMaker.spec"

python -c "import PyInstaller" >nul 2>nul
if not errorlevel 1 python -m PyInstaller --noconfirm "%SPEC%"
if not errorlevel 1 goto :built

py -3 -c "import PyInstaller" >nul 2>nul
if not errorlevel 1 py -3 -m PyInstaller --noconfirm "%SPEC%"
if not errorlevel 1 goto :built

py -c "import PyInstaller" >nul 2>nul
if not errorlevel 1 py -m PyInstaller --noconfirm "%SPEC%"
if not errorlevel 1 goto :built

echo [ERROR] Unable to find a working Python interpreter with PyInstaller installed.
exit /b 1

:built
echo.
echo Built dist\NightmareAIMusicMaker.exe
