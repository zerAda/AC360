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

@description('Localisation de Document Intelligence. Par défaut = location ; PROD peut basculer sur westeurope (fallback résidence EU / dispo S0).')
param docIntelLocation string = location

@description('Plafond d\'instances du plan Flex (scaleAndConcurrency.maximumInstanceCount). Petit pour une seule équipe.')
param funcMaxInstanceCount int = 40

@description('Mémoire par instance Flex en Mo (scaleAndConcurrency.instanceMemoryMB).')
@allowed([ 512, 2048, 4096 ])
param funcInstanceMemoryMB int = 2048

@description('Version du runtime Python du plan Flex (functionAppConfig.runtime.version).')
param funcRuntimeVersion string = '3.12'

@description('Nom du conteneur Blob hébergeant le package de déploiement Flex (deployment.storage).')
param deploymentContainerName string = 'app-package'

// --------------------------------------------------------------------------
// Params PROD durcissement storage (INF-09). Défauts = forme staging.
// --------------------------------------------------------------------------
@description('SKU du compte de stockage. Standard_LRS en staging ; Standard_GRS en PROD (géo-redondance INF-09).')
param storageSku string = 'Standard_LRS'

@description('Active le stockage par identité managée (AzureWebJobsStorage sans clé). PROD=true => allowSharedKeyAccess=false.')
param enableIdentityStorage bool = false

@description('Rétention soft-delete des blobs en jours (INF-09).')
param blobSoftDeleteDays int = 7

@description('Rétention soft-delete des conteneurs en jours (INF-09).')
param containerSoftDeleteDays int = 7

@description('Fenêtre Point-in-Time Restore en jours. DOIT être < fenêtre soft-delete (INF-09 / RESEARCH A6).')
param pointInTimeRestoreDays int = 6

var storageName = '${namePrefix}${environmentName}store'
var kvName = '${namePrefix}-kv-${environmentName}'
var funcName = '${namePrefix}-func-${environmentName}'
var gatewayName = '${namePrefix}-gateway-${environmentName}'
var docIntelName = '${namePrefix}-docintel-${environmentName}'
var funcPlanName = '${namePrefix}-func-plan'
var gwPlanName = '${namePrefix}-gw-plan'

// Rôle intégré "Key Vault Secrets User".
var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

// Rôles DATA-plane (moindre privilège) pour la Managed Identity de la Function (INF-07).
// Trio Durable (Blob/Queue/Table) scopé au compte de stockage + Cognitive Services User sur DocIntel.
// NB: le rôle Blob est "Storage Blob Data Owner" (rôle host canonique pour AzureWebJobsStorage par
// identité ; supersède le Contributor pour l'hôte — RESEARCH Pattern 4 §host-storage). JAMAIS Owner/
// Contributor de gestion (ne donnent PAS l'accès data-plane).
var storageBlobDataOwner = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
var storageQueueDataContributor = '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
var storageTableDataContributor = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
var cognitiveServicesUserRoleId = 'a97b65f3-24c7-4388-baec-2e87135dc908'
var funcStorageDataRoles = [
  storageBlobDataOwner
  storageQueueDataContributor
  storageTableDataContributor
]

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
  sku: { name: storageSku } // INF-09 : Standard_GRS en PROD (géo-redondance), Standard_LRS en staging
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    // INF-09 : les connexions par identité managée (AzureWebJobsStorage__credential=managedidentity)
    // suppriment le besoin de la clé partagée. PROD => enableIdentityStorage=true => allowSharedKeyAccess=false.
    allowSharedKeyAccess: !enableIdentityStorage
  }
}

// blobServices enfant — soft-delete blob/conteneur + Point-in-Time Restore + versioning + change feed (INF-09).
// versioning + changeFeed sont des prérequis du PITR ; la fenêtre PITR doit être < fenêtre soft-delete.
resource blobSvc 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    isVersioningEnabled: true
    changeFeed: { enabled: true }
    deleteRetentionPolicy: { enabled: true, days: blobSoftDeleteDays }
    containerDeleteRetentionPolicy: { enabled: true, days: containerSoftDeleteDays }
    restorePolicy: { enabled: true, days: pointInTimeRestoreDays }
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
  location: docIntelLocation
  sku: { name: 'S0' }
  kind: 'FormRecognizer'
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: docIntelName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: docIntelDisableLocalAuth
  }
}

// --------------------------------------------------------------------------
// RBAC data-plane de la Function MI (INF-07) — moindre privilège, scopé par ressource.
// Trio Durable (Blob Owner / Queue / Table Data) sur le compte de stockage + Cognitive
// Services User sur DocIntel (OCR Entra-only). AUCUN rôle "SharePoint OBO" : l'accès
// SharePoint est un consentement DÉLÉGUÉ géré dans le script d'app-reg (RESEARCH ln 462),
// PAS un rôle de Managed Identity.
// --------------------------------------------------------------------------
resource funcStorageRoles 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for r in funcStorageDataRoles: {
  // Le nom doit être calculable au début du déploiement : on utilise functionApp.id (et non le
  // principalId, valeur runtime). Le principalId reste consommé dans properties (autorisé).
  name: guid(storage.id, functionApp.id, r)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', r)
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}]

resource funcDocIntelRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(docIntel.id, functionApp.id, cognitiveServicesUserRoleId)
  scope: docIntel
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRoleId)
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// --------------------------------------------------------------------------
// Plans
// --------------------------------------------------------------------------
resource funcPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: funcPlanName
  location: location
  // Flex Consumption (INF-03). Y1->Flex en place est non supporté : c'est un plan/app neufs.
  sku: { name: 'FC1', tier: 'FlexConsumption' }
  properties: { reserved: true } // Linux
}

// --------------------------------------------------------------------------
// PIN INSTANCE UNIQUE — LOAD-BEARING (AUD-04)
// --------------------------------------------------------------------------
// La passerelle FastAPI conserve un état EN MÉMOIRE, propre au processus, qui
// n'est correct qu'à EXACTEMENT un seul processus / une seule instance :
//   - le compteur de quota par utilisateur  (api_server.py  _rate_limit_store)
//   - le cache JWKS                          (auth.py        _JWKS_CACHE)
//   - la table « propriétaire » de raccourci (api_server.py  _audit_job_owners)
// Un second worker/instance rendrait ces structures incohérentes :
//   -> contournement du rate-limit (requêtes réparties sur plusieurs workers),
//   -> divergence du cache JWKS pendant une rotation de clés,
//   -> divergence du raccourci IDOR _audit_job_owners (le contrôle durable
//      owner_hash du Plan 01-06 reste l'autorité, mais le raccourci doit rester
//      cohérent).
// Le pin DOIT donc être maintenu : sku.capacity = 1, gunicorn --workers 1, et
// AUCUNE règle d'autoscale ne doit porter la capacité au-dessus de 1.
//
// Note F1/Free : le tier Free est figé à une seule instance et REFUSE un
// sku.capacity explicite. Le pin capacity=1 explicite est posé en Phase 2
// (INF-02, plan B1) lors du passage au plan B1. Ici, sur F1, l'instance unique
// est garantie par le tier ; le pin load-bearing est porté par la commande de
// démarrage gunicorn --workers 1 ci-dessous (gatewayApp.siteConfig) et par ce
// commentaire. AUCUN autoscaleSettings ne cible ce plan : n'en ajoutez aucun
// qui porterait maximum > 1.
resource gwPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: gwPlanName
  location: location
  // B1/Basic : le pin capacity=1 explicite est désormais POSÉ (INF-02). B1 accepte
  // un sku.capacity explicite (contrairement à F1/Free qui le refusait en Phase 1) :
  // c'est le pin load-bearing différé par D-AUD-04, ici landé. AUCUN autoscaleSettings
  // ne cible ce plan ; n'en ajoutez aucun qui porterait maximum > 1 (briserait AUD-04).
  sku: { name: 'B1', tier: 'Basic', capacity: 1 }
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
      // Flex Consumption : NE PAS poser linuxFxVersion ni FUNCTIONS_EXTENSION_VERSION /
      // WEBSITE_RUN_FROM_PACKAGE (dépréciés/déplacés sur Flex — le runtime vit dans functionAppConfig).
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      ipSecurityRestrictions: ipRestrictions
      // INF-09 : host-storage par identité managée — AUCUNE chaîne de connexion AzureWebJobsStorage.
      // __accountName + __credential=managedidentity ; les endpoints blob/queue/table sont inférés du
      // suffixe DNS Azure global. Couplé à allowSharedKeyAccess=false (clé partagée désactivée).
      appSettings: [
        { name: 'AzureWebJobsStorage__accountName', value: storage.name }
        { name: 'AzureWebJobsStorage__credential', value: 'managedidentity' }
      ]
    }
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${storage.properties.primaryEndpoints.blob}${deploymentContainerName}'
          authentication: { type: 'SystemAssignedIdentity' } // pas de chaîne de connexion
        }
      }
      scaleAndConcurrency: {
        maximumInstanceCount: funcMaxInstanceCount
        instanceMemoryMB: funcInstanceMemoryMB
      }
      runtime: { name: 'python', version: funcRuntimeVersion }
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
      alwaysOn: true // INF-02 : Always On (B1 le supporte ; maintient le process chaud)
      // PIN INSTANCE UNIQUE — LOAD-BEARING (AUD-04). --workers 1 est obligatoire :
      // un second worker gunicorn romprait l'état en mémoire de la passerelle
      // (_rate_limit_store, _JWKS_CACHE, _audit_job_owners). Ne pas augmenter le
      // nombre de workers et ne laisser aucun défaut plateforme en réintroduire.
      appCommandLine: 'gunicorn --workers 1 -k uvicorn.workers.UvicornWorker api_server:app'
    }
  }
}

output functionPrincipalId string = functionApp.identity.principalId
output gatewayPrincipalId string = gatewayApp.identity.principalId
output keyVaultName string = keyVault.name
