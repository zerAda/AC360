# Phase 5 : Post-Audit et Sécurité (Étape E)

## Objectif
Clôturer le pipeline d'audit. Une fois l'analyse effectuée, alerter les équipes via Microsoft Teams s'il y a un écart, et déplacer le document analysé vers une zone d'archive sécurisée pour investigation humaine (tout en purgeant les fichiers temporaires locaux).

## Tâches d'Exécution

1. **Intégration Teams**
   - Mise à jour du `requirements.txt` avec `requests` pour effectuer les appels Webhook vers Teams.
   
2. **Script Post-Audit (`scripts/post_audit_workflow.py`)**
   - **Input** : Rapport d'audit JSON (Phase 4) et le fichier source (PDF).
   - **Logique** :
     - Vérifier la présence de la balise `ecart_detecte: true` dans le rapport JSON.
     - Si Oui -> Construire et envoyer une *Adaptive Card* ou un simple message Markdown au Webhook Teams configuré en variable d'environnement (`TEAMS_WEBHOOK_URL`).
     - Si Non -> Fin normale du processus.
   - **Archivage et Nettoyage** :
     - Créer un répertoire (ou se connecter à SharePoint) `Archives_Documentaires/A_Auditer`.
     - Déplacer physiquement le fichier PDF source de son dossier temporaire vers l'archive.
     - Nettoyer les fichiers résiduels locaux (le fichier temporaire PDF d'origine ne doit plus exister dans le dossier de travail).

## Critères de Validation
- En cas d'écart, une requête HTTP POST est bien formatée et envoyée à l'URL Teams.
- Le fichier source est bien déplacé dans le dossier `Archives_Documentaires` et disparaît du dossier racine/temporaire.
