# Phase 6 : Contrôle Juridique & Génération FIC (Étape F)

## Objectif
Ajouter une dimension réglementaire à l'application AC360.
1. Contrôler la présence des pièces obligatoires dans SharePoint (KBIS, Mandat) sans bloquer le traitement global.
2. Générer automatiquement un brouillon de FIC (Fiche d'Information et de Conseil) au format Microsoft Word (`.docx`) basé sur les données remontées par l'audit.

## Tâches d'Exécution

1. **Vérification Juridique (`scripts/check_legal_compliance.ps1`)**
   - Utilisation de PnP.PowerShell.
   - Entrée : `SiteUrl` et `ClientFolderName`.
   - Action : Vérifie si des fichiers existent dans les dossiers `Juridique/KBIS`, `Juridique/Mandat` et `Juridique/DUE - accord collectif`.
   - Sortie : Avertissements dans la console et génération d'un `legal_alerts.json`.

2. **Génération FIC (`scripts/generate_fic_draft.py`)**
   - Librairie : `python-docx` (à ajouter aux requirements).
   - Entrée : Fichier `audit_report.json` contenant les informations du client.
   - Action : Crée un document Word contenant les mentions légales obligatoires ("Devoir de Conseil"), le nom du client, et les garanties actuelles détectées (pour justifier le conseil).
   - Sortie : Fichier `FIC_Brouillon_[NomClient].docx`.

3. **Orchestration (`scripts/run_audit_pipeline.ps1`)**
   - Insérer ces deux nouvelles étapes dans l'orchestrateur.

## Critères de Validation
- Le script Word génère bien un `.docx` lisible par MS Word.
- Le script PnP ne plante pas si les dossiers sont vides, il signale juste l'absence de fichiers.
