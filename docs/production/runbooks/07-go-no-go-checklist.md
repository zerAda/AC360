# Runbook 07 — AC360 Go/No-Go Checklist (GO-03)

**Owner:** solo operator · **Requirement:** GO-03 (operator-signed) · **Decision:** GO / NO-GO before opening AC360 to the target team.

> Single consolidated go-live punch-list. Every box must be ✅ (or an explicit, signed risk acceptance) before GO. This is the **hard gate** before the gradual rollout (runbook 08).

---

## A. Code & audit (Phase 1)

- [ ] All AUD-01..08 complete; full test suite green (`pytest` → 230+ passed).
- [ ] `docs/security/SECURITY_POSTURE.md` reviewed; WR-01 `_assert_durable_owner` runtimeStatus contract confirmed against the deployed Durable status webhook.

## B. Infrastructure (Phase 2) — LIVE

- [ ] `rg-ac360-prod` provisioned in **EU** (France Central); `az bicep build` + `validate_infra.ps1` green.
- [ ] **EU residency confirmed** live: M365 tenant geo, Fabric capacity region, Power Platform env region (RGP-06). _Operator checkpoint — Plan 02-06._
- [ ] OBO **admin consent** granted in the prod tenant; `az ad app permission list-grants` shows expected scopes; **no AADSTS65001** (INF-06).
- [ ] All secrets in Key Vault (zero cleartext); MI role assignments live; KV/DocIntel private endpoints up before public-access flip.

## C. Deploy & observability (Phase 3) — LIVE

- [ ] `cd-prod.yml` first deploy succeeded (OIDC, what-if reviewed, prod-Environment approval); gateway `/health` 200 + `/ready` over Entra TLS.
- [ ] App Insights wired (both apps); failure alerts fire; availability test green; **one-pane dashboard** renders; **budget alert** wired to a real sink.
- [ ] `gatewayOutboundIps` populated in `prod.parameters.json` (ingress deny-all armed).
- [ ] Five operator runbooks (01-05) reviewed; rollback (<10 min) dry-run understood.

## D. Copilot publish (Phase 4) — LIVE

- [ ] Agent published to Teams as **1:1 personal install** (channel scope OFF); manual Entra V2 + Teams SSO; 1:1 sign-in completes without repeated prompts.
- [ ] **Guardrails live-validated**: a known-blocked prompt is blocked; `useModelKnowledge=false` + High moderation confirmed (PUB-04 / `GUARDRAILS_VALIDATION.md` §2).

## E. Compliance (Phase 5) — DPO HARD GATE

- [ ] **DPIA DPO-signed (RGP-02)** — _hard gate; no GO without it._
- [ ] **Art. 30 record DPO-finalized (RGP-01)**.
- [ ] Retention enforcement live (storage lifecycle + JOBS_BASE_DIR TTL; ~37-day effective window disclosed); Log Analytics retention 90 d (RGP-03/04).
- [ ] DSR procedure + EU-residency confirmation reviewed (RGP-05/06).

## F. Controlled E2E (Phase 6) — LIVE

- [ ] `scripts/e2e_smoke.py` run against prod with **synthetic** client/doc: happy CONFORME + ECART+FIC + CLIENT_NON_TROUVE + OCR-timeout + Fabric-down → expected verdicts (GO-01).
- [ ] **No-PII telemetry check** (`no_pii_kql`) → count 0 in App Insights for the E2E run (GO-01 / AUD-06 / RGP-04).

## G. Gating (Phase 6)

- [ ] `AC360_ALLOWED_USERS_HASHED` (and/or `AC360_ALLOWED_TEAMS`) set to **exactly the target team's** members (GO-02); allowlist fail-safe verified (set ⇒ deny-by-default).
- [ ] Kill-switch (runbook 05) confirmed working.

---

## Decision

| Field | Value |
|-------|-------|
| Date | __________ |
| Operator | __________ |
| All A-G boxes ✅ (or signed risk acceptance attached)? | YES / NO |
| **Decision** | **GO** / **NO-GO** |
| Signature | __________ |

> On **GO** → proceed to runbook **08-gradual-rollout.md**. On **NO-GO** → record blocking item(s); do not open to users.

## Dry-run / validation (offline)

- This checklist is reviewable now; boxes B-F require the live stack + DPO sign-off.
- `grep -c "## " 07-go-no-go-checklist.md` ≥ 8 sections; references DPIA, E2E, allowlist, rollback.
