---
phase: 02-production-infrastructure-provisioning
plan: 01
subsystem: infra
tags: [bicep, azure, parameters, powershell, iac, validator, static-analysis]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: hardened main.bicep baseline (httpsOnly, TLS1.2, KV RBAC, MI least-privilege) and AUD-04 single-instance pin rationale carried forward to INF-02
provides:
  - "infra/prod.parameters.json — production parameter surface (France Central, prod SKUs, GRS, identity storage, private networking, KV public access Disabled)"
  - "scripts/validate_infra.ps1 — offline fail-closed az bicep build + per-INF (02/03/04/07/08/09) static-assertion gate"
  - "infra/bicepconfig.json — minimal Bicep core linter ruleset (warning level)"
affects: [02-02-main-bicep-extension, 02-04, 02-05, phase-03-backend-observability, provisioning]

# Tech tracking
tech-stack:
  added: [bicepconfig.json linter ruleset]
  patterns:
    - "Offline fail-closed static-assertion validator (collect-violations -> exit 1) modeled on package_release.ps1"
    - "Deferred-assertion gate: exit 0 (yellow) while prod resources absent, fail closed once prod shape compiled"
    - "Staging-safe param opt-in: prod.parameters.json carries every prod delta without touching staging.parameters.json"

key-files:
  created:
    - infra/prod.parameters.json
    - scripts/validate_infra.ps1
    - infra/bicepconfig.json
  modified: [.gitignore]

key-decisions:
  - "docIntelLocation defaults to francecentral in prod.parameters.json; West Europe is the operator-applied fallback if the EU-residency/DocIntel-S0-availability checkpoint (INF-01/INF-04) fails at provisioning"
  - "Validator defers per-INF assertions (exit 0) while main.bicep is still the staging baseline (no B1 plan compiled), so this Wave-0 plan's own verify passes; it fails closed once prod resources land"
  - "validate_infra.ps1 rewritten ASCII-safe (no accented chars/apostrophe-adjacent quotes) so Windows PowerShell 5.1 parses it regardless of codepage/BOM (Rule 1 fix)"
  - "prod.parameters.json declares only the param names plan 02-02 will add to main.bicep; the validator's az bicep build is the intended cross-check against inventing unknown params"

patterns-established:
  - "Per-INF static assertion gate over compiled ARM JSON (B1/capacity=1/alwaysOn, FC1/python3.12, S0/disableLocalAuth, GRS+soft-delete+PITR+versioning+changeFeed+allowSharedKeyAccess=false, MI Durable trio + Cognitive Services User, KV-ref-only secrets + PE + privatelink.vaultcore.azure.net, SharePoint-OBO-is-NOT-a-roleAssignment negative check)"

requirements-completed: [INF-01]

# Metrics
duration: 14min
completed: 2026-06-14
---

# Phase 02 Plan 01: Prod Parameter Surface + Offline Infra Validator Summary

**Production Bicep parameter file (France Central, GRS, identity storage, private networking, KV public access Disabled) plus an offline fail-closed `az bicep build` + per-INF static-assertion PowerShell gate that defers cleanly against the current staging baseline.**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-06-14T00:50:00Z
- **Completed:** 2026-06-14T01:04:00Z
- **Tasks:** 2
- **Files created:** 3

## Accomplishments
- Authored `infra/prod.parameters.json` with the full locked prod parameter surface (INF-01 explicit EU `location=francecentral`, plus every prod-only opt-in: KV `Disabled`, DocIntel `disableLocalAuth`, `Standard_GRS`, identity storage, private networking, Flex sizing, blob/container soft-delete and PITR retention) — `staging.parameters.json` left byte-identical.
- Authored `scripts/validate_infra.ps1`: offline (no `az login`) `az bicep build` compile gate, then per-INF static assertions (INF-02/03/04/07/08/09) over the compiled ARM JSON, fail-closed (collect-violations -> red print -> `exit 1`).
- Validator includes the two posture-critical negative/positive checks from the threat register: SharePoint OBO must NOT appear as a roleAssignment (INF-07, T-02-03) and every secret-like app-setting must be a `@Microsoft.KeyVault(...)` reference with no literal value (INF-08, T-02-01).
- Added `infra/bicepconfig.json` minimal `core` linter ruleset at `warning` so `az bicep build` surfaces lint issues without blocking.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create infra/prod.parameters.json** - `be75e95` (feat)
2. **Task 2: Create scripts/validate_infra.ps1 + infra/bicepconfig.json** - `f54b327` (feat)
3. **Rule 1 fix: ASCII-safe validator + gitignore compiled ARM** - `5438666` (fix)

**Plan metadata:** (final docs commit — see below)

## Files Created/Modified
- `infra/prod.parameters.json` - Production parameter values feeding main.bicep (francecentral, prod SKUs, GRS, identity storage, private networking, KV Disabled, Flex + retention params).
- `scripts/validate_infra.ps1` - Offline `az bicep build` + per-INF static-assertion fail-closed validator (the IaC phase's offline test runner).
- `infra/bicepconfig.json` - Minimal Bicep `core` linter ruleset (warning level).

## Decisions Made
- **DocIntel location:** prod params set `docIntelLocation=francecentral`; West Europe remains the operator fallback if the EU-residency / DocIntel-S0-availability checkpoint fails at provisioning (JSON cannot carry a comment, hence documented here per the plan).
- **Deferred assertions:** the validator detects the prod shape by the presence of a `B1` serverfarm; while main.bicep is still the staging baseline it prints a yellow `[DIFFÉRÉ]` notice and exits 0, satisfying this Wave-0 plan's own verify. Assertions activate and fail closed once plan 02-02 lands the prod resources.
- **Param surface scope:** prod.parameters.json declares only the param names plan 02-02 will add to main.bicep; `az bicep build` (Task 2) is the intended cross-check so no phantom params are introduced.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] validate_infra.ps1 rewritten ASCII-safe for PowerShell 5.1**
- **Found during:** Task 2 (validator verification run)
- **Issue:** The validator committed in `f54b327` used French accented characters and apostrophes (e.g. `l'OBO`, `sécurité`, accented comment-help) and was stored without a UTF-8 BOM. The default shell here is Windows PowerShell 5.1, which decodes BOM-less files with the legacy CP1252 codepage; the multi-byte UTF-8 sequences became mojibake and the apostrophe-adjacent quotes broke the tokenizer (`Parenthèse fermante manquante` / unterminated-string parse errors), causing `exit 1` before any logic ran.
- **Fix:** Rewrote the script with **ASCII-only** text (unaccented French comments/strings, no apostrophes abutting quotes). This is codepage-independent and parses under PS 5.1, PS 7, and Linux CI without relying on a BOM. Assertion logic and structure unchanged.
- **Files modified:** scripts/validate_infra.ps1
- **Verification:** `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate_infra.ps1` runs to completion: "Build OK." + deferred-assertion notice, exit 0. Fail-closed path also verified: a temp B1-shaped bicep (prod shape present, hardening absent) produced 15 violations and exit 1.
- **Committed in:** `5438666` (fix)

**2. [Rule 1 - Bug] Ignore compiled ARM artifact infra/main.json**
- **Found during:** Task 2 (post-build git status check)
- **Issue:** A bare `az bicep build -f infra/main.bicep` (no `--outfile`) writes the compiled ARM to `infra/main.json`, leaving a generated artifact untracked in the working tree.
- **Fix:** Added `infra/main.json` to `.gitignore` (the validator itself already targets `$TEMP`, so no script change needed) and removed the leaked file.
- **Files modified:** .gitignore
- **Committed in:** `5438666` (fix)

---

**Total deviations:** 2 auto-fixed (2 bugs).
**Impact on plan:** Fix 1 was required for the validator to run at all on Windows PowerShell 5.1; Fix 2 prevents a generated artifact from polluting the repo. No scope change — content and assertions are exactly as planned.

## Issues Encountered
- The three primary files (`prod.parameters.json`, `validate_infra.ps1`, `bicepconfig.json`) and an earlier draft SUMMARY existed from a prior session (`be75e95`, `f54b327`, `b19d805`). The committed `validate_infra.ps1` (f54b327) still failed to parse under PS 5.1; this session diagnosed and fixed that (commit `5438666`), then corrected the SUMMARY's encoding-fix description (it had claimed a UTF-8-BOM fix that did not resolve the parse failure; the working fix is ASCII-safe content).
- Console output of the validator renders cleanly now that all text is ASCII.

## Deferred Issues (out of scope for 02-01)
- An uncommitted `infra/main.bicep` change (a partial Flex `functionAppConfig.runtime python 3.12` addition) was found in the working tree. It belongs to the main.bicep prod-shape extension (plans 02-04/02-05), not to 02-01, so it was **left unstaged** and logged in `.planning/phases/02-production-infrastructure-provisioning/deferred-items.md`. It does not affect this plan's verify — the validator still defers (exit 0) because no B1 plan is compiled.

## Threat Surface Verification
- T-02-01 (info disclosure): prod.parameters.json contains zero literal secret values; validator asserts secret app-settings are KV references (INF-08). Mitigated as planned.
- T-02-02 (main.bicep drift): validator is the fail-closed static gate asserting the hardened prod shape (INF-02/09). Mitigated as planned.
- T-02-03 (over-broad MI roles): validator negative-asserts no "SharePoint" roleAssignment and checks for least-privilege data roles (INF-07). Mitigated as planned.
- No new security surface introduced beyond the threat model.

## User Setup Required
None - no external service configuration required for this Wave-0 file-authoring plan. The operator will populate `keyVaultSecretsReaderPrincipalIds` and `gatewayOutboundIps` from live deployment outputs at provisioning time (per infra/README), and confirm the DocIntel/EU-residency checkpoints (INF-01/04/06) at apply.

## Next Phase Readiness
- Prod parameter surface and the offline fail-closed validator are in place; plan 02-02 can now extend main.bicep to the prod shape and use `scripts/validate_infra.ps1` as its offline per-task verify.
- Carried blockers (unchanged): EU residency vs. live GEREP tenant; DocIntel S0 availability in France Central (West Europe fallback wired via `docIntelLocation`); OBO delegated Graph scope list vs. live staging app reg.

## Self-Check: PASSED

- FOUND: infra/prod.parameters.json
- FOUND: scripts/validate_infra.ps1
- FOUND: infra/bicepconfig.json
- FOUND commit be75e95 (Task 1)
- FOUND commit f54b327 (Task 2)
- FOUND commit 5438666 (Rule 1 fix: ASCII-safe validator + gitignore)
- Validator exit 0 against baseline; fail-closed exit 1 verified against B1-shaped bicep; staging.parameters.json unmodified.

---
*Phase: 02-production-infrastructure-provisioning*
*Completed: 2026-06-14*
