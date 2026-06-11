import os
import json
import logging
import argparse
from dotenv import load_dotenv

logger = logging.getLogger("AC360.ocr")


def _ocr_timeout() -> float:
    try:
        return float(os.getenv("AZURE_OCR_TIMEOUT_S", "120"))
    except (ValueError, TypeError):
        return 120.0


# NOTE: Le SDK Azure est une dépendance *optionnelle* chargée paresseusement au
# runtime (voir _require_azure_sdk). On n'appelle JAMAIS sys.exit() à l'import :
# cela casserait la collection pytest et tout import du module dans un
# environnement sans le SDK natif. Les noms restent exposés au niveau module
# (initialisés à None) pour rester mockables par les tests.
AzureKeyCredential = None
DocumentAnalysisClient = None


def _require_azure_sdk():
    """Importe le SDK Azure à la demande et le mémorise au niveau module. Lève
    une RuntimeError explicite (et non un sys.exit) si la dépendance optionnelle
    est absente. Si les symboles ont déjà été fournis (import réel ou mock de
    test), ils sont réutilisés tels quels."""
    global AzureKeyCredential, DocumentAnalysisClient
    if AzureKeyCredential is None or DocumentAnalysisClient is None:
        try:
            from azure.core.credentials import AzureKeyCredential as _AKC
            from azure.ai.formrecognizer import DocumentAnalysisClient as _DAC
        except ImportError as exc:  # pragma: no cover - dépend de l'environnement
            raise RuntimeError(
                "Le SDK Azure (azure-ai-formrecognizer) n'est pas installé. "
                "Exécutez 'pip install -r requirements.txt'."
            ) from exc
        AzureKeyCredential = _AKC
        DocumentAnalysisClient = _DAC
    return AzureKeyCredential, DocumentAnalysisClient


# Load environment variables from .env file
load_dotenv()

AZURE_OCR_ENDPOINT = os.getenv("AZURE_OCR_ENDPOINT")
AZURE_OCR_KEY = os.getenv("AZURE_OCR_KEY")


def extract_document_azure(file_path):
    """
    Extrait les données du document via Azure AI Document Intelligence.
    Utilise le modèle prebuilt-document pour extraire les paires Clé-Valeur et les Tableaux.
    """
    logger.info("OCR: analyse via Azure Document Intelligence")

    AzureKeyCredential, DocumentAnalysisClient = _require_azure_sdk()
    document_analysis_client = DocumentAnalysisClient(
        endpoint=AZURE_OCR_ENDPOINT,
        credential=AzureKeyCredential(AZURE_OCR_KEY)
    )

    logger.debug("OCR: analyse du fichier %s", os.path.basename(str(file_path)))
    with open(file_path, "rb") as f:
        poller = document_analysis_client.begin_analyze_document("prebuilt-document", document=f)

    # Borne le temps d'attente : sans timeout, un document pathologique pourrait
    # bloquer indéfiniment l'activité Durable (worker épuisé).
    result = poller.result(timeout=_ocr_timeout())

    # Structuration de la sortie JSON
    output_data = {
        "metadata": {
            "source_file": os.path.basename(file_path),
            "extraction_mode": "azure-prebuilt-document",
            "pages": len(result.pages)
        },
        "fields": {},
        "tables": []
    }

    # Extraction des paires clé-valeur
    if result.key_value_pairs:
        for kv_pair in result.key_value_pairs:
            if kv_pair.key and kv_pair.value:
                key_text = kv_pair.key.content.strip()
                val_text = kv_pair.value.content.strip()
                confidence = kv_pair.confidence
                output_data["fields"][key_text] = {
                    "value": val_text,
                    "confidence": confidence
                }

    # Extraction des tableaux
    if result.tables:
        for table in result.tables:
            table_info = {
                "row_count": table.row_count,
                "column_count": table.column_count,
                "cells": []
            }
            for cell in table.cells:
                table_info["cells"].append({
                    "row_index": cell.row_index,
                    "column_index": cell.column_index,
                    "content": cell.content
                })
            output_data["tables"].append(table_info)

    return output_data


def main():
    parser = argparse.ArgumentParser(description="Extrait les données d'un document (PDF, Image) via Azure OCR.")
    parser.add_argument("file", help="Chemin du fichier à analyser.")
    parser.add_argument("--output", help="Chemin du fichier JSON de sortie.", default="ocr_result.json")
    args = parser.parse_args()

    file_path = args.file

    if not os.path.exists(file_path):
        print(f"Erreur : Le fichier '{file_path}' n'existe pas.")
        exit(1)

    if not AZURE_OCR_ENDPOINT or not AZURE_OCR_KEY:
        print("Erreur : Les variables d'environnement AZURE_OCR_ENDPOINT et AZURE_OCR_KEY sont manquantes.")
        print("Veuillez exécuter le script de déploiement Azure et ajouter ces valeurs dans votre fichier .env.")
        exit(1)

    result_data = extract_document_azure(file_path)

    # Sauvegarde du résultat
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)

    print(f"\n[SUCCÈS] Extraction terminée. Résultats sauvegardés dans : {args.output}")


if __name__ == "__main__":
    main()
