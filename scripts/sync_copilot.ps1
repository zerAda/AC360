<#
.SYNOPSIS
Synchronise le bot Copilot Studio (c82f127c-8f47-f111-bec6-000d3ab9a512) avec le dépôt local Git.

.DESCRIPTION
Ce script permet de :
1. S'authentifier sur l'environnement Default-f7d2b917-8798-45ee-b57c-d7c3421f3ac0.
2. En mode 'Pull' : Télécharger ou mettre à jour le code source du bot depuis le cloud, puis faire un commit/push automatique vers Git.
3. En mode 'Push' : Envoyer vos modifications locales vers le cloud Copilot Studio.

.PARAMETER Mode
Le mode de synchronisation : 'Pull' (Cloud vers Local) ou 'Push' (Local vers Cloud). Par défaut : 'Pull'.

.PARAMETER CommitMessage
Message utilisé pour le commit automatique lors d'un Pull.
#>

param (
    [ValidateSet('Pull', 'Push')]
    [string]$Mode = 'Pull',

    [string]$CommitMessage = "Auto-sync: mise à jour du bot Copilot Studio depuis le Cloud"
)

$EnvironmentId = "https://org2cf282f3.crm4.dynamics.com"
$BotId = "c82f127c-8f47-f111-bec6-000d3ab9a512"
$CopilotParentDir = Join-Path -Path $PSScriptRoot -ChildPath "..\src\copilot"
$CopilotProjectDir = Join-Path -Path $CopilotParentDir -ChildPath "AC360"

$pacCmd = "pac"
if (-not (Get-Command "pac" -ErrorAction SilentlyContinue)) {
    # Attempt to find pac.exe in local app data
    $pacPath = Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\PowerAppsCLI" -Filter "pac.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
    if ($pacPath) {
        $pacCmd = $pacPath
        Write-Host "Utilisation de pac depuis: $pacCmd" -ForegroundColor Cyan
    } else {
        Write-Host "Erreur: Le Power Platform CLI (pac) n'est pas reconnu dans ce terminal et n'a pas été trouvé dans LocalAppData." -ForegroundColor Red
        Write-Host "S'il vient d'être installé, fermez ce terminal et rouvrez-en un nouveau." -ForegroundColor Yellow
        exit 1
    }
}

# 1. Authentification
Write-Host "Assurez-vous d'être authentifié via 'pac auth create' si ce n'est pas déjà fait." -ForegroundColor Yellow

# 2. Synchronisation
if ($Mode -eq 'Pull') {
    Write-Host "Début du PULL : Téléchargement du bot depuis Copilot Studio..." -ForegroundColor Cyan
    
    if (-not (Test-Path $CopilotProjectDir)) {
        Write-Host "Premier téléchargement, utilisation de 'clone'..." -ForegroundColor Cyan
        if (-not (Test-Path $CopilotParentDir)) { New-Item -ItemType Directory -Path $CopilotParentDir | Out-Null }
        Set-Location $CopilotParentDir
        & $pacCmd copilot clone --bot $BotId --output-dir . --environment $EnvironmentId
    } else {
        Write-Host "Dossier existant, utilisation de 'pull'..." -ForegroundColor Cyan
        Set-Location $CopilotProjectDir
        & $pacCmd copilot pull
    }

    if ($LASTEXITCODE -eq 0) {
        Write-Host "PULL réussi." -ForegroundColor Green
        
        Write-Host "Synchronisation Git en cours..." -ForegroundColor Cyan
        Set-Location $PSScriptRoot\..
        git add src/copilot
        git commit -m $CommitMessage
        git push
        Write-Host "Synchronisation locale et Git terminée avec succès." -ForegroundColor Green
    } else {
        Write-Host "Erreur lors du pull/clone." -ForegroundColor Red
    }
}
elseif ($Mode -eq 'Push') {
    Write-Host "Début du PUSH : Envoi du code local vers Copilot Studio..." -ForegroundColor Cyan
    
    if (-not (Test-Path $CopilotProjectDir)) {
        Write-Host "Erreur: Le dossier du bot ($CopilotProjectDir) n'existe pas. Veuillez faire un PULL d'abord." -ForegroundColor Red
        exit 1
    }

    Set-Location $CopilotProjectDir
    & $pacCmd copilot push

    if ($LASTEXITCODE -eq 0) {
        Write-Host "PUSH réussi ! Le bot sur Copilot Studio a été mis à jour." -ForegroundColor Green
    } else {
        Write-Host "Erreur lors du push vers le Cloud." -ForegroundColor Red
    }
}
