"""
Configuration pytest pour les tests backend AC360.

- Ajoute `scripts/` au PYTHONPATH : les modules s'importent en absolu, comme à
  l'exécution (`import api_server`, `from db_manager import ...`,
  `from safe_logger import ...`).
- Définit les variables d'environnement obligatoires AVANT tout import
  d'`api_server` (celui-ci applique un fail-fast si TENANT_ID / CLIENT_ID sont
  absents). pytest importe ce conftest avant les modules de test du dossier.
"""
import os
import sys
import tempfile
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# Valeurs factices : suffisent à satisfaire le fail-fast d'api_server au moment
# de l'import. Aucune requête réseau JWKS n'est déclenchée tant qu'on n'appelle
# pas un endpoint authentifié.
os.environ.setdefault("TENANT_ID", "00000000-0000-0000-0000-000000000000")
os.environ.setdefault("CLIENT_ID", "11111111-1111-1111-1111-111111111111")
os.environ.setdefault("JOBS_BASE_DIR", tempfile.gettempdir())
