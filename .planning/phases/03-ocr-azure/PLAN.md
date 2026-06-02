# Phase 3 : OCR Azure AI Document Intelligence (Étape C)

## Objectif
Automatiser l'extraction intelligente des métadonnées (nom du client, dates, montants, garanties) depuis des documents PDF (Contrats, Tableaux de garanties) en utilisant Azure AI Document Intelligence.

## Tâches d'Exécution

1. **Déploiement de l'Infrastructure Azure**
   - Étant donné que la ressource n'existe pas encore, fournir un script Azure CLI (`scripts/deploy_azure_ocr.ps1`) permettant à l'administrateur de créer rapidement un groupe de ressources et une instance "Cognitive Services / Form Recognizer".
   
2. **Script Python d'Extraction (`scripts/process_document_ocr.py`)**
   - Créer un outil Python utilisant `azure-ai-formrecognizer`.
   - Utiliser le modèle `prebuilt-document` (ou `prebuilt-layout`) adapté aux documents non structurés complexes (ex: contrats d'assurance).
   - Extraire les paires Clé-Valeur et les Tableaux.
   - Si les variables d'environnement d'Azure ne sont pas configurées, le script retournera une erreur bloquante afin de s'assurer qu'aucun test ne tourne à vide.
   
3. **Dépendances**
   - Mettre à jour `requirements.txt` avec `azure-ai-formrecognizer` et `python-dotenv`.

## Critères de Validation
- Le script `process_document_ocr.py` s'exécute sans erreur de syntaxe.
- Le fichier `requirements.txt` est à jour.
- Le fichier de déploiement Azure CLI est prêt à l'emploi.
