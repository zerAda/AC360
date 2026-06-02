<#
.SYNOPSIS
Script de création de l'arborescence documentaire d'un dossier client sur SharePoint.

.DESCRIPTION
Ce script utilise PnP.PowerShell pour se connecter à un site SharePoint et générer 
la structure exacte issue de la matrice métier AC360 pour un client donné.
Si les dossiers parents n'existent pas, ils sont créés récursivement.

.PARAMETER SiteUrl
L'URL du site SharePoint cible. (ex: https://votre-tenant.sharepoint.com/sites/AC360)

.PARAMETER ClientFolderName
Le nom du dossier du client à créer (ex: CLI12345_ALPHA).

.PARAMETER LibraryName
Le nom interne de la bibliothèque de documents (par défaut: "Dossiers_Clients").
Si elle n'existe pas, elle peut être créée en amont.
#>

param (
    [Parameter(Mandatory=$true)]
    [string]$SiteUrl,
    
    [Parameter(Mandatory=$true)]
    [string]$ClientFolderName,
    
    [string]$LibraryName = "Dossiers_Clients"
)

# 1. Définition de la structure issue de la matrice
$TargetStructure = @(
    "Pilotage technique/Compte de résultats - stats assureurs - bilan de gestion",
    "Pièces contractuelles/Contrat - avenants",
    "Pièces contractuelles/Conditions générales - particulières",
    "Pièces contractuelles/Notice d’information",
    "Juridique/DUE - accord collectif",
    "Juridique/CCN",
    "Juridique/KBIS",
    "Juridique/FIC (devoir de conseil)",
    "Juridique/Mandat",
    "Juridique/Convention de courtage",
    "Juridique/Résiliation",
    "Juridique/Autres",
    "Commercial/Relation client/Bilan & Perspectives",
    "Commercial/Relation client/Présentation CSE",
    "Commercial/Relation client/Bilan de gestion",
    "Commercial/Relation client/Restitution audit et appels d’offres",
    "Commercial/Relation client/Propositions commerciales",
    "Commercial/Relation client/Accords dérogatoires assureurs",
    "Commercial/Relation client/Renouvellements actés",
    "Commercial/Etudes/Audit",
    "Commercial/Etudes/Appels d'offres",
    "Commercial/Etudes/Simulations - amélioration de garanties",
    "Commercial/Etudes/Analyses spécifiques (services ou autres)",
    "Commercial/Etudes/Mise en conformité CCN",
    "Commercial/Etudes/Cahier des charges",
    "Gestion/Données brutes/Fichier d'affiliation - radiation - portabilité - retraité",
    "Gestion/Données brutes/Extraction salariés (mailing)",
    "Gestion/Gestion courante/Guide de gestion",
    "Gestion/Gestion courante/Tableau de garanties excel",
    "Gestion/Gestion courante/BIA - Désignation de bénéficiaire - autres formulaires de gestion",
    "Gestion/Gestion courante/Bilan de gestion",
    "Gestion/Communication/Flyer de bienvenue",
    "Gestion/Communication/Affiches",
    "Gestion/Communication/Services (carnet des services)",
    "Gestion/Communication/Webinaire salariés"
)

# 2. Vérification du module PnP
if (-not (Get-Module -ListAvailable -Name PnP.PowerShell)) {
    Write-Host "Le module PnP.PowerShell n'est pas installé. Veuillez l'installer avec : Install-Module PnP.PowerShell" -ForegroundColor Red
    exit
}

# 3. Connexion au SharePoint
Write-Host "Connexion au site SharePoint : $SiteUrl" -ForegroundColor Cyan
Connect-PnPOnline -Url $SiteUrl -Interactive

# 4. Vérification/Création du dossier Client Racine
$RootClientPath = "$LibraryName/$ClientFolderName"
try {
    $null = Get-PnPFolder -Url $RootClientPath -ErrorAction Stop
    Write-Host "Le dossier racine du client existe déjà ($RootClientPath)." -ForegroundColor Yellow
} catch {
    Write-Host "Création du dossier racine du client : $ClientFolderName" -ForegroundColor Green
    $null = Add-PnPFolder -Name $ClientFolderName -Folder $LibraryName
}

# 5. Création de l'arborescence complète
Write-Host "Création de la structure métier en cours..." -ForegroundColor Cyan

foreach ($path in $TargetStructure) {
    # Découpage du chemin pour le créer récursivement
    $parts = $path -split "/"
    $currentParent = $RootClientPath
    
    foreach ($folderName in $parts) {
        $checkPath = "$currentParent/$folderName"
        try {
            $null = Get-PnPFolder -Url $checkPath -ErrorAction Stop
        } catch {
            Write-Host "  -> Création du dossier : $checkPath" -ForegroundColor DarkGray
            $null = Add-PnPFolder -Name $folderName -Folder $currentParent
        }
        # On descend d'un niveau pour la prochaine itération de sous-dossier
        $currentParent = $checkPath
    }
}

Write-Host "L'arborescence pour le client '$ClientFolderName' a été créée avec succès dans SharePoint !" -ForegroundColor Green
Disconnect-PnPOnline
