---
phase: 03-backend-deploy-observability
plan: 01
subsystem: observability
tags: [telemetry, opentelemetry, azure-monitor, redaction, readiness]
requires: []
provides:
  - "scripts/telemetry.py: RedactingSpanProcessor + gated setup_telemetry (OBS-01)"
  - "tests/backend/test_telemetry_redaction.py: span-attribute redaction spec"
  - "tests/backend/test_ready_endpoint.py: /ready 401/200/503/no-leak contract (RED, xfail until Plan 02)"
  - "azure-monitor-opentelemetry pin in both requirements files"
affects:
  - "scripts/api_server.py (Plan 02 will call setup_telemetry() and implement /ready)"
tech-stack:
  added:
    - "azure-monitor-opentelemetry>=1.8.8,<2.0.0 (lazy-imported, gated)"
  patterns:
    - "Lazy SDK import (function_app.py:26-33 idiom) for import-safety"
    - "Two-var AppInsights env gate (audit_trail.py:47) for inert-by-default posture"
    - "Single audited redaction surface reuse (safe_logger.redact) — no new regex (AUD-06)"
key-files:
  created:
    - scripts/telemetry.py
    - tests/backend/test_telemetry_redaction.py
    - tests/backend/test_ready_endpoint.py
  modified:
    - requirements.txt
    - azure_functions/requirements.txt
decisions:
  - "RedactingSpanProcessor is duck-typed (no opentelemetry.* import at module top) for import-safety; distro accepts any object with on_start/on_end/shutdown/force_flush"
  - "/ready contract encoded as xfail(strict=False) scaffold; endpoint lands in Plan 02"
metrics:
  duration: ~12m
  completed: 2026-06-14
  tasks: 3
  files: 5
---

# Phase 3 Plan 01: Observability Foundation Summary

Redaction-preserving OpenTelemetry span processor plus a gated, import-safe `setup_telemetry()` (`scripts/telemetry.py`), the offline span-redaction unit test, the `/ready` contract RED scaffold, and the `azure-monitor-opentelemetry` dependency pin in both requirements files — landing the real Azure Monitor exporter that Phase 1 deferred to OBS-01, behind the same AppInsights gate.

## What Was Built

- **`scripts/telemetry.py`** (OBS-01):
  - `RedactingSpanProcessor` — duck-typed span processor whose `on_end` routes the span name and every `str` attribute through `safe_logger.redact` (the single audited redaction surface, AUD-06; no new regex). Non-`str` attributes pass through intact. The entire scrub body is wrapped in `try/except Exception: pass` so telemetry scrubbing can never raise into the request path (T-03-02).
  - `setup_telemetry()` — early-returns `None` when the two-var AppInsights gate is closed (inert in dev/test/import, T-03-03). When open, lazily imports `configure_azure_monitor` and wires it with `logger_name="AC360"` and `span_processors=[RedactingSpanProcessor()]` so redaction runs in the export path.
  - No `azure.*` / `opentelemetry.*` import at module level — pytest collection never requires the SDK.
- **`tests/backend/test_telemetry_redaction.py`** (OBS-01, AUD-06): three tests proving email/IBAN/JWT/secret span attributes are masked, non-`str` passthrough is preserved, the span name is scrubbed, and `on_end` never raises.
- **`tests/backend/test_ready_endpoint.py`** (OBS-03): RED scaffold encoding the locked `/ready` contract (401 unauth, 200 ready, 503 degraded, no-detail-leak) via `api_server.app.dependency_overrides`. Marked `xfail(strict=False)` until Plan 02 implements the route.
- **Requirements pins**: `azure-monitor-opentelemetry>=1.8.8,<2.0.0` appended (existing pins untouched) to `requirements.txt` and `azure_functions/requirements.txt` under an `# Observability (OBS-01)` comment.

## Verification

- `python -m pytest tests/backend/test_telemetry_redaction.py tests/backend/test_ready_endpoint.py` → 3 passed, 3 xfailed, 1 xpassed (exit 0).
- `python -c "import sys; sys.path.insert(0,'scripts'); import telemetry"` → exit 0 with the SDK uninstalled (import-safe / lazy import proven).
- `setup_telemetry()` returns `None` when the AppInsights gate is closed.
- No new redaction regex: no standalone `import re` / `re.compile` in `telemetry.py` (AUD-06).
- Both requirements files contain the pinned `azure-monitor-opentelemetry>=1.8.8,<2.0.0`.

## Decisions Made

- **Duck-typed processor over SpanProcessor subclass**: keeps `telemetry.py` import-safe (no `opentelemetry.*` at module top) while remaining fully testable without the SDK. The Azure Monitor distro accepts any object exposing `on_start`/`on_end`/`shutdown`/`force_flush`.
- **`/ready` as xfail scaffold**: the route does not exist until Plan 02 (FastAPI returns 404/401 today). `strict=False` keeps this plan's suite green while locking the contract; the `test_ready_unauthenticated_returns_401` case currently xpasses because the Entra auth dependency runs before route resolution.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The `/ready` scaffold is an intentional Wave-0 RED spec (documented in its docstring) whose endpoint is implemented in Plan 02; this is the planned Phase-1 Wave-0 pattern, not an unwired stub.

## Self-Check: PASSED

- FOUND: scripts/telemetry.py
- FOUND: tests/backend/test_telemetry_redaction.py
- FOUND: tests/backend/test_ready_endpoint.py
- FOUND commit 4e74c27 (feat telemetry module)
- FOUND commit 3b872ca (test telemetry redaction)
- FOUND commit 6f7c1df (test /ready scaffold + requirements pins)
