# AC360 — Traçage d'usage (P0-08)

> Spécification technique des événements d'usage. Implémentation :
> `scripts/usage_tracker.py` ; schéma : `schemas/usage_event.schema.json`.

## Types d'événements (`event_type`)

`conversation_started`, `message_sent`, `message_received`,
`rag_search_executed`, `sharepoint_document_accessed`,
`ocr_started`, `ocr_completed`, `ocr_failed`, `backend_action_called`,
`email_draft_generated`, `audit_documentaire_started`,
`audit_documentaire_completed`, `cost_estimated`, `budget_warning_triggered`,
`user_blocked`, `user_unblocked`, `bot_emergency_stopped`.

## Champs (extrait)

| Champ | Note |
|---|---|
| `event_id`, `timestamp_utc` | identité + horodatage UTC |
| `environment`, `bot_version` | contexte de déploiement |
| `user_id_hash`, `commercial_id_hash`, `client_id_hash` | **SHA-256**, jamais en clair |
| `team_id`, `conversation_id`, `session_id` | corrélation |
| `action_name`, `topic_name` | quoi |
| `document_count`, `page_count` | volume |
| `estimated_tokens_input`, `estimated_tokens_output` | **ESTIMÉS** (pas le réel) |
| `estimated_cost_eur`, `cost_source` | coût qualifié |
| `status`, `error_code`, `safe_error_message` | issue (sans secret) |

## Confidentialité (RGPD)

- Identifiants personnels → **hash SHA-256** (`feature_flags.hash_id`).
- Aucun secret en clair (`safe_logger`).
- Champs tokens explicitement nommés `estimated_*` : interdiction d'affirmer
  « tokens réels » sans preuve (Copilot Studio ne les expose pas).

## Émission

```python
from usage_tracker import track
track("ocr_completed", user_id="c@gerep.fr", client_id="ACME",
      page_count=3, document_count=1)   # identifiants hashés automatiquement
```

- **Best-effort** : une erreur d'émission n'interrompt jamais le métier
  (prouvé : `tests/usage/test_usage_tracker.py::test_emit_is_best_effort_never_raises`).
- Sink : fichier JSONL via `AC360_USAGE_SINK`, sinon `safe_logger`.

## Intégration prouvée

La passerelle (`scripts/api_server.py`) émet `audit_documentaire_started`
(`ok`/`blocked`) à chaque déclenchement d'audit — cf.
`tests/backend/test_killswitch_gate.py`.

## Production

Brancher le sink sur **Application Insights / Log Analytics** puis construire les
dashboards adoption/coûts. Statut : **À VALIDER EN ENVIRONNEMENT RÉEL**.
