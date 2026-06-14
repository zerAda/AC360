# Phase 02 — Deferred / Out-of-Scope Items

Items discovered during execution that are outside the current plan's scope.
Logged per the executor scope-boundary rule (do NOT auto-fix unrelated churn).

## Discovered during 02-01 execution (2026-06-14)

- **Uncommitted `infra/main.bicep` change (`functionAppConfig.runtime python 3.12`)**
  - **Status:** Left UNSTAGED — out of scope for plan 02-01 (this plan only authors
    `infra/prod.parameters.json`, `scripts/validate_infra.ps1`, `infra/bicepconfig.json`).
  - **Belongs to:** the main.bicep prod-shape extension (plans 02-04 / 02-05). The change
    is a partial Flex `functionAppConfig` addition with no accompanying B1 plan / S0 /
    GRS / PE wiring, so it is incomplete prod-shape work.
  - **Why not committed here:** scope boundary — committing another plan's partial work
    under a 02-01 commit would misattribute it. It also does NOT affect 02-01's verify:
    the validator still defers (exit 0) because no B1 serverfarm is compiled.
  - **Action for the owning plan (02-04/02-05):** finish the main.bicep prod-shape
    extension, then commit the complete change; `scripts/validate_infra.ps1` will then
    activate the per-INF assertions and must pass fail-closed.
