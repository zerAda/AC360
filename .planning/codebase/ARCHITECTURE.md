<!-- refreshed: 2026-06-08 -->
# Architecture

**Analysis Date:** 2026-06-08

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                     CONVERSATIONAL LAYER (Copilot Studio)                 │
│  Agent + Topics (.mcs.yml)        SharePoint knowledge (read-only RAG)    │
│  `src/copilot-workspace/AC360/`   `src/copilot/AC360/`                    │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ HttpRequestAction (POST /api/audit)
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       API GATEWAY (FastAPI)                               │
│  `scripts/api_server.py`  — Entra ID JWT auth, rate-limit, App Insights   │
└──────────────┬──────────────────────────────────────┬─────────────────────┘
               │ proxy /api/audit                      │ Planner / Fiche RDV
               ▼                                       ▼
┌──────────────────────────────────┐   ┌─────────────────────────────────────┐
│  ORCHESTRATION                   │   │  SYNC HELPERS (threadpool)          │
│  Azure Durable Functions (Azure) │   │  `generate_fiche_rdv.py`            │
│  `azure_functions/` (host.json)  │   │  `planner_integration.py`           │
│  also: `run_audit_pipeline.ps1`  │   └─────────────────────────────────────┘
└──────────────┬───────────────────┘
               │ phase chain (3 → 4 → 6 → 5)
               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       AUDIT PIPELINE (Python CLI scripts)                 │
│  P3 OCR            P4 Fabric audit        P6 FIC          P5 post-audit    │
│  process_document  audit_fabric_          generate_fic_   post_audit_      │
│  _ocr.py           comparison.py          draft.py        workflow.py      │
└──────────────┬─────────────┬──────────────────┬────────────────┬──────────┘
               ▼             ▼                  ▼                ▼
        Azure Document  Microsoft Fabric   python-docx      Teams webhook
        Intelligence    (Artus SQL)        (.docx FIC)      + SQLite tracking
                                                            `audits.db`
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Copilot agent | Read-only commercial assistant, SharePoint RAG, citation rules | `src/copilot-workspace/AC360/agent.mcs.yml` |
| Audit trigger topic | Collects document ID, POSTs to API gateway | `src/copilot-workspace/AC360/topics/LancerAudit.mcs.yml` |
| API gateway | Auth, rate-limit, proxy to Azure Functions, file download | `scripts/api_server.py` |
| JWT verifier | Entra ID token validation (JWKS, issuer, scope, role) | `scripts/auth.py` |
| OCR extractor (P3) | Azure Document Intelligence → structured JSON | `scripts/process_document_ocr.py` |
| Fabric audit (P4) | Fuzzy client match + field comparison vs Artus | `scripts/audit_fabric_comparison.py` |
| FIC generator (P6) | Business-rule gate + Word FIC draft | `scripts/generate_fic_draft.py` |
| Post-audit (P5) | Teams alerts, archival, RGPD cleanup | `scripts/post_audit_workflow.py` |
| Pipeline orchestrator | Chains P3→P4→P6→P5 with isolated job dir | `scripts/run_audit_pipeline.ps1` |
| Standalone desktop audit | Tkinter PDF/Excel reconciliation app | `src/main.py`, `src/core.py` |
| Persistence | SQLite tracking of audits / FIC generation | `scripts/db_manager.py`, `core.py:AuditHistory` |

## Pattern Overview

**Overall:** Layered pipeline with a conversational front-end. A thin FastAPI gateway fronts an Azure Durable Functions orchestration; the orchestration (and the equivalent PowerShell orchestrator) drives a chain of single-purpose Python CLI scripts that pass JSON artifacts file-to-file.

**Key Characteristics:**
- Stateless CLI stages communicating via JSON files in an isolated per-job directory (UUID).
- Fail-fast / fail-closed posture (no fake fallback data when Fabric is unreachable).
- Security-first: JWT auth, path-traversal guards, dangerous-char rejection, RGPD cleanup of generated drafts.
- Two parallel orchestrators exist: Azure Durable Functions (production proxy target) and `run_audit_pipeline.ps1` (local/full chain).

## Layers

**Conversational (Copilot Studio):**
- Purpose: User entry point; read-only SharePoint RAG and audit triggering.
- Location: `src/copilot-workspace/AC360/`, `src/copilot/AC360/`
- Contains: `agent.mcs.yml`, `topics/*.mcs.yml`, `actions/*.mcs.yml`, `knowledge/*.mcs.yml`
- Depends on: API gateway via `HttpRequestAction`.

**API Gateway (FastAPI):**
- Purpose: Authenticated entry to backend; proxy + sync helper endpoints.
- Location: `scripts/api_server.py`
- Depends on: `auth.py`, `planner_integration.py`, `generate_fiche_rdv.py`, `safe_logger.py`, `config.py`.
- Used by: Copilot topics, external callers.

**Orchestration:**
- Purpose: Sequence the audit phases.
- Location: `azure_functions/` (Durable Functions, configured via `host.json`), `scripts/run_audit_pipeline.ps1`.

**Pipeline Stages (Python CLI):**
- Purpose: One business phase each, JSON in / JSON out.
- Location: `scripts/process_document_ocr.py`, `audit_fabric_comparison.py`, `generate_fic_draft.py`, `post_audit_workflow.py`.

**Standalone Desktop:**
- Purpose: Independent Tkinter PDF/Excel reconciliation tool (separate from the cloud pipeline).
- Location: `src/main.py` (UI), `src/core.py` (parsing, fuzzy match, écart calc, SQLite history).

## Data Flow

### Primary Request Path (audit pipeline)

1. User triggers audit in Copilot (`LancerAudit.mcs.yml`) → POST `https://ac360-api.azurewebsites.net/api/audit`.
2. Gateway authenticates and rate-limits, then proxies to Azure Function (`scripts/api_server.py:108` `trigger_audit`).
3. **P3 OCR** — `process_document_ocr.py:21` `extract_document_azure` → `prebuilt-document` model → `temp_ocr_result.json` (fields + tables).
4. **P4 Fabric** — `audit_fabric_comparison.py:197` `main` loads OCR JSON, `fetch_artus_data` queries Fabric SQL, `match_client_name` fuzzy-matches (≥85% threshold), `perform_audit` compares plafonds → `final_audit_report.json` + `.csv`.
5. **P6 FIC** — `generate_fic_draft.py:25` `evaluate_fic_rules` gates on `motif_operation`; if eligible, `generate_fic_document` writes `FIC_Brouillon_*.docx` and emits `FIC_GENERATED_PATH=...`.
6. **P5 Post-audit** — `post_audit_workflow.py:105` `main` sends Teams alert on écart, archives litigious docs, deletes temp + FIC drafts (RGPD).
7. Pipeline cleans temp JSON/CSV; status polled via `GET /api/audit/{job_id}/status` (`api_server.py:227`).

### Desktop Reconciliation Flow

1. User selects PDF + Excel (`src/main.py` `select_pdf`/`select_excel`).
2. `PDFParser.parse_file` (pdfplumber) and `ExcelParser.parse` (pandas) extract records.
3. `OptimizedMatcher.match_with_index` (indexed + fuzzy, seuil 0.75) → `EcartCalculator.calculer_ecarts` (écart = Excel − PDF).
4. Results shown in Treeview, saved to `audits.db` via `AuditHistory.save_audit`, exportable to Excel/CSV/PDF.

**State Management:**
- Per-job isolation via UUID directories created by `run_audit_pipeline.ps1`; JSON artifacts are the inter-stage state.
- In-process rate-limit store (`_rate_limit_store` dict) in `api_server.py`.
- Persistent state in SQLite (`audits.db`, FIC tracking via `db_manager.py`).

## Key Abstractions

**OCR JSON contract:**
- Purpose: Canonical document representation passed between stages.
- Shape: `{ metadata, fields{ name:{value,confidence} }, tables[{cells[]}], keyValuePairs[] }`.
- Produced: `process_document_ocr.py`; consumed: `audit_fabric_comparison.py:125` `perform_audit`.

**Audit report JSON contract:**
- Purpose: Output of P4, input to P5/P6.
- Shape: `{ client_document, meilleur_match_fabric, score_correspondance_nom, motif_operation, details_ecarts[] }`.

**Copilot topic (`*.mcs.yml`):**
- Purpose: Declarative dialog unit (intent, actions, HTTP calls).
- Pattern: `kind: AdaptiveDialog` with `beginDialog` + `actions`.

## Entry Points

**Copilot agent:** `src/copilot-workspace/AC360/agent.mcs.yml` — user conversation entry; triggers topics.

**API gateway:** `scripts/api_server.py` (`uvicorn api_server:app`, port 8000) — `/api/audit`, `/api/planner/task`, `/api/generate-fiche-rdv`, `/api/download/...`, `/health`.

**Pipeline orchestrator:** `scripts/run_audit_pipeline.ps1` — full local chain, args `-DocumentPath -Upn -JobDir`.

**Azure Functions:** `azure_functions/` — Durable Functions host (`host.json`); production proxy target of the gateway.

**Desktop app:** `src/main.py` (`python src/main.py`).

**Pipeline stages:** each `scripts/*.py` stage is independently runnable via `argparse`.

## Architectural Constraints

- **Threading:** FastAPI gateway is async; synchronous file I/O is offloaded via `run_in_threadpool` (`api_server.py:172`). Desktop app runs audits on a background `threading.Thread`. Pipeline stages are synchronous subprocesses.
- **Global state:** Module-level singletons — `http_client` (`api_server.py:29`), `_rate_limit_store` (`:62`), `_JWKS_CACHE` (`auth.py:13`). These are per-process and not shared across replicas.
- **Fail-closed:** `fetch_artus_data` raises `ConnectionError` rather than using fake data when Fabric is unavailable (`audit_fabric_comparison.py:75`).
- **Two source files only as `.pyc`:** `azure_functions/function_app.py`, `audit_engine.py`, `rdv_engine.py` exist only as compiled `.pyc` in `azure_functions/__pycache__/` — source is absent from the tree.

## Anti-Patterns

### Inconsistent fuzzy-match thresholds

**What happens:** Cloud audit uses an 85% match threshold (`audit_fabric_comparison.py:118`) but the rejection comment and post-audit still reference 75% (`:186`, `post_audit_workflow.py:30`); desktop uses 0.75 (`core.py:310`).
**Why it's wrong:** Divergent thresholds and stale comments make audit behavior ambiguous and hard to reason about.
**Do this instead:** Centralize the threshold in config and reference it consistently.

### Duplicated copilot workspace trees

**What happens:** `src/copilot/AC360/` and `src/copilot-workspace/AC360/` both hold overlapping `topics/*.mcs.yml`.
**Why it's wrong:** Two sources of truth for the same agent risk drift between deployed and edited versions.
**Do this instead:** Treat `src/copilot-workspace/AC360/` as canonical and document `src/copilot/AC360/` as the export/backup.

### Missing backend source under version control

**What happens:** Durable Functions logic is only present compiled in `azure_functions/__pycache__/`.
**Why it's wrong:** The orchestration brain cannot be reviewed, tested, or modified from source.
**Do this instead:** Commit `function_app.py`, `audit_engine.py`, `rdv_engine.py` source.

## Error Handling

**Strategy:** Fail-fast at security boundaries (HTTP 4xx/5xx in gateway), fail-closed on data integrity (Fabric), best-effort + WARNING logs for non-critical steps (FIC, Teams).

**Patterns:**
- Gateway wraps backend calls and maps exceptions to `HTTPException` (502/500) with `log_security`.
- PowerShell orchestrator uses `Set-StrictMode`, `$ErrorActionPreference="Stop"`, structured JSON logging (`Write-JsonLog`) and per-phase exit codes.
- CLI stages `exit(1)` on missing inputs / missing SDK / missing env vars.

## Cross-Cutting Concerns

**Logging:** `scripts/safe_logger.py` (`log_security`, redaction); structured JSON pipeline log (`pipeline.log.json`); App Insights middleware in gateway.
**Validation:** Pydantic request models (`AuditRequest`, `PlannerTaskRequest`, `FicheRDVRequest`); path-traversal guards (`api_server.py:198`, `post_audit_workflow.py:76` via `commonpath`); dangerous-char rejection in PowerShell.
**Authentication:** Entra ID JWT (RS256, JWKS, issuer/scope/role checks) in `scripts/auth.py`; Copilot enforces SharePoint read-only permissions per `agent.mcs.yml`; Fabric uses `DefaultAzureCredential`.

---

*Architecture analysis: 2026-06-08*
