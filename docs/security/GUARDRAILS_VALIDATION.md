# AC360 — Guardrails Validation Evidence (PUB-04)

**Purpose:** Evidence that AC360's no-hallucination / content-safety guardrails are enforced, both **offline** (repo + CI) and **live** (against the published agent). Feeds Phase 5 — **SEC-03** (threat-coverage matrix) and **SEC-04** (posture).

**Last updated:** 2026-06-14 (offline section complete; live section awaits operator post-publish).

---

## 1. Offline evidence (automated, CI-gated) — COMPLETE

The guardrail posture is asserted offline against the repo by `scripts/validate_copilot_yaml.py` (runs in CI, `ci.yml`) and unit-tested by `tests/backend/test_validate_copilot_yaml.py`.

| Guardrail | Source of truth | Asserted by | Status |
|-----------|-----------------|-------------|--------|
| **No model world-knowledge** (`useModelKnowledge: false` — grounded/RAG-only answers, no fabricated "general knowledge" presented as client fact) | `src/copilot/AC360/settings.mcs.yml` → `configuration.aISettings.useModelKnowledge` | `validate_copilot_yaml.find_agent_guardrail_issues` (fails if not exactly `false`) + `test_useModelKnowledge_true_fails` | ✅ enforced |
| **Agent-level content moderation = High** (strictest RAI filter: jailbreak / prompt-injection / exfiltration) | `settings.mcs.yml` → `configuration.aISettings.contentModeration` | `find_agent_guardrail_issues` (fails if `!= High`) + `test_moderation_not_high_fails` | ✅ enforced |
| **Uniform High moderation on every RAG node** (`SearchAndSummarizeContent` `moderationLevel: High`; no low-moderation high-traffic topic) | each topic `.mcs.yml` RAG node | `validate_copilot_yaml.find_rag_node_issues` (`RAG_REQUIRED_MODERATION = "High"`) | ✅ enforced (pre-existing) |
| **Validator gate runs in CI** | `.github/workflows/ci.yml` → `validate_copilot_yaml.py` | exit 0 required | ✅ enforced |
| **No staging gateway host shipped to prod** (PUB-02 cutover) | `src/copilot/AC360/topics/*.yml` | `find_wiring_issues` staging-host fail-closed + `test_staging_host_in_prod_flagged` | ✅ enforced |

**Reproduce:**
```
python scripts/validate_copilot_yaml.py        # exit 0
python -m pytest tests/backend/test_validate_copilot_yaml.py -x
```
Last run (2026-06-14): validator **exit 0** ("0 KO"); 7/7 tests pass; full suite 211 passed / 1 skipped.

---

## 2. Live evidence (operator, post-publish) — PENDING

To be completed by the operator after the agent is published (runbook `docs/production/runbooks/06-copilot-publish.md`, Step 4) against the live Teams 1:1 agent.

| Live check | Requirement | Evidence to capture | Status |
|------------|-------------|---------------------|--------|
| **Known-blocked prompt is blocked** | PUB-04 (live) | Conversation ID + screenshot of a prompt-injection / system-prompt-exfiltration attempt being refused by the agent (contentModeration High) | ◷ pending |
| **Grounded-only answer** | PUB-04 | A query answered only from SharePoint citations; a "general knowledge" question NOT answered from model world-knowledge | ◷ pending |
| **OBO user-scoping honored** | PUB-05 / AUD-03 | A doc the user can access is retrievable; one they cannot is not | ◷ pending |
| **No PII leak in telemetry** | AUD-06 / GO-01 | App Insights trace of the above shows redacted dimensions (cross-ref Phase 3 RedactingSpanProcessor) | ◷ pending (also GO-01) |

> Record conversation IDs / screenshots here (or link to a secure evidence store) when performed.

---

## 3. Cross-references

- Repo gate: `scripts/validate_copilot_yaml.py`, `tests/backend/test_validate_copilot_yaml.py`.
- Telemetry redaction (AUD-06): `scripts/telemetry.py` (RedactingSpanProcessor), `scripts/safe_logger.py`.
- Phase 5 consumers: **SEC-03** (threat-coverage matrix — maps OWASP LLM risks → these guardrails → tests), **SEC-04** (dependency/vuln posture).
- Go-live: **GO-01** (controlled E2E telemetry no-PII-leak check reuses the live evidence above).
