# AC360 — Personas

> **Objet du document.** Décrire les utilisateurs cibles d'AC360 et préciser, pour chacun, ce que l'assistant fait et — tout aussi important — ce qu'il ne fait **pas**.
>
> **Rappel de cadrage.** AC360 est un assistant IA Microsoft Copilot Studio **en lecture seule**, connecté aux dossiers clients SharePoint, destiné aux équipes de courtage en assurance santé / prévoyance collective. Il répond **uniquement** à partir des documents SharePoint **accessibles à l'utilisateur connecté**, cite ses sources (nom de fichier) et n'invente jamais.
>
> **Mentions de maturité.** Les éléments dépendant d'Azure, Microsoft Fabric, SharePoint ou Entra ID en conditions réelles sont marqués **« À VALIDER EN ENVIRONNEMENT RÉEL »**. Aucun élément de ce document ne doit être lu comme une garantie « production ready », « enterprise ready » ou « DLP validée ».

---

## Vue d'ensemble

| # | Persona | Rôle résumé | Usage principal d'AC360 |
|---|---------|-------------|--------------------------|
| 1 | **Commercial / chargé de compte** | Suivi et développement d'un portefeuille clients | Préparer ses RDV, retrouver l'information dans les dossiers |
| 2 | **Responsable commercial / manager** | Pilotage d'une équipe commerciale | Visibilité sur la complétude et la qualité des dossiers de l'équipe |
| 3 | **Gestionnaire de contrats** | Administration et fiabilité des dossiers contractuels | Vérifier la complétude, retrouver les pièces, contrôler la cohérence |
| 4 | **RSSI / Admin Power Platform** | Sécurité, conformité et gouvernance de la plateforme | Garantir le périmètre lecture seule, les permissions et la traçabilité |

**Capacités communes (topics Copilot vérifiés, qui affichent leur réponse) :** résumé de dossier client, préparation de rendez-vous, documents manquants (complétude), points d'attention, recherche de document client, brouillon de mail commercial, arguments de vente, demande de clarification, refus de toute modification/suppression de document, recherche juridique documentaire.

**Garde-fous communs à tous les personas :** réponses issues uniquement de SharePoint accessible à l'utilisateur ; pas de web ; pas d'Outlook/OneDrive personnel ; permissions respectées ; jamais confirmer l'existence d'un client ou d'un document inaccessible ; jamais mélanger deux clients ; citations obligatoires ; le contenu des documents est traité comme **non fiable** (protection anti-injection) ; pas de promesse commerciale non sourcée ; pas d'avis juridique définitif. (`useModelKnowledge=false`, `contentModeration=High`.)

---

## Persona 1 — Commercial / chargé de compte

### Rôle
Gère et développe un portefeuille de clients (entreprises) en assurance santé et prévoyance collective. Prépare et anime les rendez-vous, répond aux sollicitations, rédige les échanges commerciaux et fait avancer les dossiers.

### Objectifs
- Arriver préparé à chaque rendez-vous, avec une vision claire et à jour du dossier.
- Retrouver rapidement la bonne information ou le bon document dans un dossier client.
- Gagner du temps sur les tâches répétitives (synthèses, premiers jets de mails).
- Ne rien laisser passer : points d'attention, échéances, pièces manquantes.

### Frustrations actuelles
- Dossiers SharePoint volumineux et hétérogènes : l'information est dispersée.
- Temps de préparation des RDV trop long, souvent fait dans l'urgence.
- Risque d'oublier une pièce ou un point sensible faute de relecture exhaustive.
- Repartir d'une page blanche pour chaque mail ou chaque synthèse.

### Comment AC360 aide
- **Résumé de dossier client** : synthèse rapide d'un dossier, sourcée par nom de fichier.
- **Préparation de rendez-vous** : points clés, éléments récents et sujets à aborder.
- **Points d'attention** : signalement des éléments sensibles présents dans les documents accessibles.
- **Recherche de document client** : localiser une pièce précise dans le dossier.
- **Brouillon de mail commercial** et **arguments de vente** : premiers jets à relire et personnaliser.
- **Clarification** : si la demande est ambiguë, AC360 pose une question plutôt que de deviner.

### Ce qu'AC360 NE fait PAS pour lui (limites / sécurité)
- Ne modifie, ne déplace, ni ne supprime **aucun** document (lecture seule ; tout demande de modification est refusée).
- N'accède à **aucun** dossier hors de ses propres permissions SharePoint, et ne confirme jamais l'existence d'un client ou d'un document qu'il ne peut pas voir.
- Ne mélange jamais deux clients dans une même réponse.
- N'invente aucun chiffre, garantie ou clause : pas de promesse commerciale non sourcée.
- Ne fournit pas d'avis juridique définitif ni d'information venant du web ou d'une boîte mail personnelle.
- Le brouillon de mail et les arguments de vente restent des **propositions à valider** par le commercial — ils ne sont jamais envoyés automatiquement.

### KPIs pertinents
- Temps de préparation d'un rendez-vous (avant / après).
- Nombre de synthèses de dossier générées.
- Taux de réponses correctement sourcées (citation présente).
- Adoption (utilisateurs actifs, fréquence d'usage).

---

## Persona 2 — Responsable commercial / manager

### Rôle
Encadre une équipe de commerciaux / chargés de compte. Pilote l'activité, veille à la qualité et à la complétude des dossiers, prépare les points d'équipe et accompagne la montée en compétence.

### Objectifs
- Avoir une vision fiable de l'état des dossiers de l'équipe.
- Identifier rapidement les dossiers incomplets ou à risque.
- Homogénéiser la qualité des préparations et des échanges clients.
- Réduire le temps passé par l'équipe sur les tâches à faible valeur ajoutée.

### Frustrations actuelles
- Manque de visibilité consolidée sur la complétude des dossiers.
- Qualité de préparation variable selon les commerciaux.
- Difficulté à repérer en amont les dossiers qui posent problème.

### Comment AC360 aide
- **Documents manquants (complétude)** : mise en évidence des pièces absentes d'un dossier accessible.
- **Points d'attention** : repérage des éléments sensibles à suivre.
- **Résumé de dossier** : prise de connaissance rapide d'un dossier avant un point d'équipe.
- Outil partagé qui **standardise** la façon de préparer et de synthétiser, à condition que le manager dispose des accès SharePoint correspondants.

### Ce qu'AC360 NE fait PAS pour lui (limites / sécurité)
- N'est **pas** un outil de reporting RH ou de scoring de performance individuelle : il n'évalue pas les commerciaux.
- Ne contourne **pas** les permissions : un manager ne voit via AC360 que les dossiers auxquels **ses propres accès** donnent droit (pas de vue « super-admin » implicite).
- Ne produit pas de tableau de bord ou de KPI consolidé automatiquement — la mesure des indicateurs reste un dispositif à mettre en place à part. **À VALIDER EN ENVIRONNEMENT RÉEL.**
- Ne modifie ni ne supprime aucun document, ne mélange jamais deux clients, n'invente aucune donnée.

### KPIs pertinents
- Taux de complétude des dossiers de l'équipe (évolution dans le temps).
- Nombre de dossiers signalés comme incomplets puis régularisés.
- Homogénéité de la qualité de préparation (qualitatif).
- Adoption au sein de l'équipe.

---

## Persona 3 — Gestionnaire de contrats

### Rôle
Assure l'administration et la fiabilité des dossiers contractuels : classement des pièces, vérification de la complétude, contrôle de cohérence entre les documents reçus et les données de gestion.

### Objectifs
- Garantir des dossiers complets et bien classés.
- Détecter rapidement les incohérences (montants, dates, noms, références de contrat).
- Retrouver une pièce précise sans parcourir tout le dossier.
- Fiabiliser les données avant transmission ou décision commerciale.

### Frustrations actuelles
- Contrôles de cohérence manuels, longs et sujets à l'erreur.
- Pièces manquantes détectées tardivement.
- Recherche fastidieuse d'un document dans des dossiers volumineux.

### Comment AC360 aide
- **Documents manquants (complétude)** : liste des pièces absentes d'un dossier accessible.
- **Recherche de document client** : localisation rapide d'une pièce.
- **Recherche juridique documentaire** : retrouver un élément dans les documents accessibles (sans constituer un avis juridique).
- **Capacité d'aide au contrôle de cohérence** côté backend : un moteur de comparaison (OCR ↔ données de gestion) normalise montants, dates, noms et références de contrat et restitue des statuts `MATCH` / `MISMATCH` / `UNCERTAIN` / `MISSING` avec un score de confiance. Ce moteur est **testé hors ligne** ; son intégration de bout en bout (OCR Azure Document Intelligence, Microsoft Fabric) reste **À VALIDER EN ENVIRONNEMENT RÉEL**.

### Ce qu'AC360 NE fait PAS pour lui (limites / sécurité)
- Ne **corrige** pas et ne **complète** pas les dossiers : il **signale**, l'action reste humaine (lecture seule, toute modification est refusée).
- Côté assistant Copilot, le déclenchement d'un audit affiche honnêtement que **la fonctionnalité d'audit est en cours de déploiement** : aucune simulation n'est présentée comme un résultat réel.
- Les statuts du moteur de comparaison (`UNCERTAIN`, score de confiance) sont une **aide à la décision**, pas un verdict : ils nécessitent une relecture humaine.
- Ne traite aucune donnée hors du périmètre accessible et ne mélange jamais deux clients.

### KPIs pertinents
- Taux de complétude des dossiers contrôlés.
- Nombre d'incohérences détectées et corrigées en amont.
- Temps moyen de recherche d'une pièce.
- Part des dossiers fiabilisés avant transmission.

---

## Persona 4 — RSSI / Admin Power Platform

### Rôle
Responsable de la sécurité, de la conformité et de la gouvernance de la solution sur Power Platform / Microsoft 365. Définit et contrôle le périmètre, les accès, les politiques DLP et la traçabilité.

### Objectifs
- Garantir le caractère **lecture seule** et le respect strict des permissions SharePoint.
- S'assurer qu'aucune donnée ne fuit hors du périmètre autorisé (pas de web, pas de messagerie personnelle).
- Disposer d'une traçabilité des traitements et d'une gestion saine des secrets.
- Maîtriser les fonctionnalités en aperçu (Preview) et leur gouvernance.

### Frustrations actuelles
- Difficulté à prouver qu'un assistant IA respecte réellement le périmètre annoncé.
- Crainte des fuites de données et des injections via le contenu des documents.
- Manque de traçabilité de bout en bout sur les traitements automatisés.

### Comment AC360 aide
- **Garde-fous RAG explicites et vérifiés** dans la configuration de l'agent : réponses depuis SharePoint accessible uniquement, pas de web, pas d'Outlook/OneDrive perso, permissions respectées, jamais de confirmation d'un élément inaccessible, jamais de mélange entre clients, citations obligatoires, contenu des documents traité comme non fiable (anti-injection), `useModelKnowledge=false`, `contentModeration=High`.
- **Posture honnête côté Copilot** : le topic d'audit annonce une fonctionnalité « en cours de déploiement » plutôt que de simuler un résultat.
- **Backend conçu pour la sécurité** (réel, testé hors ligne) : authentification Entra ID via JWKS RS256 avec scopes/rôles ; protection anti *path-traversal* (`safe_paths`) ; rédaction des secrets dans les logs (`safe_logger`) ; traçabilité des traitements via un *job store* (identifiant de job externe + identifiant de tâche interne, suivi du cycle de vie). **134 tests pytest** au vert.
- **Actions WorkIQ / MCP (Preview) désactivées par défaut**, la gouvernance DLP n'étant pas prouvée.

### Ce qu'AC360 NE fait PAS pour lui (limites / sécurité)
- N'élargit jamais les droits d'un utilisateur : AC360 s'appuie sur les permissions SharePoint existantes, il n'en crée pas.
- Ne prétend pas être « production ready », « enterprise ready » ni « DLP validée » : ces qualifications nécessitent une validation formelle. **À VALIDER EN ENVIRONNEMENT RÉEL.**
- N'active pas les connecteurs Azure Document Intelligence / Microsoft Fabric ni les actions Preview sans décision et validation de gouvernance explicites.
- Ne stocke pas de secrets en clair et ne les expose pas dans les journaux.
- Les tests verts attestent du comportement **hors ligne** ; ils ne se substituent pas à une recette en environnement réel (Azure / Fabric / SharePoint / Entra).

### KPIs pertinents
- Nombre d'incidents de sécurité : **0** (cible).
- Taux de réponses correctement sourcées (preuve du respect du périmètre documentaire).
- Couverture et résultat des tests automatisés (134 tests verts, suivi dans le temps).
- Absence de fonctionnalités Preview activées sans validation DLP.
- Traçabilité : part des traitements disposant d'un identifiant de job et d'un cycle de vie suivi.

---

## Synthèse — ce qu'AC360 ne fait pour personne

Quel que soit le persona, AC360 :

1. **ne modifie, ne déplace ni ne supprime** aucun document (lecture seule) ;
2. **ne sort jamais du périmètre** accessible à l'utilisateur (pas de web, pas de messagerie personnelle, permissions respectées) ;
3. **ne confirme jamais** l'existence d'un client ou d'un document inaccessible ;
4. **ne mélange jamais** deux clients ;
5. **n'invente rien** et **cite toujours** ses sources ;
6. **ne donne pas** d'avis juridique définitif ni de promesse commerciale non sourcée ;
7. **traite le contenu des documents comme non fiable** (protection anti-injection).

> Les capacités reposant sur Azure Document Intelligence, Microsoft Fabric, SharePoint ou Entra ID en conditions réelles restent **À VALIDER EN ENVIRONNEMENT RÉEL**.
