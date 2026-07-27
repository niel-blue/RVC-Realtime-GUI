@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
start "" /b wscript.exe //B "%SCRIPT_DIR%app\RVC-Realtime-GUI.vbs"
exit /b
