# AC360 — Évaluation de readiness production

> **Verdict global : CONDITIONALLY READY — pilote supervisé en staging.**
> AC360 est déployé et vérifié en **staging uniquement**. Aucun environnement de production n'existe à ce jour, et l'agent Copilot Studio n'est pas encore publié. Ce document n'autorise PAS une mise en production : il liste ce qui est prouvé, ce qui ne l'est pas, et les conditions à lever avant toute promotion.

- **Date d'évaluation :** 2026-06-10
- **Périmètre évalué :** environnement `rg-ac360-staging` (France Central)
- **Statut documentaire :** ce fichier ne se substitue pas à une décision formelle de Go/No-Go (voir section dédiée)

---

## 1. Taxonomie de statut

Chaque affirmation de ce document est qualifiée par l'un des statuts suivants. L'objectif est de ne jamais confondre « écrit dans le code » et « vérifié en condition réelle ».

| Statut | Signification |
|---|---|
| **PROUVÉ** | Vérifié dans l'environnement staging (test exécuté, ressource déployée, comportement observé). |
| **DOCUMENTÉ MAIS NON PROUVÉ** | Implémenté dans le code et/ou documenté, mais non démontré en exécution sur un environnement vivant. |
| **ABSENT** | Non implémenté / non déployé à ce jour. |
| **À VALIDER EN ENVIRONNEMENT RÉEL** | Dépend de données, de coûts, de licences ou de configuration tenant qui n'existent qu'en production ou sous trafic réel. |

---

## 2. Périmètre fonctionnel d'AC360

AC360 est un assistant **Microsoft Copilot Studio** destiné aux équipes commerciales. Fonctions couvertes :

- **Synthèse de dossiers client** à partir de SharePoint.
- **Préparation de rendez-vous** (consolidation des éléments d'un dossier).
- **Audit documentaire** par OCR (Azure AI Document Intelligence) et enrichissement Microsoft Fabric.
- **Brouillons de mail** générés pour les commerciaux.

Hors périmètre de cette évaluation : tout usage en dehors des équipes commerciales pilotes, toute écriture dans Fabric/OneLake (lecture seule), tout envoi automatique de mail (brouillons uniquement).

---

## 3. Architecture réelle (telle que déployée en staging)

```
Copilot Studio (NON publié)
        │  appel authentifié (JWT Entra ID)
        ▼
Passerelle FastAPI — Azure App Service Linux (plan F1)
   ac360-gateway-staging
        │  clé de fonction + allowlist IP
        ▼
Azure Durable Functions (Consumption)
   ac360-func-staging
        ├──► Azure AI Document Intelligence F0 (OCR)   ac360-docintel-staging
        ├──► Microsoft Fabric / OneLake  (LECTURE SEULE)
        ├──► SharePoint  (Graph, Sites.Selected)
        └──► Azure Key Vault  (secrets)   ac360-kv-staging
Identités managées entre les composants Azure.
Stockage : ac360stagingstore.
Application Entra : AC360-API-staging (scope Audit.Trigger).
```

---

## 4. État par composant

| Composant | Détail | Statut | Notes |
|---|---|---|---|
| Passerelle FastAPI | `ac360-gateway-staging`, App Service Linux **F1** | **PROUVÉ** (déployée, vérifiée en staging) | Plan F1 = niveau gratuit, **non dimensionné production** (pas de SLA, pas d'autoscale, quotas CPU). |
| Durable Functions | `ac360-func-staging`, plan **Consumption** | **PROUVÉ** (déployé) | Démarrage à froid possible ; comportement sous charge réelle → À VALIDER EN ENVIRONNEMENT RÉEL. |
| OCR Document Intelligence | `ac360-docintel-staging`, tier **F0** | **PROUVÉ** (déployé) | F0 = tier gratuit, **limité en débit/pages**. Qualité OCR sur dossiers réels → À VALIDER EN ENVIRONNEMENT RÉEL. |
| Fabric / OneLake | Accès **lecture seule** | **DOCUMENTÉ MAIS NON PROUVÉ** | Lecture seule par conception ; validation sur données réelles à faire. |
| SharePoint (Graph) | `Sites.Selected` | **DOCUMENTÉ MAIS NON PROUVÉ** | Permission de moindre privilège ; consentement par site à confirmer côté production. |
| Key Vault | `ac360-kv-staging`, **0 secret en clair** | **PROUVÉ** | Audit logging activé (cf. historique de hardening). Rotation → voir `docs/security/SECRET_ROTATION.md`. |
| Identités managées | Inter-composants Azure | **PROUVÉ** (staging) | À recréer/recâbler en production. |
| Application Entra | `AC360-API-staging`, scope `Audit.Trigger` | **PROUVÉ** (staging) | Une **app de production distincte** sera nécessaire. |
| Agent Copilot Studio | — | **ABSENT (non publié)** | Publication conditionnée à une **licence premium / pay-as-you-go**. |

---

## 5. État par capacité transverse (sécurité, contrôle, FinOps)

| Capacité | Implémentation | Statut | Notes |
|---|---|---|---|
| Auth passerelle | JWT Entra ID validé via **JWKS** | **PROUVÉ** (staging) | Vérif 401/403 à rejouer au go-live (cf. checklist). |
| Auth backend | **Clé de fonction + allowlist IP** | **PROUVÉ** (staging) | Allowlist à mettre à jour avec les IP de sortie de production. |
| Secrets | 100 % en **Key Vault**, 0 secret en clair | **PROUVÉ** | Rotation procédurée mais à exécuter en production. |
| Kill-switch / feature flags | `scripts/feature_flags.py` + `scripts/admin_controls.py` | **DOCUMENTÉ MAIS NON PROUVÉ** (sous trafic réel) | Variables : `AC360_GLOBAL_ENABLED`, `AC360_OCR_ENABLED`, `AC360_RAG_ENABLED`, `AC360_EMAIL_DRAFT_ENABLED`, `AC360_AUDIT_ENABLED`, `AC360_BLOCKED_USERS_HASHED`, `AC360_BLOCKED_TEAMS`, `AC360_ADMIN_ROLE`. Appliquées via App Service app settings (**admin uniquement**). Test de bascule en conditions réelles requis. |
| Usage tracking | `scripts/usage_tracker.py` (événements **hashés**, sink `AC360_USAGE_SINK`) | **DOCUMENTÉ MAIS NON PROUVÉ** | Sink de production à configurer ; volumétrie réelle non observée. |
| FinOps / coûts | `scripts/cost_tracker.py` (`AC360_RATE_CARD`, `AC360_BUDGET_EUR`) | **DOCUMENTÉ MAIS NON PROUVÉ** | **Grille tarifaire VIDE par défaut.** Coûts réels → À VALIDER EN ENVIRONNEMENT RÉEL. |
| Citations RAG | Restitution des sources | **À VALIDER EN ENVIRONNEMENT RÉEL** | Exactitude des citations sur dossiers réels non démontrée. |
| DLP (Power Platform) | — | **ABSENT** | Politique DLP non appliquée. Voir `docs/governance/DLP_POLICY_REQUIREMENTS.md`. À valider en environnement réel. |
| Private Endpoints | — | **ABSENT** | Trafic actuellement non privatisé (allowlist IP seulement). |
| Microsoft Defender (for Cloud / App Service) | — | **ABSENT** | Non activé sur le périmètre. |
| Tests | ~**211 pytest** OK, **flake8 0**, **mypy clean** | **PROUVÉ** (CI) | CI : `.github/workflows/ci.yml` (gitleaks, bandit, pytest, flake8, mypy). |

---

## 6. Tableau de readiness par domaine

| Domaine | Readiness | Statut dominant | Bloquant pour la prod ? |
|---|---|---|---|
| Fonctionnel (4 capacités) | 🟡 Partielle | DOCUMENTÉ / À VALIDER | Non (mais à valider sur données réelles) |
| Architecture & déploiement | 🟡 Staging OK, prod absente | PROUVÉ (staging) / ABSENT (prod) | **Oui** |
| Authentification & accès | 🟢 Solide en staging | PROUVÉ | Non (recâblage prod requis) |
| Secrets & Key Vault | 🟢 Solide | PROUVÉ | Non (rotation à exécuter) |
| Contrôle d'exécution (kill-switch) | 🟡 Implémenté, non éprouvé | DOCUMENTÉ MAIS NON PROUVÉ | Non (test réel requis) |
| Réseau (Private Endpoints) | 🔴 Absent | ABSENT | **Oui** (selon exigence RSSI) |
| DLP & conformité données | 🔴 Absent | ABSENT | **Oui** |
| Sécurité avancée (Defender) | 🔴 Absent | ABSENT | À arbitrer (RSSI) |
| FinOps & coûts | 🟡 Outillé, non chiffré | DOCUMENTÉ MAIS NON PROUVÉ | Non (chiffrage requis avant validation budget) |
| Observabilité / usage | 🟡 Outillé, non éprouvé | DOCUMENTÉ MAIS NON PROUVÉ | Non |
| Licence Copilot Studio | 🔴 Absente | ABSENT | **Oui** |
| Qualité de code / CI | 🟢 Solide | PROUVÉ | Non |

Légende : 🟢 prêt / 🟡 partiel ou à éprouver / 🔴 absent.

---

## 7. Prérequis production manquants

Aucun de ces points n'est satisfait à ce jour. Chacun est un prérequis à lever **avant** toute promotion.

1. **Environnement de production** — **ABSENT.** Aucun RG production n'existe. La promotion vers la prod est **facturable et n'a pas été réalisée** (App Service ≥ B1/P, Functions plan adapté, Document Intelligence tier payant ≥ S0 pour lever les quotas F0).
2. **Licence Copilot Studio** — **ABSENT.** Publication de l'agent impossible sans **licence premium / pay-as-you-go**. Tant que l'agent n'est pas publié, l'expérience utilisateur de bout en bout ne peut être prouvée.
3. **Politique DLP (Power Platform)** — **ABSENT.** À définir et appliquer sur l'environnement Power Platform cible (cf. `docs/governance/DLP_POLICY_REQUIREMENTS.md`). **À VALIDER EN ENVIRONNEMENT RÉEL.**
4. **Private Endpoints** — **ABSENT.** Privatisation du trafic vers Key Vault, Storage, Functions et Document Intelligence à instruire (aujourd'hui : allowlist IP uniquement).
5. **Microsoft Defender** — **ABSENT.** Activation Defender for Cloud / plan App Service à arbitrer avec le RSSI.
6. **Rotation des secrets exécutée en production** — procédure existante (`docs/security/SECRET_ROTATION.md`) **DOCUMENTÉE MAIS NON PROUVÉE** sur un tenant de production.
7. **Grille tarifaire & budget** — `AC360_RATE_CARD` **vide par défaut** ; `AC360_BUDGET_EUR` à fixer. Coûts réels **À VALIDER EN ENVIRONNEMENT RÉEL**.
8. **Application Entra de production** — l'app `AC360-API-staging` est dédiée au staging ; une app de production distincte (avec le scope `Audit.Trigger`) est à créer.

---

## 8. Critères de Go / No-Go

La promotion en production (pilote supervisé) ne peut être décidée que si **tous** les critères Go sont satisfaits. Le défaut d'un seul critère No-Go suffit à bloquer.

### Critères Go (tous requis)
- [ ] Environnement de production provisionné et vérifié (tiers payants adaptés) — *aujourd'hui : ABSENT*.
- [ ] Licence Copilot Studio acquise et agent publié sur un canal restreint — *aujourd'hui : ABSENT*.
- [ ] Politique DLP appliquée et validée sur l'environnement cible — *aujourd'hui : ABSENT*.
- [ ] Kill-switch testé en conditions réelles (bascule `AC360_GLOBAL_ENABLED` + un flag granulaire observée) — *aujourd'hui : DOCUMENTÉ MAIS NON PROUVÉ*.
- [ ] Auth vérifiée de bout en bout en production (401 sans token, 403 hors scope) — *à rejouer*.
- [ ] Secrets de production en Key Vault, rotation initiale exécutée, 0 secret en clair — *à exécuter*.
- [ ] Budget validé avec grille tarifaire renseignée et alerte budgétaire active — *aujourd'hui : grille VIDE*.
- [ ] Périmètre pilote nominatif (équipes/utilisateurs) défini et borné.

### Conditions No-Go (bloquantes)
- Agent Copilot Studio non publié (pas de licence).
- DLP absente sur l'environnement cible.
- Kill-switch non démontré.
- Coûts non chiffrés / budget non validé.
- Données client réelles exposées sans validation RSSI (Private Endpoints / Defender non arbitrés).

> **À ce jour (2026-06-10), au moins cinq conditions No-Go sont actives.** Le seul périmètre approuvable est la **poursuite du pilote supervisé en staging**.

---

## 9. Risques résiduels

| # | Risque | Probabilité | Impact | Statut / mitigation |
|---|---|---|---|---|
| R1 | Coûts réels supérieurs au prévu (OCR, Functions, Fabric) | Moyenne | Élevé | Grille tarifaire VIDE → **À VALIDER EN ENVIRONNEMENT RÉEL** ; activer `cost_tracker.py` + alerte budget. |
| R2 | Quotas F0/F1 atteints sous trafic réel (throttling, indispo) | Élevée | Moyen | Tiers staging non dimensionnés prod → exiger tiers payants avant Go. |
| R3 | Citations RAG inexactes / hallucinations sur dossiers réels | Moyenne | Élevé | **À VALIDER EN ENVIRONNEMENT RÉEL** ; revue qualité sur échantillon avant élargissement. |
| R4 | Fuite de données via canal non privatisé | Faible–Moyenne | Élevé | Private Endpoints **ABSENT** ; allowlist IP en place ; arbitrage RSSI requis. |
| R5 | Absence de DLP → exfiltration via connecteurs Power Platform | Moyenne | Élevé | DLP **ABSENT** ; prérequis bloquant. |
| R6 | Kill-switch inopérant le jour où il faut couper | Faible | Élevé | **DOCUMENTÉ MAIS NON PROUVÉ** ; test de bascule obligatoire au go-live. |
| R7 | Dérive de permissions SharePoint (`Sites.Selected`) | Faible | Moyen | Moindre privilège ; revue d'accès périodique. |
| R8 | Rotation de secrets non réalisée en prod | Faible | Élevé | Procédure existante non exécutée sur tenant prod. |
| R9 | Démarrage à froid Functions impactant l'UX | Moyenne | Faible–Moyen | Plan Consumption ; à mesurer, envisager plan premium si critique. |

---

## 10. RACI (gouvernance de la mise en production)

R = Réalise · A = Approuve (imputable) · C = Consulté · I = Informé.
Voir aussi `docs/governance/RACI.md` pour le RACI projet complet.

| Activité | Owner produit | RSSI | Power Platform Admin | DevSecOps |
|---|---|---|---|---|
| Décision Go/No-Go production | **A** | C | C | C |
| Provisionnement environnement prod (Azure) | I | C | I | **R** |
| Acquisition licence Copilot Studio | **R/A** | I | C | I |
| Publication de l'agent Copilot Studio | C | I | **R** | I |
| Définition & application DLP | C | **A** | **R** | C |
| Private Endpoints / Defender | I | **A** | I | **R** |
| Rotation des secrets (Key Vault) | I | C | I | **R/A** |
| Configuration kill-switch (app settings) | C | C | I | **R** |
| Test kill-switch + auth 401/403 | C | C | I | **R** |
| Grille tarifaire & budget (FinOps) | **A** | I | C | **R** |
| Définition périmètre pilote (utilisateurs) | **R/A** | C | C | I |
| Support & monitoring post-go-live | C | I | C | **R** |

---

## 11. Synthèse

AC360 dispose d'une **base d'ingénierie saine et vérifiée en staging** : architecture déployée, authentification éprouvée, secrets correctement gérés, qualité de code sous CI (≈211 tests, flake8/mypy propres). Les mécanismes de gouvernance (kill-switch, usage tracking, FinOps) sont **implémentés** mais **non éprouvés sous trafic réel**, et plusieurs prérequis structurants (**environnement de production, licence Copilot Studio, DLP, Private Endpoints, Defender, chiffrage des coûts**) sont **absents**.

En conséquence, le verdict honnête est **CONDITIONALLY READY — pilote supervisé en staging**. Aucune mention « production ready » ne peut être faite tant que les conditions No-Go de la section 8 ne sont pas levées. La prochaine étape recommandée est l'exécution de la **`GO_LIVE_CHECKLIST.md`** comme feuille de route conditionnelle, sans engagement de date tant que la licence et l'environnement de production ne sont pas obtenus.
