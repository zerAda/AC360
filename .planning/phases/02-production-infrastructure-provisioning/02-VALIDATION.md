---
phase: 2
slug: production-infrastructure-provisioning
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-13
---

# Phase 2 — Validation Strategy

> IaC has no unit-test framework; "validation" = Bicep static analysis + what-if + script self-checks. Each INF requirement is mechanically validated WITHOUT a live subscription where possible; live-only checks are operator checkpoints.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `az bicep build` (compile/lint, offline) + `az deployment group what-if` (dry-run, needs login) + PowerShell `-WhatIf`/Pester for script logic |
| **Config file** | none (optional `bicepconfig.json` linter rules — Wave 0 nice-to-have) |
| **Quick run command** | `az bicep build -f infra/main.bicep` |
| **Full suite command** | `az bicep build -f infra/main.bicep && az deployment group what-if -g rg-ac360-prod -f infra/main.bicep -p @infra/prod.parameters.json` |
| **Estimated runtime** | build ~5s (offline); what-if ~30–60s (operator, live) |

---

## Sampling Rate

- **After every task commit:** `az bicep build -f infra/main.bicep` (offline, must pass)
- **After every wave:** build + the static-assertion validator over compiled JSON (per-INF property checks) + script Pester (if added)
- **Phase gate:** build green + a documented `what-if` run (operator, live sub) reviewed and attached as evidence before `/gsd-verify-work`. Live apply is a separate operator checkpoint (Phase 3).
- **Max feedback latency:** ~5s offline

---

## Per-Requirement Validation Map

| Req | Behavior | Type | Automated Command / Check | Offline? |
|-----|----------|------|---------------------------|----------|
| INF-01 | RG + explicit `location` everywhere | static + build | build passes; `prod.parameters.json` sets `location=francecentral`; no implicit `resourceGroup().location` where explicit needed | ✅ |
| INF-02 | B1 + capacity=1 + alwaysOn | static | `gwPlan.sku.name=='B1'`, `capacity==1`, `gatewayApp alwaysOn==true`, gunicorn `--workers 1` present | ✅ |
| INF-03 | Flex app correct shape | build + what-if | `az bicep build` accepts `functionAppConfig`; what-if shows FC1 + python 3.12 | build ✅ / what-if live |
| INF-04 | DocIntel S0 + disableLocalAuth | static | `docIntel.sku.name=='S0'`, `disableLocalAuth==true` | ✅ |
| INF-05 | App regs (API no secret; OBO secret→KV) | script self-check | `provision_app_registrations.ps1` Pester/dry-run: API app no credential; OBO secret only `keyvault secret set`, never echoed | ✅ (logic) |
| INF-06 | Admin consent + no AADSTS65001 | runtime (operator) | post-consent `az ad app permission list-grants`; OBO smoke = no 65001 | ✗ live-only |
| INF-07 | MI role assignments wired | static + what-if | role GUIDs present + scoped; SharePoint OBO is NOT a roleAssignment (delegated consent); what-if shows assignments | build ✅ |
| INF-08 | KV refs + PE + VNet + zero cleartext | static + grep | every secret uses `@Microsoft.KeyVault(`; no literal secrets; PE + `privatelink.vaultcore.azure.net` + DNS group; KV `publicNetworkAccess=Disabled` in prod | ✅ |
| INF-09 | GRS + soft-delete + PITR + identity storage + unique hub | static | `Standard_GRS`; blob+container deleteRetention + restorePolicy + versioning + changeFeed; `allowSharedKeyAccess==false`; `AzureWebJobsStorage__credential==managedidentity`; prod hub ≠ staging | ✅ |

---

## Wave 0 Requirements

- [ ] `infra/prod.parameters.json` — new file (prod param values)
- [ ] `scripts/provision.ps1` — orchestrator + pre-flight gates (new)
- [ ] `scripts/provision_app_registrations.ps1` — app-reg/consent (new)
- [ ] Static-assertion validator — a small script (PowerShell or `jq` over `az bicep build` JSON) asserting the per-INF properties above (closes the "IaC has no test runner" gap for Nyquist). **Recommended.**
- [ ] Optional: `bicepconfig.json` linter rules + arm-ttk
- [ ] No package install needed

---

## Manual-Only Verifications (operator checkpoints)

| Behavior | Req | Why Manual | Test Instructions |
|----------|-----|------------|-------------------|
| OBO delegated Graph scope set + admin consent | INF-06 | Needs live tenant + admin rights | Run app-reg script, `az ad app permission admin-consent`, confirm `az ad app permission list-grants` shows expected scopes, OBO smoke yields no AADSTS65001 |
| EU residency (M365 geo, Fabric region, DocIntel S0 / Flex availability in France Central) | INF-01/03/04 | Live tenant + region probe | `provision.ps1` pre-flight `az` probes; if DocIntel S0 absent in France Central → West Europe fallback; if Flex absent → escalate |
| `what-if` dry-run + live `az deployment` | INF-01..09 | Needs login + subscription | Operator runs what-if, reviews, then applies via `provision.ps1` |
| Fabric/OneLake read grant for Functions MI | INF-07 | Workspace-level grant, not Azure RBAC | Grant MI workspace read in Fabric portal/API |

---

## Validation Sign-Off

- [ ] All tasks have offline `az bicep build` verify or a Wave 0 dependency
- [ ] Static-assertion validator covers INF-01,02,04,07,08,09 offline
- [ ] Live-only checks (INF-06, what-if/apply, residency, Fabric grant) documented as operator checkpoints
- [ ] No watch-mode flags
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
