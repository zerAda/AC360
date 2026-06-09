# AC360 — Cadre de KPIs

> **Version** : 1.0
> **Date** : 2026-06-04
> **Propriétaire** : Product Owner AC360
> **Contributeurs** : Responsable commercial, Admin Power Platform, RSSI
> **Révision** : Trimestrielle

---

## Avertissement sur les cibles

> ⚠️ **Les cibles chiffrées de ce document sont INDICATIVES et À VALIDER AVEC LE MÉTIER.**
> Elles servent de point de départ à la discussion (baseline de lancement). Aucune valeur n'a été calibrée
> sur des données de production AC360 réelles. Elles doivent être confirmées, ajustées ou remplacées par
> le Product Owner, le responsable commercial et le RSSI avant tout engagement de pilotage ou de reporting
> à la direction.

> ⚠️ **Périmètre de mesure réel.** AC360 est un assistant **en lecture seule** (Copilot Studio + RAG sur
> dossiers clients SharePoint). Les KPIs ci-dessous se mesurent à partir des sources réellement disponibles :
> **Copilot Studio Analytics**, **logs Entra ID / Power Platform / DLP**, **Application Insights** (si l'API
> FastAPI est activée), et **enquêtes terrain**. Les métriques dépendant d'Azure / Microsoft Fabric / SharePoint /
> Entra en environnement réel sont marquées **« À VALIDER EN ENVIRONNEMENT RÉEL »**.

> ℹ️ Les fonctionnalités d'audit OCR↔gestion (Azure Document Intelligence + Microsoft Fabric / Artus, topic
> `LancerAudit`) sont **en cours de déploiement** côté Copilot. Les KPIs qui en dépendent sont signalés comme
> **non encore mesurables** tant que la fonction n'est pas activée en environnement réel.

---

## Vue d'ensemble des catégories

| # | Catégorie | Question à laquelle elle répond | Audience principale |
|---|---|---|---|
| 1 | **Adoption** | L'outil est-il utilisé, par qui, à quelle fréquence ? | PO, Responsable commercial |
| 2 | **Productivité** | Fait-il gagner du temps aux équipes ? | Responsable commercial, Direction |
| 3 | **Qualité / Fiabilité** | Les réponses sont-elles sourcées et les garde-fous tiennent-ils ? | PO, RSSI |
| 4 | **Sécurité / Conformité** | Y a-t-il des incidents ou des accès non autorisés ? | RSSI, Admin Power Platform |
| 5 | **Valeur métier** | L'outil produit-il un impact commercial mesurable ? | Direction, Responsable commercial |

### Lecture des colonnes

- **Définition** : ce que mesure le KPI, en une phrase.
- **Formule / mesure** : comment il se calcule.
- **Cible indicative** : point de départ — **À VALIDER avec le métier**.
- **Source de la mesure** : d'où provient la donnée (outil / rapport).
- **Fréquence** : cadence de relevé.

---

## 1. Adoption

> Objectif : vérifier que l'outil est réellement utilisé par les équipes commerciales visées.

### 1.1 Utilisateurs actifs hebdomadaires (WAU)

- **Définition** : nombre d'utilisateurs distincts ayant démarré au moins une conversation AC360 sur une semaine glissante.
- **Formule / mesure** : `COUNT DISTINCT(utilisateurs avec ≥ 1 conversation sur 7 jours)`.
- **Cible indicative** : **> 50 % de l'équipe commerciale** active au moins 1×/semaine à 3 mois ; **> 70 %** à 6 mois.
- **Source de la mesure** : Copilot Studio Analytics — utilisateurs uniques. *À VALIDER EN ENVIRONNEMENT RÉEL.*
- **Fréquence** : hebdomadaire (revue), mensuelle (reporting).

### 1.2 Taux de pénétration de l'équipe

- **Définition** : proportion de la population cible (commerciaux + managers + gestionnaires) ayant utilisé AC360 au moins une fois sur le mois.
- **Formule / mesure** : `utilisateurs actifs mensuels / effectif cible total × 100`.
- **Cible indicative** : **> 60 %** à 3 mois ; **> 80 %** à 6 mois.
- **Source de la mesure** : Copilot Studio Analytics (utilisateurs uniques) ÷ effectif cible (RH / annuaire). *À VALIDER EN ENVIRONNEMENT RÉEL.*
- **Fréquence** : mensuelle.

### 1.3 Conversations par utilisateur actif

- **Définition** : intensité d'usage — nombre moyen de conversations par utilisateur actif.
- **Formule / mesure** : `nombre total de conversations / nombre d'utilisateurs actifs` (sur la période).
- **Cible indicative** : **≥ 3 conversations / utilisateur actif / semaine** (baseline à confirmer).
- **Source de la mesure** : Copilot Studio Analytics — sessions. *À VALIDER EN ENVIRONNEMENT RÉEL.*
- **Fréquence** : mensuelle.

### 1.4 Rétention à 30 jours

- **Définition** : part des nouveaux utilisateurs qui reviennent utiliser AC360 dans les 30 jours suivant leur première conversation.
- **Formule / mesure** : `utilisateurs actifs en mois N ayant aussi été actifs en mois N-1 / utilisateurs actifs en mois N-1 × 100`.
- **Cible indicative** : **> 60 %** (baseline à confirmer).
- **Source de la mesure** : Copilot Studio Analytics (cohortes d'usage). *À VALIDER EN ENVIRONNEMENT RÉEL.*
- **Fréquence** : mensuelle.

### 1.5 Couverture des topics

- **Définition** : répartition de l'usage entre les topics réellement disponibles (Résumé dossier, Préparation RDV, Documents manquants, Points d'attention, Recherche document, Brouillon mail, Arguments de vente, etc.).
- **Formule / mesure** : `conversations par topic / conversations totales × 100`.
- **Cible indicative** : pas de cible chiffrée — KPI **diagnostique** (identifier les topics sous-utilisés à promouvoir ou retirer).
- **Source de la mesure** : Copilot Studio Analytics — Topics.
- **Fréquence** : mensuelle.

---

## 2. Productivité

> Objectif : quantifier le gain de temps apporté aux équipes. Ces KPIs reposent largement sur des
> **enquêtes terrain avant/après** ; ils sont déclaratifs et doivent être interprétés avec prudence.

### 2.1 Temps de préparation d'un rendez-vous

- **Définition** : temps moyen passé par un commercial pour préparer un RDV client (collecte d'infos, synthèse du dossier).
- **Formule / mesure** : `moyenne(temps déclaré « après » AC360) vs moyenne(temps déclaré « avant »)` ; gain = `(avant − après) / avant × 100`.
- **Cible indicative** : **réduction de 50 %** du temps de préparation.
- **Source de la mesure** : enquête terrain avant/après (échantillon de commerciaux). *Déclaratif — à corroborer.*
- **Fréquence** : mesure de référence au lancement, puis trimestrielle.

### 2.2 Nombre de synthèses / brouillons générés

- **Définition** : volume de livrables produits avec l'aide d'AC360 (résumés de dossier, brouillons de mail commercial, listes de points d'attention).
- **Formule / mesure** : `COUNT(conversations déclenchant les topics Résumé dossier / Brouillon mail / Points d'attention)`.
- **Cible indicative** : tendance **croissante** mois après mois (pas de seuil absolu en phase de lancement).
- **Source de la mesure** : Copilot Studio Analytics — Topics. *À VALIDER EN ENVIRONNEMENT RÉEL.*
- **Fréquence** : mensuelle.

### 2.3 Temps de recherche d'un document client

- **Définition** : temps moyen pour retrouver un document dans un dossier client SharePoint via AC360 (topic Recherche document) vs recherche manuelle.
- **Formule / mesure** : `moyenne(temps « avant ») − moyenne(temps « après »)`, en minutes.
- **Cible indicative** : **gain ≥ 50 %** (déclaratif, à confirmer).
- **Source de la mesure** : enquête terrain avant/après. *Déclaratif — à corroborer.*
- **Fréquence** : trimestrielle.

### 2.4 Latence moyenne de réponse

- **Définition** : temps de réponse moyen de l'assistant (indicateur de fluidité, prérequis à la productivité perçue).
- **Formule / mesure** : `moyenne(temps de réponse du bot par message)`.
- **Cible indicative** : **< 5 s** en moyenne (seuil d'alerte aligné sur le Plan de Monitoring).
- **Source de la mesure** : Copilot Studio Analytics ; Application Insights (P95) si l'API FastAPI est activée. *À VALIDER EN ENVIRONNEMENT RÉEL.*
- **Fréquence** : quotidienne (alerte), mensuelle (reporting).

> 📌 *Voir aussi* `docs/observability/MONITORING_PLAN.md` pour les seuils d'alerte de latence (moyenne > 5 s, P95 API > 10 s).

---

## 3. Qualité / Fiabilité

> Objectif : démontrer que les réponses sont **sourcées** et que les **garde-fous RAG** (anti-injection,
> refus de modification, cloisonnement client) fonctionnent. C'est le cœur de la promesse AC360 :
> *« des réponses précises, sourcées et sécurisées »*.

### 3.1 Taux de réponses sourcées

- **Définition** : part des réponses de contenu (hors messages d'accueil/clarification) qui citent au moins une source (nom de fichier SharePoint), conformément à la règle de citation obligatoire du `RAG_POLICY.md` / `agent.mcs.yml`.
- **Formule / mesure** : `réponses contenant ≥ 1 citation de fichier / réponses de contenu éligibles × 100`. Mesure par **échantillonnage qualité** (revue manuelle d'un échantillon de transcriptions) à défaut d'instrumentation automatique.
- **Cible indicative** : **> 95 %** des réponses de contenu sourcées.
- **Source de la mesure** : revue qualité manuelle d'un échantillon (transcriptions Copilot, métadonnées uniquement — **jamais** de contenu client logué). *À VALIDER EN ENVIRONNEMENT RÉEL.*
- **Fréquence** : mensuelle (échantillon).

### 3.2 Taux de refus corrects (garde-fous)

- **Définition** : part des sollicitations interdites correctement refusées par l'assistant. Sont comptées comme « à refuser » : demande de modification/suppression de document, demande sur un client/document inaccessible, demande hors périmètre (web, Outlook/OneDrive perso), tentative d'injection de prompt via le contenu d'un document.
- **Formule / mesure** : `refus corrects / sollicitations interdites identifiées × 100` sur un échantillon de test et de production.
- **Cible indicative** : **100 %** sur le jeu de tests de garde-fous ; **> 98 %** en production (sur échantillon).
- **Source de la mesure** : jeu de tests « red team » / garde-fous (cf. `SECURITY_GATE.md`) + revue qualité d'échantillon de production. *À VALIDER EN ENVIRONNEMENT RÉEL.*
- **Fréquence** : à chaque release (tests) + mensuelle (échantillon production).

### 3.3 Taux de fallback

- **Définition** : part des messages renvoyés au topic Fallback (question non comprise / hors sujet couvert).
- **Formule / mesure** : `messages vers Fallback / messages totaux × 100`.
- **Cible indicative** : **< 15 %** (au-delà → enrichir les topics).
- **Source de la mesure** : Copilot Studio Analytics — taux de fallback. *À VALIDER EN ENVIRONNEMENT RÉEL.*
- **Fréquence** : hebdomadaire.

### 3.4 Satisfaction utilisateur (CSAT / NPS)

- **Définition** : appréciation des réponses par les utilisateurs (notes positives Copilot) et recommandation globale (NPS via enquête).
- **Formule / mesure** : CSAT = `réponses notées positivement / réponses notées × 100` ; NPS = `% promoteurs − % détracteurs`.
- **Cible indicative** : **CSAT > 70 %** ; **NPS > 7/10** à 3 mois, **> 8/10** à 6 mois.
- **Source de la mesure** : Copilot Studio Analytics (CSAT) + enquête mensuelle (NPS).
- **Fréquence** : hebdomadaire (CSAT), mensuelle (NPS).

### 3.5 Taux d'erreur technique

- **Définition** : part des conversations terminées en erreur technique (hors fallback fonctionnel).
- **Formule / mesure** : `conversations en erreur / conversations totales × 100`.
- **Cible indicative** : **< 5 %** (seuil d'alerte aligné sur le Plan de Monitoring).
- **Source de la mesure** : Copilot Studio Analytics ; codes 4xx/5xx Application Insights si API activée. *À VALIDER EN ENVIRONNEMENT RÉEL.*
- **Fréquence** : quotidienne.

### 3.6 Exactitude du moteur de comparaison OCR↔gestion *(non encore mesurable en production)*

- **Définition** : justesse des statuts produits par `comparison_engine.py` (MATCH / MISMATCH / UNCERTAIN / MISSING) vs vérité terrain.
- **Formule / mesure** : `comparaisons correctes / comparaisons vérifiées × 100`, par statut ; suivi complémentaire de la distribution des scores de confiance.
- **Cible indicative** : **à définir avec le métier** une fois la fonction d'audit déployée (aucune cible engageante avant calibration réelle).
- **Source de la mesure** : jeu de tests pytest (134 tests verts hors-ligne, base de non-régression) + validation sur dossiers réels. **Topic `LancerAudit` en cours de déploiement.** *À VALIDER EN ENVIRONNEMENT RÉEL.*
- **Fréquence** : à chaque release (tests) ; production non applicable tant que la fonction n'est pas active.

---

## 4. Sécurité / Conformité

> Objectif : garantir qu'aucun incident de sécurité n'est confirmé et qu'aucun accès non autorisé
> n'aboutit. Ces KPIs sont sous responsabilité **RSSI + Admin Power Platform**.

### 4.1 Incidents de sécurité confirmés

- **Définition** : nombre d'incidents de sécurité confirmés impliquant AC360 (fuite de données client, contournement des garde-fous avéré, exposition de secret).
- **Formule / mesure** : `COUNT(incidents confirmés)` sur la période.
- **Cible indicative** : **0 incident confirmé**.
- **Source de la mesure** : rapport sécurité RSSI mensuel ; `RUNBOOK_INCIDENTS.md`. *À VALIDER EN ENVIRONNEMENT RÉEL.*
- **Fréquence** : mensuelle (et au fil de l'eau si incident).

### 4.2 Accès non autorisés bloqués

- **Définition** : nombre de tentatives d'accès non autorisées correctement rejetées (échecs d'authentification, scopes/roles insuffisants, accès à un dossier client hors permissions).
- **Formule / mesure** : `COUNT(401/403 légitimes + refus de permission SharePoint/Entra)`. **Toutes doivent être bloquées** : le KPI suit le **taux de blocage = 100 %**, pas un volume cible.
- **Cible indicative** : **100 % des tentatives non autorisées bloquées** (aucun accès indu abouti).
- **Source de la mesure** : logs Entra ID (sign-in), logs API FastAPI (auth JWKS RS256 + scopes/roles), logs Power Platform. *À VALIDER EN ENVIRONNEMENT RÉEL.*
- **Fréquence** : hebdomadaire (revue), mensuelle (reporting).

### 4.3 Incidents DLP

- **Définition** : nombre de violations DLP détectées (tentative d'usage d'un connecteur non autorisé / sortie de périmètre Microsoft 365 GEREP).
- **Formule / mesure** : `COUNT(violations DLP)` sur la période.
- **Cible indicative** : **0 violation DLP**.
- **Source de la mesure** : logs DLP Power Platform (rétention 180 j). *À VALIDER EN ENVIRONNEMENT RÉEL.*
- **Fréquence** : mensuelle (alerte immédiate si occurrence).

> ⚠️ Les actions **WorkIQ / MCP (Preview)** sont **désactivées par défaut** (gouvernance DLP non prouvée).
> Tant qu'elles ne sont pas validées par le RSSI, aucun KPI ne doit présupposer leur activation.

### 4.4 Fuite de données dans les logs

- **Définition** : nombre d'occurrences de données interdites détectées dans les logs (nom de client, contenu de document, token complet, secret).
- **Formule / mesure** : `COUNT(occurrences détectées)` via contrôle/audit des logs (le `safe_logger` rédige les secrets côté API).
- **Cible indicative** : **0 occurrence**.
- **Source de la mesure** : audit périodique des logs (cf. liste « Logs INTERDITS » du `MONITORING_PLAN.md`). *À VALIDER EN ENVIRONNEMENT RÉEL.*
- **Fréquence** : mensuelle.

### 4.5 Échecs d'authentification anormaux

- **Définition** : pics d'échecs d'authentification pouvant indiquer une attaque (ex. échecs JWT répétés).
- **Formule / mesure** : `COUNT(échecs auth)` avec seuil d'alerte ; suivi des échecs JWT consécutifs.
- **Cible indicative** : **alerte RSSI au-delà de 3 échecs JWT consécutifs** (seuil aligné sur le Plan de Monitoring).
- **Source de la mesure** : logs Entra ID + logs API FastAPI. *À VALIDER EN ENVIRONNEMENT RÉEL.*
- **Fréquence** : quotidienne (alerte), mensuelle (reporting).

### 4.6 Conformité de la traçabilité (auditabilité)

- **Définition** : part des opérations sensibles tracées de bout en bout (job_id externe ↔ task_id interne, lifecycle), prérequis à l'audit et à la conformité.
- **Formule / mesure** : `opérations correctement tracées / opérations attendues × 100` (le `job_store` assure la traçabilité côté API).
- **Cible indicative** : **100 %** des opérations sensibles tracées.
- **Source de la mesure** : `job_store` / logs API FastAPI. *À VALIDER EN ENVIRONNEMENT RÉEL.*
- **Fréquence** : mensuelle (échantillon).

---

## 5. Valeur métier

> Objectif : relier l'usage d'AC360 à un impact commercial tangible. Ces KPIs sont **les plus difficiles
> à attribuer** à l'outil seul (nombreux facteurs externes) : ils s'interprètent comme des indicateurs de
> **contribution**, pas de causalité directe. Cibles **impérativement à co-construire avec le métier**.

### 5.1 Complétude des dossiers clients

- **Définition** : part des dossiers clients sans document manquant identifié (via le topic Documents manquants).
- **Formule / mesure** : `dossiers complets / dossiers analysés × 100`.
- **Cible indicative** : **tendance croissante** (amélioration mois après mois) ; seuil cible à fixer avec le métier.
- **Source de la mesure** : usage du topic Documents manquants + suivi métier des dossiers. *Partiellement déclaratif — à corroborer.*
- **Fréquence** : mensuelle / trimestrielle.

### 5.2 Délai de complétion d'un dossier

- **Définition** : temps moyen entre l'ouverture d'un dossier et sa complétude (tous documents requis présents).
- **Formule / mesure** : `moyenne(date complétude − date ouverture)`, comparaison avant/après AC360.
- **Cible indicative** : **réduction du délai** (cible chiffrée à définir avec le métier).
- **Source de la mesure** : données métier / SharePoint + enquête. *Déclaratif / à instrumenter — à valider.*
- **Fréquence** : trimestrielle.

### 5.3 Capacité commerciale dégagée (temps réinvesti)

- **Définition** : temps libéré par AC360 (préparation RDV, recherche doc, synthèses) réinvesti dans des activités commerciales à plus forte valeur.
- **Formule / mesure** : estimation = `gain de temps unitaire × volume d'usage` (extrapolation à partir des KPIs 2.1 à 2.3).
- **Cible indicative** : **à définir avec le métier** — indicateur d'aide à la décision, non un engagement.
- **Source de la mesure** : extrapolation des KPIs de productivité + validation managériale. *Estimatif — à valider.*
- **Fréquence** : trimestrielle.

### 5.4 Satisfaction des équipes vis-à-vis de l'outil (valeur perçue)

- **Définition** : perception par les équipes commerciales de la valeur apportée par AC360 dans leur quotidien.
- **Formule / mesure** : score d'enquête qualitative dédiée (échelle 1–5) + verbatims.
- **Cible indicative** : **score moyen ≥ 4/5** (à confirmer).
- **Source de la mesure** : enquête terrain qualitative. *Déclaratif.*
- **Fréquence** : trimestrielle.

> ℹ️ AC360 **assiste** les équipes, il **ne décide pas** et **ne génère pas de promesse commerciale non sourcée**.
> Les KPIs de valeur métier ne doivent jamais être présentés comme une garantie de résultat commercial.

---

## Synthèse — Tableau de bord recommandé

| Catégorie | KPI phare | Cible indicative (à valider) | Source | Fréquence |
|---|---|---|---|---|
| Adoption | Utilisateurs actifs hebdo (WAU) | > 50 % équipe (3 mois) / > 70 % (6 mois) | Copilot Analytics | Hebdo / Mensuel |
| Productivité | Temps de préparation RDV | −50 % | Enquête terrain | Trimestriel |
| Qualité / Fiabilité | Taux de réponses sourcées | > 95 % | Revue qualité (échantillon) | Mensuel |
| Qualité / Fiabilité | Taux de refus corrects | 100 % (tests) / > 98 % (prod) | Tests garde-fous + échantillon | Release / Mensuel |
| Sécurité / Conformité | Incidents de sécurité confirmés | 0 | Rapport RSSI | Mensuel |
| Sécurité / Conformité | Accès non autorisés bloqués | 100 % bloqués | Logs Entra / API / Power Platform | Hebdo / Mensuel |
| Valeur métier | Complétude des dossiers | Tendance croissante | Topic Documents manquants + métier | Mensuel / Trimestriel |

> 📌 Un tableau de bord Power BI consolidant ces KPIs est recommandé (cf. `docs/observability/MONITORING_PLAN.md`,
> section « Dashboard Power BI »). Le dashboard métrique adoption est planifié (cf. `PRODUCT_POSITIONING.md`, roadmap).

---

## Gouvernance des KPIs

| Activité | Responsable | Fréquence | Livrable |
|---|---|---|---|
| Calibration / validation des cibles | PO + Responsable commercial + RSSI | Au lancement, puis annuelle | Cibles validées |
| Relevé Adoption / Productivité | PO + Responsable commercial | Mensuelle | Rapport Power BI |
| Relevé Qualité / Fiabilité | PO + Admin Power Platform | Mensuelle | Revue qualité (échantillon) |
| Relevé Sécurité / Conformité | RSSI + Admin Power Platform | Mensuelle | Rapport sécurité |
| Revue complète du cadre KPI | PO + RSSI + Direction | Trimestrielle | Rapport executive |

---

## Limites et précautions de lecture

1. **Cibles indicatives.** Toutes les valeurs chiffrées sont des points de départ **À VALIDER avec le métier** ; aucune n'est calibrée sur des données de production AC360.
2. **Mesures déclaratives.** Les KPIs de productivité et de valeur métier reposent en partie sur des enquêtes terrain (biais déclaratif) ; à corroborer par des données objectives quand c'est possible.
3. **Attribution prudente.** Les KPIs de valeur métier mesurent une **contribution**, pas une causalité directe (facteurs externes nombreux).
4. **Confidentialité by design.** Aucune mesure ne doit conduire à loguer du contenu client, des noms de clients, des tokens ou des secrets (cf. liste « Logs INTERDITS » du `MONITORING_PLAN.md`).
5. **Dépendances environnement réel.** Les KPIs marqués **« À VALIDER EN ENVIRONNEMENT RÉEL »** dépendent d'Azure / Microsoft Fabric / SharePoint / Entra et ne sont fiables qu'une fois ces briques activées et instrumentées.
6. **Fonction d'audit.** Les KPIs liés à l'audit OCR↔gestion ne deviennent mesurables qu'après déploiement effectif du topic `LancerAudit` en environnement réel.

---

## Références

- `docs/observability/MONITORING_PLAN.md` — métriques opérationnelles, seuils d'alerte, rétention des logs, dashboard Power BI.
- `docs/product/PRODUCT_POSITIONING.md` — KPIs de lancement et de maturité, roadmap.
- `docs/rag/RAG_POLICY.md` — garde-fous RAG et règle de citation obligatoire.
- `docs/security/SECURITY_GATE.md` — jeu de tests de garde-fous / sécurité.
- `docs/support/RUNBOOK_INCIDENTS.md` — gestion des incidents de sécurité.

---

*Cadre de KPIs v1.0 — Cibles indicatives, à valider avec le métier avant tout engagement de pilotage.*
