@echo off
rem Copia tu database.db (edificios, simulaciones y consumos) a la base de datos de la nube.
rem No modifica database.db. Pide la direccion de la base de datos (no se vera al escribirla).
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
python -m pip install -q -r requirements.txt
python -m energia.migrar database.db
pause
