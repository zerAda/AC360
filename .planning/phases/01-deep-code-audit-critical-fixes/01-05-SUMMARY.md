---
phase: 01-deep-code-audit-critical-fixes
plan: 05
subsystem: infrastructure
tags: [iac, bicep, single-instance, in-memory-state, security]
requires: []
provides:
  - "gwPlan single-instance pin (F1 tier-fixed; explicit capacity=1 deferred to Phase 2 INF-02/B1)"
  - "gatewayApp gunicorn --workers 1 appCommandLine (load-bearing)"
  - "load-bearing comment tying the pin to _rate_limit_store / _JWKS_CACHE / _audit_job_owners"
affects:
  - infra/main.bicep
tech-stack:
  added: []
  patterns:
    - "Single-instance / single-worker pin as the in-memory-state-consistency mitigation (no Redis scale-out)"
key-files:
  created: []
  modified:
    - infra/main.bicep
decisions:
  - "F1/Free tier rejects an explicit sku.capacity; instance=1 is guaranteed by the tier. The explicit capacity=1 pin is deferred to Phase 2 (INF-02, B1). The load-bearing pin here is the gunicorn --workers 1 startup command + the documentation comment."
  - "No autoscaleSettings resource targets the gateway plan; per the plan, none was added — instead a prohibition comment forbids any autoscale rule raising capacity above 1."
metrics:
  duration: 6
  completed: "2026-06-13"
  tasks: 1
  files: 1
---

# Phase 01 Plan 05: Single-Instance Gateway Pin Summary

Pinned the FastAPI gateway to one worker via a load-bearing `gunicorn --workers 1` startup command and documented the single-instance invariant (AUD-04) as required for the gateway's per-process in-memory state.

## What Was Built

Task 1 modified `infra/main.bicep` (gateway plan + gateway app only):

- **gatewayApp.siteConfig.appCommandLine** — added `gunicorn --workers 1 -k uvicorn.workers.UvicornWorker api_server:app`, preventing any platform default from re-introducing a second worker (Pitfall 2). This is the load-bearing pin on the F1 tier.
- **Load-bearing comment block on gwPlan** — names the three in-memory structures and why >1 process breaks each:
  - `_rate_limit_store` (api_server.py:105) — rate-limit bypass if requests split across workers
  - `_JWKS_CACHE` (auth.py:28) — cache divergence during key rotation
  - `_audit_job_owners` (api_server.py:205) — IDOR fast-path divergence (durable owner_hash check from Plan 01-06 remains authoritative)
- **F1 capacity note** — Free tier is fixed at one instance and rejects an explicit `sku.capacity`; the explicit `capacity: 1` pin is deferred to Phase 2 (INF-02, B1). Documented inline.
- **Autoscale prohibition** — no `autoscaleSettings` resource targets the gateway plan; a comment forbids adding any rule that would raise capacity above 1 (instead of adding a no-op autoscale resource).

## Verification

- **Automated:** `az bicep build --file infra/main.bicep --stdout` → `BICEP_OK`. The Bicep CLI was available in this environment; the file compiles.
- **Manual (AUD-04 per 01-VALIDATION.md):** confirmed gateway startup command contains `--workers 1`, the load-bearing comment names all three structures, and no autoscale rule permits capacity > 1. The explicit `sku.capacity == 1` assertion is satisfied via the documented Phase-2 B1 deferral (F1 cannot carry an explicit capacity).

## Deviations from Plan

None — plan executed as written. The plan's F1/Free contingency (pin `--workers 1` + comment now; defer explicit `capacity=1` to Phase 2 B1) was the path taken, exactly as the plan's `<action>` and `<note>` anticipated.

## Threat Model Coverage

| Threat ID | Disposition | Status |
|-----------|-------------|--------|
| T-01-05-01 (rate-limit bypass) | mitigate | Mitigated — `--workers 1` keeps `_rate_limit_store` single-source |
| T-01-05-02 (JWKS divergence) | mitigate | Mitigated — single process = one JWKS cache |
| T-01-05-03 (IDOR fast-path) | mitigate | Mitigated — single process keeps `_audit_job_owners` coherent; durable check still authoritative |
| T-01-SC (package installs) | mitigate | N/A — IaC edit only, no package install |

No new security surface introduced (no new endpoints, auth paths, or schema changes).

## Self-Check: PASSED

- FOUND: infra/main.bicep (modified, contains `gunicorn --workers 1` + load-bearing comment)
- FOUND: commit 1582c86 (`git show --stat` confirms infra/main.bicep, 30 insertions)
