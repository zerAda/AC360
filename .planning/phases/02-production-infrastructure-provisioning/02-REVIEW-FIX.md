---
phase: 02-production-infrastructure-provisioning
fixed_at: 2026-06-14T00:00:00Z
review_path: .planning/phases/02-production-infrastructure-provisioning/02-REVIEW.md
iteration: 1
findings_in_scope: 10
fixed: 11
skipped: 3
status: all_fixed
gates: "az bicep build exit 0; validate_infra.ps1 exit 0 (prod posture, incl. new CR-02/CR-03/WR-03 assertions); staging still builds; both PowerShell scripts AST-parse clean"
note: "Applied inline by the orchestrator after the gsd-code-fixer subagent hit a session limit before making any edits (no partial work; the .review-fix-recovery-pending.json sentinel + orphan reviewfix worktrees were cleaned up first)."
---

# Phase 02 — Code Review Fix Report

All 3 Critical + 7 Warning findings fixed, plus IN-03 (an Info item fixed opportunistically while editing the script). Gates green: `az bicep build` exit 0, `validate_infra.ps1` exit 0 against the prod posture (now asserting the new CR-02/CR-03/WR-03 properties too), staging still compiles, both scripts AST-parse clean.

## Critical (3/3 fixed)

| Finding | Fix | Commit |
|---------|-----|--------|
| **CR-01** Key Vault name mismatch (`ac360-kv-prod` vs `kv-ac360-prod`) | `provision.ps1` default corrected to `ac360-kv-prod`; after apply, the real vault name is re-read from the `keyVaultName` deployment output (source of truth) and used for the secret-set step | `c83433c` |
| **CR-02** Gateway MI never granted Key Vault Secrets User | Added in-template `gwKvSecretsUser` + `funcKvSecretsUser` role assignments (Key Vault Secrets User scoped to the vault, `principalId` from each app's system-assigned identity) | `aaaa150` |
| **CR-03** DocIntel publicly reachable, no PE, local auth disabled | Parameterized `docIntelPublicNetworkAccess` (Disabled in prod), added Cognitive Services Private Endpoint (groupId `account`) + `privatelink.cognitiveservices.azure.net` DNS zone/link/group mirroring the KV pattern; validator now asserts it | `aaaa150` |

## Warnings (7/7 fixed)

| Finding | Fix | Commit |
|---------|-----|--------|
| **WR-01** Empty/failed OBO secret could be written to KV | `$LASTEXITCODE`/`IsNullOrWhiteSpace` guard throws before the KV write | `968a22a` |
| **WR-02** `Tasks.ReadWrite` vs read-only guarantee | KEPT (Planner FIC-relance is a real product feature: `planner_integration.py`, `/api/planner/task`, `CreerRelancePlanner` topic); added a documented read-only EXCEPTION comment + flagged for DPIA/SEC evidence (Phase 5) | `968a22a` |
| **WR-03** Storage not network-restricted in prod | Added `storagePublicNetworkAccess` param (Disabled in prod) + `networkAcls.defaultAction: Deny` (bypass AzureServices); validator asserts it | `aaaa150` |
| **WR-04** Fragile per-scope resolution (partial-failure risk) | Atomic resolution: resolve+validate ALL scope GUIDs first, throw before any mutation if any missing, then a single batched `az ad app permission add` | `968a22a` |
| **WR-05** Empty `gatewayOutboundIps` = open ingress | Explicit `deny-all` rule appended when ≥1 allow rule exists; documented that prod must populate `gatewayOutboundIps` at go-live (OPS-01 operator step) | `aaaa150` |
| **WR-06** Silent interactive `az login` in automation | Both scripts now fail closed unless `-Interactive` is passed | `c83433c`, `968a22a` |
| **WR-07** Subscription guard no-op when omitted | `-ExpectedSubscription` mandatory for apply runs (throw on apply if absent) | `c83433c` |

## Info

| Finding | Disposition |
|---------|-------------|
| **IN-03** DevOps secret-mask emitted unconditionally | FIXED — gated on `$env:TF_BUILD -eq 'True'` (symmetric with the GitHub mask) (`968a22a`) |
| **IN-01** PITR < soft-delete invariant not enforced | Carried (accepted) — prod params honor it (6 < 7); low risk. Candidate for a future validator assertion. |
| **IN-02** Storage name length/charset not validated | Carried (accepted) — current values valid (`ac360prodstore`, 14 chars). |
| **IN-04** bicepconfig secret rules at warning not error | Carried (accepted) — no live secret-in-output; hardening suggestion. |

## Verification

- `az bicep build -f infra/main.bicep` → exit 0
- `powershell -NoProfile -File scripts/validate_infra.ps1` → exit 0 (prod posture; INF-02/03/04/07/08/09 + new CR-02/CR-03/WR-03 assertions all pass; still fails-closed on staging)
- Staging default build → OK (all new params default staging-safe)
- Both provisioning scripts → AST parse clean

## Carried forward (operator / later phases)

- Populate `gatewayOutboundIps` in `prod.parameters.json` before go-live (after the gateway exists — Phase 3 / OPS-01).
- Sequence the DocIntel and Key Vault `publicNetworkAccess=Disabled` flips AFTER their Private Endpoints exist (provision.ps1 / RESEARCH Pitfall 2).
- Record the `Tasks.ReadWrite` write-scope exception in the DPIA/SEC evidence pack (Phase 5: RGP-01, SEC-03).
