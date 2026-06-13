---
phase: 01-deep-code-audit-critical-fixes
plan: 02
subsystem: backend-auth-logging
tags: [auth, identity, oid, redaction, idor, security, tdd]
requires:
  - scripts/auth.py verify_azure_ad_token (JWT validation pipeline)
  - scripts/safe_logger.py redact() (single audited redaction surface)
provides:
  - "verify_azure_ad_token returns immutable Entra oid (str); 401 on missing oid"
  - "safe_logger.redact_mapping(dict) -> dict — dict-value redaction helper (in __all__)"
affects:
  - Plan 01-06 (api_server owner_hash gate rebinds callers to hash_id(oid) + telemetry redaction)
  - Plan 01-04 (audit-trail emit uses redact_mapping for dimensions)
  - Plan 01-03 (graph_obo identity threading)
tech-stack:
  added: []
  patterns:
    - "Identity derived from immutable per-tenant oid, never mutable upn (closes UPN-reuse IDOR at source)"
    - "Single audited redaction surface: redact_mapping reuses redact(), zero new regexes"
key-files:
  created: []
  modified:
    - scripts/auth.py
    - scripts/safe_logger.py
    - tests/backend/test_auth_jwt.py
    - tests/backend/test_wave1_auth_identity.py
    - tests/backend/test_safe_logger_redaction.py
decisions:
  - "verify_azure_ad_token returns oid (claims['oid']) keeping the -> str signature; upn kept for log line only"
  - "App-only (client-credentials) tokens documented out of scope inline (AC360 is delegated-user only)"
  - "Redaction helper named redact_mapping; takes Mapping, returns new dict, leaves non-str values intact"
metrics:
  duration_min: 7
  completed: 2026-06-13
---

# Phase 1 Plan 2: Auth oid Identity + safe_logger Redaction Helper Summary

verify_azure_ad_token now returns the immutable Entra Object ID (oid) and rejects oid-absent tokens with 401, and safe_logger gains a redact_mapping(dict) helper that routes each string dict value through the single audited redact() surface — the two cross-cutting contracts later plans (01-03/01-04/01-06) consume.

## What Was Built

### Task 1 — verify_azure_ad_token returns oid (AUD-02)
- After the issuer/scope/role checks, `verify_azure_ad_token` extracts `oid = claims.get("oid")`. If falsy it logs `"No oid (object id) in claims"` and raises `HTTPException(401, "Le token ne contient pas d'identité stable.")` — mirroring the prior missing-UPN guard shape.
- The function now returns `oid` (a per-tenant GUID string) instead of `upn`. Signature stays `-> str`.
- `upn` is still read (`claims.get("upn") or claims.get("preferred_username")`) but only for a human-readable log line — never returned, never used as an identity key.
- Inline comment documents oid as the immutable, non-reusable per-tenant user GUID, that guests/B2B are first-class (per-tenant oid), and that app-only tokens are out of scope (delegated-user-only app). Cites the Entra id-token-claims reference.
- api_server.py deliberately NOT touched — callers are rebound in Plan 01-06.

### Task 2 — redact_mapping dict-value helper (AUD-06 helper half)
- Added `redact_mapping(mapping: Mapping[str, Any]) -> Dict[str, Any]` to `scripts/safe_logger.py`. Each string value is passed through the existing `redact()`; non-string values (int/None/bool) pass through unchanged; the input dict is not mutated (a new dict is returned).
- Reuses the single audited `redact()` surface — zero new masking regexes added (verified via `git diff`).
- Added `redact_mapping` to `__all__`. Introduced `from __future__ import annotations` + `typing` imports to match strict-module conventions.

## How It Works

```
JWT -> verify_azure_ad_token -> (issuer/scope/role checks) -> oid = claims['oid']
       oid falsy -> 401 ; else return oid  (upn only logged)

dict dims -> redact_mapping -> {k: redact(v) if isinstance(v,str) else v}  (new dict)
```

## Deviations from Plan

None - plan executed exactly as written. Both tasks followed the TDD RED -> GREEN cycle with no REFACTOR needed (changes were minimal). No deviation rules triggered; no auth gates encountered.

## Tests

- `tests/backend/test_auth_jwt.py`: added oid-returns-not-upn, missing-oid-401, guest-B2B-accepted, does-not-return-upn cases (drive the claim-extraction tail via patched header/key/decode + relaxed issuer/scope/role).
- `tests/backend/test_wave1_auth_identity.py`: added identity-is-oid, guest-B2B-via-oid, missing-oid-rejected cases.
- `tests/backend/test_safe_logger_redaction.py`: added email-value-masked, non-string-passthrough, input-not-mutated cases for redact_mapping.
- Final: `pytest tests/backend/test_auth_jwt.py tests/backend/test_wave1_auth_identity.py tests/backend/test_safe_logger_redaction.py -x` -> 22 passed, 1 skipped.

## TDD Gate Compliance

Both tasks recorded a `test(...)` RED commit followed by an implementation commit (`fix(...)` for Task 1, `feat(...)` for Task 2). RED was confirmed failing before each implementation. Gate sequence satisfied.

## Commits

- d794f82 test(01-02): add failing tests for oid identity contract (AUD-02)
- 0e73bb9 fix(01-02): return immutable oid as identity, 401 on missing (AUD-02)
- aaa1dc5 test(01-02): add failing tests for redact_mapping dict-value helper (AUD-06)
- f8e5cac feat(01-02): add redact_mapping dict-value helper to safe_logger (AUD-06)

## Known Stubs

None.

## Self-Check: PASSED

- scripts/auth.py — FOUND (oid extraction + 401 guard present)
- scripts/safe_logger.py — FOUND (redact_mapping in __all__, reuses redact())
- Commit d794f82 — FOUND
- Commit 0e73bb9 — FOUND
- Commit aaa1dc5 — FOUND
- Commit f8e5cac — FOUND
- api_server.py — confirmed NOT modified (acceptance criterion)
- No new regex constants in safe_logger.py — confirmed via git diff
