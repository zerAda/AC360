---
phase: 01-deep-code-audit-critical-fixes
reviewed: 2026-06-13T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - scripts/auth.py
  - scripts/api_server.py
  - scripts/graph_obo.py
  - scripts/safe_logger.py
  - scripts/audit_trail.py
  - azure_functions/function_app.py
  - infra/main.bicep
  - tests/backend/test_audit_trail.py
  - tests/backend/test_graph_obo.py
  - tests/azure_functions/test_jobs_dir_locality.py
findings:
  critical: 0
  blocker: 0
  warning: 6
  info: 7
  total: 13
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-06-13
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

This is a security-hardening phase that lands six audit fixes (AUD-02..08): the `oid`
identity / `owner_hash` IDOR gate, the OBO bounded-backoff retry, PII/secret redaction of
client-facing details and telemetry, the audit-trail emit seam, the single-instance Bicep pin,
and JOBS_BASE_DIR activity locality.

The core security controls are correctly built and the targeted intents are met:
- `hash_id(oid)` is used consistently as the ownership key on both the write side
  (`trigger_audit` persists `owner_hash` into the Durable orchestration input) and the read side
  (`_assert_durable_owner` compares against `hash_id(oid)`). `hash_id` lowercases its input, which
  is safe for a GUID `oid`.
- The OBO retry wrapper classifies transients correctly (429/503/504 + httpx timeout/connect),
  does NOT retry 4xx auth errors or config `ValueError`, raises the last transient on exhaustion,
  and `api_server` maps exhaustion to 503 (not 502). Test coverage is strong.
- Telemetry dimensions and the audit-trail seam route through the single audited
  `safe_logger.redact`/`redact_mapping` surface; the audit-trail event carries exactly the four
  contracted fields and is inert behind the AppInsights env gate.
- The Bicep single-instance pin is load-bearing and documented; the orchestration drives exactly
  one activity, preserving JOBS_BASE_DIR locality.

No Critical/Blocker defects were found. The findings below are robustness and consistency gaps —
the most material is the documented fail-open behavior of the authoritative IDOR gate when
`owner_hash` is absent (WR-01), and the unbounded/unvalidated `Retry-After` honored on a
threadpool-blocking path (WR-02).

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Authoritative IDOR gate fails open when `owner_hash` is absent from Durable input

**File:** `scripts/api_server.py:240-264` (`_assert_durable_owner`)
**Issue:** The "authoritative" Durable IDOR gate only raises 403 when `owner_hash` is present AND
mismatches. When `owner_hash` is missing — legacy jobs, OR an intermediate status shape that has
not yet surfaced orchestration input, OR a `showInput` payload the runtime returns without `input`
populated — the function returns silently and grants access. The in-memory fast-path
(`_assert_audit_owner`) only blocks when the job is still in the per-process cache; after a process
restart, deploy, or cache `clear()` (the 5000-entry overflow path at line 226-227), that cache is
empty. In the window where (a) the cache has been cleared/restarted and (b) the status response
lacks `owner_hash`, a different `oid` reading another user's job bypasses both gates. The
single-instance pin (AUD-04) and the fact that all new jobs carry `owner_hash` substantially
narrow this, but a gate described as "fail-closed / autoritaire" that returns success on absent
input is not actually fail-closed.
**Fix:** Distinguish "input definitively absent for a known job" from "input not yet available."
For a `Completed`/terminal job whose input cannot be read, fail closed:
```python
owner_hash = inp.get("owner_hash") if isinstance(inp, dict) else None
runtime_status = data.get("runtimeStatus")
if owner_hash:
    if owner_hash != hash_id(oid):
        log_security("WARNING", "Accès refusé (owner_hash Durable ne correspond pas)",
                     {"oid_hash": hash_id(oid)})
        raise HTTPException(status_code=403, detail="Accès refusé à ce job d'audit.")
    return
# owner_hash absent: tolerate only the transient pre-input window; fail closed once terminal.
if runtime_status in ("Completed", "Failed", "Terminated"):
    log_security("WARNING", "Statut terminal sans owner_hash — refus fail-closed",
                 {"oid_hash": hash_id(oid)})
    raise HTTPException(status_code=403, detail="Accès refusé à ce job d'audit.")
```
(If legacy jobs must remain readable, gate the fail-closed branch behind an env flag so prod can
opt in — this is the "Open Q3" follow-up referenced in the docstring; flag it explicitly rather
than leaving it ambient.)

### WR-02: `Retry-After` honored without upper bound or non-negative validation on a threadpool-blocking path

**File:** `scripts/graph_obo.py:104-116` (`_retry_after_seconds`), `:158-160`
**Issue:** `_retry_after_seconds` returns `float(raw)` for any numeric `Retry-After` value with no
clamp. The retry loop then calls `sleep(delay)` directly. `acquire_obo_graph_token_retrying` runs
under `run_in_threadpool` (api_server.py:364), so the delay blocks a worker thread. A throttling
or hostile upstream returning `Retry-After: 86400` would pin a threadpool thread for a day; with
the single-instance pin and a bounded threadpool, a burst of 429s can exhaust threads (availability
impact). Additionally a negative value (`Retry-After: -5`) parses to `-5.0`, and `time.sleep(-5)`
raises `ValueError` — which is non-transient, escapes the retry loop, and surfaces as a generic
503. RFC 7231 also permits an HTTP-date form, which `float()` silently rejects (acceptable
fallback, but undocumented).
**Fix:** Clamp to a sane non-negative bound:
```python
try:
    secs = float(raw)
except (TypeError, ValueError):
    return None
if secs <= 0:
    return None
return min(secs, 30.0)  # never block a worker thread longer than the cap
```

### WR-03: Resolve rate-limit path never triggers store cleanup — unbounded `_rate_limit_store` growth

**File:** `scripts/api_server.py:158-167` (`_check_resolve_rate_limit`)
**Issue:** `_check_rate_limit` schedules `cleanup_rate_limits()` when `len(_rate_limit_store) > 1000`,
but `_check_resolve_rate_limit` writes `resolve:{upn}` keys into the SAME shared store without ever
checking the size or scheduling cleanup. A deployment where resolve traffic dominates (search is
the more generous, more-used endpoint at 60/hr) accumulates `resolve:` keys that are only ever
pruned if the audit path happens to fire and cross 1000. Stale empty key lists are trimmed in-place
per call, but the keys themselves persist. Over a long-lived single process this is unbounded key
growth keyed by user identity.
**Fix:** Add the same overflow guard to the resolve path:
```python
async def _check_resolve_rate_limit(upn: str) -> None:
    if len(_rate_limit_store) > 1000:
        asyncio.create_task(cleanup_rate_limits())
    key = f"resolve:{upn}"
    ...
```

### WR-04: Inconsistent OBO failure mapping — resolve/planner return 502, audit returns 503

**File:** `scripts/api_server.py:469-473` (resolve), `:545` + `:559-561` (planner) vs `:364-373` (audit)
**Issue:** AUD-05's stated contract is that OBO exhaustion is a transient condition mapped to 503
(retriable), not 502 (which falsely implies a failed upstream). `trigger_audit` correctly uses the
retrying wrapper and returns 503 with a redacted detail. But `resolve_document` and
`api_create_planner_task` call the NON-retrying `acquire_obo_graph_token` and, on any OBO failure
(including a transient 429/503/504 or a timeout), raise `HTTPException(status_code=502, ...)`. This
is the exact 502-vs-503 confusion AUD-05 set out to fix, left in place on two of the three OBO call
sites. A transient throttle on document search returns a misleading 502 and clients will not retry.
**Fix:** Use `acquire_obo_graph_token_retrying` on these paths too, and map their failure to 503:
```python
graph_token = await run_in_threadpool(acquire_obo_graph_token_retrying, raw_auth)
...
except Exception as e:
    log_security("ERROR", f"OBO exchange failed (resolve): {e}")
    raise HTTPException(status_code=503,
                        detail=_redacted_detail("Échec de l'autorisation déléguée (OBO).", e))
```

### WR-05: Raw OBO failure detail logged unredacted in resolve/planner paths

**File:** `scripts/api_server.py:472`, `:485`, `:560`, `:563`
**Issue:** AUD-06's invariant is that every dynamic detail routes through `safe_logger.redact`.
`log_security` itself redacts the `message`, but several sites interpolate the raw exception into an
f-string passed as the message: `log_security("ERROR", f"OBO exchange failed (resolve): {e}")` and
`log_security("ERROR", f"Graph search error: {e}")`. `log_security` does call `redact(message)`, so
secrets/PII in `str(e)` ARE redacted before persistence — but line 560
`log_security("ERROR", f"Graph API Error: {e.response.text}")` interpolates a raw Graph HTTP body
into the message; redaction covers the known patterns (JWT/Bearer/email/IBAN/kv-secret) but an
arbitrary Graph error body may contain identifiers outside those patterns. Prefer the structured
`data=` form, which is also redacted via the same surface and keeps the message a static string.
**Fix:** Pass dynamic values through the `data` channel with a static message:
```python
log_security("ERROR", "Graph API Error", redact_mapping({"body": e.response.text}))
```
(Note: `redact_mapping` redacts values; `log_security`'s `data` arg is currently appended via
`f" | {data}"` WITHOUT calling `redact` on it — see WR-06. Fix WR-06 first or call `redact_mapping`
explicitly at the call site as shown.)

### WR-06: `log_security` does not redact the structured `data` payload

**File:** `scripts/safe_logger.py:37-52` (`log_security`)
**Issue:** `log_security` redacts only `message`; the `data` dict is appended verbatim via
`extra_info = f" | {data}"`. Multiple call sites pass dynamic dicts directly — e.g.
`{"document_id": request.document_id, "oid_hash": _user_hash}` (api_server.py:349),
`{"status": resp.status_code}` (`:290`), `{"error": str(e)}` (`:563`, `:591`). Any of these whose
values contain PII/secrets (a `document_id` carrying a client name, a stringified exception with a
token) is written to logs / App Insights WITHOUT redaction, despite the module docstring asserting
"aucune donnée client ni aucun secret ne doit être persisté en clair." The audit-trail seam dodges
this by calling `redact_mapping` itself before passing `data`, but no other call site does.
**Fix:** Redact the `data` mapping inside `log_security` so the guarantee holds for all callers:
```python
def log_security(level: str, message: str, data: Optional[dict] = None) -> None:
    safe_msg = redact(message)
    extra_info = f" | {redact_mapping(data)}" if data else ""
    ...
```

## Info

### IN-01: `log_security` signature uses mutable-style `dict = None` instead of `Optional[dict]`

**File:** `scripts/safe_logger.py:37`
**Issue:** `def log_security(level: str, message: str, data: dict = None):` annotates `data` as
`dict` but defaults to `None`, and omits the return type. CLAUDE.md mandates `Optional[Type]` for
nullable params and a return hint on every function.
**Fix:** `def log_security(level: str, message: str, data: Optional[dict] = None) -> None:`

### IN-02: `redact` / `redact_mapping` public functions lack full type hints

**File:** `scripts/safe_logger.py:87` (`def redact(message, max_len=MAX_LEN)`)
**Issue:** `redact` has no parameter or return annotations. It is part of the declared public API
(`__all__`) and the single audited redaction surface; CLAUDE.md requires type hints on all
function params/returns.
**Fix:** `def redact(message: Any, max_len: int = MAX_LEN) -> str:`

### IN-03: OBO `"Bearer "` stripping uses `replace`, not prefix strip

**File:** `scripts/graph_obo.py:57`
**Issue:** `(user_assertion or "").replace("Bearer ", "").strip()` removes EVERY occurrence of the
substring `"Bearer "` anywhere in the assertion, not just a leading scheme prefix. A base64url JWT
cannot contain a space so this is currently harmless, but the intent ("strip the prefix") is not
what the code does.
**Fix:** `assertion = re.sub(r"^\s*Bearer\s+", "", user_assertion or "", flags=re.I).strip()`

### IN-04: `_is_transient` misses non-timeout transient transport errors

**File:** `scripts/graph_obo.py:98`
**Issue:** Only `httpx.TimeoutException` and `httpx.ConnectError` are treated as transient transport
failures. `httpx.ReadError`, `httpx.WriteError`, and `httpx.RemoteProtocolError` (transient
network/connection-reset conditions) are `TransportError`s that are NOT caught, so they raise on the
first attempt instead of retrying.
**Fix:** Broaden to the transport base where appropriate, e.g.
`isinstance(exc, (httpx.TimeoutException, httpx.TransportError))` — or enumerate the additional
classes intentionally.

### IN-05: `data.get("input")` shape assumption is undocumented and brittle

**File:** `scripts/api_server.py:253`
**Issue:** `_assert_durable_owner` assumes the Durable instance-status response exposes orchestration
input under the top-level key `"input"` when `showInput=true`. This is correct for the current
webhook contract, but there is no test exercising the gate against a realistic status payload (the
test suite covers it indirectly). A future Durable runtime/version change to the status envelope
would silently turn the authoritative gate into a no-op (compounding WR-01).
**Fix:** Add a unit test that feeds `_assert_durable_owner` both a string-encoded and dict `input`
containing a mismatching `owner_hash` and asserts 403, plus a matching one that passes.

### IN-06: `docIntel` provisioned with SKU `F0` (free tier)

**File:** `infra/main.bicep:107`
**Issue:** Document Intelligence is pinned to `sku.name: 'F0'` (free). F0 has hard daily/throughput
caps and is inappropriate for a production OCR audit pipeline; under load it will throttle (429) and
silently degrade audit availability. This is a staging-shaped default in a file whose stated purpose
is the production-hardened posture.
**Fix:** Parameterize the SKU (`param docIntelSku string = 'F0'`) and set `S0` for the production
parameter file, or document explicitly that F0 is staging-only.

### IN-07: `appCommandLine` gunicorn pin is the sole enforcement of `--workers 1` on F1

**File:** `infra/main.bicep:198`
**Issue:** On the F1 tier the single-instance guarantee for in-memory state correctness depends
entirely on the `gunicorn --workers 1` command line; there is no `WEBSITES_CONTAINER_START_TIME_LIMIT`
or platform-level worker pin, and nothing fails the deploy if the command line is edited to add
workers. This is documented at length in comments but has no automated guard. Given the rate-limit,
JWKS cache, and IDOR fast-path correctness all hinge on it, a CI lint asserting the command line
contains `--workers 1` would harden the load-bearing pin.
**Fix:** Add a deploy-time / CI assertion (e.g. a Bicep `what-if` post-check or a test parsing
`main.bicep`) that fails if `appCommandLine` does not pin a single worker.

---

_Reviewed: 2026-06-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
