# AC360 — Déploiement STAGING (état réel)

> Environnement de **pré-production** déployé et vérifié le 2026-06-09. Tiers
> gratuits/dev. Ce document décrit ce qui est **réellement en ligne** (prouvé par
> commande) et ce qui reste à câbler avant la promotion en production.

## Ressources Azure provisionnées (RG `rg-ac360-staging`, France Central)

| Ressource | Nom | Tier | État |
|---|---|---|---|
| Document Intelligence (OCR) | `ac360-docintel-staging` | **F0 (gratuit)** | ✅ en ligne |
| Compte de stockage (Durable) | `ac360stagingstore` | Standard_LRS | ✅ |
| Function App (backend) | `ac360-func-staging` | Consumption Linux Python 3.11 | ✅ Running |
| Application Insights | `ac360-func-staging` | gratuit | ✅ |

- Endpoint OCR : `https://ac360-docintel-staging.cognitiveservices.azure.com/`
- Function host : `https://ac360-func-staging.azurewebsites.net`
- Task hub Durable réel : `ac360funcstaging`

## Backend Durable Functions — DÉPLOYÉ ET VÉRIFIÉ EN LIGNE

Trois fonctions indexées et actives :

| Fonction | Déclencheur | URL |
|---|---|---|
| `http_start` | HTTP `/api/audit` + durableClient | `https://ac360-func-staging.azurewebsites.net/api/audit` |
| `audit_orchestrator` | orchestrationTrigger | — |
| `activity_run_audit` | activityTrigger | — |

**Preuve E2E (smoke test réel) :**
- `POST /api/audit {"document_id":"smoke-test-001"}` → **HTTP 202** + `{ id, statusQueryGetUri }`
  (contrat attendu par `scripts/api_server.py`).
- Statut de l'orchestration → `runtimeStatus: Completed`, `output.status: Failed`,
  `error: "SHAREPOINT_DRIVE_ID manquant (configuration requise)"`.

→ La chaîne `http_start → orchestrator → activity → run_audit` fonctionne sur
Azure. Le comportement **fail-closed honnête** est confirmé : aucune donnée
fabriquée, aucun secret divulgué, aucun crash — l'orchestration signale
proprement le prérequis manquant.

## App settings configurés

- `AZURE_OCR_ENDPOINT`, `AZURE_OCR_KEY` (OCR F0 câblé)
- `TASK_HUB_NAME=ac360funcstaging`
- `JOBS_BASE_DIR=/home/site/jobs`
- `SCM_DO_BUILD_DURING_DEPLOYMENT=true` (build Python distant)
- `AzureWebJobsStorage` (auto, compte de stockage)

## Reste à câbler avant E2E complet (prérequis côté GEREP)

| Élément | Action | Qui |
|---|---|---|
| **Fabric** | définir `FABRIC_SQL_ENDPOINT` + `FABRIC_DATABASE` ; table `Artus_Contrats` accessible | GEREP |
| **SharePoint** | définir `SHAREPOINT_DRIVE_ID` ; accorder à l'identité managée de la Function la permission Graph `Files.Read.All` / `Sites.Selected` | GEREP |
| **Passerelle API** | déployer `scripts/api_server.py` (App Service / Container) + app registration Entra (`TENANT_ID`/`CLIENT_ID`) pour l'auth | à planifier |
| **Copilot Studio** | importer `src/copilot/AC360/**` dans l'environnement réel et pointer vers l'URL de la passerelle | GEREP |

## Redéploiement du backend

```powershell
pwsh azure_functions/build_package.ps1
az functionapp deployment source config-zip -g rg-ac360-staging -n ac360-func-staging `
  --src azure_functions/.build/ac360_func.zip --build-remote true
```

## Coût

Staging sur F0 (OCR) + Consumption (Functions) + stockage standard ≈ quelques
centimes à quelques euros/mois à faible volume. Aucune ressource « production »
(S0, plan premium) n'a été créée.
