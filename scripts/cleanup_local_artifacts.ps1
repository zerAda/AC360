<#
.SYNOPSIS
Nettoie les artefacts locaux générés par le pipeline AC360 sans toucher au dépôt git.

.DESCRIPTION
Supprime les fichiers temporaires, journaux, bases de données locales et documents générés
qui ne doivent jamais être versionnés (conformément au .gitignore).
Ce script N'affecte PAS les fichiers versionnés dans git.

.EXAMPLE
.\cleanup_local_artifacts.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path $PSScriptRoot -Parent

Write-Host "`n🧹 Nettoyage des artefacts locaux AC360..." -ForegroundColor Cyan

# [PATCH HATER] Correction du nettoyeur inopérant : Remplacement de l'invalid globbing ** par Get-ChildItem -Recurse
$RecursivePatterns = @(
    "__pycache__", "*.pyc", "*.pyo",
    "*.db", "*.sqlite", "*.sqlite3", "*.log",
    "temp_*.json", "final_audit_report.json", "final_audit_report.csv"
)

$ExplicitPaths = @(
    "$Root\logs",
    "$Root\jobs",
    "$Root\Archives_Documentaires"
)

$TotalDeleted = 0

# Nettoyage récursif
foreach ($Pattern in $RecursivePatterns) {
    $Items = Get-ChildItem -Path $Root -Filter $Pattern -Recurse -Force -ErrorAction SilentlyContinue
    foreach ($Item in $Items) {
        # Si c'est un dossier et qu'on le supprime, ne pas essayer de supprimer ses enfants individuellement
        if (-not (Test-Path $Item.FullName)) { continue }
        
        try {
            if ($Item.PSIsContainer) {
                Remove-Item -Recurse -Force $Item.FullName
                Write-Host "  🗂️  Dossier supprimé : $($Item.FullName)" -ForegroundColor Yellow
            } else {
                Remove-Item -Force $Item.FullName
                Write-Host "  📄 Fichier supprimé : $($Item.FullName)" -ForegroundColor Yellow
            }
            $TotalDeleted++
        } catch {
            Write-Host "  ⚠️  Impossible de supprimer $($Item.FullName) : $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

# Nettoyage des dossiers racines explicites
foreach ($Path in $ExplicitPaths) {
    if (Test-Path $Path) {
        try {
            Remove-Item -Recurse -Force $Path
            Write-Host "  🗂️  Dossier racine supprimé : $Path" -ForegroundColor Yellow
            $TotalDeleted++
        } catch {
            Write-Host "  ⚠️  Impossible de supprimer $Path : $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

Write-Host "`n✅ Nettoyage terminé. $TotalDeleted élément(s) supprimé(s)." -ForegroundColor Green
