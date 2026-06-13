# Phase 1: Deep Code Audit & Critical Fixes - Research

**Researched:** 2026-06-13
**Domain:** Python (FastAPI + Azure Durable Functions) security hardening; Entra ID identity claims; Azure Monitor/Log Analytics audit trail; OBO retry; single-instance App Service topology
**Confidence:** HIGH (all five genuine unknowns answered against current Microsoft Learn docs; landing sites confirmed against repo source)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Launch-blocking bar** = items that break correctness or security under the production topology: the 5 success criteria plus the IDOR (owner_hash reuse) and PII-in-error/trace bugs in `.planning/codebase/CONCERNS.md`. Everything else is logged as deferred tech debt, not fixed this phase.
- **In-memory store thread-safety** (JWKS cache, rate-limit store): the single-instance pin (scale-out max = 1, one worker) is the mitigation. Document as load-bearing in IaC; do NOT add async-lock rewrites this phase.
- **Broad `except Exception` cleanup**: tighten only in the auth / OBO / download hot paths touched this phase; leave other occurrences as deferred debt.
- **Phase output**: a written security-posture document (feeds Phase 5) + targeted code fixes + accompanying tests, all landed in-repo.
- **owner_hash** = SHA-256 of the Entra **Object ID** (`oid` claim), **no salt** (deterministic lookup; `oid` is already an opaque GUID). Closes the UPN-reuse IDOR bug.
- The **durable `owner_hash` check is the authoritative IDOR gate**; the in-memory ownership map is a fast-path cache only.
- **Clean cutover** — app never deployed; no existing hashes to migrate or dual-read.
- **Immutable log sink** = App Insights custom events → Log Analytics workspace with retention/immutability policy. Workspace policy provisioning is a Phase 2/3 dependency; **this phase wires the emit path and field contract.**
- **Audit record fields** = user-id hash, document id, timestamp (UTC), verdict. **No raw PII** (no UPN, no client name).
- **Client-facing error bodies**: route every HTTPException detail through `safe_logger.redact()`; return a generic message + correlation id.
- **App Insights trace redaction**: extend `redact()` coverage so PII/secrets are stripped before telemetry emit, not just file logs.
- **OBO retry**: bounded exponential backoff — 3 attempts, ~0.5s base, jitter; retry ONLY transient failures (request timeouts, 429, 503, connection errors), not auth/4xx. On exhaustion return **HTTP 503** (not 502).
- **JOBS_BASE_DIR**: keep the single-activity chain so download→OCR→compare→FIC artifacts stay co-located. Document as the pipeline invariant. Add a test asserting the chain shares the artifact path.

### Claude's Discretion
- Exact backoff jitter algorithm, correlation-id format, security-posture doc structure, and test organization — consistent with existing codebase conventions.

### Deferred Ideas (OUT OF SCOPE)
- Async-lock thread-safety rewrites for in-memory stores (mitigated by single-instance pin).
- Distributed cache / Redis scale-out.
- Symlink path-traversal hardening, Fabric-unavailable fallback mode, fuzzy-match indexing, admin dashboard, bulk/webhook endpoints — logged in CONCERNS.md as non-launch-blocking.
- Full sweep of broad `except Exception` blocks outside touched hot paths.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUD-01 | Re-validate every "addressed" mitigation under the production topology; surface launch-relevant bugs | §"Re-validation under single-instance topology" + §Common Pitfalls; topology answered by RQ4 (App Service single worker) and RQ5 (activities are stateless / multi-VM) |
| AUD-02 | `owner_hash` derived from Entra **Object ID** (`oid`), not UPN | RQ1 — `oid` is the immutable, non-reusable per-tenant GUID; `verify_azure_ad_token` must return `oid` |
| AUD-03 | Durable `owner_hash` check is authoritative IDOR gate; in-memory map is cache only | RQ1 + Code Examples; `_assert_durable_owner` must hard-fail when owner_hash present and mismatched |
| AUD-04 | Gateway pinned to single instance (scale-out max = 1, one worker), documented load-bearing | RQ4 — App Service: pin plan capacity=1, `WEBSITE_*`/autoscale max=1, gunicorn `--workers 1`; assert in `infra/main.bicep` |
| AUD-05 | OBO retries transient failures with bounded exponential backoff (no false 502) | RQ3 — transient set = timeouts/connection errors/429/503/504; honor Graph `Retry-After`; 503 on exhaustion |
| AUD-06 | Client error responses + App Insights traces redacted of PII/secrets | RQ2 + §safe_logger; extend `redact()` to HTTPException detail + telemetry `extra` dimensions |
| AUD-07 | Document-access audit trail (user-id hash, document id, timestamp, verdict) written to immutable log | RQ2 — App Insights custom event via `microsoft.custom_event.name`; Log Analytics table `retentionInDays`/`totalRetentionInDays` + `immediatePurgeDataOn30Days`; lock = Phase 2/3 |
| AUD-08 | download→OCR→compare→FIC chain keeps `JOBS_BASE_DIR` artifacts available (no cross-worker loss) | RQ5 — activities scale out to many VMs; current single-activity chain (`_run_activity`) is the correct invariant |
</phase_requirements>

## Summary

This phase is an audit + targeted-fix phase against an existing, never-deployed, security-hardened codebase. The technical domain is well understood and the locked decisions are all implementable with current, documented Microsoft platform behavior. The five genuine unknowns are now resolved with HIGH confidence against Microsoft Learn:

1. **`oid` is the correct stable identifier.** It is the immutable, per-tenant GUID for a user, is the same across all apps for that user in that tenant, and "can't be reused." `sub` is pairwise-per-app and would still be stable but is app-scoped; `oid` is the documented choice for cross-service correlation. The fix is to make `verify_azure_ad_token` return (or additionally expose) the `oid` claim and feed it to `hash_id()` everywhere ownership is computed.
2. **The audit trail is a one-line-of-code emit + an infra retention policy.** A Python app emits an App Insights *customEvent* by logging through a logger wired to `configure_azure_monitor`, with `extra={"microsoft.custom_event.name": "..."}`. Immutability/retention is configured on the Log Analytics workspace **table** (`retentionInDays` / `totalRetentionInDays`, up to 12 years) and the `immediatePurgeDataOn30Days` workspace flag — that is Phase 2/3 infra. There is **no WORM lock** on Log Analytics tables; "immutability" here means long retention + RBAC + workspace resource lock, which is the honest framing for the security-posture doc.
3. **OBO transient classification follows Graph throttling guidance.** Retry on connection/timeout errors and HTTP **429 / 503 / 504**; honor the `Retry-After` header on 429; do NOT retry 4xx auth failures. Return **503** on exhaustion (the current code returns **502** — that is a launch-blocking bug to fix).
4. **Single-worker pin is a multi-knob setting.** App Service runs gunicorn by default; pin gunicorn `--workers 1` via the startup command, set the plan capacity / autoscale max to 1, and document `WEBSITE_*` so no platform default re-introduces a second worker. The Bicep must assert plan `sku.capacity = 1` and the gateway startup command.
5. **Durable activities are stateless and scale out to many VMs.** Microsoft Learn states plainly: "Because activity triggers are stateless, they scale out to many VMs." Local disk is therefore **not** shared across activities. The repo's current design already downloads *inside a single activity* (`_run_activity` / `audit_pipeline.run_audit`) so the whole download→OCR→compare→FIC chain runs in one activity invocation on one VM — this is the correct invariant. The phase's job is to *prove and lock* it with a test, not to change it.

**Primary recommendation:** Treat this as five surgical changes (`oid` ownership, OBO retry, error/trace redaction, audit-trail emit, single-activity invariant test) plus a single-instance Bicep assertion and a security-posture document. Do not refactor pipeline structure or add locks.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Stable user identity (`oid`) extraction | API/Auth (`scripts/auth.py`) | — | JWT validation already lives here; `oid` is a validated claim |
| owner_hash computation & IDOR gate | API/Auth (`scripts/api_server.py`, `feature_flags.hash_id`) | Orchestration (durable input `owner_hash`) | Gateway computes; durable input is the authoritative persisted check |
| OBO token exchange + retry | API/Auth (`scripts/graph_obo.py`) | — | OBO is a gateway concern; downstream Function gets the delegated token via header |
| Error/secret redaction | Cross-cutting (`scripts/safe_logger.py`) | API + Pipeline | Single redaction module used by both gateway responses and telemetry |
| Audit-trail emit (customEvent) | API/Auth (document-access path) + Orchestration (download activity) | Observability (App Insights → Log Analytics) | Emit at the access point; retention/immutability is infra (Phase 2/3) |
| JOBS_BASE_DIR artifact locality | Orchestration (`function_app.py` activity + `audit_pipeline.py`) | — | Activities are stateless/multi-VM; locality only holds within one activity |
| Single-instance pin | Infra (`infra/main.bicep`) | API runtime (gunicorn `--workers 1`) | In-memory state correctness depends on exactly one process |

## Standard Stack

This phase deploys the existing locked stack — no new frameworks. The only *new* dependency consideration is the Azure Monitor OpenTelemetry distro for the audit-trail emit path (AUD-07). The codebase currently emits telemetry by logging a `log_security("INFO", "AppInsights_Telemetry", {...})` line gated on `APPINSIGHTS_INSTRUMENTATIONKEY` (`scripts/api_server.py:84`), which is NOT a real App Insights exporter — it only writes to the Python logger.

### Core (already in repo)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.111.0+ | Gateway HTTP/auth boundary | Existing, locked |
| PyJWT | >=2.8.0 | JWT RS256 validation, JWKS | Existing; CONCERNS flags pinning to 2.9.0+ as deferred |
| httpx | (repo pin) | Graph + Function calls; OBO POST | Existing; injectable `http_post` in `graph_obo` |
| azure-functions-durable | >=1.2.9 | Orchestration | Existing, locked |

### Supporting (audit-trail emit path — AUD-07)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `azure-monitor-opentelemetry` [ASSUMED] | latest | `configure_azure_monitor()` + customEvent emit via logging | The documented, supported way for a Python app to emit App Insights custom events with custom dimensions [CITED: learn.microsoft.com/azure/azure-monitor/app/opentelemetry-add-modify?tabs=python] |

**Decision flag:** Whether to introduce `azure-monitor-opentelemetry` *this phase* or only wire a redaction-safe emit seam (and let Phase 3 add the exporter with OBS-01) is a planning decision. The locked decision says "this phase wires the emit path and field contract." Minimum viable: define the audit-event function + field contract + redaction, behind the existing `APPINSIGHTS_*` gate, so Phase 3 swaps the sink without touching call sites. Verify the package on PyPI before adding it (see Package Legitimacy Audit).

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `azure-monitor-opentelemetry` distro | Raw `opencensus-ext-azure` | opencensus is the older, maintenance-mode path; OTel distro is the current Microsoft-recommended one. Do not introduce opencensus for new code. [CITED: learn.microsoft.com/azure/azure-monitor/app/opentelemetry-add-modify] |
| App Insights customEvent | Direct Logs Ingestion API → custom `_CL` table | More control over the table/immutability, but more infra and code. Overkill for a 4-field access record; customEvent → `AppEvents`/`customEvents` is simpler and solo-operator-friendly. |

**Installation (only if adding the exporter this phase):**
```bash
pip install azure-monitor-opentelemetry   # verify on PyPI first (see audit)
```

**Version verification:** Run `pip index versions azure-monitor-opentelemetry` against PyPI before pinning. Training-data versions are stale.

## Package Legitimacy Audit

> slopcheck was **not available** in this research session (no network install attempted from the sandbox). Per protocol, the one candidate new package is tagged `[ASSUMED]` and the planner MUST gate its install behind a `checkpoint:human-verify` task. All other packages already exist in `requirements.txt` and are unchanged by this phase.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `azure-monitor-opentelemetry` | PyPI | (verify) | (verify) | github.com/Azure/azure-sdk-for-python | not run | `[ASSUMED]` — planner adds checkpoint:human-verify + `pip index versions` before install |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*If the planner chooses the "emit seam only, no new dependency" path, this table is moot — no package is installed this phase.*

## Architecture Patterns

### System Architecture Diagram (request path with this phase's touchpoints)

```
  Teams / Copilot Studio
          │  Bearer JWT (audience = gateway)
          ▼
┌─────────────────────────── FastAPI Gateway (App Service, SINGLE worker) ──────────────────────────┐
│  verify_azure_ad_token  ──►  returns oid (NEW: AUD-02)                                              │
│        │                                                                                            │
│        ▼                                                                                            │
│  hash_id(oid) ─► owner_hash  ─────────────────────────────┐  (NEW: AUD-02/03 use oid not upn)      │
│        │                                                   │                                        │
│  rate-limit (in-mem)   feature gate                        │                                        │
│        │                                                   │                                        │
│  acquire_obo_graph_token  ──► RETRY transient (NEW AUD-05) │                                        │
│        │     │exhausted → 503 (NEW; was 502)               │                                        │
│        ▼     ▼                                             │                                        │
│  emit audit customEvent {oid_hash, doc_id, ts_utc, verdict?}  (NEW AUD-07, redacted AUD-06)         │
│        │                                                   │                                        │
│  POST /audit  {document_id, client_context, owner_hash} ───┘ ──────────► Durable Function           │
└────────────────────────────────────────────────────────────────────────────┬─────────────────────┘
                                                                               ▼
                                              ┌──── Durable Orchestration (activities are MULTI-VM) ──┐
                                              │  http_start: download-as-user (OBO header)            │
                                              │  audit_orchestrator → activity_run_audit (ONE activity)│
                                              │     run_audit():  download → ocr → compare → make_fic  │
                                              │     ▲ all artifacts under JOBS_BASE_DIR in ONE activity │
                                              │       = same VM = locality holds (INVARIANT AUD-08)    │
                                              │  _assert_durable_owner(owner_hash) = authoritative IDOR │
                                              └────────────────────────────────────────────────────────┘
```

### Pattern 1: Authoritative IDOR gate on persisted `owner_hash` (AUD-03)
**What:** The durable orchestration input carries `owner_hash = SHA256(oid)`. On status reads, the gateway compares `hash_id(oid_of_caller)` to the persisted `owner_hash` and hard-fails on mismatch. The in-memory `_audit_job_owners` map is only a fast-path.
**When to use:** Every `/api/audit/{job_id}/status` read.
**Current gap:** `_assert_durable_owner` (`scripts/api_server.py:225-242`) already hard-fails on mismatch — but only when `owner_hash` is *present*. Since this is a clean cutover, `owner_hash` will always be present, so no legacy-tolerance path is needed; consider making absence an error in prod. `hash_id` is currently fed `user_upn` (`api_server.py:238,308,365`) — change to feed `oid`.

### Pattern 2: Bounded exponential backoff with jitter, transient-only (AUD-05)
**What:** Wrap the OBO POST in a retry loop. Classify transient = `httpx.TimeoutException`, `httpx.ConnectError`/`ConnectTimeout`, and HTTP status in {429, 503, 504}. On 429 honor `Retry-After`. 3 attempts, base ~0.5s, full jitter. On exhaustion raise → 503.
**When to use:** `scripts/graph_obo.acquire_obo_graph_token` (and its three call sites in `api_server.py`).
**Anti-pattern fixed:** Current `api_server.py:336` returns **502** on OBO failure; the locked decision and CONCERNS bug require **503**.

### Pattern 3: Single-activity artifact locality (AUD-08)
**What:** The entire pipeline runs inside one activity (`activity_run_audit` → `_run_activity` → `run_audit`). `download()` writes to `JOBS_BASE_DIR/{document_id}/` and the same in-process call chain reads it for OCR/compare/FIC. No artifact crosses an activity boundary, so the stateless multi-VM nature of activities never bites.
**When to use:** Preserve as-is. The invariant to document and test: *no second activity may consume a file path produced by a prior activity.*

### Anti-Patterns to Avoid
- **Splitting the pipeline into fan-out activities that pass file paths.** This would break AUD-08 the moment the Functions app scales to >1 VM, because the second activity may land on a different VM with an empty `JOBS_BASE_DIR`. If large-data passing is ever needed, pass via Blob Storage, not local disk. [CITED: learn.microsoft.com/azure/durable-task/durable-functions/durable-functions-perf-and-scale]
- **Using `upn`/`preferred_username` for ownership or storage keys.** Both are mutable and reusable → the exact IDOR bug. [CITED: learn.microsoft.com/entra/identity-platform/id-token-claims-reference]
- **Treating registry existence as proof of legitimacy** for the new telemetry package — verify against PyPI + repo.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| App Insights custom-event emit | A bespoke HTTP POST to the ingestion endpoint | `configure_azure_monitor` + `logger.info(..., extra={"microsoft.custom_event.name": ...})` | Documented, handles batching/auth/schema; emits to `customEvents` table |
| OBO token exchange | New OAuth client | Keep existing `graph_obo.acquire_obo_graph_token`; only add a retry wrapper | The exchange itself is correct; only retry/error-code is wrong |
| Retry/backoff | A hand-tuned sleep loop with no jitter | A small, tested backoff helper honoring `Retry-After` (stdlib `random` for jitter is fine; no new dep needed) | Jitter prevents thundering-herd; Retry-After is mandated by Graph |
| Secret/PII redaction | New masking regexes per call site | Extend the single `safe_logger.redact()` and route all detail strings + telemetry `extra` through it | One audited redaction surface; already tested by `test_safe_logger_redaction.py` |
| Log immutability | A custom append-only store | Log Analytics table retention + workspace resource lock + RBAC | Native, solo-operator-friendly; documented limits |

**Key insight:** Every locked decision maps to *modifying an existing, tested seam* — not building new infrastructure. The risk is regressions, not missing capability.

## Runtime State Inventory

> This phase is code+IaC only (clean cutover, never deployed). There is **no live runtime state to migrate.**

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — app never deployed; no existing `owner_hash` values, no durable instances, no jobs on disk. Clean cutover per locked decision. | None |
| Live service config | None — no prod App Insights / Log Analytics workspace exists yet (provisioned Phase 2/3). | None this phase (emit path coded; sink wired Phase 3) |
| OS-registered state | None — no deployed App Service / Functions yet. | None |
| Secrets/env vars | `owner_hash` derivation changes input from `upn` → `oid` (code change only; no stored secret). `AC360_REQUIRE_OBO`, `OBO_CLIENT_SECRET`, `APPINSIGHTS_INSTRUMENTATIONKEY`/connection string are read by code; names unchanged this phase. | Code edit only |
| Build artifacts | None — pure source edits; no compiled packages renamed. If `azure-monitor-opentelemetry` is added, `requirements.txt` (root + `azure_functions/`) must be updated. | Update requirements if exporter added |

## Common Pitfalls

### Pitfall 1: `oid` absent or wrong shape for guest/B2B and app-only tokens
**What goes wrong:** Code assumes `oid` is always present and tenant-stable. For a **guest (B2B)** user authenticating in your tenant, `oid` is still present and is the per-tenant object id (Learn: a user in multiple tenants has a *different* object id per tenant). For an **app-only (client-credentials)** token there is no user, so `oid` represents the service principal, not a person — ownership semantics differ.
**Why it happens:** AC360 is delegated-user only (SSO + OBO), so app-only tokens should not reach `/api/audit`; but defensive handling matters.
**How to avoid:** In `verify_azure_ad_token`, require `oid`; if missing, 401 (same pattern as the current UPN check at `auth.py:138-141`). Treat guests as first-class users (their `oid` is their identity in this tenant — exactly what we want). Document that app-only tokens are out of scope. [CITED: learn.microsoft.com/entra/identity-platform/id-token-claims-reference]

### Pitfall 2: A second gateway worker silently re-introduced
**What goes wrong:** In-memory rate-limit (`_rate_limit_store`) and JWKS cache (`_JWKS_CACHE`) become inconsistent if gunicorn spawns >1 worker or the plan scales to >1 instance. App Service's default Python container runs gunicorn — and example startup commands show multi-worker (`--workers=4`) as common. If a startup command isn't pinned, a future change could add workers.
**Why it happens:** Default/derived worker counts; autoscale rules; `NUM_CORES`-based worker math in sample startup commands.
**How to avoid:** (1) plan `sku.capacity = 1` and any autoscale `maximum = 1`; (2) gateway startup command pins `gunicorn --workers 1 -k uvicorn.workers.UvicornWorker api_server:app` (App Service `--startup-file`); (3) Bicep comment documents this as load-bearing for in-memory state. [CITED: learn.microsoft.com/azure/app-service/configure-language-python]

### Pitfall 3: "Immutable log" oversold in the security-posture doc
**What goes wrong:** Claiming Log Analytics tables are WORM/immutable. They are **not** — there is no table-level immutability lock. You get long retention (up to 12 years via `totalRetentionInDays`), `immediatePurgeDataOn30Days` for the *opposite* (forced deletion), RBAC, and resource locks on the workspace.
**Why it happens:** Conflating Storage immutable blob policies with Log Analytics.
**How to avoid:** In the posture doc, describe the control honestly: "append-only via the ingestion pipeline (no in-place edit API), long retention, RBAC-restricted, workspace resource lock." If true WORM is later required, that's a Logs-Ingestion→immutable-Storage design (out of scope). [CITED: learn.microsoft.com/azure/azure-monitor/logs/data-retention-configure] `[ASSUMED]` that resource-lock + RBAC is acceptable evidence for the internal compliance bar — confirm with DPO in Phase 5.

### Pitfall 4: OBO `acquire_token` retried on non-transient failures
**What goes wrong:** Retrying a 400/401/403 (bad assertion, consent missing, insufficient scope) wastes time and masks a real config error as a 503.
**Why it happens:** Coarse `except Exception` (current `api_server.py:334`) catches everything.
**How to avoid:** Classify: retry only `httpx` connection/timeout errors and HTTP {429, 503, 504}; let 4xx propagate as a distinct, non-retried failure (still redacted). The OBO scope list itself is an open verification item (below).

### Pitfall 5: Redaction applied to logs but not to the HTTP response body
**What goes wrong:** `HTTPException(detail=...)` strings and App Insights `extra` dimensions can carry exception text with secrets/PII (CONCERNS "Secrets in Error Messages"). `redact()` is currently applied to `log_security()` messages but not uniformly to `detail` strings or telemetry custom dimensions.
**How to avoid:** Route every dynamic `detail` through `redact()` and return a generic message + correlation id; pass telemetry dimensions through `redact()` before emit. The audit-event itself carries only the 4 contracted fields (hash, doc id, ts, verdict) — no free-form text.

## Code Examples

### Extract `oid` from the validated JWT (AUD-02) — `scripts/auth.py`
```python
# After jwt.decode(...) succeeds and issuer/scope/role checks pass:
# Source pattern adapted from existing auth.py:138-144 (which returns upn).
oid = claims.get("oid")
if not oid:
    log_security("ERROR", "No oid (object id) in claims")
    raise HTTPException(status_code=401, detail="Le token ne contient pas d'identité stable.")
# Keep upn for human-readable logging ONLY (never for ownership/storage keys):
upn = claims.get("upn") or claims.get("preferred_username")
log_security("INFO", f"Token validated (oid present) user={upn}")
return oid   # or return a small object exposing both; callers must hash oid
# Claim semantics: oid is the immutable, non-reusable per-tenant user GUID.
# Source: https://learn.microsoft.com/entra/identity-platform/id-token-claims-reference
```
> Planner note: callers currently bind `user_upn = Depends(verify_azure_ad_token)`. The cleanest change is to return `oid` and rename the dependency variable, feeding `hash_id(oid)` at `api_server.py:238,308,365`. Keep a separate non-authoritative UPN for log lines if desired (but UPN is PII — prefer not to log it).

### App Insights custom event with custom dimensions (AUD-07) — Python
```python
import logging
from azure.monitor.opentelemetry import configure_azure_monitor

audit_logger = logging.getLogger("ac360-audit")
configure_azure_monitor(logger_name="ac360-audit")  # connection string from env

# The audit trail record — exactly the 4 contracted fields, no raw PII:
audit_logger.info(
    "document_access",
    extra={
        "microsoft.custom_event.name": "ac360_document_access",
        "user_id_hash": hash_id(oid),      # SHA-256 of oid, no salt
        "document_id": document_id,
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict or "",          # filled on completion path
    },
)
# Source: https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-add-modify?tabs=python
```
> Lands as a small helper (e.g. `scripts/audit_trail.py`) called from the document-access path in `api_server.py` and/or the download activity in `function_app.py`. Behind the existing `APPINSIGHTS_*` gate so it's inert until Phase 3 wires the real workspace.

### Bounded backoff with jitter, transient-only, Retry-After aware (AUD-05)
```python
import random, time, httpx

_TRANSIENT_STATUS = {429, 503, 504}

def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    resp = getattr(exc, "response", None)
    return getattr(resp, "status_code", None) in _TRANSIENT_STATUS

def acquire_obo_graph_token_retrying(user_assertion, *, attempts=3, base=0.5, **kw):
    last = None
    for i in range(attempts):
        try:
            return acquire_obo_graph_token(user_assertion, **kw)
        except Exception as exc:                      # narrow in the OBO hot path
            if not _is_transient(exc) or i == attempts - 1:
                raise
            last = exc
            # Honor Graph Retry-After on 429, else full-jitter exponential backoff.
            resp = getattr(exc, "response", None)
            retry_after = None
            if getattr(resp, "status_code", None) == 429:
                try: retry_after = float((resp.headers or {}).get("Retry-After"))
                except (TypeError, ValueError): retry_after = None
            delay = retry_after if retry_after is not None else random.uniform(0, base * (2 ** i))
            time.sleep(delay)
    raise last
# Caller maps exhaustion to HTTP 503 (NOT 502): see api_server.py:336.
# Source (transient set / Retry-After): https://learn.microsoft.com/graph/throttling
```
> The OBO call is currently run via `run_in_threadpool(acquire_obo_graph_token, raw_auth)` — keep that, wrapping the retrying variant. `time.sleep` is fine inside the threadpool; do not block the event loop.

### Single-activity locality assertion test (AUD-08)
```python
# tests/azure_functions/test_jobs_dir_locality.py  (new)
# Asserts the whole chain shares ONE JOBS_BASE_DIR path within a single activity,
# i.e. no stage consumes a path produced by a *different* activity.
from audit_pipeline import AuditDeps, run_audit

def test_chain_shares_artifact_path(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBS_BASE_DIR", str(tmp_path))
    seen = {}
    def fake_download(doc_id):
        p = tmp_path / doc_id / "doc.pdf"; p.parent.mkdir(parents=True); p.write_bytes(b"x")
        seen["download"] = str(p.parent); return str(p)
    def fake_ocr(path):
        seen["ocr"] = str(__import__("os").path.dirname(path))   # same dir as download
        return {"fields": {}}                                    # minimal OCR shape
    deps = AuditDeps(download=fake_download, ocr=fake_ocr,
                     fetch_reference=lambda _id: None, make_fic=None)
    run_audit("job-uuid", None, deps)
    assert seen["download"] == seen["ocr"]   # locality holds within the activity
```
> Pair with a structural test asserting `function_app._audit_orchestration` calls **exactly one** activity (`activity_run_audit`) — guarding against a future fan-out that would break AUD-08.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `opencensus-ext-azure` for App Insights in Python | `azure-monitor-opentelemetry` distro (`configure_azure_monitor`) | OTel GA for Azure Monitor | Use OTel distro for any new telemetry code; don't add opencensus |
| Identify users by UPN/email | Use `oid` (or `sub`) GUID; UPN is display-only | Long-standing Entra guidance | UPN reuse → IDOR; `oid` closes it |
| Multi-worker gateway with shared external cache | Single-instance pin for small teams (this milestone) | Project decision | In-memory state is correct only at exactly one worker |

**Deprecated/outdated:**
- The repo's `AppInsightsMiddleware` "telemetry" (`api_server.py:84-90`) is a logger line gated on the legacy `APPINSIGHTS_INSTRUMENTATIONKEY` env var — it does not export to App Insights. Modern wiring uses the **connection string** + `configure_azure_monitor`. Real exporter wiring is Phase 3 (OBS-01); this phase only needs a redaction-safe emit seam + field contract.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `azure-monitor-opentelemetry` is the package name/version to add (if added this phase) | Standard Stack / Audit | Wrong package = broken telemetry; mitigated by checkpoint:human-verify + `pip index versions` |
| A2 | Log Analytics resource-lock + RBAC + long retention is an acceptable "immutability" evidence bar for the internal compliance review | Pitfall 3 | If DPO requires true WORM, needs Logs-Ingestion→immutable-Storage redesign (out of scope) — surface in Phase 5 |
| A3 | App-only (client-credentials) tokens never reach `/api/audit` in production (delegated-only) | Pitfall 1 | If they can, `oid` would be a service principal id — ownership semantics break; add a guard |
| A4 | Honoring `Retry-After` only on 429 (not 503) is sufficient | Code Examples / RQ3 | 503/504 without Retry-After fall back to jitter backoff — acceptable per Graph guidance |

## Open Questions

1. **Exact OBO delegated Graph scope list** (carried from STATE.md blocker + CONTEXT specifics)
   - What we know: OBO exchanges to a delegated Graph token; current default scope is `https://graph.microsoft.com/.default` (`graph_obo.py:14`). Endpoints need at least SharePoint file read (`Files.Read.All`/`Sites.Selected` per `function_app._download` docstring) and Planner `Tasks.ReadWrite`.
   - What's unclear: the precise consented delegated scope set on the **staging** app registration (and whether `.default` resolves them).
   - Recommendation: Verify against the live staging app registration **before** OBO retry tests assert success paths. Plan a `checkpoint:human-verify` task. This does not block writing the retry logic (transient classification is scope-independent).

2. **Emit-now vs emit-seam for AUD-07**
   - What we know: locked decision says "wire the emit path and field contract" this phase; real workspace is Phase 2/3.
   - What's unclear: whether to add `azure-monitor-opentelemetry` now or define the seam and add the exporter in Phase 3.
   - Recommendation: Implement the audit-event helper + 4-field contract + redaction now, gated on the App Insights env var; let Phase 3 (OBS-01) attach `configure_azure_monitor`. Avoids a new dependency landing in an audit-only phase.

3. **Should absent `owner_hash` be a hard 403 in prod?**
   - What we know: clean cutover means every job will have `owner_hash`; `_assert_durable_owner` currently tolerates absence (legacy path).
   - Recommendation: Given no legacy jobs exist, tighten to fail-closed when `owner_hash` is absent on a completed job — but confirm it doesn't break the in-flight/queued status shape. Low risk; planner's call.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All code/tests | ✓ (repo targets 3.12) | 3.12 | — |
| pytest / pytest-asyncio | New tests (AUD-05/08) | ✓ (in repo) | 8.x / 0.23.x | — |
| Live Entra staging app registration | OBO scope verification (Open Q1) | ✗ (not confirmed) | — | Write retry logic now; gate success-path assertion behind verification |
| Log Analytics workspace w/ retention policy | AUD-07 immutability | ✗ (Phase 2/3) | — | Emit-seam coded behind env gate; sink wired later |
| `azure-monitor-opentelemetry` | AUD-07 exporter (if added now) | ✗ (not installed) | — | Emit-seam without exporter; add in Phase 3 |

**Missing dependencies with no fallback:** none block this phase (audit + code edits + tests are self-contained).
**Missing dependencies with fallback:** OBO scope verification (write-now/verify-before-trust); audit exporter (seam now, sink Phase 3).

## Validation Architecture

> nyquist_validation: config not inspected as explicitly `false`; treated as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio (`asyncio_mode = auto`) |
| Config file | `setup.cfg` (`[tool:pytest]`, `testpaths = tests`) |
| Quick run command | `pytest tests/backend/test_graph_obo.py tests/backend/test_audit_ownership.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUD-02 | `verify_azure_ad_token` returns/uses `oid`; missing oid → 401 | unit | `pytest tests/backend/test_auth_jwt.py -x` | ✅ extend (`test_auth_jwt.py`, `test_wave1_auth_identity.py`) |
| AUD-03 | durable owner_hash mismatch → 403; map is cache only | unit | `pytest tests/backend/test_audit_ownership.py tests/backend/test_job_isolation.py -x` | ✅ extend |
| AUD-05 | transient OBO errors retried (429/503/504/timeout); 4xx not; exhaustion → 503 | unit | `pytest tests/backend/test_graph_obo.py -x` | ✅ extend |
| AUD-06 | HTTPException detail + telemetry dims redacted | unit | `pytest tests/backend/test_safe_logger_redaction.py tests/backend/test_security_headers.py -x` | ✅ extend |
| AUD-07 | audit event carries exactly {hash, doc_id, ts_utc, verdict}, no PII | unit | `pytest tests/backend/test_audit_trail.py -x` | ❌ Wave 0 (new `test_audit_trail.py`) |
| AUD-08 | chain shares one JOBS_BASE_DIR within a single activity; orchestrator calls one activity | unit | `pytest tests/azure_functions/test_jobs_dir_locality.py -x` | ❌ Wave 0 (new file) |
| AUD-01 | re-validation: existing IDOR/rate-limit/path-traversal tests still green under single-worker assumptions | regression | `pytest tests/backend tests/security tests/azure_functions` | ✅ existing |

### Sampling Rate
- **Per task commit:** the quick command for the touched requirement.
- **Per wave merge:** `pytest tests/backend tests/azure_functions tests/security`.
- **Phase gate:** full `pytest` green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/azure_functions/test_jobs_dir_locality.py` — covers AUD-08 (locality + single-activity structural assertion)
- [ ] `tests/backend/test_audit_trail.py` — covers AUD-07 (4-field contract + no-PII redaction)
- [ ] No framework install needed — pytest/asyncio already configured in `setup.cfg`.

## Security Domain

> security_enforcement treated as enabled (not `false` in config).

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Entra ID JWT RS256 + JWKS (`auth.py`); add `oid` requirement |
| V3 Session Management | partial | Stateless bearer tokens; no server session |
| V4 Access Control (IDOR) | **yes** | Authoritative `owner_hash`(`oid`) durable check (AUD-02/03); OBO delegated SharePoint RBAC |
| V5 Input Validation | yes | Existing `document_id` UUID/allowlist guards (`api_server.py:32-39,155-178`); OData quote-escape in resolve |
| V6 Cryptography | yes | SHA-256 for hashing (non-secret, deterministic) — appropriate; no hand-rolled crypto |
| V7 Errors & Logging | **yes** | `safe_logger.redact()` extended to HTTPException detail + telemetry (AUD-06); immutable access trail (AUD-07) |
| V9 Communications | yes | `httpsOnly`, TLS1.2 in `main.bicep`; HSTS header in middleware |

### Known Threat Patterns for FastAPI + Durable Functions + Entra OBO
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR on audit jobs via reusable UPN | Elevation / Info disclosure | `owner_hash = SHA256(oid)`; durable check authoritative (AUD-02/03) |
| Secret/PII leak in error body or telemetry | Information disclosure | Uniform `redact()` on detail + dimensions; generic message + correlation id (AUD-06) |
| Cross-VM artifact loss → failed/incorrect audit | Tampering / DoS | Single-activity locality invariant + test (AUD-08) |
| OBO transient flake mis-surfaced as failure | DoS / availability | Bounded backoff, transient-only, Retry-After; 503 on exhaustion (AUD-05) |
| In-memory state inconsistency under >1 worker | Tampering (rate-limit bypass) | Single-instance pin in IaC + gunicorn `--workers 1` (AUD-04) |
| Path traversal via document id / filename | Tampering | Existing UUID + `commonpath` + `_safe_filename` (re-validated under AUD-01; symlink hardening deferred) |

## Sources

### Primary (HIGH confidence)
- [CITED] learn.microsoft.com/entra/identity-platform/id-token-claims-reference — `oid` vs `sub` semantics; immutability; per-tenant guest behavior; "use claims to reliably identify a user" (updated 2025-10).
- [CITED] learn.microsoft.com/azure/app-service/configure-language-python — gunicorn default container, `--workers` startup command, `--startup-file` (updated 2026-02).
- [CITED] learn.microsoft.com/azure/azure-monitor/logs/data-retention-configure — table `retentionInDays`/`totalRetentionInDays` (4–730 / up to 4383 days), `immediatePurgeDataOn30Days`, Bicep `workspaces/tables` (updated 2026-06).
- [CITED] learn.microsoft.com/azure/azure-monitor/app/opentelemetry-add-modify?tabs=python — Python customEvent via `microsoft.custom_event.name` in logging `extra`; `configure_azure_monitor` (updated 2026-05).
- [CITED] learn.microsoft.com/graph/throttling — 429 + Retry-After handling; exponential backoff when no Retry-After (updated 2025-08).
- [CITED] learn.microsoft.com/azure/durable-task/durable-functions/durable-functions-perf-and-scale — "activity triggers are stateless, they scale out to many VMs"; Python single-function-per-VM concurrency; fan-in is single-VM (updated 2026-06).

### Secondary (MEDIUM confidence)
- Repo source (authoritative for landing sites): `scripts/auth.py`, `scripts/api_server.py`, `scripts/graph_obo.py`, `scripts/feature_flags.py`, `scripts/safe_logger.py`, `azure_functions/function_app.py`, `azure_functions/shared/audit_pipeline.py`, `azure_functions/shared/sharepoint.py`, `infra/main.bicep`, `setup.cfg`.

### Tertiary (LOW confidence)
- `azure-monitor-opentelemetry` exact version — needs PyPI verification (Assumption A1).

## Metadata

**Confidence breakdown:**
- Identity (`oid`): HIGH — official claims reference, explicit on immutability/reuse and guest behavior.
- App Service single-worker pin: HIGH — official Python-on-App-Service doc; multi-knob (plan capacity + startup command) is the honest answer.
- Audit trail emit + retention: HIGH on the API/Bicep; MEDIUM on "immutability" framing (no true WORM — flagged A2).
- OBO retry classification: HIGH — Graph throttling guidance is explicit.
- JOBS_BASE_DIR / activity locality: HIGH — perf-and-scale doc directly states activities are stateless/multi-VM; current single-activity design is correct.
- New package legitimacy: LOW until PyPI-verified (gated by checkpoint).

**Research date:** 2026-06-13
**Valid until:** 2026-07-13 (stable platform docs; re-confirm App Service startup-command and Log Analytics retention API version at execution)
</content>
</invoke>
