# AC360 — Suivi de consommation (P0-07 / P0-08)

> Suivi fin de la consommation par **commercial / équipe / client / cas d'usage**,
> sans limite bloquante par défaut et **sans donnée personnelle en clair**.

## Sources

- Événements d'usage : `scripts/usage_tracker.py` → `schemas/usage_event.schema.json`.
- Coûts estimés : `scripts/cost_tracker.py` → `schemas/cost_event.schema.json`.

## Dimensions d'agrégation

Tous les identifiants sont des **hash SHA-256** (anti-PII) :

| Dimension | Champ |
|---|---|
| Commercial | `commercial_id_hash` |
| Équipe | `team_id` |
| Client | `client_id_hash` |
| Cas d'usage | `use_case` / `event_type` / `topic_name` |
| Période | `timestamp_utc` |

## Indicateurs de consommation

| KPI | Calcul |
|---|---|
| Conversations | count `conversation_started` |
| Commerciaux actifs | distinct `commercial_id_hash` |
| Clients consultés | distinct `client_id_hash` |
| Documents analysés | somme `document_count` |
| Pages OCR | somme `page_count` |
| Coût estimé total | somme `estimated_cost_eur` (cost events) |
| Coût par commercial / équipe / client / cas d'usage | somme groupée par dimension |
| Coût moyen / conversation | coût total ÷ conversations |
| Coût moyen / document OCR | coût OCR ÷ documents |

## Politique

- **No block by default** : le suivi ne limite rien. Le blocage est une action
  admin explicite (`EMERGENCY_SHUTDOWN_RUNBOOK.md`).
- **Tokens estimés** : `estimated_tokens_*` (Copilot Studio n'expose pas le réel).
- **Réidentification** : un commercial/client n'est ré-identifiable que via une
  table de correspondance hash→identité, détenue par l'admin (hors dépôt).

## Destination

- Dev/staging : sink JSONL (`AC360_USAGE_SINK`) ou `safe_logger`.
- Prod : **À VALIDER EN ENVIRONNEMENT RÉEL** — brancher sur Application Insights /
  Log Analytics, puis dashboards (cf. `docs/observability/USAGE_TRACKING.md`).
