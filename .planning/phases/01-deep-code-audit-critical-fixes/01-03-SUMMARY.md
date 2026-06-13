---
phase: 01-deep-code-audit-critical-fixes
plan: 03
subsystem: backend-auth-obo
tags: [obo, retry, resilience, AUD-05, mypy-strict, tdd]
requires:
  - "scripts/graph_obo.acquire_obo_graph_token (existing injectable http_post seam)"
provides:
  - "scripts/graph_obo.acquire_obo_graph_token_retrying — bounded-backoff transient-only OBO retry wrapper"
  - "scripts/graph_obo._is_transient — transient-failure classification predicate"
  - "scripts/graph_obo._retry_after_seconds — Retry-After parsing helper"
affects:
  - "Plan 01-06 (gateway): wires acquire_obo_graph_token_retrying into api_server.py and maps exhaustion 502 -> 503"
tech-stack:
  added: []
  patterns:
    - "Bounded exponential backoff with full jitter (random.uniform(0, base*2**i)), max 3 attempts"
    - "Transient-only retry classification ({429,503,504} + httpx timeout/connect); 4xx/ValueError propagate immediately"
    - "Graph Retry-After honored on 429"
    - "Injectable sleep callable for fast deterministic tests"
key-files:
  created: []
  modified:
    - "scripts/graph_obo.py"
    - "tests/backend/test_graph_obo.py"
decisions:
  - "OBO scope-verification checkpoint (Task 1) DEFERRED to Phase 2 INF-06 — staging app registration not yet available; success-path scope trust deferred, retry logic (scope-independent) proceeded."
  - "Retry wrapper added as a NEW function rather than modifying acquire_obo_graph_token, preserving the existing http_post seam and untouched inner-exchange tests."
  - "Exhaustion RAISES the last transient exception (does not return None) so the gateway maps it to HTTP 503, not 502."
metrics:
  duration_min: 9
  completed_date: 2026-06-13
  tasks_completed: 2
  files_changed: 2
---

# Phase 01 Plan 03: Bounded-Backoff OBO Retry (AUD-05) Summary

Bounded exponential-backoff, transient-only retry wrapper for the OBO token exchange (`acquire_obo_graph_token_retrying`) that honors Graph `Retry-After` on 429, uses full-jitter backoff otherwise, never retries 4xx/config errors, and raises on exhaustion so the gateway can map it to HTTP 503 — built with full type hints (mypy-strict clean) and stdlib-only.

## What Was Built

- **`scripts/graph_obo.py`**
  - `_TRANSIENT_STATUS = frozenset({429, 503, 504})` — module-level transient HTTP status set (Graph throttling/gateway).
  - `_is_transient(exc) -> bool` — True for `httpx.TimeoutException` / `httpx.ConnectError` and for exceptions whose `response.status_code` is in the transient set; False for 4xx auth errors and `ValueError` config errors.
  - `_retry_after_seconds(exc) -> Optional[float]` — parses the Graph `Retry-After` header (float seconds) only on 429; safe on missing/invalid headers.
  - `acquire_obo_graph_token_retrying(user_assertion, *, attempts=3, base=0.5, ...passthrough..., http_post=None, sleep=time.sleep) -> str` — wraps the existing exchange, forwarding `http_post` so test fakes still work. On a transient exc that is not the last attempt: delay = Retry-After (429) else `random.uniform(0, base*2**i)`, then `sleep(delay)` and retry. On non-transient or last attempt: raise.
  - **`acquire_obo_graph_token` itself is unchanged** — the injectable `http_post` seam and all its existing tests are untouched.

- **`tests/backend/test_graph_obo.py`** — extended (not rewritten) with the six+ behavior cases:
  - 429-then-200 retries once and honors `Retry-After` (asserted delay == 1.5).
  - 503-then-504-then-200 retried up to attempts=3, jitter delays within `[0, base*2**i]`.
  - 401 and 403 (non-transient) NOT retried — raise on first call, no sleep.
  - `ValueError` (empty assertion / missing config) NOT retried — raises immediately.
  - All-transient exhaustion raises the last transient exception (504), with sleeps only between attempts.
  - `httpx.TimeoutException` is transient → retried then success.
  - Added `.headers` to `_FakeResp`, a sequence-returning fake `http_post`, and a recording fake `sleep`. Existing `_FakeResp.raise_for_status` now raises a realistic `httpx.HTTPStatusError` carrying `.response`.

## Task 1 Checkpoint Resolution (DEFERRED)

Task 1 was a `checkpoint:human-verify` (gate="blocking-human") to confirm the exact delegated Microsoft Graph scope list consented on the **staging** OBO app registration. The orchestrator resolved it with the user prior to execution:

> "deferred — staging app registration not yet available; proceed with retry logic only, success-path scope trust deferred to Phase 2 INF-06"

**Disposition:** DEFERRED to **Phase 2 INF-06**. The retry LOGIC (transient classification) is scope-independent and was implemented in Task 2 regardless. The OBO success-path scope-trust assertions (exact consented delegated scopes; whether `https://graph.microsoft.com/.default` resolves them; any AADSTS65001 consent gap) remain an open verification item. This carries forward as input for:
- **Phase 2 INF-06** (live staging app registration verification), and
- the **security-posture doc (Plan 01-05)**.

This matches the existing STATE.md blocker: "Exact OBO delegated Graph scope list to be verified against the live staging app registration before replicating to prod."

## Verification

- `pytest tests/backend/test_graph_obo.py` → **14 passed in 0.06s** (well under the 60s budget; fake sleep means no real delay).
- `mypy scripts/graph_obo.py` → **Success: no issues found** (module is mypy-strict).
- No new third-party dependency: only stdlib `random` and `time` added; `httpx` was already imported in the original module.

## Threat Mitigations Applied

| Threat ID | Mitigation realized |
|-----------|---------------------|
| T-01-03-01 (DoS/availability) | Bounded backoff (3 attempts, full jitter, Retry-After) retries only `{429,503,504,timeout,connect}`; exhaustion raises → 503 (wired in 01-06). |
| T-01-03-02 (info disclosure / masking config errors) | Non-transient 4xx/`ValueError` are NOT retried — surface immediately rather than being masked as a 503 (Pitfall 4). |
| T-01-03-03 (retry storm / thundering herd) | Full jitter prevents synchronized retries; attempts capped at 3, ~0.5s base. |
| T-01-SC (supply chain) | No package install — stdlib `random`/`time` only. Legitimacy gate not triggered. |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test consistency] `test_obo_propagates_http_error` exception type**
- **Found during:** Task 2 (RED phase).
- **Issue:** The existing test expected a bare `RuntimeError` from `_FakeResp.raise_for_status`. To let `_is_transient` inspect `exc.response.status_code` realistically, `_FakeResp.raise_for_status` now raises `httpx.HTTPStatusError` (carrying `.response`), which mirrors real `httpx` behavior and is what the production `resp.raise_for_status()` raises.
- **Fix:** Updated the single existing assertion from `pytest.raises(RuntimeError)` to `pytest.raises(httpx.HTTPStatusError)`. Intent preserved (HTTP error propagates); the inner exchange code path is unchanged.
- **Files modified:** tests/backend/test_graph_obo.py
- **Commit:** 0dddb1f

**2. [Rule 3 - mypy-strict blocking] Retry-After float() narrowing**
- **Found during:** Task 2 (GREEN phase, mypy gate).
- **Issue:** mypy-strict flagged `float(headers.get("Retry-After"))` — `.get` returns `Any | None`, incompatible with `float()`.
- **Fix:** Extracted `raw = headers.get("Retry-After")` and added an explicit `if raw is None: return None` guard before `float(raw)`.
- **Files modified:** scripts/graph_obo.py
- **Commit:** 98cee90

## Known Stubs

None. No hardcoded empty values or placeholder text introduced.

## Commits

| Task | Type | Commit | Description |
| ---- | ---- | ------ | ----------- |
| 2 (RED) | test | 0dddb1f | add failing transient-only OBO retry tests (AUD-05) |
| 2 (GREEN) | feat | 98cee90 | add bounded-backoff transient-only OBO retry wrapper (AUD-05) |

## TDD Gate Compliance

- RED gate: `test(01-03): ...` commit 0dddb1f — 7 new cases failing (wrapper absent), 7 existing passing.
- GREEN gate: `feat(01-03): ...` commit 98cee90 — all 14 passing.
- REFACTOR gate: not needed; implementation was clean on first pass.

## Self-Check: PASSED

- FOUND: scripts/graph_obo.py (acquire_obo_graph_token_retrying defined)
- FOUND: tests/backend/test_graph_obo.py (retry cases present)
- FOUND commit: 0dddb1f
- FOUND commit: 98cee90
