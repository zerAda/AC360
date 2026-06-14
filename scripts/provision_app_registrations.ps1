<#
.SYNOPSIS
Provisionnement idempotent des deux enregistrements d'application Entra de production (INF-05 / INF-06).

.DESCRIPTION
Ce script utilise Azure CLI (az) pour créer, de façon idempotente (check-then-create par displayName) :

1. L'application "audience API" (AC360-API-prod) : expose le scope délégué `Audit.Trigger`,
   porte l'URI d'identification `api://<appId>` et NE possède AUCUN secret (INF-05).
2. Le client confidentiel OBO (AC360-OBO-prod) : reçoit les scopes Microsoft Graph délégués
   (résolus à l'exécution depuis le service principal Graph vivant — jamais codés en dur),
   génère un secret stocké UNIQUEMENT dans Key Vault, et demande le consentement administrateur (INF-06).

Les objets d'application Entra et le consentement ne sont pas des ressources ARM : ce script est
le complément impératif de l'IaC Bicep.

.NOTES
- Le secret OBO n'est JAMAIS écrit dans un fichier ni affiché dans les logs : il transite en mémoire
  puis est écrit dans Key Vault (`az keyvault secret set ... 1>$null`) avant d'être effacé (`$secret = $null`).
- Le consentement administrateur exige une identité Global Admin / Privileged Role Administrator dans le
  tenant de production GEREP. Le `admin-consent` émis ici est la demande ; la vérification du grant vivant
  est un point de contrôle opérateur bloquant (plan 02-04) via `az ad app permission list-grants`.
- Prérequis : Azure CLI installé (https://aka.ms/installazurecliwindows).
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$KeyVaultName,
    [string]$ApiAppName = 'AC360-API-prod',
    [string]$OboAppName = 'AC360-OBO-prod',
    [int]$SecretYears = 1,
    # WR-06 : login interactif INTERDIT par défaut (fail-closed). L'orchestrateur provision.ps1
    # authentifie déjà en amont ; ce script ne doit pas relancer un `az login` silencieux en CI.
    [switch]$Interactive
)

$ErrorActionPreference = "Stop"

# --- Garde : présence d'Azure CLI + authentification (analogue deploy_azure_ocr.ps1 lignes 23-36) ---
Write-Host "Vérification de l'installation d'Azure CLI..." -ForegroundColor Cyan
if (-not (Get-Command "az" -ErrorAction SilentlyContinue)) {
    Write-Host "Erreur : Azure CLI n'est pas installé. Veuillez l'installer puis réessayer." -ForegroundColor Red
    exit 1
}

$azAccount = az account show --query "name" -o tsv 2>$null
if (-not $azAccount) {
    # WR-06 : fail-closed sauf -Interactive (pas de prompt navigateur silencieux en automation).
    if ($Interactive) {
        Write-Host "Non authentifié. Lancement du `az login` interactif (-Interactive)..." -ForegroundColor Yellow
        az login | Out-Null
        $azAccount = az account show --query "name" -o tsv
    } else {
        throw "Non authentifié à Azure. Exécuter 'az login' (tenant PROD) puis relancer, ou passer -Interactive."
    }
}
Write-Host "Connecté à l'abonnement : $azAccount" -ForegroundColor Green

# ============================================================================
# (1) Application audience API (INF-05) — AUCUN secret
# ============================================================================
Write-Host "Vérification / création de l'application audience API : $ApiAppName..." -ForegroundColor Cyan
$apiAppId = az ad app list --filter "displayName eq '$ApiAppName'" --query "[0].appId" -o tsv
if (-not $apiAppId) {
    Write-Host "  -> création de $ApiAppName" -ForegroundColor Yellow
    $apiAppId = az ad app create --display-name $ApiAppName --sign-in-audience AzureADMyOrg --query appId -o tsv
}
else {
    Write-Host "  -> $ApiAppName existe déjà (appId réutilisé)" -ForegroundColor Green
}

# URI d'identification : les jetons portent l'audience api://<appId>
az ad app update --id $apiAppId --identifier-uris "api://$apiAppId" --only-show-errors | Out-Null

# Exposer le scope délégué Audit.Trigger (api.oauth2PermissionScopes).
# On préserve l'idempotence : on ne (re)définit le scope que s'il est absent.
$existingScope = az ad app show --id $apiAppId --query "api.oauth2PermissionScopes[?value=='Audit.Trigger'].id | [0]" -o tsv
if (-not $existingScope) {
    Write-Host "  -> exposition du scope délégué Audit.Trigger" -ForegroundColor Yellow
    $scopeId = [guid]::NewGuid().ToString()
    $apiManifest = @{
        oauth2PermissionScopes = @(
            @{
                id                      = $scopeId
                adminConsentDescription = "Permet à l'application de déclencher un audit AC360 au nom de l'utilisateur connecté."
                adminConsentDisplayName = "Déclencher un audit AC360"
                isEnabled               = $true
                type                    = "User"
                userConsentDescription  = "Permet de déclencher un audit AC360 en votre nom."
                userConsentDisplayName  = "Déclencher un audit AC360"
                value                   = "Audit.Trigger"
            }
        )
    }
    $apiManifestJson = $apiManifest | ConvertTo-Json -Depth 5 -Compress
    # Écriture via fichier temporaire JSON (pas de secret ici) pour fiabilité cross-plateforme.
    $tmp = New-TemporaryFile
    Set-Content -Path $tmp -Value $apiManifestJson -Encoding utf8
    az ad app update --id $apiAppId --set "api=@$tmp" --only-show-errors | Out-Null
    Remove-Item $tmp -Force
}
else {
    Write-Host "  -> scope Audit.Trigger déjà exposé" -ForegroundColor Green
}

# IMPORTANT (INF-05 / T-02-07) : l'application audience API ne reçoit JAMAIS de credential.
# Aucun `az ad app credential reset` n'est émis pour $apiAppId.

# ============================================================================
# (2) Client confidentiel OBO (INF-05 / INF-06) — secret -> Key Vault
# ============================================================================
$graph = '00000003-0000-0000-c000-000000000000'  # Microsoft Graph (appId well-known)

Write-Host "Vérification / création du client confidentiel OBO : $OboAppName..." -ForegroundColor Cyan
$oboAppId = az ad app list --filter "displayName eq '$OboAppName'" --query "[0].appId" -o tsv
if (-not $oboAppId) {
    Write-Host "  -> création de $OboAppName" -ForegroundColor Yellow
    $oboAppId = az ad app create --display-name $OboAppName --sign-in-audience AzureADMyOrg --query appId -o tsv
}
else {
    Write-Host "  -> $OboAppName existe déjà (appId réutilisé)" -ForegroundColor Green
}

# S'assurer que le service principal OBO existe (sinon AADSTS65001 — RESEARCH Pitfall 5 / T-02-06).
$oboSpId = az ad sp list --filter "appId eq '$oboAppId'" --query "[0].id" -o tsv
if (-not $oboSpId) {
    Write-Host "  -> création du service principal pour $OboAppName" -ForegroundColor Yellow
    az ad sp create --id $oboAppId --only-show-errors | Out-Null
}

# Résolution des GUID de scope délégués depuis le SP Graph VIVANT (tenant-correct, jamais codé en dur).
function Get-Scope($v) {
    az ad sp show --id $graph --query "oauth2PermissionScopes[?value=='$v'].id | [0]" -o tsv
}

# Scopes délégués least-privilege (T-02-05) : lecture SharePoint, écriture Planner (FIC), refresh OBO, identité.
#
# WR-02 — EXCEPTION READ-ONLY DOCUMENTÉE : `Tasks.ReadWrite` est un scope d'ÉCRITURE délégué. La
# garantie "read-only" d'AC360 porte sur les DONNÉES CLIENT / SharePoint (aucune modification des
# dossiers client) — PAS sur Microsoft Planner. La création d'une tâche Planner de relance FIC est une
# action produit DOCUMENTÉE (scripts/planner_integration.py, endpoint /api/planner/task, topic
# src/copilot/AC360/topics/CreerRelancePlanner.mcs.yml). Ce scope d'écriture DOIT être recensé dans la
# preuve DPIA/SEC (Phase 5, RGP-01/SEC-03) comme exception explicite au principe read-only.
$scopes = 'Files.Read.All', 'Sites.Read.All', 'Tasks.ReadWrite', 'offline_access', 'User.Read'

# WR-04 : résolution ATOMIQUE — on résout et valide TOUS les GUID d'abord, puis on émet UN SEUL
# `az ad app permission add` (batch). Si un scope manque, on `throw` AVANT toute mutation, évitant un
# tenant à demi-provisionné (le message indique quel scope / quel tenant).
Write-Host "Résolution des scopes Microsoft Graph délégués (atomique)..." -ForegroundColor Cyan
$resolved = @()
$missing = @()
foreach ($s in $scopes) {
    $gid = Get-Scope $s
    if (-not $gid) { $missing += $s } else { $resolved += "$gid=Scope" }
}
if ($missing.Count -gt 0) {
    throw "Scopes Graph délégués irrésolus dans ce tenant ($azAccount) : $($missing -join ', '). Aucune permission ajoutée (résolution atomique WR-04)."
}
Write-Host "  -> demande groupée des scopes : $($scopes -join ', ')" -ForegroundColor Yellow
az ad app permission add --id $oboAppId --api $graph --api-permissions $resolved --only-show-errors | Out-Null

# Génération du secret OBO et stockage UNIQUEMENT dans Key Vault (jamais dans un fichier ni un log).
Write-Host "Génération du secret OBO et stockage dans Key Vault ($KeyVaultName)..." -ForegroundColor Cyan
$secret = az ad app credential reset --id $oboAppId --append --display-name 'obo-prod' --years $SecretYears --query password -o tsv

# WR-01 : $ErrorActionPreference="Stop" ne rend PAS les codes retour non-zéro des commandes natives (az)
# terminants. Sans cette garde, un `credential reset` échoué/vide écrirait un secret VIDE dans Key Vault
# (panne d'auth prod silencieuse et difficile à diagnostiquer). Fail-closed AVANT toute écriture KV.
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($secret)) {
    $secret = $null
    throw "Echec du reset de credential OBO (code=$LASTEXITCODE) ou secret vide — abandon AVANT l'écriture Key Vault (WR-01)."
}

# Masquage CI/CD AVANT toute écriture (adapté de deploy_azure_ocr.ps1 lignes 57-61).
if ($env:GITHUB_ACTIONS -eq "true") {
    Write-Host "::add-mask::$secret"
}
# IN-03 : masque Azure DevOps émis UNIQUEMENT sous Azure DevOps ($env:TF_BUILD='True'), symétrique au
# garde GitHub — évite de placer la valeur dans un Write-Host hors d'un contexte de masquage réel.
if ($env:TF_BUILD -eq 'True') {
    Write-Host "##vso[task.setsecret]$secret"
}

# Le secret transite UNIQUEMENT vers Key Vault — sortie supprimée, puis variable effacée (T-02-04).
az keyvault secret set --vault-name $KeyVaultName --name 'OBO-CLIENT-SECRET' --value $secret 1>$null
$secret = $null  # effacement mémoire ; aucune écriture sur disque, aucun Write-Host de la valeur

# ============================================================================
# (3) Consentement administrateur (INF-06) — étape opérateur privilégié
# ============================================================================
Write-Host "Demande du consentement administrateur pour les scopes délégués de $OboAppName..." -ForegroundColor Cyan
az ad app permission admin-consent --id $oboAppId --only-show-errors | Out-Null
Write-Host "ATTENTION : le consentement administrateur exige Global/Privileged Role Admin." -ForegroundColor Yellow
Write-Host "           Le grant vivant doit être re-vérifié via : az ad app permission list-grants --id $oboAppId" -ForegroundColor Yellow

# --- Sortie machine-lisible (appIds uniquement — JAMAIS le secret) ---
Write-Host "`n=================================================" -ForegroundColor Magenta
Write-Host "PROVISIONNEMENT DES APP REGISTRATIONS TERMINÉ" -ForegroundColor Green
Write-Host "API_APP_ID=$apiAppId"
Write-Host "OBO_APP_ID=$oboAppId"
Write-Host "OBO_SECRET -> Key Vault '$KeyVaultName' / secret 'OBO-CLIENT-SECRET'" -ForegroundColor Yellow
Write-Host "=================================================`n" -ForegroundColor Magenta
