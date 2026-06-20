# AC360 — Posture de sécurité (Phase 1 : audit de code & corrections critiques)

> Livrable de sécurité de la Phase 1 (`AUD-01`). Document de hand-off vers la
> **Phase 5 (RGPD & Security Evidence Pack : SEC-01..SEC-05)**.
> Date : 2026-06-13. Re-validé sous la topologie de production réelle
> (mono-instance, mono-worker). Source : `.planning/codebase/CONCERNS.md`,
> `01-RESEARCH.md`, et les SUMMARY 01-02..01-06.

## But du document

Ce document enregistre l'état **réellement livré** des correctifs de la Phase 1
(et non des intentions). Il re-valide chaque mitigation « Addressed » / « Current
mitigation » de `CONCERNS.md` sous le **modèle de menace N>1 instance**, documente
la fermeture de l'IDOR (owner_hash sur `oid`), le correctif OBO 502→503, la
surface de rédaction, le contrat de champs du journal d'audit, et l'épinglage
mono-instance — en cadrant **honnêtement** l'« immutabilité » du journal (pas de
WORM Log Analytics). Il alimente la Phase 5 comme preuve de conformité.

## 1. Re-validation AUD-01 — suite complète verte sous mono-worker

`pytest tests/backend tests/security tests/azure_functions` → **188 passed, 1 skipped, exit 0**
(2026-06-13). Aucune régression introduite par les correctifs de la phase. Les
gardes existants (IDOR, rate-limit, path-traversal, isolation des jobs) tiennent
toujours sous les hypothèses mono-worker documentées dans le Plan 01-05.

### Table de disposition — chaque mitigation « Addressed » sous le modèle N>1

| Item CONCERNS.md | Catégorie | Disposition N>1 | Justification |
|---|---|---|---|
| **IDOR via owner_hash reuse** (UPN réutilisable) | Known Bug | **closed-by-fix** (01-02/01-06) | `owner_hash = SHA256(oid)` — `oid` est le GUID per-tenant immuable, non réutilisable. La garde durable `_assert_durable_owner` est le contrôle IDOR autoritaire. Voir §3. |
| **OBO 502 au lieu de 503** | Known Bug | **closed-by-fix** (01-03/01-06) | Retry borné transient-only ; exhaustion → **503** (et non 502). Voir §4. |
| **Secrets in Error Messages** (détail HTTPException, telemetry) | Security | **closed-by-fix** (01-02/01-06) | Tout `detail` dynamique + dimensions de télémétrie passent par la surface `safe_logger.redact()` / `redact_mapping()`. Voir §5. |
| **No Audit Trail for Document Access** | Missing Feature | **closed-by-fix (seam)** (01-04/01-06) | Seam d'émission `emit_document_access` avec contrat 4 champs ; exporter câblé en Phase 3 (OBS-01). Voir §6 et §7. |
| **JWKS Cache Thread Safety** (`_JWKS_CACHE`, `_JWKS_CACHE_TS`) | Tech Debt | **closed-by-single-instance-pin** (01-05) | Un seul process = un seul cache JWKS ; pas de divergence pendant la rotation de clés. Pas de réécriture async-lock (décision verrouillée). Voir §2. |
| **Rate Limit Store Not Thread-Safe** (`_rate_limit_store`) | Tech Debt | **closed-by-single-instance-pin** (01-05) | Un seul worker = un seul magasin de rate-limit ; pas de contournement par répartition des requêtes entre workers. Voir §2. |
| **Rate Limit Cleanup Timing Window** | Known Bug | **closed-by-single-instance-pin** (01-05) | Fenêtre de course acceptée à l'échelle d'une petite équipe sous un seul process ; l'atomicité inter-worker n'est plus en jeu (mono-worker). |
| **Path Traversal via Document ID (symlinks)** | Known Bug | **deferred-non-launch-blocking** | Gardes existantes (UUID + `commonpath` + `_safe_filename`) re-validées vertes sous AUD-01 ; durcissement symlink reporté (non launch-blocking). Non modifié. |
| **Broad Exception Handling** | Tech Debt | **deferred (hot paths only)** | Resserré uniquement dans les hot paths auth/OBO/download touchés ; le balayage complet hors hot paths reste de la dette différée. |
| **JWKS Cache Missing Stale-While-Revalidate** | Security | **deferred-non-launch-blocking** | Mitigation actuelle (TTL + refresh forcé sur kid inconnu) re-validée ; SWR différé. |
| **Managed Identity Assumption Without Fallback** | Security | **deferred** (infra Phase 2) | Fail-fast clair conservé ; provisioning MI = dépendance infra Phase 2. |
| **Graph API Token Passed in Headers** | Security | **closed-by-fix (redaction)** | `safe_logger.redact()` masque les Bearer tokens ; en-têtes jamais loggés en clair. |
| **Fabric OneLake Cache Poisoning / fallback** | Security/Fragile | **deferred-non-launch-blocking** | Mode « audit sans référence », circuit breaker, indexation fuzzy = dette différée explicite. Non modifié. |
| **Fuzzy Name Matching O(n)** | Perf | **deferred-non-launch-blocking** | Indexation BK-tree/trigram différée ; non launch-blocking. Non modifié. |

> Aucun item différé (hors périmètre) n'a été modifié pendant cette phase.

## 2. L'épinglage mono-instance comme contrôle porteur de l'état en mémoire

Trois structures en mémoire du gateway ne sont correctes qu'avec **exactement un
process** :

- `_rate_limit_store` (`scripts/api_server.py`) — contournement du rate-limit
  si les requêtes se répartissent entre workers.
- `_JWKS_CACHE` (`scripts/auth.py`) — divergence du cache pendant la rotation
  de clés.
- `_audit_job_owners` (`scripts/api_server.py`) — divergence du fast-path IDOR
  (la garde durable `owner_hash` reste autoritaire — §3).

> Réfs par **nom de symbole** (pas de numéro de ligne) pour éviter toute dérive
> documentaire ; `grep` le symbole pour localiser.

**Mitigation (AUD-04, Plan 01-05)** : épinglage mono-worker porteur dans
`infra/main.bicep` —
`gunicorn --workers 1 -k uvicorn.workers.UvicornWorker api_server:app`
(`appCommandLine`), commentaire « load-bearing » nommant les trois structures, et
**interdiction** de toute règle d'autoscale élevant la capacité au-dessus de 1.

> **Report assumé** : le tier F1/Free garantit une instance fixe et **rejette** un
> `sku.capacity` explicite. L'épinglage explicite `sku.capacity = 1` est **reporté
> à la Phase 2 (INF-02 / B1)**. Le contrôle porteur ici est le `--workers 1` + le
> commentaire de documentation ; aucune réécriture async-lock n'est faite cette
> phase (décision verrouillée — mono-instance EST la mitigation).

## 3. Analyse IDOR — owner_hash sur `oid` (et non UPN)

- **Bug fermé** : l'identité utilisée pour la propriété/les clés de stockage passe
  de l'UPN (mutable, réutilisable après suppression/re-provisioning) à l'**`oid`**
  (Object ID Entra) — un GUID per-tenant **immuable et non réutilisable**.
- `verify_azure_ad_token` retourne désormais `claims['oid']` ; un token sans `oid`
  est rejeté en **401** (Plan 01-02). `owner_hash = hash_id(oid)` = SHA-256 sans
  sel (lookup déterministe ; `oid` est déjà un GUID opaque).
- **Garde autoritaire** : `_assert_durable_owner` hard-fail en **403** sur
  mismatch du `owner_hash` persisté dans l'input Durable — c'est le contrôle IDOR
  **autoritaire**. La map en mémoire `_audit_job_owners` n'est qu'un **cache
  fast-path** (sa divergence sous N>1 est neutralisée par l'épinglage §2, et
  resterait non-autoritaire de toute façon).
- **Cutover propre** : l'app n'a jamais été déployée — aucun hash existant à
  migrer ni dual-read. L'absence de `owner_hash` reste fail-open (Open Q3) pour ne
  pas casser les formes de statut en vol/en file ; le mismatch (la vraie menace)
  hard-fail.

## 4. Posture OBO — backoff borné, 503 (et non 502)

- **Retry transient-only** (`acquire_obo_graph_token_retrying`, Plan 01-03) :
  retry uniquement sur `{429, 503, 504}` + `httpx.TimeoutException` /
  `httpx.ConnectError` ; **les 4xx auth et `ValueError` config NE sont PAS
  retryés** (un vrai défaut de config remonte immédiatement, non masqué en 503).
- **Backoff** : 3 tentatives, base ~0.5s, full jitter (`random.uniform(0, base*2**i)`),
  `Retry-After` honoré sur 429. Jitter = anti-thundering-herd.
- **Exhaustion → HTTP 503** (et non 502) sur le chemin d'audit (Plan 01-06).
- **Suivi reporté** : les sites OBO secondaires `resolve_document` et
  `api_create_planner_task` restent sur le wrapper non-retrying + 502 — cohérence
  AUD-05 à compléter, **journalisée dans `deferred-items.md`** (hors périmètre du
  chemin d'audit de 01-06).

## 5. Surface de rédaction (PII / secrets)

- **Surface unique auditée** : `safe_logger.redact()` + le helper
  `redact_mapping()` (Plan 01-02) — **zéro nouvelle regex par site d'appel**.
- **Réponses client** : chaque `detail` dynamique d'`HTTPException` passe par
  `_redacted_detail(...)` (message générique + rédaction) avant de revenir au
  client (Plan 01-06).
- **Télémétrie** : les dimensions custom d'`AppInsightsMiddleware` passent par
  `redact_mapping` **avant émission**, pas seulement dans les logs fichier.
- L'événement d'audit lui-même ne porte que les 4 champs contractés (§6) — aucun
  texte libre.

## 6. Contrat de champs du journal d'audit (AUD-07)

L'événement d'accès document porte **exactement** quatre champs, **sans PII brute**
(pas d'UPN, pas de nom client) :

```
{ user_id_hash, document_id, ts_utc, verdict }
```

- `user_id_hash = hash_id(oid)` (SHA-256, sans sel) — l'`oid` brut **ne traverse
  jamais** la frontière de télémétrie.
- `ts_utc` = ISO-8601 UTC ; `verdict` omis → chaîne vide (jamais manquant).
- **Seam env-gated** (`scripts/audit_trail.emit_document_access`, Plan 01-04) :
  inerte tant que le gate AppInsights (`APPINSIGHTS_INSTRUMENTATIONKEY` /
  `APPLICATIONINSIGHTS_CONNECTION_STRING`) est absent ; toutes les valeurs passent
  par `redact_mapping` avant émission.
- **Émis** sur le chemin api_server porteur de l'`oid` (Plan 01-06) ; l'input
  Durable ne porte que le `owner_hash` à sens unique, jamais l'`oid`.
- **Exporter câblé en Phase 3 (OBS-01)** : `configure_azure_monitor` derrière le
  même gate, sans toucher le site d'appel.

## 7. Le contrôle « journal immuable » — cadrage HONNÊTE

> **Il n'existe AUCUN verrou WORM / immuabilité au niveau table sur Log
> Analytics.** Toute prétention au WORM serait fausse (confusion avec les
> politiques de blob immuable Storage).

L'« immutabilité » du journal d'audit repose en réalité sur la combinaison :

1. **Ingestion append-only** — pas d'API d'édition en place des événements.
2. **Rétention longue** — table Log Analytics `retentionInDays` /
   `totalRetentionInDays` (jusqu'à ~12 ans).
3. **RBAC** — accès restreint à la workspace.
4. **Resource lock** sur la workspace (verrou de ressource Azure).

La configuration de la rétention/du lock workspace est une **dépendance infra
Phase 2/3** ; cette phase ne câble que le chemin d'émission et le contrat de
champs (§6). Si un vrai WORM est exigé plus tard, c'est un redesign
Logs-Ingestion → Storage immuable (hors périmètre).

> **Assumption A2 à porter en Phase 5** : que `resource-lock + RBAC + rétention
> longue` constitue une barre de preuve d'« immutabilité » acceptable pour la revue
> de conformité interne reste **à confirmer avec le DPO en Phase 5**. Si le DPO
> exige un vrai WORM, l'écart est documenté ici comme dépendance de redesign.

## 8. Items ouverts portés en avant

| Item ouvert | État | Porté vers |
|---|---|---|
| **Liste exacte des scopes Graph délégués OBO** | DEFERRED — l'app registration staging n'était pas disponible ; la logique de retry (indépendante du scope) a été implémentée ; les assertions de chemin-succès (scopes consentis, résolution de `.default`, écart de consentement AADSTS65001) restent à vérifier en environnement réel. | **Phase 2 INF-06** (vérification contre l'app registration staging live). |
| **Cohérence AUD-05 sur sites OBO secondaires** | DEFERRED — `resolve_document` / `api_create_planner_task` toujours sur wrapper non-retrying + 502. | `deferred-items.md` (suivi AUD-05). |
| **Durcissement symlink path-traversal, fallback Fabric, index fuzzy, balayage broad-except** | DEFERRED non launch-blocking | Registre known-issues Phase 5 (SEC-05). |
| **`sku.capacity = 1` explicite** | DEFERRED — F1 rejette une capacity explicite ; mono-worker assuré par tier + `--workers 1`. | **Phase 2 INF-02 / B1**. |

## Conclusion

Sous la topologie de production réelle (mono-instance, mono-worker), tous les bugs
launch-blocking de `CONCERNS.md` sont fermés (IDOR `oid`, OBO 503, rédaction
erreur/télémétrie, seam d'audit) ou couverts par l'épinglage mono-instance porteur
(rate-limit, JWKS, fast-path IDOR), la dette restante étant classée et différée
sans être modifiée. Le contrôle « journal immuable » est cadré honnêtement
(append-only + rétention + RBAC + resource lock ; **pas de WORM**). Ce document
constitue l'entrée de la **Phase 5 (RGPD & Security Evidence Pack)** et porte les
items ouverts vers la Phase 2 (INF-06, INF-02/B1) et le registre known-issues
(SEC-05).
