---
phase: 5
slug: rgpd-security-evidence-pack
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-14
validated: 2026-06-17
---

# Phase 5 — Validation Strategy

> Code/IaC deliverables (RGP-03 TTL + storage rule, RGP-04 retention) are offline-verifiable (pytest + az bicep build). Evidence docs are validated by structural grep. DPO sign-off (RGP-01/02) + live residency (RGP-06) are operator/DPO checkpoints.
> **Validated 2026-06-17** (audit-and-flip): `test_jobs_ttl.py` 5 passed, `test_telemetry_redaction.py` 3 passed, `az bicep build` exit 0; all SEC-01..05 + RGP-01..06 evidence docs present. RGP-01/02 DPO sign-off + RGP-06 live residency remain external/operator checkpoints.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (`setup.cfg`, asyncio_mode auto) |
| **Quick run command** | `python -m pytest tests/azure_functions/test_jobs_ttl.py -x` |
| **Full suite command** | `python -m pytest tests/backend tests/security tests/azure_functions` |
| **IaC validation** | `az bicep build --file infra/main.bicep` + `--file infra/observability.bicep` (offline) |
| **Doc validation** | structural section check per evidence doc (sections present) |

---

## Sampling Rate

- **After every task commit:** the relevant quick command (`pytest …test_jobs_ttl.py -x` for code; `az bicep build` for IaC; per-doc section check for docs).
- **After every wave:** `python -m pytest tests/backend tests/security tests/azure_functions` + `az bicep build` both templates.
- **Phase gate:** full suite green + both Bicep compile + all evidence-doc section checks pass + **DPO sign-off checkpoints** (RGP-01/02) + RGP-06 operator residency checkpoints.

---

## Per-Requirement Validation Map

| Req | Behavior | Type | Command / check | Status |
|-----|----------|------|-----------------|--------|
| RGP-03 (storage rule) | main.bicep compiles with `managementPolicies` delete rule + `jobRetentionDays` param | offline IaC | `az bicep build --file infra/main.bicep` | ✅ green |
| RGP-03 (TTL logic) | `prune_jobs_dir` deletes only entries older than cutoff; keeps fresh; tolerates missing | unit | `pytest tests/azure_functions/test_jobs_ttl.py -x` (5 passed) | ✅ green |
| RGP-04 (retention) | observability.bicep compiles with `logAnalyticsRetentionDays` param default 90 | offline IaC | `az bicep build --file infra/observability.bicep` | ✅ green |
| RGP-04 (redaction) | RedactingSpanProcessor routes str attrs through redact | unit | `pytest tests/backend/test_telemetry_redaction.py -x` (3 passed) | ✅ green |
| SEC-01..05 | each evidence doc exists with required sections | structural | per-doc section check (5/5 present) | ✅ green |
| RGP-05/06 | governance doc exists with required sections (DSR steps; residency table) | structural | per-doc section check | ✅ green (doc) / RGP-06 ◷ tenant residency operator |
| RGP-01/02 | Art.30 record + DPIA (9-criteria) drafted with all fields | structural | per-doc section check | ✅ green (draft) / ◷ **DPO sign-off** |

---

## Wave 0 Requirements

- [x] `scripts/jobs_ttl.py` — pure cleanup module (`prune_jobs_dir`, injected `now`/`remover`) (exists)
- [x] `tests/azure_functions/test_jobs_ttl.py` — RGP-03 TTL logic (fresh kept, old deleted, missing tolerated) — **5 passed**
- [x] `tests/backend/test_telemetry_redaction.py` covers RedactingSpanProcessor (RGP-04 evidence) — **3 passed**
- [x] Structural doc-existence/section checks for each SEC-0x / RGP-0x evidence doc (11/11 present)

---

## Manual-Only Verifications (operator / DPO checkpoints)

| Behavior | Req | Why Manual | Instructions |
|----------|-----|------------|--------------|
| DPO sign-off of DPIA | RGP-02 | External DPO; **hard gate before Phase 6** | DPO reviews + signs the drafted DPIA; record sign-off |
| DPO finalizes Art. 30 record | RGP-01 | External DPO (controller) | DPO completes controller fields + signs |
| Live EU residency | RGP-06 | Live tenant | Confirm M365 geo / Fabric region / Power Platform env (Phase 2 checkpoint) |
| Live retention apply | RGP-03/04 | Needs live deploy | Apply Bicep; confirm lifecycle rule + LA retention live |

---

## Validation Sign-Off

- [x] RGP-03 (storage rule + TTL module + test) + RGP-04 (retention bump) offline-verified
- [x] All SEC/RGP evidence docs present with required sections
- [x] DPO sign-off (RGP-01/02) + residency (RGP-06) documented as operator/DPO checkpoints
- [x] `nyquist_compliant: true` set

**Approval:** validated 2026-06-17 (audit-and-flip; offline code/IaC/doc gates green, DPO sign-off + live residency external/operator-gated).

## Validation Audit 2026-06-17

| Metric | Count |
|--------|-------|
| Requirements | 11 (SEC-01..05, RGP-01..06) |
| Automated & green (offline) | SEC-01..05 (docs), RGP-03, RGP-04, RGP-05 (doc), RGP-06 (doc) |
| Manual-only (DPO/operator) | RGP-01, RGP-02 (DPO sign-off, hard gate), RGP-06 live residency, live retention apply |
| Gaps found | 0 |
| Tests generated this audit | 0 |

Evidence: `test_jobs_ttl.py` 5 passed, `test_telemetry_redaction.py` 3 passed, `az bicep build` exit 0; all 11 SEC/RGP docs present (docs/security + docs/governance). No nyquist-auditor spawn required.
