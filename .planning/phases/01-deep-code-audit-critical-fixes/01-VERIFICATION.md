---
status: passed
phase: 01-deep-code-audit-critical-fixes
verified: 2026-06-13
method: inline goal-backward verification (subagent dispatch hit transient API errors; orchestrator verified directly against the live codebase + full test run)
requirements: [AUD-01, AUD-02, AUD-03, AUD-04, AUD-05, AUD-06, AUD-07, AUD-08]
test_result: "188 passed, 1 skipped (pytest tests/backend tests/azure_functions tests/security)"
---

# Phase 1 Verification — Deep Code Audit & Critical Fixes

**Phase goal:** The committed hardening is re-validated against the production multi-worker topology, and every launch-blocking code fix is landed in the repo before the first prod deploy.

**Verdict: PASSED.** All 8 requirements are satisfied in the actual source (not just claimed in summaries), the full test suite is green, and the security-posture deliverable exists with honest framing. Carried-forward items are documented and correctly scoped to later phases.

## Goal-backward evidence

| Req | Must-be-true | Evidence (verified in source) | Status |
|-----|--------------|-------------------------------|--------|
| AUD-02 | `verify_azure_ad_token` returns Entra `oid`; 401 on missing | `scripts/auth.py:147-156` — `oid = claims.get("oid")`; `if not oid: raise HTTPException(status_code=401, ...)`; returns `oid`; `upn` retained for log line only | ✅ |
| AUD-03 | `hash_id(oid)` at ownership sites; durable check authoritative, map cache-only | `scripts/api_server.py:240-263` `_assert_durable_owner` compares persisted `owner_hash` to `hash_id(oid)` (authoritative hard-fail 403); `hash_id(oid)` at lines 334, 402 | ✅ |
| AUD-04 | Single-instance pin load-bearing in IaC | `infra/main.bicep:132-149,194` — `gunicorn --workers 1`, comment names `_rate_limit_store`/`_JWKS_CACHE`/`_audit_job_owners` as load-bearing, autoscale above 1 forbidden; explicit `sku.capacity=1` deferred to Phase 2 (F1 tier) — documented | ✅ |
| AUD-05 | Bounded-backoff transient-only OBO retry; 503 on exhaustion | `scripts/graph_obo.py:89,104,119` — `_is_transient`, `_retry_after_seconds`, `acquire_obo_graph_token_retrying`; `scripts/api_server.py:367-376` returns 503 on exhaustion (audit path) | ✅ |
| AUD-06 | HTTPException detail + telemetry dims redacted | `scripts/api_server.py:18,32,100` — imports `redact`/`redact_mapping`; telemetry emitted via `redact_mapping({...})`; dynamic detail via `redact(...)` | ✅ |
| AUD-07 | 4-field PII-free audit trail, env-gated, wired | `scripts/audit_trail.py:54-73` `emit_document_access` emits exactly `{user_id_hash, document_id, ts_utc, verdict}`, `user_id_hash = hash_id(oid)`, gated on APPINSIGHTS env vars; called at `api_server.py:346`; referenced in `function_app.py:46` | ✅ |
| AUD-08 | Single-activity JOBS_BASE_DIR locality preserved | `tests/azure_functions/test_jobs_dir_locality.py` — 4 passed (orchestration payload carries no cross-activity file path; single-activity invariant locked) | ✅ |
| AUD-01 | Re-validation green + security-posture doc | Full suite `188 passed, 1 skipped`; `docs/security/SECURITY_POSTURE.md` (179 lines) re-checks every "Addressed" mitigation under N>1 and frames immutability honestly (`SECURITY_POSTURE.md:16-17,138-150` — explicit "AUCUN verrou WORM") | ✅ |

## Requirement traceability

All of AUD-01..AUD-08 appear in PLAN frontmatter `requirements` fields across plans 01-01..01-07 and are marked **Complete** in `.planning/REQUIREMENTS.md`. No requirement unaccounted for.

## Test suite

`pytest tests/backend tests/azure_functions tests/security` → **188 passed, 1 skipped, 3 warnings** (35.3s). The 3 warnings are pre-existing FastAPI `on_event` / starlette `httpx` deprecations — out of scope, not regressions.

## Carried-forward (not phase-1 gaps — scoped to later phases)

1. OBO delegated Graph **scope verification** against live staging app registration → **Phase 2 INF-06** (operator-deferred at the 01-03 checkpoint).
2. Explicit Bicep `sku.capacity = 1` → **Phase 2 INF-02/B1** (F1/Free rejects explicit capacity; `--workers 1` pins single-worker now).
3. **AUD-05 secondary-site consistency**: `resolve_document` / `api_create_planner_task` OBO sites still use the non-retrying wrapper + 502 — logged in `deferred-items.md` as a follow-up (audit path, the launch-blocking surface, is fixed).
4. Log Analytics retention/immutability + workspace resource lock → **Phase 2/3 infra**; DPO confirmation of retention duration → **Phase 5**.

## Human verification

None required — all phase-1 must-haves are automatically verifiable and were confirmed against source + tests. The one human gate in the phase (security-posture sign-off, Plan 01-07 Task 3) was **approved** by the operator on 2026-06-13.
