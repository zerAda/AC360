# Roadmap Projet AC360

Cette feuille de route définit les grandes étapes de la construction de l'Assistant Client 360, alignées sur l'architecture cible.

## Phases d'Implémentation

### Phase 1 : Socle AC360 Sécurisé (Étape A)
- Intégration Teams et Copilot Studio.
- Authentification Entra ID.
- Cadrage des instructions (prompts) et des rubriques (topics) de base.
- Mise en place du RAG sur SharePoint avec sources sécurisées.
- *Statut : En cours*

### Phase 2 : Qualité Documentaire (Étape B)
- Structuration des dossiers clients dans SharePoint.
- Définition des métadonnées minimales et règles de nommage.
- Implémentation logique de la "Checklist de complétude" et détection des documents manquants.
- Gestion explicite des statuts documentaires (Brouillon, Validé, Archivé).

### Phase 3 : OCR Azure (Étape C)
- Intégration d'Azure AI Document Intelligence.
- Extraction automatique du texte, des tableaux et champs clés depuis des PDFs scannés/structurés.
- Pré-remplissage des métadonnées dans SharePoint.
- Workflow de validation humaine pour les champs critiques.

### Phase 4 : Fabric / Artus (Étape D)
- Consolidation des données de gestion (Artus) dans Microsoft Fabric via des tables normalisées.
- Définition des règles de contrôle et de rapprochement (ex: garanties SharePoint vs paramétrage Artus).
- Restitution des écarts par l'AC360 de manière explicable.

### Phase 5 : FIC Brouillon (Étape E)
- Mapping des champs et génération de fiches d'information commerciales brouillons.
- Renseignement automatique des sources et des incertitudes.

### Phase 6 : Juridique et Appels d'Offres (Étape F)
- Structuration de la base juridique.
- Assistance avancée à l'analyse d'exigences d'Appels d'Offres.
- Cadrage des limites de recommandations juridiques.
