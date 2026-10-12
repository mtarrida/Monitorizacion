@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo No encuentro el entorno .venv en esta carpeta.
    echo Crealo con:  py -3.12 -m venv .venv ^&^& .venv\Scripts\python -m pip install -r requirements.txt
    pause
    exit /b 1
)
.venv\Scripts\python.exe servidor.py
pause
