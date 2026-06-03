# Politique DLP Power Platform — AC360

> **Version** : 1.0  
> **Date** : 2026-06-03  
> **Propriétaire** : Admin Power Platform  
> **Approbateur** : RSSI + DSI  
> **Révision** : Trimestrielle ou après ajout de connecteur

---

## Contexte

La politique DLP (Data Loss Prevention) Power Platform contrôle quels connecteurs peuvent être utilisés ensemble dans un flux ou un agent Copilot Studio. Elle constitue le dernier rempart technique contre l'exfiltration non autorisée de données.

---

## Architecture DLP

```
Power Platform Admin Center
    └── Politique DLP : AC360-Policy
            ├── Business (données professionnelles autorisées)
            ├── Non-Business (données séparées des données business)
            └── Blocked (connecteurs interdits)
```

**Règle fondamentale** : Les connecteurs de la catégorie **Business** et **Non-Business** ne peuvent pas être utilisés ensemble dans le même flux. Les connecteurs **Blocked** ne peuvent pas être utilisés du tout.

---

## Classification des connecteurs

### ✅ Connecteurs BUSINESS — Autorisés

| Connecteur | Raison | Périmètre |
|---|---|---|
| **Microsoft SharePoint** | Source de données principale | Sites GEREP uniquement |
| **Microsoft Teams** | Canal de déploiement | Tenant GEREP |
| **Copilot Studio** | Agent principal | — |
| **Microsoft Dataverse** | Données Power Platform | Environnement GEREP |
| **Office 365 Users** | Informations annuaire | Tenant GEREP |
| **WorkIQ SharePoint MCP** | Accès SharePoint (Preview — sous surveillance) | Sites GEREP uniquement |
| **WorkIQ User MCP** | Informations utilisateur (Preview — sous surveillance) | Tenant GEREP |

### ⚠️ Connecteurs PREVIEW — Surveillance renforcée

| Connecteur | Statut actuel | Conditions d'approbation |
|---|---|---|
| **WorkIQ SharePoint MCP** | AUTORISÉ en DEV — Sous examen pour PROD | Approbation RSSI + documentation des scopes OAuth |
| **WorkIQ User MCP** | AUTORISÉ en DEV — Sous examen pour PROD | Évaluer si réellement nécessaire |

**Procédure d'approbation pour connecteurs Preview** :
1. Documenter le besoin métier
2. Analyser les scopes OAuth demandés
3. Tester en DEV
4. Présenter au RSSI pour approbation
5. Documenter la décision dans ACTIONS_SECURITY_REVIEW.md

### ❌ Connecteurs NON-BUSINESS / BLOQUÉS

| Connecteur | Statut | Raison |
|---|---|---|
| **HTTP** (générique) | ❌ BLOQUÉ (sauf exception approuvée) | Surface d'attaque externe non contrôlée — exfiltration possible |
| **OneDrive (personnel)** | ❌ BLOQUÉ | Données hors périmètre GEREP |
| **Gmail** | ❌ BLOQUÉ | Données hors périmètre Microsoft 365 |
| **Google Drive** | ❌ BLOQUÉ | Données hors périmètre GEREP |
| **Dropbox** | ❌ BLOQUÉ | Stockage externe non gouverné |
| **Slack** | ❌ BLOQUÉ | Communication externe non gouvernée |
| **Twitter / X** | ❌ BLOQUÉ | Données publiques — risque réputation |
| **RSS** | ❌ BLOQUÉ | Source de contenu externe non vérifiée |
| **Connectors tiers non répertoriés** | ❌ BLOQUÉ par défaut | Non gouvernés — approbation requise |

### ⚠️ Connecteur HTTP — Cas particulier

Le connecteur HTTP peut être nécessaire pour l'API Python (LancerAudit). Dans ce cas :

**Conditions d'exception** :
- URL de destination fixe et documentée (Azure App Service GEREP uniquement)
- Authentification JWT obligatoire
- Approbation RSSI explicite et documentée
- Restriction par Scope DLP (Environment-level restriction)

---

## Microsoft Fabric — Cas particulier

| Accès Fabric | Conditions |
|---|---|
| Via identité managée / service principal | ✅ AUTORISÉ si approbation RSSI |
| Via compte utilisateur direct | ⚠️ À évaluer |
| Via connecteur Fabric Power Platform | ❌ INTERDIT sans approbation explicite |

**Note** : Microsoft Fabric n'est pas dans la portée actuelle d'AC360. Toute intégration future nécessite une révision DLP dédiée.

---

## Audit logs obligatoires

| Action | Log requis | Rétention |
|---|---|---|
| Connexion d'un utilisateur à AC360 | ✅ Copilot Analytics + Entra ID Sign-in logs | 90 jours |
| Appel d'un connecteur | ✅ Power Platform Admin logs | 90 jours |
| Violation DLP | ✅ DLP incident logs | 180 jours |
| Erreur de connecteur | ✅ Application Insights (si configuré) | 90 jours |
| Modification de politique DLP | ✅ Power Platform Admin audit | 365 jours |

---

## Configuration recommandée — Admin Center

```
Power Platform Admin Center
→ Policies → Data policies → New policy

Nom : AC360-DLP-Policy
Scope : Environnement(s) AC360 (DEV / TEST / PROD séparés)

Business :
  - SharePoint
  - Teams
  - Copilot Studio
  - Dataverse
  - Office 365 Users
  [+ WorkIQ connectors après approbation RSSI]

Non-Business :
  [Vide — aucun connecteur non-business autorisé]

Blocked :
  - HTTP (sans exception approuvée)
  - OneDrive Personal
  - Gmail
  - Google Drive
  - Dropbox
  - Tous connecteurs non listés en Business
```

---

## Matrice de conformité par environnement

| Critère | DEV | TEST | PROD |
|---|---|---|---|
| Politique DLP configurée | 🟡 Basique | 🔴 À configurer | 🔴 À configurer |
| Connecteurs Preview approuvés | ⚠️ Sous surveillance | ⚠️ Sous surveillance | 🔴 Approbation RSSI requise |
| HTTP bloqué | 🟡 Partiel | 🔴 À configurer | 🔴 À configurer |
| OneDrive personnel bloqué | 🟡 Partiel | 🔴 À configurer | 🔴 À configurer |
| Audit logs actifs | 🟡 Partiel | 🔴 À configurer | 🔴 À configurer |

---

## Actions prioritaires DLP

| Priorité | Action | Responsable | Délai |
|---|---|---|---|
| 🔴 CRITIQUE | Configurer politique DLP en TEST | Admin Power Platform | 1 semaine |
| 🔴 CRITIQUE | Configurer politique DLP en PROD | Admin Power Platform | Avant passage PROD |
| 🟡 ÉLEVÉ | Obtenir approbation RSSI pour WorkIQ connectors | RSSI | 2 semaines |
| 🟡 ÉLEVÉ | Documenter exception HTTP si nécessaire pour API | RSSI + Admin | 2 semaines |
| 🟢 MOYEN | Activer audit logs DLP en DEV | Admin Power Platform | 1 semaine |

---

*Document maintenu par l'Admin Power Platform — Approbation RSSI requise*
