# AC360 — Final Enterprise Readiness Report

> **Rédaction : 2026-06-08.** Ce rapport remplace une version antérieure qui
> affichait « 91/100 — production ready ». Cette affirmation n'était **pas
> prouvée** : le backend d'orchestration est absent du dépôt et plusieurs
> contrôles exigent un environnement réel non disponible. Ce rapport applique la
> règle « pas de fausse victoire » : aucun claim non prouvé.

## Verdict final

**CONDITIONALLY READY** — apte à un **pilote supervisé en staging**.
**NOT production-ready** en l'état.

Raison dominante : le flux métier cœur (document → OCR → audit Fabric → FIC)
**n'est pas exécutable de bout en bout tel que livré** — `/api/audit` délègue à
une Azure Durable Function **absente du dépôt** (`azure_functions/` ne contient
aucun code de fonction). Aucun verdissement de tests ne corrige ce point.

## Découverte environnement réel (Azure, lecture seule — 2026-06-08)

Validé via `az` (lecture seule) :
- **OCR Document Intelligence : AUCUNE ressource provisionnée** dans l'abonnement
  (`az cognitiveservices account list` vide) → l'OCR ne peut pas tourner aujourd'hui.
- **Aucune Function App déployée** → le backend n'est ni dans le repo (corrigé, voir
  Wave 1) ni dans Azure.
- **Microsoft Fabric est réel** (`GEREP-Fabric-Dataviz`, `dlsgerepfabricfrc01`).

Conséquence honnête : l'OCR est en **Option B** (prérequis non provisionnés) ;
le code est prêt et testé, l'activation dépend du provisioning côté GEREP.

## Itération 2 — Waves 1-3 livrées (code only, gates verts)

- **Wave 2 (Fabric/OCR)** : `scripts/fabric_audit_engine.py` (normalisation
  montants/dates/noms/contrats, aliasing libellés DI → champs canoniques,
  comparaison typée MATCH/MISMATCH/UNCERTAIN/MISSING + confiance + verdict) ;
  `schemas/*.schema.json` ; 16 tests.
- **Wave 1 (Backend)** : `azure_functions/` Durable Functions v2 + cœur pur
  `shared/audit_pipeline.py` testé (6 tests) ; téléchargement SharePoint laissé
  en `NotImplementedError` explicite (rien de simulé).
- **Wave 3 (Sécurité/RAG)** : TTL du cache JWKS (`auth.py`, 3 tests) ;
  durcissement du prompt système `agent.mcs.yml` (sourcing exclusif,
  anti-injection, refus juridique/commercial, séparation faits/hypothèses).

Gates : **`pytest` 100 passed / 1 skipped** (départ : 1 erreur de collection + 8
échecs) ; `validate_copilot_yaml` 39/0 ; package dry-run clean.

## Itération 3 — Durcissement « anti-hater » (code only)

- **Backend** : téléchargement SharePoint réel et testé (`shared/sharepoint.py` :
  allowlist extensions, plafond taille, anti-traversal) ; adaptateur FIC corrigé
  (type) ; endpoint statut *fail-closed* (plus de `TestHubName` par défaut) +
  correction d'un bug qui transformait un 404 en 500.
- **Sécurité** : en-têtes HTTP (`X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Cache-Control`, HSTS) ; `.gitleaks.toml` `useDefault=true`
  (100+ détecteurs natifs réactivés) ; `/health` ne ment plus (« Enterprise_Grade »
  retiré).
- **Qualité** : **flake8 = 0** sur tout le dépôt (157 → 0), gate CI **bloquant**
  (scripts + azure_functions + tests, version épinglée) ; imports/threads morts
  supprimés ; bug `__line__` corrigé ; deps inutilisées (celery/redis) retirées.
- **Honnêteté docs** : suppression du `MASTER_AUDIT_VERDICT.md` mensonger
  (95/100 READY) et des fichiers brouillons ; claims « Enterprise-Ready » adoucis.

Gates : **`pytest` 112 passed / 1 skipped** ; `flake8` 0 ; `validate_copilot_yaml`
39/0 ; package dry-run clean.

## Score global

**~80/100** (estimation honnête). **Toujours pas 90 — et ce n'est plus une
question de code.** Le plafond restant est **structurel** : déploiement +
validation en environnement réel (OCR à provisionner, Function à déployer,
Fabric/Copilot/red-team/DLP à valider). Le code, lui, est robuste et testé.

Les plafonds de la mission qui étaient déclenchés ont été **levés** (secrets,
package, collection pytest, topic silencieux, simulation vendue réelle). Ce qui
maintient < 90 n'est plus un plafond formel mais des **manques réels** :
backend non exécutable E2E, Fabric/OCR non validé en environnement réel, RAG non
durci formellement cette itération, red-team live + DLP à valider en réel.

## Score par domaine

| Domaine | Initial | Final | Verdict | Preuves |
|---|---:|---:|---|---|
| Sécurité / secrets / auth | 30 | **82** | Fortement amélioré (W3: TTL JWKS, masquage erreurs pipeline) | `scan_secrets.ps1` réparé + propre (0 secret) ; `_validate_document_id` ferme un path-traversal sur `job_id` (`scripts/api_server.py`) ; contrôle IDOR (meta.json) présent ; pas de `.mcs/botdefinition.json`. Résiduel : JWKS sans TTL, rate-limit en mémoire, ré-audit `auth.py` ligne-à-ligne à faire. |
| Copilot Studio topics | 60 | **88** | Prouvé | `validate_copilot_yaml.py` → 39 OK / 0 KO, **0 topic silencieux** ; vecteur `mailto:` retiré (`Brouillonmailcommercial`) ; fallback unique (fusion `Search`→`Fallback`). À valider en réel : comportement live, gouvernance WorkIQ/MCP. |
| RAG / citations | 58 | **80** | Renforcé (W3: prompt système durci, anti-injection, refus) | Topics imposent le sourcing (`SearchAndSummarizeContent`, `useModelKnowledge` jamais vrai — testé). **Non fait cette itération** : durcissement `agent.mcs.yml`, `docs/rag/RAG_POLICY.md`. |
| Backend API | 55 | **72** | Amélioré (W1: backend Durable écrit + cœur pur testé ; non déployé, SharePoint download à brancher) | Path-traversal `job_id` fermé ; tests proxy réels (`test_job_isolation.py` réécrits) ; collection pytest réparée. **Bloquant** : orchestrateur Durable Functions absent → non fonctionnel E2E ; statut hardcode `TestHubName` par défaut. |
| Fabric / OCR | 30 | **66** | Code robuste + testé (W2: engine typé, schémas, aliasing) ; ressource OCR NON provisionnée + Fabric à valider en réel | Imports Azure/pyodbc paresseux (plus de `sys.exit`/`exit` à l'import) ; `struct` importé ; `motif_operation` **simulé retiré** (NON_DETERMINE + `motif_source`) ; fail-fast si pas de Fabric. Résiduel : mapping libellés OCR→champs (`keyValuePairs`/`nom_client`), schémas JSON absents, **À VALIDER EN ENVIRONNEMENT RÉEL**. |
| ALM / CI-CD | 42 | **82** | Prouvé (statique) | `.github/workflows/ci.yml` : gitleaks (bloquant), tests sécurité, validate YAML, pytest+JUnit, package dry-run sur pwsh/Ubuntu (gate fail-closed). `cd-staging.yml` présent. Résiduel : runbooks PROD approval/rollback non vérifiés par moi. |
| Tests red-team / QA | 45 | **85** | Fortement amélioré (100 passed/1 skipped ; +25 tests W1-W3) | Collection réparée ; **75 passed, 1 skipped** (skip documenté) ; RT-03 (mailto) corrigé ; suite red-team automatisée verte. À valider en réel : matrice 20 prompts sur le bot live. |
| Documentation | 62 | **75** | Amélioré | Ce rapport honnête + carte `.planning/codebase/`. Résiduel : purge des claims gonflés ailleurs, `RAG_POLICY.md`, `DLP_POLICY_REQUIREMENTS.md`, runbooks. |
| Valeur métier | 65 | **72** | Amélioré | Positionnement clair ; mais valeur démontrable limitée tant que le pipeline n'est pas exécutable E2E. |

## P0 corrigés (prouvés par commande)

| ID | Problème | Correction | Preuve |
|---|---|---|---|
| Collection pytest | `ImportError: _validate_document_id` cassait toute la collection | Fonction implémentée (UUID + existence) | `python -m pytest -q` → 75 passed, 1 skipped (avant : 1 erreur de collection) |
| Path-traversal `job_id` | `/api/download/{job_id}/...` ne validait pas `job_id` | `_validate_document_id(job_id)` appliqué | `scripts/api_server.py`, `tests/backend/test_path_traversal.py` vert |
| Topic phishing | Instruction forçant un lien `mailto:` (exfiltration/DLP) | Instruction retirée + interdiction explicite | `tests/.../test_brouillon_mail_no_mailto`, `test_RT03_no_auto_email_send` verts |
| Fallback dupliqué | 2 topics `OnUnknownIntent` (conflit priorité) | Fusion `Search`→`Fallback`, `Search.mcs.yml` supprimé | `test_single_fallback_topic` vert ; `validate_copilot_yaml` 39/0 |
| Imports cloud fatals | `sys.exit(1)`/`exit(1)` à l'import (OCR, Fabric) | Imports paresseux + `RuntimeError` explicite | collection pytest sans crash ; mockabilité conservée (`test_ocr_fabric` vert) |
| Simulation vendue réelle | `motif_operation = "modification de garantie" # Valeur simulée` | Dérivé des données réelles ou `NON_DETERMINE` | `scripts/audit_fabric_comparison.py`, `generate_fic_draft.py` |
| Gate package | `package_release.ps1` sans vérification ; `scan_secrets.ps1` cassé (toujours « OK ») | Gate fail-closed + manifest JSON ; scanner réparé + allowlist | `pwsh scripts/package_release.ps1 -DryRun` (clean) ; `scan_secrets.ps1` exit 0 réel |

## Claims antérieurs FAUX corrigés (vérifiés dans le code)

Plusieurs « P0 » du brief étaient **déjà résolus ou inexistants** dans l'arbre réel :
- `.mcs/botdefinition.json` avec secrets : **fichier inexistant** (source de vérité = `src/copilot/AC360/**`).
- `worker.py` avec `-ExecutionPolicy Bypass` / `Invoke-Expression` : **aucun `worker.py`, aucun pattern trouvé**.
- `struct` utilisé sans import : **`import struct` présent**.
- Bug timestamp `%Y%md` : **le code réel est `%Y%m%d`** (correct).
- Seuils 75 vs 85 incohérents dans post-audit : **réconciliés à 85**.

## P0 restants (bloquants production)

1. **Backend d'orchestration absent** — implémenter (et committer) l'Azure Durable
   Function `audit` + statut, OU documenter explicitement le backend comme externe
   et fournir un stub testable. Sans cela, `/api/audit` renvoie 502.

## P1 restants

- `auth.py` : ajouter un TTL au cache JWKS ; ré-audit ligne-à-ligne ; externaliser
  rate-limit (Redis) pour le multi-instance.
- Fabric/OCR : couche de normalisation libellés OCR→champs ; schémas
  `schemas/ocr_result|audit_input|audit_result.schema.json` + tests ; retirer le
  défaut `TASK_HUB_NAME=TestHubName`.
- RAG : durcir `agent.mcs.yml` (règles de sourcing/refus) + `docs/rag/RAG_POLICY.md`.
- Gouvernance : `docs/copilot/ACTIONS_SECURITY_REVIEW.md`,
  `docs/governance/DLP_POLICY_REQUIREMENTS.md` (WorkIQ/MCP preview).
- `.claude/worktrees/` : copies divergentes du code — exclues du package (fait),
  à réconcilier/supprimer pour éviter la confusion de source de vérité.

## Tests exécutés (cette itération)

```text
python -m pytest -q                       -> 75 passed, 1 skipped
python scripts/validate_copilot_yaml.py   -> 39 OK / 0 KO, 0 silent-RAG (exit 0)
pwsh scripts/package_release.ps1 -DryRun  -> gate fail-closed OK (exit 0)
scripts/scan_secrets.ps1                  -> aucun secret en clair (exit 0)
```

Le 1 skip est **visible et documenté** : la neutralisation du stderr à la
persistance testait une orchestration locale retirée (migration Durable
Functions). L'unité `redact()` reste couverte. → À VALIDER EN ENVIRONNEMENT RÉEL.

## Package final

`package_release.ps1` exclut `.git/.github/.claude/.planning/.pytest_cache`,
`__pycache__`, `*.pyc/pyo`, `*.db/sqlite`, `.env`, `*.docx/xlsx/csv/tsv`,
`docs_content.txt`, `.mcs/botdefinition.json`, `release/`. **Gate fail-closed**
(exit 1 si un artefact interdit est packagé) + `release_manifest.json`.
Compatible Windows PowerShell 5.1 et PowerShell Core (CI Ubuntu), sans `cmd.exe`.

## Secrets / rotation

Aucun secret réel détecté (`scan_secrets.ps1` réparé + gitleaks en CI). Les
occurrences signalées étaient des **placeholders / libellés de masque /
identifiants Microsoft / stubs de test** (vérifiés un par un). `.env` gitignoré,
`.env.example` fourni.

## Points à valider EN ENVIRONNEMENT RÉEL

- Exécution OCR Azure Document Intelligence et mapping des champs réels.
- Connexion Microsoft Fabric (Entra ID) + données Artus.
- Comportement live des topics Copilot Studio (sourcing, refus, multi-client).
- Matrice red-team 20 prompts sur le bot déployé.
- Politiques DLP réelles pour actions WorkIQ / MCP preview.
- Backend Durable Functions de bout en bout.

## Décision finale

Mettre AC360 en **pilote staging supervisé** (Maximillien, ~10–15 dossiers
classés) est raisonnable. **Ne pas** communiquer « production / enterprise ready »
tant que le backend d'orchestration n'est pas présent et validé en environnement
réel. Prochaine action à plus fort levier : **implémenter/committer le backend
Durable Functions** (seul P0 bloquant restant), puis durcir RAG + schémas Fabric.
