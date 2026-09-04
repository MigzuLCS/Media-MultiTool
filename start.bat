@echo off
title Media MultiTool
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Criando ambiente virtual Python...
    py -3 -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
)

echo [INFO] Iniciando Media MultiTool...
start "" ".venv\Scripts\pythonw.exe" run.py
