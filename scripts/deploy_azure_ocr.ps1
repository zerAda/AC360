<#
.SYNOPSIS
Script de création de la ressource Azure AI Document Intelligence.

.DESCRIPTION
Ce script utilise Azure CLI (az) pour :
1. Se connecter à Azure (si non connecté).
2. Créer un Resource Group.
3. Déployer une ressource Azure Cognitive Services de type "FormRecognizer" (Document Intelligence).
4. Afficher l'Endpoint et les Clés nécessaires pour le code Python.

.NOTES
Assurez-vous d'avoir installé Azure CLI au préalable (https://aka.ms/installazurecliwindows)
#>

param(
    [string]$ResourceGroupName = "rg-ac360-ocr",
    [string]$Location = "westeurope",
    [string]$CognitiveServiceName = "cog-ac360-docintel",
    [string]$Sku = "S0"
)

Write-Host "Vérification de l'installation d'Azure CLI..." -ForegroundColor Cyan
if (-not (Get-Command "az" -ErrorAction SilentlyContinue)) {
    Write-Host "Erreur : Azure CLI n'est pas installé. Veuillez l'installer puis réessayer." -ForegroundColor Red
    exit 1
}

# Vérification de l'authentification
$azAccount = az account show --query "name" -o tsv 2>$null
if (-not $azAccount) {
    Write-Host "Vous n'êtes pas connecté à Azure. Lancement de la fenêtre de connexion..." -ForegroundColor Yellow
    az login | Out-Null
    $azAccount = az account show --query "name" -o tsv
}
Write-Host "Connecté à l'abonnement : $azAccount" -ForegroundColor Green

# Création du Resource Group
Write-Host "Création du groupe de ressources : $ResourceGroupName dans $Location..." -ForegroundColor Cyan
az group create --name $ResourceGroupName --location $Location | Out-Null

# Création de la ressource Document Intelligence
Write-Host "Déploiement de la ressource Document Intelligence : $CognitiveServiceName (SKU: $Sku)..." -ForegroundColor Cyan
az cognitiveservices account create `
    --name $CognitiveServiceName `
    --resource-group $ResourceGroupName `
    --kind FormRecognizer `
    --sku $Sku `
    --location $Location `
    --yes | Out-Null

# Récupération de l'Endpoint et des clés
Write-Host "Récupération des informations de connexion..." -ForegroundColor Cyan
$endpoint = az cognitiveservices account show --name $CognitiveServiceName --resource-group $ResourceGroupName --query "properties.endpoint" -o tsv
$key1 = az cognitiveservices account keys list --name $CognitiveServiceName --resource-group $ResourceGroupName --query "key1" -o tsv

Write-Host "`n=================================================" -ForegroundColor Magenta
Write-Host "DÉPLOIEMENT TERMINÉ AVEC SUCCÈS !" -ForegroundColor Green
Write-Host "Veuillez copier ces valeurs dans votre fichier .env :" -ForegroundColor Yellow
Write-Host "AZURE_OCR_ENDPOINT=$endpoint"
Write-Host "AZURE_OCR_KEY=$key1"
Write-Host "=================================================`n" -ForegroundColor Magenta
