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

$Patterns = @(
    # Caches Python
    "$Root\**\__pycache__",
    "$Root\**\*.pyc",
    "$Root\**\*.pyo",

    # Bases de données locales
    "$Root\**\*.db",
    "$Root\**\*.sqlite",
    "$Root\**\*.sqlite3",

    # Logs
    "$Root\logs",
    "$Root\**\*.log",

    # Fichiers temporaires pipeline
    "$Root\**\temp_*.json",
    "$Root\**\final_audit_report.json",
    "$Root\**\final_audit_report.csv",

    # Répertoires jobs (UUID isolés)
    "$Root\jobs",

    # Archives documentaires locales
    "$Root\Archives_Documentaires"
)

$TotalDeleted = 0

foreach ($Pattern in $Patterns) {
    $Items = Get-Item -Path $Pattern -ErrorAction SilentlyContinue
    foreach ($Item in $Items) {
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

Write-Host "`n✅ Nettoyage terminé. $TotalDeleted élément(s) supprimé(s)." -ForegroundColor Green
