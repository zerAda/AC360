---
phase: 01-deep-code-audit-critical-fixes
plan: 01
subsystem: testing
tags: [pytest, dependency-injection, audit-trail, app-insights, durable-functions, redaction, rgpd]

# Dependency graph
requires:
  - phase: 01-deep-code-audit-critical-fixes
    provides: "AuditDeps/run_audit DI shape, function_app._audit_orchestration single-activity structure, feature_flags.hash_id, safe_logger.redact/log_security"
provides:
  - "AUD-08 executable spec: JOBS_BASE_DIR locality + single-activity (no fan-out) structural assertions (tests/azure_functions/test_jobs_dir_locality.py)"
  - "AUD-07 executable spec: 4-field event contract {user_id_hash, document_id, ts_utc, verdict} + no-PII redaction (tests/backend/test_audit_trail.py, RED until 01-04)"
affects: [01-04, 01-05, 01-06, observability, rgpd-evidence]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave 0 RED-test scaffolds: pin contracts as failing/passing-but-locked specs before implementation (Nyquist rule)"
    - "DI fake-driven tests with no live cloud SDK / Durable runtime"

key-files:
  created:
    - tests/azure_functions/test_jobs_dir_locality.py
    - tests/backend/test_audit_trail.py
  modified: []

key-decisions:
  - "AUD-08 structural test drives the orchestration generator via gen.send() with a fake context — no azure.durable_functions import"
  - "AUD-07 test captures pre-emit dimensions by patching audit_trail.log_security (the env-gated emit seam), not a live Azure Monitor exporter"
  - "AUD-07 test imports scripts/audit_trail directly (no importorskip) so the missing module surfaces as a clear ModuleNotFoundError RED — module lands in Plan 01-04"

patterns-established:
  - "Locality invariant as executable spec: download() and ocr() must observe the same JOBS_BASE_DIR/{document_id} within one run_audit call"
  - "Single-activity guard: _audit_orchestration must call call_activity exactly once with 'activity_run_audit'"

requirements-completed: [AUD-07, AUD-08]

# Metrics
duration: 16min
completed: 2026-06-13
---

# Phase 1 Plan 1: Wave 0 RED Test Scaffolds (AUD-07 / AUD-08) Summary

**Two pytest scaffolds that pin the AUD-08 JOBS_BASE_DIR locality + single-activity invariant and the AUD-07 4-field no-PII audit-trail event contract as executable specifications, ahead of the production code later waves implement.**

## Performance

- **Duration:** ~16 min
- **Started:** 2026-06-13T09:16Z
- **Completed:** 2026-06-13T09:31Z
- **Tasks:** 2
- **Files modified:** 2 (both created)

## Accomplishments

- `tests/azure_functions/test_jobs_dir_locality.py` (AUD-08) — two tests, DI fakes only:
  - **Locality:** asserts `download()` and `ocr()` observe the same `JOBS_BASE_DIR/{document_id}` directory within a single `run_audit` call.
  - **Single-activity (structural):** drives `function_app._audit_orchestration` with a fake context and asserts `call_activity` is invoked exactly once and only with `"activity_run_audit"` — guarding against a future fan-out that would cross a file boundary (the AUD-08 anti-pattern).
- `tests/backend/test_audit_trail.py` (AUD-07) — locks the 4-field event contract `{user_id_hash, document_id, ts_utc, verdict}`:
  - exact-key-set assertion (no extra free-form fields),
  - `user_id_hash == hash_id(oid)` (SHA-256, no salt) and raw `oid` absent from every dimension,
  - poisoned PII (realistic email) routed through `document_id` is redacted/absent,
  - `ts_utc` is an ISO-8601 UTC string,
  - emit is inert when the `APPINSIGHTS_*` gate is unset.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create JOBS_BASE_DIR locality test scaffold (AUD-08)** — `ec352f3` (test)
2. **Task 2: Create audit-trail contract test scaffold (AUD-07)** — `29bc490` (test)

**Plan metadata:** (this commit — docs: complete plan)

## Files Created/Modified

- `tests/azure_functions/test_jobs_dir_locality.py` — AUD-08 locality + single-activity structural assertions; DI fakes against `AuditDeps`/`run_audit` and a fake orchestration context. No live SDK / Durable import.
- `tests/backend/test_audit_trail.py` — AUD-07 4-field + no-PII + hash_id + UTC contract against the not-yet-built `scripts/audit_trail.emit_document_access`. Captures pre-emit dimensions via the `log_security` seam.

## Decisions Made

- The AUD-08 structural test unrolls the orchestration generator with `gen.send()` and a fake context exposing `get_input()` + a `call_activity` recorder — avoids importing `azure.durable_functions` entirely.
- The AUD-07 test patches `audit_trail.log_security` (the env-gated emit seam described in PATTERNS §"Env-gated emit") to capture the pre-emit dimension dict, rather than wiring a live Azure Monitor exporter.
- AUD-07 imports `audit_trail` directly so the missing module fails loudly as `ModuleNotFoundError` — the intended Wave 0 RED, resolved when Plan 01-04 ships the helper.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. CRLF/LF git warnings on the new files are benign (OneDrive-synced Windows working copy).

## TDD / RED-State Confirmation

This is a Wave 0 RED-test plan. The success condition is failing/locked tests, not passing production code:

- **AUD-08 (`test_jobs_dir_locality.py`):** collects cleanly and **passes** against current code — the locality and single-activity invariants already hold in `audit_pipeline.run_audit` / `function_app._audit_orchestration`. These passing tests now **lock** the invariant: any future fan-out or cross-activity path handoff in later waves (or regressions) will turn them RED. Collection success (no import errors) is the hard acceptance criterion and is met. Plan 01-05 confirms/locks this invariant.
- **AUD-07 (`test_audit_trail.py`):** **RED by design** — `ModuleNotFoundError: No module named 'audit_trail'`. The module `scripts/audit_trail.py` (`emit_document_access`) does not exist yet; it lands in Plan 01-04. The test fully specifies the contract that 01-04 must satisfy.

Verification command result:
`pytest tests/azure_functions/test_jobs_dir_locality.py tests/backend/test_audit_trail.py` → locality test 2 passed; audit-trail test collection error (`ModuleNotFoundError audit_trail`). No `azure.durable_functions` / live Azure SDK import in either file (only a docstring mention).

## Known Stubs

None. Both files are complete test specifications; the AUD-07 RED state is an intentional reference to a future-wave module (Plan 01-04), documented above — not a stub.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both Wave 0 contracts are pinned. Later AUD-07/AUD-08 tasks verify against these pre-existing tests instead of "MISSING".
- **Plan 01-04** must create `scripts/audit_trail.py` with `emit_document_access(*, oid, document_id, verdict=None)` satisfying the 4-field + no-PII + hash_id(oid) + UTC ISO-8601 contract, behind the `APPINSIGHTS_*` gate, to turn `test_audit_trail.py` GREEN.
- **Plan 01-05** must preserve the single-activity / locality invariant to keep `test_jobs_dir_locality.py` GREEN.

## Self-Check: PASSED

- FOUND: tests/azure_functions/test_jobs_dir_locality.py
- FOUND: tests/backend/test_audit_trail.py
- FOUND: .planning/phases/01-deep-code-audit-critical-fixes/01-01-SUMMARY.md
- FOUND commit: ec352f3 (Task 1)
- FOUND commit: 29bc490 (Task 2)

---
*Phase: 01-deep-code-audit-critical-fixes*
*Completed: 2026-06-13*
