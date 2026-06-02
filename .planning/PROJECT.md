# AC360 — Assistant Commercial Client 360

## Vision du Projet
AC360 est un assistant commercial interne (POC) intégré à Microsoft 365 Copilot / Teams.
Son objectif est d'aider les équipes commerciales à **rechercher, résumer, et comprendre les dossiers clients** stockés dans SharePoint, de manière sécurisée et sourcée, afin d'accélérer la préparation des rendez-vous et de réduire les risques opérationnels.

## Principes Directeurs
1. **Lecture Seule (Secure by Design) :** AC360 ne modifie pas les documents.
2. **Gouvernance des Données :** AC360 répond uniquement à partir des sources autorisées (SharePoint, puis Fabric) en respectant les permissions de l'utilisateur (Entra ID).
3. **Anti-Hallucination :** Le bot cite ses sources, ne mélange jamais les clients, et indique explicitement s'il manque des informations ("Je n'ai pas trouvé...").
4. **Architecture par Couches :**
   - *Canal :* Teams
   - *Orchestrateur :* Copilot Studio
   - *Source :* SharePoint RAG
   - *Data / Traitement :* Azure AI Document Intelligence & Microsoft Fabric

## Cas d'Usage Principaux (MVP)
- Résumé du dossier client (360).
- Préparation de rendez-vous commercial.
- Vérification de la complétude d'un dossier client.
- Génération de brouillons (mail, FIC).
- Assistance documentaire juridique (sans avis juridique).
- Recherche d'informations dans les appels d'offres.
