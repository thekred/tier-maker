#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "Checking PyInstaller..."
python -m pip show pyinstaller *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing PyInstaller..."
    python -m pip install pyinstaller
}

Write-Host "Building TierMaker.exe (single file)..."
python -m PyInstaller `
    --noconfirm `
    --onefile `
    --name TierMaker `
    --add-data "static;static" `
    --hidden-import board `
    --hidden-import rawg `
    --hidden-import game_cache `
    --hidden-import paths `
    main.py

Write-Host ""
Write-Host "Done. Executable: $Root\dist\TierMaker.exe"
Write-Host "Runtime data (board, cache, API key): next to the executable in 'tier-maker-data' folder"
Write-Host "Place your RAWG key at: <exe_folder>\tier-maker-data\.rawg_key or set RAWG_API_KEY"
