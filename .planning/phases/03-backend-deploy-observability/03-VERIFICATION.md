---
status: human_needed
phase: 03-backend-deploy-observability
verified: 2026-06-14
method: inline goal-backward verification (orchestrator) — offline gates green; live deploy/alerting/runbook execution deferred to operator per the locked execution boundary
requirements: [CD-01, CD-02, OBS-01, OBS-02, OBS-03, OBS-04, OBS-05, OPS-01, OPS-02, OPS-03, OPS-04, OPS-05]
gates: "pytest 204 passed/1 skipped; az bicep build exit 0 (main/observability/budget); validate_infra.ps1 exit 0 (prod posture); cd-prod.yml valid YAML; 5 runbooks with dry-run sections; code review clean (0 critical/0 warning, 2 info)"
---

# Phase 3 Verification — Backend Deploy & Observability

**Phase goal:** The fixed backend is deployed to production through a real, gated CD pipeline, with monitoring, alerting, a one-pane dashboard, and the five solo-operator runbooks live and tested before any end-to-end test.

**Verdict: HUMAN_NEEDED.** All deploy/observability/ops **artifacts** are complete, offline-verified, and code-review-clean. The goal's *live* half — the first deploy through the pipeline, OIDC federated-credential creation, live alert/dashboard/budget provisioning, the Teams webhook, and full live runbook execution — requires live Azure + the Phase 2 infra provisioned, and is queued as operator checkpoints. This matches the milestone execution boundary.

## Offline-verifiable requirements (artifacts COMPLETE)

| Req | Evidence | Status |
|-----|----------|--------|
| CD-01 | `.github/workflows/cd-prod.yml`: OIDC `id-token: write`, `environment: production` approval, Bicep what-if gate; no stored SP secret; pinned actions | ✅ artifact |
| CD-02 | Pipeline build→whatif→deploy graph; gateway `azure/webapps-deploy@v3`, Functions `Azure/functions-action@v1 remote-build:true`; **first live deploy = operator checkpoint** | ◷ operator |
| OBS-01 | `scripts/telemetry.py` (configure_azure_monitor + RedactingSpanProcessor, AUD-06 preserved) wired in gateway startup + function_app; `host.json telemetryMode: OpenTelemetry`; App Insights + Log Analytics added to main.bicep; conn string via KV ref | ✅ artifact |
| OBS-02 | `observability.bicep`: metricAlerts (gw 5xx, func 5xx) + scheduledQueryRules (dep failures) + action group | ✅ artifact |
| OBS-03 | `/ready` (Entra-gated, 200/503, no leak) + `/health` liveness; Standard webtest + alert in observability.bicep; `test_ready_endpoint.py` green | ✅ artifact |
| OBS-04 | `budget.bicep` (subscription-scoped) → action group (email + Teams webhookReceiver, param-driven); **Teams webhook provisioning = operator checkpoint** | ✅ artifact / ◷ webhook |
| OBS-05 | `workbook-ops.json` (4 panels: 24h audits, error rate, p95, budget% link tile) in observability.bicep | ✅ artifact |
| OPS-01 | `docs/production/runbooks/01-deploy.md` (Bicep apply + Functions + App Service + OIDC federated creds + KV-ref verification + Phase 2 checkpoints folded in) | ✅ artifact |
| OPS-02 | `02-rollback.md` (<10-min redeploy-previous-known-good; git tag marker; no slots on B1) | ✅ artifact |
| OPS-03 | `03-secret-rotation.md` (per secret incl. OBO app-registration; expiry table) | ✅ artifact |
| OPS-04 | `04-incident-triage.md` (alert → cause → first-action decision tree) | ✅ artifact |
| OPS-05 | `05-killswitch.md` (feature_flags / admin_controls disable audit/OCR/RAG or block user/team) | ✅ artifact |

Gates: pytest 204 passed/1 skipped; `az bicep build` exit 0 (main/observability/budget); `validate_infra.ps1` exit 0 (prod posture); cd-prod.yml valid YAML; all 5 runbooks carry a `## Dry-run / validation` section.

## Code review

Inline review (03-REVIEW.md): **clean** — 0 critical, 0 warning, 2 info (telemetry private-attr mutation; sequence-valued attribute redaction). The plaintext-secret scanner false-positive on the /ready fixture was fixed.

## Human verification required (operator)

1. **First live deploy** via cd-prod.yml (needs Phase 2 live infra + GitHub OIDC/secrets + `production` Environment + reviewer); confirm `/health` 200 and `/ready` over Entra TLS. [CD-02, OPS-01]
2. **OIDC federated-credential creation** (deploy `:environment:production` + what-if tag subject). [CD-01]
3. **Live alerting/dashboard/budget**: trigger synthetic failures → alerts fire; webtest green from EU locations; workbook renders; budget notification received; provision the Teams webhook. [OBS-02/03/04/05]
4. **Full live runbook execution** once each (deploy, rollback, rotation, triage, kill-switch). [OPS-01..05]

These gate go-live but do not block downstream artifact-production phases.
