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

@description('Accès réseau public de Document Intelligence. Enabled en staging ; Disabled + Private Endpoint en PROD (CR-03 : évite l\'OCR de PII sur l\'endpoint public).')
@allowed([ 'Enabled', 'Disabled' ])
param docIntelPublicNetworkAccess string = 'Enabled'

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

@description('Accès réseau public du compte de stockage. Enabled en staging ; Disabled (networkAcls defaultAction=Deny) en PROD (WR-03 : data-plane non joignable depuis l\'Internet public).')
@allowed([ 'Enabled', 'Disabled' ])
param storagePublicNetworkAccess string = 'Enabled'

@description('Rétention soft-delete des blobs en jours (INF-09).')
param blobSoftDeleteDays int = 7

@description('Rétention soft-delete des conteneurs en jours (INF-09).')
param containerSoftDeleteDays int = 7

@description('Fenêtre Point-in-Time Restore en jours. DOIT être < fenêtre soft-delete (INF-09 / RESEARCH A6).')
param pointInTimeRestoreDays int = 6

@description('RGP-03 : rétention (jours) des artefacts job/OCR/FIC avant suppression serveur (lifecycle).')
param jobRetentionDays int = 30

@description('RGP-03 : préfixes blob des artefacts job/OCR/FIC ciblés par la règle de suppression. Scopé pour NE JAMAIS toucher les blobs de contrôle Durable.')
param jobBlobPrefixes array = [ 'jobs/' ]

// --------------------------------------------------------------------------
// Params PROD périmètre réseau (INF-08). Défaut staging-off : la section réseau
// entière est conditionnée par enablePrivateNetworking (staging reste intact).
// Les CIDR sont au choix (CONTEXT <decisions> "Claude's Discretion").
// --------------------------------------------------------------------------
@description('Active le périmètre privé : VNet + Private Endpoint Key Vault + DNS privé + intégration VNet des apps. PROD=true.')
param enablePrivateNetworking bool = false

@description('Plage d\'adresses du VNet (INF-08).')
param vnetAddressPrefix string = '10.42.0.0/24'

@description('Sous-réseau Private Endpoint (policies PE désactivées).')
param subnetPePrefix string = '10.42.0.0/27'

@description('Sous-réseau Function Flex (délégation Microsoft.App/environments, /27 min).')
param subnetFxPrefix string = '10.42.0.32/27'

@description('Sous-réseau passerelle App Service B1 (délégation Microsoft.Web/serverFarms, /28 min).')
param subnetGwPrefix string = '10.42.0.64/28'

// --------------------------------------------------------------------------
// Params observabilité (OBS-01..05). Transmis au module observability.bicep.
// Le budget (OBS-04) est SUBSCRIPTION-scoped et NE vit PAS ici (Pitfall 4) :
// déployé via infra/budget.bicep + `az deployment sub create` (Plan 04).
// --------------------------------------------------------------------------
@description('Adresses email destinataires des alertes et du budget (groupe d\'actions OBS).')
param alertEmails array = []

@description('URL du webhook Teams pour le groupe d\'actions (sink alertes + budget — OBS-04). Vide => pas de webhook. Power Automate/Workflows (connecteurs O365 legacy en retrait).')
param teamsWebhookUrl string = ''

@description('RGP-04 : rétention Log Analytics (jours), transmise au module observability. Courte EU-region délibérée (data-minimization). 90 j par défaut.')
param logAnalyticsRetentionDays int = 90

var storageName = '${namePrefix}${environmentName}store'
var kvName = '${namePrefix}-kv-${environmentName}'
var funcName = '${namePrefix}-func-${environmentName}'
var gatewayName = '${namePrefix}-gateway-${environmentName}'
var docIntelName = '${namePrefix}-docintel-${environmentName}'
var funcPlanName = '${namePrefix}-func-plan'
var gwPlanName = '${namePrefix}-gw-plan'

// Noms réseau (INF-08). privatelink.vaultcore.azure.net est le SEUL nom littéral obligatoire :
// il est posé EN DUR sur la ressource privateDnsZones (PATTERNS.md ln 35) — pas via une var, pour
// que le nom compilé reste un littéral exact (résolution DNS Azure + analyse statique).
var vnetName = '${namePrefix}-vnet-${environmentName}'
// IDs de sous-réseaux calculés au début du déploiement (pour virtualNetworkSubnetId des apps,
// même quand la section réseau est conditionnelle). Vides quand enablePrivateNetworking=false.
var subnetFxId = enablePrivateNetworking ? resourceId('Microsoft.Network/virtualNetworks/subnets', vnetName, 'snet-fx') : ''
var subnetGwId = enablePrivateNetworking ? resourceId('Microsoft.Network/virtualNetworks/subnets', vnetName, 'snet-gw') : ''

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

var ipAllowRules = [for (ip, i) in gatewayOutboundIps: {
  ipAddress: '${ip}/32'
  action: 'Allow'
  priority: 100 + i
  name: 'allow-gw-${100 + i}'
}]
// WR-05 : rendre le Deny-all EXPLICITE dès qu'au moins une règle Allow existe (la « Deny all
// implicite » d'App Service ne tient que s'il y a >=1 Allow). Tant que gatewayOutboundIps est vide
// (staging, ou prod avant que les IP sortantes de la passerelle soient connues) on n'ajoute PAS le
// Deny-all pour ne pas verrouiller toute joignabilité. EN PROD, gatewayOutboundIps DOIT être peuplé
// avant le go-live (étape opérateur Phase 3 : lire les outboundIpAddresses de la passerelle, puis
// redéployer) — sinon l'ingress Function reste ouvert. Voir runbook OPS-01.
var ipRestrictions = empty(gatewayOutboundIps) ? ipAllowRules : concat(ipAllowRules, [
  {
    ipAddress: 'Any'
    action: 'Deny'
    priority: 2147483647
    name: 'deny-all'
  }
])

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
    // WR-03 : restriction réseau data-plane. PROD => Disabled + networkAcls Deny (bypass AzureServices
    // pour laisser la plateforme/Functions par MI joindre le compte). Staging => Enabled/Allow (inchangé).
    publicNetworkAccess: storagePublicNetworkAccess
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: storagePublicNetworkAccess == 'Disabled' ? 'Deny' : 'Allow'
    }
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

// RGP-03 : suppression serveur des artefacts job/OCR/FIC à jobRetentionDays jours.
// prefixMatch SCOPE la règle aux seuls blobs d'artefacts (jamais les blobs de contrôle
// /lease Durable du même compte — RESEARCH Pitfall 3). name DOIT valoir 'default'.
// Coexiste avec blobSvc (soft-delete/PITR/versioning) ; les actions snapshot/version
// purgent aussi les copies retenues à la même fenêtre.
resource storageLifecycle 'Microsoft.Storage/storageAccounts/managementPolicies@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    policy: {
      rules: [
        {
          enabled: true
          name: 'rgp03-delete-job-artifacts'
          type: 'Lifecycle'
          definition: {
            filters: {
              blobTypes: [ 'blockBlob' ]
              prefixMatch: jobBlobPrefixes
            }
            actions: {
              baseBlob: { delete: { daysAfterModificationGreaterThan: jobRetentionDays } }
              snapshot: { delete: { daysAfterCreationGreaterThan: jobRetentionDays } }
              version: { delete: { daysAfterCreationGreaterThan: jobRetentionDays } }
            }
          }
        }
      ]
    }
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

// CR-02 : la passerelle consomme @Microsoft.KeyVault(...) pour OBO_CLIENT_SECRET ; sa Managed
// Identity DOIT donc avoir Key Vault Secrets User sur le coffre, sinon la référence KV ne résout
// pas et la passerelle démarre sans secret OBO (auth cassée en prod). Le principalId n'étant connu
// qu'à l'existence de l'app, on l'assigne IN-TEMPLATE (le nom guid() reste calculable via .id).
resource gwKvSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, gatewayApp.id, kvSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: gatewayApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// CR-02 (Function MI) : la Function peut elle aussi consommer un secret KV (ex. credentials Fabric/OCR
// migrés en référence KV). On lui accorde le même rôle de lecture des secrets pour éviter une régression
// symétrique « KV reference not resolved » côté Functions.
resource funcKvSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, functionApp.id, kvSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// INF-08 / OBS-01 : la chaîne de connexion App Insights (non high-value — T-03-08) est
// stockée comme secret Key Vault et consommée par les deux apps via @Microsoft.KeyVault(...),
// pour respecter l'invariant zéro-cleartext de la posture durcie (validate_infra.ps1 INF-08).
// La valeur provient de la sortie du module observability ; les apps la référencent par URI
// déterministe (sans dépendance symbolique => pas de cycle).
resource appiConnSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'APPINSIGHTS-CONNECTION-STRING'
  properties: {
    value: observability.outputs.connectionString
  }
}

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
    // CR-03 : PROD => Disabled (PII OCR sur Private Endpoint Entra-only, jamais sur l'Internet public).
    // Le flip vers Disabled est séquencé APRÈS le PE (provision.ps1 ; même ordre Pitfall 2 que le Key Vault).
    publicNetworkAccess: docIntelPublicNetworkAccess
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
    // INF-08 : intégration VNet (sous-réseau délégué Microsoft.App/environments) en PROD ; null en staging.
    virtualNetworkSubnetId: enablePrivateNetworking ? subnetFxId : null
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
        // OBS-01 : exporter Azure Monitor via référence Key Vault (zéro cleartext — INF-08).
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/APPINSIGHTS-CONNECTION-STRING)'
        }
        // Pitfall 2 : active la télémétrie worker SANS double-compter les requêtes (l'hôte les émet déjà).
        { name: 'PYTHON_APPLICATIONINSIGHTS_ENABLE_TELEMETRY', value: 'true' }
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
    // INF-08 : intégration VNet (sous-réseau délégué Microsoft.Web/serverFarms) en PROD ; null en staging.
    virtualNetworkSubnetId: enablePrivateNetworking ? subnetGwId : null
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
      // INF-08 : ZÉRO secret en clair. Le secret OBO est résolu par la MI via une référence Key Vault.
      // Le secret lui-même est créé au runtime par provision_app_registrations.ps1 (nom KV : OBO-CLIENT-SECRET).
      // L'app consomme le nom OBO_CLIENT_SECRET (inchangé, lu par scripts/config.py). SecretUri déterministe
      // construit sur le vaultUri du Key Vault existant (sans version => dernière version).
      appSettings: [
        {
          name: 'OBO_CLIENT_SECRET'
          value: '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/OBO-CLIENT-SECRET)'
        }
        // OBS-01 : exporter Azure Monitor via référence Key Vault (zéro cleartext — INF-08).
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/APPINSIGHTS-CONNECTION-STRING)'
        }
      ]
    }
  }
}

// --------------------------------------------------------------------------
// Périmètre réseau privé (INF-08) — GATED par enablePrivateNetworking.
// VNet (3 sous-réseaux : PE / Flex / passerelle) + Private Endpoint Key Vault +
// zone DNS privée privatelink.vaultcore.azure.net (+ link VNet + zone group).
// Staging (enablePrivateNetworking=false) : aucune de ces ressources n'est déployée.
// NB ordre opérateur : PE + intégration VNet AVANT le flip publicNetworkAccess=Disabled
// (provision.ps1 step 6 ; RESEARCH Pitfall 2) — le flip n'est PAS fait ici.
// --------------------------------------------------------------------------
resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = if (enablePrivateNetworking) {
  name: vnetName
  location: location
  properties: {
    addressSpace: { addressPrefixes: [ vnetAddressPrefix ] }
    subnets: [
      {
        name: 'snet-pe' // pas d'underscore (Flex/Network) ; policies PE désactivées (requis pour PE)
        properties: {
          addressPrefix: subnetPePrefix
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
      {
        name: 'snet-fx' // Function Flex : délégation Microsoft.App/environments (PAS serverFarms)
        properties: {
          addressPrefix: subnetFxPrefix
          delegations: [ { name: 'flexdeleg', properties: { serviceName: 'Microsoft.App/environments' } } ]
        }
      }
      {
        name: 'snet-gw' // Passerelle App Service B1 : délégation Microsoft.Web/serverFarms
        properties: {
          addressPrefix: subnetGwPrefix
          delegations: [ { name: 'gwdeleg', properties: { serviceName: 'Microsoft.Web/serverFarms' } } ]
        }
      }
    ]
  }
}

resource kvDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = if (enablePrivateNetworking) {
  name: 'privatelink.vaultcore.azure.net' // littéral EXACT — obligatoire (PATTERNS.md ln 35)
  location: 'global'
}

resource kvDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = if (enablePrivateNetworking) {
  parent: kvDnsZone
  name: '${namePrefix}-kvdns-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: vnet.id }
  }
}

resource kvPe 'Microsoft.Network/privateEndpoints@2023-11-01' = if (enablePrivateNetworking) {
  name: '${namePrefix}-kv-pe-${environmentName}'
  location: location
  properties: {
    subnet: { id: resourceId('Microsoft.Network/virtualNetworks/subnets', vnetName, 'snet-pe') }
    privateLinkServiceConnections: [
      {
        name: 'kv-plsc'
        properties: {
          privateLinkServiceId: keyVault.id
          groupIds: [ 'vault' ]
        }
      }
    ]
  }
}

resource kvPeDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = if (enablePrivateNetworking) {
  parent: kvPe
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'vaultcore'
        properties: { privateDnsZoneId: kvDnsZone.id }
      }
    ]
  }
}

// --------------------------------------------------------------------------
// CR-03 : Private Endpoint Document Intelligence (Cognitive Services) — GATED.
// groupId 'account' + zone DNS privée privatelink.cognitiveservices.azure.net. Avec
// docIntelPublicNetworkAccess=Disabled (prod), l'OCR de PII ne transite QUE par le PE (Entra-only).
// Même ordre opérateur que le Key Vault : PE + DNS AVANT le flip publicNetworkAccess=Disabled.
// --------------------------------------------------------------------------
resource docIntelDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = if (enablePrivateNetworking) {
  name: 'privatelink.cognitiveservices.azure.net' // littéral EXACT — résolution DNS Azure
  location: 'global'
}

resource docIntelDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = if (enablePrivateNetworking) {
  parent: docIntelDnsZone
  name: '${namePrefix}-docinteldns-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: vnet.id }
  }
}

resource docIntelPe 'Microsoft.Network/privateEndpoints@2023-11-01' = if (enablePrivateNetworking) {
  name: '${namePrefix}-docintel-pe-${environmentName}'
  location: location
  properties: {
    subnet: { id: resourceId('Microsoft.Network/virtualNetworks/subnets', vnetName, 'snet-pe') }
    privateLinkServiceConnections: [
      {
        name: 'docintel-plsc'
        properties: {
          privateLinkServiceId: docIntel.id
          groupIds: [ 'account' ]
        }
      }
    ]
  }
}

resource docIntelPeDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = if (enablePrivateNetworking) {
  parent: docIntelPe
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'cognitiveservices'
        properties: { privateDnsZoneId: docIntelDnsZone.id }
      }
    ]
  }
}

// --------------------------------------------------------------------------
// Observabilité (OBS-01..05) — module dédié. Garde Microsoft.Insights/* HORS de
// main.bicep (isolation quality-gate). Placé après les apps pour disposer de
// leurs .id. Le budget (OBS-04) reste subscription-scoped (infra/budget.bicep).
// --------------------------------------------------------------------------
// gatewayId/functionId passés via resourceId() calculé (PAS via .id symbolique) pour
// rompre le cycle : les apps consomment observability.outputs.connectionString en app
// setting, donc le module ne peut PAS dépendre symboliquement des ressources d'app.
// Les noms sont déterministes (gatewayName/funcName) -> resourceId() suffit pour le
// scope des alertes (BCP080 évité).
module observability 'observability.bicep' = {
  name: 'observability'
  params: {
    location: location
    namePrefix: namePrefix
    environmentName: environmentName
    gatewayId: resourceId('Microsoft.Web/sites', gatewayName)
    functionId: resourceId('Microsoft.Web/sites', funcName)
    gatewayName: gatewayName
    alertEmails: alertEmails
    teamsWebhookUrl: teamsWebhookUrl
    logAnalyticsRetentionDays: logAnalyticsRetentionDays
  }
}

output functionPrincipalId string = functionApp.identity.principalId
output gatewayPrincipalId string = gatewayApp.identity.principalId
output keyVaultName string = keyVault.name
// OBS-01 : chaîne de connexion App Insights (non high-value — T-03-08) câblée en app
// setting sur les deux apps. actionGroupId exposé pour le déploiement sub-scoped du budget (Plan 04).
output appInsightsConnectionString string = observability.outputs.connectionString
output actionGroupId string = observability.outputs.actionGroupId
