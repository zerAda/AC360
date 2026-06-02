import os
import sys
import json
import argparse
from dotenv import load_dotenv

# Optional dependencies for Azure
try:
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.formrecognizer import DocumentAnalysisClient
except ImportError:
    print("Erreur : Le SDK Azure n'est pas installé. Exécutez 'pip install -r requirements.txt'.")
    sys.exit(1)

# Load environment variables from .env file
load_dotenv()

AZURE_OCR_ENDPOINT = os.getenv("AZURE_OCR_ENDPOINT")
AZURE_OCR_KEY = os.getenv("AZURE_OCR_KEY")

def extract_document_azure(file_path):
    """
    Extrait les données du document via Azure AI Document Intelligence.
    Utilise le modèle prebuilt-document pour extraire les paires Clé-Valeur et les Tableaux.
    """
    print(f"[AZURE MODE] Connexion à l'endpoint : {AZURE_OCR_ENDPOINT}")
    
    document_analysis_client = DocumentAnalysisClient(
        endpoint=AZURE_OCR_ENDPOINT, 
        credential=AzureKeyCredential(AZURE_OCR_KEY)
    )

    print(f"[AZURE MODE] Analyse du fichier : {file_path}...")
    with open(file_path, "rb") as f:
        poller = document_analysis_client.begin_analyze_document("prebuilt-document", document=f)
    
    result = poller.result()

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
