# Phase 3: Backend Deploy & Observability - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous)

<domain>
## Phase Boundary

Produce the production deployment + observability layer for AC360: a real gated CD pipeline (`cd-prod.yml`), Application Insights wired on both apps, failure + availability + budget alerting, a one-pane ops dashboard, and the five solo-operator runbooks. Covers OBS-01..05, CD-01..02, OPS-01..05.

**Execution boundary (milestone decision):** This phase produces all artifacts (pipeline YAML, App Insights wiring code + the real exporter, health/ready endpoints, Bicep alerts/dashboard/budget, runbooks). The **first live deploy**, OIDC federated-credential creation, and live alert/dashboard provisioning are **operator checkpoints** — they depend on the Phase 2 infra being provisioned live (still pending). Nothing is deployed live this session.

Depends on: Phase 1 (fixed backend), Phase 2 (prod infra artifacts; live provisioning pending). Out of scope: Copilot publish (Phase 4), E2E test (Phase 6), SLO/error-budget (v2 OBS-06).

</domain>

<decisions>
## Implementation Decisions

### CD Pipeline & Deploy
- Auth: **OIDC federated credentials** (azure/login@v2, no stored SP secret) + a setup runbook documenting federated-credential creation (operator step).
- Approval: GitHub **`production` Environment** with a required reviewer; a Bicep **what-if** job runs before apply (gate).
- Deploy mechanism: gateway → Azure **App Service** deploy; Functions → **Flex remote-build zip deploy**; infra via `az deployment group` what-if → apply.
- Execution boundary: produce `cd-prod.yml` + the deploy runbook (OPS-01); the **first real deploy** is an operator checkpoint (needs Phase 2 infra live + GitHub OIDC/secrets configured).
- Analog: extend the patterns in `.github/workflows/cd-staging.yml`.

### Observability
- App Insights: wire **`configure_azure_monitor`** (azure-monitor-opentelemetry) on BOTH the gateway and the Functions app — this lands the real exporter Phase 1 deferred and replaces the inert `audit_trail` seam gate. **Adds the `azure-monitor-opentelemetry` pip dependency** (the one Phase 1 explicitly deferred to OBS-01). OBS-01.
- Readiness: add **`/ready`** (readiness — checks Key Vault reference resolution + Fabric/OCR reachability, Entra-gated TLS); keep existing `/health` as the unauthenticated liveness 200. OBS-03.
- Alerts + dashboard as code: **Bicep** metric/log alert rules (gateway 5xx, Functions/orchestration errors, OCR/Fabric/Graph dependency failures) + an **action group**; an **Azure Monitor Workbook** (Bicep) for the one-pane dashboard. OBS-02, OBS-05.
- Availability: a **Standard availability test** (Bicep) against `/health` + its alert. OBS-03.

### Runbooks & FinOps
- Runbooks: **`docs/production/runbooks/*.md`** — 5 files, solo-operator decision-tree style: deploy (OPS-01), rollback (OPS-02), secret rotation (OPS-03), incident triage (OPS-04), feature-flag kill-switch (OPS-05).
- Rollback: **redeploy the previous known-good release** (git tag = known-good marker; <10-min path via pipeline re-run). B1 has NO deployment slots (slots need S1+, which would break the AUD-04 single-instance pin), so slot-swap is NOT used. OPS-02.
- Budget: **Azure Cost Management budget (Bicep) + action group → Teams webhook** (both sinks). OBS-04.
- "Tested": each runbook includes a **dry-run / validation section** exercisable offline; the full live test is an operator checkpoint.

### Claude's Discretion
- Exact alert thresholds, workbook query layout, action-group naming, pip version pin, and runbook section granularity are at Claude's discretion, consistent with `infra/` + `docs/` conventions.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.github/workflows/cd-staging.yml` + `ci.yml` — CD/CI analogs for `cd-prod.yml`.
- `scripts/api_server.py` — `/health` exists (line 672); add `/ready`. `AppInsightsMiddleware`/telemetry gate at line 96 (does NOT currently export — wire the real exporter).
- `scripts/audit_trail.py` — the inert APPINSIGHTS-gated emit seam (Phase 1); OBS-01 attaches `configure_azure_monitor` so the seam exports for real.
- `infra/main.bicep` — extend with alerts, action group, availability test, workbook, budget (or a linked module).
- `docs/production/` — existing prod docs dir; runbooks go under `docs/production/runbooks/`.

### Established Patterns
- Bicep parameterized, staging-safe defaults; role-assignment + resource patterns from Phase 2.
- PowerShell ops scripts house-style (az login guard, fail-closed) — for any deploy helper.
- safe_logger redaction mandatory on telemetry (AUD-06) — the real exporter must keep redaction.

### Integration Points
- `cd-prod.yml` consumes the Phase 2 Bicep + `provision.ps1`; deploys to the Phase 2 resources.
- App Insights connection string flows via Key Vault reference / app setting (Phase 2 wiring) into both apps; `configure_azure_monitor` reads it.
- Alerts/dashboard/budget reference the Phase 2 resource IDs (gateway, function, storage, docintel).

### Reference
- App Insights instrumentation guidance available via the Azure `appinsights-instrumentation` skill / Microsoft Learn.

</code_context>

<specifics>
## Specific Ideas

- Telemetry must remain PII/secret-redacted through the real exporter (preserve AUD-06 redaction in the OpenTelemetry path).
- Rollback known-good marker = an immutable git tag per release (e.g. `prod-YYYYMMDD-N`).
- Dashboard panels: last-24h audits, error rate, p95 latency, budget % (the four OBS-05 panels).

</specifics>

<deferred>
## Deferred Ideas

- SLO + error-budget definition (OBS-06, v2).
- Automated secret-expiry calendar/alerting (OPS-06, v2).
- Deployment slots / blue-green (requires S1+ plan; conflicts with B1 single-instance pin).
- Actual live deploy, OIDC federated-credential creation, live alert/dashboard provisioning — operator checkpoints (depend on Phase 2 live infra).

</deferred>
