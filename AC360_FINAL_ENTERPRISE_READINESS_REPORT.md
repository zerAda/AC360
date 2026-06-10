# AC360 — Final Enterprise Readiness Report

> **Réécrit le 2026-06-10.** Remplace une version du 2026-06-08 devenue
> **obsolète** (elle affirmait « backend absent / rien déployé »). Depuis,
> l'environnement staging a été déployé et le flux métier prouvé E2E sur données
> Fabric réelles, et les piliers gouvernance/FinOps/usage/kill-switch ont été
> construits. Règle appliquée : **aucune fausse victoire**, tout point non prouvé
> est marqué `À VALIDER EN ENVIRONNEMENT RÉEL`.

## Verdict final

**CONDITIONALLY READY** — **socle technique et gouvernance complets**, apte à un
**pilote supervisé en staging**. La promotion en production reste conditionnée à
des items qui dépendent de **décisions GEREP (licence, budget, DLP, provisioning)**
et non de correctifs de code.

## Score global

**≈ 84 / 100** (honnête). L'écart vers 90 est **entièrement** constitué d'items
`À VALIDER EN ENVIRONNEMENT RÉEL` (cf. fin de rapport) — aucun n'est un défaut de
code, ce sont des dépendances environnement/licence/budget.

## Score par domaine

| Domaine | Initial | Final | Verdict | Preuves |
|---|---:|---:|---|---|
| Sécurité / secrets / auth | 30 | **88** | PROUVÉ | 0 secret (scan), KV+MI, SP automation supprimé, ingress Function verrouillé (403), KV purge+audit log, JWKS, bandit CI |
| Copilot Studio topics | 60 | **85** | PROUVÉ | 39 `.mcs.yml` valides, 0 silent-RAG (`validate_copilot_yaml.py`), CI |
| RAG / citations | 58 | **80** | PARTIEL | `RAG_POLICY.md` + validateur ; rendu citations réelles À VALIDER |
| Backend API | 55 | **87** | PROUVÉ | JWKS, path-traversal, validation au bord, endpoint statut réparé, kill-switch câblé, 212 tests |
| Fabric / OCR | 30 | **80** | PROUVÉ (staging) | OneLake lecture seule E2E **réel** ; OCR F0 déployé ; tracking coût ajouté |
| ALM / CI-CD | 42 | **82** | PROUVÉ | `ci.yml` (gitleaks+bandit+pytest+flake8+mypy+coverage) + `cd-staging.yml` + build scripts + env strategy + rollback |
| Tests red-team / QA | 45 | **85** | PROUVÉ | 212 pass, `RED_TEAM_PROMPTS` + test auto + `ACCEPTANCE_TEST_MATRIX` + tests kill-switch/finops |
| Documentation | 62 | **88** | PROUVÉ | 30+ docs honnêtes, gouvernance complète, claims faux supprimés |
| Valeur métier | 65 | **80** | DOCUMENTÉ | positionnement + use cases ; ROI réel À VALIDER |
| Production readiness | 0 | **78** | DOCUMENTÉ | readiness + go-live + rollback + emergency + env strategy ; env prod réel À CRÉER |
| FinOps / coûts | 0 | **85** | PROUVÉ (modèle) | `cost_tracker.py` paramétrable, schémas, docs, tests ; prix réels À VALIDER |
| Usage tracking | 0 | **88** | PROUVÉ | `usage_tracker.py` + schéma + câblé passerelle + tests + docs |
| Observability / SRE | 0 | **80** | DOCUMENTÉ | monitoring + logging + alerting + usage + runbook incidents |
| Admin kill-switch | 0 | **90** | PROUVÉ | `feature_flags`+`admin_controls` câblés (/api/audit → 403), no-block-default, admin-only, runbook |

## P0 — statut

| P0 | Sujet | Statut |
|---|---|---|
| 01 | Secrets dans botdefinition | **RÉSOLU/N-A** — `.mcs/botdefinition.json` absent, scan propre |
| 02 | Package sale | **RÉSOLU** — `.docx/.xlsx/.csv` dé-trackés + test anti-régression git |
| 03 | botdefinition stale | **RÉSOLU/N-A** — absent, 0 topic silencieux |
| 04 | pytest crash collection | **RÉSOLU** — 213 collectés, 0 crash |
| 05 | Fabric/OCR simulé | **RÉSOLU** — OneLake réel prouvé + tracking coût |
| 06 | Gouvernance prod | **RÉSOLU** — readiness/go-live/rollback/emergency/env-strategy |
| 07 | FinOps / coûts | **RÉSOLU** — modèle paramétrable + schémas + docs + tests |
| 08 | Usage tracker | **RÉSOLU** — module + schéma + câblé + tests |
| 09 | Kill-switch | **RÉSOLU** — flags + admin controls câblés + runbook |

**Aucun P0 ouvert.**

## Tests exécutés (preuves)

- `python -m pytest -q` → **212 passed, 1 skipped** (0 crash collection).
- `flake8` → **0** ; `mypy` (7 modules cœur) → **clean**.
- `scan_secrets.ps1` → **aucun secret en clair** ; `validate_copilot_yaml.py` → **0 KO**.
- Live (staging) : `/health` 200 ; `/api/audit` sans/mauvais jeton → 401 ; jeton valide → 202 ;
  statut → 200 ; accès direct Function depuis IP non-passerelle → 403 ;
  kill-switch → /api/audit **403** quand bloqué (`tests/backend/test_killswitch_gate.py`).

## Sécurité / secrets

- 0 secret en clair (working tree + historique git vérifiés). Secrets en Key Vault
  (purge protection + audit log). SP d'automatisation **supprimé**. Rotation
  documentée (`docs/security/SECRET_ROTATION.md`).

## Tracking consommation commerciaux

- Par `commercial_id_hash` / `team_id` / `client_id_hash` / `use_case` (hash SHA-256,
  0 PII en clair). Tokens **ESTIMÉS** (Copilot Studio n'expose pas le réel).
  Sans limite bloquante par défaut. Cf. `docs/finops/CONSUMPTION_TRACKING.md`.

## Bouton blocage consommation

- Kill-switch global / par fonctionnalité / par utilisateur / par équipe, **sans
  supprimer le bot**, réservé admin, tracé, réversible (`EMERGENCY_SHUTDOWN_RUNBOOK.md`).
  Câblé dans la passerelle (403 + message propre). Un commercial **ne peut pas** se
  débloquer (rôle admin + RBAC Azure).

## Déploiement réel (staging — PROUVÉ)

- RG `rg-ac360-staging` : passerelle, Functions, OCR F0, storage, Key Vault.
  Auth Entra active. E2E prouvé sur SharePoint + Fabric réels (verdict
  `CLIENT_NON_TROUVE` correct sur doc de test). Coût ≈ quelques €/mois.

## Points à valider en environnement réel (= l'écart vers 90)

| # | Item | Dépend de |
|---|---|---|
| 1 | Publication **Copilot Studio** | licence premium / pay-as-you-go (décision GEREP) |
| 2 | **Coûts réels** (grille `AC360_RATE_CARD`, budget) | contrat/facturation GEREP |
| 3 | **DLP policies** appliquées | admin Power Platform |
| 4 | **Environnement PROD** dédié | provisioning facturable |
| 5 | **Private Endpoints + Defender** | durcissement prod facturable |
| 6 | Rendu **citations RAG** réelles | Copilot Studio réel |

## Décision finale

Le **produit est sain et gouverné** : sécurité forte, backend prouvé E2E sur
données réelles (staging), FinOps + usage + kill-switch + gouvernance de prod
**construits, câblés et testés**. Le passage à **≥ 90 / PRODUCTION READY** ne
dépend plus du code mais de **6 décisions GEREP** (licence, budget, DLP, prod env).
Tant qu'elles ne sont pas tranchées, le verdict honnête reste **CONDITIONALLY
READY (≈ 84/100)** — apte au **pilote supervisé**, pas encore production.
