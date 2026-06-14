---
phase: 3
slug: backend-deploy-observability
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-14
---

# Phase 3 — Validation Strategy

> Each CD/OBS/OPS requirement is validated OFFLINE where possible (pytest, az bicep build, yamllint, markdownlint); live deploy/alert/dashboard/runbook execution are operator checkpoints per the locked execution boundary.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (`setup.cfg` asyncio_mode auto) |
| **Config file** | `setup.cfg`; per-dir `conftest.py` adds `scripts/` to path |
| **Quick run command** | `python -m pytest tests/backend/test_ready_endpoint.py tests/backend/test_telemetry_redaction.py -x` |
| **Full suite command** | `python -m pytest tests/ -q` (env `TENANT_ID=test_tenant CLIENT_ID=test_client PYTHONPATH=scripts`) |
| **Offline infra** | `az bicep build -f infra/main.bicep` + `-f infra/observability.bicep` + `-f infra/budget.bicep`; `scripts/validate_infra.ps1` |
| **Offline workflow** | `yamllint .github/workflows/cd-prod.yml` (optional `actionlint`) |
| **Offline runbooks** | `markdownlint-cli2 docs/production/runbooks/**.md` or `pymarkdownlnt scan` |

---

## Sampling Rate

- **After every task commit:** quick run (pytest -x on the two new test files) + `az bicep build` on the edited module.
- **After every wave:** full pytest suite + bicep build of all three templates + yamllint + markdownlint.
- **Phase gate:** full suite green + all bicep compiles + all linters clean before `/gsd-verify-work`. Live deploy/alert/dashboard/runbook execution are operator checkpoints.
- **Max feedback latency:** ~30s offline.

---

## Per-Requirement Validation Map

| Req | Behavior | Type | Offline command / check | Live (operator checkpoint) |
|-----|----------|------|--------------------------|----------------------------|
| CD-01 | cd-prod.yml: OIDC + what-if gate + env approval | lint + structural | `yamllint cd-prod.yml`; grep `id-token: write`, `environment: production`, `what-if` | First OIDC login + approval |
| CD-02 | Backend deployed via pipeline | structural | Job graph present (build→whatif→deploy) | **First live deploy** (needs Phase-2 live infra) |
| OBS-01 | App Insights wired both apps + redaction preserved | unit + compile | `pytest test_telemetry_redaction.py`; `az bicep build observability.bicep` | Telemetry visible post-deploy |
| OBS-02 | Failure alerts (5xx, orchestration, dep failures) | compile | `az bicep build` validates metricAlerts + scheduledQueryRules | Trigger synthetic failure; alert fires |
| OBS-03 | /health + /ready + availability test | unit + compile | `pytest test_ready_endpoint.py` (200/503/401); bicep build webtest | Webtest green from EU locations |
| OBS-04 | Budget → real sink (Teams/email) | compile | `az bicep build budget.bicep` (sub scope); webhook+emails param | Budget notification received |
| OBS-05 | One-pane dashboard 4 panels | offline | workbook JSON valid; 4 KQL tiles present | Workbook renders in portal |
| OPS-01..05 | 5 runbooks w/ dry-run sections | markdown lint + structural | markdownlint; each file has a `## Dry-run / validation` section | Full live runbook execution |

---

## Wave 0 Requirements

- [ ] `tests/backend/test_ready_endpoint.py` — /ready 200/503/401 (OBS-03), monkeypatch env + Depends override
- [ ] `tests/backend/test_telemetry_redaction.py` — RedactingSpanProcessor.on_end masks PII/secret attrs (OBS-01, AUD-06)
- [ ] `scripts/telemetry.py` (or inline) — processor + setup_telemetry under test
- [ ] Offline tool installs: `pip install yamllint pymarkdownlnt` (or npm markdownlint-cli2); `az bicep` (already used)
- [ ] (Optional) `actionlint` for deeper workflow validation

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

- [ ] All auto tasks have offline pytest/bicep/lint verify or a Wave 0 dependency
- [ ] Wave 0 creates the two test files + telemetry module
- [ ] Live-only checks documented as operator checkpoints
- [ ] No watch-mode flags
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
