---
phase: 01-deep-code-audit-critical-fixes
fixed_at: 2026-06-13T00:00:00Z
review_path: .planning/phases/01-deep-code-audit-critical-fixes/01-REVIEW.md
iteration: 2
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
test_result: "197 passed, 1 skipped"
---

# Phase 01 — Code Review Fix Report

All in-scope (Critical + Warning) findings resolved across two iterations. Full suite green (197 passed, 1 skipped), mypy clean on strict core modules, flake8 clean.

## Iteration 1 — 6 warnings fixed (gsd-code-fixer)

| Finding | Fix | Commit |
|---------|-----|--------|
| WR-06 | `log_security` redacts the structured `data` dict via `redact_mapping` (was message-only); signature `Optional[dict] -> None` | `054a0c1` |
| WR-02 | `_retry_after_seconds` rejects non-positive / non-numeric and clamps to 30s (no thread-pinning, no `sleep(negative)`) | `837f702` |
| WR-03 | overflow cleanup guard added to `_check_resolve_rate_limit` (`> 1000`) | `0ecfb43` |
| WR-01 | `_assert_durable_owner` fails closed (403) on terminal jobs missing `owner_hash`; tolerates only the transient pre-input window | `a30a95c` |
| WR-04/WR-05 | `resolve_document` + `api_create_planner_task` route OBO through `acquire_obo_graph_token_retrying` → 503; dynamic detail moved to redacted `data=` channel | `35b4f18` |
| (doc) | deferred AUD-05 OBO-consistency item marked RESOLVED in `deferred-items.md` | `2bdc97d` |

Iteration-1 added 9 regression tests (test_audit_ownership.py fail-closed cases, realistic owner_hash fixtures, retrying-wrapper patches).

## Iteration 2 — re-review + 1 regression fixed (orchestrator inline)

| Finding | Fix | Commit |
|---------|-----|--------|
| WR-07 | WR-04 left `acquire_obo_graph_token` (non-retrying) imported-but-unused in `api_server.py` → flake8 F401 (CI-blocking). Removed the dead symbol from the import. | (committed with this report) |

Re-review confirmed all six iteration-1 fixes correct and complete with no other regressions.

## Carried forward (non-blocking)

- **WR-01 human-verify:** the terminal-vs-transient `runtimeStatus` split in `_assert_durable_owner` must be confirmed against the deployed Durable status-webhook contract before go-live. Recorded for operator verification.
- **4 Info findings** (IN-02/03/04/06 et al.): accepted non-blocking carried items, out of the `critical_warning` fix scope. Documented in 01-REVIEW.md.
