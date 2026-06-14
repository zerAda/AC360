---
phase: 03-backend-deploy-observability
plan: 03
subsystem: infra / observability
tags: [observability, bicep, app-insights, alerts, budget, finops, OBS-01, OBS-02, OBS-03, OBS-04, OBS-05]
dependency_graph:
  requires:
    - "infra/main.bicep hardened baseline (Phase 02 — apps, Key Vault, storage MI)"
  provides:
    - "infra/observability.bicep — LAW + workspace-based App Insights + action group + alerts + /health webtest + workbook"
    - "infra/workbook-ops.json — one-pane workbook (4 OBS-05 panels)"
    - "infra/budget.bicep — subscription-scoped Cost Management budget"
    - "main.bicep observability module wiring + APPLICATIONINSIGHTS_CONNECTION_STRING (KV ref) on both apps"
    - "main.bicep outputs: appInsightsConnectionString, actionGroupId (for Plan 04 sub-deploy of budget)"
  affects:
    - "Plan 03-04 cd-prod.yml (deploys observability module + separate az deployment sub create for budget.bicep)"
tech_stack:
  added:
    - "Microsoft.OperationalInsights/workspaces@2023-09-01 (PerGB2018, 30d retention)"
    - "Microsoft.Insights/components@2020-02-02 (workspace-based App Insights)"
    - "Microsoft.Insights/actionGroups@2024-10-01-preview (email + Teams webhook)"
    - "Microsoft.Insights/metricAlerts@2018-03-01 (gateway 5xx, function 5xx, webtest availability)"
    - "Microsoft.Insights/scheduledQueryRules@2023-03-15-preview (dependency + Functions/orchestration)"
    - "Microsoft.Insights/webtests@2022-06-15 (Standard /health)"
    - "Microsoft.Insights/workbooks@2023-06-01 (loadTextContent workbook-ops.json)"
    - "Microsoft.Consumption/budgets@2024-08-01 (subscription-scoped)"
  patterns:
    - "Module isolation: all Microsoft.Insights/* kept OUT of main.bicep (PATTERNS.md)"
    - "Cycle break: app IDs passed to module via resourceId() (computed string), not symbolic .id"
    - "Zero-cleartext: App Insights connection string stored as KV secret + @Microsoft.KeyVault ref on both apps"
key_files:
  created:
    - infra/observability.bicep
    - infra/workbook-ops.json
    - infra/budget.bicep
  modified:
    - infra/main.bicep
    - infra/prod.parameters.json
decisions:
  - "App Insights connection string wired as a Key Vault reference (not a plain app setting) to satisfy the INF-08 zero-cleartext gate in validate_infra.ps1 — the plan's <note> explicitly allowed a KV reference"
  - "observability module receives gateway/function IDs via resourceId() (computed) to break the BCP080 cycle (apps consume the module's connectionString output)"
  - "Added a func5xx metric alert (scoped to functionId) — provides metric-based Functions failure coverage AND clears the no-unused-params warning that broke the PowerShell validator"
metrics:
  duration: 18min
  completed: "2026-06-14"
  tasks: 3
  files: 5
---

# Phase 3 Plan 3: Observability-as-Code Summary

Observability-as-code layer for AC360: a workspace-based App Insights component + Log Analytics workspace (the OBS-01 prerequisite main.bicep lacked), an email+Teams action group, failure alerts (gateway/function 5xx + dependency + Functions/orchestration KQL), a Standard /health availability test with alert, a one-pane ops workbook, and a subscription-scoped Cost Management budget — all compiling offline and wired into the hardened infra without disturbing existing security settings.

## What Was Built

- **`infra/observability.bicep`** (OBS-01/02/03/05) — Log Analytics workspace (PerGB2018, 30d EU-short retention per RGP-04) + workspace-based App Insights component (`WorkspaceResourceId` set; classic retired) + action group (email for-loop + Teams `webhookReceivers` gated on `teamsWebhookUrl`) + `gw5xx`/`func5xx` metric alerts + `depFail`/`funcErr` `scheduledQueryRules` + Standard `/health` webtest + `webtestAlert` + workbook (`loadTextContent('workbook-ops.json')`). Exports `connectionString`, `appInsightsId`, `actionGroupId`.
- **`infra/workbook-ops.json`** (OBS-05) — valid Azure Monitor Workbook with the 4 required panels: (1) 24h audits (`customEvents | where name == "ac360_document_access"`), (2) request error rate, (3) p95 latency (`percentile(duration, 95)`), (4) budget % as a markdown/link tile (cost data is not queryable from App Insights — Open Q3).
- **`infra/budget.bicep`** (OBS-04) — `targetScope = 'subscription'` Consumption budget `ac360-prod-monthly`, Actual>80% + Forecasted>100% notifications routing to the action group via `contactGroups` (→ Teams + email).
- **`infra/main.bicep`** (ISOLATED edit) — `module observability` call, a KV secret `APPINSIGHTS-CONNECTION-STRING` (value from module output), `APPLICATIONINSIGHTS_CONNECTION_STRING` wired as a `@Microsoft.KeyVault(...)` reference on BOTH apps, `PYTHON_APPLICATIONINSIGHTS_ENABLE_TELEMETRY=true` on the worker, and new outputs `appInsightsConnectionString` + `actionGroupId`. New params `alertEmails`, `teamsWebhookUrl`. Existing hardened settings (OBO KV ref, AzureWebJobsStorage MI) untouched.
- **`infra/prod.parameters.json`** — added `alertEmails`, `teamsWebhookUrl`, `budgetAmount` (operator fills webhook/email values).

## Task Commits

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | observability.bicep: LAW + App Insights + action group + outputs | b1ee1d0 | infra/observability.bicep |
| 2 | alerts + /health webtest + workbook + workbook-ops.json | 5b55368 | infra/observability.bicep, infra/workbook-ops.json |
| 3 | budget.bicep + main.bicep module/app-setting wiring + prod.parameters.json | b95c71d | infra/budget.bicep, infra/main.bicep, infra/observability.bicep, infra/prod.parameters.json |

## Verification

- `az bicep build -f infra/observability.bicep` → exit 0 (no warnings)
- `az bicep build -f infra/budget.bicep` → exit 0
- `az bicep build -f infra/main.bicep` → exit 0 (no warnings)
- `infra/workbook-ops.json` and `infra/prod.parameters.json` → valid JSON
- `scripts/validate_infra.ps1` → exit 0, "Toutes les assertions par-INF (02/03/04/07/08/09) sont satisfaites."
- `grep -c "Microsoft.Insights/scheduledQueryRules"` → 2 (dependency + Functions/orchestration)
- `grep -c "APPLICATIONINSIGHTS_CONNECTION_STRING" infra/main.bicep` → 2 (both apps)
- `grep "targetScope = 'subscription'" infra/budget.bicep` and `grep "contactGroups"` → present
- OBO KV ref + AzureWebJobsStorage MI settings → still present (hardened posture preserved)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Broke a Bicep dependency cycle (BCP080) between the observability module and the apps**
- **Found during:** Task 3
- **Issue:** Passing `gatewayApp.id`/`functionApp.id` into the module while the apps consume `observability.outputs.connectionString` as an app setting created a circular dependency (`observability` ↔ `gatewayApp`/`functionApp`), failing `az bicep build`.
- **Fix:** Pass the app resource IDs via `resourceId('Microsoft.Web/sites', gatewayName/funcName)` (a computed string, no symbolic dependency). Names are deterministic, so this is sufficient for alert scopes.
- **Files modified:** infra/main.bicep
- **Commit:** b95c71d

**2. [Rule 3 - Blocking / security-gate precedence] App Insights connection string wired as a Key Vault reference instead of a plain app setting**
- **Found during:** Task 3
- **Issue:** `scripts/validate_infra.ps1` (the project's fail-closed INF-08 gate) explicitly treats `APPLICATIONINSIGHTS_CONNECTION_STRING` as secret-like and rejects any literal value (requires `@Microsoft.KeyVault(...)`). The plan's primary wording suggested using the module output directly; the threat model (T-03-08) accepted a plain setting.
- **Fix:** Store the connection string in a `Microsoft.KeyVault/vaults/secrets` resource (`APPINSIGHTS-CONNECTION-STRING`, value from the module output) and reference it on both apps via `@Microsoft.KeyVault(SecretUri=...)`. The plan's `<note>` explicitly listed "Key Vault reference OR the module connectionString output" as acceptable, and the existing hardened security gate takes precedence (CLAUDE.md zero-cleartext invariant). Validator returns exit 0.
- **Files modified:** infra/main.bicep
- **Commit:** b95c71d

**3. [Rule 2 - Missing functionality + unblocks validator] Added a `func5xx` metric alert scoped to the function app**
- **Found during:** Task 3
- **Issue:** The `functionId` param was declared but unused (per the plan's param list), emitting a `no-unused-params` Bicep warning. On Windows PowerShell the validator rendered the warning on stderr as a `NativeCommandError`, and the unused param signaled missing Functions metric coverage.
- **Fix:** Added a `func5xx` `Microsoft.Insights/metricAlerts` (Http5xx, scoped to `functionId`, routing to the action group). This complements the `funcErr` KQL alert with a metric-based path, satisfies OBS-02 Functions-failure coverage, and clears the warning (validator output now clean).
- **Files modified:** infra/observability.bicep
- **Commit:** b95c71d

## Deferred Operator Checkpoint (Task 4 — live provisioning)

Per the execution directive, Task 4 (`checkpoint:human-verify`, Teams webhook + EU webtest location IDs + budget start month) was NOT paused on. The Bicep is authored connector-agnostically and compiles offline; the live confirmations are recorded here as an operator action for provisioning (no live Azure this session):

1. **Teams webhook (OBS-04):** Create a durable inbound webhook (Power Automate / Teams Workflows — NOT a legacy O365 connector, which is retiring). Set `teamsWebhookUrl` in `infra/prod.parameters.json` (or as a deploy secret). The `webhookReceivers` shape already accepts it.
2. **Webtest EU Location IDs (OBS-03, A2):** Confirm the current EU availability-test location IDs and replace the `[ASSUMED]` placeholders (`emea-nl-ams-azr`, `emea-fr-pra-edge`) in `infra/observability.bicep` if Azure has changed them.
3. **Budget start month (OBS-04):** Set `budget.bicep` `timePeriod.startDate` to the first day of the intended billing month (`2026-07-01` placeholder; must be >= the current month at provisioning).
4. **Budget-% workbook tile (OBS-05, Open Q3):** Update the markdown/link tile in `infra/workbook-ops.json` to point at the exact Cost Management budget blade for `ac360-prod-monthly`.

**Resume signal:** Operator types "approved" once the Teams webhook URL is provisioned, EU webtest location IDs are confirmed valid, and the budget start month + budget-% tile link are set.

## Known Stubs

- **`teamsWebhookUrl` / `alertEmails` = empty placeholders** in `infra/prod.parameters.json` — intentional; operator fills live values at provisioning (deferred operator checkpoint above). Not a goal-blocking stub: the Bicep gates `webhookReceivers` on a non-empty `teamsWebhookUrl` (`empty(...) ? [] : [...]`) so the templates deploy validly with or without the webhook, and the operator wires the real URL at go-live.
- **Webtest EU `Locations.Id` placeholders** and **budget `startDate` placeholder** — `[ASSUMED]`-flagged in-template with comments; confirmed at provisioning (Task 4).

## Threat Flags

No new security surface beyond the plan's `<threat_model>`. The connection string was moved to a Key Vault reference (stronger than the accepted T-03-08 disposition); the Teams webhook URL (T-03-09) remains a parameter/secret (not committed); webtest is EU-only over TLS (T-03-12).

## Self-Check: PASSED

- infra/observability.bicep — FOUND
- infra/workbook-ops.json — FOUND
- infra/budget.bicep — FOUND
- .planning/phases/03-backend-deploy-observability/03-03-SUMMARY.md — FOUND
- Commit b1ee1d0 — FOUND
- Commit 5b55368 — FOUND
- Commit b95c71d — FOUND
