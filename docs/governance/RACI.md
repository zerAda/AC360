# Matrice RACI — Projet AC360

> **Version** : 1.0  
> **Date** : 2026-06-03  
> **Propriétaire** : Product Owner GEREP  
> **Révision** : Semestrielle ou lors de changement d'équipe

---

## Légende RACI

| Lettre | Rôle | Signification |
|---|---|---|
| **R** | Responsible | Exécute la tâche |
| **A** | Accountable | Responsable final — décide et signe |
| **C** | Consulted | Consulté pour avis — impliqué avant la décision |
| **I** | Informed | Informé après la décision ou l'action |

---

## Rôles identifiés

| Rôle | Description | Personne / Équipe |
|---|---|---|
| **PO** | Product Owner GEREP | [À compléter] |
| **DEV** | Développeur / Équipe Digital GEREP | [À compléter] |
| **ADMIN_PP** | Admin Power Platform | [À compléter] |
| **RSSI** | Responsable Sécurité des Systèmes d'Information | [À compléter] |
| **DPO** | Délégué à la Protection des Données | [À compléter] |
| **OWN_SP** | Owner SharePoint (GEREP) | [À compléter] |
| **OWN_ENTRA** | Owner Entra ID / Azure | [À compléter] |
| **OWN_FABRIC** | Owner Microsoft Fabric (si activé) | [À compléter] |
| **METIER** | Équipe commerciale (utilisateurs finaux) | Commerciaux GEREP |
| **SUPPORT** | Support informatique N1/N2 | [À compléter] |
| **DSI** | Direction des Systèmes d'Information | [À compléter] |

---

## Matrice RACI

### Développement et livraison

| Activité | PO | DEV | ADMIN_PP | RSSI | DPO | OWN_SP | OWN_ENTRA | METIER | SUPPORT | DSI |
|---|---|---|---|---|---|---|---|---|---|---|
| Définition des exigences fonctionnelles | A | C | I | C | C | I | I | C | I | I |
| Développement des topics Copilot Studio | C | R | I | I | — | — | — | C | — | — |
| Développement de l'API Python (expérimental) | C | R | I | C | — | — | — | — | — | — |
| Validation des scripts PowerShell / Python | A | R | C | C | — | — | — | — | — | — |
| Revue de code (sécurité) | I | R | C | A | — | — | — | — | — | — |
| Validation des YAML Copilot | I | R | C | I | — | — | — | — | — | — |

---

### Déploiement

| Activité | PO | DEV | ADMIN_PP | RSSI | DPO | OWN_SP | OWN_ENTRA | METIER | SUPPORT | DSI |
|---|---|---|---|---|---|---|---|---|---|---|
| Export de la solution Copilot Studio | I | R | A | I | — | — | — | — | — | — |
| Import en environnement TEST | I | C | R | I | — | — | — | — | — | — |
| Import en environnement PROD | I | C | R | A | — | — | — | — | — | A |
| Configuration des Connection References | I | C | R | I | — | — | — | — | — | — |
| Configuration des Variables d'environnement | I | C | R | C | — | — | — | — | — | — |
| Validation post-déploiement (smoke tests) | A | R | C | C | — | — | — | I | — | — |
| Rollback en cas d'incident | I | C | R | A | — | — | — | I | I | A |

---

### Sécurité et conformité

| Activité | PO | DEV | ADMIN_PP | RSSI | DPO | OWN_SP | OWN_ENTRA | METIER | SUPPORT | DSI |
|---|---|---|---|---|---|---|---|---|---|---|
| Définition de la baseline sécurité | C | C | C | A | C | — | C | — | — | I |
| Validation du Security Gate | C | R | C | A | — | — | — | — | — | — |
| Configuration DLP Power Platform | I | — | R | A | C | — | — | — | — | — |
| Gestion des App Registrations Entra ID | I | C | C | C | — | — | R/A | — | — | — |
| Rotation des secrets | I | — | C | A | — | — | R | — | — | — |
| Tests red team (20 prompts) | I | R | I | A | — | — | — | — | — | — |
| Audit de sécurité annuel | I | I | C | R | C | C | C | — | — | A |
| Gestion des incidents de sécurité | I | C | C | R/A | C | — | C | — | I | I |
| Revue RGPD / conformité données | C | C | I | C | A | — | — | — | — | I |

---

### SharePoint et sources de données

| Activité | PO | DEV | ADMIN_PP | RSSI | DPO | OWN_SP | OWN_ENTRA | METIER | SUPPORT | DSI |
|---|---|---|---|---|---|---|---|---|---|---|
| Création et configuration des sites SharePoint | I | I | C | C | — | R/A | — | — | — | — |
| Gestion des permissions SharePoint | C | — | C | C | — | R/A | — | I | — | — |
| Dépôt des documents clients dans SharePoint | I | — | — | — | — | I | — | R | — | — |
| Validation de la qualité des sources RAG | A | — | — | — | — | I | — | R | — | — |
| Ajout d'une nouvelle knowledge source | A | C | R | C | — | C | — | C | — | — |

---

### Microsoft Entra ID

| Activité | PO | DEV | ADMIN_PP | RSSI | DPO | OWN_SP | OWN_ENTRA | METIER | SUPPORT | DSI |
|---|---|---|---|---|---|---|---|---|---|---|
| Création d'App Registrations | — | C | C | C | — | — | R/A | — | — | — |
| Gestion des groupes AD (AC360-Users) | I | — | C | C | — | — | R/A | — | — | — |
| Configuration des scopes OAuth | C | C | C | A | — | — | R | — | — | — |
| Révocation d'accès utilisateur | I | — | I | C | — | — | R/A | — | — | — |
| Configuration MFA | — | — | — | C | — | — | R/A | — | — | — |

---

### Microsoft Fabric (si activé)

| Activité | PO | DEV | ADMIN_PP | RSSI | DPO | OWN_SP | OWN_ENTRA | OWN_FABRIC | METIER | DSI |
|---|---|---|---|---|---|---|---|---|---|---|
| Décision d'activation Fabric | A | C | C | C | C | — | — | C | — | A |
| Configuration service principal Fabric | — | C | C | A | — | — | C | R | — | — |
| Gouvernance des données Fabric | C | — | C | C | A | — | — | R | — | — |

---

### Support et opérations

| Activité | PO | DEV | ADMIN_PP | RSSI | DPO | OWN_SP | OWN_ENTRA | METIER | SUPPORT | DSI |
|---|---|---|---|---|---|---|---|---|---|---|
| Support N1 (questions utilisateurs) | I | — | I | — | — | — | — | C | R | — |
| Support N2 (problèmes techniques) | I | C | R | I | — | — | — | I | A | — |
| Support N3 (incidents critiques) | I | R | C | A | — | — | — | I | C | I |
| Monitoring et alertes | I | C | R | I | — | — | — | — | C | — |
| Revue mensuelle des métriques | A | I | C | I | — | — | — | I | — | — |

---

### Validation métier

| Activité | PO | DEV | ADMIN_PP | RSSI | DPO | OWN_SP | OWN_ENTRA | METIER | SUPPORT | DSI |
|---|---|---|---|---|---|---|---|---|---|---|
| Tests d'acceptance (UAT) | A | C | I | I | — | — | — | R | — | — |
| Validation des scripts de démo | A | C | I | — | — | — | — | R | — | — |
| Formation des utilisateurs finaux | A | C | — | — | — | — | — | R | C | — |
| Go/No-Go avant PROD | A | C | C | C | C | — | — | I | — | A |

---

## Contacts et escalade

| Situation | Contact principal | Escalade |
|---|---|---|
| Question fonctionnelle AC360 | PO | METIER |
| Problème technique Copilot | ADMIN_PP | DEV |
| Incident sécurité | RSSI | DSI |
| Question RGPD | DPO | RSSI |
| Problème accès SharePoint | OWN_SP | ADMIN_PP |
| Problème authentification | OWN_ENTRA | RSSI |

---

*Matrice RACI validée par : [Product Owner — à signer] [DSI — à signer] — Date : [À compléter]*
