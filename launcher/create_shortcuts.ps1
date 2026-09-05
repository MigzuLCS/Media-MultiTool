param (
    [string]$TargetDir = $PSScriptRoot
)

$baseDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$exePath = Join-Path $baseDir "Media MultiTool.exe"
$icoPath = Join-Path $baseDir "assets\icon.ico"

if (-not (Test-Path $exePath)) {
    Write-Host "[ERRO] Executavel nao encontrado: $exePath" -ForegroundColor Red
    exit 1
}

$wsh = New-Object -ComObject WScript.Shell

# 1. Menu Iniciar (para pesquisa do Windows)
$programsPath = [Environment]::GetFolderPath('Programs')
$startLnk = Join-Path $programsPath "Media MultiTool.lnk"
$shortcut = $wsh.CreateShortcut($startLnk)
$shortcut.TargetPath = $exePath
$shortcut.WorkingDirectory = $baseDir
$shortcut.IconLocation = "$icoPath,0"
$shortcut.Description = "Media MultiTool - Central de Midia Desktop"
$shortcut.Save()
Write-Host "[OK] Atalho criado no Menu Iniciar: $startLnk" -ForegroundColor Green

# 2. Area de Trabalho (Desktop)
$desktopPath = [Environment]::GetFolderPath('Desktop')
$deskLnk = Join-Path $desktopPath "Media MultiTool.lnk"
$dShortcut = $wsh.CreateShortcut($deskLnk)
$dShortcut.TargetPath = $exePath
$dShortcut.WorkingDirectory = $baseDir
$dShortcut.IconLocation = "$icoPath,0"
$dShortcut.Description = "Media MultiTool - Central de Midia Desktop"
$dShortcut.Save()
Write-Host "[OK] Atalho criado na Area de Trabalho: $deskLnk" -ForegroundColor Green
