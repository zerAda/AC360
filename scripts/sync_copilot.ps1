<#
.SYNOPSIS
Synchronise le bot Copilot Studio avec le dépôt local Git de manière robuste.

.DESCRIPTION
Gère automatiquement l'absence de workspace .pac en clonant dans un dossier temporaire
si nécessaire.
#>

param (
    [ValidateSet('Pull', 'Push')]
    [string]$Mode = 'Pull',

    [string]$CommitMessage = "Auto-sync: mise à jour du bot Copilot Studio depuis le Cloud"
)

# Identifiants d'environnement Dataverse / Bot : externalisés (pas de couplage
# tenant figé dans le script). Définir AC360_DATAVERSE_ENV_URL / AC360_BOT_ID.
$EnvironmentId = if ($env:AC360_DATAVERSE_ENV_URL) { $env:AC360_DATAVERSE_ENV_URL } else { "" }
$BotId = if ($env:AC360_BOT_ID) { $env:AC360_BOT_ID } else { "" }
if (-not $EnvironmentId -or -not $BotId) {
    Write-Host "Erreur: définissez AC360_DATAVERSE_ENV_URL et AC360_BOT_ID avant de lancer ce script." -ForegroundColor Red
    exit 1
}
$CopilotParentDir = Join-Path -Path $PSScriptRoot -ChildPath "..\src\copilot"
$CopilotProjectDir = Join-Path -Path $CopilotParentDir -ChildPath "AC360"

$pacCmd = "pac"
if (-not (Get-Command "pac" -ErrorAction SilentlyContinue)) {
    $pacPath = Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\PowerAppsCLI" -Filter "pac.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
    if ($pacPath) {
        $pacCmd = $pacPath
        Write-Host "Utilisation de pac depuis: $pacCmd" -ForegroundColor Cyan
    } else {
        Write-Host "Erreur: Le Power Platform CLI (pac) n'est pas installé." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Vérification de l'authentification..." -ForegroundColor Yellow
# On tente de voir si l'outil répond
& $pacCmd auth list | Out-Null

$TempCloneDir = Join-Path -Path $env:TEMP -ChildPath "AC360_Sync_$([guid]::NewGuid().ToString().Substring(0,8))"

function Sync-ViaTempClone {
    param([string]$Action)
    
    Write-Host "Création d'un workspace sain dans $TempCloneDir..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $TempCloneDir -Force | Out-Null
    Set-Location $TempCloneDir
    
    # 1. Clone initial du cloud vers le temp dir
    & $pacCmd copilot clone --bot $BotId --output-dir . --environment $EnvironmentId
    $TempProjectDir = Join-Path -Path $TempCloneDir -ChildPath "AC360"

    if (-not (Test-Path $TempProjectDir)) {
        Write-Host "Échec du clone. Vérifiez l'accès à Copilot Studio." -ForegroundColor Red
        Remove-Item -Recurse -Force $TempCloneDir
        exit 1
    }

    if ($Action -eq 'Pull') {
        # Copier du temp (Cloud) vers le repo Git
        Write-Host "Copie des fichiers du Cloud vers le dépôt Git local..." -ForegroundColor Cyan
        Copy-Item -Path "$TempProjectDir\*" -Destination $CopilotProjectDir -Recurse -Force
    }
    elseif ($Action -eq 'Push') {
        # Copier du repo Git vers le temp, puis push
        Write-Host "Copie des fichiers locaux vers le workspace pac..." -ForegroundColor Cyan
        Copy-Item -Path "$CopilotProjectDir\*" -Destination $TempProjectDir -Recurse -Force
        
        Set-Location $TempProjectDir
        & $pacCmd copilot push
    }

    # Cleanup
    Set-Location $PSScriptRoot
    Remove-Item -Recurse -Force $TempCloneDir -ErrorAction SilentlyContinue
}

if ($Mode -eq 'Pull') {
    Write-Host "Début du PULL..." -ForegroundColor Cyan
    if (-not (Test-Path $CopilotProjectDir)) {
        New-Item -ItemType Directory -Path $CopilotProjectDir -Force | Out-Null
    }
    
    Set-Location $CopilotProjectDir
    $pullOutput = & $pacCmd copilot pull 2>&1
    
    if ($pullOutput -match "No synced workspace found") {
        Write-Host "Workspace pac manquant, fallback sur le mode clone temporaire..." -ForegroundColor Yellow
        Sync-ViaTempClone -Action 'Pull'
    }

    Write-Host "Synchronisation Git en cours..." -ForegroundColor Cyan
    Set-Location $PSScriptRoot\..
    git add src/copilot

    # Ne pas commit si l'arbre est propre.
    $gitStatus = git status --porcelain src/copilot
    if ([string]::IsNullOrWhiteSpace($gitStatus)) {
        Write-Host "Aucune modification détectée dans Copilot Studio. Le dépôt est déjà à jour." -ForegroundColor Green
    } else {
        git commit -m $CommitMessage
        # Pas de push automatique vers main : l'opérateur revoit puis pousse.
        Write-Host "Modifications committées localement. Revoyez puis 'git push' manuellement." -ForegroundColor Green
    }
}
elseif ($Mode -eq 'Push') {
    Write-Host "Début du PUSH..." -ForegroundColor Cyan
    Set-Location $CopilotProjectDir
    $pushOutput = & $pacCmd copilot push 2>&1
    
    if ($pushOutput -match "No synced workspace found") {
        Write-Host "Workspace pac manquant, fallback sur le mode clone temporaire..." -ForegroundColor Yellow
        Sync-ViaTempClone -Action 'Push'
    }
    
    Write-Host "PUSH terminé !" -ForegroundColor Green
}
