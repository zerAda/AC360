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
| App Service plan (passerelle) | `ac360-gw-plan` | **F1 (gratuit)** Linux | ✅ |
| Passerelle API (FastAPI) | `ac360-gateway-staging` | Python 3.11 | ✅ Running |

- Endpoint OCR : `https://ac360-docintel-staging.cognitiveservices.azure.com/`
- Function host : `https://ac360-func-staging.azurewebsites.net`
- Passerelle : `https://ac360-gateway-staging.azurewebsites.net`
- Task hub Durable réel : `ac360funcstaging`

## Posture sécurité transport (vérifiée)

| Contrôle | Function | Passerelle | Stockage |
|---|---|---|---|
| `httpsOnly` (HTTP refusé) | ✅ true | ✅ true | n/a |
| TLS minimum | 1.2 | 1.2 | 1.2 |
| FTPS | désactivé | désactivé | n/a |
| Accès blob public | n/a | n/a | désactivé |

En-têtes de la passerelle (vérifiés sur `/health`) : `Strict-Transport-Security:
max-age=31536000; includeSubDomains`, `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, `Cache-Control: no-store`. **Aucun chemin HTTP en clair.**

## Passerelle API — DÉPLOYÉE, AUTH ACTIVE ET VÉRIFIÉE

- `GET /health` → **HTTP 200** (public)
  `{"status":"healthy","version":"3.0.0","auth":"entra-id-jwt","orchestration":"azure-durable-functions"}`
- `POST /api/audit` **sans token** → **HTTP 401** (auth JWT Entra appliquée). ✅

## Identité & secrets (Key Vault)

| Élément | Valeur |
|---|---|
| App registration Entra | `AC360-API-staging`, `CLIENT_ID = 5399f31e-c4d5-46db-b620-033e59abda84`, scope `Audit.Trigger` (token v2) |
| Identité managée Function | `710e845c-...` — **Sites.Selected** (Graph) accordé (accès SharePoint moindre privilège) |
| Identité managée Passerelle | `be67f9db-...` |
| **Key Vault** | `ac360-kv-staging` (RBAC, retention 90 j) |
| Secrets stockés | `ocr-key`, `function-key` |
| Références | Function `AZURE_OCR_KEY` et Passerelle `AZURE_FUNCTION_KEY` = `@Microsoft.KeyVault(...)` — **aucune clé en clair** dans les app settings ; résolution via MI (Key Vault Secrets User). |

> Identifiants non secrets (`CLIENT_ID`, `TENANT_ID`, `TASK_HUB_NAME`, URLs) restent
> en app settings ; seules les vraies clés sont en Key Vault.

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

## Reste à câbler avant E2E complet

Rôles Entra de l'opérateur GEREP : **Fabric Administrator** + **Power Platform
Administrator** (mais PAS Application/Cloud-App/Global Admin → ne peut pas créer
d'app registration).

| Élément | Action | Qui |
|---|---|---|
| **App registration Entra** | créer `AC360-API-staging` (single tenant, exposer scope `Audit.Trigger`) → fournir `CLIENT_ID` ; puis `az webapp config appsettings set ... CLIENT_ID=<id>` sur la passerelle | **Global Admin GEREP** (bloquant auth) |
| **Fabric** | définir `FABRIC_SQL_ENDPOINT` + `FABRIC_DATABASE` (app settings Function) ; table `Artus_Contrats` accessible | **opérateur** (Fabric Admin ✅) |
| **SharePoint** | activer l'identité managée de la Function, lui accorder Graph `Files.Read.All`/`Sites.Selected`, définir `SHAREPOINT_DRIVE_ID` | Global Admin (consent) + opérateur |
| **Copilot Studio** | importer `src/copilot/AC360/**` et pointer vers `https://ac360-gateway-staging.azurewebsites.net` | **opérateur** (Power Platform Admin ✅) |

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

## ✅ E2E COMPLET SUR DONNÉES RÉELLES (2026-06-09)

Pipeline vérifié de bout en bout sur Azure, document SharePoint réel + données
Fabric réelles :

| Étape | Résultat |
|---|---|
| validate / download (SharePoint MI) / ocr (F0) / extract | ✅ |
| fetch_reference (OneLake Delta, pur Python) | ✅ lecture réelle de tbl_super_product_client_api_gold |
| Verdict | CLIENT_NON_TROUVE (doc de test fictif « GEREP SA » -> correct) |

orchestration runtimeStatus=Completed, error=null.

### Fabric — accès OneLake
- Workspace DEV : GEREP_Fabric_DEV (a1dad2a0-...), Lakehouse_Gold (832729f5-...).
- Table de référence : tbl_super_product_client_api_gold (noms lisibles + SIRET ;
  la table client agrégée est hashée RGPD).
- Identité managée de la Function : rôle **Contributor** sur le workspace
  (Viewer donne le SQL endpoint mais PAS la lecture OneLake directe).
- Tenant setting « OneLakeForThirdParty » : déjà activé.

### Durcissement production recommandé
- Remplacer le rôle workspace Contributor par un **rôle d'accès aux données
  OneLake au niveau item** (lecture seule sur la seule table de référence) —
  moindre privilège.
- Évolution scalable : exposer la table via l'**API GraphQL Fabric** (requête
  filtrée côté serveur, déjà utilisée dans le workspace).

### Durcissement appliqué (2026-06-09) — moindre privilège Fabric
L'identité managée de la Function n'est plus **Contributor**. Elle a désormais :
- rôle workspace **Viewer** (minimal) ;
- rôle d'accès aux données OneLake **DefaultReader (lecture seule, ReadAll)** sur
  Lakehouse_Gold.
→ Lecture des données réelles confirmée (E2E Completed), **aucun accès en
écriture**. OCR maintenu en **F0 (gratuit)** — pas de S0.
