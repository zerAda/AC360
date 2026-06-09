<#
.SYNOPSIS
Génère un package de release AC360 propre (sans artefacts dangereux) et VÉRIFIE
que le package final ne contient aucun fichier interdit (gate fail-closed).

.DESCRIPTION
Compatible Windows PowerShell 5.1 et PowerShell Core (Linux CI). N'utilise pas
cmd.exe. Échoue (exit 1) si un artefact interdit se retrouve dans le package —
permet de bloquer la CI. Génère un release_manifest.json.
#>
param(
    [string]$OutputDir = ".\release",
    [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"

# Motifs exclus de la copie (préfixe de chemin relatif OU nom de fichier).
$ExcludePatterns = @(
    ".git", ".github", ".claude", ".planning", ".pytest_cache", ".mypy_cache",
    "__pycache__", "*.pyc", "*.pyo", "*.pyd",
    "*.db", "*.sqlite", "*.sqlite3",
    ".env", "logs", "*.log",
    "temp_*.json", "final_audit_report.*",
    "Archives_Documentaires", "jobs",
    "test_audits.db",
    "*.docx", "*.xlsx", "*.xlsm", "*.csv", "*.tsv",
    "docs_content.txt", "matrice_content.*", "matrice_classement_clients.xlsx",
    ".mcs/botdefinition.json", ".mcs\botdefinition.json",
    "release", "release\*", "release/*"
)

# Gate fail-closed : extensions / dossiers JAMAIS autorisés dans le package final.
$ForbiddenExts = @(".pyc", ".pyo", ".pyd", ".db", ".sqlite", ".sqlite3",
                   ".log", ".docx", ".xlsx", ".xlsm", ".csv", ".tsv")
$ForbiddenNames = @(".env", "botdefinition.json", "test_audits.db", "docs_content.txt")
$ForbiddenDirSegments = @(".git", ".github", ".claude", ".planning", ".pytest_cache",
                          "__pycache__", "jobs", "Archives_Documentaires", "logs")

$Timestamp  = (Get-Date -Format "yyyyMMdd_HHmmss")
$PackageDir = Join-Path $OutputDir "AC360_$Timestamp"
$ZipPath    = "$PackageDir.zip"

Write-Host "=== AC360 Package Release ===" -ForegroundColor Cyan
Write-Host "Timestamp : $Timestamp"
Write-Host "Output    : $PackageDir"
if ($DryRun) { Write-Host "[DRY-RUN] Aucun fichier ne sera créé." -ForegroundColor Yellow }

$Source = (Get-Location).Path
$Files = Get-ChildItem -Recurse $Source | Where-Object {
    if ($_.PSIsContainer) { return $false }
    $rel = $_.FullName.Substring($Source.Length + 1)
    $relUnix = $rel -replace '\\', '/'
    foreach ($p in $ExcludePatterns) {
        $pUnix = $p -replace '\\', '/'
        if ($relUnix -like "$pUnix*" -or $_.Name -like $p) { return $false }
    }
    return $true
}

Write-Host ""
Write-Host "Fichiers à inclure : $($Files.Count)"

# --- Fonction de vérification fail-closed du package -----------------------
function Test-PackageClean {
    param([System.IO.FileInfo[]]$FileList, [string]$Base)
    $violations = @()
    foreach ($f in $FileList) {
        $rel = $f.FullName.Substring($Base.Length + 1)
        $relUnix = ($rel -replace '\\', '/')
        $ext = $f.Extension.ToLower()
        if ($ForbiddenExts -contains $ext) { $violations += $rel; continue }
        if ($ForbiddenNames -contains $f.Name) { $violations += $rel; continue }
        foreach ($seg in $ForbiddenDirSegments) {
            if ($relUnix -like "*/$seg/*" -or $relUnix -like "$seg/*") { $violations += $rel; break }
        }
    }
    return $violations
}

# Vérification AVANT copie sur la sélection.
$preViolations = Test-PackageClean -FileList $Files -Base $Source
if ($preViolations.Count -gt 0) {
    Write-Host "[ÉCHEC GATE] Artefacts interdits dans la sélection :" -ForegroundColor Red
    $preViolations | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    exit 1
}

if ($DryRun) {
    $Files | Select-Object -ExpandProperty FullName | ForEach-Object { Write-Host "  [SERAIT INCLUS] $_" }
    Write-Host "[DRY-RUN] Gate fail-closed : OK (aucun artefact interdit)." -ForegroundColor Green
    exit 0
}

New-Item -ItemType Directory -Force -Path $PackageDir | Out-Null
foreach ($f in $Files) {
    $rel  = $f.FullName.Substring($Source.Length + 1)
    $dest = Join-Path $PackageDir $rel
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    Copy-Item $f.FullName -Destination $dest -Force
}

# Vérification fail-closed APRÈS copie (sur le package réel).
$packaged = Get-ChildItem -Recurse $PackageDir -File
$postViolations = Test-PackageClean -FileList $packaged -Base $PackageDir
if ($postViolations.Count -gt 0) {
    Write-Host "[ÉCHEC GATE] Artefacts interdits dans le package :" -ForegroundColor Red
    $postViolations | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Remove-Item -Recurse -Force $PackageDir
    exit 1
}

# Manifest JSON.
$ManifestObj = [ordered]@{
    product    = "AC360"
    timestamp  = $Timestamp
    commit     = (git rev-parse --short HEAD 2>$null)
    file_count = $packaged.Count
    gate       = "clean"
    files      = ($packaged | ForEach-Object { $_.FullName.Substring($PackageDir.Length + 1) -replace '\\','/' })
}
$ManifestJson = $ManifestObj | ConvertTo-Json -Depth 4
$ManifestJson | Out-File (Join-Path $PackageDir "release_manifest.json") -Encoding utf8

Compress-Archive -Path $PackageDir -DestinationPath $ZipPath -Force
Write-Host "Package : $ZipPath ($($packaged.Count) fichiers)" -ForegroundColor Green
Write-Host "[GATE] Package vérifié propre (fail-closed)." -ForegroundColor Green
