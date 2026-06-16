---
phase: 06-controlled-e2e-go-no-go-team-rollout
plan: 02
status: complete
completed: 2026-06-14
requirements: [GO-02]
test_result: "test_feature_flags_allowlist 8 passed; 14 related green, no regression"
---

# Plan 06-02 Summary — Allowlist gating (GO-02)

Executed inline. Added allowlist mode to `scripts/feature_flags.py`: env vars `AC360_ALLOWED_USERS_HASHED` / `AC360_ALLOWED_TEAMS`; `is_user_allowlisted` / `is_team_allowlisted` (empty ⇒ True/no-restriction = backward-compatible; set ⇒ only-listed-pass, None-caller denied). Wired into `is_allowed` AFTER the block checks (a block always overrides an allow), returning `user_not_allowlisted` / `team_not_allowlisted`; added French user messages. Combined with the Phase 4 Teams 1:1 install scope for "exactly the target team."

**Verification:** 8 allowlist tests + 14 related green; no regression to the existing blocklist model. The `is_allowed(...)` signature is unchanged (api_server call site untouched). Live application of the allowlist to the target team is an operator step (runbook 08).
