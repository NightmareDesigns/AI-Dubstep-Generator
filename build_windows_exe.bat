@echo off
cd /d "%~dp0"
py -m PyInstaller --noconfirm NightmareAIMusicMaker.spec
if errorlevel 1 exit /b %errorlevel%
echo.
echo Built dist\NightmareAIMusicMaker.exe
