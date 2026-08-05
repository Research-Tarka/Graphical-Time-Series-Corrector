<#
.SYNOPSIS
    Creates shortcuts that launch the correction app via run_app.bat.

.DESCRIPTION
    Run this after setup_runtime.ps1 (or any time afterwards - it is safe to
    re-run, it just overwrites the existing shortcuts).

    Creates one shortcut on the Desktop and one inside the project folder
    itself (next to run_app.bat).
#>

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$target = Join-Path $root "run_app.bat"
$icon = Join-Path $root "app\resources\app.ico"

if (-not (Test-Path $target)) {
    throw "run_app.bat not found at $target"
}

$shell = New-Object -ComObject WScript.Shell

$shortcutPaths = @(
    (Join-Path ([Environment]::GetFolderPath("Desktop")) "Correction series temporelles.lnk")
    (Join-Path $root "Lancer l application.lnk")
)

foreach ($shortcutPath in $shortcutPaths) {
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $target
    $shortcut.WorkingDirectory = $root
    $shortcut.Description = "Correction de series temporelles"
    if (Test-Path $icon) {
        $shortcut.IconLocation = $icon
    }
    $shortcut.Save()
    Write-Host "Shortcut created: $shortcutPath" -ForegroundColor Green
}
