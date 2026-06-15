# Runbook 06 — Copilot Studio Production Publish (Teams 1:1)

**Owner:** solo operator · **Requirements:** PUB-01..05 · **Depends on:** Phase 2 (prod app registrations + gateway URL), Phase 3 (gateway deployed & answering `/health`).

> **Execution note.** Copilot Studio publish, Teams SSO, and the 1:1 install are **UI / admin actions** that require the live GEREP tenant + a Power Platform / Teams admin. This runbook is the operator procedure; the repo-side guardrail validation (PUB-04 offline) is already enforced by `scripts/validate_copilot_yaml.py` in CI and the gateway URLs are rebound to prod (Phase 04-01). Microsoft's publish UI changes often — **reconcile each step against the cited Microsoft Learn pages at execution time.**

---

## Prerequisites (gate — do not proceed until all true)

- [ ] Phase 2 applied live: `rg-ac360-prod` exists; prod **API audience** app registration created; OBO confidential client secret in Key Vault; admin consent granted (no AADSTS65001).
- [ ] Phase 3 applied live: prod gateway answers `https://ac360-gateway-prod.azurewebsites.net/health` → 200, and `/ready` (Entra-gated) → 200.
- [ ] You have **Power Platform admin** + **Teams admin** + an Entra **Application Administrator** (or equivalent) role.
- [ ] `python scripts/validate_copilot_yaml.py` exits 0 on the current repo (PUB-04 offline guardrail gate green).

---

## Step 0 — Confirm/select the EU prod Power Platform environment (PUB-01)

1. Power Platform Admin Center → Environments → confirm (or create) the **production** environment and that its **region is EU** (France / "France" or "Europe"). Record the env name + region.
2. Cross-ref **RGP-06** (EU residency) — the env region is part of the residency evidence.

> ✅ Acceptance: env region is EU; recorded. ❌ If not EU → STOP; do not import the solution.

---

## Step 1 — Import the AC360 solution & rebind connection references (PUB-02)

1. Export the AC360 solution from the source (or use the managed solution package).
2. Import into the **prod** environment. During the **import wizard**, bind each **connection reference** (from `src/copilot/AC360/connectionreferences.mcs.yml`) to the **prod** connections (SharePoint read-only connector signed in as the prod service/connection identity).
3. Set the **custom action endpoint** to the **prod gateway URL**: `https://ac360-gateway-prod.azurewebsites.net` (already rebound in the topic YAML by Phase 04-01 — verify the imported agent shows the prod host, not staging).
4. Set the action's **API audience / scope** to the prod API audience: `<PROD_API_AUDIENCE_SCOPE>` (the `api://<prod-api-app-id>/<scope>` value from the Phase 2 app-reg outputs — **do not** hardcode in the repo).

> ⚠️ **Authentication does NOT transfer on solution import** (Microsoft Learn) — you must reconfigure auth in Step 2 even if the source env had it.
> ✅ Acceptance: no `ac360-gateway-staging` host anywhere in the published agent; action endpoint + audience point at prod.

---

## Step 2 — Reconfigure Teams SSO via "Authenticate manually" (Entra ID V2) (PUB-03)

> **CRITICAL — auth mode.** Use **"Authenticate manually" (Microsoft Entra ID V2)**, NOT **"Authenticate with Microsoft."** Only manual auth exposes `System.User.AccessToken`, which every audit topic forwards to the gateway as the `Bearer` token. The zero-config "Authenticate with Microsoft" option exposes only `User.ID`/`DisplayName` and would **silently break every gateway call** (401 / no OBO).

1. Copilot Studio → **Settings → Security → Authentication** → **Authenticate manually**; **Require users to sign in** = ON.
2. Provide the Entra **OAuth** settings: client id/secret (or **federated credential** — preferred, no stored secret), token endpoints, scopes including the prod API audience scope, and the EU token-exchange redirect `https://europe.token.botframework.com/...`.
3. Configure **Teams SSO** per Microsoft Learn (Application ID URI `api://botid-<TeamsAppId>`, the two fixed Teams client IDs in the pre-authorized apps, token-exchange URL).
4. **Republish** the agent.

Cited: [configuration-authentication-azure-ad](https://learn.microsoft.com/en-us/microsoft-copilot-studio/configuration-authentication-azure-ad), [configure-sso-teams](https://learn.microsoft.com/en-us/microsoft-copilot-studio/configure-sso-teams), [configuration-end-user-authentication](https://learn.microsoft.com/en-us/microsoft-copilot-studio/configuration-end-user-authentication).

> ✅ Acceptance: auth mode = manual Entra V2; agent republished after the change.

---

## Step 3 — Publish to Teams as a 1:1 personal install (PUB-05)

> **Why 1:1 only.** AC360 uses **OBO / user-delegated SharePoint access** and **SharePoint RAG**, which Microsoft Learn states are **supported only in 1:1 chats**. Group/meeting chats don't support manual-auth SSO. Therefore: **personal scope only; "Allow add to team/channel" = OFF.**

1. Copilot Studio → **Channels → Teams + Microsoft 365** → enable; **Availability options**.
2. Set scope to **personal (1:1)**; ensure team/channel scope is **OFF**.
3. Distribution for the target team:
   - **Preferred (covers mobile):** Submit for **admin approval** → approve in **Teams Admin Center → Manage apps** → assign via an app **setup/permission policy** scoped to the target team.
   - **Desktop-only alternative:** share the install link (works on desktop/web, not Teams mobile).
4. Cross-ref **GO-02** (feature-flag gating restricts actual use to exactly the target team).

Cited: [publication-add-bot-to-microsoft-teams](https://learn.microsoft.com/en-us/microsoft-copilot-studio/publication-add-bot-to-microsoft-teams), [knowledge-copilot-studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/knowledge-copilot-studio).

> ✅ Acceptance: agent installable as a personal app for the target team; channel/team scope OFF.

---

## Step 4 — Acceptance tests (operator, live)

1. **Teams 1:1 sign-in (PUB-03):** open the agent in a Teams 1:1 chat as a target-team user → sign-in completes **without repeated prompts** and without auth failure. (If repeated prompts: re-check Step 2 SSO config + token-exchange URL.)
2. **End-to-end smoke:** run one read-only search → returns grounded SharePoint citations (no model world-knowledge).
3. **Known-blocked-prompt (PUB-04 live):** send a known-blocked prompt (e.g. a prompt-injection / exfiltration attempt) → the agent **blocks** it (contentModeration High). Capture the conversation ID as evidence in `docs/security/GUARDRAILS_VALIDATION.md`.
4. **OBO scope:** confirm a SharePoint document the signed-in user can access is retrievable, and one they cannot is not (user-scoped OBO honored).

---

## Dry-run / validation (offline — runnable now, before any live tenant)

- [ ] `python scripts/validate_copilot_yaml.py` → exit 0 (PUB-04 guardrails: `useModelKnowledge=false`, agent `contentModeration=High`, uniform High RAG moderation, no staging host).
- [ ] `python -m pytest tests/backend/test_validate_copilot_yaml.py -x` → green.
- [ ] `grep -r ac360-gateway-staging src/copilot` → no matches (PUB-02 cutover complete).
- [ ] Confirm `src/copilot/AC360/settings.mcs.yml` `configuration.aISettings` has `useModelKnowledge: false` and `contentModeration: High`.

---

## Rollback / abort

- If sign-in or guardrails fail post-publish: **unpublish** (or remove the Teams app assignment) to take the agent offline for the team, fix the config, republish. The gateway itself rolls back via runbook **02-rollback.md**.

---

## Evidence to capture (feeds Phase 5)

- EU env name + region (PUB-01 / RGP-06).
- Screenshot: auth mode = "Authenticate manually" (PUB-03).
- Screenshot: channel scope OFF / personal-only (PUB-05).
- Conversation ID of the blocked prompt (PUB-04 live) → `docs/security/GUARDRAILS_VALIDATION.md`.
