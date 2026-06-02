# Phase 4 : Audit et Comparaison Microsoft Fabric (Étape D)

## Objectif
Créer le moteur central de l'application d'audit. Ce moteur prend les données extraites d'un PDF (issues de la Phase 3), se connecte au SI de gestion hébergé sur Microsoft Fabric (données Artus), et identifie les écarts en appliquant des règles d'audit précises (notamment le *Fuzzy Matching* à 75% pour les noms).

## Tâches d'Exécution

1. **Intégration des dépendances pour l'Audit**
   - Mise à jour du fichier `requirements.txt` avec :
     - `pyodbc` : Pour exécuter des requêtes sur le SQL Endpoint de Fabric.
     - `azure-identity` : Pour l'authentification M2M (Entra ID) sans mot de passe vers Fabric.
     - `pandas` : Pour croiser facilement les données.
     - `thefuzz` et `python-Levenshtein` : Pour l'algorithme de correspondance floue (Fuzzy Matching défini dans les règles AGENTS.md).
   
2. **Script Moteur d'Audit (`scripts/audit_fabric_comparison.py`)**
   - **Input** : Fichier JSON de l'OCR (issu de `process_document_ocr.py`).
   - **Connexion Data** : Requête sur la base Fabric pour récupérer le client / les garanties. Si Fabric n'est pas accessible, un mode "Fallback" lira un faux dataset local pour ne pas bloquer les tests.
   - **Logique d'Audit** :
     - Règle 1 : *Correspondance des noms*. Utiliser `fuzz.ratio` pour s'assurer que le nom sur le document match à au moins 75% le nom dans la base (tolérance aux acronymes, accents, suffixes SA/SAS).
     - Règle 2 : *Calcul des Écarts*. `Écart = Montant Base de gestion (Fabric) - Montant Document (PDF)`.
   - **Output** : Un fichier hybride structuré au format JSON contenant le rapport des écarts (et un CSV pour affichage tableur classique).

## Critères de Validation
- Le code gère le Fuzzy matching correctement.
- Les fichiers générés (`audit_report.json` et `audit_report.csv`) reflètent bien les écarts calculés.
