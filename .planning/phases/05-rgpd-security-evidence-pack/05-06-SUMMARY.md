---
phase: 05-rgpd-security-evidence-pack
plan: 06
subsystem: governance
tags: [rgpd, gdpr, dsr, data-residency, evidence-pack]
requires:
  - docs/governance/RGP-03-retention-policy.md
  - docs/governance/RGP-04-pii-in-logs-statement.md
  - infra/main.bicep
  - infra/prod.parameters.json
  - .planning/phases/02-production-infrastructure-provisioning/02-06-SUMMARY.md
provides:
  - docs/governance/RGP-05-DSR-procedure.md
  - docs/governance/RGP-06-data-residency.md
affects:
  - docs/governance/RGP-01-record-of-processing.md
  - docs/governance/RGP-02-DPIA.md
tech-stack:
  added: []
  patterns:
    - "Erasure-by-design via read-only + ephemeral 30-day TTL (RGP-03)"
    - "Two-column residency split: Bicep-verifiable-now vs operator-checkpoint"
key-files:
  created:
    - docs/governance/RGP-05-DSR-procedure.md
    - docs/governance/RGP-06-data-residency.md
  modified: []
decisions:
  - "DSR access/erasure satisfied largely automatically by read-only + TTL; manual action limited to optional hashed audit-trail purge"
  - "Rectification/erasure of source content routed to system of record (SharePoint/ARTUS), not AC360"
  - "RGP-06 tenant-level residency (M365/Fabric/Power Platform/webtest) left as operator checkpoints, NOT asserted as confirmed"
metrics:
  duration: ~12m
  completed: 2026-06-15
---

# Phase 5 Plan 06: RGP-05 DSR Procedure + RGP-06 Data Residency Summary

DSR procedure (Art. 15/16/17/21 + Art. 12) leveraging AC360's read-only + ephemeral-TTL architecture for erasure-by-design, plus an EU data-residency confirmation that honestly separates Bicep-verifiable-now regions from the four tenant-level operator checkpoints.

## What Was Built

### Task 1 — RGP-05 DSR procedure (`docs/governance/RGP-05-DSR-procedure.md`)
French governance doc documenting how each data-subject right is satisfied given AC360's architecture:
- **Access (Art. 15):** AC360 holds no canonical client record; 4-field hashed audit trail has no raw PII to export; access to content routes to the system of record. No over-disclosure (T-05-19).
- **Rectification (Art. 16):** AC360 is read-only / never writes → corrections happen upstream in SharePoint/ARTUS.
- **Erasure (Art. 17) — erasure-by-design:** 30-day TTL auto-deletion (RGP-03, two enforcement points) + honest ~37-day effective window; Log Analytics purge path documented for the hashed audit trail if required.
- **Objection (Art. 21):** feature-flag block.
- Art. 12 one-month (extendable +2) timeline, identity-verification intake (anti-spoofing T-05-18), DPO/operator roles, and a request log.

### Task 2 — RGP-06 EU data-residency confirmation (`docs/governance/RGP-06-data-residency.md`)
French governance doc with a TWO-COLUMN structure:
- **Vérifiable maintenant (Bicep `location`):** gateway App Service, gateway plan, Functions, Functions plan, Storage (GRS intra-EU), Key Vault, Document Intelligence (francecentral; westeurope EU fallback), Log Analytics, Application Insights — all `francecentral` per `infra/prod.parameters.json`, cited with real resource names + line numbers.
- **Point de contrôle opérateur (tenant live, NOT confirmed):** M365 tenant geo, Fabric capacity region, Power Platform/Copilot Studio environment region, and the `[ASSUMED]` webtest `Locations` — each aggregating the Phase 2 (Plan 02-06 Checkpoint 1) operator checkpoint and deferred to Plan 05-07.
- Hors-UE transfers = néant on the Bicep surface; conclusion explicitly marks residency as verifiable-now for Azure-IaC and pending-operator for the four tenant surfaces.

## Verification Results

Plan `<verify>` blocks and acceptance criteria all pass:
- RGP-05: `RGP-05`×2, `Art. 15`×2, `Art. 16`×2, `Art. 17`×2, `RGP-03`×8, read-only/TTL ×15, `## ` headings ×10 (≥3). SimpleMatch verify tokens all present → count ≥4.
- RGP-06: `RGP-06`×2, `francecentral`×10, `Fabric`×4, `opérateur`×12, `M365|Fabric|Power Platform`×6 (≥2), operator-column ×14, `02-06|Phase 2`×9. SimpleMatch verify tokens all present → count ≥3.

RGP-06 does NOT assert live M365/Fabric/Power Platform/webtest residency as confirmed — all four remain operator checkpoints aggregating Phase 2, confirmed at Plan 05-07 (satisfies T-05-20 / RESEARCH Pitfall 5).

## Deviations from Plan

None - plan executed exactly as written. Both files authored to the plan's exact filenames and section structure; all cited paths, resource names, line numbers, and the `francecentral` / `westeurope`-fallback Bicep values verified against the live repo before citing.

## Threat Model Coverage

- **T-05-18 (Spoofing, DSR intake):** RGP-05 §3 requires identity verification before any access/erasure action.
- **T-05-19 (Info Disclosure, over-disclosure):** RGP-05 §1/§5 — AC360 holds only hashed audit fields, no raw PII; routes content to source.
- **T-05-20 (Repudiation, residency from Bicep alone):** RGP-06 two-column split; tenant rows are operator checkpoints, not confirmed.
- **T-05-SC (package installs):** none in this phase — no-op.

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary surfaces introduced (documentation only).

## Known Stubs

None — both deliverables are complete governance documents. RGP-06's four operator-checkpoint rows are intentional deferrals (live-tenant verification, confirmed at Plan 05-07), explicitly documented as such rather than stubbed/falsely confirmed.

## Notes for Orchestrator

This executor session has no reliable shell; files are authored to disk and verified via grep. Orchestrator should verify + commit:
- `docs/governance/RGP-05-DSR-procedure.md`
- `docs/governance/RGP-06-data-residency.md`
- `.planning/phases/05-rgpd-security-evidence-pack/05-06-SUMMARY.md`
