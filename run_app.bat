@echo off
REM Launches the correction app. Prefer the packaged runtime when present,
REM otherwise use the local virtual environment created during setup.

set "ROOT=%~dp0"
set "PYTHONW=%ROOT%runtime\pythonw.exe"

if not exist "%PYTHONW%" (
    set "PYTHONW=%ROOT%.venv\Scripts\pythonw.exe"
)

if not exist "%PYTHONW%" (
    echo Python runtime not found.
    echo Expected either:
    echo   %ROOT%runtime\pythonw.exe
    echo   %ROOT%.venv\Scripts\pythonw.exe
    pause
    exit /b 1
)

"%PYTHONW%" "%ROOT%app\main.py"
