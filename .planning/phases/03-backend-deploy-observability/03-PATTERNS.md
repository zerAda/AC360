# Phase 3: Backend Deploy & Observability - Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 16 (8 CREATE, 8 MODIFY)
**Analogs found:** 15 / 16 (1 net-new with no direct analog: workbook JSON)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.github/workflows/cd-prod.yml` (NEW) | config (CI/CD) | event-driven | `.github/workflows/cd-staging.yml` + `ci.yml` | role-match (staging is single-job, no OIDC/gate; ci.yml has multi-job graph) |
| `infra/observability.bicep` (NEW) | config (IaC) | declarative/control-plane | `infra/main.bicep` (resource + role-assignment + `for`-loop + gated-resource patterns) | role-match (no `Microsoft.Insights/*` exists yet) |
| `infra/budget.bicep` (NEW) | config (IaC) | declarative/control-plane | `infra/main.bicep` (param + resource shape) | role-match (subscription targetScope is net-new) |
| `scripts/telemetry.py` (NEW) | utility (telemetry) | transform/event-driven | `scripts/audit_trail.py` (gate + `redact_mapping` reuse) + `scripts/safe_logger.py` | exact (same gate, same redaction surface) |
| `tests/backend/test_ready_endpoint.py` (NEW) | test | request-response | `tests/backend/test_security_headers.py` (TestClient + monkeypatch + Depends) | exact |
| `tests/backend/test_telemetry_redaction.py` (NEW) | test | transform | `tests/backend/test_safe_logger_redaction.py` (fake PII fixtures + redact assertions) | exact |
| `docs/production/runbooks/01-deploy.md` … `05-killswitch.md` (NEW x5) | docs (runbook) | n/a | `docs/production/EMERGENCY_SHUTDOWN_RUNBOOK.md` | exact (same audience, az-CLI/pwsh decision-tree style) |
| `scripts/api_server.py` (MODIFY) | controller (gateway) | request-response | self — `/health` (ln 672), `AppInsightsMiddleware` gate (ln 90-116), `verify_azure_ad_token` deps | exact |
| `azure_functions/function_app.py` (MODIFY) | controller (worker) | event-driven | self — guarded-import header (ln 14-33) | exact |
| `azure_functions/host.json` (MODIFY) | config | n/a | self (ln 1-16) | exact |
| `requirements.txt` + `azure_functions/requirements.txt` (MODIFY) | config | n/a | self | exact |
| `infra/observability.bicep` workbook tile JSON (NEW) | config (data) | n/a | — | **no analog** (see § No Analog Found) |

## Pattern Assignments

### `.github/workflows/cd-prod.yml` (config, event-driven)

**Analog:** `.github/workflows/cd-staging.yml` (trigger + package + artifact + step-summary) and `ci.yml` (multi-job `needs:` graph). cd-staging is a *single* job with no OIDC, no what-if, no approval — extend, do not copy verbatim.

**Trigger + version input** — copy the `workflow_dispatch.inputs` shape from cd-staging.yml:8-14; ADD the tag trigger (RESEARCH ln 190-191: `push: tags: ['prod-*']`) and the `permissions: id-token: write` block (RESEARCH ln 198-200) which cd-staging.yml does NOT have.

**Multi-job `needs:` graph** — copy from ci.yml. Job dependency chaining (ci.yml:88-91, 113-116):
```yaml
  whatif:
    runs-on: ubuntu-latest
    needs: build          # ci.yml pattern: needs: <previous-job>
```
The build→whatif→deploy graph mirrors ci.yml's security-scan→validate-yaml→test chain.

**Secrets reference convention** — cd-staging.yml:51-54 and ci.yml:67-70 read `${{ secrets.TENANT_ID }}` / `${{ secrets.CLIENT_ID }}`. The three OIDC secrets (`AZURE_CLIENT_ID/TENANT_ID/SUBSCRIPTION_ID`, RESEARCH ln 229-231) follow the same `${{ secrets.* }}` form.

**GITHUB_STEP_SUMMARY block** — copy the `cat >> $GITHUB_STEP_SUMMARY << 'EOF'` markdown-table pattern from cd-staging.yml:77-125 for the what-if diff posting (RESEARCH ln 241). NOTE: this is GitHub workflow YAML (a heredoc inside a `run:` step) — that is legitimate and unrelated to the file-creation no-heredoc rule.

**Checkout/setup-python pin** — `actions/checkout@v4` + `actions/setup-python@v5` with `python-version: "3.12"`, `cache: pip` (ci.yml:54-58). Reuse exactly.

**Full target YAML:** RESEARCH §Code Examples 1 (ln 184-274). **Operator-only items (→ OPS-01, NOT in YAML):** RESEARCH ln 276 + Code Example 2 (federated-credential creation).

---

### `infra/observability.bicep` (config, control-plane)

**Analog:** `infra/main.bicep`.

**Param + description convention** (main.bicep:14-22):
```bicep
@description('Région Azure.')
param location string = resourceGroup().location
@description('Préfixe des ressources.')
param namePrefix string = 'ac360'
@description('Nom court d\'environnement.')
param environmentName string = 'staging'
```
Reuse `location` / `namePrefix` / `environmentName` verbatim; add `gatewayId`, `functionId`, `alertEmails array = []`, `teamsWebhookUrl string = ''` (RESEARCH ln 378-384).

**Resource naming `var` convention** (main.bicep:98-103): `var <name> = '${namePrefix}-<kind>-${environmentName}'`. Apply to LAW / App Insights / action group / alerts.

**Built-in role GUID + `subscriptionResourceId` pattern** (main.bicep:116, 123-126) — if observability needs a Monitoring role; copy the literal-GUID-in-`var` style.

**`for`-loop over an array param** (main.bicep:133-138, 214-222) — reuse for `emailReceivers: [for (e, i) in alertEmails: {...}]` (RESEARCH ln 410).

**Gated/conditional resource `= if (...)`** (main.bicep:433, 464, 479) — if any observability resource is environment-gated, copy the `= if (enable...)` form.

**`output` convention** (main.bicep:560-562): `output connectionString string = appi.properties.ConnectionString` (RESEARCH ln 398-399) so main.bicep can wire the app setting.

**Resource shapes:** RESEARCH §Code Examples 7-11, 13 (LAW, App Insights component, action group, metricAlerts, scheduledQueryRules, webtest, workbook). Keep `Microsoft.Insights/*` OUT of main.bicep — call this module from main.bicep (RESEARCH ln 155-158).

---

### `infra/budget.bicep` (config, control-plane)

**Analog:** `infra/main.bicep` param/resource shapes — BUT note the scope difference.

**Net-new vs main.bicep:** `targetScope = 'subscription'` (RESEARCH ln 509). main.bicep is implicitly RG-scoped (uses `resourceGroup().location` at ln 15). The budget CANNOT live in main.bicep (RESEARCH Pitfall 4, ln 580-584) — separate `az deployment sub create`.

**Param convention** — reuse main.bicep `@description` + typed-param style for `amount int = 200`, `actionGroupId string`, `alertEmails array` (RESEARCH ln 510-512).

**Resource shape:** RESEARCH §Code Example 12 (ln 506-541).

---

### `scripts/telemetry.py` (utility, transform)

**Analog:** `scripts/audit_trail.py` (gate + redaction reuse) and `scripts/safe_logger.py` (the single audited redaction surface).

**`from __future__` + import convention** (audit_trail.py:24-31):
```python
from __future__ import annotations
import os
from safe_logger import log_security, redact_mapping
```
telemetry.py imports `from safe_logger import redact` (RESEARCH ln 301). No path alias — relative-from-`scripts/` import (CLAUDE.md Import Organization).

**AppInsights env gate — REUSE the exact two-var gate** (audit_trail.py:39-51, mirrored at api_server.py:96):
```python
_APPINSIGHTS_ENV_VARS = ("APPINSIGHTS_INSTRUMENTATIONKEY", "APPLICATIONINSIGHTS_CONNECTION_STRING")
def _appinsights_gate_open() -> bool:
    return any((os.environ.get(name) or "").strip() for name in _APPINSIGHTS_ENV_VARS)
```
`setup_telemetry()` must early-return when the gate is closed (RESEARCH ln 320-323) — identical posture to `audit_trail.emit_document_access` ln 77-78.

**Redaction reuse — NO new regex (AUD-06):** the `RedactingSpanProcessor.on_end` routes every string attribute through `safe_logger.redact` (RESEARCH ln 303-317), exactly as `redact_mapping` does at safe_logger.py:137-140. Wrap the scrub in `try/except … pass` so telemetry scrubbing never breaks the request path (RESEARCH ln 314-315).

**`__all__` + module docstring convention** (safe_logger.py:60, audit_trail.py:33; CLAUDE.md Module Design): declare `__all__ = ["RedactingSpanProcessor", "setup_telemetry"]`; French domain docstring permitted.

**Lazy import of the heavy SDK** — import `configure_azure_monitor` INSIDE `setup_telemetry()` after the gate (RESEARCH ln 324), mirroring function_app.py's guarded-import discipline (ln 26-33) so pytest collection never requires the package.

**Full target:** RESEARCH §Code Example 3 (ln 294-331).

---

### `scripts/api_server.py` (controller, request-response) — MODIFY

**Analog:** self.

**`/health` stays as-is** (ln 672-679) — anonymous liveness 200, the availability-test target. Do NOT gate it.

**`/ready` — Entra-gated, copy the Depends pattern** used by every authed endpoint (e.g. ln 685, `oid: str = Depends(verify_azure_ad_token)`):
```python
@app.get("/ready")
async def readiness(oid: str = Depends(verify_azure_ad_token)):
    ...
```
Return coarse booleans only, 200/503, never leak detail (RESEARCH ln 359-372) — consistent with the `_redacted_detail` no-leak posture at ln 25-33.

**Telemetry wiring** — call `setup_telemetry()` once at startup, BEFORE traffic. The existing `AppInsightsMiddleware` (ln 90-116) already gates on `APPINSIGHTS_INSTRUMENTATIONKEY` (ln 96) and redacts via `redact_mapping` (ln 100); the new exporter reuses the SAME gate. The middleware log line may stay as belt-and-braces or be retired (RESEARCH ln 332 — Claude's discretion).

**Existing JSONResponse import** — `/ready` needs `JSONResponse`; api_server.py currently imports `FileResponse` from `fastapi.responses` (ln 2). Add `JSONResponse` to that import.

---

### `azure_functions/function_app.py` + `host.json` + `requirements.txt` (MODIFY)

**Analog:** self.

**Guarded-import discipline** (function_app.py:14-33) — wire `configure_azure_monitor` consistent with the existing `try/except` guard so non-runtime import (pytest) never fails. RESEARCH ln 345-348.

**host.json edit** — add `"telemetryMode": "OpenTelemetry"` at root, preserving the existing `version`/`logging.applicationInsights`/`extensionBundle` blocks (host.json:1-16). RESEARCH ln 341-342.

**Duplicate-telemetry guard (AVOID):** host emits request telemetry; the worker distro must NOT re-instrument requests (RESEARCH Pitfall 2, ln 568-572). App setting `PYTHON_APPLICATIONINSIGHTS_ENABLE_TELEMETRY=true` (RESEARCH ln 350).

**requirements pins** — add `azure-monitor-opentelemetry>=1.8.8,<2.0.0` to BOTH `requirements.txt` and `azure_functions/requirements.txt` (RESEARCH ln 62-65). First install gated by existing ci.yml `pip-audit` job (ci.yml:79-82).

---

### `tests/backend/test_ready_endpoint.py` (test, request-response)

**Analog:** `tests/backend/test_security_headers.py`.

**Path bootstrap + TestClient** (test_security_headers.py:7-11):
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
import api_server  # noqa: E402
client = TestClient(api_server.app)
```
`conftest.py` (tests/backend/conftest.py:16-25) already sets `TENANT_ID`/`CLIENT_ID`/`JOBS_BASE_DIR` and adds `scripts/` — no extra fixture needed.

**Depends override for the Entra gate** — `/ready` is authed, so override `verify_azure_ad_token` via `app.dependency_overrides` (RESEARCH ln 641); assert 200 (ready) / 503 (degraded) / 401 (unauth, no override). Use `monkeypatch.setenv`/`delenv` to flip the readiness env checks (RESEARCH ln 363-366).

---

### `tests/backend/test_telemetry_redaction.py` (test, transform)

**Analog:** `tests/backend/test_safe_logger_redaction.py`.

**Fake PII/secret fixtures — reuse exactly** (test_safe_logger_redaction.py:18-26): `FAKE_JWT`, `FAKE_SECRET_VALUE`, `FAKE_EMAIL = "jean.dupont@client-prive.fr"`, `FAKE_IBAN = "FR7630006000011234567890189"`.

**Assertion shape** (test_safe_logger_redaction.py:49-55): build a span with a PII-bearing attribute, run `RedactingSpanProcessor().on_end(span)`, assert the raw value is gone and a `MASQUÉ` marker is present (RESEARCH ln 577, Pitfall 3). Mock/stub the span object (`_name`, `_attributes`) — no live exporter.

---

### `docs/production/runbooks/{01-deploy,02-rollback,03-secret-rotation,04-incident-triage,05-killswitch}.md`

**Analog:** `docs/production/EMERGENCY_SHUTDOWN_RUNBOOK.md`.

**House style to copy:** title `# AC360 — <titre> (REQ-ID)`; a `> Objectif :` blockquote; a `## Principe` section; numbered `## Procédure` sections with fenced ```powershell``` az-CLI blocks using backtick line-continuation and `-g rg-ac360-prod` (analog uses `rg-ac360-staging`; swap to prod) — see EMERGENCY_SHUTDOWN_RUNBOOK.md:1-59. Markdown tables for variable/effect mappings (ln 14-22).

**Required addition per file:** a `## Dry-run / validation` section exercisable offline (RESEARCH ln 633). `05-killswitch.md` cross-links the existing EMERGENCY_SHUTDOWN_RUNBOOK.md (CONTEXT ln 35, RESEARCH ln 152).

## Shared Patterns

### Redaction (AUD-06) — the single audited surface
**Source:** `scripts/safe_logger.py:92-122` (`redact`), `:125-140` (`redact_mapping`).
**Apply to:** `scripts/telemetry.py` (span processor), test_telemetry_redaction.py.
**Rule:** NO new redaction regex may be introduced (RESEARCH ln 173). Route span name + every string attribute through `redact`:
```python
from safe_logger import redact
# inside on_end:
for k, v in list(span._attributes.items()):
    if isinstance(v, str):
        span._attributes[k] = redact(v)
```

### AppInsights env gate
**Source:** `scripts/audit_trail.py:39-51` (canonical two-var gate); mirrored at `scripts/api_server.py:96`.
**Apply to:** `scripts/telemetry.py setup_telemetry()`. Early-return when neither `APPINSIGHTS_INSTRUMENTATIONKEY` nor `APPLICATIONINSIGHTS_CONNECTION_STRING` is set — keeps telemetry inert in dev/test.

### Bicep param + naming + role-assignment + KV-reference app setting
**Source:** `infra/main.bicep` — `@description` params (ln 14-22), `var <name>='${namePrefix}-…-${environmentName}'` (ln 98-103), `for`-loop role assignments with `guid(...)` names + `subscriptionResourceId` role defs (ln 214-222, 276-296), KV-reference app setting form (ln 415-420).
**Apply to:** observability.bicep (alerts/action group/outputs), budget.bicep (params), and the main.bicep EDIT that wires `APPLICATIONINSIGHTS_CONNECTION_STRING` as an app setting on both apps (KV-ref `@Microsoft.KeyVault(...)` per ln 418, or plain — RESEARCH ln 163, A6).

### Test bootstrap (path + env)
**Source:** `tests/backend/conftest.py:16-25` (sets `scripts/` path + `TENANT_ID`/`CLIENT_ID`/`JOBS_BASE_DIR`) and `tests/backend/test_security_headers.py:7-11` (`TestClient(api_server.app)`).
**Apply to:** both new test files. Run env per RESEARCH ln 618: `TENANT_ID=test_tenant CLIENT_ID=test_client PYTHONPATH=scripts`.

### GitHub Actions step conventions
**Source:** `ci.yml` (checkout@v4, setup-python@v5 `cache: pip`, `needs:` graph, `${{ secrets.* }}`) + `cd-staging.yml` (`workflow_dispatch.inputs`, `GITHUB_STEP_SUMMARY` heredoc, `upload-artifact@v4`).
**Apply to:** cd-prod.yml.

## No Analog Found

| File | Role | Data Flow | Reason | Planner guidance |
|------|------|-----------|--------|------------------|
| `infra/workbook-ops.json` (loaded by observability.bicep `loadTextContent`) | config (data) | n/a | No Azure Monitor Workbook serialized-JSON exists in the repo | Use RESEARCH §Code Example 13 (ln 544-558) + panel KQL at ln 558; budget-% tile is a markdown/link tile (RESEARCH A4, Open Q3) |
| `infra/budget.bicep` `targetScope = 'subscription'` mechanics | config (IaC) | control-plane | All existing Bicep is RG-scoped (main.bicep); no subscription-scoped template precedent | Use RESEARCH §Code Example 12 + Pitfall 4 (separate `az deployment sub create`) |

## Metadata

**Analog search scope:** `.github/workflows/`, `infra/`, `scripts/`, `azure_functions/`, `tests/backend/`, `docs/production/`
**Files scanned (read):** cd-staging.yml, ci.yml, api_server.py (ln 1-130, 650-699), safe_logger.py, audit_trail.py, main.bicep (full), function_app.py (ln 1-45), host.json, test_safe_logger_redaction.py, test_security_headers.py, conftest.py, EMERGENCY_SHUTDOWN_RUNBOOK.md
**Pattern extraction date:** 2026-06-14
