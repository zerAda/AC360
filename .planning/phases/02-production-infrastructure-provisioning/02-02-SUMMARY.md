---
phase: 02
plan: 02
subsystem: infrastructure-provisioning
tags: [entra-id, app-registration, obo, graph-delegated, admin-consent, key-vault, powershell]
requires:
  - "Key Vault (target for OBO-CLIENT-SECRET; provisioned via Bicep in 02-01/02-03)"
  - "Authenticated operator with Global/Privileged Role Admin (admin-consent)"
provides:
  - "scripts/provision_app_registrations.ps1 — idempotent az-based app-reg + delegated-scope + admin-consent + secret→KV script"
  - "Entra objects (operator-created at runtime): AC360-API-prod (no secret), AC360-OBO-prod (secret in KV)"
  - "Key Vault secret name: OBO-CLIENT-SECRET"
affects:
  - "prod.parameters.json / gateway app settings (consume API_APP_ID, OBO_APP_ID, @Microsoft.KeyVault OBO secret ref)"
  - "Operator checkpoint plan 02-04 (live admin-consent grant verification)"
tech-stack:
  added: []
  patterns:
    - "Idempotent check-then-create by displayName (az ad app list --filter)"
    - "Runtime delegated-scope GUID resolution from live Graph SP (Get-Scope via az ad sp show)"
    - "Secret hygiene: az keyvault secret set 1>$null then $secret=$null; never to file/log"
key-files:
  created:
    - "scripts/provision_app_registrations.ps1"
  modified: []
decisions:
  - "Delegated Graph scope GUIDs resolved at runtime from the live Graph SP (00000003-...), never hardcoded — tenant-correct and idempotent (resolves Open Q1 mechanism; live scope-set still operator-verified at 02-04)"
  - "API audience app carries NO credential (asserted offline); only the OBO confidential client holds a secret, written exclusively to Key Vault"
  - "admin-consent is issued by the script but the live grant requires Global/Privileged Role Admin — verification deferred to blocking operator checkpoint in plan 02-04 (az ad app permission list-grants)"
  - "Audit.Trigger scope exposed idempotently via a temp JSON manifest (api=@file) only when absent — no secret transits the temp file"
metrics:
  duration_min: 9
  completed: 2026-06-13
---

# Phase 2 Plan 2: Entra App Registration Provisioning Script Summary

Idempotent az-driven PowerShell script that provisions the two production Entra app registrations (API audience app with no secret; OBO confidential client with secret routed only to Key Vault), resolves delegated Microsoft Graph scope GUIDs at runtime from the live tenant, requests them on the OBO app, and issues admin consent — with zero secret leakage to logs or files.

## What Was Built

`scripts/provision_app_registrations.ps1` (169 lines, UTF-8 with BOM for Windows PowerShell 5.1 French comment-help compatibility):

1. **az presence + login guard** — copied from `deploy_azure_ocr.ps1` (lines 23-36): checks `az` is installed, runs `az account show` / `az login` fallback.
2. **API audience app (INF-05)** — `AC360-API-prod`, check-then-create by displayName, sets `identifier-uris api://<appId>`, exposes the `Audit.Trigger` delegated scope (idempotent, only when absent). Issues NO `credential reset` — the API app holds no secret (T-02-07).
3. **OBO confidential client (INF-05/06)** — `AC360-OBO-prod`, check-then-create; ensures the SP exists (`az ad sp create` if missing — prevents AADSTS65001, T-02-06); `Get-Scope` resolves each delegated scope GUID from the live Graph SP (`az ad sp show --id 00000003-0000-0000-c000-000000000000`); loops `Files.Read.All, Sites.Read.All, Tasks.ReadWrite, offline_access, User.Read` via `az ad app permission add`. Generates the secret via `az ad app credential reset`, masks it for CI, writes it via `az keyvault secret set ... 1>$null`, then zeroes `$secret` (T-02-04).
4. **admin-consent (INF-06)** — issues `az ad app permission admin-consent`; prints a yellow warning that the live grant requires a privileged operator and must be re-verified via `az ad app permission list-grants`.
5. **Machine-readable output** — prints `API_APP_ID` and `OBO_APP_ID` (never the secret) for wiring into prod params/app settings.

## Verification Results

Plan automated verify (offline AST parse + secret-hygiene grep) — PASS:
- `AST_OK (errors=0)` — script parses without syntax errors.
- `hasKV=True` — writes the OBO secret via `az keyvault secret set`.
- `hasGraph=True` — references the Graph well-known appId.
- `noEchoSec=True` — no `Write-Host $secret`.
- `noEnv=True` — no `.env` write (the `.env` substring was removed from a comment to satisfy the strict hygiene grep).
- `noApiCred=True` — no `credential reset --id $apiAppId` (API app has no secret).
- `hasConsent=True` — issues `az ad app permission admin-consent`.
- `hasRuntimeScope=True` — resolves scope GUIDs at runtime via `az ad sp show --id $graph`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed `.env` substring from a French comment**
- **Found during:** Task 1 verification
- **Issue:** A comment read "aucune écriture .env" — the literal `.env` substring tripped the plan's strict `-notmatch '\.env'` secret-hygiene grep, failing the offline verify even though no `.env` write exists.
- **Fix:** Reworded the comment to "aucune écriture sur disque" (no disk write). Behavior unchanged; the script still never writes any file other than Key Vault.
- **Files modified:** scripts/provision_app_registrations.ps1
- **Commit:** c15d4ba

**2. [Rule 2 - Critical] Idempotent SP existence check before scopes/consent**
- **Found during:** Task 1 implementation
- **Issue:** The OBO app needs a service principal to exist before admin-consent, otherwise the first OBO token exchange fails with AADSTS65001 (RESEARCH Pitfall 5).
- **Fix:** Added `az ad sp list --filter "appId eq '$oboAppId'"` check + `az ad sp create` when absent, before permission add / admin-consent.
- **Files modified:** scripts/provision_app_registrations.ps1
- **Commit:** c15d4ba

### Implementation note (not a deviation)
- The `Audit.Trigger` scope is exposed by passing `api=@<tempfile>` to `az ad app update`. The temp JSON manifest contains no secret (only scope metadata) and is deleted immediately. The plan said "set api.oauth2PermissionScopes"; the temp-file mechanism is the cross-platform-reliable way to do that with az.

## Authentication Gates

None encountered during authoring. The script itself contains the operator auth touchpoints (its own `az login` guard, and the admin-consent step requiring Global/Privileged Role Admin) — these are runtime operator concerns deferred to the live-execution checkpoint in plan 02-04, not gates for this authoring plan.

## Known Stubs

None. The script is complete and authors all required imperative steps; the only deliberately deferred action is the live admin-consent grant against the GEREP prod tenant (operator checkpoint, plan 02-04), which is intentional and documented in the script and plan.

## Self-Check: PASSED
- FOUND: scripts/provision_app_registrations.ps1
- FOUND: commit c15d4ba (feat(02-02): add idempotent Entra app-reg provisioning script)
