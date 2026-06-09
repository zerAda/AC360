# Fix Backend Technical Debt (Claude's Findings)

Les mappers de Claude Code ont découvert 6 problèmes majeurs dans l'API Python et les scripts d'audit (backend). Le code Copilot Studio (Frontend YAML) que nous avons corrigé est intact, mais la passerelle API nécessite un correctif de sécurité et de robustesse avant le lancement.

## User Review Required
Aucun impact métier majeur, mais il s'agit d'un durcissement des règles de sécurité (IDOR) et de corrections de bugs de traitement OCR. 
Merci de valider ce plan d'action pour que je puisse lancer les réparations.

## Proposed Changes

---

### API Server (`scripts/api_server.py`)
- [MODIFY] [api_server.py](file:///C:/Users/adelz/OneDrive%20-%20GEREP/Bureau/Zeriri/AC360/scripts/api_server.py)
  - **IDOR sur le téléchargement** : L'endpoint de téléchargement ne vérifie pas l'appartenance du fichier. L'appel à `generate_fiche_rdv` enregistrera désormais l'UPN de l'utilisateur dans un fichier `meta.json` que l'endpoint `/api/download/` devra valider.
  - **Hardcode Azure Function** : Remplacement de `taskHub=TestHubName` par une variable d'environnement dynamique.

### Fiche RDV (`scripts/generate_fiche_rdv.py`)
- [MODIFY] [generate_fiche_rdv.py](file:///C:/Users/adelz/OneDrive%20-%20GEREP/Bureau/Zeriri/AC360/scripts/generate_fiche_rdv.py)
  - Ajout du support de sauvegarde sécurisée de l'UPN (`user_upn`) pour lier la fiche générée à son créateur et prévenir les IDORs.

### Pipeline Post-Audit (`scripts/post_audit_workflow.py`)
- [MODIFY] [post_audit_workflow.py](file:///C:/Users/adelz/OneDrive%20-%20GEREP/Bureau/Zeriri/AC360/scripts/post_audit_workflow.py)
  - **Bug de Timestamp** : Remplacement du format erroné `"%Y%md_%H%M%S"` par `"%Y%m%d_%H%M%S"`.
  - **Alignement Seuil Fuzzy** : L'alerte se déclenche actuellement si le score est `< 75`, alors que le moteur OCR exige `85`. Passage du déclencheur d'alerte à `< 85`.

### Moteur de Comparaison (`scripts/audit_fabric_comparison.py`)
- [MODIFY] [audit_fabric_comparison.py](file:///C:/Users/adelz/OneDrive%20-%20GEREP/Bureau/Zeriri/AC360/scripts/audit_fabric_comparison.py)
  - **Mismatch des champs OCR** : Correction de la logique d'extraction `nom_client`. Azure Document Intelligence génère des `keyValuePairs` standards, mais le code cherchait bêtement un objet `fields["nom_client"]`. 
  - **Alignement Seuil Fuzzy** : Mise à jour des commentaires et statuts d'erreur pour refléter le seuil strict de `85%`.

### Nettoyage du Dépôt
- Je vais supprimer les dossiers obsolètes `.claude/worktrees/` et `src/copilot-workspace/` pour éviter la confusion de code et purger l'historique fantôme.

## Verification Plan

- Exécution de tests lint sur les scripts Python.
- Vérification que la commande API Uvicorn se lance correctement.
- Confirmation de la suppression des dossiers dupliqués.
