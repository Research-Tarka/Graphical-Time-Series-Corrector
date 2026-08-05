<#
.SYNOPSIS
    One-shot setup: downloads an embeddable Python runtime into ../runtime
    and installs the dependencies listed in requirements.txt.

.DESCRIPTION
    Run this once on a machine with internet access (it can be a different
    machine than the one that will run the app - just copy the whole
    `correction_app` folder afterwards, including `runtime/`).

    Re-run it after editing requirements.txt to add/update a dependency;
    it is safe to re-run (it recreates `runtime/`).

.NOTES
    Requires internet access. Does NOT require Python to be installed.
#>

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $root "runtime"
$requirementsFile = Join-Path $PSScriptRoot "requirements.txt"

$pyVersion = "3.12.7"
$pyZipUrl = "https://www.python.org/ftp/python/$pyVersion/python-$pyVersion-embed-amd64.zip"
$getPipUrl = "https://bootstrap.pypa.io/get-pip.py"

Write-Host "=== Correction app - runtime setup ===" -ForegroundColor Cyan

if (Test-Path $runtimeDir) {
    Write-Host "Removing existing runtime/ ..."
    Remove-Item -Recurse -Force $runtimeDir
}
New-Item -ItemType Directory -Path $runtimeDir | Out-Null

# --- 1. Download + extract the embeddable Python ------------------------
$zipPath = Join-Path $env:TEMP "python-$pyVersion-embed-amd64.zip"
Write-Host "Downloading embeddable Python $pyVersion ..."
Invoke-WebRequest -Uri $pyZipUrl -OutFile $zipPath

Write-Host "Extracting to $runtimeDir ..."
Expand-Archive -Path $zipPath -DestinationPath $runtimeDir -Force
Remove-Item $zipPath

# --- 2. Enable site-packages in the embeddable distribution --------------
# The embeddable distribution ships with a python3XX._pth file that disables
# `import site` and restricts sys.path. We need site-packages enabled so
# pip-installed packages (PyQt6, polars, ...) can be imported.
$pthFile = Get-ChildItem -Path $runtimeDir -Filter "python*._pth" | Select-Object -First 1
if (-not $pthFile) {
    throw "Could not find python*._pth in $runtimeDir"
}

# Build the _pth content explicitly: keep the zip, add site-packages, the app root, and enable site.
$pyTag = ($pyVersion -split '\.')[0..1] -join ''
@(
    "python$pyTag.zip"
    "."
    "Lib\site-packages"
    ""
    "import site"
) | Set-Content -Path $pthFile.FullName -Encoding ascii

Write-Host "Updated $($pthFile.Name) to enable site-packages."

# --- 3. Bootstrap pip ------------------------------------------------------
$getPipPath = Join-Path $runtimeDir "get-pip.py"
Write-Host "Downloading get-pip.py ..."
Invoke-WebRequest -Uri $getPipUrl -OutFile $getPipPath

$pythonExe = Join-Path $runtimeDir "python.exe"
Write-Host "Bootstrapping pip ..."
& $pythonExe $getPipPath --no-warn-script-location
Remove-Item $getPipPath

# --- 4. Install dependencies ----------------------------------------------
Write-Host "Installing dependencies from requirements.txt ..."
& $pythonExe -m pip install --no-warn-script-location -r $requirementsFile

Write-Host ""
Write-Host "=== Done. ===" -ForegroundColor Green
Write-Host "You can now run the app via run_app.bat or setup\create_shortcut.ps1"
