---
phase: 01-deep-code-audit-critical-fixes
plan: 04
subsystem: backend-audit-trail
tags: [audit-trail, telemetry, emit-seam, AUD-07, pii-redaction, tdd]
requires:
  - "scripts/feature_flags.hash_id (SHA-256 of oid, no salt)"
  - "scripts/safe_logger.redact_mapping (dict-value redaction helper, Plan 01-02)"
  - "scripts/safe_logger.log_security (telemetry sink seam)"
provides:
  - "scripts/audit_trail.emit_document_access — AUD-07 document-access emit seam with the locked 4-field contract"
affects:
  - "Phase 3 OBS-01: attaches the real configure_azure_monitor exporter behind the same APPINSIGHTS gate without touching this call site"
  - "Plan 01-06 (gateway): can wire emit_document_access into the document-access path"
  - "Plan 01-07 (posture doc): immutable-retention sink for this trail documented there"
tech-stack:
  added: []
  patterns:
    - "Env-gated emit (APPINSIGHTS_INSTRUMENTATIONKEY / APPLICATIONINSIGHTS_CONNECTION_STRING); inert seam when unset"
    - "Deterministic one-way ownership hash via hash_id(oid); raw oid never crosses the telemetry boundary"
    - "All dimension values routed through safe_logger.redact_mapping before emit; no per-call-site regex"
    - "Locked 4-field contract {user_id_hash, document_id, ts_utc, verdict}; verdict omitted -> empty string, never missing"
    - "Keyword-only public API; ISO-8601 UTC timestamp via datetime.now(timezone.utc).isoformat()"
key-files:
  created:
    - "scripts/audit_trail.py"
  modified: []
decisions:
  - "Seam-only this phase (Open Q2): no azure-monitor-opentelemetry / configure_azure_monitor and no requirements.txt change; the real exporter lands in Phase 3 OBS-01 behind the same env gate."
  - "Gate accepts EITHER APPINSIGHTS_INSTRUMENTATIONKEY or APPLICATIONINSIGHTS_CONNECTION_STRING (matches api_server.py:84 idiom and the inert-case test which deletes both)."
  - "Redaction reuses safe_logger.redact_mapping (Plan 01-02) rather than introducing new regex — single audited surface; poisoned PII in any value is masked before emit."
  - "Reused the existing RED contract test from Plan 01-01 unchanged (it already fully specified the contract); only the implementation was added to turn it GREEN."
metrics:
  duration_min: 6
  completed_date: 2026-06-13
  tasks_completed: 1
  files_changed: 1
---

# Phase 01 Plan 04: AUD-07 Document-Access Audit-Trail Emit Seam Summary

New `scripts/audit_trail.py` module exposing `emit_document_access` — an env-gated, PII-free emit seam that writes a document-access record carrying EXACTLY the four locked fields `{user_id_hash, document_id, ts_utc, verdict}`, computes `user_id_hash` via `hash_id(oid)` (the raw oid never crosses the telemetry boundary), routes every dimension value through `safe_logger.redact_mapping`, and stays inert behind the existing AppInsights env gate so Phase 3 (OBS-01) can attach the real exporter without touching the call site — all with no new pip dependency. Turns the Wave 0 RED AUD-07 contract test GREEN.

## What Was Built

- **`scripts/audit_trail.py` (NEW)** — module with `from __future__ import annotations`, a module docstring documenting purpose and the seam-only design intent, and `__all__ = ["emit_document_access"]`.
- **`emit_document_access(*, oid, document_id, verdict=None) -> None`** — keyword-only public function that:
  - returns immediately (no emit) unless the AppInsights gate is open;
  - builds the dimension dict with exactly the four contracted keys;
  - sets `user_id_hash = hash_id(oid)`, `ts_utc = datetime.now(timezone.utc).isoformat()`, `verdict = verdict or ""`;
  - routes the dict through `safe_logger.redact_mapping` before emit;
  - emits via `log_security("INFO", "ac360_document_access", safe_dimensions)`.
- **`_appinsights_gate_open()`** — internal helper checking either `APPINSIGHTS_INSTRUMENTATIONKEY` or `APPLICATIONINSIGHTS_CONNECTION_STRING` is set and non-empty (mirrors `api_server.py:84`).

## How It Works

```
emit_document_access(oid, document_id, verdict)
  -> gate closed?  -> return (inert seam)
  -> gate open:
       dims = {user_id_hash: hash_id(oid), document_id, ts_utc: iso8601-utc, verdict or ""}
       safe = redact_mapping(dims)         # single audited redaction surface
       log_security("INFO", "ac360_document_access", safe)
```

The raw `oid` is hashed (one-way SHA-256, no salt) before it ever appears in a dimension. Any PII poisoned into a value (e.g. an email embedded in `document_id`) is masked by `redact()` (via `redact_mapping`) to `[EMAIL_MASQUÉ]` before emit. No exporter is wired here — `log_security` is the seam; Phase 3 OBS-01 attaches `configure_azure_monitor` behind the same gate.

## Verification

`pytest tests/backend/test_audit_trail.py -x` — 5 passed (was RED / ModuleNotFoundError in Wave 0):
- exactly the 4 contracted field keys emitted;
- `user_id_hash == hash_id(oid)` and raw oid absent from every dimension;
- poisoned email redacted/absent from emitted dimensions;
- `ts_utc` is an ISO-8601 UTC string (offset 0);
- emit is inert when the AppInsights gate is unset.

Constraint checks: `scripts/audit_trail.py` contains no `import azure...` and no `configure_azure_monitor(` call (only deferred-to-Phase-3 references in the docstring); `requirements.txt` (root + `azure_functions/`) unchanged; redaction reuses `safe_logger.redact_mapping` with no new regex.

## Deviations from Plan

None - plan executed exactly as written. The `tests/backend/test_audit_trail.py` file listed in `files_modified` already fully specified the contract from the Plan 01-01 RED scaffold and required no changes; only the new implementation module was added to turn it GREEN.

## TDD Gate Compliance

The RED gate commit is `29bc490` (`test(01-01): add audit-trail contract test scaffold (AUD-07)`) from Plan 01-01. The GREEN gate commit is `4932579` (`feat(01-04): add AUD-07 document-access audit-trail emit seam`). No REFACTOR commit was needed (implementation was minimal and clean on first pass).

## Known Stubs

None. The emit seam is intentionally inert without the AppInsights gate — this is the documented seam-only design (Open Q2), not a stub. The real exporter is the scoped responsibility of Phase 3 OBS-01.

## Self-Check: PASSED

- FOUND: scripts/audit_trail.py
- FOUND: commit 4932579 (feat(01-04): add AUD-07 document-access audit-trail emit seam)
- FOUND: tests/backend/test_audit_trail.py — 5 passed
