---
phase: 01-deep-code-audit-critical-fixes
plan: 06
subsystem: backend-gateway-orchestration
tags: [idor, oid, obo, redaction, audit-trail, locality, integration, security]
requires:
  - scripts/auth.py verify_azure_ad_token (returns immutable oid — Plan 01-02)
  - scripts/safe_logger.py redact + redact_mapping (single audited surface — Plan 01-02)
  - scripts/graph_obo.py acquire_obo_graph_token_retrying (bounded backoff — Plan 01-03)
  - scripts/audit_trail.py emit_document_access (4-field gated seam — Plan 01-04)
  - feature_flags.hash_id (one-way owner-hash)
provides:
  - "api_server owner_hash derived from hash_id(oid) at all 3 sites; _assert_durable_owner is the authoritative IDOR gate (hard-fail on mismatch)"
  - "OBO exchange on audit path routed through acquire_obo_graph_token_retrying; exhaustion -> HTTP 503 (not 502) with redacted detail"
  - "every dynamic HTTPException detail (_redacted_detail) + AppInsightsMiddleware telemetry dimensions routed through the audited redaction surface"
  - "document-access audit event emitted on the oid-bearing api_server path (AUD-07)"
  - "function_app single-activity JOBS_BASE_DIR locality invariant documented + proven (AUD-08)"
affects:
  - Phase 3 OBS-01 (real Azure Monitor exporter behind the same APPINSIGHTS gate)
  - Phase 2 INF-06 (OBO scope verification against staging app registration)
tech-stack:
  added: []
  patterns:
    - "Authoritative durable IDOR gate (persisted owner_hash) over an in-memory fast-path cache"
    - "Transient OBO exhaustion surfaces as retriable 503, never a misleading 502"
    - "All response detail + telemetry crossing a trust boundary routed through one audited redaction surface"
    - "Audit-trail emit anchored at the oid-bearing site; Durable state carries only the one-way owner_hash"
key-files:
  created: []
  modified:
    - scripts/api_server.py
    - azure_functions/function_app.py
    - tests/backend/test_audit_ownership.py
    - tests/backend/test_job_isolation.py
    - tests/backend/test_security_headers.py
    - tests/backend/test_job_status.py
    - tests/backend/test_killswitch_gate.py
    - tests/backend/test_auth_jwt_real.py
    - tests/azure_functions/test_jobs_dir_locality.py
decisions:
  - "Open Q3: kept absent-owner_hash as fail-open (not fail-closed-on-completed) to avoid breaking legacy/transient status shapes; mismatch is the real IDOR threat and hard-fails"
  - "resolve_document + planner OBO call sites left on the non-retrying wrapper / 502 (out of this plan's audit-path scope) — logged as a consistency follow-up"
  - "function_app references audit_trail but the canonical emit lives at api_server (oid-bearing); Durable input carries only the one-way owner_hash, never the oid"
metrics:
  duration_min: 35
  completed: 2026-06-13
---

# Phase 1 Plan 6: Wire oid IDOR Gate + 503 OBO + Redaction + Audit-Trail Locality Summary

The integration plan connects four Wave 1-2 seams (oid identity, bounded OBO retry, audited redaction, audit-trail emit) into the live request/orchestration paths: all three api_server ownership sites now hash the immutable oid with `_assert_durable_owner` as the authoritative hard-fail IDOR gate, the audit-path OBO exchange retries and surfaces exhaustion as a retriable 503, every dynamic detail and telemetry dimension is redacted, the document-access audit event fires at the oid-bearing site, and the single-activity JOBS_BASE_DIR locality invariant is documented and proven.

## What Was Built

### Task 1 — api_server oid IDOR gate + 503 OBO + redaction (AUD-03/05/06)
- Rebound the `verify_azure_ad_token` dependency binding to `oid` on `trigger_audit` and `get_job_status`; all three ownership sites now feed `hash_id(oid)` — feature-gate `_user_hash`, persisted `owner_hash` in the Durable post body, and the `_assert_durable_owner` comparison. No `hash_id(user_upn)` remains for ownership/storage keys.
- `_assert_durable_owner` documented as the authoritative IDOR gate: hard-fails 403 on owner_hash mismatch (the real threat); the in-memory `_assert_audit_owner` map is fast-path cache only. Absent-owner_hash stays fail-open (Open Q3) to avoid breaking legacy/transient status shapes.
- Audit-path OBO call routed through `acquire_obo_graph_token_retrying`; the exhaustion branch changed from `HTTPException(502)` to `503` with a `_redacted_detail(...)` generic message.
- Added `_redacted_detail(generic, *sensitive)` helper routing interpolated exception/PII through the single audited `safe_logger.redact` surface.
- `AppInsightsMiddleware` telemetry dimensions routed through `redact_mapping` before emit.
- `emit_document_access(oid=..., document_id=...)` fired on the audit path (the oid-bearing site).

### Task 2 — function_app audit_trail reference + single-activity locality (AUD-07/08)
- Imported the `audit_trail` seam and documented that the canonical document-access emit lives at the oid-bearing `api_server.trigger_audit` site — the Durable input carries only the one-way `owner_hash`, never the oid, so the activity cannot recompute `hash_id(oid)`.
- Documented the AUD-08 single-activity locality invariant on `_run_activity` (download->ocr->compare->make_fic share one JOBS_BASE_DIR/{document_id} on one VM) and `_audit_orchestration` (exactly one `activity_run_audit`, no fan-out, no output path across the activity boundary).
- Turned the Wave 0 locality test fully GREEN and added structural guards: no cross-activity output path in the orchestration payload, and an audit_trail-reference assertion.

## How It Works

```
JWT -> verify_azure_ad_token -> oid
  trigger_audit: hash_id(oid) -> feature gate + persisted owner_hash + emit_document_access
  OBO: acquire_obo_graph_token_retrying -> exhaustion -> 503 (redacted detail)
  get_job_status: _assert_durable_owner(data, oid) -> mismatch hard-fails 403 (authoritative)
  telemetry: redact_mapping(dims) before log_security

function_app: single activity (activity_run_audit) runs the whole chain on one VM /
  one JOBS_BASE_DIR; audit_trail referenced, canonical emit documented at api_server.
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Aligned stale real-JWT test to the oid identity contract**
- **Found during:** Wave-merge gate run (`pytest tests/backend tests/azure_functions tests/security`)
- **Issue:** `tests/backend/test_auth_jwt_real.py::test_valid_token_returns_upn` asserted the pre-oid contract (verify returns upn) and was left RED by Plan 01-02's oid cutover (01-02 updated other auth tests but not this one). It blocks this plan's required wave-merge gate.
- **Fix:** Added an `oid` claim to the token fixture; renamed/retargeted `test_valid_token_returns_oid` (asserts the immutable oid, not upn) and `test_missing_oid_rejected` (oid is the stable identity).
- **Files modified:** tests/backend/test_auth_jwt_real.py
- **Commit:** 32e48f0

**2. [Rule 3 - Blocking] Rebound coupled test call sites to the `oid=` keyword**
- **Found during:** Task 1 (renamed the `trigger_audit`/`get_job_status` dependency parameter to `oid`)
- **Issue:** `test_job_status.py` and `test_killswitch_gate.py` invoked the renamed functions by the old `user_upn=` keyword and would raise `TypeError`.
- **Fix:** Rebound the keyword to `oid=` in those two coupled callers (and in the listed plan tests).
- **Files modified:** tests/backend/test_job_status.py, tests/backend/test_killswitch_gate.py
- **Commit:** a302552

### Scope notes (logged, not fixed)
- `resolve_document` and `api_create_planner_task` keep the non-retrying `acquire_obo_graph_token` and 502 — they are separate OBO call sites outside this plan's audit-path scope. Logged to `deferred-items.md` as an AUD-05 consistency follow-up.

No auth gates were encountered. No architectural (Rule 4) changes were needed.

## Tests

- `tests/backend/test_audit_ownership.py`: durable owner match/mismatch->403, oid-hash-not-raw.
- `tests/backend/test_job_isolation.py`: owner_hash persisted from oid (not raw), two-oid distinct hash, cross-oid status read 403, OBO exhaustion -> 503.
- `tests/backend/test_security_headers.py`: telemetry dims routed through redact_mapping, _redacted_detail masks PII.
- `tests/azure_functions/test_jobs_dir_locality.py`: locality + single-activity (GREEN), no cross-activity output path, audit_trail reference documented.
- Verification: `pytest tests/backend/test_audit_ownership.py tests/backend/test_job_isolation.py tests/backend/test_security_headers.py tests/azure_functions/test_jobs_dir_locality.py -x` -> all pass.
- Wave-merge gate: `pytest tests/backend tests/azure_functions tests/security` -> 188 passed, 1 skipped.

## TDD Gate Compliance

Both tasks recorded a `test(...)` RED commit (50640d9, 11aa453) followed by an implementation commit (a302552 feat, e7204db feat). RED was confirmed failing before each implementation. Gate sequence satisfied.

## Commits

- 50640d9 test(01-06): add failing tests for oid IDOR gate, 503 OBO, redacted detail+telemetry (AUD-03/05/06)
- a302552 feat(01-06): wire oid IDOR gate + 503 OBO + redacted detail/telemetry in api_server (AUD-03/05/06)
- 11aa453 test(01-06): add failing tests for audit_trail reference + no cross-activity path (AUD-07/08)
- e7204db feat(01-06): reference audit_trail seam + document single-activity locality in function_app (AUD-07/08)
- 32e48f0 fix(01-06): align stale real-JWT test to oid identity contract (AUD-02 follow-through)

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file-access patterns, or trust-boundary schema introduced beyond the plan's threat_model.

## Self-Check: PASSED

- .planning/phases/01-deep-code-audit-critical-fixes/01-06-SUMMARY.md — FOUND
- scripts/api_server.py — FOUND (hash_id(oid) at 3 sites, 503 OBO, _redacted_detail, redact_mapping telemetry, emit_document_access)
- azure_functions/function_app.py — FOUND (audit_trail referenced, single-activity locality documented)
- Commit 50640d9 — FOUND
- Commit a302552 — FOUND
- Commit 11aa453 — FOUND
- Commit e7204db — FOUND
- Commit 32e48f0 — FOUND
- No hash_id(user_upn) for ownership/storage keys — confirmed via grep
- No 502 on the audit-path OBO failure branch — confirmed via grep
