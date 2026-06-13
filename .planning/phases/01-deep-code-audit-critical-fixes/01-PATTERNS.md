# Phase 1: Deep Code Audit & Critical Fixes - Pattern Map

**Mapped:** 2026-06-13
**Files analyzed:** 11 (8 modified, 3 created)
**Analogs found:** 11 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `scripts/auth.py` (MODIFY: return `oid`) | middleware (auth dependency) | request-response | self — existing UPN check `auth.py:138-144` | exact (in-place) |
| `scripts/api_server.py` (MODIFY: `hash_id(oid)` at 3 sites; redact HTTPException detail; 503 on OBO) | controller | request-response | self — existing `hash_id(user_upn)` calls `api_server.py:238,308,365` | exact (in-place) |
| `scripts/graph_obo.py` (MODIFY: bounded backoff retry, 503 on exhaustion) | service (token exchange) | request-response | self — existing `acquire_obo_graph_token` | exact (in-place) |
| `scripts/safe_logger.py` (MODIFY: redact telemetry dims + detail strings) | utility (cross-cutting) | transform | self — existing `redact()` / `log_security()` | exact (in-place) |
| `scripts/audit_trail.py` (CREATE: emit seam) | utility / observability | event-driven (emit) | `scripts/usage_tracker.py` (`build_usage_event` / `track`) + `safe_logger.log_security` | role-match |
| `azure_functions/function_app.py` (MODIFY: audit-trail emit at download activity) | orchestration | event-driven | self — `_run_activity` / `_download_as_user` | exact (in-place) |
| `infra/main.bicep` (MODIFY: single-instance assertions on `gwPlan`) | config (IaC) | n/a | self — `gwPlan` resource `main.bicep:127-132` | exact (in-place) |
| `tests/backend/test_audit_trail.py` (CREATE) | test | event-driven | `tests/backend/test_safe_logger_redaction.py` + `test_graph_obo.py` | role-match |
| `tests/azure_functions/test_jobs_dir_locality.py` (CREATE) | test | file-I/O | RESEARCH §Code Examples + `audit_pipeline.run_audit` DI shape | role-match |
| `tests/backend/test_graph_obo.py` (MODIFY: transient retry cases) | test | request-response | self — existing fake-`http_post` injection tests | exact (in-place) |
| `docs/security/SECURITY_POSTURE.md` (CREATE) | doc deliverable | n/a | `docs/security/SECURITY_BASELINE.md` (referenced in `safe_logger.py:7`) | role-match |

## Pattern Assignments

### `scripts/auth.py` — return `oid` (AUD-02)

**Analog:** self, the existing UPN validation block `auth.py:138-144`.

**Existing pattern to mirror** (`auth.py:138-144`):
```python
upn = claims.get("upn") or claims.get("preferred_username")
if not upn:
    log_security("ERROR", "No UPN in claims")
    raise HTTPException(status_code=401, detail="Le token ne contient pas d'identité.")

log_security("INFO", f"Token validated for user: {upn}")
return upn
```

**Change shape (per RESEARCH §Code Examples AUD-02):** extract `oid` after scope/role checks, require it (401 if absent — same shape as the UPN guard), keep `upn` for human log line only, and return `oid`. `verify_azure_ad_token` signature stays `-> str`. The return type/contract is the single seam consumed by every `Depends(verify_azure_ad_token)` caller in `api_server.py` (which currently binds `user_upn`). Note Pitfall 1 (RESEARCH:198): app-only tokens out of scope; guests are first-class (their per-tenant `oid` is their identity).

---

### `scripts/api_server.py` — owner_hash from oid + 503 + redacted detail (AUD-03/05/06)

**Analog:** self. Three ownership sites + one OBO failure site + the telemetry middleware.

**Site 1 — durable IDOR gate** (`api_server.py:238`, inside `_assert_durable_owner` lines 225-242):
```python
owner_hash = inp.get("owner_hash") if isinstance(inp, dict) else None
if owner_hash and owner_hash != hash_id(user_upn):   # ← feed oid, not upn
    log_security("WARNING", "...owner_hash Durable ne correspond pas", {"user": user_upn})
    raise HTTPException(status_code=403, detail="Accès refusé à ce job d'audit.")
```
This is already the authoritative hard-fail gate (AUD-03). Per RESEARCH Pattern 1, the only change is the hash input source (oid). Open Q3 (RESEARCH:354): consider fail-closed when `owner_hash` absent — planner's call.

**Site 2 — feature gate hash** (`api_server.py:308`): `_user_hash = hash_id(user_upn)` → `hash_id(oid)`.

**Site 3 — persisted durable owner_hash** (`api_server.py:365`): `"owner_hash": hash_id(user_upn)` → `hash_id(oid)`.

**OBO failure → 503 (AUD-05)** — current anti-pattern at `api_server.py:334-336`:
```python
except Exception as e:
    log_security("ERROR", f"OBO exchange failed: {e}")
    raise HTTPException(status_code=502, detail="Échec de l'autorisation déléguée (OBO).")  # ← must be 503
```
Change `502` → `503`; route the call through the new retrying wrapper (below). Keep the `run_in_threadpool(...)` wrapping (`api_server.py:332`).

**HTTPException detail redaction (AUD-06)** — current dynamic-detail risk: `detail` strings built from `f"...{e}"` / `{exc}` (e.g. `auth.py:47,114`). Pattern: route every dynamic detail through `redact()` and return a generic message + correlation id. The static French strings already in place are safe; the targeted fix is any `detail` interpolating an exception/user value.

**Telemetry middleware** (`api_server.py:84-90`, `AppInsightsMiddleware`):
```python
if os.environ.get("APPINSIGHTS_INSTRUMENTATIONKEY"):
    log_security("INFO", "AppInsights_Telemetry", { "method": ..., "url": ..., ... })
```
This is the existing emit gate. The `data` dict here is NOT currently passed through `redact()` (only the message is, via `log_security`). AUD-06 fix: redact the dimension *values* before emit — pattern lands in `safe_logger` (below) and is reused here.

---

### `scripts/graph_obo.py` — bounded backoff retry (AUD-05)

**Analog:** self — existing `acquire_obo_graph_token` (lines 36-80) with its injectable `http_post`. The retry wrapper preserves that injection seam so the existing `test_graph_obo.py` fakes keep working.

**RESEARCH §Code Examples AUD-05 reference** (transient set `{429, 503, 504}` + `httpx.TimeoutException`/`ConnectError`, Retry-After on 429, full jitter, 3 attempts, raise on exhaustion). Add a sibling `acquire_obo_graph_token_retrying(...)` wrapping the existing function; do NOT modify the inner exchange. `graph_obo.py` is mypy-strict (CONVENTIONS.md:41) → full type hints required. Use stdlib `random`/`time` (RESEARCH §Don't Hand-Roll — no new dep). `time.sleep` runs inside the threadpool, never the event loop (RESEARCH:297).

---

### `scripts/safe_logger.py` — extend redaction to telemetry + detail (AUD-06)

**Analog:** self — existing `redact()` (lines 84-114) and `log_security()` (lines 34-49). `redact()` already handles JWT/Bearer/webhook/KV-secret/email/IBAN/long-digits/ANSI/control-char/truncation.

**Change shape:** add a helper that maps `redact()` over the *values* of a dict (telemetry dimensions), since `redact()` today only takes a single string. Keep `__all__` updated (CONVENTIONS.md:130 — module declares public API). Existing masks (`_MASK_SECRET`, `_MASK_EMAIL`, `_MASK_PII`) are reused, not duplicated (RESEARCH §Don't Hand-Roll: "one audited redaction surface"). Already exercised by `test_safe_logger_redaction.py`.

---

### `scripts/audit_trail.py` (NEW) — emit seam (AUD-07)

**Analog:** `scripts/usage_tracker.py` (`build_usage_event(event_type, *, status=..., ...)` + `track(...)`, already imported as `track` in `api_server.py:311`) for the keyword-only event-builder shape, and `safe_logger.log_security` for the env-gated emit.

**RESEARCH §Code Examples AUD-07 reference** — the 4-field contract is locked: `{user_id_hash, document_id, ts_utc, verdict}`, **no raw PII**. Implement as a small function (e.g. `emit_document_access(*, oid, document_id, verdict=None)`) that computes `hash_id(oid)`, stamps `datetime.now(timezone.utc).isoformat()`, passes dims through `redact()`, and emits behind the existing `APPINSIGHTS_*` gate. Per Open Q2 (RESEARCH:349): emit-seam only this phase; Phase 3 attaches `configure_azure_monitor`. Follow keyword-only-arg convention (CONVENTIONS.md:119) and module-docstring convention.

**Call sites:** document-access path in `api_server.py` (around `trigger_audit`, after auth/owner_hash) and/or the download activity in `function_app.py` (`_download_as_user` / `_run_activity`).

---

### `azure_functions/function_app.py` — emit at download activity (AUD-07) + locality invariant (AUD-08)

**Analog:** self. `_run_activity` (lines 170-185) is the single activity that runs the whole `run_audit` chain; `_audit_orchestration` (lines 188-198) calls **exactly one** activity (`activity_run_audit`). This is the AUD-08 invariant to preserve and document — do NOT split into fan-out activities (RESEARCH Anti-Pattern). Add the audit-trail emit call here (import the new `audit_trail` helper, matching the existing `from audit_pipeline import ...` local-import style at line 35). Note JOBS_BASE_DIR is composed at `function_app.py:60,80` and `_make_fic:142`.

---

### `infra/main.bicep` — single-instance pin (AUD-04)

**Analog:** self — the `gwPlan` resource (`main.bicep:127-132`), currently `sku: { name: 'F1', tier: 'Free' }` with no explicit `capacity`.

**Change shape (RESEARCH Pitfall 2 / RQ4):** assert plan `sku.capacity = 1`, any autoscale `maximum = 1`, and document the gateway startup command `gunicorn --workers 1 -k uvicorn.workers.UvicornWorker api_server:app` as load-bearing for in-memory state (`_rate_limit_store` `api_server.py:105`, `_JWKS_CACHE` `auth.py:28`, `_audit_job_owners`). Add a Bicep comment (French docstring style consistent with existing `// ---` section comments). Mirror the existing hardened-site pattern (`functionApp` resource `main.bicep:137-152`: `httpsOnly`, `minTlsVersion: '1.2'`, `ftpsState: 'Disabled'`).

---

### `tests/backend/test_graph_obo.py` (MODIFY) + AUD-05 cases

**Analog:** self. Reuse the existing `_FakeResp(payload, status)` class (lines 13-24) and `fake_post` injection (lines 29-32). Add: transient 429/503/504 retried-then-success; 4xx not retried; exhaustion raises (→ caller maps 503); Retry-After honored on 429. Inject a fake clock/sleep to keep tests fast. Header on `_FakeResp` needs a `.headers` dict for the Retry-After case.

---

### `tests/backend/test_audit_trail.py` (NEW) — AUD-07

**Analog:** `test_safe_logger_redaction.py` (fake-secret constants `FAKE_JWT/FAKE_EMAIL/FAKE_IBAN` lines 18-25; `MagicMock/patch` style) + `test_graph_obo.py` (`sys.path.insert(0, .../scripts)` bootstrap line 8).

**Assert:** emitted event carries exactly `{user_id_hash, document_id, ts_utc, verdict}`; `user_id_hash == hash_id(oid)`; no raw `oid`/UPN/email/client-name leaks into dimensions (route a poisoned value through and assert it is redacted/absent). Behind the `APPINSIGHTS_*` gate — patch the env var.

---

### `tests/azure_functions/test_jobs_dir_locality.py` (NEW) — AUD-08

**Analog:** RESEARCH §Code Examples AUD-08 (verbatim starting point) + `audit_pipeline.AuditDeps`/`run_audit` DI shape. Existing `tests/azure_functions/` conftest provides the path bootstrap.

**Assert (two tests):** (1) `download()` and `ocr()` see the same `JOBS_BASE_DIR/{doc_id}` directory within one `run_audit` call (locality holds); (2) structural — `function_app._audit_orchestration` (or `_run_activity`) drives **exactly one** activity, guarding against future fan-out. Use `monkeypatch.setenv("JOBS_BASE_DIR", str(tmp_path))` and fake `download`/`ocr` callables.

---

### `docs/security/SECURITY_POSTURE.md` (NEW) — Phase 1 deliverable

**Analog:** `docs/security/SECURITY_BASELINE.md` (referenced in `safe_logger.py:7` — same `docs/security/` location and French security-doc register). Structure at Claude's discretion (CONTEXT.md:52).

**Must honestly frame "immutability"** (RESEARCH Pitfall 3 / A2): Log Analytics has NO table-level WORM lock — describe as "append-only ingestion (no in-place edit API) + long retention + RBAC + workspace resource lock." Cover AUD-01 re-validation results, the single-instance pin as load-bearing, owner_hash/oid IDOR closure, OBO 503 fix, redaction surface, and the audit-trail field contract. Feeds Phase 5 (RGPD Evidence Pack).

## Shared Patterns

### Redaction (cross-cutting — AUD-06)
**Source:** `scripts/safe_logger.py` `redact()` (lines 84-114), `log_security()` (lines 34-49). Defense-in-depth twin: `audit_pipeline._safe_error` / `_SENSITIVE_ASSIGN` (`audit_pipeline.py:51-74`).
**Apply to:** every HTTPException `detail` that interpolates a dynamic value (auth/OBO/download hot paths), all App Insights telemetry dimensions, and the new audit-trail event dims.
```python
text = _JWT_RE.sub(_MASK_SECRET, text)
text = _BEARER_RE.sub("Bearer " + _MASK_SECRET, text)
text = _EMAIL_RE.sub(_MASK_EMAIL, text)
# ... single audited surface; do not add per-call-site regexes (RESEARCH §Don't Hand-Roll)
```

### Deterministic ownership hash (AUD-02/03)
**Source:** `scripts/feature_flags.py` `hash_id` (lines 22-23) — SHA-256, lowercased/stripped, no salt.
**Apply to:** all 3 ownership sites in `api_server.py` (238, 308, 365) and the audit-trail emit. Input source changes from `upn` → `oid` everywhere; the function itself is unchanged.
```python
def hash_id(raw: str) -> str:
    return hashlib.sha256((raw or "").strip().lower().encode("utf-8")).hexdigest()
```

### Env-gated emit (AUD-07)
**Source:** `api_server.py:84` (`if os.environ.get("APPINSIGHTS_INSTRUMENTATIONKEY")`) — existing telemetry gate.
**Apply to:** the new `audit_trail` emit seam so it stays inert until Phase 3 wires `configure_azure_monitor`.

### Dependency-injected, fake-driven tests
**Source:** `test_graph_obo.py` injectable `http_post` + `_FakeResp`; `audit_pipeline.AuditDeps` callables.
**Apply to:** all new/modified tests — no live cloud SDK, no Durable runtime (CONTEXT.md:70).

### Test bootstrap
**Source:** `test_graph_obo.py:8` — `sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))`.
**Apply to:** new backend test; `tests/azure_functions/` relies on its own conftest path bootstrap.

## No Analog Found

None. Every file maps to an existing in-repo analog (this is a brownfield audit + targeted-fix phase; all work modifies tested seams).

## Metadata

**Analog search scope:** `scripts/`, `azure_functions/`, `azure_functions/shared/`, `tests/backend/`, `tests/azure_functions/`, `infra/`, `docs/security/`
**Files scanned (read):** auth.py, graph_obo.py, safe_logger.py, api_server.py (targeted ranges), audit_pipeline.py, function_app.py, feature_flags.py (hash_id), main.bicep (gwPlan range), test_graph_obo.py, test_audit_ownership.py, test_safe_logger_redaction.py
**Pattern extraction date:** 2026-06-13
