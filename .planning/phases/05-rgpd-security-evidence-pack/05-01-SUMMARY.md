---
phase: 05-rgpd-security-evidence-pack
plan: 01
status: complete
completed: 2026-06-14
requirements: [RGP-03]
test_result: "test_jobs_ttl.py 5 passed; tests/azure_functions 36 passed; az bicep build exit 0"
---

# Plan 05-01 Summary — RGP-03 Data-Retention Enforcement

**Note:** executed inline by the orchestrator (subagent reliability issues this session).

## What landed (TDD: RED → GREEN → wire → document)

- **`scripts/jobs_ttl.py`** — pure, injectable `prune_jobs_dir(base_dir, *, max_age_seconds, now=None, remover=None)`: age-based (mtime < now-cutoff), keeps fresh entries, tolerates a missing base dir and per-entry `OSError` (best-effort), default remover rmtree/remove. NOT the destructive full-wipe `cleanup_local_artifacts.ps1`.
- **`tests/azure_functions/test_jobs_ttl.py`** — 5 tests: old-deleted/fresh-kept, missing-dir tolerated, per-entry OSError tolerated, injected-now governs cutoff, default-remover actually deletes. All green.
- **`azure_functions/function_app.py`** — daily `@app.timer_trigger(schedule="0 0 2 * * *", run_on_startup=False)` `prune_job_artifacts` inside the `_DURABLE_AVAILABLE` block, reads `JOBS_BASE_DIR` + `JOB_RETENTION_DAYS` (default 30), calls `prune_jobs_dir`, logs `RGP-03 prune` count.
- **`infra/main.bicep`** — `jobRetentionDays` (30) + `jobBlobPrefixes` (`['jobs/']`) params; `storageLifecycle` `managementPolicies@2023-05-01` (`name: 'default'`) with the `rgp03-delete-job-artifacts` Lifecycle rule, `prefixMatch`-scoped (never Durable control blobs), baseBlob/snapshot/version delete at the retention window. Coexists with the existing blobSvc soft-delete/PITR.
- **`docs/governance/RGP-03-retention-policy.md`** — canonical 30-day policy: scope, the two aligned sources of truth (`jobRetentionDays` Bicep + `JOB_RETENTION_DAYS` env), the two enforcement points, and the honest **~37-day effective-erasure window** (30d + ~7d soft-delete) disclosure for reuse by DPIA/Art.30/DSR.

## Verification
- `pytest tests/azure_functions/test_jobs_ttl.py -x` → 5 passed; `pytest tests/azure_functions` → 36 passed (no collection regression from the timer trigger).
- `az bicep build -f infra/main.bicep` → exit 0; `managementPolicies` + `prefixMatch: jobBlobPrefixes` present.
- Policy doc has the required sections + the ~37-day disclosure.

## Carried forward
- Exact job/OCR/FIC blob prefix confirmed at provisioning (parameterized `jobBlobPrefixes`).
- Live retention apply + timer execution = operator post-deploy check.
