# Phase 2 : Qualité Documentaire SharePoint (Étape B)

## Objectif
Standardiser et automatiser la création de l'arborescence des dossiers clients sur SharePoint en se basant strictement sur la `matrice_classement_clients.xlsx`. 
Cette standardisation est requise pour garantir que le moteur de RAG (Copilot Studio) et l'OCR (Azure AI Document Intelligence) trouvent les documents au bon endroit.

## Tâches d'Exécution

1. **Création du script d'automatisation PnP PowerShell**
   - Nom : `scripts/setup_sharepoint_client_folder.ps1`.
   - Fonction : Permet de créer la structure complète de la matrice métier pour un (ou plusieurs) client(s) donné(s) en entrée.
   - Pré-requis techniques : Module `PnP.PowerShell`.
   
2. **Arborescence cible (issue de la matrice)**
   - Le script doit itérer sur les catégories principales :
     - Pilotage technique
     - Pièces contractuelles
     - Juridique
     - Commercial (avec ses sous-dossiers Relation client et Etudes)
     - Gestion (avec ses sous-dossiers Données brutes, Gestion courante, Communication)
   - Et y injecter les sous-dossiers terminaux exacts (ex: `CCN`, `KBIS`, `Flyer de bienvenue`, etc.).

## Critères de Validation
- Le script s'exécute sans erreur avec PnP PowerShell.
- Lorsqu'on lui fournit un nom de client (ex: "CLI12345_ALPHA"), le script crée le dossier parent puis toute la hiérarchie.
