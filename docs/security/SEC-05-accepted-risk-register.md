# AC360 — SEC-05 : Registre des risques acceptés / problèmes connus

> Livrable de la **Phase 5 (RGPD & Security Evidence Pack)** — composant **SEC-05**
> du pack de preuves de sécurité. Date : 2026-06-15.
>
> **But :** classifier **chaque** item de `.planning/codebase/CONCERNS.md` en
> `must-fix-done` (fermé par un correctif Phase 1) ou `accepted-deferred`
> (non launch-blocking, avec justification explicite et source de différé).
> Rend visible le risque résiduel — **aucun risque accepté n'est divulgué
> silencieusement** (couvre STRIDE `T-05-14`).
>
> **Sources :** `.planning/codebase/CONCERNS.md` (intégralité), `docs/security/SECURITY_POSTURE.md`
> §1 « Table de disposition » + §8 « Items ouverts portés en avant »,
> `.planning/phases/01-deep-code-audit-critical-fixes/deferred-items.md`.
>
> **Conclusion (en tête) :** **aucun item `accepted-deferred` n'est
> launch-blocking.** Tous les bugs launch-blocking sont `must-fix-done` (Phase 1).
> Le caveat « pas de WORM » sur le journal d'audit est porté comme **risque accepté
> à confirmer avec le DPO** (voir §3, dernière ligne).
>
> **Renvois :** SEC-03 (matrice de menaces), SEC-04 (posture dépendances),
> SECURITY_POSTURE.md (preuve des correctifs Phase 1).

---

## 1. Légende des dispositions

| Disposition | Sens |
|-------------|------|
| **must-fix-done** | Risque launch-blocking **fermé par un correctif Phase 1** (voir SECURITY_POSTURE.md). |
| **accepted-deferred** | Risque **non launch-blocking**, accepté pour le go-live avec justification + source de différé. À reprendre post-launch. |

---

## 2. Registre — chaque item CONCERNS.md classifié

| Item (CONCERNS.md) | Catégorie CONCERNS | Disposition | Justification | Source |
|--------------------|--------------------|-------------|---------------|--------|
| **IDOR via owner_hash reuse** (UPN réutilisable après suppression) | Known Bug | **must-fix-done** | `owner_hash = SHA256(oid)` — `oid` est le GUID Entra per-tenant immuable, non réutilisable ; garde durable autoritaire `_assert_durable_owner` (403 sur mismatch) ; token sans `oid` rejeté en 401. | SECURITY_POSTURE §3 (Plan 01-02/01-06) |
| **OBO Token Exchange Error Propagation** (502 au lieu de 503) | Known Bug | **must-fix-done** | Retry transient-only borné ; exhaustion → **503** (et non 502) ; étendu aux sites OBO secondaires (`resolve_document`, `api_create_planner_task`) en revue de code. | SECURITY_POSTURE §4 ; deferred-items.md (RÉSOLU, commit `35b4f18`) |
| **Secrets in Error Messages** (détail HTTPException, télémétrie) | Security | **must-fix-done** | Tout `detail` dynamique + dimensions de télémétrie passent par `safe_logger.redact()` / `redact_mapping()` avant retour client/émission. | SECURITY_POSTURE §5 (Plan 01-02/01-06) |
| **Graph API Token Passed in Headers** | Security | **must-fix-done** | `safe_logger.redact()` masque les Bearer tokens ; en-têtes jamais loggés en clair. | SECURITY_POSTURE §1 + §5 |
| **No Audit Trail for Document Access** | Missing Feature | **must-fix-done** | Seam `emit_document_access` avec contrat 4 champs hachés `{user_id_hash, document_id, ts_utc, verdict}` ; exporter câblé Phase 3 (OBS-01). | SECURITY_POSTURE §6 (Plan 01-04/01-06) |
| **JWKS Cache Thread Safety** (`_JWKS_CACHE`) | Tech Debt | **must-fix-done** *(par pin mono-instance)* | Un seul process = un seul cache JWKS ; pas de divergence pendant rotation. Pas de réécriture async-lock (décision verrouillée — mono-instance EST la mitigation). | SECURITY_POSTURE §2 (Plan 01-05) |
| **Rate Limit Store Not Thread-Safe** (`_rate_limit_store`) | Tech Debt | **must-fix-done** *(par pin mono-instance)* | Un seul worker = un seul magasin ; pas de contournement inter-worker. `--workers 1` porteur dans `infra/main.bicep`. | SECURITY_POSTURE §2 (Plan 01-05) |
| **Rate Limit Cleanup Timing Window** | Known Bug | **must-fix-done** *(par pin mono-instance)* | Fenêtre de course acceptée à l'échelle d'une petite équipe sous un seul process ; atomicité inter-worker hors jeu (mono-worker). | SECURITY_POSTURE §1 (Plan 01-05) |
| **Path Traversal via Document ID (symlinks)** | Known Bug | **accepted-deferred** | Gardes existantes (UUID + `commonpath` + `_safe_filename`) re-validées vertes sous AUD-01 ; durcissement symlink reporté (non launch-blocking ; permissions du répertoire jobs restreignent la création de symlinks). | SECURITY_POSTURE §1 + §8 ; deferred-items.md |
| **Broad Exception Handling** | Tech Debt | **accepted-deferred** *(hot paths déjà resserrés)* | Resserré uniquement dans les hot paths auth/OBO/download touchés ; le balayage complet hors hot paths est de la dette différée (non launch-blocking). | SECURITY_POSTURE §1 + §8 |
| **JWKS Cache Missing Stale-While-Revalidate** | Security | **accepted-deferred** | Mitigation actuelle (TTL + refresh forcé sur kid inconnu) re-validée ; SWR différé (non launch-blocking). | SECURITY_POSTURE §1 + §8 |
| **Managed Identity Assumption Without Fallback** | Security | **accepted-deferred** *(dépendance infra Phase 2)* | Fail-fast clair conservé ; provisioning MI = dépendance infra Phase 2 (vérifié au déploiement). | SECURITY_POSTURE §1 |
| **Fabric OneLake Cache Poisoning / pas de fallback** | Security / Fragile | **accepted-deferred** | Mode « audit sans référence », circuit breaker, vérification d'intégrité = dette différée explicite, non launch-blocking. | SECURITY_POSTURE §1 + §8 |
| **Fabric OneLake Dependency** (échec total si Fabric down) | Fragile Area | **accepted-deferred** | Pas de moteur d'audit de secours ; circuit breaker / mode dégradé différés ; échec propre plutôt que silencieux. | SECURITY_POSTURE §8 |
| **Fuzzy Name Matching O(n) Linear Scan** | Performance | **accepted-deferred** | Indexation BK-tree/trigram différée ; acceptable pour la taille de base client cible (non launch-blocking). | SECURITY_POSTURE §1 + §8 |
| **Fabric Reference Data Loaded On Every Audit** | Performance | **accepted-deferred** | Cache TTL existant ; pré-chargement / cache distribué (Redis) différés (optimisation, non launch-blocking). | CONCERNS.md §Performance |
| **Document Download Redundancy** (double I/O) | Performance | **accepted-deferred** | Defense-in-depth assumée (eager-fail à la frontière API) ; coût I/O accepté. | CONCERNS.md §Performance |
| **Safe Logger Regex Compilation Not Cached** | Performance | **accepted-deferred** | Micro-optimisation ; Python met en cache les regex compilées ; impact négligeable. | CONCERNS.md §Performance |
| **Missing Optional Dependency Graceful Degradation** (thefuzz / python-Levenshtein) | Tech Debt | **accepted-deferred** | Dégradation gracieuse documentée (fallback pur-Python) ; cf. SEC-04 (`python-Levenshtein` optionnel). | CONCERNS.md §Tech Debt ; SEC-04 |
| **OCR Pipeline Timeout Handling** (pas de retry) | Fragile Area | **accepted-deferred** | Timeout configurable conservé ; retry/backoff exponentiel différé (non launch-blocking). | CONCERNS.md §Fragile Areas |
| **YAML Validation Script Import Complexity** | Fragile Area | **accepted-deferred** | Validateur garde l'app de prod fail-closed en CI ; durcissement des erreurs de parsing différé (outil dev/CI, non runtime). | CONCERNS.md §Fragile Areas |
| **In-Memory Rate Limit Store (scaling)** | Scaling Limit | **accepted-deferred** *(neutralisé par pin mono-instance)* | Limite de scaling 10K+ users non atteinte (équipe 20–100) ; pin mono-instance porte la correction fonctionnelle ; Redis/sharding différés. | SECURITY_POSTURE §2 ; CONCERNS.md §Scaling |
| **JWKS Cache Single Instance (scaling)** | Scaling Limit | **accepted-deferred** | OK pour mono-instance (topologie verrouillée) ; cache centralisé différé. | CONCERNS.md §Scaling |
| **Fabric OneLake Index Memory (scaling)** | Scaling Limit | **accepted-deferred** | ~5 MB pour <50K clients ; lazy-loading/cache distribué différés pour 100K+. | CONCERNS.md §Scaling |
| **API Server Connection Pool (200 max)** | Scaling Limit | **accepted-deferred** | Suffisant à l'échelle cible ; backoff sur 429 Graph différé. | CONCERNS.md §Scaling |
| **No Bulk Operation Support** | Missing Feature | **accepted-deferred** | Audit mono-document par design ; endpoint batch hors périmètre du go-live. | CONCERNS.md §Missing Features |
| **No Export/Integration with External Systems** | Missing Feature | **accepted-deferred** | Webhooks/GraphQL hors périmètre ; pas de besoin launch. | CONCERNS.md §Missing Features |
| **No Admin Dashboard** | Missing Feature | **accepted-deferred** | Observabilité via Application Insights (Phase 3) ; dashboard dédié différé. | CONCERNS.md §Missing Features |
| **End-to-End OCR + Fabric Comparison (test gap)** | Test Coverage Gap | **accepted-deferred** | Test full-stack en environnement staging recommandé avant chaque release ; couvert par GO-01 (E2E contrôlé live). | CONCERNS.md §Test Gaps |
| **Concurrent Rate Limit Violations (test gap)** | Test Coverage Gap | **accepted-deferred** | Neutralisé en pratique par le pin mono-worker ; harnais de test concurrent différé. | CONCERNS.md §Test Gaps ; SECURITY_POSTURE §2 |
| **Path Traversal with Symlinks (test gap)** | Test Coverage Gap | **accepted-deferred** | Lié au durcissement symlink différé ci-dessus ; cas de test symlink à ajouter si symlinks possibles en déploiement. | CONCERNS.md §Test Gaps |
| **Fabric Unavailability Fallback (test gap)** | Test Coverage Gap | **accepted-deferred** | Lié au mode dégradé Fabric différé ; chaos tests réseau différés. | CONCERNS.md §Test Gaps |
| **JWKS Rotation Edge Cases (test gap)** | Test Coverage Gap | **accepted-deferred** | Tests JWKS existants (`test_jwks_cache_ttl`) ; cas kid-inconnu + refresh concurrent à ajouter. | CONCERNS.md §Test Gaps |

---

## 3. Risque accepté flaggé pour le DPO

| Risque | Disposition | Justification | Source |
|--------|-------------|---------------|--------|
| **Journal d'audit immuable = PAS de WORM** (Log Analytics) | **accepted-deferred — à confirmer DPO** | Il n'existe **aucun verrou WORM / immutabilité au niveau table** sur Log Analytics. L'« immutabilité » repose sur la combinaison : ingestion **append-only** + rétention longue + **RBAC** workspace + **resource-lock** Azure. Que cette combinaison constitue une barre de preuve d'immutabilité acceptable reste **à confirmer avec le DPO en Phase 5**. Si un vrai WORM est exigé, c'est un redesign Logs-Ingestion → Storage immuable (hors périmètre, documenté comme écart). | SECURITY_POSTURE §7 (cadrage honnête) ; STRIDE `T-05-08` (SEC-03) |

---

## 4. Synthèse

- **must-fix-done :** tous les bugs launch-blocking de CONCERNS.md (IDOR `oid`,
  OBO 503, rédaction erreur/télémétrie, seam d'audit) + l'état en mémoire porté par
  le pin mono-instance (rate-limit, JWKS, fast-path IDOR).
- **accepted-deferred :** dette différée non launch-blocking (durcissement symlink,
  balayage broad-except, JWKS SWR, fallback/circuit-breaker Fabric, index fuzzy
  O(n), limites de scaling en mémoire, features manquantes, gaps de test) — chacune
  avec justification + source.
- **Aucun item `accepted-deferred` n'est launch-blocking.**
- Le caveat **no-WORM** est porté comme risque accepté **explicitement flaggé pour
  confirmation DPO** (§3) — pas de divulgation silencieuse (STRIDE `T-05-14`).

---

*SEC-05 — pack de preuves de sécurité Phase 5 — 2026-06-15.*
