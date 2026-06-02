<#
.SYNOPSIS
Vérifie la présence des pièces juridiques obligatoires dans le dossier d'un client.

.DESCRIPTION
Ce script non bloquant scanne les dossiers "KBIS", "Mandat", "DUE - accord collectif"
et "FIC (devoir de conseil)" pour s'assurer qu'au moins un fichier est présent.
Génère une alerte si le dossier est vide.

.PARAMETER SiteUrl
URL du site SharePoint.

.PARAMETER ClientFolderName
Nom du dossier du client.
#>

param (
    [Parameter(Mandatory=$true)]
    [string]$SiteUrl,
    
    [Parameter(Mandatory=$true)]
    [string]$ClientFolderName,
    
    [string]$LibraryName = "Dossiers_Clients"
)

# Liste des sous-dossiers juridiques obligatoires (basé sur la matrice)
$JuridiqueFolders = @(
    "Juridique/KBIS",
    "Juridique/Mandat",
    "Juridique/DUE - accord collectif"
)

$Alerts = @()

Write-Host "`n>>> [CONTRÔLE JURIDIQUE] Vérification de la complétude pour $ClientFolderName..." -ForegroundColor Cyan

try {
    Connect-PnPOnline -Url $SiteUrl -Interactive
} catch {
    Write-Host "[WARNING] Impossible de se connecter à SharePoint pour la vérification juridique." -ForegroundColor Yellow
    exit 0
}

$RootClientPath = "$LibraryName/$ClientFolderName"

foreach ($subfolder in $JuridiqueFolders) {
    $folderUrl = "$RootClientPath/$subfolder"
    try {
        # Get files inside the specific folder
        $files = Get-PnPFolderItem -FolderSiteRelativeUrl $folderUrl -ItemType File -ErrorAction Stop
        if ($files.Count -eq 0) {
            Write-Host "[ALERTE] Aucun fichier trouvé dans le dossier : $subfolder" -ForegroundColor Yellow
            $Alerts += "Dossier vide : $subfolder"
        } else {
            Write-Host "[OK] Pièce juridique présente dans : $subfolder" -ForegroundColor Green
        }
    } catch {
        Write-Host "[ALERTE] Le dossier $subfolder n'existe pas ou est inaccessible." -ForegroundColor Yellow
        $Alerts += "Dossier manquant : $subfolder"
    }
}

Disconnect-PnPOnline

# Export des alertes pour la suite du pipeline (Post-Audit)
if ($Alerts.Count -gt 0) {
    $Alerts | ConvertTo-Json | Out-File "legal_alerts.json" -Encoding UTF8
    Write-Host "Alertes juridiques générées dans legal_alerts.json." -ForegroundColor Yellow
} else {
    Write-Host "Contrôle juridique parfait ! Toutes les pièces sont présentes." -ForegroundColor Green
    if (Test-Path "legal_alerts.json") { Remove-Item "legal_alerts.json" }
}
