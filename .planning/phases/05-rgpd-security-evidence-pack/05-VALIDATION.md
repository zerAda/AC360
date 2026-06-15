---
phase: 5
slug: rgpd-security-evidence-pack
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-14
---

# Phase 5 — Validation Strategy

> Code/IaC deliverables (RGP-03 TTL + storage rule, RGP-04 retention) are offline-verifiable (pytest + az bicep build). Evidence docs are validated by structural grep. DPO sign-off (RGP-01/02) + live residency (RGP-06) are operator/DPO checkpoints.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (`setup.cfg`, asyncio_mode auto) |
| **Quick run command** | `python -m pytest tests/azure_functions/test_jobs_ttl.py -x` |
| **Full suite command** | `python -m pytest tests/backend tests/security tests/azure_functions` |
| **IaC validation** | `az bicep build -f infra/main.bicep` + `-f infra/observability.bicep` (offline); `scripts/validate_infra.ps1` |
| **Doc validation** | structural grep per evidence doc (sections present) / markdown lint |

---

## Sampling Rate

- **After every task commit:** the relevant quick command (`pytest …test_jobs_ttl.py -x` for code; `az bicep build` for IaC; per-doc grep for docs).
- **After every wave:** `python -m pytest tests/backend tests/security tests/azure_functions` + `az bicep build` both templates.
- **Phase gate:** full suite green + both Bicep compile + all evidence-doc structural greps pass + **DPO sign-off checkpoints** (RGP-01/02) + RGP-06 operator residency checkpoints.

---

## Per-Requirement Validation Map

| Req | Behavior | Type | Command / check | Live? |
|-----|----------|------|-----------------|-------|
| RGP-03 (storage rule) | main.bicep compiles with `managementPolicies` delete rule + `jobRetentionDays` param | offline IaC | `az bicep build -f infra/main.bicep` | offline |
| RGP-03 (TTL logic) | `prune_jobs_dir` deletes only entries older than cutoff; keeps fresh; tolerates missing | unit | `pytest tests/azure_functions/test_jobs_ttl.py -x` | offline |
| RGP-04 (retention) | observability.bicep compiles with `logAnalyticsRetentionDays` param default 90 | offline IaC | `az bicep build -f infra/observability.bicep` | offline |
| RGP-04 (redaction) | RedactingSpanProcessor routes str attrs through redact | unit | `pytest tests/backend/test_telemetry_redaction.py -x` | offline |
| SEC-01..05 | each evidence doc exists with required sections | structural | per-doc grep | offline |
| RGP-01/02/05/06 | each governance doc exists with required sections (Art.30 fields; 9-criteria table; DSR steps; residency table) | structural | per-doc grep | offline (DPO sign-off operator) |

---

## Wave 0 Requirements

- [ ] `scripts/jobs_ttl.py` — pure cleanup module (`prune_jobs_dir`, injected `now`/`remover`)
- [ ] `tests/azure_functions/test_jobs_ttl.py` — RGP-03 TTL logic (fresh kept, old deleted, missing tolerated)
- [ ] Confirm `tests/backend/test_telemetry_redaction.py` covers RedactingSpanProcessor (RGP-04 evidence) — extend if needed
- [ ] Structural doc-existence/section checks for each SEC-0x / RGP-0x evidence doc

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

- [ ] RGP-03 (storage rule + TTL module + test) + RGP-04 (retention bump) offline-verified
- [ ] All SEC/RGP evidence docs present with required sections
- [ ] DPO sign-off (RGP-01/02) + residency (RGP-06) documented as operator/DPO checkpoints
- [ ] `nyquist_compliant: true` set

**Approval:** pending
