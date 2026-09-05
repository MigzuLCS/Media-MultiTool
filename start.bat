@echo off
title Media MultiTool
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Criando ambiente virtual Python...
    py -3 -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
)

if not exist "assets\icon.ico" (
    echo [INFO] Gerando icones da aplicacao...
    .venv\Scripts\python.exe generate_icon.py
)

if not exist "Media MultiTool.exe" (
    echo [INFO] Compilando launcher executavel...
    "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /target:winexe /win32icon:assets\icon.ico /out:"Media MultiTool.exe" launcher\launcher.cs
)

echo [INFO] Iniciando Media MultiTool...
start "" ".venv\Scripts\pythonw.exe" run.py
