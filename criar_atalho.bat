@echo off
title Criar Atalho - Media MultiTool
cd /d "%~dp0"

echo ========================================================
echo        Media MultiTool - Configurador de Atalhos
echo ========================================================
echo.

:: 1. Verificar se o icone existe
if not exist "assets\icon.ico" (
    echo [1/3] Gerando icones...
    if exist ".venv\Scripts\python.exe" (
        .venv\Scripts\python.exe generate_icon.py
    ) else (
        python generate_icon.py
    )
) else (
    echo [1/3] Icones verificados.
)

:: 2. Compilar executavel se nao existir
if not exist "Media MultiTool.exe" (
    echo [2/3] Compilando executavel inicializador...
    "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /target:winexe /win32icon:assets\icon.ico /out:"Media MultiTool.exe" launcher\launcher.cs
) else (
    echo [2/3] Executavel verificado.
)

:: 3. Criar atalhos via PowerShell script
echo [3/3] Criando atalhos no Menu Iniciar e Area de Trabalho...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher\create_shortcuts.ps1"

echo.
echo ========================================================
echo [SUCESSO] Atalhos configurados!
echo O aplicativo agora aparece na Pesquisa do Windows
echo (pressione a tecla Windows e digite 'Media MultiTool')
echo e tambem na sua Area de Trabalho.
echo ========================================================
echo.
pause
