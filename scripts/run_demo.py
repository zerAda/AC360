"""run_demo.py — Démo AC360 de bout en bout, SANS dépendance cloud obligatoire."""
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Optional

# Permet l'exécution directe (python scripts/run_demo.py) comme importée (tests).
_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
import sys
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from fabric_audit_engine import (  # noqa: E402
    audit, compare_name, extract_canonical_fields,
)

_ROOT = os.path.abspath(os.path.join(_SCRIPTS, ".."))

# Fixtures synthétiques embarquées — aucun fichier externe requis.
_DEMO_OCR: Dict[str, Any] = {
    "metadata": {"source_file": "Contrat_DEMO_2026.pdf",
                 "extraction_mode": "azure-prebuilt-document", "pages": 2},
    "fields": {
        "Raison sociale": {"value": "GEREP SA", "confidence": 0.97},
        "Date d'effet": {"value": "01/06/2026", "confidence": 0.95},
        "N° de contrat": {"value": "AB-2026-0142", "confidence": 0.93},
    },
    "tables": [{"row_count": 2, "column_count": 2, "cells": [
        {"row_index": 0, "column_index": 0, "content": "Garantie"},
        {"row_index": 0, "column_index": 1, "content": "Plafond"},
        {"row_index": 1, "column_index": 0, "content": "Plafond hospitalisation"},
        {"row_index": 1, "column_index": 1, "content": "1 500 €"},
    ]}],
}
_DEMO_REF: List[Dict[str, Any]] = [
    {"client_id": 101, "nom_client": "GEREP SA",
     "plafond_hospitalisation": "2000", "date_effet": "2026-06-01",
     "numero_contrat": "AB-2026-0142"},
    {"client_id": 102, "nom_client": "BETA CORP",
     "plafond_hospitalisation": "1000", "date_effet": "2025-01-15",
     "numero_contrat": "BX-2025-0033"},
]


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def select_reference(client_name: Optional[str],
                     references: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Sélectionne la ligne de référence dont le nom correspond le mieux au client
    extrait. Retourne None si aucun rapprochement suffisamment sûr (MATCH/UNCERTAIN)."""
    if not client_name:
        return None
    best = None
    best_conf = 0.0
    for row in references:
        statut, conf = compare_name(client_name, row.get("nom_client"))
        if statut in ("MATCH", "UNCERTAIN") and conf > best_conf:
            best, best_conf = row, conf
    return best


def audit_from_sources(ocr_data: Dict[str, Any],
                       references: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extrait les champs OCR, rapproche le client, et produit un audit typé."""
    document = extract_canonical_fields(ocr_data)
    reference = select_reference(document.get("nom_client"), references)
    return audit({"document": document, "reference": reference or {}})


def _format_report(result: Dict[str, Any]) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("  AC360 — RAPPORT D'AUDIT (DÉMO)")
    lines.append("=" * 60)
    lines.append(f"Client (document)   : {result.get('client_document') or '—'}")
    lines.append(f"Référence Fabric    : {result.get('meilleur_match_fabric') or '—'}")
    lines.append(f"Score correspondance: {result.get('score_correspondance_nom')} %")
    lines.append(f"VERDICT GLOBAL      : >>> {result.get('verdict')} <<<")
    lines.append("-" * 60)
    lines.append(f"{'Champ':<26}{'Document':<14}{'Référence':<14}{'Statut'}")
    lines.append("-" * 60)
    for field in result.get("fields", []):
        lines.append(
            f"{str(field.get('champ')):<26}"
            f"{str(field.get('valeur_document') or '—'):<14}"
            f"{str(field.get('valeur_reference') or '—'):<14}"
            f"{field.get('statut')} ({field.get('confiance')})"
        )
    lines.append("=" * 60)
    return "\n".join(lines)


def run(ocr_path: Optional[str] = None,
        reference_path: Optional[str] = None,
        make_fic: bool = False,
        out_dir: Optional[str] = None,
        printer=print) -> Dict[str, Any]:
    """Exécute la démo et retourne le résultat d'audit. `printer` injectable (tests)."""
    ocr_data = _load_json(ocr_path) if ocr_path else _DEMO_OCR
    references = _load_json(reference_path) if reference_path else _DEMO_REF

    result = audit_from_sources(ocr_data, references)
    printer(_format_report(result))

    fic_path = None
    if make_fic:
        fic_path = _generate_fic(result, out_dir or os.path.join(_ROOT, "demo", "out"))
        printer(f"\n[FIC] Brouillon généré : {fic_path}")

    result["_fic_path"] = fic_path
    return result


def _generate_fic(result: Dict[str, Any], out_dir: str) -> Optional[str]:
    try:
        from generate_fic_draft import generate_fic_document
    except Exception as exc:  # python-docx absent
        return f"(FIC non générée : {exc})"
    os.makedirs(out_dir, exist_ok=True)
    garanties = {}
    date_effet = None
    for field in result.get("fields", []):
        champ = field.get("champ")
        val = field.get("valeur_reference") or field.get("valeur_document")
        if champ == "date_effet":
            date_effet = val
        elif champ and val is not None:
            garanties[champ] = val
    client = result.get("client_document") or "client"
    safe = "".join(c for c in client if c.isalnum() or c == " ").strip().replace(" ", "_")
    out_path = os.path.join(out_dir, f"FIC_Demo_{safe or 'client'}.docx")
    generate_fic_document(client, date_effet, garanties, out_path)
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Démo AC360 (audit + FIC), hors-ligne par défaut.")
    parser.add_argument("--ocr", default=None, help="Fichier JSON OCR (défaut : fixture embarquée).")
    parser.add_argument("--reference", default=None, help="Fichier JSON de référence Fabric (défaut : fixture embarquée).")
    parser.add_argument("--pdf", default=None, help="PDF à analyser via Azure OCR réel (si .env configuré).")
    parser.add_argument("--fic", action="store_true", help="Générer aussi le brouillon FIC (.docx).")
    args = parser.parse_args()

    ocr_path = args.ocr
    if args.pdf:
        # OCR réel (Azure F0) -> écrit un JSON temporaire réutilisé par la démo.
        from process_document_ocr import extract_document_azure
        ocr_data = extract_document_azure(args.pdf)
        ocr_path = os.path.join(_ROOT, "demo", "out", "ocr_live.json")
        os.makedirs(os.path.dirname(ocr_path), exist_ok=True)
        with open(ocr_path, "w", encoding="utf-8") as f:
            json.dump(ocr_data, f, ensure_ascii=False, indent=2)

    run(ocr_path=ocr_path, reference_path=args.reference, make_fic=args.fic)


if __name__ == "__main__":
    main()
