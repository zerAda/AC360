---
phase: 01-deep-code-audit-critical-fixes
reviewed: 2026-06-13T00:00:00Z
depth: standard
iteration: 2
files_reviewed: 7
files_reviewed_list:
  - scripts/auth.py
  - scripts/api_server.py
  - scripts/graph_obo.py
  - scripts/safe_logger.py
  - scripts/audit_trail.py
  - azure_functions/function_app.py
  - infra/main.bicep
findings:
  critical: 0
  blocker: 0
  warning: 0
  info: 4
  total: 4
status: clean
resolution_note: "WR-07 (dead acquire_obo_graph_token import in api_server.py, flake8 F401) fixed inline by orchestrator after iteration-2 re-review. flake8 clean, full suite 197 passed/1 skipped. Remaining 4 Info findings are accepted non-blocking carried items (out of critical_warning fix scope)."
---

# Phase 01: Code Review Report (iteration 2 — all warnings resolved)

**Reviewed:** 2026-06-13
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Re-review of the six Warning fixes (WR-01..06) landed across `054a0c1..2bdc97d`
(+ WR-06 in `054a0c1` on `safe_logger.py`). All six fixes are **correct and
complete**, and each verified against its stated contract:

- **WR-01** (`_assert_durable_owner`): now fails closed — `owner_hash` present →
  compare-or-403; `owner_hash` absent on a TERMINAL status (`Completed` /
  `Failed` / `Terminated`) → 403; only the non-terminal pre-input window is
  tolerated. The 404 short-circuit at `get_job_status` (line 705) still runs
  before the gate, so unknown jobs 404 rather than reaching the new branch. New
  tests in `test_job_status.py` / `test_audit_ownership.py` exercise it.
- **WR-02** (`_retry_after_seconds`): clamps to `_RETRY_AFTER_MAX_SECONDS = 30.0`,
  rejects `<= 0` and non-numeric (falls back to jitter backoff), eliminating the
  unbounded-block and the `time.sleep(negative)` `ValueError` escape.
- **WR-03** (`_check_resolve_rate_limit`): the same `len(_rate_limit_store) > 1000`
  overflow guard as the audit path is now present, scheduling `cleanup_rate_limits()`.
- **WR-04** (resolve + planner OBO): both now call `acquire_obo_graph_token_retrying`
  and map exhaustion to **503** (retriable), matching the audit path. The planner's
  nested OBO `try/except` re-raises its `HTTPException(503)` cleanly through the
  outer `except HTTPException: raise` — not downgraded to 500.
- **WR-05** (redacted detail): resolve/planner OBO failures use the static-message +
  `data=`-channel form; the planner Graph error body now flows through
  `{"body": e.response.text}` (redacted by WR-06's `redact_mapping`).
- **WR-06** (`log_security`): the `data` dict is now redacted via `redact_mapping(data)`
  before being appended, so the "no plaintext PII/secrets" guarantee holds for
  every caller, not only the audit-trail seam. Signature also corrected to
  `data: Optional[dict] = None) -> None` (closes prior IN-01).

Verification: full suite **351 passed, 1 skipped**; `mypy` clean on all eight
strict core modules (incl. `graph_obo.py`); `flake8` clean on every reviewed file
**except** one new unused-import flagged below.

No Critical/Blocker defects. One genuine regression introduced by WR-04 (an
orphaned import that fails the CI flake8 gate) plus carried-over Info items.

## Narrative Findings (AI reviewer)

## Warnings

### WR-07: WR-04 left `acquire_obo_graph_token` imported but unused — fails CI flake8 gate

**File:** `scripts/api_server.py:21`
**Issue:** WR-04 swapped all three OBO call sites (audit / resolve / planner) from
`acquire_obo_graph_token` to `acquire_obo_graph_token_retrying`. The non-retrying
symbol is still imported on line 21 but is now referenced nowhere in the module
(`grep` confirms the only occurrence is the import line). `flake8` reports
`api_server.py:21:1: F401 'graph_obo.acquire_obo_graph_token' imported but unused`.
Per CLAUDE.md, `flake8` is configured in `setup.cfg` and runs in CI
(`.github/workflows/ci.yml`); this is a hard lint failure that will block the
pipeline even though the runtime behavior is correct. This is a fix-introduced
regression, not a pre-existing condition.
**Fix:** Drop the dead symbol from the import:
```python
from graph_obo import acquire_obo_graph_token_retrying, obo_configured
```
(`acquire_obo_graph_token` remains the wrapper's internal callee in `graph_obo.py`
and is still exercised directly by `tests/backend/test_graph_obo.py`, so no test
import breaks.)

## Info

The following are carried items from iteration 1, explicitly accepted as
non-blocking per the re-review scope. They are unchanged by the fixes and are
listed for continuity only.

### IN-02: `redact` / `redact_mapping` parameter+return hints (carried)

**File:** `scripts/safe_logger.py:92` (`def redact(message, max_len=MAX_LEN):`)
**Issue:** `redact` — part of the declared `__all__` public API and the single
audited redaction surface — still lacks parameter and return annotations. CLAUDE.md
requires type hints on all function params/returns. (IN-01, the `log_security`
signature, was fixed in WR-06.)
**Fix:** `def redact(message: Any, max_len: int = MAX_LEN) -> str:`

### IN-03: OBO `"Bearer "` stripping uses `replace`, not a prefix strip (carried)

**File:** `scripts/graph_obo.py:57`
**Issue:** `(user_assertion or "").replace("Bearer ", "").strip()` removes every
occurrence of the substring, not just a leading scheme prefix. Harmless today (a
base64url JWT cannot contain a space) but does not express the stated intent.
**Fix:** `re.sub(r"^\s*Bearer\s+", "", user_assertion or "", flags=re.I).strip()`

### IN-04: `_is_transient` misses non-timeout transient transport errors (carried)

**File:** `scripts/graph_obo.py:98`
**Issue:** Only `httpx.TimeoutException` and `httpx.ConnectError` are treated as
transient. `httpx.ReadError` / `httpx.WriteError` / `httpx.RemoteProtocolError`
(transient connection-reset conditions) are not retried.
**Fix:** Broaden to `isinstance(exc, (httpx.TimeoutException, httpx.TransportError))`
or enumerate the additional classes intentionally.

### IN-06: `docIntel` provisioned with SKU `F0` (free tier) (carried)

**File:** `infra/main.bicep:107`
**Issue:** Document Intelligence pinned to `sku.name: 'F0'`. F0 has hard
daily/throughput caps inappropriate for a production OCR audit pipeline; under load
it throttles (429). Staging-shaped default in a production-hardened file.
**Fix:** Parameterize the SKU (`param docIntelSku string = 'F0'`, `S0` for prod) or
document explicitly that F0 is staging-only.

## Accepted carried items (not re-reported)

Per the re-review instructions, the following iteration-1 items are accepted as
non-blocking and intentionally NOT re-listed as new findings: the WR-01
"requires human verification" runtimeStatus-contract note (now mitigated by the
fail-closed terminal branch; the Durable status envelope shape remains a
deploy-time validation per IN-05), and IN-05 / IN-07 infrastructure-guard
follow-ups. IN-01 is resolved by WR-06.

---

_Reviewed: 2026-06-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard (iteration 2)_
