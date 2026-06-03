#!/usr/bin/env python3
"""validate_copilot_yaml.py — Validates all Copilot Studio YAML files in AC360."""
import sys
import yaml
from pathlib import Path

COPILOT_ROOT = Path(__file__).parent.parent / "src" / "copilot" / "AC360"

def validate_all():
    ok, ko = [], []
    if not COPILOT_ROOT.exists():
        print(f"[ECHEC] Le répertoire {COPILOT_ROOT} n'existe pas.")
        sys.exit(1)
        
    for yml_file in sorted(COPILOT_ROOT.rglob("*.yml")):
        try:
            with open(yml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data is None:
                ko.append((yml_file.name, "Fichier vide ou non YAML"))
            else:
                ok.append(yml_file.name)
        except yaml.YAMLError as e:
            ko.append((yml_file.name, str(e)[:120]))
        except Exception as e:
            ko.append((yml_file.name, f"Erreur lecture: {e}"))
    
    print(f"\n=== Validation YAML Copilot Studio ===")
    print(f"Répertoire : {COPILOT_ROOT}")
    print(f"")
    for name in ok:
        print(f"  [OK]  {name}")
    for name, err in ko:
        print(f"  [KO]  {name} -> {err}")
    print(f"")
    print(f"Résultat : {len(ok)} OK / {len(ko)} KO")
    
    if ko:
        print("\n[ECHEC] Des fichiers YAML sont invalides.")
        sys.exit(1)
    else:
        print("\n[SUCCES] Tous les fichiers YAML sont valides.")
        sys.exit(0)

if __name__ == "__main__":
    validate_all()
