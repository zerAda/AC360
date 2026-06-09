"""Garde-fou : .env.example doit documenter toute variable d'environnement lue
par le code applicatif (anti-dérive de configuration)."""
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOURCE_DIRS = ("scripts", "azure_functions")

# Variables posées en interne par l'application (pas des paramètres de config).
INTERNAL_VARS = {"CURRENT_USER_UPN"}

_ENV_RE = re.compile(r"os\.(?:getenv|environ\.get)\(\s*['\"]([A-Z][A-Z0-9_]+)['\"]")


def _collect_env_keys():
    keys = set()
    for d in SOURCE_DIRS:
        base = os.path.join(ROOT, d)
        for dirpath, _dirnames, filenames in os.walk(base):
            if "__pycache__" in dirpath:
                continue
            for fn in filenames:
                if fn.endswith(".py"):
                    with open(os.path.join(dirpath, fn), "r", encoding="utf-8") as f:
                        keys.update(_ENV_RE.findall(f.read()))
    return keys - INTERNAL_VARS


def test_env_example_documents_all_keys():
    with open(os.path.join(ROOT, ".env.example"), "r", encoding="utf-8") as f:
        documented = f.read()
    missing = sorted(k for k in _collect_env_keys() if k not in documented)
    assert not missing, f"Variables d'environnement non documentées dans .env.example : {missing}"
