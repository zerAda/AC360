# AC360

## What This Is

AC360 is a read-only commercial assistant for Microsoft Teams, built on Microsoft Copilot Studio with a Python backend (FastAPI + Azure Durable Functions). It lets commercial/insurance staff search SharePoint client folders and run automated document audits — extracting fields via OCR, comparing them against the Fabric/ARTUS reference system, and producing a conformity verdict (CONFORME / ECART / INCERTAIN / CLIENT_NON_TROUVE) plus an optional FIC draft — all under strict security guardrails (Entra ID SSO, user-scoped permissions, no hallucinations).

The application is feature-complete and security-hardened in the repository but has **never been deployed**. This milestone takes the existing AC360 from local/dev to a live, stable, compliant production service for one internal team.

## Core Value

AC360 is live in production — a 20–100 person team can reliably and compliantly audit client documents from Teams, end-to-end, and one person can operate it with confidence.

## Requirements

### Validated

<!-- Inferred from existing code (brownfield). Shipped in-repo and relied upon; confirmed by the production launch, not yet by real-user usage. -->

- ✓ Document audit pipeline: OCR → Fabric/ARTUS lookup → compare → verdict — existing
- ✓ FIC draft generation (Word) for ECART/INCERTAIN verdicts — existing
- ✓ Native Copilot Studio RAG search over SharePoint client folders — existing
- ✓ Document resolution/search endpoint (`/api/document/resolve`) — existing
- ✓ Entra ID SSO with JWT RS256 (JWKS) validation — existing
- ✓ On-Behalf-Of delegated SharePoint access (user-scoped Graph) — existing
- ✓ Feature flags & admin gates (per-user / per-team / per-feature blocking) — existing
- ✓ Security hardening: IDOR protection, path-traversal guards, rate limiting, safe/PII-redacting logging, no-hallucination guardrails — existing
- ✓ Bicep Infrastructure-as-Code for Azure resources — existing
- ✓ Test suite (30+ files: auth, OBO, rate limit, IDOR, path traversal, OCR timeout, red-team) — existing

### Active

<!-- This milestone: production launch of the full app. -->

- [ ] Deep audit of the existing codebase to surface and fix bugs, issues, and quality/security gaps before launch
- [ ] Deploy the Azure backend (FastAPI gateway + Azure Durable Functions) to production
- [ ] Publish the Copilot Studio agent to Teams for the target team
- [ ] Controlled real-production end-to-end test using a known test client/document, before opening to the team
- [ ] Production monitoring (Application Insights) and alerting on failures/budget
- [ ] Operational runbooks written for a single operator (deploy, rotate secrets, triage, rollback)
- [ ] Internal security review readiness (documented posture, threat coverage evidence)
- [ ] GDPR/RGPD compliance evidence (PII handling, data retention, DPIA for client data)

### Out of Scope

<!-- Explicit boundaries for THIS milestone, with reasoning. -->

- New audit types (new document categories / comparison rules) — deferred to a future milestone; deploy what exists first
- New conversation topics / use cases — deferred to a future milestone; not required for go-live
- Write/action capabilities (beyond read-only) — read-only enforcement is a core guardrail; out of scope by design
- New integrations (additional data sources / downstream systems) — deferred; current integrations are sufficient for launch
- Rewriting or re-architecting the application — milestone deploys the existing, hardened codebase, not a refactor

## Context

- **Brownfield, undeployed.** The codebase is mature and recently hardened (uniform High moderation on RAG nodes, validator gate, Bicep IaC, OCR deadline, IDOR + doc_id E2E tests). A full codebase map exists at `.planning/codebase/`.
- **Stack (locked):** Python 3.12, FastAPI/Uvicorn, Azure Functions (Durable, Python v2), Microsoft Copilot Studio, Microsoft Fabric (OneLake/Delta + SQL endpoint), Azure Document Intelligence (OCR), Azure Key Vault, Application Insights. Frontend conversational layer publishes to Teams via Copilot Studio.
- **Deployment shape:** Copilot Studio hosts the agent (Teams); the Azure backend must be provisioned/hosted so the audit pipeline works. Both halves ship together ("full app") at launch.
- **Domain:** French insurance / commercial client-data context (ARTUS reference system, "FIC" drafts, SIRET lookups) — implies RGPD obligations on client PII.
- **Operator model:** Solo operator owns production. Runbooks and alerting must assume one person, not an ops team.
- **Launch sequence:** audit & fix existing → deploy full app → controlled real-prod E2E (known test client/doc) → close ops gaps → satisfy compliance → open to the team.

## Constraints

- **Tech stack**: Locked to the existing stack — this milestone deploys what exists; no rewrites or new frameworks.
- **Operability**: Single operator — monitoring, alerting, and runbooks must be usable by one person.
- **Compliance**: EU/French data protection (RGPD/GDPR) applies to client PII — retention, PII handling, and DPIA evidence required before go-live.
- **Security**: Read-only enforcement and no-hallucination guardrails must be preserved through deployment.
- **Platform**: Requires an Azure subscription and an M365 tenant (Entra ID, SharePoint, Teams, Copilot Studio).
- **Timeline**: ASAP but no hard deadline — quality and compliance take priority over speed.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Deploy what exists first; defer new audit types/topics | Get the hardened app live and stable before expanding scope | — Pending |
| Ship the full app (agent + backend), not RAG-first | Document audit is AC360's core value; launching without it loses the point | — Pending |
| Gate launch behind a deep codebase audit | Prove the committed hardening is actually complete; catch bugs before real users | — Pending |
| E2E test in real production, controlled (known test client/doc) | A true end-to-end proof against real services before opening to the team | — Pending |
| Runbooks/monitoring designed for a solo operator | Production is owned by one person; ops must be sustainable at that scale | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-13 after initialization*
