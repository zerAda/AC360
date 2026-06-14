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

// --------------------------------------------------------------------------
// Alerte métrique — 5xx passerelle (OBS-02). SingleResourceMultipleMetricCriteria
// sur la métrique Http5xx du namespace Microsoft.Web/sites, scopée sur gatewayId.
// severity 1, fenêtre 5 min, évaluation 1 min, seuil par défaut 5 (réglable).
// --------------------------------------------------------------------------
resource gw5xx 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${namePrefix}-gw-5xx-${environmentName}'
  location: 'global'
  properties: {
    description: 'Passerelle FastAPI : nombre de réponses HTTP 5xx au-dessus du seuil.'
    severity: 1
    enabled: true
    scopes: [ gatewayId ]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'http5xx'
          criterionType: 'StaticThresholdCriterion'
          metricNamespace: 'Microsoft.Web/sites'
          metricName: 'Http5xx'
          operator: 'GreaterThan'
          threshold: 5
          timeAggregation: 'Total'
        }
      ]
    }
    autoMitigate: true
    actions: [ { actionGroupId: ag.id } ]
  }
}

// --------------------------------------------------------------------------
// Alerte log (KQL) — échecs de dépendance OCR/Fabric/Graph (OBS-02). scheduledQueryRules
// scopée sur le composant App Insights. Cible les dépendances en échec vers
// cognitiveservices (Document Intelligence) / fabric / graph.microsoft.com.
// --------------------------------------------------------------------------
resource depFail 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${namePrefix}-dep-fail-${environmentName}'
  location: location
  properties: {
    displayName: 'AC360 — échecs de dépendance OCR/Fabric/Graph'
    description: 'Dépendances en échec vers Document Intelligence, Fabric ou Microsoft Graph.'
    severity: 1
    enabled: true
    scopes: [ appi.id ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    criteria: {
      allOf: [
        {
          query: 'dependencies | where success == false and (target has "cognitiveservices" or target has "fabric" or target has "graph.microsoft.com") | summarize c = count()'
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 3
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: { actionGroups: [ ag.id ] }
  }
}

// --------------------------------------------------------------------------
// Alerte log (KQL) — erreurs Functions / orchestration Durable (OBS-02, alerte
// distincte des échecs de dépendance). KQL sur exceptions + traces de niveau
// erreur portant les signatures d'échec d'orchestration. scopée sur App Insights.
// --------------------------------------------------------------------------
resource funcErr 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${namePrefix}-func-err-${environmentName}'
  location: location
  properties: {
    displayName: 'AC360 — erreurs Functions / orchestration'
    description: 'Exceptions worker Functions et échecs d\'orchestration Durable.'
    severity: 1
    enabled: true
    scopes: [ appi.id ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      allOf: [
        {
          query: 'union exceptions, (traces | where severityLevel >= 3) | where (cloud_RoleName has "func" or operation_Name has "orchestr" or message has "orchestration" or message has "activity") | summarize c = count()'
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 3
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: { actionGroups: [ ag.id ] }
  }
}

// --------------------------------------------------------------------------
// Test de disponibilité Standard (OBS-03) contre /health (endpoint anonyme de
// liveness). Tag hidden-link obligatoire vers le composant App Insights.
// Locations EU uniquement (RGP-06). [ASSUMED — les Id de localisation EU exacts
// sont vérifiés au provisioning : checkpoint opérateur Task 4 / A2.]
// --------------------------------------------------------------------------
resource webtest 'Microsoft.Insights/webtests@2022-06-15' = {
  name: '${namePrefix}-avail-${environmentName}'
  location: location
  kind: 'standard'
  tags: {
    'hidden-link:${appi.id}': 'Resource' // tag de liaison obligatoire vers le composant
  }
  properties: {
    SyntheticMonitorId: '${namePrefix}-avail-${environmentName}'
    Name: 'AC360 gateway /health'
    Enabled: true
    Frequency: 300
    Timeout: 30
    Kind: 'standard'
    RetryEnabled: true
    // [ASSUMED] Id de localisation EU à confirmer au provisioning (Task 4 / A2).
    Locations: [
      { Id: 'emea-nl-ams-azr' }
      { Id: 'emea-fr-pra-edge' }
    ]
    Request: {
      RequestUrl: 'https://${gatewayName}.azurewebsites.net/health'
      HttpVerb: 'GET'
    }
    ValidationRules: {
      ExpectedHttpStatusCode: 200
      SSLCheck: true
    }
  }
}

// Alerte de disponibilité couplée au webtest (OBS-03). metricAlert sur la métrique
// availabilityResults/availabilityPercentage, scopée sur webtest + composant.
resource webtestAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${namePrefix}-avail-alert-${environmentName}'
  location: 'global'
  tags: {
    'hidden-link:${appi.id}': 'Resource'
    'hidden-link:${webtest.id}': 'Resource'
  }
  properties: {
    description: 'Disponibilité du test /health sous le seuil.'
    severity: 1
    enabled: true
    scopes: [
      webtest.id
      appi.id
    ]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.WebtestLocationAvailabilityCriteria'
      webTestId: webtest.id
      componentId: appi.id
      failedLocationCount: 1
    }
    actions: [ { actionGroupId: ag.id } ]
  }
}

// --------------------------------------------------------------------------
// Workbook une-page (OBS-05). name = GUID (exigence Azure). serializedData chargé
// depuis workbook-ops.json (4 panneaux : audits 24h, taux d'erreur, p95 latence,
// budget % en tuile markdown/lien — les données coût ne sont pas dans App Insights).
// --------------------------------------------------------------------------
resource wb 'Microsoft.Insights/workbooks@2023-06-01' = {
  name: guid('ac360-ops-workbook', environmentName)
  location: location
  kind: 'shared'
  properties: {
    displayName: 'AC360 Ops — une page'
    category: 'workbook'
    sourceId: appi.id
    serializedData: loadTextContent('workbook-ops.json')
  }
}

output connectionString string = appi.properties.ConnectionString
output appInsightsId string = appi.id
output actionGroupId string = ag.id
