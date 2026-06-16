---
phase: 2
slug: production-infrastructure-provisioning
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-13
validated: 2026-06-17
---

# Phase 2 — Validation Strategy

> IaC has no unit-test framework; "validation" = Bicep static analysis + what-if + script self-checks. Each INF requirement is mechanically validated WITHOUT a live subscription where possible; live-only checks are operator checkpoints.
> **Validated 2026-06-17** (audit-and-flip): `az bicep build` exit 0 (main/observability/budget); offline INF assertions green. Live INF-06/residency/what-if/Fabric-grant remain operator checkpoints (legitimately not offline-automatable).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `az bicep build` (compile/lint, offline) + `az deployment group what-if` (dry-run, needs login) + PowerShell `-WhatIf`/Pester for script logic |
| **Config file** | none (optional `bicepconfig.json` linter rules — not adopted) |
| **Quick run command** | `az bicep build --file infra/main.bicep` |
| **Full suite command** | `az bicep build --file infra/main.bicep` + `scripts/validate_infra.ps1` (prod posture) |
| **Estimated runtime** | build ~5s (offline); what-if ~30–60s (operator, live) |

---

## Sampling Rate

- **After every task commit:** `az bicep build --file infra/main.bicep` (offline, must pass)
- **After every wave:** build + the static-assertion validator over compiled JSON (per-INF property checks) + script AST parse
- **Phase gate:** build green + a documented `what-if` run (operator, live sub) reviewed and attached as evidence before `/gsd-verify-work`. Live apply is a separate operator checkpoint (Phase 3).
- **Max feedback latency:** ~5s offline

---

## Per-Requirement Validation Map

| Req | Behavior | Type | Automated Command / Check | Offline? | Status |
|-----|----------|------|---------------------------|----------|--------|
| INF-01 | RG + explicit `location` everywhere | static + build | build passes; `prod.parameters.json` sets `location=francecentral` | ✅ | ✅ green (offline) |
| INF-02 | B1 + capacity=1 + alwaysOn | static | `gwPlan.sku.name=='B1'`, `capacity==1`, `alwaysOn==true`, gunicorn `--workers 1` | ✅ | ✅ green |
| INF-03 | Flex app correct shape | build + what-if | `az bicep build` accepts `functionAppConfig`; what-if shows FC1 + python 3.12 | build ✅ / what-if live | ✅ green (build) / ◷ what-if operator |
| INF-04 | DocIntel S0 + disableLocalAuth | static | `docIntel.sku.name=='S0'`, `disableLocalAuth==true` | ✅ | ✅ green |
| INF-05 | App regs (API no secret; OBO secret→KV) | script self-check | `provision_app_registrations.ps1` AST/dry-run: API app no credential; OBO secret only `keyvault secret set` | ✅ (logic) | ✅ green |
| INF-06 | Admin consent + no AADSTS65001 | runtime (operator) | post-consent `az ad app permission list-grants`; OBO smoke = no 65001 | ✗ live-only | ◷ operator checkpoint |
| INF-07 | MI role assignments wired | static + what-if | role GUIDs present + scoped; SharePoint OBO is delegated consent | build ✅ | ✅ green (build) |
| INF-08 | KV refs + PE + VNet + zero cleartext | static + grep | every secret uses `@Microsoft.KeyVault(`; PE + `privatelink.vaultcore.azure.net` + DNS group | ✅ | ✅ green |
| INF-09 | GRS + soft-delete + PITR + identity storage + unique hub | static | `Standard_GRS`; deleteRetention + restorePolicy; `allowSharedKeyAccess==false`; identity AzureWebJobsStorage; prod hub ≠ staging | ✅ | ✅ green |

---

## Wave 0 Requirements

- [x] `infra/prod.parameters.json` — prod param values (exists)
- [x] `scripts/provision.ps1` — orchestrator + pre-flight gates (exists)
- [x] `scripts/provision_app_registrations.ps1` — app-reg/consent (exists)
- [x] Static-assertion validator — `scripts/validate_infra.ps1` asserting the per-INF properties (closes the "IaC has no test runner" gap for Nyquist)
- [ ] Optional: `bicepconfig.json` linter rules + arm-ttk — **not adopted** (optional; `az bicep build` lint + validate_infra.ps1 deemed sufficient for an internal one-team launch)
- [x] No package install needed

---

## Manual-Only Verifications (operator checkpoints)

| Behavior | Req | Why Manual | Test Instructions |
|----------|-----|------------|-------------------|
| OBO delegated Graph scope set + admin consent | INF-06 | Needs live tenant + admin rights | Run app-reg script, `az ad app permission admin-consent`, confirm `list-grants` shows expected scopes, OBO smoke yields no AADSTS65001 |
| EU residency (M365 geo, Fabric region, DocIntel S0 / Flex availability in France Central) | INF-01/03/04 | Live tenant + region probe | `provision.ps1` pre-flight `az` probes; West Europe fallback if DocIntel S0 absent; escalate if Flex absent |
| `what-if` dry-run + live `az deployment` | INF-01..09 | Needs login + subscription | Operator runs what-if, reviews, then applies via `provision.ps1` |
| Fabric/OneLake read grant for Functions MI | INF-07 | Workspace-level grant, not Azure RBAC | Grant MI workspace read in Fabric portal/API |

---

## Validation Sign-Off

- [x] All tasks have offline `az bicep build` verify or a Wave 0 dependency
- [x] Static-assertion validator covers INF-01,02,04,07,08,09 offline
- [x] Live-only checks (INF-06, what-if/apply, residency, Fabric grant) documented as operator checkpoints
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-06-17 (audit-and-flip; offline IaC gates green, live actions operator-gated).

## Validation Audit 2026-06-17

| Metric | Count |
|--------|-------|
| Requirements | 9 (INF-01..09) |
| Automated & green (offline) | 8 (INF-01/02/03-build/04/05/07/08/09) |
| Manual-only (operator) | INF-06 + the live what-if/residency/Fabric-grant halves of INF-01/03/07 |
| Gaps found | 0 |
| Tests generated this audit | 0 |

Evidence: `az bicep build` exit 0 for main/observability/budget; `validate_infra.ps1` prod-posture assertions (per Phase-2 verification). IaC has no pytest surface — offline build+validator IS the automated gate. No nyquist-auditor spawn required.
