---
phase: 4
slug: copilot-studio-production-publish
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-14
validated: 2026-06-17
---

# Phase 4 — Validation Strategy

> PUB-04 (guardrail assertions) and PUB-02 (gateway-host rebind) are offline-verifiable via the validator + pytest. The live publish/SSO/install/known-blocked-prompt items are operator checkpoints with evidence capture.
> **Validated 2026-06-17** (audit-and-flip): `validate_copilot_yaml.py` exit 0 (40 OK / 0 KO), `test_validate_copilot_yaml.py` 7 passed. PUB-01/03/05 + live known-blocked-prompt remain operator checkpoints.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (`setup.cfg`, asyncio_mode auto) |
| **Config file** | `setup.cfg`; `tests/backend/conftest.py` adds `scripts/` to path |
| **Quick run command** | `python -m pytest tests/backend/test_validate_copilot_yaml.py -x` + `python scripts/validate_copilot_yaml.py` |
| **Full suite command** | `python -m pytest` |
| **Offline runbook** | structural section check on `docs/production/runbooks/06-copilot-publish.md` |

---

## Sampling Rate

- **After every task commit:** `python -m pytest tests/backend/test_validate_copilot_yaml.py -x` + `python scripts/validate_copilot_yaml.py` (exit 0).
- **After every wave:** full `python -m pytest`.
- **Phase gate:** full suite green + `validate_copilot_yaml.py` exit 0 + runbook section check before `/gsd-verify-work`. Operator (live) items are checklist evidence, not automated gates.

---

## Per-Requirement Validation Map

| Req | Behavior | Type | Command / check | Status |
|-----|----------|------|-----------------|--------|
| PUB-04 | `useModelKnowledge=false` asserted offline | unit | `pytest …::test_useModelKnowledge_true_fails -x` | ✅ green |
| PUB-04 | agent-level `contentModeration=High` asserted | unit | `pytest …::test_moderation_not_high_fails -x` | ✅ green |
| PUB-04 | uniform High on each RAG node (existing check) | unit | `pytest -k moderation -x` | ✅ green |
| PUB-04 | validator gate runs as CI guardrail | smoke | `python scripts/validate_copilot_yaml.py` exit 0 (40 OK / 0 KO) | ✅ green |
| PUB-02 | no staging gateway host remains after prod cutover | unit | `pytest …::test_staging_host_in_prod_flagged -x` | ✅ green |
| PUB-01 | EU env region | manual | Power Platform Admin Center | ◷ operator |
| PUB-03 | Teams SSO completes without repeated prompts | manual | operator 1:1 sign-in checklist | ◷ operator |
| PUB-04 (live) | known-blocked prompt is blocked | manual | operator live prompt test → evidence | ◷ operator |
| PUB-05 | 1:1 personal install only (channel scope OFF) | manual | operator install + scope check | ◷ operator |

---

## Wave 0 Requirements

- [x] `tests/backend/test_validate_copilot_yaml.py` — PUB-04 (`useModelKnowledge`, `contentModeration`) + PUB-02 (staging-host fail-closed) — **7 passed**
- [x] No new fixtures; no framework install (pytest present)

---

## Manual-Only Verifications (operator checkpoints)

| Behavior | Req | Why Manual | Test Instructions |
|----------|-----|------------|-------------------|
| Live publish to Teams (1:1 personal) | PUB-05 | Copilot Studio + Teams admin UI | Publish; "Allow add to team" OFF; install as personal app; record evidence |
| EU env confirmation | PUB-01 | Live tenant | Power Platform Admin Center → env region EU |
| Teams SSO (manual Entra V2) reconfig + sign-in | PUB-03 | Live Entra + Teams; auth does NOT transfer on solution import | Reconfigure manual auth; 1:1 sign-in completes without repeated prompts |
| Connection-reference rebind | PUB-02a | Solution-import wizard (operator UI) | Bind refs to prod connections; set action endpoint = prod gateway URL + prod API audience |
| Known-blocked-prompt block | PUB-04 (live) | Needs live agent | Send a known-blocked prompt; confirm blocked; capture conversation-ID evidence (→ GUARDRAILS_VALIDATION.md §2) |

---

## Validation Sign-Off

- [x] PUB-04 + PUB-02 offline assertions added (validator + pytest)
- [x] Wave 0 test file created
- [x] Live items documented as operator checkpoints with evidence capture (GUARDRAILS_VALIDATION.md + runbook)
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-06-17 (audit-and-flip; offline guardrail gates green, live publish/SSO operator-gated).

## Validation Audit 2026-06-17

| Metric | Count |
|--------|-------|
| Requirements | 5 (PUB-01..05) |
| Automated & green (offline) | PUB-02, PUB-04 (validator exit 0 + 7 pytest) |
| Manual-only (operator) | PUB-01, PUB-03, PUB-05, PUB-04-live |
| Gaps found | 0 |
| Tests generated this audit | 0 |

Evidence: `validate_copilot_yaml.py` 40 OK / 0 KO (guardrails + anti-silent-RAG + dead-host wiring all clean); `test_validate_copilot_yaml.py` 7 passed. No nyquist-auditor spawn required.
