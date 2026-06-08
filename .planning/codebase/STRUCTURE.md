# Codebase Structure

**Analysis Date:** 2026-06-08

## Directory Layout

```
AC360/
├── scripts/                  # Backend: API gateway + pipeline stages + PowerShell orchestration
│   ├── api_server.py         # FastAPI gateway (entry point)
│   ├── auth.py               # Entra ID JWT verification
│   ├── safe_logger.py        # Redacting security logger
│   ├── process_document_ocr.py    # P3: Azure Document Intelligence OCR
│   ├── audit_fabric_comparison.py # P4: Fabric/Artus fuzzy audit
│   ├── generate_fic_draft.py      # P6: FIC Word draft + rule gate
│   ├── post_audit_workflow.py     # P5: Teams alert, archive, RGPD cleanup
│   ├── generate_fiche_rdv.py      # RDV sheet generator (gateway helper)
│   ├── planner_integration.py     # Microsoft Graph Planner tasks
│   ├── db_manager.py              # SQLite FIC tracking
│   ├── run_audit_pipeline.ps1     # Orchestrator (P3→P4→P6→P5)
│   ├── deploy_azure_ocr.ps1, sync_copilot.ps1, scan_secrets.ps1, ...  # Ops scripts
│   └── requirements.txt
├── azure_functions/          # Azure Durable Functions (orchestration backend)
│   ├── host.json
│   ├── local.settings.json
│   └── __pycache__/          # function_app/audit_engine/rdv_engine ONLY as .pyc (source absent)
├── src/
│   ├── main.py               # Tkinter desktop PDF/Excel audit UI
│   ├── core.py               # Parsers, fuzzy match, écart calc, SQLite history
│   ├── requirements.txt
│   ├── copilot-workspace/AC360/   # CANONICAL Copilot Studio project
│   │   ├── agent.mcs.yml
│   │   ├── settings.mcs.yml, connectionreferences.mcs.yml
│   │   ├── topics/*.mcs.yml        # Dialogs (LancerAudit, system topics, commercial topics)
│   │   ├── actions/*.mcs.yml       # Connector actions (WorkIQ, SharePoint MCP)
│   │   ├── knowledge/*.mcs.yml     # SharePoint RAG sources
│   │   └── .mcs/                   # Studio metadata (botdefinition.json, conn.json)
│   └── copilot/AC360/             # Export/backup copy of topics + knowledge
├── tests/                    # pytest suites by domain
│   ├── backend/              # auth, job isolation, OCR/Fabric, path traversal, logger
│   ├── copilot/              # topic integrity, silent-success, hardened RAG
│   ├── red_team/             # automated red-team prompts
│   ├── security/             # forbidden files, plaintext secrets
│   └── evaluation/
├── docs/                     # architecture, security, governance, alm, product, copilot, rag
├── prompts/                  # System prompt + example/test questions
├── .planning/                # GSD phases, roadmap, requirements, state, codebase maps
├── conftest.py, setup.cfg    # Test config
├── requirements.txt
├── .env.example, .gitleaks.toml
└── AGENTS.md, README.md
```

## Directory Purposes

**`scripts/`:**
- Purpose: All backend logic — the FastAPI gateway, the six-phase pipeline stages, and PowerShell orchestration/ops.
- Key files: `api_server.py`, `audit_fabric_comparison.py`, `process_document_ocr.py`, `generate_fic_draft.py`, `post_audit_workflow.py`, `run_audit_pipeline.ps1`.

**`azure_functions/`:**
- Purpose: Azure Durable Functions orchestration host (production target proxied by the gateway).
- Note: Python source for the functions is currently only compiled `.pyc` under `__pycache__/`.

**`src/copilot-workspace/AC360/`:**
- Purpose: Canonical Microsoft Copilot Studio agent definition and topics.
- Key files: `agent.mcs.yml`, `topics/LancerAudit.mcs.yml`.

**`src/` (main.py / core.py):**
- Purpose: Standalone Tkinter desktop reconciliation tool, independent of the cloud pipeline.

**`tests/`:**
- Purpose: pytest suites split by domain (backend, copilot, red_team, security, evaluation).

## Key File Locations

**Entry Points:**
- `scripts/api_server.py`: FastAPI gateway (`uvicorn`, port 8000).
- `scripts/run_audit_pipeline.ps1`: full pipeline orchestrator.
- `src/copilot-workspace/AC360/agent.mcs.yml`: conversational entry.
- `src/main.py`: desktop app.

**Configuration:**
- `scripts/config.py`: gateway config (JWKS_URL, CLIENT_ID, JOBS_BASE_DIR, scopes/roles) — imported but not present as `.py` source in tree (compiled `config.cpython-312.pyc` only).
- `azure_functions/host.json`, `azure_functions/local.settings.json`.
- `.env.example`, `setup.cfg`, `conftest.py`.

**Core Logic:**
- `scripts/audit_fabric_comparison.py`: fuzzy matching + comparison engine.
- `src/core.py`: desktop parsers and écart calculator.

**Testing:**
- `tests/backend/`, `tests/copilot/`, `tests/security/`, `tests/red_team/`.

## Naming Conventions

**Files:**
- Python pipeline stages: `snake_case.py`, verb-led (`process_document_ocr.py`, `generate_fic_draft.py`).
- PowerShell: `snake_case.ps1` (`run_audit_pipeline.ps1`).
- Copilot topics: `PascalCase` or French label-derived names with `.mcs.yml` suffix (`LancerAudit.mcs.yml`).
- Tests: `test_<subject>.py` under domain subdirectory.

**Directories:**
- Lowercase, domain-named (`scripts`, `azure_functions`, `tests/backend`).

## Where to Add New Code

**New pipeline phase:**
- Stage script: `scripts/<verb>_<subject>.py` with an `argparse` `main()` reading the upstream JSON artifact and writing a new JSON artifact.
- Wire it into `scripts/run_audit_pipeline.ps1` as a new `Write-JsonLog`-bracketed phase block.

**New API endpoint:**
- Add a Pydantic request model and `@app.post`/`@app.get` handler in `scripts/api_server.py`, guarded by `Depends(verify_azure_ad_token)`; offload sync I/O with `run_in_threadpool`.

**New Copilot capability:**
- Add a topic under `src/copilot-workspace/AC360/topics/*.mcs.yml`; back it with an API endpoint via `HttpRequestAction`. Mirror into `src/copilot/AC360/` only on export.

**New Azure Function activity:**
- Add to `azure_functions/` (commit source alongside the existing `host.json`).

**Tests:**
- Place under the matching `tests/<domain>/` subdirectory as `test_*.py`.

**Shared helpers:**
- Cross-cutting backend utilities go in `scripts/` (e.g., logging in `safe_logger.py`).

## Special Directories

**`azure_functions/__pycache__/`:**
- Purpose: Compiled Durable Functions bytecode.
- Generated: Yes. Committed: Yes (currently the only form of this source).

**`.claude/worktrees/`:**
- Purpose: Git worktrees from agent runs (contain duplicate `scripts/`).
- Generated: Yes. Treat as non-canonical; do not edit production code here.

**`.planning/`:**
- Purpose: GSD phase plans, roadmap, requirements, and these codebase maps.
- Committed: Yes.

---

*Structure analysis: 2026-06-08*
