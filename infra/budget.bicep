// =============================================================================
// AC360 — Budget Cost Management (OBS-04)
//
// SUBSCRIPTION-scoped : Microsoft.Consumption/budgets se déploie au niveau
// souscription, PAS dans le main.bicep RG-scoped (Pitfall 4 — sinon erreur de
// scope au what-if). Déployé via un `az deployment sub create` séparé (Plan 04).
//
//   az deployment sub create --location <loc> -f infra/budget.bicep \
//     -p amount=<n> actionGroupId=<idDuGroupeActions> alertEmails="['a@b']"
//
// Le actionGroupId provient de la sortie observability.outputs.actionGroupId
// (exposée par main.bicep). Les notifications routent vers ce groupe d'actions
// (-> Teams + email — OBS-04).
// =============================================================================

targetScope = 'subscription'

@description('Plafond budgétaire mensuel (devise de la souscription).')
param amount int = 200

@description('Resource ID du groupe d\'actions (sortie observability) vers lequel router les notifications de budget.')
param actionGroupId string

@description('Adresses email destinataires des notifications de budget.')
param alertEmails array = []

resource budget 'Microsoft.Consumption/budgets@2024-08-01' = {
  name: 'ac360-prod-monthly'
  properties: {
    amount: amount
    category: 'Cost'
    timeGrain: 'Monthly'
    timePeriod: {
      // Premier jour d'un mois, >= 2017-06-01. [ASSUMED] L'opérateur confirme le
      // mois de démarrage (>= mois courant) au provisioning (Task 4 / OBS-04).
      startDate: '2026-07-01T00:00:00Z'
    }
    notifications: {
      Actual_GreaterThan_80_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        thresholdType: 'Actual'
        contactEmails: alertEmails
        contactGroups: [ actionGroupId ] // route vers le groupe d'actions -> Teams + email
      }
      Forecasted_GreaterThan_100_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        thresholdType: 'Forecasted'
        contactEmails: alertEmails
        contactGroups: [ actionGroupId ]
      }
    }
  }
}
