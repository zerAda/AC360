# Règles d'alerte — AC360

> **Version** : 1.0
> **Date** : 2026-06-10
> **Propriétaire** : Admin Power Platform + RSSI + FinOps
> **Révision** : Mensuelle
> **Note transversale** : tout seuil chiffré non encore observé sur l'environnement réel est marqué **À VALIDER EN ENVIRONNEMENT RÉEL**. Les valeurs proposées sont des points de départ à calibrer, **pas** des engagements.

---

## 0. Principes

1. **Détecter, pas bloquer.** Les alertes notifient. Le **blocage** (kill-switch, `user_blocked`, `bot_emergency_stopped`) reste une **décision administrateur** — voir `check_budget()` qui ne bloque jamais (`scripts/cost_tracker.py`).
2. **Sévérités** : `INFO` (suivi), `WARNING` (à surveiller), `CRITIQUE` (action immédiate).
3. **Source des signaux** : `usage_event` / `cost_event` (Application Insights / Log Analytics), métriques de la passerelle FastAPI, état du kill-switch.
4. **Anonymat préservé** : les alertes par commercial s'appuient sur `commercial_id_hash` — jamais d'identité en clair (cf. `LOGGING_POLICY.md`).

---

## 1. Tableau des règles d'alerte

| Nom | Condition | Seuil | Sévérité | Canal | Action |
|---|---|---|---|---|---|
| **Budget — avertissement** | `check_budget().level == "warning"` (consommation cumulée vs `AC360_BUDGET_EUR`) | `ratio ≥ AC360_BUDGET_WARN_PCT` (**défaut 80 %**) | WARNING | Teams FinOps + e-mail Admin | Revue de consommation ; émission `budget_warning_triggered` |
| **Budget — dépassement** | `check_budget().level == "exceeded"` | `ratio ≥ 100 %` | CRITIQUE | Teams FinOps + e-mail Admin/RSSI | Décision **humaine** : plafonnement / kill-switch admin (pas d'auto-block) |
| **Budget — non configuré** | `check_budget().level == "unknown"` (`AC360_BUDGET_EUR` absent/≤0) | — | INFO | Teams FinOps | Configurer `AC360_BUDGET_EUR` |
| **Taux d'échec OCR** | Part d'événements `ocr_failed` parmi `ocr_started` sur fenêtre glissante | `> 5 %` sur 1 h — **À VALIDER EN ENVIRONNEMENT RÉEL** | WARNING | Teams Support | Vérifier quota OCR F0, format des documents |
| **OCR — panne franche** | Aucun `ocr_completed` alors que des `ocr_started` arrivent | 0 succès / N tentatives — **À VALIDER** | CRITIQUE | Teams Support + Admin | Vérifier service Document Intelligence / clé OCR |
| **Latence p95 backend** | p95 du temps de réponse de la passerelle FastAPI | `> 10 s` — **À VALIDER EN ENVIRONNEMENT RÉEL** (baseline à établir) | WARNING | Teams Digital | Profiler ; vérifier Functions / dépendances |
| **Latence — durée audit** | Durée d'un cas `audit_documentaire` (entre `audit_documentaire_started` et `…_completed`) | `> 120 s` — **À VALIDER** | WARNING | Teams Support | Vérifier taille des pièces, OCR, backend |
| **RAG — réponses sans source** | Part de `rag_search_executed` sans document/source rattaché (proxy : absence de `sharepoint_document_accessed` corrélé) | `> 15 %` — **À VALIDER EN ENVIRONNEMENT RÉEL** | WARNING | Teams Digital | Revoir indexation OneLake (lecture seule) / SharePoint, topics RAG |
| **Pic de consommation par commercial** | Volume (messages/actions/coût estimé) d'un `commercial_id_hash` très au-dessus de sa baseline | `> 3× médiane glissante` — **À VALIDER** | WARNING | Teams FinOps | Vérifier usage anormal ; pas de blocage auto |
| **Pic de consommation global** | Hausse brutale du volume agrégé (tous postes) | Écart vs baseline — **À VALIDER EN ENVIRONNEMENT RÉEL** | WARNING | Teams FinOps | Corréler à un incident / un déploiement |
| **Échecs d'authentification (401/403)** | Taux anormal de réponses `401` / `403` sur la passerelle | `> 3` consécutifs ou pic vs baseline — **À VALIDER** | CRITIQUE | Teams Sécurité (RSSI) | Investiguer tentative d'accès / mauvaise config token |
| **Kill-switch activé** | Émission `bot_emergency_stopped` (ou `user_blocked`) | Toute occurrence | CRITIQUE | Teams Sécurité + Admin | Confirmer l'action volontaire ; tracer la décision |

> Les seuils marqués **À VALIDER EN ENVIRONNEMENT RÉEL** doivent être recalibrés après collecte d'une baseline. Les valeurs latence p95 (`10 s`), durée audit (`120 s`) et taux d'erreur (`5 %`) sont cohérentes avec `docs/observability/MONITORING_PLAN.md` mais restent à confirmer sur la prod.

---

## 2. Détail des familles d'alerte

### 2.1 Budget (FinOps)

- Pilotées par `check_budget(spent_eur, budget_eur, warn_pct)` (`scripts/cost_tracker.py`).
- Variables : `AC360_BUDGET_EUR` (budget), `AC360_BUDGET_WARN_PCT` (seuil d'avertissement, **défaut 80**).
- Niveaux exacts : `unknown` (pas de budget), `ok`, `warning` (`≥ warn_pct`), `exceeded` (`≥ 100 %`).
- **Aucun blocage automatique** : `warning`/`exceeded` notifient ; toute restriction est une décision admin (kill-switch).
- Rappel : tant que la grille `AC360_RATE_CARD` est vide, les coûts sont `A_VALIDER` → l'alerte budget peut rester à `unknown` ou à `0 €`. Voir `docs/finops/CHARGEBACK_MODEL.md`.

### 2.2 OCR (Document Intelligence F0)

- Signaux : `ocr_started`, `ocr_completed`, `ocr_failed` (`usage_tracker`).
- Le palier **F0** impose des limites de débit propres → un taux d'échec peut signaler un quota atteint plutôt qu'un bug. Le seuil exact est **À VALIDER EN ENVIRONNEMENT RÉEL**.

### 2.3 Latence

- p95 de la passerelle FastAPI + durée des cas d'audit (`audit_documentaire_started`/`…_completed`).
- Établir une **baseline** avant de figer les seuils (`> 10 s` p95, `> 120 s` audit sont des points de départ).

### 2.4 Qualité RAG (réponses sans source)

- Une réponse RAG sans source affaiblit la confiance. Mesure : `rag_search_executed` non corrélés à un accès document (`sharepoint_document_accessed`) ou à une source citée.
- Sources de connaissance : Microsoft Fabric OneLake (**lecture seule**) + SharePoint. Un taux élevé peut révéler un défaut d'indexation, pas seulement de génération.

### 2.5 Anomalies de consommation par commercial

- Basées sur `commercial_id_hash` (anonyme). Détection par écart à une baseline glissante.
- Objectif : repérer un usage atypique (boucle, mésusage) **sans** réidentifier directement le commercial ni le bloquer automatiquement.

### 2.6 Sécurité (auth + kill-switch)

- **401/403** : pics → tentative d'accès non autorisé ou token mal configuré → alerte RSSI.
- **Kill-switch** : `bot_emergency_stopped` / `user_blocked` → toute occurrence est `CRITIQUE` et doit être tracée comme décision volontaire.

---

## 3. Canaux et destinataires

| Canal | Destinataires | Familles |
|---|---|---|
| Teams FinOps + e-mail Admin | FinOps, Admin Power Platform | Budget, pics de consommation |
| Teams Support | Support / Digital | OCR, durée d'audit |
| Teams Digital | Équipe Digital | Latence p95, qualité RAG |
| Teams Sécurité (RSSI) | RSSI, Admin | 401/403, kill-switch |

> Le détail d'une alerte doit rester **sans PII** : uniquement hash, compteurs, codes d'erreur, statut (cf. `LOGGING_POLICY.md`).

---

## 4. Cycle de vie d'une alerte

1. **Calibration** : collecter une baseline (≥ quelques semaines de prod) avant de figer les seuils `À VALIDER`.
2. **Activation** : créer la règle dans Application Insights / Log Analytics (requête KQL sur `usage_event` / métriques FastAPI).
3. **Revue** : ajuster mensuellement seuils et faux positifs.
4. **Documentation** : tout changement de seuil est consigné ici (version + date).

---

## 5. Références

- `scripts/cost_tracker.py` — `check_budget()`, `AC360_BUDGET_EUR`, `AC360_BUDGET_WARN_PCT`
- `scripts/usage_tracker.py` — événements `ocr_*`, `rag_search_executed`, `budget_warning_triggered`, `user_blocked`, `bot_emergency_stopped`
- `schemas/usage_event.schema.json` — types d'événements et `status`
- `docs/observability/MONITORING_PLAN.md` — métriques et seuils indicatifs
- `docs/observability/LOGGING_POLICY.md` — anonymisation et neutralisation des logs
- `docs/finops/CHARGEBACK_MODEL.md` — postes de coût et statut `A_VALIDER`
