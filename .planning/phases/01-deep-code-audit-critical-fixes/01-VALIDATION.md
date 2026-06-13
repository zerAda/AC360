---
phase: 1
slug: deep-code-audit-critical-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-13
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (`asyncio_mode = auto`) |
| **Config file** | `setup.cfg` (`[tool:pytest]`, `testpaths = tests`) |
| **Quick run command** | `pytest tests/backend/test_graph_obo.py tests/backend/test_audit_ownership.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~60 seconds (full), ~5s (quick) |

---

## Sampling Rate

- **After every task commit:** Run the quick command for the touched requirement.
- **After every plan wave:** Run `pytest tests/backend tests/azure_functions tests/security`
- **Before `/gsd-verify-work`:** Full `pytest` suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| AUD-02 | TBD | 1 | AUD-02 | IDOR | `verify_azure_ad_token` uses `oid`; missing oid → 401 | unit | `pytest tests/backend/test_auth_jwt.py -x` | ✅ extend | ⬜ pending |
| AUD-03 | TBD | 1 | AUD-03 | IDOR | durable owner_hash mismatch → 403; map cache-only | unit | `pytest tests/backend/test_audit_ownership.py tests/backend/test_job_isolation.py -x` | ✅ extend | ⬜ pending |
| AUD-05 | TBD | 1 | AUD-05 | DoS/availability | transient OBO retried (429/503/504/timeout); 4xx not; exhaustion → 503 | unit | `pytest tests/backend/test_graph_obo.py -x` | ✅ extend | ⬜ pending |
| AUD-06 | TBD | 1 | AUD-06 | info-leak | HTTPException detail + telemetry dims redacted | unit | `pytest tests/backend/test_safe_logger_redaction.py tests/backend/test_security_headers.py -x` | ✅ extend | ⬜ pending |
| AUD-07 | TBD | 0/1 | AUD-07 | audit/compliance | audit event = {hash, doc_id, ts_utc, verdict}, no PII | unit | `pytest tests/backend/test_audit_trail.py -x` | ❌ W0 | ⬜ pending |
| AUD-08 | TBD | 0/1 | AUD-08 | data-loss | chain shares one JOBS_BASE_DIR in a single activity | unit | `pytest tests/azure_functions/test_jobs_dir_locality.py -x` | ❌ W0 | ⬜ pending |
| AUD-01 | TBD | 1 | AUD-01 | regression | existing IDOR/rate-limit/path-traversal tests green under single-worker | regression | `pytest tests/backend tests/security tests/azure_functions` | ✅ existing | ⬜ pending |
| AUD-04 | TBD | 1 | AUD-04 | scale-out state | Bicep asserts capacity=1, autoscale max=1, gunicorn --workers 1 | manual/IaC | (see Manual-Only) | ✅ infra | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/azure_functions/test_jobs_dir_locality.py` — covers AUD-08 (locality + single-activity structural assertion)
- [ ] `tests/backend/test_audit_trail.py` — covers AUD-07 (4-field contract + no-PII redaction)
- [ ] No framework install needed — pytest/asyncio already configured in `setup.cfg`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Single-instance pin in IaC | AUD-04 | Bicep static assertion, not runtime-testable without a live deploy | Inspect `infra/main.bicep`: `sku.capacity == 1`, autoscale `maximum == 1`, startup command contains `--workers 1`; confirm a comment documents in-memory state as load-bearing |
| OBO delegated Graph scope list | AUD-05 | Depends on live staging app registration (carried STATE.md blocker) | Verify scope list against live staging app registration before trusting OBO success-path tests |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (test_audit_trail.py, test_jobs_dir_locality.py)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
