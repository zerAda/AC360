# Phase 3: Backend Deploy & Observability - Research

**Researched:** 2026-06-14
**Domain:** Azure CD (GitHub Actions OIDC), App Service + Flex Functions deploy, Azure Monitor OpenTelemetry, Bicep observability-as-code, solo-operator runbooks
**Confidence:** HIGH (all genuine unknowns verified against current Microsoft Learn; package versions verified against PyPI)

## Summary

Phase 3 produces, but does not live-deploy, the production CD + observability layer. Every genuine unknown resolved cleanly against current Microsoft Learn (docs dated 2026-03 → 2026-06) and the existing codebase:

- **CD auth** is OIDC: `permissions: id-token: write` + `azure/login@v2` with `client-id`/`tenant-id`/`subscription-id` (no stored SP secret). The federated-credential creation (`az ad app federated-credential create`, subject `repo:ORG/REPO:environment:production`) is an **operator step** that belongs in the deploy runbook, not in `cd-prod.yml`.
- **Flex Functions deploy** uses **One Deploy** via `Azure/functions-action@v1` with **`remote-build: true`** — and you must NOT set `scm-do-build-during-deployment` or `enable-oryx-build` (Flex always does an Oryx remote build; Python on Flex *always* requires remote build). This differs from Y1/Consumption-Linux (external package URL).
- **Gateway (App Service B1)** deploys with `azure/webapps-deploy@v3`; the gunicorn `--workers 1` pin is already baked into the Bicep `appCommandLine` (AUD-04), so deploy carries no startup-command risk.
- **App Insights wiring** is `configure_azure_monitor()` from `azure-monitor-opentelemetry` (PyPI **1.8.8** [VERIFIED: pip index versions]). It reads `APPLICATIONINSIGHTS_CONNECTION_STRING` from the environment (= a Key Vault-reference app setting). FastAPI is auto-instrumented by the distro. **PII/secret redaction is preserved by registering a custom `SpanProcessor` (and `LogRecordProcessor`) whose `on_end`/`emit` calls `safe_logger.redact` on attribute values** — the same audited surface AUD-06 already mandates.
- **Functions-side** wiring is host-level: `host.json` `"telemetryMode": "OpenTelemetry"` + app setting `PYTHON_APPLICATIONINSIGHTS_ENABLE_TELEMETRY=true` + `azure-monitor-opentelemetry` in `azure_functions/requirements.txt` + `configure_azure_monitor()` in `function_app.py`.
- **Alerts/dashboard/budget as code** are standard Bicep resource types: `Microsoft.Insights/metricAlerts`, `Microsoft.Insights/scheduledQueryRules`, `Microsoft.Insights/actionGroups`, `Microsoft.Insights/webtests`, `Microsoft.Insights/workbooks`, `Microsoft.Consumption/budgets`. **Critical scoping fact:** the budget is **subscription-scoped**, not resource-group-scoped — it needs a module with `targetScope = 'subscription'` or a `scope:` override.
- **CRITICAL GAP found in the repo:** `infra/main.bicep` has **NO Application Insights resource and NO Log Analytics workspace today.** OBS-01 must add both (a workspace-based App Insights component) before any alert/workbook/availability-test can reference them. This is the single largest net-new infra item in the phase.

**Primary recommendation:** Add a single new Bicep module `infra/observability.bicep` (Log Analytics + App Insights component + action group + metric alerts + scheduled query rules + webtest + webtest alert + workbook), wire `APPLICATIONINSIGHTS_CONNECTION_STRING` as a KV-reference (or plain App Insights connection string) app setting onto both apps in `main.bicep`, add a **subscription-scoped** budget module, add `azure-monitor-opentelemetry` to both requirements files, add the redaction-preserving processor + `configure_azure_monitor()` call to `api_server.py` and `function_app.py`, add `/ready`, and author the five runbooks with offline dry-run sections.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CD orchestration / gating | GitHub Actions (CI tier) | — | What-if, approval, deploy jobs live in `cd-prod.yml`; OIDC trust is GitHub↔Entra |
| Federated credential trust | Entra ID (identity) | operator runbook | App-reg federated cred is a tenant config, created once by operator |
| Infra provisioning (alerts/dashboard/budget) | Bicep / ARM control plane | — | Declarative resources in `infra/` |
| Telemetry capture + redaction | Gateway app (api_server) + Functions worker | safe_logger (shared) | OTel processors run in-process; redaction is shared audited surface |
| Telemetry storage / alerting / dashboard | Azure Monitor (App Insights + Log Analytics) | — | Backend service owns retention, alert evaluation, workbook rendering |
| Readiness/liveness probing | Gateway app (`/health`, `/ready`) | Azure Monitor webtest | Endpoints in-app; availability test in Monitor calls `/health` |
| Budget / cost notification | Cost Management (subscription scope) | Action group → Teams/email | Budget is a subscription resource; routes to the same action group |
| Operator procedures | docs/ (runbooks) | — | Markdown decision trees, offline-validatable |

## Standard Stack

### Core
| Library / Action | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `azure-monitor-opentelemetry` | **1.8.8** [VERIFIED: pip index versions] | One-call App Insights instrumentation (`configure_azure_monitor`) for gateway + Functions | Microsoft's official OTel distro; the exporter Phase 1 deferred (OBS-01) [CITED: learn.microsoft.com/azure/azure-monitor/app/opentelemetry-enable] |
| `azure/login@v2` | v2 | OIDC federated login from GitHub Actions | Official, supports `id-token` OIDC, no stored secret [CITED: learn.microsoft.com/azure/developer/github/connect-from-azure-openid-connect] |
| `Azure/functions-action@v1` | v1 | Deploy Functions package (One Deploy on Flex) | Official Functions deploy action; `remote-build` input for Flex [CITED: learn.microsoft.com/azure/azure-functions/functions-how-to-github-actions] |
| `azure/webapps-deploy@v3` | v3 | Deploy gateway (App Service B1) zip/package | Official App Service deploy action |
| `azure/arm-deploy@v2` (or `azure/cli@v2`) | v2 | Run `az deployment group what-if` / `create` | Bicep what-if + apply in pipeline |

### Supporting
| Library / Action | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `opentelemetry-instrumentation-fastapi` | bundled by distro | FastAPI auto-instrumentation | Pulled in transitively by `azure-monitor-opentelemetry`; no separate pin needed [ASSUMED — distro bundles it; pin only if you must disable it via `instrumentation_options`] |
| `actions/setup-python@v5` | v5 | Python 3.12 for build/zip steps | Already used in `ci.yml` |
| `markdownlint-cli2` (npm) or `pymarkdownlnt` (pip) | latest | Offline runbook lint (OPS validation) | Wave-0 validation of `docs/production/runbooks/*.md` |
| `yamllint` (pip) | latest | Offline `cd-prod.yml` lint | Wave-0 validation of the new workflow |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `configure_azure_monitor` (distro) | Raw `azure-monitor-opentelemetry-exporter` + manual TracerProvider | More control, far more code; loses one-call auto-instrumentation — **rejected** (CONTEXT locks the distro) |
| OIDC federated cred | Stored SP secret in GitHub secret | Secret rotation burden, leak surface — **rejected** (CONTEXT locks OIDC) |
| `Microsoft.Consumption/budgets` | `Microsoft.CostManagement/budgets` (MG/sub) | CostManagement supports MG scope; Consumption is the standard sub/RG cost budget — Consumption is sufficient for one subscription |
| App Service deployment slots (blue-green) | — | Needs S1+; **breaks AUD-04 single-instance B1 pin** — **rejected** (CONTEXT) |

**Installation (apps):**
```bash
# root requirements.txt (gateway) AND azure_functions/requirements.txt (Functions worker)
azure-monitor-opentelemetry>=1.8.8,<2.0.0
```

**Version verification performed:**
```text
azure-monitor-opentelemetry  -> 1.8.8 latest [VERIFIED: pip index versions, 2026-06-14]
azure/login                  -> v2          [CITED: official action docs]
Azure/functions-action       -> v1          [CITED: official action docs]
```

## Package Legitimacy Audit

> slopcheck was not available in this research environment. Per protocol, the one net-new pip package is verified directly against PyPI and tagged accordingly. Only one external package is introduced; all GitHub Actions are first-party `Azure/*` / `actions/*`.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| azure-monitor-opentelemetry | PyPI | mature (1.0.0 GA 2023; 1.8.8 current) | very high | github.com/Azure/azure-sdk-for-python | n/a (unavailable) | Approved — first-party Microsoft, verified on PyPI |
| azure/login, Azure/functions-action, azure/webapps-deploy, azure/arm-deploy | GitHub Marketplace | mature | very high | github.com/Azure/* | n/a | Approved — first-party Microsoft actions |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

> slopcheck unavailable → the one net-new package (`azure-monitor-opentelemetry`) is treated as confirmed via PyPI + official Microsoft Learn citation, but the planner should still gate the *first install* behind the existing CI `pip-audit` job (already present in `ci.yml`).

## Architecture Patterns

### System Architecture Diagram

```
                 ┌─────────────────────────────────────────────┐
   git push tag  │  GitHub Actions: cd-prod.yml                 │
   prod-* ──────►│                                              │
                 │  job: build        (zip gateway + functions) │
                 │  job: whatif  ─── az deployment group what-if│──► posts diff to summary
                 │        │                                     │
                 │  [GitHub Environment "production": APPROVAL] │◄── required reviewer (operator)
                 │        ▼                                     │
                 │  job: deploy  (needs: whatif, environment:   │
                 │        ├─ azure/login@v2 (OIDC)              │   production)
                 │        ├─ az deployment group create (Bicep) │──► RG resources
                 │        ├─ webapps-deploy@v3 → gateway B1     │
                 │        └─ functions-action@v1 → Flex (remote)│
                 └─────────────────────────────────────────────┘
                                     │ deploys to
                                     ▼
   Teams/Copilot ──► Gateway (FastAPI, B1, --workers 1)         Functions (Flex, Durable)
                       │  configure_azure_monitor()               │ host.json telemetryMode=OpenTelemetry
                       │  + Redacting SpanProcessor (AUD-06)       │ + configure_azure_monitor()
                       │  /health (liveness, anon)                 │ + same Redacting processor
                       │  /ready  (readiness, Entra-gated)         ▼
                       └──────────────► App Insights (workspace-based) ◄── Log Analytics
                                              │
              ┌───────────────────────────────┼───────────────────────────────┐
              ▼                                ▼                                ▼
   metricAlerts (5xx)            scheduledQueryRules            webtests (Standard avail.
   + scheduledQueryRules         (Functions/orchestration/      test against /health) + alert
   (dep failures OCR/Fabric/     dep failures)
   Graph)                                       └──► actionGroups (email + Teams webhook)
                                                              ▲
   Cost Management budget (subscription scope) ───────────────┘ (contactGroups → action group)
                                                              │
                          Azure Monitor Workbook ◄────────────┘ (4 panels: 24h audits,
                                                                  error rate, p95, budget %)
```

### Recommended File Structure (net-new + edits)
```
.github/workflows/
└── cd-prod.yml                      # NEW — OIDC, what-if gate, environment approval, deploy
infra/
├── main.bicep                       # EDIT — add App Insights connection-string app setting to both apps;
│                                    #        emit appInsightsConnectionString output; call observability module
├── observability.bicep             # NEW — Log Analytics + App Insights + action group + alerts + webtest + workbook
├── budget.bicep                    # NEW — subscription-scoped Microsoft.Consumption/budgets module
└── prod.parameters.json            # EDIT — add budget amount, alert emails, Teams webhook URL param
scripts/
├── api_server.py                    # EDIT — configure_azure_monitor() at startup + Redacting processors + /ready
└── telemetry.py                     # NEW (optional) — RedactingSpanProcessor / RedactingLogProcessor + setup()
azure_functions/
├── function_app.py                  # EDIT — configure_azure_monitor() + same processors
├── host.json                        # EDIT — "telemetryMode": "OpenTelemetry"
└── requirements.txt                 # EDIT — add azure-monitor-opentelemetry
requirements.txt                     # EDIT — add azure-monitor-opentelemetry
docs/production/runbooks/
├── 01-deploy.md                     # NEW OPS-01
├── 02-rollback.md                   # NEW OPS-02
├── 03-secret-rotation.md            # NEW OPS-03
├── 04-incident-triage.md            # NEW OPS-04
└── 05-killswitch.md                 # NEW OPS-05 (cross-link existing EMERGENCY_SHUTDOWN_RUNBOOK.md)
```

### Pattern: keep Bicep alerts in a module, not inline in main.bicep
**What:** Put all `Microsoft.Insights/*` resources in `infra/observability.bicep`, called from `main.bicep` with resource IDs passed in.
**When:** Always — keeps the hardened `main.bicep` posture readable and lets the what-if diff group observability changes.
**Why:** main.bicep is already 562 lines of security-load-bearing config; mixing alert noise in raises regression risk.

### Anti-Patterns to Avoid
- **Setting `scm-do-build-during-deployment: true` on a Flex deploy.** Flex always does an Oryx remote build; setting Kudu build flags conflicts. Use ONLY `remote-build: true`. [CITED: functions-how-to-github-actions]
- **Putting the federated-credential `az ad app` command in `cd-prod.yml`.** It's a one-time tenant setup → operator runbook (OPS-01 / setup section).
- **Writing the App Insights connection string in cleartext app settings.** Use a KV-reference app setting OR the App Insights output piped through Bicep (the connection string is not a secret per se, but project policy INF-08 favors KV references; either is acceptable — connection string is not a high-value secret like the OBO secret).
- **Adding the Azure Monitor distro to BOTH host and worker for request tracking on Functions.** Avoid duplicate request telemetry — host emits request telemetry; the worker distro must not re-instrument requests. Use host `telemetryMode` + worker `configure_azure_monitor()` only for logs/custom events. [CITED: opentelemetry-howto — "Duplicate request telemetry"]
- **Adding a deployment slot for rollback.** B1 has no slots; slots need S1+ which breaks AUD-04. Rollback = redeploy previous tag.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| App→App Insights pipeline | Custom HTTP telemetry poster | `configure_azure_monitor()` | Batching, retry, OTLP semantics, auto-instrumentation handled |
| FastAPI request spans | Manual middleware timing | distro auto-instruments FastAPI | Already covered; the existing `AppInsightsMiddleware` log line becomes redundant once distro is on |
| PII scrubbing regexes in OTel path | New redaction regexes | `safe_logger.redact` inside a SpanProcessor | AUD-06: single audited redaction surface; no new regex may be introduced |
| OIDC token exchange | Manual JWT to Entra | `azure/login@v2` | Action performs the federated exchange |
| Flex zip build | Custom pip --target packaging | `functions-action@v1 remote-build: true` | Oryx builds remotely; matches Flex contract |
| Cost alerting | Polling Cost Management API | `Microsoft.Consumption/budgets` + action group | Native, declarative, notifies email + action group |
| Availability probing | Cron curl from a VM | `Microsoft.Insights/webtests` Standard | Multi-region, native alert integration |

**Key insight:** Everything in this phase is a *wiring* exercise of first-party Azure primitives. The only bespoke code is the redaction-preserving processor (mandatory) and the `/ready` endpoint — both small and testable offline.

## Code Examples

### 1. `cd-prod.yml` — OIDC + what-if gate + environment approval + deploy
```yaml
# Source: composed from learn.microsoft.com/azure/developer/github/connect-from-azure-openid-connect
#         + functions-how-to-github-actions (Flex remote-build)
name: AC360 CD — Production

on:
  push:
    tags: [ 'prod-*' ]          # immutable known-good marker (OPS-02 rollback target)
  workflow_dispatch:
    inputs:
      ref:
        description: "Tag/SHA to deploy (rollback = a previous prod-* tag)"
        required: true

permissions:
  id-token: write               # REQUIRED for OIDC token fetch
  contents: read

env:
  RG: rg-ac360-prod
  GATEWAY_APP: ac360-gateway-prod
  FUNC_APP: ac360-func-prod

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - name: Package gateway zip
        run: |
          pip install -r requirements.txt --target=".gw/.python_packages/lib/site-packages" || true
          # zip gateway app (scripts/) per package_release.ps1 conventions
      # Functions remote-build means we ship source, not a built artifact.
      - uses: actions/upload-artifact@v4
        with: { name: deploy-artifacts, path: . }

  whatif:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - name: Bicep what-if (GATE — diff posted to summary)
        uses: azure/cli@v2
        with:
          azcliversion: latest
          inlineScript: |
            az deployment group what-if \
              -g ${{ env.RG }} \
              -f infra/main.bicep \
              -p @infra/prod.parameters.json | tee whatif.txt
            { echo '## Bicep what-if (PROD)'; echo '```'; cat whatif.txt; echo '```'; } >> "$GITHUB_STEP_SUMMARY"

  deploy:
    runs-on: ubuntu-latest
    needs: whatif
    environment: production       # ← required reviewer approval gate (manual)
    steps:
      - uses: actions/download-artifact@v4
        with: { name: deploy-artifacts }
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - name: Bicep apply
        uses: azure/cli@v2
        with:
          azcliversion: latest
          inlineScript: |
            az deployment group create \
              -g ${{ env.RG }} -f infra/main.bicep -p @infra/prod.parameters.json
      - name: Deploy gateway (App Service B1)
        uses: azure/webapps-deploy@v3
        with:
          app-name: ${{ env.GATEWAY_APP }}
          package: .                       # gunicorn --workers 1 startup is set in Bicep appCommandLine
      - name: Deploy Functions (Flex — One Deploy, remote build)
        uses: Azure/functions-action@v1
        with:
          app-name: ${{ env.FUNC_APP }}
          package: azure_functions
          remote-build: true               # Flex: Oryx remote build. Do NOT set scm-do-build/enable-oryx-build.
          # sku: flexconsumption           # only needed when authenticating with publish-profile; omit with OIDC/RBAC
```
> **Where it lands:** `.github/workflows/cd-prod.yml`.
> **Operator-only items (→ OPS-01 setup section, NOT in YAML):** create the GitHub `production` Environment with a required reviewer; create three GitHub repo/env secrets (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`); run the federated-credential command below.

### 2. Federated credential creation (OPERATOR step — deploy runbook)
```bash
# Source: learn.microsoft.com/azure/developer/github/connect-from-azure-openid-connect
# Run once by the operator after the prod app-reg exists. Subject MUST match the GitHub Environment.
az ad app federated-credential create \
  --id <PROD_DEPLOY_APP_OBJECT_ID> \
  --parameters '{
    "name": "ac360-gh-prod",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<ORG>/<REPO>:environment:production",
    "audiences": ["api://AzureADTokenExchange"]
  }'
# Then grant the deploy app/MI a least-privilege role on rg-ac360-prod (e.g. Contributor on the RG only).
```
> **Where it lands:** `docs/production/runbooks/01-deploy.md` (setup section). NOT in `cd-prod.yml`.

### 3. Gateway App Insights wiring + redaction-preserving processor (`api_server.py` / `scripts/telemetry.py`)
```python
# Source: learn.microsoft.com/azure/azure-monitor/app/opentelemetry-enable (configure_azure_monitor)
#       + opentelemetry-add-modify (custom SpanProcessor.on_end)
# AUD-06: redaction must survive the OpenTelemetry export path — reuse safe_logger.redact, no new regex.
import os
from opentelemetry.sdk.trace import SpanProcessor
from safe_logger import redact

class RedactingSpanProcessor(SpanProcessor):
    """Scrubs span name + every string attribute through the single audited redaction surface."""
    def on_start(self, span, parent_context=None): ...
    def on_end(self, span):
        try:
            if span._name:
                span._name = redact(span._name)
            if span._attributes:
                for k, v in list(span._attributes.items()):
                    if isinstance(v, str):
                        span._attributes[k] = redact(v)
        except Exception:
            pass  # never let telemetry scrubbing break the request path
    def shutdown(self): ...
    def force_flush(self, timeout_millis=30000): return True

def setup_telemetry() -> None:
    # Gate kept identical to existing api_server.py:96 / audit_trail.py — wire ONLY when configured.
    if not (os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
            or os.environ.get("APPINSIGHTS_INSTRUMENTATIONKEY")):
        return
    from azure.monitor.opentelemetry import configure_azure_monitor
    configure_azure_monitor(
        logger_name="AC360",                          # matches safe_logger.logger
        span_processors=[RedactingSpanProcessor()],   # redaction in the export path
        # FastAPI is auto-instrumented by the distro; to disable: instrumentation_options={"fastapi": {"enabled": False}}
    )
# Call setup_telemetry() once at module import / FastAPI startup, BEFORE app handles traffic.
```
> **Where it lands:** new `scripts/telemetry.py` (processor + `setup_telemetry`), called from `scripts/api_server.py` at startup. The existing `AppInsightsMiddleware` redacted-log line (api_server.py:96-105) becomes redundant for request telemetry and may be left as a belt-and-braces audit log or removed — Claude's discretion.

> **Connection-string env var:** `configure_azure_monitor()` reads `APPLICATIONINSIGHTS_CONNECTION_STRING` from the environment automatically [CITED: opentelemetry-enable — "Environment variable … recommended for production"]. Supply it as a Bicep app setting (KV-reference or plain) on both apps.

### 4. A custom-event / log path (AUD-07 audit trail keeps exporting)
`audit_trail.emit_document_access` already routes through `safe_logger.log_security` → `logging.getLogger("AC360")`. Once `configure_azure_monitor(logger_name="AC360")` is active, those INFO logs export as App Insights traces/custom events automatically — **no call-site change** (exactly the Phase-1 design: "the seam exports for real"). To surface them as `customEvents` with the canonical name, set the `microsoft.custom_event.name` attribute on the log record (optional; the four-field contract is already in the log `data`). [CITED: opentelemetry-add-modify]

### 5. Functions-side wiring
```jsonc
// azure_functions/host.json  (EDIT — add to root)
{ "version": "2.0", "telemetryMode": "OpenTelemetry", /* existing extensionBundle/logging … */ }
```
```python
# azure_functions/function_app.py (EDIT — at top of module entry, App Insights tab)
# Source: learn.microsoft.com/azure/azure-functions/opentelemetry-howto (python, app-insights)
from azure.monitor.opentelemetry import configure_azure_monitor
configure_azure_monitor(logger_name="AC360", span_processors=[RedactingSpanProcessor()])
```
App settings on the Functions app (Bicep): `APPLICATIONINSIGHTS_CONNECTION_STRING` (KV-ref or plain) **and** `PYTHON_APPLICATIONINSIGHTS_ENABLE_TELEMETRY=true`. requirements: add `azure-monitor-opentelemetry`. [CITED: opentelemetry-howto]
> **Where it lands:** `azure_functions/host.json`, `azure_functions/function_app.py`, `azure_functions/requirements.txt`, and Bicep `functionApp.siteConfig.appSettings`.

### 6. `/ready` readiness endpoint (Entra-gated) vs `/health` liveness (anon)
```python
# scripts/api_server.py — keep /health (anon liveness 200) as-is; ADD /ready (Entra-gated readiness).
from fastapi import Depends
from auth import verify_azure_ad_token

@app.get("/ready")
async def readiness(oid: str = Depends(verify_azure_ad_token)):
    checks = {}
    # 1) Key Vault reference resolved? -> the OBO secret app setting must NOT still be the @Microsoft.KeyVault(...) literal
    obo = os.environ.get("OBO_CLIENT_SECRET", "")
    checks["keyvault_ref"] = bool(obo) and not obo.startswith("@Microsoft.KeyVault")
    # 2) Downstream reachability — shallow, no PII, no secret. Bounded timeout; report bool only.
    checks["function_host"] = bool(os.environ.get("AZURE_FUNCTION_URL"))
    # (Optional) OCR/Fabric reachability via a HEAD/ping with short timeout — return bool only.
    ready = all(checks.values())
    # Never leak detail: return coarse booleans, 200 if ready else 503.
    return JSONResponse(status_code=200 if ready else 503,
                        content={"status": "ready" if ready else "degraded", "checks": checks})
```
> **Where it lands:** `scripts/api_server.py`. `/health` stays anonymous (liveness + the Standard availability test target). `/ready` is Entra-gated (readiness) and returns only coarse booleans (no detail leak). Testable offline with FastAPI `TestClient` + monkeypatched env.

### 7. Bicep — App Insights + Log Analytics (NET-NEW; OBS-01 prerequisite)
```bicep
// infra/observability.bicep (NEW). main.bicep passes gateway/function/storage/docintel IDs in.
param location string
param namePrefix string
param environmentName string
param gatewayId string
param functionId string
param alertEmails array = []
param teamsWebhookUrl string = ''     // FinOps + alert Teams sink (OBS-04)

resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-law-${environmentName}'
  location: location
  properties: { sku: { name: 'PerGB2018' }, retentionInDays: 30 }   // RGP-04: deliberate short EU-region retention
}

resource appi 'Microsoft.Insights/components@2020-02-02' = {
  name: '${namePrefix}-appi-${environmentName}'
  location: location
  kind: 'web'
  properties: { Application_Type: 'web', WorkspaceResourceId: law.id }   // workspace-based (classic is retired)
}
output connectionString string = appi.properties.ConnectionString
output appInsightsId string = appi.id
```

### 8. Bicep — action group (email + Teams webhook)
```bicep
resource ag 'Microsoft.Insights/actionGroups@2024-10-01-preview' = {
  name: '${namePrefix}-ag-${environmentName}'
  location: 'global'
  properties: {
    groupShortName: 'ac360ops'      // <= 12 chars
    enabled: true
    emailReceivers: [for (e, i) in alertEmails: { name: 'email${i}', emailAddress: e, useCommonAlertSchema: true }]
    // Teams: use webhookReceiversV2 / Logic App if posting to a channel; legacy office365 connectors are retiring.
    webhookReceivers: empty(teamsWebhookUrl) ? [] : [
      { name: 'teams', serviceUri: teamsWebhookUrl, useCommonAlertSchema: true }
    ]
  }
}
```
> **Open item:** Microsoft is retiring O365 connector Teams webhooks; a Power Automate / Workflows webhook URL is the durable sink. The Bicep `webhookReceivers` shape is correct regardless of which URL the operator supplies. [ASSUMED — connector-retirement timeline; verify the operator's Teams webhook type at provisioning.]

### 9. Bicep — metric alert (gateway 5xx)
```bicep
// Source shape: learn.microsoft.com/azure/templates/microsoft.insights/metricalerts (Bicep)
resource gw5xx 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${namePrefix}-gw-5xx-${environmentName}'
  location: 'global'
  properties: {
    severity: 1
    enabled: true
    scopes: [ gatewayId ]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'http5xx'
          criterionType: 'StaticThresholdCriterion'
          metricNamespace: 'Microsoft.Web/sites'
          metricName: 'Http5xx'
          operator: 'GreaterThan'
          threshold: 5
          timeAggregation: 'Total'
        }
      ]
    }
    autoMitigate: true
    actions: [ { actionGroupId: ag.id } ]
  }
}
```

### 10. Bicep — log alert (dependency failures OCR/Fabric/Graph; Functions/orchestration errors)
```bicep
// scheduledQueryRules = KQL log alert. Scope = the App Insights component (or LAW).
resource depFail 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${namePrefix}-dep-fail-${environmentName}'
  location: location
  properties: {
    severity: 1
    enabled: true
    scopes: [ appi.id ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    criteria: {
      allOf: [
        {
          query: 'dependencies | where success == false and (target has "cognitiveservices" or target has "fabric" or target has "graph.microsoft.com") | summarize c = count()'
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 3
          failingPeriods: { numberOfEvaluationPeriods: 1, minFailingPeriodsToAlert: 1 }
        }
      ]
    }
    actions: { actionGroups: [ ag.id ] }
  }
}
```
> A second `scheduledQueryRules` (or a `Microsoft.Web/sites`-namespace metric alert on `FunctionExecutionCount`/exceptions) covers Functions/orchestration errors. Use a KQL `exceptions`/`traces` query for orchestration failure signatures.

### 11. Bicep — Standard availability test (webtest) against `/health` + alert
```bicep
resource webtest 'Microsoft.Insights/webtests@2022-06-15' = {
  name: '${namePrefix}-avail-${environmentName}'
  location: location
  kind: 'standard'
  tags: { 'hidden-link:${appi.id}': 'Resource' }   // required link tag to the App Insights component
  properties: {
    SyntheticMonitorId: '${namePrefix}-avail-${environmentName}'
    Name: 'AC360 gateway /health'
    Enabled: true
    Frequency: 300
    Timeout: 30
    Kind: 'standard'
    RetryEnabled: true
    Locations: [ { Id: 'emea-nl-ams-azr' }, { Id: 'emea-fr-pra-edge' } ]  // EU locations (RGP-06)
    Request: { RequestUrl: 'https://${gatewayName}.azurewebsites.net/health', HttpVerb: 'GET' }
    ValidationRules: { ExpectedHttpStatusCode: 200, SSLCheck: true }
  }
}
// Pair with a metricAlerts on the webtest's availabilityResults/availabilityPercentage (or a webtest alert).
```
> [ASSUMED — exact `Locations.Id` strings; verify the current EU availability-test location IDs at provisioning. The webtest resource shape and `hidden-link` tag are CITED-pattern.]

### 12. Bicep — subscription-scoped budget (OBS-04)
```bicep
// infra/budget.bicep (NEW) — budgets are SUBSCRIPTION-scoped, not RG-scoped.
// Source shape: learn.microsoft.com/azure/templates/microsoft.consumption/budgets (Bicep)
targetScope = 'subscription'
param amount int = 200
param actionGroupId string
param alertEmails array

resource budget 'Microsoft.Consumption/budgets@2024-08-01' = {
  name: 'ac360-prod-monthly'
  properties: {
    amount: amount
    category: 'Cost'
    timeGrain: 'Monthly'
    timePeriod: { startDate: '2026-07-01T00:00:00Z' }   // first of a month, >= 2017-06-01
    notifications: {
      'Actual_GreaterThan_80_Percent': {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        thresholdType: 'Actual'
        contactEmails: alertEmails
        contactGroups: [ actionGroupId ]   // routes to the same action group → Teams + email
      }
      'Forecasted_GreaterThan_100_Percent': {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        thresholdType: 'Forecasted'
        contactEmails: alertEmails
        contactGroups: [ actionGroupId ]
      }
    }
  }
}
```
> **Scope note:** because this is `targetScope = 'subscription'`, it cannot live inside the RG-scoped `main.bicep` body — deploy it as a separate `az deployment sub create` step in `cd-prod.yml`, OR as a `module` with explicit subscription scope. Plan a distinct what-if/apply for the budget. [CITED: budgets Bicep reference — "deployed at … Subscription"]

### 13. Bicep — Workbook (one-pane dashboard, OBS-05)
```bicep
resource wb 'Microsoft.Insights/workbooks@2023-06-01' = {
  name: guid('ac360-ops-workbook', environmentName)   // workbook name must be a GUID
  location: location
  kind: 'shared'
  properties: {
    displayName: 'AC360 Ops — one pane'
    category: 'workbook'
    sourceId: appi.id
    serializedData: loadTextContent('workbook-ops.json')  // 4 panels as KQL: 24h audits, error rate, p95, budget %
  }
}
```
> Panels (KQL against App Insights): (1) last-24h audits = `customEvents | where name == "ac360_document_access" | where timestamp > ago(24h) | count`; (2) error rate = requests success ratio; (3) p95 latency = `requests | summarize percentile(duration,95)`; (4) budget % is shown via a markdown/metric tile linking to the budget (cost data isn't in App Insights — link out or use a Cost Management workbook tile). [ASSUMED — budget-% panel cannot query App Insights; render as a link/markdown tile or a separate Cost Management view. Flag for operator.]

## Common Pitfalls

### Pitfall 1: Flex deploy fails because no remote build
**What goes wrong:** Python Flex deploy ships source without an Oryx build → missing dependencies at runtime.
**Why:** Flex Python *always* requires remote build; the Consumption-Linux external-package-URL path does not apply.
**How to avoid:** `functions-action@v1` with `remote-build: true`; do NOT set `scm-do-build-during-deployment`/`enable-oryx-build`.
**Warning signs:** ModuleNotFoundError in Functions logs post-deploy.

### Pitfall 2: Duplicate request telemetry on Functions
**What goes wrong:** Host emits request telemetry AND worker distro re-instruments → double counts, doubled cost.
**Why:** Azure Monitor distro includes request instrumentation; host already emits requests.
**How to avoid:** Use host `telemetryMode: OpenTelemetry` + worker `configure_azure_monitor()` for logs/custom events; rely on host for request spans. Set `PYTHON_APPLICATIONINSIGHTS_ENABLE_TELEMETRY=true`. [CITED: opentelemetry-howto]
**Warning signs:** Each audit shows two request entries with the same operationId.

### Pitfall 3: Redaction silently dropped in the OTel path
**What goes wrong:** Distro auto-instrumentation captures raw URLs/attributes containing PII before any redaction.
**Why:** `configure_azure_monitor()` exports attributes as captured unless a processor scrubs them.
**How to avoid:** Register `RedactingSpanProcessor` (and a log-record equivalent if you emit raw logs) via `span_processors=[...]`; route through `safe_logger.redact`. Write a unit test asserting a PII-bearing span attribute is masked after `on_end`.
**Warning signs:** A test span with an email/IBAN attribute exports unmasked.

### Pitfall 4: Budget deploy fails inside RG-scoped deployment
**What goes wrong:** `Microsoft.Consumption/budgets` placed in RG-scoped `main.bicep` → scope error.
**Why:** Budgets deploy at subscription (or RG) scope; the standard one is subscription.
**How to avoid:** Separate `targetScope = 'subscription'` module + `az deployment sub create`.
**Warning signs:** `InvalidTemplateDeployment` / scope mismatch at what-if.

### Pitfall 5: Federated subject mismatch → OIDC login 401
**What goes wrong:** `azure/login@v2` fails with AADSTS70021/AADSTS700213.
**Why:** The federated-credential `subject` doesn't match the workflow's actual subject. For a job with `environment: production`, the subject is `repo:ORG/REPO:environment:production` — NOT `:ref:refs/heads/main`.
**How to avoid:** Because the deploy job uses `environment: production`, the federated cred MUST use the `:environment:production` subject. Document exact ORG/REPO casing in OPS-01.
**Warning signs:** what-if job (no environment) may need a *separate* federated cred with a `:ref:` or pull_request subject if it also uses OIDC.

> **Note for planner:** the `whatif` job above also uses `azure/login@v2` but has NO `environment:`. Its OIDC subject will be `repo:ORG/REPO:ref:refs/tags/prod-*` (tag trigger) or `:pull_request`. Either add a second federated credential for that subject, or run what-if read-only under the same environment. Surface as an OPS-01 decision.

## Runtime State Inventory

> This is a deploy/observability phase (largely additive code + infra), but it touches live-service config and OS/registered state. Inventory completed.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no datastore keys renamed. App Insights is new storage, not a migration. | None — verified by reviewing main.bicep (no AI resource exists). |
| Live service config | (1) **GitHub `production` Environment + required reviewer** — lives in GitHub settings, not git. (2) **3 GitHub secrets** (`AZURE_CLIENT_ID/TENANT_ID/SUBSCRIPTION_ID`). (3) **Teams webhook URL** for action group + budget — lives in Power Automate/Teams, not git. (4) **gatewayOutboundIps** must be populated in prod.parameters AFTER first deploy (carried Phase-2 operator item). | Operator setup steps in OPS-01; webhook URL passed as a Bicep param/secret. |
| OS-registered state | **Entra app-reg federated credential** (`az ad app federated-credential create`) — registered once in the tenant. **Role assignment** for the deploy identity on `rg-ac360-prod`. | Operator step (OPS-01 setup). |
| Secrets/env vars | **`APPLICATIONINSIGHTS_CONNECTION_STRING`** new app setting on both apps (KV-ref or plain — not high-value). **`PYTHON_APPLICATIONINSIGHTS_ENABLE_TELEMETRY=true`** on Functions. OBO secret unchanged. | Bicep app-setting edits; no secret rotation. |
| Build artifacts | Flex remote-build produces a fresh package each deploy; no stale egg-info concern here. | None. |

**The canonical question — after every file is updated, what runtime state remains?** The GitHub Environment, three GitHub secrets, the Entra federated credential, the deploy-identity role assignment, the Teams webhook URL, and the post-first-deploy `gatewayOutboundIps` value. All are operator checkpoints, all documented in OPS-01.

## Validation Architecture

> nyquist_validation treated as enabled (no `.planning/config.json` override found disabling it). Below: how each CD/OBS/OPS requirement is validated OFFLINE vs at an operator-checkpoint live check.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio (existing, `setup.cfg` asyncio_mode auto) |
| Config file | `setup.cfg` (`[tool:pytest]`); per-dir `conftest.py` add `scripts/` to path |
| Quick run | `python -m pytest tests/backend/test_ready_endpoint.py tests/backend/test_telemetry_redaction.py -x` |
| Full suite | `python -m pytest tests/ -q` (env: `TENANT_ID=test_tenant CLIENT_ID=test_client PYTHONPATH=scripts`) |
| Offline infra | `az bicep build -f infra/main.bicep` + `-f infra/observability.bicep` + `-f infra/budget.bicep`; existing `scripts/validate_infra.ps1` |
| Offline workflow | `yamllint .github/workflows/cd-prod.yml`; optional `actionlint` |
| Offline runbooks | `markdownlint-cli2 docs/production/runbooks/**.md` or `pymarkdownlnt scan` |

### Phase Requirements → Test/Validation Map
| Req ID | Behavior | Validation Type | Offline command / check | Live (operator checkpoint) |
|--------|----------|-----------------|--------------------------|----------------------------|
| CD-01 | cd-prod.yml exists w/ OIDC, what-if gate, env approval | offline lint + structural | `yamllint cd-prod.yml`; grep `id-token: write`, `environment: production`, `what-if` | First OIDC login + approval on first run |
| CD-02 | Backend deployed via pipeline | structural | Job graph present (build→whatif→deploy) | **First live deploy** (depends on Phase-2 live infra) |
| OBS-01 | App Insights wired both apps + redaction preserved | unit | `pytest test_telemetry_redaction.py` (span attr w/ email → masked); `az bicep build observability.bicep` | Telemetry visible in App Insights post-deploy |
| OBS-02 | Failure alerts (5xx, orchestration, dep failures) | offline compile | `az bicep build` validates metricAlerts + scheduledQueryRules shapes | Trigger synthetic failure; confirm alert fires |
| OBS-03 | /health + /ready + availability test | unit + compile | `pytest test_ready_endpoint.py` (200 ready / 503 degraded / 401 unauth); bicep build webtest | Webtest green from EU locations |
| OBS-04 | Budget → real sink (Teams/email) | offline compile | `az bicep build budget.bicep` (sub scope); param has webhook+emails | Budget notification received |
| OBS-05 | One-pane dashboard 4 panels | offline | workbook JSON valid; 4 KQL tiles present | Workbook renders in portal |
| OPS-01..05 | 5 runbooks w/ dry-run sections | offline markdown lint + structural | markdownlint; each file has a `## Dry-run / validation` section | Full live runbook execution |

### Sampling Rate
- **Per task commit:** quick run (`pytest -x` on the two new test files) + `az bicep build` on the edited module.
- **Per wave merge:** full pytest suite + bicep build of all three templates + yamllint + markdownlint.
- **Phase gate:** full suite green + all bicep compiles + all linters clean before `/gsd-verify-work`. Live deploy/alert/dashboard/runbook execution are explicit operator checkpoints (CONTEXT execution boundary).

### Wave 0 Gaps
- [ ] `tests/backend/test_ready_endpoint.py` — /ready 200/503/401 (REQ OBS-03), monkeypatch env + Depends override
- [ ] `tests/backend/test_telemetry_redaction.py` — RedactingSpanProcessor.on_end masks PII/secret attrs (REQ OBS-01, AUD-06)
- [ ] `scripts/telemetry.py` (or inline in api_server) — processor + setup_telemetry under test
- [ ] Offline tool installs (Wave 0): `pip install yamllint pymarkdownlnt` (or npm `markdownlint-cli2`); `az bicep` (already used in Phase 2)
- [ ] (Optional) `actionlint` for deeper workflow validation

## Security Domain

> `security_enforcement` treated as enabled (no config override found). This phase is security-sensitive: it opens a telemetry export path (AUD-06) and a CD path to production.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V1 Architecture / SDLC | yes | OIDC CD (no long-lived secret), what-if gate, manual approval = change control |
| V2 Authentication | yes | `/ready` Entra-gated via existing `verify_azure_ad_token`; deploy identity is least-privilege RG-scoped |
| V4 Access Control | yes | Federated subject scoped to `:environment:production`; deploy role scoped to `rg-ac360-prod` only |
| V7 Error/Logging | yes (**central**) | RedactingSpanProcessor + safe_logger.redact in OTel path (AUD-06); `/ready` returns coarse booleans, no detail leak |
| V8 Data Protection / PII | yes | EU-region App Insights + short LAW retention (RGP-04); no PII in spans/logs (redaction) |
| V6 Cryptography | indirect | TLS-only endpoints (existing httpsOnly); webtest SSLCheck:true; no new crypto |

### Known Threat Patterns for {GitHub Actions CD + Azure telemetry}
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Stolen long-lived deploy secret | Spoofing/Elevation | OIDC federated cred — no stored secret; subject-scoped trust |
| Over-privileged deploy identity | Elevation | RG-scoped Contributor only, not subscription Owner |
| Unreviewed prod deploy | Tampering | GitHub `production` Environment required reviewer + what-if diff gate |
| PII/secret leak via telemetry | Information Disclosure | RedactingSpanProcessor (AUD-06); EU-region App Insights; short retention |
| Readiness probe info leak | Information Disclosure | `/ready` Entra-gated, returns booleans only |
| Supply-chain (action/pkg) | Tampering | First-party `Azure/*`/`actions/*`; pin tags; existing CI `pip-audit`/gitleaks |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| App Insights via instrumentation key + opencensus/old SDK | `configure_azure_monitor` (OTel distro), connection string | 2023+ | Use distro + connection string (CONTEXT-locked) |
| Classic (non-workspace) App Insights | Workspace-based App Insights (LAW-backed) | classic retired | observability.bicep creates LAW + workspace-based component |
| Functions Y1 Consumption deploy (external package URL) | Flex Consumption One Deploy + remote build | 2024 (Flex GA) | `functions-action remote-build: true`; no Kudu build flags |
| Stored SP secret for GH Actions | OIDC federated credentials | 2022+ | CONTEXT-locked; no secret in repo |
| O365 connector Teams webhook | Power Automate / Workflows webhook | connectors retiring | Action group `webhookReceivers` shape unchanged; operator supplies durable URL |

**Deprecated/outdated:**
- Classic App Insights, instrumentation keys (use connection string), opencensus exporter (use OTel distro), App Service slots for B1 rollback (not available; use tag redeploy).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `azure-monitor-opentelemetry` bundles `opentelemetry-instrumentation-fastapi` (FastAPI auto-instrumented) | Standard Stack | LOW — if not, add explicit pin + `FastAPIInstrumentor().instrument_app(app)`; both verified-adjacent |
| A2 | Webtest EU `Locations.Id` strings (`emea-nl-ams-azr`, `emea-fr-pra-edge`) are current | Code Ex 11 | LOW — wrong IDs fail at deploy (operator checkpoint); verify location IDs at provisioning |
| A3 | Teams sink via action group `webhookReceivers` works with the operator's webhook type | Code Ex 8 | MED — O365 connector retirement; operator must supply a Power Automate/Workflows URL |
| A4 | Budget % panel cannot be a native App Insights KQL tile (cost data not in AI) | Code Ex 13 | LOW — render as link/markdown or Cost Management tile; doesn't block other panels |
| A5 | what-if job OIDC needs its own federated subject (tag/PR), distinct from `:environment:production` | Pitfall 5 | MED — if mis-set, what-if job 401s; resolve in OPS-01 (one decision) |
| A6 | Connection string treated as non-high-value (plain app setting acceptable; KV-ref optional) | Anti-patterns | LOW — either works; KV-ref aligns with INF-08 preference |

## Open Questions (RESOLVED)

1. **what-if job authentication subject**
   - Known: deploy job uses `environment: production` → subject `repo:ORG/REPO:environment:production`.
   - Unclear: the what-if job (tag trigger, no environment) needs a different federated subject OR should be run under the same environment.
   - **RESOLVED:** documented as an OPS-01 deploy-runbook decision (Plan 03-05); the operator creates the federated credential(s) (`environment:production` for the gated deploy job, plus a tag/PR subject for the what-if job) at setup. Carried as the OPS-01 federated-credential checkpoint — does not block authoring cd-prod.yml.

2. **Teams webhook mechanism**
   - Known: action group `webhookReceivers` + budget `contactGroups` both route to the action group.
   - Unclear: which Teams webhook type (legacy connector vs Power Automate Workflows) the operator will provision.
   - **RESOLVED:** Bicep authors `webhookReceivers` (works for any HTTPS sink); creating the actual Teams webhook (Power Automate Workflows recommended) is an operator-provisioning checkpoint (Plan 03-03). The IaC is connector-agnostic.

3. **Budget %-of-budget dashboard panel**
   - Known: 4 panels required (OBS-05); cost data lives in Cost Management, not App Insights.
   - **RESOLVED:** budget% rendered as a markdown/link tile to the Cost Management budget in the workbook; the other 3 panels (last-24h audits, error rate, p95 latency) are native App Insights KQL (Plan 03-03).

## Environment Availability

| Dependency | Required By | Available (this phase) | Notes / Fallback |
|------------|------------|-----------------------|------------------|
| Live Azure prod RG (rg-ac360-prod) | CD-02 live deploy, live alerts | ✗ (Phase-2 live provisioning pending) | All live steps are operator checkpoints; artifacts produced offline |
| GitHub `production` Environment + secrets | CD-01 approval, OIDC | ✗ (operator setup) | Documented in OPS-01; `cd-prod.yml` authored regardless |
| Entra federated credential | OIDC login | ✗ (operator one-time) | OPS-01 setup section |
| `az bicep` CLI | offline bicep build validation | ✓ (used in Phase 2) | — |
| pytest + asyncio | offline unit tests | ✓ | — |
| yamllint / markdownlint | offline lint | ✗ install in Wave 0 | `pip install yamllint pymarkdownlnt` |
| Teams webhook URL | OBS-04 sink | ✗ (operator) | passed as Bicep param at provisioning |

**Missing dependencies with no fallback (blocking LIVE only, not artifact production):** live prod RG, GitHub Environment/secrets, federated cred, Teams webhook — all operator checkpoints per the CONTEXT execution boundary. **None block this phase's artifact deliverables.**

## Sources

### Primary (HIGH confidence)
- learn.microsoft.com/azure/developer/github/connect-from-azure-openid-connect — OIDC, `azure/login@v2`, `id-token: write`, federated credential (updated 2026-01)
- learn.microsoft.com/azure/azure-functions/functions-how-to-github-actions — `functions-action@v1`, Flex `remote-build`, One Deploy table (updated 2026-03)
- learn.microsoft.com/azure/azure-functions/flex-consumption-how-to — Flex Python always remote build (updated 2026-06)
- learn.microsoft.com/azure/azure-monitor/app/opentelemetry-enable — `configure_azure_monitor`, connection string env var, package name (updated 2026-05)
- learn.microsoft.com/azure/azure-monitor/app/opentelemetry-add-modify — custom `SpanProcessor.on_end`, `span_processors=[...]` (updated 2026-05)
- learn.microsoft.com/azure/azure-functions/opentelemetry-howto — host `telemetryMode`, `PYTHON_APPLICATIONINSIGHTS_ENABLE_TELEMETRY`, duplicate-telemetry guidance (updated 2026-06)
- learn.microsoft.com/azure/templates/microsoft.insights/metricalerts (Bicep) — metricAlerts shape
- learn.microsoft.com/azure/templates/microsoft.consumption/budgets (Bicep) — budgets shape + subscription scope + example
- PyPI `pip index versions azure-monitor-opentelemetry` → 1.8.8 (verified 2026-06-14)
- Context7 /azure-samples/azure-monitor-opentelemetry-python — processor/instrumentation samples

### Secondary (MEDIUM confidence)
- learn.microsoft.com/python/api/overview/azure/monitor-opentelemetry-readme — `instrumentation_options` for FastAPI enable/disable (via WebSearch)

### Tertiary (LOW confidence — flagged in Assumptions Log)
- Webtest EU location IDs; Teams connector retirement timeline (verify at provisioning)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — package + actions verified against PyPI + official docs
- CD (OIDC, Flex deploy, what-if/approval): HIGH — all from current Microsoft Learn
- Observability wiring (OTel + redaction): HIGH — distro + processor pattern cited; redaction reuses existing audited surface
- Bicep observability resources: HIGH for metricAlerts/budgets/actionGroups/components (cited shapes); MEDIUM for webtest location IDs (assumption-flagged)
- Pitfalls: HIGH — Flex remote-build, duplicate telemetry, budget scope all doc-cited

**Research date:** 2026-06-14
**Valid until:** 2026-07-14 (fast-moving Azure surface; re-verify Flex deploy + webtest/Teams-connector specifics at provisioning, ~30 days)
