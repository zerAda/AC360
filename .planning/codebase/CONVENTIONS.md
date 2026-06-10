# Coding Conventions

**Analysis Date:** 2026-06-10

## Naming Patterns

**Files:**
- Snake case for Python modules: `safe_logger.py`, `api_server.py`, `fabric_audit_engine.py`
- Tkinter/UI modules use camelCase for class names: `AuditApp`, `AuditHistory`
- Test files follow pattern: `test_<module>.py` (e.g., `test_auth_jwt.py`, `test_ocr_fabric.py`)
- Data/config files: `conftest.py` for pytest config, `setup.cfg` for tool config

**Functions:**
- Snake case for all functions: `verify_azure_ad_token()`, `extract_document_azure()`, `fetch_artus_data()`
- Private helpers prefixed with `_`: `_validate_sharepoint_doc_id()`, `_extract_montant_from_line()`, `_strip_accents()`
- Async functions prefixed with `async def`: `async def trigger_audit()`, `async def download_fiche_rdv()`
- Static methods in classes: `@staticmethod` decorator (e.g., `PDFParser.parse_file()`, `Normalizer.normalize()`)

**Variables:**
- Snake case: `pdf_data`, `excel_data`, `job_id`, `user_upn`
- Module-level constants: UPPER_SNAKE_CASE: `SEUIL = 0.75`, `_MASK_SECRET = "[SECRET_MASQUÉ]"`
- Type hints used throughout: `def load_config(require_auth: bool = False) -> AppConfig:`
- Meaningful abbreviations in context: `pdf`, `excel`, `ocr`, `jwt`, `upn` (User Principal Name), `mtd` (middleware)

**Types:**
- Dataclasses used for config: `@dataclass(frozen=True) class AppConfig:`
- Pydantic models for API: `class AuditRequest(BaseModel):`, `class FicheRDVRequest(BaseModel):`
- Type hints via `from typing import Optional, List, Dict, Tuple, Any, FrozenSet`
- Optional used for nullable types: `tenant_id: Optional[str]`, `document_id: Optional[str] = None`

## Code Style

**Formatting:**
- No automatic formatter (black/prettier) enforced; code is written to PEP 8 standards
- Indentation: 4 spaces (Python standard)
- Line length: ~80-100 characters (observed; no strict limit in .flake8)
- Multi-line strings use triple quotes for docstrings and error messages

**Linting:**
- flake8 v7.1.1 via pre-commit (`.pre-commit-config.yaml`)
- mypy v1.11.2 for type checking (configuration in `setup.cfg [mypy]`)
- detect-private-key pre-commit hook to block committed secrets
- gitleaks v8.18.2 to scan for credential patterns (`.gitleaks.toml`)
- No isort, no autopep8; imports organized manually

**Linting Rules Enforced:**
- Trailing whitespace removed (pre-commit hook)
- End-of-file newlines enforced
- YAML/JSON validity checked
- Large file detection (>1MB blocked)
- flake8 rules in `setup.cfg [flake8]` (if present—see project root)

## Import Organization

**Order:**
1. Standard library: `import os`, `import sys`, `import re`, `import json`, `import time`, `from typing import ...`
2. Third-party: `import pytest`, `from fastapi import ...`, `import pandas as pd`, `from unittest.mock import ...`
3. Local/project: `from config import load_config`, `from safe_logger import log_security`, `from auth import ...`

**Path Aliases:**
- No path aliases configured (`import src.services.user` not used; direct imports relative to PYTHONPATH)
- PYTHONPATH manipulation in test fixtures: `sys.path.insert(0, ...)` (e.g., `tests/backend/conftest.py`)
- Imports use absolute paths after PYTHONPATH setup: `from api_server import ...`, `from auth import verify_azure_ad_token`

**Special Pattern — Conditional Imports:**
Imports protected with try/except for optional dependencies:
```python
try:
    import pdfplumber
except ImportError:
    raise Exception("pdfplumber requis. Installez: pip install pdfplumber")

try:
    from thefuzz import fuzz as _fuzz
except Exception:
    _fuzz = None
```

## Error Handling

**Patterns:**
- Raise `HTTPException` from FastAPI routes with explicit status codes:
  ```python
  raise HTTPException(status_code=400, detail="document_id manquant.")
  raise HTTPException(status_code=401, detail="Token JWT invalide : champ 'kid' manquant.")
  raise HTTPException(status_code=403, detail="Access forbidden: IDOR check")
  ```
- Raise `ConfigurationError` for critical missing env vars: `raise ConfigurationError("Variables manquantes : ...")`
- Raise `RuntimeError` for missing Azure resources: `raise RuntimeError("SHAREPOINT_DRIVE_ID manquant (configuration requise).")`
- Generic `Exception` for utility failures: `raise Exception("pandas requis. Installez: pip install pandas")`

**Fail-Fast Pattern:**
- Configuration validation happens on import via `load_config(require_auth=True)` in `api_server.py`
- Does NOT fail during pytest collection; test-safe wrapper in `conftest.py` injects test defaults
- Errors logged via `log_security()` before raising exceptions

**Try/Except Usage:**
- Catch specific exceptions: `except ImportError:`, `except HTTPException:`, `except ValueError:`, `except jwt.exceptions.DecodeError:`
- Suppress errors with context messages: `except Exception as e: print(f"[BATCH] Erreur sur {pdf_path}: {e}")`
- Fail-closed pattern: Missing metadata/authorization raises 403, no fallback

## Logging

**Framework:** Standard Python `logging` module (no third-party logger library)

**Custom Implementation:** `safe_logger.py` provides `log_security()` and `redact()` for PII/secret masking before persistence

**Patterns:**
- Print statements for non-critical info: `print(f"[BENCHMARK] Audit terminé en {duree:.2f} secondes")`
- `log_security()` for authentication/authorization events: `log_security("ERROR", "Missing kid in JWT header")`
- Logger instance created once: `logger = logging.getLogger("AC360")` in `safe_logger.py`
- Messages redacted before logging: `safe_msg = redact(message)` removes secrets, PII, ANSI escapes
- Prefixes for context: `[BENCHMARK]`, `[BATCH]`, `[POST-AUDIT]`, `[HISTORIQUE]`, `[DB]`

**Secrets Redaction:**
- JWT patterns masked: `_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_\-]+\....")`
- Bearer tokens masked: `_BEARER_RE = re.compile(r"(?i)\bbearer\s+...")`
- Key=value secrets masked: `_KV_SECRET_RE` matches `password=...`, `api_key=...`, etc.
- Email/IBAN/PII masked via regex patterns in `safe_logger.redact()`
- Max log length: 800 characters (truncated)

## Comments

**When to Comment:**
- Algorithm explanations: "Phase 6: Pattern pour détecter les montants"
- Business logic decisions: "Source de vérité: PDF" (documented in module docstring)
- Security reasoning: "défense en profondeur : rejet au bord avant de démarrer une orchestration"
- Workarounds/fixes: Comments prefixed `# FIX <CODE>:` e.g., `# FIX PERF-03: Nettoyer mémoire avant audit`
- Complex regex: Each pattern documented with example formats

**No Comments For:**
- Obvious code: `self.progress_var.set(value)` needs no comment
- Names that are self-documenting

**JSDoc/TSDoc:**
- Docstrings on all public functions, classes, modules
- Triple-quoted format:
  ```python
  def fetch_artus_data(client_name=None):
      """Récupère les données de référence client depuis Fabric.
      
      Args:
          client_name: Optionnel, pour filtrer par nom
      
      Returns:
          DataFrame avec colonnes client_id, nom_client, plafonds...
      
      Raises:
          ConnectionError: Si la connexion Fabric n'est pas disponible
      """
  ```
- Parameter descriptions included
- Return type and exceptions documented

**Module-Level Docstrings:**
All modules start with docstring:
```python
"""function_app.py — Backend AC360 (Azure Durable Functions, modèle Python v2).

Passerelle d'orchestration appelée par `scripts/api_server.py`.
Démarre une orchestration durable document -> OCR -> Fabric -> comparaison -> FIC.
"""
```

## Function Design

**Size:**
- Typical: 10-50 lines; larger functions split into helpers
- Exception: `run_audit()` in `main.py` reaches ~240 lines (legacy UI, acceptable for single flow)
- UI event handlers stay co-located with UI class for clarity

**Parameters:**
- Use type hints: `def download_fiche_rdv(job_id: str, filename: str, user_upn: str) -> FileResponse:`
- Optional params have defaults: `def match_with_index(pdf_data, excel_data, seuil=None):`
- Avoid positional-only for internal APIs; keyword args preferred: `fetch_client_reference(client_name=None, siret=None)`

**Return Values:**
- Explicit returns: `return app` (FastAPI instance), `return result, total_ecart` (tuple unpacking)
- None for operations that log only: `def init_db():` has no explicit return
- Typed returns in signature: `-> AppConfig:`, `-> dict`, `-> List[str]`

## Module Design

**Exports:**
- Public API listed in docstring or via `__all__` list:
  ```python
  __all__ = ["redact", "MAX_LEN", "logger", "log_security"]
  ```
- Modules import functions directly: `from auth import verify_azure_ad_token`, not `from auth import *`

**Barrel Files:**
- No barrel files (no `__init__.py` re-exporting modules)
- Direct imports from files: `from config import load_config`, `from db_manager import log_fic_generation`

**Module Organization:**
- Constants and imports at top
- Helper functions (prefixed `_`) defined before public functions
- Classes defined before usage
- Main entry point at bottom: `if __name__ == "__main__":`
- Example from `db_manager.py`:
  ```python
  # Imports
  import sqlite3
  import os
  
  # Constants
  DB_PATH = os.path.join(...)
  
  # Public functions
  def init_db(): ...
  def log_fic_generation(...): ...
  
  # Main
  if __name__ == "__main__":
      init_db()
  ```

## Async/Await Patterns

**Used In:**
- FastAPI endpoints: `async def trigger_audit()`, `async def download_fiche_rdv()`
- Azure Function orchestration: Durable Tasks (native async model)
- Background tasks: Thread pools for long-running ops like PDF parsing

**Pattern:**
```python
async def trigger_audit(...) -> dict:
    try:
        response = await http_client.post(...)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Threading:**
- Tkinter long operations wrapped: `threading.Thread(target=self.run_audit, daemon=True)`
- FastAPI uses `run_in_threadpool` for blocking I/O
- No explicit `await` in Tkinter (no event loop integration)

## Database & ORM

**Pattern:** SQLite with raw SQL (no ORM)

**Design:**
```python
def log_fic_generation(...):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO ...', (param1, param2, ...))
    conn.commit()
    conn.close()
```

**No Transactions Beyond Single Statements:**
- Each function opens/closes connection independently
- Transactions are implicit (auto-commit after `.commit()`)
- No connection pooling (SQLite doesn't require it for single-process apps)

---

*Convention analysis: 2026-06-10*
