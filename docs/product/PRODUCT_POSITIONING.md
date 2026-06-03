# Positionnement Produit — AC360

> **Version** : 1.0  
> **Date** : 2026-06-03  
> **Propriétaire** : Product Owner GEREP  
> **Audience** : Direction commerciale, Comité de pilotage, Partenaires

---

## Promesse produit

> **"L'assistant intelligent des équipes commerciales GEREP — des réponses précises, sourcées et sécurisées en 30 secondes."**

---

## Positionnement en une phrase

**AC360 est l'assistant commercial de GEREP** qui permet aux équipes de préparer leurs rendez-vous, synthétiser les dossiers clients et identifier les opportunités en interrogeant directement leurs documents SharePoint en langage naturel, sans quitter Microsoft Teams.

---

## Utilisateurs cibles

| Profil | Rôle | Besoin principal | Fréquence d'usage estimée |
|---|---|---|---|
| **Commercial junior** | Gestion d'un portefeuille client moyen | Comprendre rapidement un dossier avant un RDV | Quotidienne |
| **Responsable de compte** | Pilotage d'un portefeuille stratégique | Identifier les risques et opportunités | Plurihebdomadaire |
| **Directeur commercial** | Vue globale et pilotage | Comprendre les points d'attention prioritaires | Hebdomadaire |
| **Gestionnaire** | Support aux équipes commerciales | Vérifier les documents manquants | Hebdomadaire |

---

## Proposition de valeur par profil

### Pour le commercial terrain

> *"Avant, je passais 20 minutes à parcourir SharePoint avant chaque RDV. Maintenant, en 30 secondes, AC360 me donne l'essentiel."*

- ⏱️ **Gain de temps** : Synthèse client en 30 secondes vs 15-20 minutes manuellement
- 📅 **Préparation RDV** : Briefing structuré et actionnable généré automatiquement
- 📧 **Efficacité** : Brouillons d'e-mails commerciaux prêts à envoyer (à valider)
- 🎯 **Pertinence** : Informations sourcées — zéro approximation

### Pour le responsable de compte

- 📋 **Vue d'ensemble** : Points d'attention et alertes contractuelles identifiés automatiquement
- 📂 **Complétude dossier** : Documents manquants listés en un clic
- ⚖️ **Sécurité juridique** : Clauses contractuelles identifiées (à titre indicatif)

### Pour la direction commerciale

- 🔒 **Conformité** : Aucune donnée client ne quitte le périmètre Microsoft 365 GEREP
- 📊 **Adoption mesurable** : Analytics Copilot intégrés (NPS, taux d'usage)
- 🚀 **Time to value** : Déploiement dans Teams sans nouvelle installation

---

## Différenciation vs ChatGPT classique

| Critère | AC360 | ChatGPT / Copilot générique |
|---|---|---|
| **Sécurité** | ✅ Données dans le tenant Microsoft 365 GEREP | ❌ Données envoyées vers des serveurs externes |
| **Sourcing** | ✅ Réponses basées sur vos documents SharePoint | ❌ Réponses basées sur connaissances générales (peuvent être fausses) |
| **Confidentialité** | ✅ Chaque utilisateur voit uniquement son périmètre | ❌ Pas de contrôle d'accès par client |
| **Intégration M365** | ✅ Natif Teams, SSO Entra ID | ❌ Application externe |
| **Citations** | ✅ Chaque réponse cite le document source | ❌ Pas de source (hallucinations possibles) |
| **Gouvernance** | ✅ DLP, logs, audit trail | ❌ Non gouverné |
| **Personnalisation** | ✅ Adapté aux processus GEREP | ❌ Générique |

---

## Limites honnêtes (à communiquer proactivement)

> La transparence sur les limites est une force, pas une faiblesse.

| Limite | Ce qu'AC360 fait | Ce que vous devez faire |
|---|---|---|
| **Lecture seule** | Lit et synthétise les documents | Modifier les documents dans SharePoint directement |
| **SharePoint uniquement** | Accède à Dossiers_Clients_POC uniquement | Déposer vos documents dans SharePoint |
| **Pas d'avis juridique définitif** | Identifie les clauses (indicatif) | Consulter le service juridique pour les décisions |
| **Un client à la fois** | Réponse focalisée sur un seul client | Faire deux questions séparées |
| **Qualité = qualité des sources** | Répond en fonction des documents disponibles | S'assurer que les dossiers sont complets et à jour |
| **Pas de mémoire longue** | Ne mémorise pas vos échanges passés | Mentionner le contexte à chaque conversation |

---

## Critères de succès

### KPIs de lancement (3 mois)

| KPI | Cible | Méthode de mesure |
|---|---|---|
| **Adoption** | > 50% de l'équipe commerciale utilise AC360 au moins 1x/semaine | Copilot Analytics — utilisateurs uniques/semaine |
| **Satisfaction (NPS)** | Score NPS > 7/10 | Enquête mensuelle + CSAT Copilot |
| **Taux de fallback** | < 15% | Copilot Analytics — taux fallback |
| **Incidents sécurité** | 0 incident confirmé | RSSI — Rapport mensuel |
| **Temps de préparation RDV** | Réduction de 50% | Enquête terrain avant/après |

### KPIs de maturité (6 mois)

| KPI | Cible |
|---|---|
| Adoption > 70% de l'équipe | |
| NPS > 8/10 | |
| Suggestions de nouveaux topics générées par les utilisateurs | |
| Extension à d'autres équipes GEREP | |

---

## Risques métier identifiés

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| **Dépendance SharePoint** (qualité sources) | Élevée | Élevé | Formation sur les bonnes pratiques de dépôt documentaire |
| **Hallucination** (si mal configuré) | Faible (si `useModelKnowledge=false`) | Élevé | Monitoring continu + tests réguliers |
| **Résistance au changement** | Moyenne | Moyen | Formation, démonstration, quick wins |
| **Données clients manquantes** | Moyenne | Moyen | Audit qualité SharePoint avant déploiement |
| **Connecteur Preview retiré** | Faible | Moyen | Plan B documenté (connecteur alternatif) |
| **Incident sécurité (fuite données)** | Très faible | Critique | Security Gate + RSSI + DLP + tests red team |
| **Sur-confiance utilisateur** | Moyenne | Moyen | Formation : AC360 assiste, ne décide pas |

---

## Roadmap produit

| Phase | Fonctionnalité | Statut | Horizon |
|---|---|---|---|
| v1 | Topics principaux (résumé, préparation RDV, mail, points attention, documents manquants) | ✅ En production DEV | Maintenant |
| v1 | Déploiement TEST + PROD | 🔴 À planifier | Q3 2026 |
| v2 | Amélioration topics (arguments de vente, recherche juridique) | 🟡 En cours | Q3 2026 |
| v2 | Dashboard Power BI (métriques adoption) | 🔴 À planifier | Q4 2026 |
| v3 | Audit PDF/Excel (LancerAudit) — si validé RSSI | 🔴 Expérimental | 2027 |
| v3 | Extension à d'autres équipes GEREP | 🔴 À évaluer | 2027 |

---

*Document Product Owner — Pour usage interne et présentations direction*
