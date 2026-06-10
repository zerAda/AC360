# Politique de journalisation — AC360

> **Version** : 1.0
> **Date** : 2026-06-10
> **Propriétaire** : Admin Power Platform + RSSI
> **Révision** : Trimestrielle
> **Périmètre** : Passerelle FastAPI, Azure Durable Functions, OCR Document Intelligence (F0), traçage usage/coût, kill-switch.

---

## 1. Principes

1. **Aucune PII en clair.** Les identifiants utilisateur / commercial / client sont des **hash SHA-256** — jamais la valeur brute. Voir `hash_id` (`scripts/feature_flags.py`).
2. **Aucun secret en clair.** Toute chaîne susceptible de contenir un secret passe par `redact()` (`scripts/safe_logger.py`) avant journalisation.
3. **Minimisation.** On ne journalise que ce qui est nécessaire à l'exploitation, à la sécurité et au FinOps.
4. **Anti log-injection.** Les caractères de contrôle (dont CR/LF) sont neutralisés avant écriture, pour empêcher la forge de fausses lignes de journal.
5. **Best-effort non bloquant.** La journalisation et le traçage ne doivent **jamais** interrompre le métier (exceptions avalées côté `usage_tracker` / sink).

> Référence de conformité : Baseline Sécurité (`docs/security/SECURITY_BASELINE.md` §6.1 et §7) — aucune donnée client ni secret persisté en clair (SQLite `audit_logs.details`, console, Application Insights).

---

## 2. Niveaux de log

| Niveau | Usage | Exemple AC360 |
|---|---|---|
| `DEBUG` | Diagnostic développeur, désactivé en prod | Détail d'un appel interne |
| `INFO` | Événements nominaux | `usage_event` émis, conversation démarrée, OCR terminé |
| `WARNING` | Situation anormale non bloquante | `budget_warning_triggered` (≥ 80 %), retry OCR |
| `ERROR` | Échec d'opération | `ocr_failed`, erreur d'appel backend, 5xx |

> `safe_logger.log_security(level, message, data)` route vers `logger.info/warning/error/debug` selon le niveau ; tout niveau inconnu retombe en `DEBUG`. Le logger nommé est `"AC360"` (niveau `INFO` par défaut).

---

## 3. Champs structurés à journaliser

Pour permettre la corrélation sans exposer de PII, chaque entrée significative doit porter, lorsque disponible :

| Champ | Source | Nature | PII ? |
|---|---|---|---|
| `correlation_id` / `event_id` | `uuid4` (cost/usage trackers) | Corrélation technique d'une opération | Non |
| `conversation_id` | `usage_event.conversation_id` | Fil de conversation Copilot | Non (identifiant technique) |
| `session_id` | `usage_event.session_id` | Session | Non |
| `user_id_hash` | `hash_id(user_id)` | **Hash SHA-256** | Non (pseudonyme) |
| `commercial_id_hash` | `hash_id(commercial_id)` | **Hash SHA-256** | Non (pseudonyme) |
| `client_id_hash` | `hash_id(client_id)` | **Hash SHA-256** | Non (pseudonyme) |
| `team_id` | `usage_event.team_id` | Libellé d'organisation | Non |
| `event_type` | `usage_event.event_type` | Type d'événement métier | Non |
| `error_code` | `usage_event.error_code` | Code d'erreur applicatif | Non |
| `safe_error_message` | passé par `redact()` | Message d'erreur neutralisé | Non (neutralisé) |
| `latency_ms` | mesure d'exécution | Latence de l'opération | Non |
| `status` | `usage_event.status` (`ok`/`error`/`blocked`/`skipped`) | Issue de l'opération | Non |
| `environment` | env `AC360_ENVIRONMENT` | `dev`/`test`/`uat`/`prod`/`staging` | Non |
| `bot_version` | env `AC360_BOT_VERSION` | Version du bot | Non |

> Les champs `*_id_hash` respectent le motif `^[a-f0-9]{64}$` (cf. schémas). **Ne jamais** journaliser un identifiant qui ne respecte pas ce motif à la place d'un hash.

---

## 4. Interdictions strictes

**NE JAMAIS journaliser en clair :**

- Adresses e-mail, IBAN, NIR, numéros de carte / de compte, longues séquences de chiffres → masqués par `redact()` (`[EMAIL_MASQUÉ]`, `[PII_MASQUÉE]`).
- Secrets : JWT, jetons `Bearer`, URL de webhook Teams, couples `password`/`secret`/`client_secret`/`api_key`/`token`/`connection_string`/`azure_ocr_key`… → masqués `[SECRET_MASQUÉ]` (motifs alignés sur `.gitleaks.toml`).
- Identifiants utilisateur / commercial / client **bruts** → toujours hashés avant log.
- Extraits de documents clients (OCR, RAG, pièces jointes) → uniquement métadonnées (`document_count`, `page_count`), jamais le contenu.

> `redact()` est **robuste aux entrées `None` / non-`str`**, retire les séquences ANSI, neutralise les caractères de contrôle et **tronque à `MAX_LEN = 800`** caractères (mention « tronqué, N caractères au total »).

---

## 5. Destinations

| Destination | Contenu | Rétention | Remarque |
|---|---|---|---|
| **Application Insights** | Traces applicatives, requêtes, exceptions, métriques | À définir (voir §6) | Sink cible des `usage_event` en prod (cf. `usage_tracker`) |
| **Log Analytics** | Journaux centralisés / requêtes KQL | À définir | Requêtage des alertes (cf. `ALERTING_RULES.md`) |
| **SQLite `audit_logs.details`** | Journal d'audit local du pipeline | Selon politique d'audit | Passe **obligatoirement** par `redact()` |
| **Console / stdout** | Exécution locale, Functions | Éphémère | Neutralisé par `redact()` |
| **Fichier JSONL** (`AC360_USAGE_SINK`) | `usage_event` bruts (sink configurable) | Selon montage | À brancher sur App Insights / Log Analytics en prod |

> Comportement du sink usage (`usage_tracker._default_sink`) : si `AC360_USAGE_SINK` est défini → écriture JSONL ; sinon → `safe_logger.log_security("INFO", "usage_event", …)`. En dernier recours, **aucune exception n'est levée**.

---

## 6. Rétention

| Catégorie | Rétention cible | Statut |
|---|---|---|
| Logs d'usage (FinOps / produit) | À VALIDER EN ENVIRONNEMENT RÉEL | Dépend du coût d'ingestion (`application_insights`, cf. CHARGEBACK_MODEL §3) |
| Logs de sécurité (auth, kill-switch, DLP) | À VALIDER EN ENVIRONNEMENT RÉEL (rétention plus longue recommandée) | À aligner avec exigences RSSI |
| Journal d'audit SQLite | Selon politique d'audit projet | Défini hors de ce document |

> La rétention pilote directement le coût Application Insights / Log Analytics : tout choix doit être arbitré avec le FinOps. Les durées chiffrées restent **À VALIDER EN ENVIRONNEMENT RÉEL** tant qu'elles ne sont pas décidées.

---

## 7. Séparation logs sécurité vs logs d'usage

| Flux | Nature | Exemples d'événements | Accès |
|---|---|---|---|
| **Sécurité** | Auth, blocage, arrêt d'urgence, DLP | `user_blocked`, `user_unblocked`, `bot_emergency_stopped`, échecs 401/403 | RSSI / Admin |
| **Usage / FinOps** | Volumétrie et coût | `conversation_started`, `message_sent`, `rag_search_executed`, `ocr_*`, `cost_estimated`, `budget_warning_triggered` | FinOps / Produit |

Les deux flux **n'ont pas le même public ni la même rétention** : un événement de sécurité doit rester consultable plus longtemps et avec un accès restreint, même si la volumétrie d'usage est purgée plus tôt.

---

## 8. Conformité RGPD

- **Pseudonymisation systématique** : tout identifiant personnel est hashé (SHA-256, normalisé `strip().lower()`) avant d'entrer dans un log ou une métrique → aucune donnée directement identifiante.
- **Minimisation** : seules les métadonnées strictement nécessaires sont journalisées (compteurs, statuts, hash, codes d'erreur), jamais le contenu métier.
- **Pas de réidentification directe** : la table de correspondance hash → personne, si elle existe, est gérée **hors repo** par l'admin sous contrôle d'accès (cf. CHARGEBACK_MODEL §9).
- **Neutralisation des secrets** : `safe_logger` empêche la fuite de secrets, conformément aux motifs `.gitleaks.toml`.
- **Droit d'accès / d'effacement** : opérables via la table de correspondance et la rétention bornée ; le hash seul, sans table, n'est pas réidentifiable.

---

## 9. Vérification

- Tester `redact()` sur des chaînes contenant e-mail, IBAN, JWT, `Bearer`, webhook Teams, `api_key=…`, CR/LF → vérifier le masquage et l'absence de saut de ligne.
- Vérifier qu'aucun `usage_event` / `cost_event` ne contient d'identifiant brut (motif `^[a-f0-9]{64}$` attendu sur les champs `*_hash`).
- Vérifier que `AC360_ENVIRONMENT = prod` désactive `DEBUG`.

---

## 10. Références

- `scripts/safe_logger.py` — `redact()`, `log_security()`, `MAX_LEN`
- `scripts/feature_flags.py` — `hash_id()` (SHA-256)
- `scripts/usage_tracker.py` — sink, `AC360_USAGE_SINK`, best-effort
- `schemas/usage_event.schema.json`, `schemas/cost_event.schema.json` — champs et motifs hash
- `docs/security/SECURITY_BASELINE.md` (§6.1, §7) — exigences de non-persistance en clair
- `docs/observability/ALERTING_RULES.md`, `docs/observability/MONITORING_PLAN.md`
