@echo off
rem Crea la linea de un usuario (usuario y contrasena) para pegarla en los Secrets de la app online.
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
python -m energia.auth
pause
