"""
conftest.py — Configuration globale pytest pour AC360.

IMPORTANT : Les variables d'environnement de test sont injectées ICI,
avant tout import de module, afin que le fail-fast de config.py
ne bloque pas la collection pytest en environnement CI/CD ou local
sans fichier .env.

Ces valeurs sont des stubs de test uniquement — elles n'ont aucun
accès réel aux services Microsoft.
"""
import sys
import os

# ---------------------------------------------------------------------------
# Injection des variables d'environnement de test (stubs CI/CD)
# DOIT être fait AVANT tout import de scripts/config.py
# ---------------------------------------------------------------------------
_TEST_ENV_DEFAULTS = {
    "TENANT_ID": os.getenv("TENANT_ID", "test-tenant-00000000-0000-0000-0000-000000000000"),
    "CLIENT_ID": os.getenv("CLIENT_ID", "test-client-00000000-0000-0000-0000-000000000000"),
    "JOBS_BASE_DIR": os.getenv("JOBS_BASE_DIR", os.path.join(os.path.dirname(__file__), "jobs")),
    "AZURE_OCR_KEY": os.getenv("AZURE_OCR_KEY", "test-ocr-key"),
    "AZURE_OCR_ENDPOINT": os.getenv("AZURE_OCR_ENDPOINT", "https://test.cognitiveservices.azure.com/"),
    "FABRIC_SQL_ENDPOINT": os.getenv("FABRIC_SQL_ENDPOINT", "test-fabric-endpoint"),
    "FABRIC_DATABASE": os.getenv("FABRIC_DATABASE", "test-fabric-db"),
    "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
}
for _key, _val in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _val)

# ---------------------------------------------------------------------------
# Ajouter le dossier scripts au PYTHONPATH pour que les imports fonctionnent
# ---------------------------------------------------------------------------
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
