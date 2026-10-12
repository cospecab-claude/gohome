# gohome.exe build (output: dist\gohome.exe)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python icon.py
python -m PyInstaller --noconfirm --clean --onefile --noconsole `
    --name gohome `
    --icon gohome.ico `
    --hidden-import pystray._win32 `
    app.py

Write-Host "done: $PSScriptRoot\dist\gohome.exe"
