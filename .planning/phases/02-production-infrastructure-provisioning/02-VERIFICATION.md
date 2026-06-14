---
status: human_needed
phase: 02-production-infrastructure-provisioning
verified: 2026-06-14
method: inline goal-backward verification (orchestrator) — offline artifact gates + code-review fixes; live actions deferred to operator per the locked execution boundary
requirements: [INF-01, INF-02, INF-03, INF-04, INF-05, INF-06, INF-07, INF-08, INF-09]
gates: "az bicep build exit 0; validate_infra.ps1 exit 0 (prod posture, INF-02/03/04/07/08/09 + CR-02/CR-03/WR-03); staging builds; both provisioning scripts AST-parse clean"
---

# Phase 2 Verification — Production Infrastructure Provisioning

**Phase goal:** A production resource group exists in an EU region with production-tier SKUs, wired identity and admin consent, secrets in Key Vault, and the minimal network hardening — all provisioned in the dependency-correct order before any backend deploy.

**Verdict: HUMAN_NEEDED.** All provisioning **artifacts** (Bicep IaC, prod parameters, app-registration/consent script, provisioning orchestrator, offline validator) are complete, offline-verified, and code-review-clean (3 critical + 7 warnings fixed). The phase goal's *live* half — actually creating the resource group, granting admin consent, and confirming EU residency / Fabric grant — requires a live Azure subscription + GEREP tenant and is queued as blocking operator checkpoints (Plan 02-06). This matches the milestone-locked execution boundary ("produce artifacts; live actions are operator checkpoints").

## Offline-verifiable requirements (artifacts COMPLETE)

| Req | Evidence | Status |
|-----|----------|--------|
| INF-01 | `prod.parameters.json` location=francecentral (explicit); provision.ps1 residency pre-flight gates | ✅ artifact |
| INF-02 | main.bicep gwPlan B1 capacity=1, gatewayApp alwaysOn + gunicorn `--workers 1` (AUD-04 pin preserved) | ✅ artifact |
| INF-03 | main.bicep FC1/FlexConsumption + functionAppConfig (python 3.12); new app (Y1→Flex unsupported) | ✅ artifact |
| INF-04 | main.bicep DocIntel S0 + disableLocalAuth=true (+ publicNetworkAccess=Disabled, CR-03) | ✅ artifact |
| INF-05 | provision_app_registrations.ps1: API app no secret; OBO secret → Key Vault only | ✅ artifact |
| INF-06 | admin-consent issued by script; **live grant + no-AADSTS65001 = operator checkpoint (02-06)** | ◷ operator |
| INF-07 | main.bicep MI role loop: Durable trio + Cognitive Services User + KV Secrets User (gw+func, CR-02); SharePoint OBO NOT a role | ✅ artifact |
| INF-08 | KV Private Endpoint + VNet + privatelink DNS; zero cleartext (@Microsoft.KeyVault refs); storage networkAcls Deny (WR-03); DocIntel PE (CR-03) | ✅ artifact |
| INF-09 | Storage GRS + soft-delete + PITR + versioning/changeFeed + allowSharedKeyAccess=false + identity AzureWebJobsStorage + unique prod Task Hub | ✅ artifact |

Gates: `az bicep build` exit 0; `validate_infra.ps1` exit 0 against the prod posture (asserts INF-02/03/04/07/08/09 plus the new CR-02/CR-03/WR-03 properties); staging still compiles; both PowerShell scripts AST-parse clean.

## Code review

3 Critical + 7 Warning findings (02-REVIEW.md) all resolved (02-REVIEW-FIX.md): CR-01 KV-name mismatch, CR-02 gateway MI KV access, CR-03 public DocIntel, WR-01..07. Each would have impaired or broken the production deployment; the validator now guards against regression.

## Human verification required (operator — Plan 02-06, runbook in 02-06-SUMMARY.md)

1. **EU residency + France Central availability** — confirm M365 geo / Fabric region / Power Platform region EU; Flex + DocIntel S0 availability (West Europe DocIntel fallback if needed). [INF-01]
2. **Bicep what-if** against the live subscription as provisioning evidence (no live apply this phase — apply is Phase 3 / OPS-01).
3. **OBO admin consent** in the prod tenant + reconcile delegated scopes against live staging + verify no AADSTS65001; confirm the Fabric/OneLake read-grant mechanism for the Functions MI. [INF-06]

These are blocking for **go-live** but do not block the artifact deliverables or downstream artifact-production phases.
