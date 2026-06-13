---
phase: 02-production-infrastructure-provisioning
plan: 03
subsystem: infrastructure-provisioning
tags: [powershell, azure-cli, provisioning, pre-flight-gates, fail-closed, INF-01]
requires:
  - "scripts/provision_app_registrations.ps1 (02-02 — apps + OBO secret -> KV)"
  - "infra/main.bicep + infra/prod.parameters.json (02-01 — IaC + prod params)"
provides:
  - "scripts/provision.ps1 — dependency-ordered provisioning orchestrator with fail-closed pre-flight gates (what-if default)"
affects:
  - "Operator provisioning runbook (live run deferred to checkpoint 02-06)"
tech-stack:
  added: []
  patterns:
    - "Blocking fail-closed pre-flight gates (throw before any mutation)"
    - "What-if-by-default; every live action gated behind -not $WhatIfOnly / OPERATOR CHECKPOINT"
    - "Split-script interleave (app-regs scopes early, OBO secret to KV after deploy)"
key-files:
  created:
    - "scripts/provision.ps1"
  modified: []
decisions:
  - "[02-03]: provision.ps1 defaults to -WhatIfOnly=$true; live apply/consent/residency/KV-flip are explicit operator checkpoints — nothing live this phase."
  - "[02-03]: Flex region absence throws (escalate) — no silent EU region substitution; DocIntel S0 absence surfaces westeurope fallback as operator action, not auto-applied (INF-01)."
  - "[02-03]: KV publicNetworkAccess=Disabled flip is NOT auto-executed even with -Apply; surfaced as a second-pass operator checkpoint AFTER PE+VNet confirmed (RESEARCH Pitfall 2)."
metrics:
  duration_min: 12
  completed: 2026-06-13
  tasks: 1
  files: 1
---

# Phase 02 Plan 03: Provisioning Orchestrator Summary

Dependency-ordered Azure provisioning orchestrator (`scripts/provision.ps1`) with blocking fail-closed pre-flight gates (login, subscription match, RP registration, Flex region availability) that defaults to what-if and surfaces every live action as an explicit operator checkpoint.

## What Was Built

`scripts/provision.ps1` (213 lines) — the single entry-point an operator runs to provision AC360 production infrastructure. It encodes INF-01 (EU region/residency) as a blocking pre-flight and the locked dependency order.

### Blocking pre-flight gates (fail-closed, nothing mutates until all pass)
1. Azure CLI presence + authentication (`az account show`, login fallback) — copied from `deploy_azure_ocr.ps1`.
2. Optional `-ExpectedSubscription` match — `throw` on mismatch (T-02-08).
3. Resource Provider registration: `Microsoft.App` (Flex VNet integration) + `Microsoft.KeyVault` (RESEARCH Pitfall 4).
4. Flex Consumption region availability via `az functionapp list-flexconsumption-locations` — `throw` (escalate) if target region absent; no silent substitution (T-02-09 / INF-01).
5. DocIntel S0 region probe + EU residency (M365 geo / Fabric region / Power Platform env) as explicit yellow OPERATOR CHECKPOINTs requiring manual confirmation (T-02-11).

### Dependency-correct sequence (mutating steps gated behind `-not $WhatIfOnly`)
1. Resource Group (`az group create`).
2. Entra app registrations (create + scopes) — note the secret/KV step is deferred to step 5 since KV must exist first.
3. `az deployment group what-if` — ALWAYS run; prints "review the what-if diff and attach as evidence".
4. OPERATOR CHECKPOINT — `az deployment group create` (only when `-not $WhatIfOnly`).
5. OBO secret -> Key Vault (re-invokes `provision_app_registrations.ps1 -KeyVaultName`) + admin-consent (operator).
6. SECOND-PASS OPERATOR CHECKPOINT — KV `publicNetworkAccess=Disabled` flip, ordered strictly AFTER PE+VNet (RESEARCH Pitfall 2); NOT auto-executed.
7. Verify — permission grants, MI role assignments, KV reference resolution.

Default `-WhatIfOnly` mode performs NO mutating `az` call beyond what-if + region probes.

## How It Was Verified

Offline (script does NOT run live this phase — operator runs it at checkpoint 02-06):
- PowerShell AST parse of `scripts/provision.ps1` succeeds (`Parser::ParseFile`).
- Grep confirms presence of `az deployment group what-if`, `list-flexconsumption-locations`, `WhatIfOnly`, `Microsoft.App`.
- Verification harness exited 0 (VERIFY PASS).
- File encoded UTF-8 WITH BOM (BOM bytes 239,187,191) for Windows PowerShell 5.1 compatibility.

## Acceptance Criteria

- [x] Script parses without syntax errors (AST parse succeeds).
- [x] Pre-flight asserts login, optional subscription match, RP registration (Microsoft.App + Microsoft.KeyVault), Flex region availability — fail-closed (`throw`) on failure.
- [x] Default `-WhatIfOnly` runs what-if and performs NO mutating apply; create/consent/KV-flip/residency gated behind `-not $WhatIfOnly` / OPERATOR CHECKPOINT.
- [x] KV `publicNetworkAccess=Disabled` flip sequenced AFTER VNet integration + PE (RESEARCH Pitfall 2).
- [x] Artifact min_lines (90) satisfied — 213 lines.
- [x] key_links present: `az deployment group what-if` against Bicep+prod params; `provision_app_registrations` invocation in dependency order.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The script intentionally does NOT execute live mutations this phase (operator-checkpoint design, not a stub). The KV-flip and residency-confirmation are deliberate operator actions per the threat model (T-02-10, T-02-11), documented in decisions above.

## Self-Check: PASSED

- FOUND: scripts/provision.ps1
- FOUND: commit 5713025 (feat(02-03): add provision.ps1 orchestrator with fail-closed pre-flight gates)
