Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

python -m pip install -e ".[dev]"
python -m PyInstaller `
  --noconfirm `
  --windowed `
  --name AnM `
  --additional-hooks-dir=. `
  annotate_and_merge.py

Write-Host "Build complete: $root\dist\AnM\AnM.exe"
