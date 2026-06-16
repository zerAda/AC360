---
phase: 3
slug: backend-deploy-observability
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-14
validated: 2026-06-17
---

# Phase 3 — Validation Strategy

> Each CD/OBS/OPS requirement is validated OFFLINE where possible (pytest, az bicep build, yamllint, markdownlint); live deploy/alert/dashboard/runbook execution are operator checkpoints per the locked execution boundary.
> **Validated 2026-06-17** (audit-and-flip): pytest green (`test_ready_endpoint` 4, `test_telemetry_redaction` 3), `az bicep build` exit 0 (main/observability/budget). Live deploy/alerting/runbook execution remain operator checkpoints.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (`setup.cfg` asyncio_mode auto) |
| **Config file** | `setup.cfg`; per-dir `conftest.py` adds `scripts/` to path |
| **Quick run command** | `python -m pytest tests/backend/test_ready_endpoint.py tests/backend/test_telemetry_redaction.py -x` |
| **Full suite command** | `python -m pytest tests/backend tests/azure_functions tests/security -q` |
| **Offline infra** | `az bicep build --file infra/main.bicep` + `--file infra/observability.bicep` + `--file infra/budget.bicep`; `scripts/validate_infra.ps1` |
| **Offline workflow** | `yamllint .github/workflows/cd-prod.yml` (optional `actionlint`) |
| **Offline runbooks** | structural section checks on `docs/production/runbooks/*.md` |

---

## Sampling Rate

- **After every task commit:** quick run (pytest -x on the two new test files) + `az bicep build` on the edited module.
- **After every wave:** full pytest suite + bicep build of all three templates + yamllint + section checks.
- **Phase gate:** full suite green + all bicep compiles + linters clean before `/gsd-verify-work`. Live deploy/alert/dashboard/runbook execution are operator checkpoints.
- **Max feedback latency:** ~30s offline.

---

## Per-Requirement Validation Map

| Req | Behavior | Type | Offline command / check | Status |
|-----|----------|------|--------------------------|--------|
| CD-01 | cd-prod.yml: OIDC + what-if gate + env approval | lint + structural | grep `id-token: write`, `environment: production`, `what-if` | ✅ green (structural) / ◷ first OIDC login operator |
| CD-02 | Backend deployed via pipeline | structural | Job graph present (build→whatif→deploy) | ◷ first live deploy operator |
| OBS-01 | App Insights wired both apps + redaction preserved | unit + compile | `pytest test_telemetry_redaction.py` (3 passed); `az bicep build observability.bicep` | ✅ green |
| OBS-02 | Failure alerts (5xx, orchestration, dep failures) | compile | `az bicep build` validates metricAlerts + scheduledQueryRules | ✅ green (compile) / ◷ live fire operator |
| OBS-03 | /health + /ready + availability test | unit + compile | `pytest test_ready_endpoint.py` (4 passed: 200/503/401); bicep webtest | ✅ green |
| OBS-04 | Budget → real sink (Teams/email) | compile | `az bicep build budget.bicep` (sub scope) | ✅ green (compile) / ◷ webhook + notification operator |
| OBS-05 | One-pane dashboard 4 panels | offline | workbook JSON valid; 4 KQL tiles present | ✅ green (compile) / ◷ portal render operator |
| OPS-01..05 | 5 runbooks w/ dry-run sections | structural | each file has a `## Dry-run / validation` section | ✅ green (artifact) / ◷ full live execution operator |

---

## Wave 0 Requirements

- [x] `tests/backend/test_ready_endpoint.py` — /ready 200/503/401 (OBS-03) — **4 passed**
- [x] `tests/backend/test_telemetry_redaction.py` — RedactingSpanProcessor.on_end masks PII/secret attrs (OBS-01, AUD-06) — **3 passed**
- [x] `scripts/telemetry.py` — processor + setup_telemetry under test (exists)
- [x] Offline tooling: `az bicep build` (used); markdown section checks
- [ ] (Optional) `actionlint` for deeper workflow validation — **not adopted** (yamllint/structural grep sufficient)

---

## Manual-Only Verifications (operator checkpoints)

| Behavior | Req | Why Manual | Test Instructions |
|----------|-----|------------|-------------------|
| First live deploy via cd-prod.yml | CD-02 | Needs Phase-2 live infra + GitHub OIDC/secrets + approval | Run cd-prod.yml; confirm /health 200 + /ready over Entra TLS |
| OIDC federated credential creation | CD-01 | Live tenant admin | `az ad app federated-credential create` subject `repo:ORG/REPO:environment:production` (deploy runbook OPS-01) |
| Alerts fire / availability test green / workbook renders / budget notifies | OBS-02/03/04/05 | Needs live resources + traffic | Trigger synthetic failures; confirm alert + webtest + workbook + budget notification |
| Teams webhook provisioning | OBS-04 | Power Automate / connector setup | Create the inbound webhook, store URL as a param/secret |
| Full live runbook execution | OPS-01..05 | Needs live prod | Execute each runbook end-to-end once against prod |

---

## Validation Sign-Off

- [x] All auto tasks have offline pytest/bicep/lint verify or a Wave 0 dependency
- [x] Wave 0 creates the two test files + telemetry module
- [x] Live-only checks documented as operator checkpoints
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-06-17 (audit-and-flip; offline gates green, live deploy/alerting operator-gated).

## Validation Audit 2026-06-17

| Metric | Count |
|--------|-------|
| Requirements | 12 (CD-01/02, OBS-01..05, OPS-01..05) |
| Automated & green (offline) | OBS-01/03 (pytest); CD-01 + OBS-02/04/05 compile/structural; OPS-01..05 artifact |
| Manual-only (operator) | CD-02 first deploy; live fire of OBS-02/03/04/05; full OPS-01..05 execution |
| Gaps found | 0 |
| Tests generated this audit | 0 |

Evidence: `test_ready_endpoint.py` 4 passed, `test_telemetry_redaction.py` 3 passed; `az bicep build` exit 0 for main/observability/budget. No nyquist-auditor spawn required.
