# Vérification Documentation Microsoft — Phase 1

## Sources Consultées

- **Microsoft Learn** : https://learn.microsoft.com/en-us/microsoft-copilot-studio/
- Documentation officielle Copilot Studio knowledge sources

## Éléments Confirmés par Microsoft

### 1. SharePoint comme source de connaissance Copilot Studio

**Confirmed** ✓

- Copilot Studio permet d'ajouter un site SharePoint comme source de connaissance
- Connexion via URL SharePoint (ex: `contoso.sharepoint.com/sites/clients`)
- Utilise l'authentification Microsoft Entra ID de l'utilisateur
- Les utilisateurs doivent avoir les droits SharePoint nécessaires
- Limite : 4 URLs SharePoint par agent
- Fichiers supportés : Word (DOC/DOCX), PowerPoint (PPT/PPTX), PDF
- Taille max : 200 MB (avec Microsoft 365 Copilot), 7 MB (sans)

**Confirmed** ✓ via Microsoft Learn

### 2. Publication dans Teams

**Confirmed** ✓

- Copilot Studio permet de publier des agents dans Teams
- Par défaut, l'authentification Microsoft est configurée pour Teams
- Les utilisateurs accèdent via leur compte Microsoft 365

**Confirmed** ✓ via Microsoft Learn

### 3. Publication dans SharePoint

**Confirmed** ✓ ( depuis Mai 2025)

- Nouvelles fonctionnalités 2025 Release Wave 1
- Possibilité de publier des agents sur des sites SharePoint
- Publication disponible depuis Mai 2025

**Confirmed** ✓ via Microsoft Learn release plan

### 4. Fonctionnement des permissions

**Confirmed** ✓

- Les réponses sont filtrées selon les permissions SharePoint de l'utilisateur
- Un utilisateur ne peut pas voir de documents auquel il n'a pas accès dans SharePoint
- L'authentification SharePoint valide les droits avant réponse
- Utilisation de Microsoft authentication par défaut

**Confirmed** ✓ via Microsoft Learn

### 5. Tenant Graph Grounding

**Recommandation** (pas confirmé obligatoire)

- Améliore la qualité de recherche avec Microsoft 365 Copilot
- Utilise Semantic Search pour de meilleurs résultats
- Optionnel mais recommandé

**Nota** : Cette fonctionnalité nécessite une licence Microsoft 365 Copilot

## Éléments Non Confirmés (Hypothèses)

### Points nécessitant validation

1. **Indexation en temps réel** : Hypothèse - SharePoint search indexe automatiquement, délais possibles
2. **Gestion des métadonnées** : Pas de confirmation explicite dans la doc
3. **Filtrage par dossier** : Limité aux permissions SharePointuelles
4. **Taille des fichiers** : Confirmé mais non testé en conditions réelles

## Éléments Non Recommandés pour le POC

### Non confirmée comme Scénario A

1. **Microsoft Purview** : Hors périmètre (non demandé)
2. **Azure AI Search** : Hors périmètre (non demandé)
3. **Dataverse stockage** : Optionnel, pas nécessaire pour le POC simple
4. **Connecteurs externes** : Pas autorisés dans le scénario A

---

*Document créé : 2026-04-28 - Vérification documentation Microsoft Phase 1*