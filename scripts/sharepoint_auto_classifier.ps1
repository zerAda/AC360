<#
.SYNOPSIS
    Script "Femme de Ménage" SharePoint (AC360 Auto-Classifier).
.DESCRIPTION
    Ce script scanne un dossier "Boîte de réception" (Inbox) sur SharePoint, analyse le nom des fichiers
    pour en déduire le nom du client, et déplace les fichiers vers le dossier du client correspondant.
    Si le dossier client n'existe pas, il le crée automatiquement.
    
    Version: Fast-Mode (Basé sur le nom de fichier, sans OCR).
#>

param(
    [string]$SiteUrl = "https://gerep.sharepoint.com/sites/AC360",
    [string]$InboxFolderUrl = "/sites/AC360/Shared Documents/Boite_De_Reception",
    [string]$TargetRootUrl = "/sites/AC360/Shared Documents/Clients - Documents",
    [string]$LogFile = "classification_report.csv",
    [string]$ClientId = $env:ENTRA_CLIENT_ID,
    [string]$ClientSecret = $env:ENTRA_CLIENT_SECRET
)

# 1. Connexion à SharePoint (Mode App-Only pour automatisation)
Write-Host "Connexion au site SharePoint : $SiteUrl" -ForegroundColor Cyan
try {
    if ([string]::IsNullOrEmpty($ClientId) -or [string]::IsNullOrEmpty($ClientSecret)) {
        Write-Host "[ERREUR] ClientId ou ClientSecret manquant. Le mode interactif est proscrit en production." -ForegroundColor Red
        exit 1
    }
    Connect-PnPOnline -Url $SiteUrl -ClientId $ClientId -ClientSecret $ClientSecret
} catch {
    Write-Host "[ERREUR] Échec de la connexion SharePoint. Veuillez vérifier vos accès." -ForegroundColor Red
    exit 1
}

# 2. Récupération des fichiers en vrac dans la boîte de réception
Write-Host "Analyse du dossier Inbox : $InboxFolderUrl" -ForegroundColor Yellow
$files = Get-PnPFolderItem -FolderSiteRelativeUrl $InboxFolderUrl -ItemType File

if ($files.Count -eq 0) {
    Write-Host "✅ Aucun document orphelin à classer. Le dossier est propre." -ForegroundColor Green
    exit 0
}

Write-Host "Trouvé $($files.Count) fichier(s) à classer." -ForegroundColor Yellow

$logData = @()

foreach ($file in $files) {
    $fileName = $file.Name
    Write-Host "`nTraitement de : $fileName" -ForegroundColor Cyan
    
    # 3. Extraction stricte du nom du client via Regex (Enterprise Grade)
    # Règle : (Contrat|Client|Avenant)_(Type)_<NomClient>_YYYY.pdf
    $clientName = "INCONNU"
    
    # Recherche stricte du NomClient avant l'année
    if ($fileName -match "(?i)^(?:Contrat|Devis|Avenant|Client)_[a-zA-Z0-9]+_(?<ClientName>[a-zA-Z0-9]+)_[0-9]{4}\.pdf$") {
        $clientName = $Matches['ClientName']
    } else {
        # Si le nom ne respecte pas la convention, on l'isole dans un dossier "À Vérifier Manuellement"
        $clientName = "_A_VERIFIER"
    }

    $targetFolderRelativeUrl = "$TargetRootUrl/$clientName"
    
    # 4. Vérification et Création du dossier client s'il n'existe pas
    try {
        $folderExists = Get-PnPFolder -Url $targetFolderRelativeUrl -ErrorAction Stop
    } catch {
        Write-Host "Création du nouveau dossier client : $clientName" -ForegroundColor Magenta
        Resolve-PnPFolder -SiteRelativePath $targetFolderRelativeUrl | Out-Null
    }

    # 5. Déplacement du fichier
    try {
        $sourceUrl = "$InboxFolderUrl/$fileName"
        $destUrl = $targetFolderRelativeUrl
        
        # [PATCH HATER] Prévention de la perte de données (Collision de fichiers)
        $existingFile = Get-PnPFile -Url "$destUrl/$fileName" -ErrorAction SilentlyContinue
        if ($existingFile) {
            $timestamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
            $newFileName = $fileName.Replace(".pdf", "_$timestamp.pdf")
            Write-Host "[WARNING] Le fichier existe déjà. Renommage en $newFileName pour éviter l'écrasement." -ForegroundColor Yellow
            
            # PnP PowerShell ne permet pas de renommer directement au déplacement, on renomme d'abord
            Rename-PnPFile -ServerRelativeUrl $sourceUrl -TargetFileName $newFileName -Force
            $sourceUrl = "$InboxFolderUrl/$newFileName"
            $fileName = $newFileName
        }
        
        Move-PnPFile -SourceUrl $sourceUrl -TargetUrl $destUrl
        Write-Host "➜ Déplacé avec succès vers : $destUrl/$fileName" -ForegroundColor Green
        
        $logData += [PSCustomObject]@{
            Date = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            FileName = $fileName
            DetectedClient = $clientName
            Status = "SUCCESS"
            TargetFolder = $targetFolderRelativeUrl
        }
    } catch {
        Write-Host "[ERREUR] Échec du déplacement pour $fileName : $_" -ForegroundColor Red
        $logData += [PSCustomObject]@{
            Date = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            FileName = $fileName
            DetectedClient = $clientName
            Status = "ERROR"
            TargetFolder = $targetFolderRelativeUrl
        }
    }
}

# 6. Export des logs
if ($logData.Count -gt 0) {
    $logData | Export-Csv -Path $LogFile -NoTypeInformation -Encoding UTF8 -Append -Delimiter ";"
    Write-Host "`nRapport de classement exporté vers : $LogFile" -ForegroundColor Cyan
}

Write-Host "--- Classement SharePoint Terminé ---" -ForegroundColor Green
