@echo off
title Build Media MultiTool
cd /d "%~dp0"

echo ========================================================
echo        Media MultiTool - Gerador de Pacote Portatil
echo ========================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual .venv nao encontrado!
    echo Execute start.bat primeiro para configurar o ambiente.
    pause
    exit /b 1
)

.venv\Scripts\python.exe build_portable.py
echo.
pause
