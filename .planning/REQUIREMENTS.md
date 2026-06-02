# Exigences Métier et Sécurité (Requirements)

## Sécurité et Accès
- L'authentification via **Microsoft Entra ID** est obligatoire.
- Le bot doit hériter strictement des permissions SharePoint de l'utilisateur (RAG contextualisé).
- **Interdiction** d'utiliser la recherche web publique.
- **Interdiction** d'utiliser OneDrive personnel, Outlook, ou des conversations Teams comme source officielle de réponse au démarrage.

## Règles d'Intelligence Artificielle (Anti-Hallucination)
- Le modèle LLM (GPT-4) doit **toujours citer ses sources** documentaires.
- En cas de manque d'information, le bot doit répondre : *"Je n’ai pas trouvé d’information accessible sur ce client dans les documents disponibles."*
- Si le nom du client est ambigu, le bot doit **demander une clarification** avant de répondre.
- Le bot ne doit **jamais** donner d'avis juridique définitif.

## Périmètre Fonctionnel (MVP - Première Version)
| Fonction | Inclus | Commentaire |
|----------|--------|-------------|
| Recherche dossier client | OUI | RAG SharePoint actif |
| Synthèse avant rendez-vous | OUI | Cœur de valeur métier |
| Checklist de complétude | OUI | Identification des documents manquants |
| Brouillon mail commercial | OUI | Texte à copier-coller (pas d'envoi auto) |
| Brouillon FIC | OUI | Pas de modification de la FIC officielle |
| Modification automatique de documents | NON | Trop risqué pour la V1 (Read-Only) |
| Décision juridique auto | NON | Aide documentaire uniquement |
