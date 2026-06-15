# RGP-03 — Politique de rétention des artefacts (source canonique)

**Exigence :** RGP-03 (rétention des artefacts job/OCR/FIC, définie ET appliquée).
**Statut :** appliquée (deux points d'enforcement) — voir §3.
**Dernière MAJ :** 2026-06-14.

> Ce document est la **source de vérité unique** de la fenêtre de rétention. Le DPIA (RGP-02) et le registre Art. 30 (RGP-01) réutilisent la section §4 (fenêtre d'effacement effective).

---

## 1. Portée

Artefacts contenant potentiellement de la **PII client** produits par le pipeline d'audit :

- documents SharePoint **téléchargés** (au nom de l'utilisateur, OBO) ;
- sorties **OCR** temporaires (Document Intelligence) ;
- **brouillons FIC** générés (Word).

Deux emplacements de stockage :

- **FS local de la VM Functions** — `JOBS_BASE_DIR` (éphémère, par instance).
- **Azure Storage (blobs)** — tout artefact persisté sous le préfixe `jobs/` (le même compte héberge aussi l'état de contrôle Durable, **non concerné**).

## 2. Fenêtre de rétention

**30 jours.** Source de vérité alignée sur **deux** paramètres nommés :

| Paramètre | Emplacement | Défaut |
|-----------|-------------|--------|
| `jobRetentionDays` | `infra/main.bicep` (règle de cycle de vie Storage) | 30 |
| `JOB_RETENTION_DAYS` | variable d'app Functions (timer `prune_job_artifacts`) | 30 |

Les deux DOIVENT rester alignés (data-minimization RGPD). 30 jours couvre la fenêtre opérationnelle d'audit/relance tout en bornant la conservation de PII.

## 3. Points d'application (enforcement)

1. **Serveur — Azure Storage `managementPolicies`** (`infra/main.bicep`, ressource `storageLifecycle`, `name: 'default'`) : règle `rgp03-delete-job-artifacts` qui supprime les blobs `blockBlob` filtrés par `prefixMatch: jobBlobPrefixes` (`jobs/`) au-delà de `jobRetentionDays`, plus les actions `snapshot`/`version` à la même fenêtre. **`prefixMatch` garantit que les blobs de contrôle/lease Durable ne sont JAMAIS collectés** (sinon corruption d'orchestration).
2. **FS local — timer Functions `prune_job_artifacts`** (`azure_functions/function_app.py`, quotidien 02:00 UTC) appelant `scripts/jobs_ttl.prune_jobs_dir(JOBS_BASE_DIR, max_age_seconds=JOB_RETENTION_DAYS*86400)` : purge **âgée** (mtime < cutoff), best-effort, qui ne supprime **jamais** les audits en cours (entrées récentes conservées).

> ⚠️ `scripts/cleanup_local_artifacts.ps1` (wipe complet de `jobs/`) est un utilitaire **DEV** et **N'EST PAS** le mécanisme d'application RGP-03 (il détruirait des audits en cours). Ne pas l'utiliser comme contrôle de rétention.

## 4. Fenêtre d'effacement effective (divulgation honnête)

La suppression à 30 jours n'est **pas** un effacement définitif immédiat. Les durcissements INF-09 (sécurité opérationnelle / anti-ransomware) prolongent la **récupérabilité maximale effective** :

- **soft-delete blob** : `blobSoftDeleteDays` = 7 j (`infra/main.bicep`) ;
- **soft-delete conteneur** : `containerSoftDeleteDays` = 7 j ;
- **versioning + PITR** : `pointInTimeRestoreDays` = 6 j (versions conservées).

**Fenêtre d'effacement effective ≈ 30 + 7 ≈ 37 jours** (la suppression logique à 30 j, puis ~7 j de rétention soft-delete avant purge irréversible). C'est un **arbitrage assumé** sécurité-opérationnelle ↔ minimisation : la récupération protège contre une suppression accidentelle/malveillante. Les actions `snapshot`/`version` de la règle de cycle de vie bornent les copies retenues à la même fenêtre de 30 j.

Cette fenêtre de ~37 jours DOIT être déclarée telle quelle dans le DPIA (RGP-02) et le registre Art. 30 (RGP-01), et dans la procédure DSR (RGP-05, droit à l'effacement).

## 5. Vérification

- Offline : `az bicep build -f infra/main.bicep` (la règle compile) ; `pytest tests/azure_functions/test_jobs_ttl.py` (logique de purge âgée).
- Live (opérateur, post-déploiement) : confirmer la règle de cycle de vie active sur le compte de stockage prod et le timer Functions exécuté (App Insights `RGP-03 prune`).
