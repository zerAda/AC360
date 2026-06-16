---
phase: 1
slug: deep-code-audit-critical-fixes
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-13
validated: 2026-06-17
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> **Validated 2026-06-17** (audit-and-flip): all automated checks green; AUD-04 is a confirmed IaC static assertion. No missing tests.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (`asyncio_mode = auto`) |
| **Config file** | `setup.cfg` (`[tool:pytest]`, `testpaths = tests`) |
| **Quick run command** | `pytest tests/backend/test_graph_obo.py tests/backend/test_audit_ownership.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~24s (full), ~5s (quick) |

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
| AUD-02 | 01-02 | 1 | AUD-02 | IDOR | `verify_azure_ad_token` uses `oid`; missing oid → 401 | unit | `pytest tests/backend/test_auth_jwt.py -x` | ✅ extend | ✅ green |
| AUD-03 | 01-06 | 1 | AUD-03 | IDOR | durable owner_hash mismatch → 403; map cache-only | unit | `pytest tests/backend/test_audit_ownership.py tests/backend/test_job_isolation.py -x` | ✅ extend | ✅ green |
| AUD-05 | 01-03 | 1 | AUD-05 | DoS/availability | transient OBO retried (429/503/504/timeout); 4xx not; exhaustion → 503 | unit | `pytest tests/backend/test_graph_obo.py -x` (14 passed) | ✅ extend | ✅ green |
| AUD-06 | 01-02 | 1 | AUD-06 | info-leak | HTTPException detail + telemetry dims redacted | unit | `pytest tests/backend/test_safe_logger_redaction.py tests/backend/test_security_headers.py -x` | ✅ extend | ✅ green |
| AUD-07 | 01-04 | 0/1 | AUD-07 | audit/compliance | audit event = {hash, doc_id, ts_utc, verdict}, no PII | unit | `pytest tests/backend/test_audit_trail.py -x` (5 passed) | ✅ created | ✅ green |
| AUD-08 | 01-01 | 0/1 | AUD-08 | data-loss | chain shares one JOBS_BASE_DIR in a single activity | unit | `pytest tests/azure_functions/test_jobs_dir_locality.py -x` (4 passed) | ✅ created | ✅ green |
| AUD-01 | 01-07 | 1 | AUD-01 | regression | existing IDOR/rate-limit/path-traversal tests green under single-worker | regression | `pytest tests/backend tests/security tests/azure_functions` (230 passed/1 skipped) | ✅ existing | ✅ green |
| AUD-04 | 01-05 | 1 | AUD-04 | scale-out state | Bicep asserts capacity=1, autoscale max=1, gunicorn --workers 1 | manual/IaC | (see Manual-Only — confirmed `main.bicep` capacity:1 + `--workers 1`) | ✅ infra | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/azure_functions/test_jobs_dir_locality.py` — covers AUD-08 (locality + single-activity structural assertion) — **4 passed**
- [x] `tests/backend/test_audit_trail.py` — covers AUD-07 (4-field contract + no-PII redaction) — **5 passed**
- [x] No framework install needed — pytest/asyncio already configured in `setup.cfg`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Single-instance pin in IaC | AUD-04 | Bicep static assertion, not runtime-testable without a live deploy | Inspect `infra/main.bicep`: `sku.capacity == 1`, autoscale `maximum == 1`, startup command contains `--workers 1`; confirm a comment documents in-memory state as load-bearing. **Confirmed 2026-06-17** (capacity:1 + `--workers 1` present). |
| OBO delegated Graph scope list | AUD-05 | Depends on live staging app registration (carried STATE.md blocker) | Verify scope list against live staging app registration before trusting OBO success-path tests |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (test_audit_trail.py, test_jobs_dir_locality.py)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-06-17 (audit-and-flip; tests landed during execution, flag flipped retroactively).

## Validation Audit 2026-06-17

| Metric | Count |
|--------|-------|
| Requirements | 8 (AUD-01..08) |
| Automated & green | 7 (AUD-01/02/03/05/06/07/08) |
| Manual-only (documented) | 1 (AUD-04 — IaC static assertion, confirmed) |
| Gaps found | 0 |
| Tests generated this audit | 0 (all pre-existing, green) |

Evidence: full suite `230 passed, 1 skipped`; `test_graph_obo.py` 14, `test_audit_trail.py` 5, `test_jobs_dir_locality.py` 4. No nyquist-auditor spawn required (no MISSING gaps).
