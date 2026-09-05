@echo off
title Media MultiTool
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ========================================================
    echo      Media MultiTool - Configuracao de Primeiro Uso
    echo ========================================================
    echo.

    where py >nul 2>&1
    if %errorlevel% neq 0 (
        where python >nul 2>&1
        if %errorlevel% neq 0 (
            echo [AVISO] Python nao foi encontrado no seu computador!
            echo.
            echo Deseja instalar o Python automaticamente pelo Windows Package Manager?
            set /p install_py="Instalar Python agora? (S/N): "
            if /i "%install_py%"=="S" (
                echo [INFO] Instalando Python 3.12...
                winget install Python.Python.3.12 -e
                echo.
                echo [INFO] Apos a instalacao ser concluida, feche e abra o start.bat novamente.
                pause
                exit /b 0
            ) else (
                echo Por favor, instale o Python manualmente em https://www.python.org/downloads/
                echo (Lembre-se de marcar a opcao "Add python.exe to PATH" ao instalar).
                pause
                exit /b 1
            )
        )
    )

    echo [INFO] Criando ambiente virtual Python...
    py -3 -m venv .venv 2>nul || python -m venv .venv

    echo [INFO] Instalando dependencias necessarias...
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
