// =============================================================================
// AC360 — Observabilité as Code (OBS-01..05)
//
// Module appelé par main.bicep (RG-scoped). Garde TOUS les Microsoft.Insights/*
// HORS de main.bicep (isolation quality-gate / PATTERNS.md ln 75, 155-158).
//
// Pose le prérequis OBS-01 (composant App Insights workspace-based + Log Analytics
// workspace — main.bicep n'en a AUCUN aujourd'hui), un groupe d'actions (email +
// webhook Teams), les alertes d'échec (5xx passerelle + échecs de dépendance
// OCR/Fabric/Graph + erreurs Functions/orchestration), un test de disponibilité
// Standard sur /health + son alerte, et le workbook une-page (OBS-05).
//
// Sorties consommées : connectionString (-> app settings des deux apps, main.bicep),
// actionGroupId (-> budget.bicep, déploiement sub-scoped séparé).
// =============================================================================

@description('Région Azure.')
param location string

@description('Préfixe des ressources.')
param namePrefix string = 'ac360'

@description('Nom court d\'environnement.')
param environmentName string = 'prod'

@description('Resource ID de la passerelle (App Service FastAPI) — cible des alertes 5xx.')
param gatewayId string

@description('Resource ID de la Function (worker Durable) — réservé pour de futures alertes ciblées.')
param functionId string

@description('Nom de la passerelle (pour l\'URL du test de disponibilité RequestUrl).')
param gatewayName string

@description('Adresses email destinataires des alertes (groupe d\'actions). Une entrée emailReceivers par adresse.')
param alertEmails array = []

@description('URL du webhook Teams (sink FinOps + alertes — OBS-04). Power Automate / Workflows (les connecteurs O365 legacy sont en cours de retrait). Vide => pas de webhookReceiver.')
param teamsWebhookUrl string = ''

// Noms de ressources — convention main.bicep (var <name> = '${namePrefix}-<kind>-${environmentName}').
var lawName = '${namePrefix}-law-${environmentName}'
var appiName = '${namePrefix}-appi-${environmentName}'
var actionGroupName = '${namePrefix}-ag-${environmentName}'

// --------------------------------------------------------------------------
// Log Analytics workspace (OBS-01 prérequis). retentionInDays:30 = rétention
// EU-region courte délibérée (RGP-04). SKU PerGB2018 standard.
// --------------------------------------------------------------------------
resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: lawName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30 // RGP-04 : rétention EU courte délibérée
  }
}

// --------------------------------------------------------------------------
// Composant App Insights workspace-based (OBS-01). WorkspaceResourceId obligatoire :
// le mode classic est retiré (T-03-11). kind 'web' + Application_Type 'web'.
// --------------------------------------------------------------------------
resource appi 'Microsoft.Insights/components@2020-02-02' = {
  name: appiName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: law.id // workspace-based (classic retiré — T-03-11)
  }
}

// --------------------------------------------------------------------------
// Groupe d'actions (email + webhook Teams). location 'global' (groupe d'actions).
// groupShortName <= 12 caractères. useCommonAlertSchema=true => pas de PII brute
// dans le payload (T-03-10). webhookReceivers gardé sur teamsWebhookUrl non vide.
// NB OBS-04 : Microsoft retire les connecteurs O365 ; l'opérateur fournit une URL
// Power Automate / Workflows. La forme webhookReceivers reste correcte quelle que
// soit l'URL fournie (RESEARCH A3 / Open Q2 — checkpoint opérateur Task 4).
// --------------------------------------------------------------------------
resource ag 'Microsoft.Insights/actionGroups@2024-10-01-preview' = {
  name: actionGroupName
  location: 'global'
  properties: {
    groupShortName: 'ac360ops' // <= 12 caractères
    enabled: true
    emailReceivers: [for (e, i) in alertEmails: {
      name: 'email${i}'
      emailAddress: e
      useCommonAlertSchema: true
    }]
    webhookReceivers: empty(teamsWebhookUrl) ? [] : [
      {
        name: 'teams'
        serviceUri: teamsWebhookUrl
        useCommonAlertSchema: true
      }
    ]
  }
}

output connectionString string = appi.properties.ConnectionString
output appInsightsId string = appi.id
output actionGroupId string = ag.id
