<#
.SYNOPSIS
Génère un package de release AC360 propre (sans artefacts dangereux).
#>
param(
    [string]$OutputDir = ".\release",
    [switch]$DryRun = $false
)

$ExcludePatterns = @(
    ".git", "__pycache__", "*.pyc", "*.pyo",
    "*.db", "*.sqlite", "*.sqlite3",
    ".env", "logs", "*.log",
    "temp_*.json", "final_audit_report.*",
    "Archives_Documentaires", "jobs",
    "test_audits.db", "matrice_classement_clients.xlsx",
    "docs_content.txt", "matrice_content.*",
    "*.docx", ".mcs\botdefinition.json",
    # [PATCH HATER] Fix Release Bomb : Ne pas inclure l'ancien dossier release
    "release", "release\*", "release/*"
)

$Timestamp = (Get-Date -Format "yyyyMMdd_HHmmss")
$PackageDir = Join-Path $OutputDir "AC360_$Timestamp"
$ZipPath    = "$PackageDir.zip"

Write-Host "=== AC360 Package Release ==" -ForegroundColor Cyan
Write-Host "Timestamp : $Timestamp"
Write-Host "Output    : $PackageDir"
if ($DryRun) { Write-Host "[DRY-RUN] Aucun fichier ne sera créé." -ForegroundColor Yellow }

$Source = (Get-Location).Path
$Files = Get-ChildItem -Recurse $Source | Where-Object {
    $rel = $_.FullName.Substring($Source.Length + 1)
    $excluded = $false
    foreach ($p in $ExcludePatterns) {
        if ($rel -like "$p*" -or $_.Name -like $p) { $excluded = $true; break }
    }
    -not $excluded -and -not $_.PSIsContainer
}

Write-Host ""
Write-Host "Fichiers à inclure : $($Files.Count)"

if (-not $DryRun) {
    New-Item -ItemType Directory -Force -Path $PackageDir | Out-Null
    foreach ($f in $Files) {
        $rel = $f.FullName.Substring($Source.Length + 1)
        $dest = Join-Path $PackageDir $rel
        New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
        Copy-Item $f.FullName -Destination $dest -Force
    }
    
    # [PATCH HATER] Fix Ghost Manifest : Générer le manifeste AVANT de zipper
    $Manifest = Join-Path $PackageDir "RELEASE_MANIFEST.txt"
    "AC360 Release Manifest" | Out-File $Manifest
    "Timestamp : $Timestamp" | Add-Content $Manifest
    "Commit : $(git rev-parse --short HEAD 2>$null)" | Add-Content $Manifest
    "Fichiers : $($Files.Count)" | Add-Content $Manifest
    
    Compress-Archive -Path $PackageDir -DestinationPath $ZipPath -Force
    Write-Host "Package : $ZipPath" -ForegroundColor Green
} else {
    $Files | Select-Object -ExpandProperty FullName | ForEach-Object { Write-Host "  [SERAIT INCLUS] $_" }
}
