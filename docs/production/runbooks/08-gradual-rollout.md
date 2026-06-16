# Runbook 08 — Gradual Rollout (GO-04)

**Owner:** solo operator · **Requirement:** GO-04 · **Precondition:** runbook 07 Go/No-Go = **GO** (incl. DPO DPIA sign-off).

> Roll out AC360 to the target team in two steps using the allowlist as the lever: a small pilot, then the full team after a sustained clean signal. Abort at any point to the rollback / kill-switch runbooks.

---

## Lever: the allowlist (GO-02)

- `AC360_ALLOWED_USERS_HASHED` = comma-separated `hash_id(oid)` of the currently-allowed users (deny-by-default when set).
- Optionally `AC360_ALLOWED_TEAMS` for team-scoped gating.
- To compute a user hash: `python -c "import sys; sys.path.insert(0,'scripts'); from feature_flags import hash_id; print(hash_id('<oid>'))"`.
- Changing the env var on the single gateway instance + restart applies the new perimeter (no redeploy).

---

## Step 1 — Pilot cohort (2–5 users)

1. Set `AC360_ALLOWED_USERS_HASHED` to the hashed oids of **2–5 pilot users** from the target team.
2. Confirm a non-pilot user is denied (`user_not_allowlisted`) and a pilot user is allowed.
3. Announce to pilots; capture first-use feedback.

## Step 2 — Observation window (24–48 h)

Watch the dashboard + alerts for a **sustained clean signal** before expanding.

**Clean-signal criteria (ALL must hold for 24–48 h):**
- [ ] No **Sev1/Sev2** alerts fired (gateway 5xx, Functions/orchestration errors, dependency failures).
- [ ] Gateway + Functions **error rate below threshold** (e.g. < 2% of requests).
- [ ] **No PII-leak** finding in telemetry (re-run `no_pii_kql` spot-check).
- [ ] **Budget** within bound (no FinOps budget alert).
- [ ] No unresolved pilot-reported correctness issue (wrong verdict, broken OBO).

## Step 3 — Full team

1. Only after a clean 24–48 h signal: expand `AC360_ALLOWED_USERS_HASHED` (or switch to `AC360_ALLOWED_TEAMS` = the target team) to the **full target team**.
2. Confirm allowlist still denies anyone outside the target team.
3. Continue monitoring for a further 24–48 h.

---

## Abort / rollback (any step)

**Abort triggers:** a Sev1 alert, error-rate spike above threshold, any confirmed PII leak, a budget breach, or a correctness regression.

- **Instant containment:** runbook **05-killswitch.md** — flip a feature flag (`AC360_AUDIT_ENABLED=false` / block user/team) or shrink the allowlist to zero pilots.
- **Code/infra rollback:** runbook **02-rollback.md** — redeploy the previous known-good tag (<10 min; B1 has no slots).
- Record the abort cause; return to runbook 07 before re-attempting.

---

## Dry-run / validation (offline)

- Allowlist lever verified by `tests/backend/test_feature_flags_allowlist.py` (set ⇒ deny-by-default; unset ⇒ no restriction; block overrides).
- `hash_id` command above runs offline.
- Clean-signal criteria reference the Phase 3 alerts/dashboard/budget + the GO-01 no-PII check.
