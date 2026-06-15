# SEC-02 — Authentification & autorisation (tracées aux tests)

> Livrable **SEC-02** du Security Evidence Pack (Phase 5).
> Description de chaque contrôle authN/authZ d'AC360 (Entra SSO, JWT RS256/JWKS,
> identité `oid`, garde IDOR, OBO délégué, lecture seule), **chaque contrôle tracé à
> au moins un test existant cité par chemin**.
> Sources autoritaires : `docs/security/SECURITY_POSTURE.md` §3 (IDOR `owner_hash` sur
> `oid`) et §4 (posture OBO) ; `scripts/auth.py`, `scripts/graph_obo.py`.
> Mapping ASVS L1 : V2 (Authentication), V3 (Session), V4 (Access Control).
> Date : 2026-06-15.

## But du document

Permettre à un reviewer (auditeur sécurité / DPO) de **tracer chaque contrôle authN/authZ
à une preuve concrète** : un test existant et vert du dépôt, cité par chemin. SEC-02 est
l'une des cinq composantes du pack de preuves (SEC-01..SEC-05) et le pendant « contrôles »
du diagramme **SEC-01** (frontières de confiance). Aucun nouveau contrôle n'est implémenté
ici : les contrôles existent depuis les Phases 1–4 ; SEC-02 les **documente et les trace**.

Tests cités vérifiés présents et verts dans la suite (`pytest tests/backend` —
cf. `SECURITY_POSTURE.md` §1 : 188 passed).

---

## 1. Tableau de traçabilité : Contrôle -> Description -> Test (chemin)

| # | Contrôle (authN/authZ) | Description | ASVS | Test(s) proof (chemin) |
|---|------------------------|-------------|------|------------------------|
| 1 | **Entra ID SSO + JWT RS256 via JWKS** | `verify_azure_ad_token` (`scripts/auth.py`) valide la signature **RS256** contre les clés **JWKS** Entra (cache TTL + refresh forcé sur `kid` inconnu), et vérifie `audience`, `issuer`, `exp`, `nbf`. `alg` non-RS256 rejeté (anti alg-confusion), `kid` manquant rejeté. | V2 | `tests/backend/test_auth_jwt.py`, `tests/backend/test_auth_jwt_real.py`, `tests/backend/test_jwks_cache_ttl.py` |
| 2 | **Identité = `oid` (Object ID Entra)** | L'identité retournée est le claim `oid` (GUID per-tenant **immuable et non réutilisable**), jamais l'UPN (mutable). Un token **sans `oid` est rejeté en 401**. L'UPN n'est lu que pour une ligne de log lisible, jamais utilisé comme clé d'appartenance. | V2 / V3 | `tests/backend/test_wave1_auth_identity.py`, `tests/backend/test_auth_jwt.py` |
| 3 | **Garde IDOR autoritaire (`owner_hash` sur `oid`)** | Le contrôle IDOR **autoritaire** est `_assert_durable_owner` : `owner_hash = hash_id(oid)` (SHA-256) est persisté dans l'input Durable et vérifié à chaque lecture de statut ; **mismatch -> 403**. La map en mémoire `_audit_job_owners` n'est qu'un **cache fast-path** non autoritaire (cf. `SECURITY_POSTURE.md` §3). Deux `oid` distincts produisent deux `owner_hash` distincts ; lecture croisée bloquée. | V4 | `tests/backend/test_audit_ownership.py`, `tests/backend/test_job_isolation.py` |
| 4 | **OBO user-delegated (RBAC SharePoint, jamais persisté)** | `scripts/graph_obo.py` échange l'assertion utilisateur contre un token **Graph délégué** (`requested_token_use=on_behalf_of`). Le download SharePoint en aval honore les **permissions propres de l'utilisateur** (pas d'accès -> Graph 403 -> l'audit ne démarre pas). Le `X-MS-Graph-Token` n'est **jamais persisté** ; retry transient-only borné, épuisement -> **503** (et non 502). cf. `SECURITY_POSTURE.md` §4. | V3 / V4 | `tests/backend/test_graph_obo.py`, `tests/backend/test_wave1_auth_identity.py`, `tests/backend/test_job_isolation.py` |
| 5 | **Lecture seule (read-only / lecture seule)** | AC360 est délégué-utilisateur uniquement et **read-only** : aucune écriture/action sur les données SharePoint ; le FIC est un **brouillon pour revue humaine**. Les jetons app-only (client_credentials) sont hors périmètre et n'atteignent pas `/api/audit`. L'output d'audit est validé par JSON-schema (pas d'effet de bord). | V4 | `tests/backend/test_audit_ownership.py`, `tests/backend/test_job_isolation.py` |
| 6 | **Surface de validation associée (en-têtes de sécurité, rédaction)** | En-têtes de sécurité présents ; détail `HTTPException` et dimensions de télémétrie rédigés (`safe_logger.redact`) avant retour client / émission (cf. `SECURITY_POSTURE.md` §5). | V7 | `tests/backend/test_security_headers.py`, `tests/backend/test_safe_logger_redaction.py` |

> **Chaque ligne de contrôle cite au moins un chemin `tests/...`.** Tous ces tests font
> partie de la suite existante (verte) — aucun test n'a été ajouté pour ce document.

---

## 2. Détail par contrôle

### 2.1 Entra SSO + JWT RS256/JWKS (V2)

`scripts/auth.py` :

- **JWKS** : `_fetch_jwks` télécharge les clés signantes Entra avec un cache TTL
  (`JWKS_TTL_SECONDS`, défaut 3600 s) et **refresh forcé sur `kid` inconnu** (rotation
  anticipée). Échec de téléchargement -> 503.
- **RS256 uniquement** : `alg != "RS256"` -> 401 (anti **alg-confusion** HS256).
- **Décodage validé** : `jwt.decode(..., algorithms=["RS256"], audience=API_AUDIENCE,
  options={verify_exp, verify_nbf, verify_iss, verify_aud})` ; issuer re-vérifié contre
  `ALLOWED_ISSUERS`.

Preuves :
- `tests/backend/test_auth_jwt.py` — `kid` manquant, `alg` non autorisé, identité `oid`.
- `tests/backend/test_auth_jwt_real.py` — `test_forged_signature_rejected`,
  `test_expired_token_rejected`, `test_not_yet_valid_token_rejected`,
  `test_wrong_audience_rejected`, `test_wrong_issuer_rejected`,
  `test_alg_confusion_hs256_rejected`, `test_missing_kid_rejected`.
- `tests/backend/test_jwks_cache_ttl.py` — TTL respecté, refetch après TTL,
  refresh forcé sur `kid` inconnu.

### 2.2 Identité `oid` (V2/V3)

`verify_azure_ad_token` retourne `claims['oid']` ; un token sans `oid` -> 401
(`test_verify_missing_oid_raises_401`). L'`oid` est un GUID immuable et non réutilisable,
ce qui ferme la cause racine de l'IDOR par réutilisation d'UPN (AUD-02). Un invité/B2B
possède aussi un `oid` per-tenant et est accepté.

Preuves :
- `tests/backend/test_wave1_auth_identity.py` — `test_identity_is_oid_not_upn`,
  `test_identity_guest_b2b_accepted_via_oid`, `test_identity_missing_oid_rejected_401`.
- `tests/backend/test_auth_jwt.py` — `test_verify_returns_oid_not_upn`,
  `test_verify_does_not_return_upn`.

### 2.3 Garde IDOR `owner_hash` (V4)

`_assert_durable_owner` est le contrôle **autoritaire** : `owner_hash = hash_id(oid)`
(SHA-256) persisté dans l'input Durable, hard-fail **403** sur mismatch. La map en mémoire
`_audit_job_owners` n'est qu'un cache fast-path (sa divergence sous N>1 est neutralisée par
l'épinglage mono-instance — `SECURITY_POSTURE.md` §2/§3). Comportement fail-closed sur
statut terminal sans `owner_hash`.

Preuves :
- `tests/backend/test_audit_ownership.py` — `test_durable_owner_match_passes`,
  `test_durable_owner_mismatch_raises_403`, `test_durable_owner_uses_oid_hash_not_raw`,
  `test_durable_terminal_without_owner_hash_fails_closed`, `test_status_endpoint_blocks_non_owner`.
- `tests/backend/test_job_isolation.py` — `test_owner_hash_persisted_from_oid`,
  `test_two_oids_produce_distinct_owner_hash`, `test_durable_gate_blocks_cross_oid_status_read`.

### 2.4 OBO user-delegated (V3/V4)

`scripts/graph_obo.py` (`acquire_obo_graph_token` / `..._retrying`) échange l'assertion
utilisateur contre un token Graph **délégué**. Le RBAC SharePoint de l'utilisateur est
ainsi honoré en aval. Retry **transient-only** (429/503/504 + timeout/connexion httpx),
backoff plein-jitter, `Retry-After` borné ; **4xx auth et `ValueError` config NON retryés** ;
épuisement -> **503**. Le token Graph n'est jamais persisté (cf. `SECURITY_POSTURE.md` §4).

Preuves :
- `tests/backend/test_graph_obo.py` — `test_obo_builds_correct_request_and_returns_token`,
  `test_no_retry_on_401_non_transient`, `test_no_retry_on_403_non_transient`,
  `test_no_retry_on_valueerror_config`, `test_retry_on_429_then_success_honors_retry_after`,
  `test_exhaustion_raises_last_transient`.
- `tests/backend/test_wave1_auth_identity.py` —
  `test_planner_exchanges_obo_not_gateway_token`, `test_planner_503_when_obo_unconfigured`.
- `tests/backend/test_job_isolation.py` — `test_obo_exhaustion_returns_503_not_502`.

### 2.5 Lecture seule (read-only / lecture seule) (V4)

AC360 est un assistant **read-only** : aucune écriture sur SharePoint, le FIC est un
brouillon pour revue humaine, l'output est validé par JSON-schema (aucun effet de bord).
Combiné à l'OBO délégué (§2.4), l'utilisateur ne peut jamais agir au-delà de son propre
périmètre de lecture SharePoint. Les jetons app-only sont hors périmètre.

Preuves : la lecture seule effective est démontrée par l'absence d'écriture et par les
gardes d'appartenance/d'isolation — `tests/backend/test_audit_ownership.py`,
`tests/backend/test_job_isolation.py`.

---

## 3. Mapping ASVS (L1)

| ASVS Category | Contrôles AC360 (SEC-02) |
|---------------|--------------------------|
| **V2 Authentication** | Entra SSO, JWT RS256/JWKS (`scripts/auth.py`), identité `oid` |
| **V3 Session Management** | JWT stateless ; token OBO délégué jamais persisté |
| **V4 Access Control** | Garde IDOR `_assert_durable_owner` (`owner_hash` sur `oid`), OBO RBAC, lecture seule |

---

## 4. Renvois

- **SEC-01** — diagrammes d'architecture & flux PII ; frontières de confiance (cf. tableau §3 de SEC-01).
- **SECURITY_POSTURE.md** — §3 (IDOR `oid`), §4 (OBO 503), §5 (rédaction), §6 (journal 4 champs).
- **SEC-03** — matrice de couverture des menaces (STRIDE + OWASP LLM Top 10) réutilisant ces preuves.
