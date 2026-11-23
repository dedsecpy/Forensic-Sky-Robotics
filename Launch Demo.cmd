@echo off
cd /d "%~dp0"
set "PYTHONPATH=%~dp0.venv\Lib\site-packages"
set "PY=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0demo.py"
if errorlevel 1 pause
