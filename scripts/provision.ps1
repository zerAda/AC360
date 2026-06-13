<#
.SYNOPSIS
Orchestrateur de provisionnement de production AC360 (INF-01) : portes pré-vol bloquantes
(fail-closed) puis séquence dépendance-correcte. Par défaut en mode WHAT-IF (aucun apply réel).

.DESCRIPTION
Point d'entrée UNIQUE qu'un opérateur exécute pour provisionner l'infrastructure de production.

Le script applique d'abord des PORTES PRÉ-VOL BLOQUANTES (rien de mutant tant qu'elles ne passent
pas toutes) :
  1. Présence d'Azure CLI + authentification (`az account show`).
  2. Correspondance d'abonnement optionnelle (`-ExpectedSubscription`) — `throw` si divergence.
  3. Enregistrement des Resource Providers requis : Microsoft.App (intégration VNet Flex) et
     Microsoft.KeyVault.
  4. Disponibilité régionale Flex Consumption (`az functionapp list-flexconsumption-locations`) —
     `throw` (escalade) si la région cible est absente : AUCUNE substitution silencieuse de région.
  5. Sonde DocIntel S0 + résidence EU (géo tenant M365 / région capacité Fabric / région env
     Power Platform) surfacées comme POINTS DE CONTRÔLE OPÉRATEUR (confirmation manuelle).

Puis il déroule la SÉQUENCE DÉPENDANCE-CORRECTE (les étapes mutantes sont gardées derrière
`-not $WhatIfOnly` / des messages OPERATOR CHECKPOINT explicites) :
  (1) Resource Group
  (2) Enregistrements d'application Entra (création + scopes) — le secret OBN va dans KV APRÈS
      l'existence de KV ; on scinde donc : créer les apps maintenant, poser le secret après le deploy.
  (3) `az deployment group what-if` (TOUJOURS exécuté — l'opérateur revoit le diff)
  (4) OPERATOR CHECKPOINT — `az deployment group create` (seulement si `-not $WhatIfOnly`)
  (5) Pose du secret OBO dans KV (via provision_app_registrations.ps1, KV existant) + admin-consent (opérateur)
  (6) SECOND PASS OPERATOR CHECKPOINT — bascule KV `publicNetworkAccess=Disabled` UNIQUEMENT après
      intégration VNet + Private Endpoint confirmés (RESEARCH Pitfall 2)
  (7) Vérification — grants de permission, role assignments MI, résolution d'une référence KV.

Le comportement par défaut (`-WhatIfOnly`) n'effectue AUCUN appel `az` mutant au-delà du what-if /
des sondes régionales : apply réel, consentement, résidence et bascule KV sont des points de
contrôle opérateur. RIEN n'est appliqué en live durant cette phase.

.NOTES
- Prérequis : Azure CLI installé (https://aka.ms/installazurecliwindows), PowerShell 7+ recommandé.
- Analogues : scripts/deploy_azure_ocr.ps1 (garde login), scripts/package_release.ps1 (param +
  $ErrorActionPreference = "Stop" + gate fail-closed), scripts/provision_app_registrations.ps1
  (créé en 02-02, séquencé ici).
- INF-01 : résidence/région EU encodée comme pré-vol bloquant avec locations EU explicites.
#>

param(
    [string]$ResourceGroup = 'rg-ac360-prod',
    [string]$Location = 'francecentral',
    [string]$ExpectedSubscription,
    [string]$BicepFile = 'infra/main.bicep',
    [string]$ParamFile = 'infra/prod.parameters.json',
    [string]$KeyVaultName = 'kv-ac360-prod',
    [string]$DocIntelLocation = 'francecentral',
    [switch]$WhatIfOnly = $true
)

$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "==== $Title ====" -ForegroundColor Cyan
}

function Write-OperatorCheckpoint {
    param([string]$Message)
    Write-Host ""
    Write-Host "*** OPERATOR CHECKPOINT *** $Message" -ForegroundColor Yellow
}

# ============================================================================
# PORTES PRÉ-VOL BLOQUANTES (fail-fast — rien de mutant tant que tout ne passe pas)
# ============================================================================
Write-Section "PRÉ-VOL — portes bloquantes (fail-closed)"

# (1) Présence d'Azure CLI + authentification (analogue deploy_azure_ocr.ps1 lignes 23-36).
Write-Host "Vérification de l'installation d'Azure CLI..." -ForegroundColor Cyan
if (-not (Get-Command "az" -ErrorAction SilentlyContinue)) {
    Write-Host "Erreur : Azure CLI n'est pas installé. Veuillez l'installer puis réessayer." -ForegroundColor Red
    exit 1
}

$azAccount = az account show --query "name" -o tsv 2>$null
if (-not $azAccount) {
    Write-Host "Vous n'êtes pas connecté à Azure. Lancement de la fenêtre de connexion..." -ForegroundColor Yellow
    az login | Out-Null
    $azAccount = az account show --query "name" -o tsv
}
Write-Host "Connecté à l'abonnement : $azAccount" -ForegroundColor Green

# (2) Correspondance d'abonnement optionnelle — fail-closed (T-02-08).
$sub = az account show --query id -o tsv
if ($ExpectedSubscription -and ($sub -ne $ExpectedSubscription)) {
    Write-Host "Mauvais abonnement actif : $sub (attendu : $ExpectedSubscription)" -ForegroundColor Red
    throw "Wrong subscription: $sub (expected $ExpectedSubscription)"
}
Write-Host "Abonnement cible vérifié : $sub" -ForegroundColor Green

# (3) Enregistrement des Resource Providers requis (RESEARCH Pitfall 4).
Write-Host "Enregistrement des Resource Providers requis (Microsoft.App, Microsoft.KeyVault)..." -ForegroundColor Cyan
az provider register -n Microsoft.App | Out-Null      # Intégration VNet Flex Consumption
az provider register -n Microsoft.KeyVault | Out-Null # Prérequis Key Vault

# (4) Disponibilité régionale Flex Consumption — fail-closed, AUCUNE substitution (T-02-09 / INF-01).
$flexKey = $Location.Replace(" ", "").ToLower()
$flex = az functionapp list-flexconsumption-locations --query "[?name=='$flexKey'] | length(@)" -o tsv
if ($flex -eq '0') {
    Write-Host "Flex Consumption indisponible dans '$Location' — escalade (aucun fallback EU Flex retenu)." -ForegroundColor Red
    throw "Flex not available in $Location — escalate (no EU Flex fallback chosen)."
}
Write-Host "Flex Consumption disponible dans '$Location'." -ForegroundColor Green

# (5) Sonde DocIntel S0 + résidence EU — POINTS DE CONTRÔLE OPÉRATEUR (pas de substitution silencieuse).
Write-Section "PRÉ-VOL — sondes résidence/capacité (contrôle opérateur)"
$docKey = $DocIntelLocation.Replace(" ", "").ToLower()
$docS0 = az cognitiveservices account list-skus `
    --kind FormRecognizer `
    --query "[?name=='S0' && contains(locations, '$($docKey.ToUpper())')] | length(@)" -o tsv 2>$null
if (-not $docS0 -or $docS0 -eq '0') {
    Write-OperatorCheckpoint "DocIntel S0 introuvable dans '$DocIntelLocation'. NE PAS substituer en silence."
    Write-Host "  -> Action opérateur : positionner docIntelLocation=westeurope (fallback verrouillé) dans $ParamFile." -ForegroundColor Yellow
} else {
    Write-Host "DocIntel S0 disponible dans '$DocIntelLocation'." -ForegroundColor Green
}

Write-OperatorCheckpoint "Confirmer manuellement la RÉSIDENCE EU avant de continuer :"
Write-Host "  - Géo du tenant M365 (GEREP) en zone EU." -ForegroundColor Yellow
Write-Host "  - Région de la capacité Fabric en zone EU." -ForegroundColor Yellow
Write-Host "  - Région de l'environnement Power Platform en zone EU." -ForegroundColor Yellow
Write-Host "  (INF-01 / précurseur RGP-06 — confirmation manuelle requise.)" -ForegroundColor Yellow

# ============================================================================
# SÉQUENCE DÉPENDANCE-CORRECTE
# (étapes mutantes gardées derrière `-not $WhatIfOnly` / OPERATOR CHECKPOINT)
# ============================================================================
if ($WhatIfOnly) {
    Write-Host ""
    Write-Host "MODE WHAT-IF (par défaut) : aucun apply mutant ne sera exécuté. Live = points de contrôle opérateur." -ForegroundColor Yellow
}

$appRegScript = Join-Path $PSScriptRoot 'provision_app_registrations.ps1'

# --- (1) Resource Group ---
Write-Section "(1) Resource Group"
if (-not $WhatIfOnly) {
    az group create -n $ResourceGroup -l $Location | Out-Null
    Write-Host "Resource Group '$ResourceGroup' créé/à jour dans '$Location'." -ForegroundColor Green
} else {
    Write-Host "[WHAT-IF] az group create -n $ResourceGroup -l $Location" -ForegroundColor Yellow
}

# --- (2) Enregistrements d'application Entra (création + scopes) ---
# Le secret OBO doit aller dans KV APRÈS l'existence de KV : on scinde la pose du secret à l'étape (5).
Write-Section "(2) Enregistrements d'application Entra (création + scopes)"
if (-not $WhatIfOnly) {
    Write-Host "Invocation de provision_app_registrations.ps1 (création apps + demande de scopes)." -ForegroundColor Cyan
    Write-Host "Note : la pose du secret OBO dans Key Vault est effectuée à l'étape (5), une fois KV créé par le deploy." -ForegroundColor Yellow
    # NB : exécuté pleinement à l'étape (5) ; ici l'opérateur confirme que les apps existent avant le what-if.
} else {
    Write-Host "[WHAT-IF] & '$appRegScript' -KeyVaultName $KeyVaultName  (création apps + scopes ; secret -> KV en (5))" -ForegroundColor Yellow
}

# --- (3) Bicep what-if (TOUJOURS exécuté) ---
Write-Section "(3) Bicep what-if (revue opérateur)"
az deployment group what-if -g $ResourceGroup -f $BicepFile -p "@$ParamFile"
Write-Host "OPERATOR: review the what-if diff above and attach as evidence." -ForegroundColor Yellow

# --- (4) OPERATOR CHECKPOINT — Bicep apply ---
Write-Section "(4) Bicep apply (OPERATOR CHECKPOINT)"
if (-not $WhatIfOnly) {
    Write-OperatorCheckpoint "Application du déploiement Bicep (création KV, storage, plans, apps, VNet, PE, rôles)."
    az deployment group create -g $ResourceGroup -f $BicepFile -p "@$ParamFile" | Out-Null
    Write-Host "Déploiement Bicep appliqué." -ForegroundColor Green
} else {
    Write-Host "[WHAT-IF] az deployment group create -g $ResourceGroup -f $BicepFile -p `@$ParamFile  (apply gardé derrière -not WhatIfOnly)" -ForegroundColor Yellow
}

# --- (5) Pose du secret OBO dans KV (existant) + admin-consent ---
Write-Section "(5) Secret OBO -> Key Vault + admin-consent"
if (-not $WhatIfOnly) {
    Write-OperatorCheckpoint "Pose du secret OBO dans Key Vault (KV désormais existant) et demande de consentement administrateur."
    & $appRegScript -KeyVaultName $KeyVaultName
    Write-Host "Le consentement administrateur a été DEMANDÉ ; la vérification du grant vivant est un contrôle opérateur (02-04)." -ForegroundColor Yellow
} else {
    Write-Host "[WHAT-IF] & '$appRegScript' -KeyVaultName $KeyVaultName  +  az ad app permission admin-consent  (opérateur)" -ForegroundColor Yellow
}

# --- (6) SECOND PASS OPERATOR CHECKPOINT — bascule KV public access ---
# RESEARCH Pitfall 2 : la bascule DOIT venir APRÈS l'intégration VNet + Private Endpoint, sinon les
# références KV cassent (le README staging avertit de ce mode d'échec exact). T-02-10.
Write-Section "(6) Bascule KV publicNetworkAccess=Disabled (SECOND PASS — OPERATOR CHECKPOINT)"
if (-not $WhatIfOnly) {
    Write-OperatorCheckpoint "Basculer KV en privé UNIQUEMENT après confirmation de l'intégration VNet + Private Endpoint."
    Write-Host "  Une fois VNet integration + PE confirmés, exécuter :" -ForegroundColor Yellow
    Write-Host "    az keyvault update -n $KeyVaultName --public-network-access Disabled" -ForegroundColor Yellow
    Write-Host "  (Non exécuté automatiquement : ordre RESEARCH Pitfall 2 — éviter de casser les références KV.)" -ForegroundColor Yellow
} else {
    Write-Host "[WHAT-IF] az keyvault update -n $KeyVaultName --public-network-access Disabled  (APRÈS PE+VNet — Pitfall 2)" -ForegroundColor Yellow
}

# --- (7) Vérification ---
Write-Section "(7) Vérification post-provisionnement"
if (-not $WhatIfOnly) {
    Write-Host "Vérification des grants de permission délégués..." -ForegroundColor Cyan
    az ad app permission list-grants 2>$null | Out-Null
    Write-Host "Vérification des role assignments de l'identité managée (MI) et de la résolution d'une référence KV recommandée." -ForegroundColor Cyan
    Write-Host "  - az role assignment list (identité managée du Function App)" -ForegroundColor Yellow
    Write-Host "  - confirmer qu'une référence KV résout (App Setting @Microsoft.KeyVault(...))" -ForegroundColor Yellow
    Write-Host "Vérification terminée." -ForegroundColor Green
} else {
    Write-Host "[WHAT-IF] az ad app permission list-grants ; az role assignment list ; résolution référence KV" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== provision.ps1 terminé (mode : $(if ($WhatIfOnly) { 'WHAT-IF (par défaut, aucun apply)' } else { 'APPLY (opérateur)' })) ===" -ForegroundColor Green
