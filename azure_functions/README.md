# AC360 — Backend Azure Durable Functions

Orchestrateur du pipeline d'audit appelé par `scripts/api_server.py`
(`POST /api/audit`). Démarre une orchestration durable :

```
document_id → download (SharePoint/Graph) → OCR (Document Intelligence)
            → extraction champs canoniques → référence Fabric/Artus
            → comparaison typée → (FIC si ECART/INCERTAIN)
```

## Statut honnête (2026-06-08)

| Élément | État |
|---|---|
| Orchestration pure (`shared/audit_pipeline.py`) | **PROUVÉ** — testée en CI (`tests/azure_functions/`) |
| Moteur de comparaison (`scripts/fabric_audit_engine.py`) | **PROUVÉ** — testé |
| Wrapper Durable (`function_app.py`) | **CODE ÉCRIT — À VALIDER AU DÉPLOIEMENT** (nécessite le runtime) |
| Téléchargement SharePoint (`shared/sharepoint.py`) | **CODE ÉCRIT + TESTÉ** (Graph injecté ; allowlist ext, plafond taille, anti-traversal). Validation tenant réel : À VALIDER |
| OCR Document Intelligence | **RESSOURCE NON PROVISIONNÉE** (cf. README racine) |
| Accès Fabric (Entra ID) | **À VALIDER EN ENVIRONNEMENT RÉEL** |

> Aucune simulation n'est présentée comme réelle. Les points non branchés lèvent
> une erreur explicite plutôt que de retourner des données factices.

## Architecture testable

La logique métier est isolée dans `shared/audit_pipeline.py::run_audit`, une
fonction **pure à dépendances injectées** (`AuditDeps`). Elle ne fait aucune I/O :
téléchargement, OCR, requête Fabric et génération FIC sont injectés. Le wrapper
Durable (`function_app.py`) ne fait que brancher les implémentations réelles.
→ 100 % testable en CI sans runtime Durable ni accès cloud.

## Prérequis de déploiement

1. **Provisionner OCR** — ressource Azure AI Document Intelligence (voir README racine).
2. **Compte de stockage** — requis par Durable Functions (`AzureWebJobsStorage`).
3. **Fabric** — `FABRIC_SQL_ENDPOINT`, `FABRIC_DATABASE`, identité (Managed Identity ou SP) avec accès SQL.
4. **SharePoint/Graph** — implémenter `_download()` (permission `Files.Read.All` ou `Sites.Selected`).
5. **Variables d'app** : `AZURE_OCR_ENDPOINT`, `AZURE_OCR_KEY`, `FABRIC_*`, `JOBS_BASE_DIR`.

## Déploiement (exemple, à exécuter de votre côté)

```bash
# Local
func start

# Déploiement
func azure functionapp publish <nom-function-app>
```

## Contrat avec api_server.py

- `http_start` renvoie `create_check_status_response` → `{ id, statusQueryGetUri, ... }`.
- `scripts/api_server.py::trigger_audit` lit `id` (job_id) et `statusQueryGetUri`.
- Le statut est interrogé via l'API standard des instances Durable Functions.
