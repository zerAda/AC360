# AC360 — SEC-03 : Matrice de couverture des menaces (OWASP LLM Top 10 2025 + STRIDE → mitigation → preuve)

> Livrable de la **Phase 5 (RGPD & Security Evidence Pack)** — composant **SEC-03**
> du pack de preuves de sécurité. Date : 2026-06-15.
>
> **But :** permettre à un relecteur de conformité de lire chaque risque
> (OWASP LLM Top 10 **édition 2025** + chaque menace STRIDE des registres
> `<threat_model>` par phase) et d'en voir **la mitigation AC360 concrète** et
> **le test / la preuve qui l'atteste**. Chaque ligne porte une mitigation ET une
> référence de preuve (test, validateur, doc, schéma).
>
> **Sources :** `docs/security/SECURITY_POSTURE.md` (Phase 1), `docs/security/GUARDRAILS_VALIDATION.md`
> (Phase 4, PUB-04), les blocs `<threat_model>` STRIDE des `*-PLAN.md` Phases 1–5,
> les tests existants (`tests/backend`, `tests/security`, `tests/azure_functions`),
> `schemas/audit_result.schema.json`, OWASP Top 10 for LLM Applications **2025**
> (https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/).
>
> **Renvois croisés :** SEC-01 (architecture & flux PII / frontières de confiance),
> SEC-02 (authn/authz — Entra/JWT/OBO/IDOR/read-only + tests), SEC-04 (posture
> dépendances — supply chain LLM03), SEC-05 (registre des risques acceptés).

---

## 1. Matrice OWASP LLM Top 10 (2025) → mitigation AC360 → preuve/test

> Édition **2025** (IDs 2025, pas 2023). AC360 est un assistant **read-only** bâti
> sur Microsoft Copilot Studio + un backend FastAPI / Azure Durable Functions ; les
> risques LLM s'appliquent à la surface conversationnelle (Copilot), à la chaîne
> RAG (SharePoint), et à la chaîne d'audit OCR→Fabric.

| OWASP LLM (2025) | Surface AC360 | Mitigation AC360 | Preuve / test |
|------------------|---------------|------------------|---------------|
| **LLM01 — Prompt Injection** | Entrée Copilot / contenu de document | `contentModeration: High` (filtre RAI strict : jailbreak / prompt-injection / exfiltration) ; `useModelKnowledge: false` (réponses ancrées RAG-only, jamais de « connaissance générale » présentée comme fait client) ; gate validateur en CI (PUB-04) ; modération `High` uniforme sur chaque nœud RAG `SearchAndSummarizeContent` | `docs/security/GUARDRAILS_VALIDATION.md` §1 ; `scripts/validate_copilot_yaml.py` (`find_agent_guardrail_issues`, `find_rag_node_issues`) ; `tests/backend/test_validate_copilot_yaml.py` (`test_moderation_not_high_fails`, `test_useModelKnowledge_true_fails`) — gate CI exit 0 |
| **LLM02 — Sensitive Information Disclosure** | Logs, télémétrie, réponses d'erreur, journal d'audit | Surface de rédaction unique `safe_logger.redact()` / `redact_mapping()` (AUD-06, zéro nouvelle regex par site) ; `RedactingSpanProcessor` rédige nom de span + attributs string avant export télémétrie ; `_redacted_detail()` sur chaque `HTTPException.detail` dynamique ; journal d'audit limité à **4 champs hachés sans PII brute** `{user_id_hash, document_id, ts_utc, verdict}` | `tests/security/test_no_plaintext_secrets.py` ; `tests/backend/test_telemetry_redaction.py` (RedactingSpanProcessor) ; `docs/security/SECURITY_POSTURE.md` §5–§6 ; `scripts/safe_logger.py`, `scripts/telemetry.py`, `scripts/audit_trail.py` |
| **LLM03 — Supply Chain** | Dépendances pip + actions GitHub | Dependabot ENABLED (écosystèmes `pip` racine + `/azure_functions` + `/scripts` + `github-actions`, hebdomadaire, labels `dependencies`/`security`) ; politique d'épinglage PyJWT / deltalake / azure-functions-durable / python-Levenshtein ; gate `pip-audit` en CI | `.github/dependabot.yml` ; **SEC-04** (`docs/security/SEC-04-dependency-posture.md`) ; `.github/workflows/ci.yml` |
| **LLM05 — Improper Output Handling** | Sortie d'audit (verdict) + brouillon FIC | Le FIC est un **brouillon pour relecture humaine** (jamais une action automatique) ; sortie d'audit validée par JSON-schema (verdict, champs, score) ; read-only (aucune écriture downstream non revue) | `schemas/audit_result.schema.json` (validation en orchestration, `azure_functions/shared/audit_pipeline.py`) ; `tests/azure_functions/test_audit_pipeline.py` |
| **LLM06 — Excessive Agency** | Permissions de l'agent | **Read-only** strict (aucune écriture / action mutante sur SharePoint) ; OBO user-delegated honorant le RBAC SharePoint de l'utilisateur ; garde IDOR durable `_assert_durable_owner` (403 sur mismatch `owner_hash`) ; pas de fallback non-RBAC | `tests/backend/test_audit_ownership.py` / `tests/azure_functions/test_job_isolation.py` ; `docs/security/SECURITY_POSTURE.md` §3 ; **SEC-02** |
| **LLM07 — System Prompt Leakage** | `additionalInstructions` de l'agent | Instructions système testées en red-teaming (tentative d'exfiltration du system prompt refusée par `contentModeration: High`) ; pas de secret embarqué dans les instructions | `docs/governance/GOVERNANCE.md` §3 ; `docs/security/GUARDRAILS_VALIDATION.md` §2 (preuve live : conversation ID + capture d'un refus, opérateur post-publish) |
| **LLM08 — Vector & Embedding Weaknesses** | Index RAG SharePoint | RAG borné aux sources SharePoint connectées sous OBO (pas d'index partagé cross-tenant) ; périmètre documentaire = dossiers clients accessibles à l'utilisateur ; pas d'embedding store custom à empoisonner | **SEC-01** (frontières de confiance, flux RAG) ; `src/copilot/AC360/knowledge/` ; OBO RBAC (LLM06 ci-dessus) |
| **LLM09 — Misinformation** | Réponses ancrées | `useModelKnowledge: false` (pas de fabrication présentée comme fait) ; réponses = citations de documents existants ; verdict d'audit borné à l'enum (CONFORME / ECART / INCERTAIN / CLIENT_NON_TROUVE) ; INCERTAIN/CLIENT_NON_TROUVE plutôt qu'une affirmation hallucinée | `docs/security/GUARDRAILS_VALIDATION.md` §1 (grounded-only) ; `schemas/audit_result.schema.json` (enum verdict) ; `scripts/fabric_audit_engine.py` (logique de verdict) |
| **LLM10 — Unbounded Consumption** | Coûts / DoS gateway | Rate-limit par utilisateur (`_rate_limit_store`, 429) ; pin mono-instance/mono-worker porteur ; OCR timeout configurable ; pool de connexions httpx borné (`max_connections=200`) ; feature flags admin (blocage par user/team/feature) | `tests/backend/test_rate_limit.py` ; `scripts/feature_flags.py` ; `docs/security/SECURITY_POSTURE.md` §2 |

**Couverture OWASP LLM 2025 :** 9 des 10 risques sont mappés ci-dessus (LLM04
*Data and Model Poisoning* est hors périmètre — AC360 n'entraîne ni n'affine aucun
modèle ; le LLM est le service managé Copilot Studio, le « poisoning » de données de
référence est traité côté Fabric/SEC-05 *cache poisoning*). Chaque ligne porte une
mitigation **et** une preuve.

---

## 2. Matrice STRIDE (synthèse des registres `<threat_model>` par phase)

> Synthèse des blocs `<threat_model>` / *STRIDE Threat Register* des `*-PLAN.md`
> Phases 1–5. IDs `T-0x-NN` représentatifs ; chaque ligne porte une mitigation et
> une preuve. (`T-0x-SC` = supply-chain pip/actions, couvert par SEC-04 / pip-audit.)

| Threat ID | Catégorie STRIDE | Composant / menace | Mitigation AC360 | Preuve / test |
|-----------|------------------|--------------------|------------------|---------------|
| **T-01-SC** | Tampering | Installs pip/cargo (supply chain) | Aucun install non vérifié ; gate `pip-audit` ; Dependabot | `.github/workflows/ci.yml` ; **SEC-04** |
| **T-02-03** | Elevation of Privilege | Rôles Managed Identity trop larges | MI least-privilege (rôles scopés au strict nécessaire) | `infra/main.bicep` (assignations RBAC) ; **SEC-02** |
| **T-02-11 / T-02-24** | Compliance | Violation de résidence des données | `location` EU (France Central / West Europe) dans Bicep ; checkpoints opérateur M365/Fabric/Power Platform | `infra/*.bicep` ; RGP-06 (résidence, deux colonnes) |
| **T-03-01** | Information Disclosure | Chemin d'export télémétrie (PII) | `RedactingSpanProcessor.on_end` route nom de span + attributs string via `safe_logger.redact` (surface unique AUD-06) | `tests/backend/test_telemetry_redaction.py` (email/IBAN/JWT/secret masqués) |
| **T-03-03** | Information Disclosure | Télémétrie active en dev/test/import | `setup_telemetry()` early-return tant que le gate AppInsights deux-vars est fermé (inerte par défaut) ; import SDK paresseux | `scripts/telemetry.py` ; `tests/backend/test_telemetry_redaction.py` |
| **T-03-05** | Spoofing / Access Control | `/ready` atteignable non authentifié | `/ready` derrière `Depends(verify_azure_ad_token)` (401 si non-auth) | `tests/backend/test_ready_unauthenticated_returns_401` |
| **T-04-01** | Tampering | Clés de garde-fou `settings.mcs.yml` | `useModelKnowledge: false` + `contentModeration: High` asserts par le validateur (fail-closed) | `scripts/validate_copilot_yaml.py` ; `tests/backend/test_validate_copilot_yaml.py` |
| **T-04-02** | Information Disclosure | « Connaissance générale » présentée comme fait client | `useModelKnowledge: false` (RAG-only ancré) | `docs/security/GUARDRAILS_VALIDATION.md` §1 ; LLM01/LLM09 ci-dessus |
| **T-04-06** | Elevation of Privilege | Mauvais mode auth → fallback non-RBAC | Mode auth user-token forcé ; pas de fallback non-RBAC ; OBO honore le RBAC SharePoint | **SEC-02** ; `tests/backend/test_audit_ownership.py` |
| **T-04-09** | Tampering / Info Disclosure | Prompt injection / exfiltration via contenu de document | `contentModeration: High` ; `useModelKnowledge: false` ; gate validateur (LLM01) | `docs/security/GUARDRAILS_VALIDATION.md` ; `scripts/validate_copilot_yaml.py` |
| **T-05-06** | Information Disclosure | PII dans attributs/nom de span (LLM02) | `RedactingSpanProcessor` + `safe_logger.redact` (surface unique) | `tests/backend/test_telemetry_redaction.py` ; `tests/security/test_no_plaintext_secrets.py` |
| **T-05-08** | Repudiation | Prétention WORM/immutabilité de table pour le journal d'audit | **Pas de WORM** : « immutabilité » = ingestion append-only + rétention longue + RBAC + resource-lock (cadrage honnête) ; flag DPO (voir SEC-05) | `docs/security/SECURITY_POSTURE.md` §7 ; **SEC-05** (ligne risque accepté, flag DPO) |
| **T-05-09** | Spoofing | JWT forgé/invalide au gateway | Validation JWT RS256 via JWKS Entra ; audience + issuer vérifiés ; token sans `oid` rejeté en 401 | `tests/backend/test_auth_jwt_real.py` ; `scripts/auth.py` ; **SEC-02** |
| **T-05-10** | Elevation of Privilege / Info Disclosure | IDOR — accès au job d'audit d'autrui | `owner_hash = SHA256(oid)` (GUID per-tenant immuable) ; garde durable autoritaire `_assert_durable_owner` (403 sur mismatch) | `tests/backend/test_audit_ownership.py` / `tests/azure_functions/test_job_isolation.py` ; `docs/security/SECURITY_POSTURE.md` §3 |
| **T-05-12** | Tampering | Prompt injection (LLM01) | `contentModeration High` + `useModelKnowledge=false` + gate validateur | `docs/security/GUARDRAILS_VALIDATION.md` ; `validate_copilot_yaml.py` |
| **T-05-13** | Tampering | Dépendance vulnérable/compromise (LLM03 supply chain) | Dependabot (pip + actions) + politique d'épinglage PyJWT/deltalake | **SEC-04** ; `.github/dependabot.yml` |
| **T-05-14** | Repudiation | Risque résiduel non divulgué expédié silencieusement | SEC-05 classifie chaque item CONCERNS.md ; items accepted-deferred avec justification + source ; caveat no-WORM flag DPO | **SEC-05** (`docs/security/SEC-05-accepted-risk-register.md`) |

---

## 3. Synthèse de couverture

- **OWASP LLM Top 10 (2025) :** 9/10 risques mappés à une mitigation + preuve ;
  LLM04 (Data/Model Poisoning) hors périmètre (pas d'entraînement/fine-tuning AC360).
- **STRIDE :** chaque menace launch-blocking des registres Phases 1–5 est soit
  **mitigée + testée** (auth, IDOR, rédaction, garde-fous, retention), soit
  **acceptée + documentée** (SEC-05), soit **portée en infra** (SEC-04 supply chain).
- **Surface de preuve :** tests automatisés (`tests/backend`, `tests/security`,
  `tests/azure_functions`), validateur CI (`validate_copilot_yaml.py`), schéma
  (`schemas/audit_result.schema.json`), docs (GUARDRAILS_VALIDATION, SECURITY_POSTURE),
  config (`.github/dependabot.yml`). Aucune ligne sans preuve.
- **Renvois :** SEC-01 (flux PII / frontières), SEC-02 (authn/authz détaillé),
  SEC-04 (posture dépendances), SEC-05 (risques acceptés). Les preuves *live*
  (red-teaming prompt-injection, no-PII télémétrie) sont capturées par l'opérateur
  post-publish (`GUARDRAILS_VALIDATION.md` §2, GO-01).

---

*SEC-03 — pack de preuves de sécurité Phase 5 — 2026-06-15.*
