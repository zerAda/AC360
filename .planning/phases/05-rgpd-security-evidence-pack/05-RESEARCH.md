# Phase 5: RGPD & Security Evidence Pack - Research

**Researched:** 2026-06-15
**Domain:** GDPR/RGPD compliance evidence + security-review documentation + 2 small IaC/code retention deliverables (Azure Bicep / Python)
**Confidence:** HIGH (Bicep idioms verified on Microsoft Learn + against the live repo; CNIL/EDPB/GDPR frameworks cited from EDPB/WP248/gdpr-info; OWASP LLM Top 10 2025 cited)

## Summary

Phase 5 is ~80% documentation/evidence assembly and ~20% two small enforcement deliverables. The two code/IaC deliverables (RGP-03 retention enforcement, RGP-04 telemetry retention) are concrete and verifiable offline; everything else is markdown evidence sourced from artifacts that **already exist in the repo** (`docs/security/SECURITY_POSTURE.md`, per-phase `<threat_model>` blocks, `CONCERNS.md`, existing tests, Bicep `location` values, `scripts/telemetry.py`).

Two findings materially shape the plan and were NOT visible from the phase brief:

1. **`.github/dependabot.yml` already exists** with the `pip` ecosystem (root + `/azure_functions` + `/scripts`) plus `github-actions`. SEC-04 is therefore **mostly done** — the remaining work is (a) documenting the PyJWT/deltalake pin policy and (b) optionally adding a `groups`/security-only tightening, not creating the file from scratch. `[VERIFIED: codebase grep]`
2. **`scripts/cleanup_local_artifacts.ps1` already exists but is a destructive full-wipe** of `jobs/`, `logs/`, `Archives_Documentaires/` — it deletes *everything*, not artifacts *older than N days*. It is a dev-hygiene tool, **not** the RGP-03 TTL enforcement. RGP-03 needs a NEW age-based cleaner; do not repurpose the wipe script (it would delete in-flight jobs). `[VERIFIED: codebase read]`

Two more grounding facts:
- **Log Analytics retention is already wired** in `infra/observability.bicep` at `retentionInDays: 30`. RGP-04 wants **90 days**. The fix is a one-line value change promoted to a parameter (`logAnalyticsRetentionDays = 90`). For AC360's **workspace-based** App Insights component (`WorkspaceResourceId: law.id`), retention is governed by the **workspace** `retentionInDays`, NOT by the component — so the component needs no retention property. `[VERIFIED: observability.bicep read + Microsoft Learn]`
- **No storage `managementPolicies` resource exists** in `infra/main.bicep`. RGP-03 adds one. `[VERIFIED: main.bicep read]`

**Primary recommendation:** Treat Phase 5 as four lanes — (A) SEC docs (pure markdown from existing sources), (B) RGP-03 storage lifecycle Bicep rule + a new timer-triggered Python TTL cleaner (testable), (C) RGP-04 one-line LA retention bump-to-param + a PII-in-logs statement confirming `RedactingSpanProcessor`, (D) RGPD governance docs (DPIA/Art.30/DSR/residency) drafted autonomously with DPO sign-off as the hard external gate before Phase 6. Lock the CONTEXT decisions; do not re-open the WORM/immutability question (already framed honestly in SECURITY_POSTURE.md §7).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Blob retention enforcement (job/OCR/FIC blobs in Durable storage) | Database/Storage (Azure Storage `managementPolicies`) | — | Server-side, identity-free, runs without compute; data-minimization at the storage tier is the canonical GDPR enforcement |
| Ephemeral local artifact TTL (`JOBS_BASE_DIR` files) | API/Backend (Azure Functions timer trigger, Python) | Ops (documented manual fallback) | `JOBS_BASE_DIR` lives on the Functions VM's local/ephemeral FS, not in blob storage — storage lifecycle rules cannot reach it; needs in-app scheduled deletion |
| Telemetry/log retention (Log Analytics) | Observability (Bicep `Microsoft.OperationalInsights/workspaces`) | — | Workspace `retentionInDays` is the single retention control for workspace-based App Insights |
| PII redaction in telemetry | API/Backend (`scripts/telemetry.py RedactingSpanProcessor`) | — | Already implemented Phase 3; Phase 5 only documents/confirms it |
| Security/RGPD evidence docs | Governance (markdown `docs/security/`, `docs/governance/`) | — | Documentation tier; sourced from existing artifacts + DPO sign-off |

## Standard Stack

This phase introduces **no new runtime dependencies** (CLAUDE.md constraint: "no rewrites or new frameworks"; locked decision: "deploys what exists"). All deliverables use the existing stack.

### Core (already present — reused, not added)
| Library / Tool | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Bicep CLI (`az bicep build`) | existing | Compile/validate RGP-03 storage rule + RGP-04 retention change | Project's IaC validator (`validate_infra.ps1`) already uses it |
| Azure Functions (Python v2 model) | runtime 2.0 | Timer-triggered TTL cleaner for `JOBS_BASE_DIR` (RGP-03) | Already the backend runtime; `function_app.py` is the v2 host |
| pytest 8.0.0+ / pytest-asyncio | existing | Unit-test the TTL cleanup logic (pure function, no SDK) | Project test framework; matches the `audit_pipeline` dependency-injection testability pattern |
| `scripts/safe_logger.py` / `scripts/telemetry.py` | existing | RGP-04 evidence (`redact`, `RedactingSpanProcessor`) | Single audited redaction surface (AUD-06) |
| markdownlint (offline) | n/a (lint-only) | Structural lint of evidence docs | Lightweight doc gate; no runtime impact |

### Supporting (CNIL / EDPB / OWASP reference material — documents, not packages)
| Source | Purpose | When to Use |
|---------|---------|-------------|
| EDPB/WP248 rev.01 9 criteria | RGP-02 DPIA "≥2-of-9" assessment | DPIA necessity section |
| GDPR Art. 30(1) | RGP-01 record-of-processing field list | Art. 30 entry |
| GDPR Art. 15/16/17 + Art. 12 | RGP-05 DSR procedure | DSR doc |
| OWASP Top 10 for LLM Applications 2025 | SEC-03 threat-coverage matrix | OWASP/LLM risk → mitigation → test rows |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Timer-triggered Functions cleaner (RGP-03 local TTL) | Documented-manual operator cleanup only | Manual is cheaper but non-enforcing — fails the RGP-03 word "enforcement"; recommend the timer with a documented-manual fallback in the runbook |
| Storage `managementPolicies` (server-side) | App-side blob deletion loop | Server-side lifecycle is zero-compute, audit-friendly, and the canonical GDPR pattern; do not hand-roll blob iteration |
| Per-table `totalRetentionInDays` for the audit-trail table | Workspace-level `retentionInDays` only | Per-table is only needed if the audit trail must outlive 90 days for compliance; CONTEXT locks 90-day short retention, so workspace-level is sufficient — note per-table as an option for the DPO |

**Installation:** None. No `pip install` / `npm install` in this phase.

## Package Legitimacy Audit

> Not applicable — this phase installs **no external packages**. All code reuses the existing, already-vetted dependency set (`requirements.txt`, unchanged). slopcheck gate is therefore a no-op for Phase 5. Any SEC-04 work *documents* the existing pin policy; it does not add packages.

## Architecture Patterns

### System Architecture Diagram (PII / retention flow — for SEC-01 reuse)

```
                         ┌─────────────────────────────────────────────┐
   Teams / Copilot user  │             TRUST BOUNDARY: Entra ID SSO     │
        │  (JWT RS256)    │                                             │
        ▼                 │   ┌──────────────┐    OBO (user-delegated)  │
  ┌───────────┐  JWKS     │   │  FastAPI      │  ───────────────────►   │
  │  Gateway  │◄──────────┼───│  gateway      │      Microsoft Graph    │
  │ (B1, 1 wk)│           │   │  api_server   │      (SharePoint RBAC)  │
  └─────┬─────┘           │   └──────┬───────┘                          │
        │ start_new                  │ X-MS-Graph-Token (never persisted)│
        ▼                            ▼                                   │
  ┌──────────────────────────────────────────────┐                     │
  │  Durable Functions (Flex) — single activity    │   PII enters here  │
  │  download → OCR(DocIntel) → Fabric → FIC        │◄── client document │
  │  writes to JOBS_BASE_DIR/{document_id} (local) │                     │
  └───────┬───────────────────────────┬────────────┘                    │
          │ ephemeral local artifacts  │ Durable state blobs            │
          ▼                            ▼                                 │
   ┌────────────────┐         ┌──────────────────┐                      │
   │ JOBS_BASE_DIR  │  RGP-03 │ Azure Storage    │  RGP-03              │
   │ (VM-local FS)  │◄─TTL────│ (job/OCR/FIC blob)│◄─managementPolicy── │
   │ timer cleaner  │  cleaner│  delete @ 30d     │  delete @ 30d        │
   └────────────────┘         └──────────────────┘                      │
          │                            │                                 │
          ▼ telemetry (redacted)       ▼                                 │
   ┌──────────────────────────────────────────────┐                     │
   │ App Insights (workspace-based) → Log Analytics │  RGP-04            │
   │ RedactingSpanProcessor strips PII before export│  retentionInDays=90│
   │ Audit trail: {user_id_hash, doc_id, ts, verdict}│ (no raw PII)      │
   └────────────────────────────────────────────────┘─────────────────┘

  Retention enforcement points (RGP-03/04):
   ① Storage blobs  → managementPolicies delete @ jobRetentionDays (30)
   ② JOBS_BASE_DIR  → timer-trigger Python cleaner @ jobRetentionDays (30)
   ③ Log Analytics  → workspace retentionInDays = 90 (short, EU region)
```

### Recommended Evidence-Pack File Layout (Claude's discretion — consistent with existing `docs/`)
```
docs/
├── security/
│   ├── SECURITY_POSTURE.md          # EXISTS (Phase 1) — SEC source, do not overwrite
│   ├── GUARDRAILS_VALIDATION.md     # EXISTS (Phase 4) — SEC-03 LLM source
│   ├── SECURITY_AUDIT_STAGING.md    # EXISTS — re-validation source
│   ├── SEC-01-architecture-dataflow.md   # NEW: Mermaid diagrams, PII flow, trust boundaries
│   ├── SEC-02-authn-authz.md             # NEW: Entra/JWT/OBO/IDOR/read-only + test links
│   ├── SEC-03-threat-coverage-matrix.md  # NEW: STRIDE + OWASP LLM Top 10 → mitigation → test
│   ├── SEC-04-dependency-posture.md       # NEW: Dependabot (already on) + PyJWT/deltalake pin policy
│   └── SEC-05-accepted-risk-register.md   # NEW: CONCERNS.md classified must-fix-done vs accepted-deferred
└── governance/
    ├── GOVERNANCE.md                # EXISTS — UPDATE its §4 RGPD claim (see Pitfall 1)
    ├── RGP-01-record-of-processing.md     # NEW: Art. 30 draft (DPO finalizes)
    ├── RGP-02-DPIA.md                      # NEW: full DPIA + CNIL ≥2-of-9 (DPO signs — hard gate)
    ├── RGP-04-pii-in-logs-statement.md    # NEW: redaction + RedactingSpanProcessor + 90d retention
    ├── RGP-05-DSR-procedure.md             # NEW: access/erasure/rectification procedure
    └── RGP-06-data-residency.md            # NEW: aggregates Bicep locations + Phase 2 operator checkpoints
```
(`RGP-03` is code/IaC, not a governance doc — its policy text can live as a short section in `RGP-05` or a dedicated `RGP-03-retention-policy.md`; the *enforcement* lands in `infra/main.bicep` + a new cleaner.)

### Pattern 1: Storage lifecycle management rule (RGP-03 — server-side blob deletion)
**What:** `Microsoft.Storage/storageAccounts/managementPolicies@2023-05-01` child of the existing `storage` resource, with a single `Lifecycle` rule that deletes base blobs N days after last modification, filtered to the job/OCR/FIC blob prefix.
**When to use:** For all artifacts that live in Azure Storage blobs (Durable state outputs, any blob-persisted OCR/FIC).
**Composes with main.bicep:** Yes — add as a child resource of the existing `resource storage 'Microsoft.Storage/storageAccounts@2023-05-01'` (main.bicep:168). It is independent of `blobServices` (soft-delete/PITR/versioning at main.bicep:192) — they coexist. Note the data-minimization vs. PITR interaction in Pitfall 2.

```bicep
// Source: https://learn.microsoft.com/en-us/azure/storage/blobs/lifecycle-management-policy-delete
//         https://learn.microsoft.com/en-us/azure/storage/blobs/lifecycle-management-overview
// [VERIFIED: Microsoft Learn] — add to infra/main.bicep as a child of `storage`.

@description('Rétention des artefacts de jobs (job/OCR/FIC) en jours avant suppression (RGP-03, minimisation). Param configurable.')
param jobRetentionDays int = 30

@description('Préfixe(s) de blob ciblé(s) par la règle de cycle de vie RGP-03. Aligner sur le conteneur Durable d\'artefacts de jobs.')
param jobBlobPrefixes array = [ 'jobs/' ]   // confirm actual container/prefix at provisioning (Open Q1)

resource storageLifecycle 'Microsoft.Storage/storageAccounts/managementPolicies@2023-05-01' = {
  parent: storage
  name: 'default'              // MUST be 'default' (only one policy per account)
  properties: {
    policy: {
      rules: [
        {
          enabled: true
          name: 'rgp03-delete-job-artifacts'
          type: 'Lifecycle'
          definition: {
            filters: {
              blobTypes: [ 'blockBlob' ]
              prefixMatch: jobBlobPrefixes   // scope to job/OCR/FIC artifacts, NOT Durable control blobs
            }
            actions: {
              baseBlob: {
                delete: { daysAfterModificationGreaterThan: jobRetentionDays }
              }
              // Optional: also expire snapshots/versions created by versioning (main.bicep enables it)
              snapshot: { delete: { daysAfterCreationGreaterThan: jobRetentionDays } }
              version:  { delete: { daysAfterCreationGreaterThan: jobRetentionDays } }
            }
          }
        }
      ]
    }
  }
}
```
**Key constraints `[VERIFIED: Microsoft Learn]`:** the management-policy resource name MUST be `'default'`; only one policy per storage account; `prefixMatch` is `{container}/{prefix}` form; `daysAfterModificationGreaterThan` operates on the *current* (base) blob's last-modified time. Use `prefixMatch` (NOT a blanket account-wide rule) so the rule does not garbage-collect Durable's own task-hub control blobs.

### Pattern 2: Timer-triggered local TTL cleaner (RGP-03 — `JOBS_BASE_DIR` ephemeral files)
**What:** A pure, testable cleanup function that deletes files/dirs under `JOBS_BASE_DIR` older than N days, invoked by an Azure Functions **timer trigger** (NCRONTAB) added to `function_app.py`, with the deletion logic in a separate importable module so pytest can drive it without the SDK (mirrors the `audit_pipeline` dependency-injection testability pattern).
**Why a timer (not the existing wipe script):** `scripts/cleanup_local_artifacts.ps1` deletes the *entire* `jobs/` tree unconditionally — that would destroy in-flight audits. RGP-03 requires *age-based* deletion. `[VERIFIED: cleanup_local_artifacts.ps1 read]`
**When to use:** For artifacts on the Functions VM-local filesystem (`JOBS_BASE_DIR/{document_id}` downloads, OCR temp, `FIC_Brouillon_*.docx`) that storage lifecycle rules cannot reach.

```python
# Source: timer trigger NCRONTAB — https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer
# Place pure logic in a new module (e.g. scripts/jobs_ttl.py) for SDK-free pytest.
from __future__ import annotations
import os
import shutil
import time
from typing import Callable

__all__ = ["prune_jobs_dir"]

def prune_jobs_dir(
    base_dir: str,
    *,
    max_age_seconds: int,
    now: float | None = None,
    remover: Callable[[str], None] | None = None,
) -> list[str]:
    """Supprime les entrées de `base_dir` plus vieilles que `max_age_seconds`.

    Pur et testable : `now` et `remover` sont injectables (pas d'I/O réel en test).
    Retourne la liste des chemins supprimés. Ne lève jamais sur une entrée isolée.
    """
    now = time.time() if now is None else now
    remove = remover or _default_remove
    deleted: list[str] = []
    if not os.path.isdir(base_dir):
        return deleted
    cutoff = now - max_age_seconds
    for name in os.listdir(base_dir):
        path = os.path.join(base_dir, name)
        try:
            if os.path.getmtime(path) < cutoff:
                remove(path)
                deleted.append(path)
        except OSError:
            continue  # entrée disparue / verrouillée — best-effort
    return deleted

def _default_remove(path: str) -> None:
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
    else:
        os.remove(path)
```

```python
# In azure_functions/function_app.py, inside the `if _DURABLE_AVAILABLE:` block,
# guarded exactly like the existing triggers (SDK-only). NCRONTAB = daily 02:00 UTC.
# Source: https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer
    @app.timer_trigger(schedule="0 0 2 * * *", arg_name="timer", run_on_startup=False)
    def prune_job_artifacts(timer) -> None:
        from jobs_ttl import prune_jobs_dir
        base = os.environ.get("JOBS_BASE_DIR", "jobs")
        days = int(os.environ.get("JOB_RETENTION_DAYS", "30"))
        deleted = prune_jobs_dir(base, max_age_seconds=days * 86400)
        logging.info("RGP-03 prune: %d entrée(s) supprimée(s) sous %s", len(deleted), base)
```
**Notes:** Flex Consumption supports timer triggers. Keep `JOB_RETENTION_DAYS` aligned with the Bicep `jobRetentionDays` (30) — document the single source of truth in the RGP-03 policy text. Document the manual fallback (operator runs an equivalent prune) in case the timer is disabled.

### Pattern 3: Log Analytics retention bump-to-param (RGP-04)
**What:** Promote the hardcoded `retentionInDays: 30` in `observability.bicep:55` to a parameter defaulting to **90**.
**When to use:** Now — it is a one-line change. For workspace-based App Insights, this workspace setting is the effective retention; the `Microsoft.Insights/components` resource needs **no** retention property.

```bicep
// observability.bicep — promote to param (currently hardcoded 30 at line 55).
// Source: https://learn.microsoft.com/en-us/azure/templates/microsoft.operationalinsights/workspaces
//         https://learn.microsoft.com/en-us/azure/azure-monitor/logs/data-retention-configure
@description('Rétention Log Analytics en jours (RGP-04 : 90 j, EU-region, délibérément courte).')
@minValue(30)
@maxValue(730)
param logAnalyticsRetentionDays int = 90

resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: lawName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: logAnalyticsRetentionDays   // RGP-04 : 90 j (était 30 en dur)
  }
}
```
Thread `logAnalyticsRetentionDays` from `main.bicep` into the `observability` module params (and add to `prod.parameters.json` if you want it explicit). **Optional per-table override:** if the DPO later requires the audit-trail (`AppEvents`/custom event) table to differ from 90 days, use a separate `Microsoft.OperationalInsights/workspaces/tables@2023-09-01` resource with `retentionInDays` + `totalRetentionInDays` — once set at table level the workspace default no longer governs that table. Not needed under the locked 90-day decision; note as a DPO option. `[VERIFIED: Microsoft Learn]`

### Anti-Patterns to Avoid
- **Repurposing `cleanup_local_artifacts.ps1` as the RGP-03 enforcement** — it unconditionally wipes `jobs/`; would delete in-flight audits. Write an age-based cleaner instead.
- **Account-wide lifecycle rule with no `prefixMatch`** — would also delete Durable's own task-hub control/lease blobs, breaking orchestration. Always scope by prefix.
- **Setting `RetentionInDays` on the App Insights component and assuming it governs retention** — for workspace-based components it does not; the workspace setting wins. Set retention on the workspace only.
- **Claiming WORM/table immutability for the audit trail** — SECURITY_POSTURE.md §7 already framed this honestly (append-only + retention + RBAC + resource-lock, *not* WORM). Do not regress that framing in SEC docs.
- **Re-opening locked CONTEXT decisions** (30-day artifact / 90-day log retention, Mermaid diagrams, DPO-as-external-gate). Research the HOW, keep the WHAT.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Delete old job/OCR/FIC blobs | App loop iterating + deleting blobs | Storage `managementPolicies` lifecycle rule | Server-side, zero-compute, audit-evident, no MI data-plane churn |
| Log retention enforcement | Scheduled KQL purge / export job | Workspace `retentionInDays` | Native, single property; purge APIs are for DSR erasure, not routine retention |
| PII redaction in telemetry | New redaction regex in the cleaner/docs | Existing `safe_logger.redact` / `RedactingSpanProcessor` | AUD-06 single audited surface — never add a second redaction code path |
| DPIA criteria interpretation | Inventing a bespoke risk rubric | EDPB/WP248 9-criteria + CNIL methodology | Regulator-recognized; "≥2-of-9" is the accepted bar |
| Record-of-processing fields | Free-form table | GDPR Art. 30(1) field list | Auditors check against the exact statutory fields |

**Key insight:** Every Phase-5 deliverable has an authoritative template (Azure resource type, GDPR article, EDPB guideline, OWASP list). Custom solutions add review surface with no compliance benefit.

## Runtime State Inventory

> Phase 5 is additive (new docs + one Bicep rule + one cleaner). It is not a rename/refactor. This section covers the *retention-relevant* state the deliverables must account for.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data (blobs) | Azure Storage account `${namePrefix}${env}store` holds Durable state + (potentially) job/OCR/FIC artifacts. Soft-delete 7d + PITR 6d + versioning ON (main.bicep:192-202). | RGP-03 lifecycle rule deletes job-prefixed blobs @30d; note soft-delete extends *effective* erasure by up to 7d (Pitfall 2). |
| Live service config | Log Analytics workspace currently `retentionInDays: 30` (observability.bicep:55). | RGP-04: bump to 90 via param. |
| OS/VM-local state | `JOBS_BASE_DIR/{document_id}` downloads, OCR temp, `FIC_Brouillon_*.docx` on the Functions VM FS (function_app.py:83,103,165). | RGP-03: NEW timer cleaner (no existing age-based mechanism). |
| Secrets/env vars | `JOBS_BASE_DIR`, new `JOB_RETENTION_DAYS` env var (cleaner). No secret involved. | Document `JOB_RETENTION_DAYS` default 30; keep aligned with Bicep `jobRetentionDays`. |
| Build artifacts | None affected by this phase. | None — verified: phase adds files, changes no package/build identity. |
| Existing dev tooling | `scripts/cleanup_local_artifacts.ps1` (destructive full-wipe). | Do NOT use for RGP-03; optionally cross-reference it in docs as a dev-only tool. |

## Common Pitfalls

### Pitfall 1: GOVERNANCE.md §4 already claims "Pas de Rétention" / immediate deletion
**What goes wrong:** `docs/governance/GOVERNANCE.md` §4 states documents are *"effacés immédiatement à la fin du pipeline"*. The new RGP-03 decision is **30-day** retention with TTL cleanup — a direct contradiction. An auditor reading both finds inconsistent retention claims.
**Why it happens:** The governance doc predates the Phase-5 retention decision.
**How to avoid:** UPDATE GOVERNANCE.md §4 to reflect the real, enforced policy (30-day TTL + storage lifecycle + 90-day log retention), and make the new RGP docs the canonical source. `[VERIFIED: GOVERNANCE.md read]`
**Warning signs:** Two docs naming different retention periods.

### Pitfall 2: Soft-delete / PITR / versioning extends effective erasure beyond 30 days
**What goes wrong:** RGP-03 claims 30-day deletion, but blob soft-delete (7d, main.bicep:198), container soft-delete (7d), and versioning+PITR mean a "deleted" blob (and its versions) is *recoverable* for up to ~7 extra days — so the *effective* maximum retention is ~37 days, and prior versions persist until the version-delete action fires.
**Why it happens:** Lifecycle delete + soft-delete + versioning are independent INF-09 controls layered on the same account.
**How to avoid:** State the honest effective window in the RGP-03 policy text ("artifacts deleted at 30 days; recoverable via soft-delete for up to 7 further days for operational safety; versions/snapshots expired by the same rule"). Include `snapshot`/`version` delete actions in the lifecycle rule (Pattern 1). Frame the 7-day soft-delete as an intentional operational-safety tradeoff for the DPIA. `[VERIFIED: main.bicep read]`
**Warning signs:** DPIA/Art.30 says "30 days" with no mention of soft-delete recovery.

### Pitfall 3: Lifecycle rule garbage-collects Durable control blobs
**What goes wrong:** An unscoped delete rule removes Durable Functions' own task-hub blobs (leases, history, instances), corrupting orchestration.
**Why it happens:** `AzureWebJobsStorage` (Durable state) and job artifacts share one storage account.
**How to avoid:** Always set `filters.prefixMatch` to the job/OCR/FIC container/prefix only. Confirm the actual container name at provisioning (Open Q1). `[CITED: lifecycle-management-overview]`
**Warning signs:** Orchestrations failing with missing-blob errors after the rule deploys.

### Pitfall 4: DPIA/Art.30 treated as autonomously "complete"
**What goes wrong:** The plan marks RGP-01/RGP-02 done when Claude finishes the draft, skipping the DPO gate — but CONTEXT locks DPO sign-off as the **hard external gate before Phase 6**.
**Why it happens:** The drafts look finished.
**How to avoid:** Plan tasks must end RGP-01/RGP-02 at a `checkpoint:human-verify` (DPO sign-off) — the draft is the autonomous deliverable; finalization is the operator/DPO checkpoint. STATE.md already flags the DPO as an external blocker engaged day-one. `[VERIFIED: CONTEXT.md + STATE.md]`
**Warning signs:** Phase 6 starting with an unsigned DPIA.

### Pitfall 5: RGP-06 residency claimed from Bicep alone
**What goes wrong:** Residency doc asserts EU residency from `location: francecentral` in Bicep, but M365 tenant geo, Fabric capacity region, and Power Platform env region are NOT in Bicep and remain operator-verifiable only (STATE.md blocker).
**How to avoid:** RGP-06 doc has two columns — "verifiable now (Bicep `location` values)" vs "operator checkpoint (M365/Fabric/Power Platform)" — and aggregates the Phase 2 operator residency checkpoints rather than asserting them. The webtest `Locations` in observability.bicep are already `[ASSUMED]` EU IDs pending operator verification. `[VERIFIED: STATE.md + observability.bicep:259]`
**Warning signs:** A residency doc with no operator-confirmation column.

## Code Examples

### EDPB/WP248 nine-criteria assessment table (RGP-02 — pre-fill for AC360)
```markdown
<!-- Source: EDPB/WP248 rev.01 (https://ec.europa.eu/newsroom/article29/items/611236/en);
     CNIL methodology. "≥2-of-9 → DPIA required" (EDPB). -->
| # | EDPB/WP248 criterion | Applies to AC360? | Justification |
|---|----------------------|-------------------|---------------|
| 1 | Evaluation / scoring | PARTIAL | Audit produces a conformity verdict (CONFORME/ECART/INCERTAIN) — scoring of documents, not profiling of persons |
| 2 | Automated decision-making w/ legal/similar effect | NO | Read-only; FIC is a *draft for human review*; no automated decision affecting the data subject |
| 3 | Systematic monitoring | NO | On-demand per-document audit, not monitoring of individuals |
| 4 | Sensitive / highly personal data | YES | Insurance client documents contain PII (identity, financial data, possibly IBAN/SSN captured by OCR) |
| 5 | Large scale | PARTIAL | 20–100 internal users; client base volume TBD with DPO (could push to YES) |
| 6 | Matching / combining datasets | YES | OCR-extracted fields are matched/compared against the Fabric/ARTUS reference system |
| 7 | Vulnerable data subjects | NO | Insurance clients, not children/employees-as-subjects |
| 8 | Innovative technology | YES | LLM/Copilot Studio + OCR document audit is a novel org/tech solution |
| 9 | Prevents exercising a right / using a service | NO | Read-only assistant; does not gate the client's access to a service |

**Outcome:** ≥2 criteria met (4, 6, 8 firmly; 1/5 partial) → **DPIA required and warranted.** Draft full DPIA. DPO signs off (hard gate).
```

### GDPR Art. 30(1) record-of-processing skeleton (RGP-01)
```markdown
<!-- Source: GDPR Art. 30(1) (https://gdpr-info.eu/art-30-gdpr/). DPO finalizes. -->
1. Controller / joint controller / representative / DPO — name & contact   [DPO to confirm]
2. Purposes of processing — conformity audit of insurance client documents (read-only)
3. Categories of data subjects & personal data — insurance clients; identity/financial PII via OCR
4. Categories of recipients — internal commercial team only; no external disclosure
5. Third-country transfers — NONE (EU residency: France Central / West Europe — see RGP-06)
6. Envisaged erasure time limits — job/OCR/FIC artifacts 30 days (RGP-03); logs 90 days (RGP-04);
   audit trail (hashed, no raw PII) per workspace retention
7. General description of technical/organisational security measures — Art. 32: Entra SSO, JWT RS256,
   OBO user-scoped, IDOR gate, read-only, PII redaction, MI/Key Vault, private endpoints (ref SEC-01..05)
```

### OWASP LLM Top 10 2025 → AC360 mitigation → test (SEC-03 rows)
```markdown
<!-- Source: OWASP Top 10 for LLM Applications 2025 (https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/) -->
| OWASP LLM (2025) | AC360 mitigation | Evidence/test |
|------------------|------------------|---------------|
| LLM01 Prompt Injection | contentModeration High; useModelKnowledge=false; validator gate (PUB-04) | GUARDRAILS_VALIDATION.md; validate_copilot_yaml.py |
| LLM02 Sensitive Information Disclosure | safe_logger.redact + RedactingSpanProcessor; 4-field hashed audit trail; redacted HTTPException detail | tests/security/test_no_plaintext_secrets.py; telemetry RedactingSpanProcessor |
| LLM03 Supply Chain | Dependabot (pip + actions) ON; PyJWT/deltalake pin policy (SEC-04) | .github/dependabot.yml |
| LLM05 Improper Output Handling | FIC is human-review draft; JSON-schema validation of audit output | schemas/audit_result.schema.json |
| LLM06 Excessive Agency | Read-only; no write/actions; OBO honors user SharePoint RBAC | test_audit_ownership / test_job_isolation |
| LLM07 System Prompt Leakage | additionalInstructions tested (red-teaming, GOVERNANCE §3) | GOVERNANCE.md §3 |
```
(Synthesize the full matrix from the per-phase `<threat_model>` STRIDE blocks + this OWALL mapping + existing tests, per the locked SEC-03 decision.)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Classic (non-workspace) App Insights with component-level retention | Workspace-based App Insights; retention on the Log Analytics workspace | Classic retired (already enforced — observability.bicep `WorkspaceResourceId`) | RGP-04 retention is a *workspace* property; component retention is moot |
| OWASP LLM Top 10 (2023) | OWASP LLM Top 10 (2025) — adds System Prompt Leakage (LLM07), Vector/Embedding Weaknesses (LLM08); reorders | 2025 | Use the 2025 IDs in SEC-03 |
| "Documents deleted immediately" (GOVERNANCE §4) | 30-day TTL + storage lifecycle + 90-day logs | Phase 5 (this) | Update GOVERNANCE §4 to avoid contradiction |

**Deprecated/outdated:**
- Component-level App Insights retention for workspace-based instances — ignored; set workspace retention.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Job/OCR/FIC artifacts that need lifecycle deletion live under a blob prefix like `jobs/` in the Durable storage account (vs. only on VM-local FS) | RGP-03 Pattern 1 | If artifacts are *only* VM-local, the storage rule is a no-op and only the timer cleaner enforces RGP-03 — confirm actual blob container/prefix at provisioning |
| A2 | Flex Consumption supports the timer trigger as used | RGP-03 Pattern 2 | If unsupported, fall back to documented-manual prune or a separate scheduled runner — verify on the Flex plan |
| A3 | "Large scale" (criterion 5) and exact controller identity are DPO-confirmable | RGP-02 / RGP-01 | DPIA scope/legal basis may shift — explicitly a DPO checkpoint |
| A4 | 90-day Log Analytics retention is within the free workspace allowance and acceptable to the DPO as "deliberately short EU retention" | RGP-04 | If DPO wants shorter/longer or per-table differentiation, adjust the param / add a tables resource |
| A5 | Webtest `Locations` EU IDs in observability.bicep are correct EU points | RGP-06 | Already flagged `[ASSUMED]` in-repo; operator verifies at provisioning |

## Open Questions

1. **Actual job-artifact blob container/prefix** — What container/prefix do job/OCR/FIC blobs land in (vs. Durable control blobs)? Needed to scope `prefixMatch` correctly.
   - What we know: artifacts are written to `JOBS_BASE_DIR` (local FS) by `function_app.py`; Durable uses the same account for state.
   - What's unclear: whether any job/OCR/FIC content is *also* persisted as blobs under a known prefix.
   - Recommendation: confirm at provisioning; if artifacts are purely VM-local, the timer cleaner is the primary RGP-03 control and the storage rule covers Durable output blobs only (still valuable). Parameterize `jobBlobPrefixes`.

2. **Per-table audit-trail retention** — Does the DPO require the 4-field audit trail to differ from the 90-day default (e.g., longer for compliance evidence)?
   - Recommendation: ship workspace 90d now; offer the `workspaces/tables` per-table override as a documented DPO option.

3. **DPO availability / controller identity** — Art. 30/DPIA finalization blocks Phase 6.
   - Recommendation: draft autonomously now; DPO sign-off is the locked external checkpoint.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Bicep CLI (`az bicep build`) | RGP-03/04 validation | Assumed (used by validate_infra.ps1) | — | Compile in CI |
| pytest / pytest-asyncio | TTL cleaner unit tests | ✓ (setup.cfg) | 8.0.0+ | — |
| markdownlint | doc lint | Optional (offline) | — | Structural grep checks |
| Azure subscription / live tenant | RGP-06 residency, DPO finalization, live retention apply | ✗ at research time | — | Operator/DPO checkpoints (locked) |
| DPO (external) | RGP-01/02 sign-off | ✗ (external) | — | None — hard gate before Phase 6 |

**Missing dependencies with no fallback:** DPO sign-off (RGP-01/02) — locked external checkpoint.
**Missing dependencies with fallback:** Live tenant verification (RGP-06) → Phase 2 operator checkpoints aggregated here.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0.0+ / pytest-asyncio 0.23.0+ |
| Config file | `setup.cfg` ([tool:pytest], testpaths=tests, asyncio_mode=auto) |
| Quick run command | `pytest tests/azure_functions/test_jobs_ttl.py -x` |
| Full suite command | `pytest tests/backend tests/security tests/azure_functions` |
| IaC validation | `az bicep build -f infra/main.bicep` and `-f infra/observability.bicep` (offline) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RGP-03 (storage rule) | main.bicep compiles with `managementPolicies` delete rule + `jobRetentionDays` param | offline IaC | `az bicep build -f infra/main.bicep` | ✅ (extend) |
| RGP-03 (TTL logic) | `prune_jobs_dir` deletes only entries older than cutoff; keeps fresh; never raises on missing entry | unit | `pytest tests/azure_functions/test_jobs_ttl.py -x` | ❌ Wave 0 |
| RGP-04 (retention) | observability.bicep compiles with `logAnalyticsRetentionDays` param defaulting 90 | offline IaC | `az bicep build -f infra/observability.bicep` | ✅ (extend) |
| RGP-04 (redaction) | `RedactingSpanProcessor.on_end` routes str attrs through redact | unit | `pytest tests/backend/test_telemetry_redaction.py -x` | ⚠️ verify existing telemetry test covers it |
| SEC-01..05 | each evidence doc exists with required sections | structural grep | `grep -l "## " docs/security/SEC-0*.md` (per-doc section asserts) | ❌ Wave 0 (doc checks) |
| RGP-01/02/05/06 | each governance doc exists with required sections (Art.30 fields; 9-criteria table; DSR steps; residency two-column) | structural grep | per-doc grep asserts | ❌ Wave 0 (doc checks) |

### Sampling Rate
- **Per task commit:** the relevant quick command (`pytest ...test_jobs_ttl.py -x` for code; `az bicep build` for IaC; per-doc grep for docs).
- **Per wave merge:** `pytest tests/backend tests/security tests/azure_functions` + `az bicep build` on both templates.
- **Phase gate:** Full suite green + both Bicep templates compile + all evidence-doc structural greps pass + **DPO sign-off checkpoints** for RGP-01/RGP-02 (manual, hard gate) + RGP-06 operator residency checkpoints.

### Wave 0 Gaps
- [ ] `tests/azure_functions/test_jobs_ttl.py` — covers RGP-03 TTL logic (fresh kept, old deleted, missing-entry tolerated, injected `now`/`remover`)
- [ ] `scripts/jobs_ttl.py` — pure cleanup module (new)
- [ ] Confirm/extend `tests/backend/test_telemetry_redaction.py` covers `RedactingSpanProcessor` (RGP-04 evidence) — if absent, add
- [ ] Structural doc-existence/section checks (grep-based) for each SEC-0x / RGP-0x evidence doc — can be a small `pytest` or a shell assert in CI

> Manual-only (justified): DPO sign-off (RGP-01/02), live-tenant residency (RGP-06 M365/Fabric/Power Platform), live retention apply — all locked operator/DPO checkpoints, not automatable.

## Security Domain

> `security_enforcement: true`, ASVS L1. Phase 5 *is* the security-evidence phase — these categories are documented, not newly implemented (the controls already exist from Phases 1–4).

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control (already in AC360) |
|---------------|---------|-----------------|
| V2 Authentication | yes | Entra SSO, JWT RS256/JWKS (scripts/auth.py) — SEC-02 |
| V3 Session Management | yes | Stateless JWT; OBO user-delegated tokens never persisted — SEC-02 |
| V4 Access Control | yes | IDOR gate (`_assert_durable_owner`, owner_hash on oid); read-only; OBO RBAC — SEC-02 |
| V5 Input Validation | yes | UUID + commonpath path-traversal guards; JSON-schema audit output |
| V6 Cryptography | yes | SHA-256 user-id hash; secrets in Key Vault via MI; TLS 1.2; no hand-rolled crypto |
| V7 Logging | yes | safe_logger redaction surface; RedactingSpanProcessor; 4-field no-PII audit trail — SEC-03/RGP-04 |
| V9 Communications | yes | httpsOnly, minTlsVersion 1.2, private endpoints (INF-08) |

### Known Threat Patterns for {Copilot Studio + FastAPI + Durable Functions + OCR PII}
| Pattern | STRIDE | Standard Mitigation (in AC360) |
|---------|--------|---------------------|
| Prompt injection (LLM01) | Tampering | contentModeration High; useModelKnowledge=false; validator gate |
| PII disclosure in logs/telemetry (LLM02) | Information Disclosure | RedactingSpanProcessor + safe_logger.redact (single surface) |
| IDOR on audit jobs | Elevation/Info Disclosure | durable owner_hash gate (authoritative); single-instance pin |
| PII over-retention | Info Disclosure / non-compliance | RGP-03 30-day TTL + RGP-04 90-day logs (this phase) |
| OCR of PII on public endpoint | Info Disclosure | DocIntel private endpoint + disableLocalAuth (INF-04/CR-03) |
| Secrets in error responses | Info Disclosure | redacted HTTPException detail (Phase 1) |

## Sources

### Primary (HIGH confidence)
- Microsoft Learn — Storage lifecycle management (overview, delete-policy, find-blobs): https://learn.microsoft.com/en-us/azure/storage/blobs/lifecycle-management-overview ; https://learn.microsoft.com/en-us/azure/storage/blobs/lifecycle-management-policy-delete
- Microsoft Learn — `Microsoft.OperationalInsights/workspaces` template reference (`retentionInDays`, `workspaceCapping`, tables): https://learn.microsoft.com/en-us/azure/templates/microsoft.operationalinsights/workspaces
- Microsoft Learn — Manage data retention in a Log Analytics workspace: https://learn.microsoft.com/en-us/azure/azure-monitor/logs/data-retention-configure
- EDPB/WP248 rev.01 — Guidelines on DPIA (9 criteria, "≥2-of-9"): https://ec.europa.eu/newsroom/article29/items/611236/en
- GDPR Art. 30(1) — record of processing fields: https://gdpr-info.eu/art-30-gdpr/
- OWASP Top 10 for LLM Applications 2025: https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/
- Repo (verified by read): `infra/main.bicep`, `infra/observability.bicep`, `infra/prod.parameters.json`, `scripts/telemetry.py`, `scripts/audit_trail.py`, `azure_functions/function_app.py`, `docs/security/SECURITY_POSTURE.md`, `docs/governance/GOVERNANCE.md`, `.github/dependabot.yml`, `scripts/cleanup_local_artifacts.ps1`, `.planning/codebase/CONCERNS.md`, `.planning/STATE.md`

### Secondary (MEDIUM confidence)
- EDPB 9-criteria summary (cross-check of WP248): https://keepabl.com/news/edpb-guidance-dpias-9-criteria/
- Workspace-based App Insights retention behavior (workspace governs, component ignored): https://learn.microsoft.com/en-us/azure/azure-monitor/logs/data-retention-configure (+ community confirmation)

### Tertiary (LOW confidence)
- Azure Functions timer trigger NCRONTAB form on Flex Consumption — verify trigger support on the live Flex plan (A2).

## Metadata

**Confidence breakdown:**
- RGP-03 storage Bicep idiom: HIGH — verified on Microsoft Learn; composes with existing `storage` resource.
- RGP-03 local TTL cleaner: MEDIUM-HIGH — pattern is standard; Flex timer support to confirm (A2).
- RGP-04 LA retention: HIGH — property verified; existing line found at observability.bicep:55.
- DPIA/Art.30/DSR frameworks: HIGH — cited from EDPB/WP248 + gdpr-info.
- OWASP LLM mapping: HIGH — 2025 list cited; AC360 mitigations grounded in existing docs/tests.
- SEC-04 (Dependabot): HIGH — file already exists (verified); work is documentation + pin policy.

**Research date:** 2026-06-15
**Valid until:** 2026-07-15 (stable domain — GDPR articles/EDPB criteria are durable; re-check Azure API versions and OWASP edition if planning slips materially)
