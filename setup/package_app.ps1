<#
.SYNOPSIS
    Crée une archive .zip prête à partager de l'application (app + runtime +
    lanceur), en excluant tout ce qui n'est pas nécessaire pour faire
    fonctionner l'application chez un utilisateur final (environnement de
    dev, caches, logs).

.DESCRIPTION
    Format .zip (et non .7z) délibérément : Windows sait l'ouvrir nativement
    (clic droit > Extraire tout), sans qu'un utilisateur final ait besoin
    d'installer 7-Zip ou un autre outil.

.USAGE
    powershell -ExecutionPolicy Bypass -File setup\package_app.ps1
    powershell -ExecutionPolicy Bypass -File setup\package_app.ps1 -OutputPath "D:\partage\correction_app.zip"
#>

param(
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$AppName = Split-Path -Leaf $ProjectRoot

if (-not $OutputPath) {
    $date = Get-Date -Format "yyyyMMdd"
    $OutputPath = Join-Path (Split-Path -Parent $ProjectRoot) "$AppName`_$date.zip"
}

if (Test-Path $OutputPath) {
    Remove-Item $OutputPath -Force
}

# Stage only what an end user needs into a temp folder, then zip that folder's
# contents (not the folder itself) so the archive extracts flat (run_app.bat
# at the archive root, not inside a wrapper folder).
$stageDir = Join-Path $env:TEMP "gtsc_package_stage_$(Get-Random)"
New-Item -ItemType Directory -Path $stageDir | Out-Null

Write-Host "Dossier source : $ProjectRoot"
Write-Host "Archive cible  : $OutputPath"
Write-Host "Dossier temporaire : $stageDir"

$excludeDirs = @(".venv", "__pycache__", ".git", "setup", "app\logs")
$excludeFiles = @("*.pyc")
$excludeTopLevelFiles = @(".gitignore", "RELEASING.md")

try {
    Get-ChildItem -Path $ProjectRoot -Force | ForEach-Object {
        $relativeExcluded = ($excludeDirs -contains $_.Name) -or ($excludeTopLevelFiles -contains $_.Name)
        if (-not $relativeExcluded) {
            Copy-Item -Path $_.FullName -Destination $stageDir -Recurse -Force
        }
    }

    # Second pass: remove any nested excluded dirs/files that got copied
    # (e.g. app\logs, __pycache__ inside app\, *.pyc anywhere).
    foreach ($dirName in $excludeDirs) {
        Get-ChildItem -Path $stageDir -Recurse -Directory -Filter $dirName -ErrorAction SilentlyContinue |
            ForEach-Object { Remove-Item $_.FullName -Recurse -Force }
    }
    foreach ($filePattern in $excludeFiles) {
        Get-ChildItem -Path $stageDir -Recurse -File -Filter $filePattern -ErrorAction SilentlyContinue |
            ForEach-Object { Remove-Item $_.FullName -Force }
    }

    Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $OutputPath -CompressionLevel Optimal
}
finally {
    Remove-Item $stageDir -Recurse -Force -ErrorAction SilentlyContinue
}

$size = (Get-Item $OutputPath).Length / 1MB
Write-Host ""
Write-Host ("Archive créée : {0} ({1:N1} Mo)" -f $OutputPath, $size)
Write-Host "Contenu : app\, runtime\, run_app.bat, README.md, LICENSE"
Write-Host "Exclus  : .venv, setup, .git, caches __pycache__, logs"
