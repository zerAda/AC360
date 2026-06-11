// =============================================================================
// AC360 — Infrastructure as Code (posture de sécurité durcie)
//
// Codifie la posture VÉRIFIÉE en live le 2026-06-11 (httpsOnly, TLS 1.2, FTPS off,
// ingress Function verrouillé, Key Vault RBAC + purge protection, storage sans
// blob public, identités managées en moindre privilège) afin d'empêcher la dérive
// (ex. régression httpsOnly déjà observée après un redéploiement).
//
// ⚠️ NE PAS appliquer à l'aveugle sur le staging vivant. Valider d'abord :
//    az deployment group what-if -g rg-ac360-staging -f infra/main.bicep -p @infra/staging.parameters.json
// Les durcissements réseau (KV/DocIntel privés) nécessitent une fenêtre + VNet/PE.
// =============================================================================

@description('Région Azure.')
param location string = resourceGroup().location

@description('Préfixe des ressources.')
param namePrefix string = 'ac360'

@description('Nom court d\'environnement.')
param environmentName string = 'staging'

@description('IP sortantes de la passerelle autorisées à joindre la Function (verrou ingress). Une règle Allow par IP, puis Deny all implicite.')
param gatewayOutboundIps array = []

@description('Accès réseau public du Key Vault. Enabled en staging ; Disabled + Private Endpoint en PROD.')
@allowed([ 'Enabled', 'Disabled' ])
param keyVaultPublicNetworkAccess string = 'Enabled'

@description('Désactive l\'auth locale par clé sur Document Intelligence (Entra-only). Passer à true une fois la Managed Identity câblée + rôle Cognitive Services User accordé.')
param docIntelDisableLocalAuth bool = false

@description('Object IDs (principalId) des identités managées autorisées à lire les secrets du Key Vault.')
param keyVaultSecretsReaderPrincipalIds array = []

var storageName = '${namePrefix}${environmentName}store'
var kvName = '${namePrefix}-kv-${environmentName}'
var funcName = '${namePrefix}-func-${environmentName}'
var gatewayName = '${namePrefix}-gateway-${environmentName}'
var docIntelName = '${namePrefix}-docintel-${environmentName}'
var funcPlanName = '${namePrefix}-func-plan'
var gwPlanName = '${namePrefix}-gw-plan'

// Rôle intégré "Key Vault Secrets User".
var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

var ipRestrictions = [for (ip, i) in gatewayOutboundIps: {
  ipAddress: '${ip}/32'
  action: 'Allow'
  priority: 100 + i
  name: 'allow-gw-${100 + i}'
}]

// --------------------------------------------------------------------------
// Storage (Durable + jobs) — durci
// --------------------------------------------------------------------------
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true // requis par Durable Functions aujourd'hui
  }
}

// --------------------------------------------------------------------------
// Key Vault — RBAC, purge protection, soft-delete
// --------------------------------------------------------------------------
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: kvName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    publicNetworkAccess: keyVaultPublicNetworkAccess
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: keyVaultPublicNetworkAccess == 'Disabled' ? 'Deny' : 'Allow'
    }
  }
}

resource kvRoleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for pid in keyVaultSecretsReaderPrincipalIds: {
  name: guid(keyVault.id, pid, kvSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: pid
    principalType: 'ServicePrincipal'
  }
}]

// --------------------------------------------------------------------------
// Document Intelligence (OCR)
// --------------------------------------------------------------------------
resource docIntel 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: docIntelName
  location: location
  sku: { name: 'F0' }
  kind: 'FormRecognizer'
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: docIntelName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: docIntelDisableLocalAuth
  }
}

// --------------------------------------------------------------------------
// Plans
// --------------------------------------------------------------------------
resource funcPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: funcPlanName
  location: location
  sku: { name: 'Y1', tier: 'Dynamic' }
  properties: { reserved: true }
}

resource gwPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: gwPlanName
  location: location
  sku: { name: 'F1', tier: 'Free' }
  properties: { reserved: true }
}

// --------------------------------------------------------------------------
// Function (backend Durable) — durci + ingress verrouillé
// --------------------------------------------------------------------------
resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: funcName
  location: location
  kind: 'functionapp,linux'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: funcPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.12'
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      ipSecurityRestrictions: ipRestrictions
    }
  }
}

// --------------------------------------------------------------------------
// Gateway (FastAPI) — durci
// --------------------------------------------------------------------------
resource gatewayApp 'Microsoft.Web/sites@2023-12-01' = {
  name: gatewayName
  location: location
  kind: 'app,linux'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: gwPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.12'
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
    }
  }
}

output functionPrincipalId string = functionApp.identity.principalId
output gatewayPrincipalId string = gatewayApp.identity.principalId
output keyVaultName string = keyVault.name
