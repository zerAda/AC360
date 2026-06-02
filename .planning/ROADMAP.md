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

### Phase 5 : Règles Métier et Intelligence Juridique (Étape E)
- Implémentation des règles de gestion d'Adel pour la génération des FIC (Modification vs Reprise).
- Mise en place du tableau de suivi des FIC (O:\FIC).
- Exigence stricte de RAG : forcer le bot à sourcer ses réponses et préciser la limite de responsabilité.
- Configuration du bot pour interroger la base documentaire globale "Juridique & Technique".

### Phase 6 : Synthèses et Modèles Documentaires (Étape F)
- Assistant métier interne interrogeant un dossier client (risques couverts, assureur, financement, cotisations).
- Génération de synthèses globales (ex: panorama des régimes pour préparer les BP).

### Phase 7 : Backlog & Projets Non Prioritaires
- Classification et rangement automatisé des documents dans les bons sous-dossiers selon la matrice de classement.
- Traitement des standards (leads).
- Assistance à l'analyse des appels d'offres et des cahiers des charges.
