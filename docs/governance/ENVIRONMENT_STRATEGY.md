# Stratégie d'Environnements — AC360

> **Version** : 1.0  
> **Date** : 2026-06-03  
> **Propriétaire** : Admin Power Platform + DSI  
> **Révision** : Avant chaque phase de déploiement majeur

---

## Principe de séparation des environnements

**AC360 doit opérer dans trois environnements strictement séparés.** Aucune ressource, credential ou données ne doit être partagée entre environnements.

```
DEV ──→ (export solution) ──→ TEST/UAT ──→ (approbation) ──→ PROD
```

---

## Vue d'ensemble des environnements

| Critère | DEV | TEST / UAT | PROD |
|---|---|---|---|
| **Nom** | `dev-ac360` | `test-ac360` | `prod-ac360` |
| **Objectif** | Développement et expérimentation | Validation métier et QA | Production — Utilisateurs réels |
| **SharePoint** | `dev-assistant-client-360` | Site TEST dédié (données fictives) | Site PROD dédié (données réelles) |
| **App Registration Entra ID** | `AC360-DEV` | `AC360-TEST` | `AC360-PROD` |
| **Accès** | Développeurs + Product Owner | Testeurs + Équipe métier clé | Équipe commerciale GEREP |
| **DLP** | Basic | Full (même qu'en PROD) | Full + stricte |
| **Données** | Fictives / POC | Fictives ou anonymisées | Données client réelles |
| **Approbation déploiement** | Développeur | Admin Power Platform | RSSI + DSI |
| **URL Copilot** | Générée DEV | Générée TEST | Générée PROD |

---

## Détail des environnements

### 🔵 Environnement DEV

**Objectif** : Développement rapide, itérations fréquentes, expérimentation.

```
Power Platform Environment : dev-ac360
SharePoint : gerep75008.sharepoint.com/sites/dev-assistant-client-360
App Reg Entra ID : AC360-DEV (client ID à compléter)
```

**Règles** :
- Les commits sur `main` ou `dev` peuvent déclencher un déploiement DEV
- Les développeurs peuvent publier l'agent sans approbation
- Les données doivent être fictives — **jamais de données client réelles**
- DLP minimale — connecteurs Preview autorisés pour les tests
- Les topics expérimentaux (LancerAudit) peuvent être activés

**Accès autorisés** :
- Équipe développement (full access)
- Product Owner (read + test)
- Admin Power Platform (full access)

---

### 🟡 Environnement TEST / UAT

**Objectif** : Validation fonctionnelle et de sécurité avant PROD.

```
Power Platform Environment : test-ac360 (à créer)
SharePoint : Site TEST dédié (données fictives - à créer)
App Reg Entra ID : AC360-TEST (à créer)
```

**Règles** :
- Déploiement uniquement via export/import de solution
- Données fictives ou anonymisées obligatoirement
- DLP identique à la PROD (pour valider le comportement)
- Topics expérimentaux **désactivés** (même qu'en PROD)
- Tests red team et acceptance à exécuter ici
- Durée d'un cycle TEST : minimum 1 semaine avant passage en PROD

**Accès autorisés** :
- Équipe QA (test)
- Équipe métier sélectionnée (UAT)
- Admin Power Platform (déploiement)
- RSSI (validation sécurité)

**Gate requis avant passage en PROD** :
- [ ] Acceptance Test Matrix complétée (20 tests)
- [ ] Red Team 20 prompts exécutés
- [ ] Security Gate validé (8 gates)
- [ ] Sign-off Product Owner
- [ ] Approbation RSSI

---

### 🟢 Environnement PROD

**Objectif** : Service de production pour les équipes commerciales GEREP.

```
Power Platform Environment : prod-ac360 (à créer)
SharePoint : gerep75008.sharepoint.com/sites/[prod-client-360] (à créer)
App Reg Entra ID : AC360-PROD (à créer)
Groupe AD : AC360-Users (utilisateurs autorisés)
```

**Règles strictes** :
- Approbation **RSSI + DSI** obligatoire avant tout déploiement
- Données client réelles — protection maximale
- DLP stricte — aucun connecteur non approuvé
- Pas de topics expérimentaux
- Monitoring actif (Copilot Analytics + Application Insights)
- Rollback documenté et testé

**Accès autorisés** :
- Équipe commerciale GEREP (utilisation — via groupe AD)
- Admin Power Platform (déploiement uniquement — pas d'accès aux données)
- RSSI (audit)

---

## Séparation des ressources par environnement

| Ressource | DEV | TEST | PROD |
|---|---|---|---|
| **SharePoint Site** | dev-assistant-client-360 | test-assistant-client-360 | prod-assistant-client-360 |
| **App Registration** | AC360-DEV | AC360-TEST | AC360-PROD |
| **Client ID** | À compléter | À créer | À créer |
| **Key Vault** | kv-ac360-dev | kv-ac360-test | kv-ac360-prod |
| **Connection References** | DEV_SP, DEV_WorkIQ | TEST_SP, TEST_WorkIQ | PROD_SP, PROD_WorkIQ |
| **Variables d'env** | Préfixe DEV_ | Préfixe TEST_ | Préfixe PROD_ |

---

## Stratégie de release (ALM)

### Cycle de déploiement

```
1. Développement en DEV
   └── Commit + validation locale

2. Export solution DEV (Copilot Studio → Settings → Export)
   └── Format : .zip (managed ou unmanaged selon besoin)

3. Import en TEST
   └── Power Platform Admin → Import Solution
   └── Mapper les Connection References TEST
   └── Configurer les Variables d'environnement TEST

4. Tests en TEST (1 semaine minimum)
   └── Acceptance Tests (20 cas)
   └── Red Team (20 prompts)
   └── Security Gate (8 gates)

5. Sign-off (Product Owner + RSSI)

6. Import en PROD
   └── Même procédure qu'étape 3 (avec refs PROD)
   └── Double-vérification DLP

7. Validation post-déploiement
   └── Smoke tests (5 topics principaux)
   └── Vérification monitoring actif

8. Communication aux utilisateurs
```

---

## Gestion des branches Git

| Branche | Environnement | Qui peut committer |
|---|---|---|
| `dev` | DEV | Développeurs |
| `release/*` | TEST | Admin Power Platform |
| `main` | PROD | Admin + RSSI (après approbation) |

---

## Plan de création des environnements

| Action | Responsable | Délai estimé | Statut |
|---|---|---|---|
| Créer environment TEST dans Power Platform | Admin PP | 1 jour | 🔴 À faire |
| Créer site SharePoint TEST avec données fictives | Owner SharePoint | 2 jours | 🔴 À faire |
| Créer App Registration AC360-TEST dans Entra ID | Owner Entra ID | 0.5 jour | 🔴 À faire |
| Configurer DLP sur TEST (identique PROD) | Admin PP | 1 jour | 🔴 À faire |
| Créer environment PROD | Admin PP | 1 jour | 🔴 À faire (après validation TEST) |
| Créer groupe AD AC360-Users | Owner Entra ID | 0.5 jour | 🔴 À faire |

---

*Document maintenu par l'Admin Power Platform — Approbation DSI requise*
