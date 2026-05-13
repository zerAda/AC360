---
phase: 01
slug: setup-agent-creation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-28
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | N/A — No-code Copilot Studio platform |
| **Config file** | Copilot Studio portal (manual) |
| **Verification** | Manual via Teams/SharePoint UI |
| **API Available** | Microsoft Copilot Studio API (future) |

**Note:** Phase 1 validation is primarily manual since it involves configuring a no-code agent in Copilot Studio. Automated verification would require Copilot Studio API integration.

---

## Verification Approach

### Manual Verifications Required

| Behavior | Requirement | Verification Method |
|----------|-------------|---------------------|
| Agent exists in Copilot Studio | CFA-01 | Web UI check |
| SharePoint connected | CFA-02 | Portal configuration check |
| Agent accessible via Teams | QI-01 | Send test message in Teams |
| Agent accessible via SharePoint | QI-02 | Open agent in SharePoint |
| Natural language understanding | QI-03 | Test with sample questions |
| Permissions respected | CFA-03, CFA-04 | Test with different user accounts |
| "Not found" response | SAF-01 | Ask about non-existent topic |
| Clarification request | SAF-04 | Use ambiguous client name |

### Automated (Future)

- Copilot Studio Management API for configuration validation
- Teams API for message testing
- SharePoint API for content verification

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Verification |
|---------|------|------|-------------|------------|-----------------|-----------|--------------|
| 01-01-01 | 01 | 1 | QI-01 | — | N/A | Manual | Send message in Teams |
| 01-01-02 | 01 | 1 | CFA-01 | — | N/A | Manual | Check portal |
| 01-01-03 | 01 | 1 | QI-02 | — | N/A | Manual | Open in SharePoint |
| 01-02-01 | 02 | 1 | CFA-02 | — | N/A | Manual | Check knowledge source |
| 01-02-02 | 02 | 1 | CFA-03 | T-01-01 | Permissions enforced | Manual | Test with restricted user |
| 01-02-03 | 02 | 1 | CFA-04 | T-01-01 | Content filtered | Manual | Verify filtering |
| 01-03-01 | 03 | 1 | QI-03 | — | N/A | Manual | Test NLP queries |
| 01-03-02 | 03 | 1 | SAF-01 | T-01-02 | Safe responses | Manual | Test edge cases |
| 01-03-03 | 03 | 1 | SAF-04 | T-01-02 | Clarification | Manual | Test ambiguous input |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Agent creation | CFA-01 | No-code platform | Open Copilot Studio, verify agent exists |
| SharePoint connection | CFA-02 | Portal configuration | Check knowledge sources in agent settings |
| Teams channel | QI-01 | UI interaction | Open Teams, find agent, send message |
| SharePoint channel | QI-02 | UI interaction | Navigate to SharePoint page with agent |
| Permission enforcement | CFA-03, CFA-04 | SharePoint model | Test with different user accounts |
| Response quality | QI-03 | LLM behavior | Test with various natural language queries |
| Safety responses | SAF-01, SAF-04 | LLM behavior | Test edge cases |

---

## Validation Sign-Off

- [ ] All tasks have manual verification defined
- [ ] Manual verification steps documented for each requirement
- [ ] No automated framework required for POC
- [ ] nyquist_compliant: true (manual verification mode)

**Approval:** pending

---

*Validation strategy created: 2026-04-28*
*Note: Copilot Studio is a no-code platform - validation is primarily manual verification of agent configuration and behavior*