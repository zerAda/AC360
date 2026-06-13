# Deferred Items — Phase 01 (deep-code-audit-critical-fixes)

Out-of-scope discoveries logged during execution. Not fixed in the originating plan.

| Discovered in | Item | Why deferred |
|---------------|------|--------------|
| 01-06 | `resolve_document` and `api_create_planner_task` OBO call sites still use the non-retrying `acquire_obo_graph_token` and return 502 on failure. | Plan 01-06 scoped AUD-05 to the audit-path OBO exchange only. AUD-05 consistency (retry wrapper + 503) on these secondary OBO sites is a follow-up. |
