# AC360 — Assistant Commercial Copilot Studio

![Statut](https://img.shields.io/badge/Statut-Beta%20%2F%20Validation%20en%20cours-orange)
![Plateforme](https://img.shields.io/badge/Plateforme-Copilot%20Studio-blue)
![Sécurité](https://img.shields.io/badge/Auth-Entra%20ID%20SSO-green)
![Langue](https://img.shields.io/badge/Langue-Français-lightgrey)

> **AC360** est l'assistant commercial intelligent des équipes GEREP, construit sur Microsoft Copilot Studio. Il permet aux commerciaux d'interroger en langage naturel les documents clients stockés dans SharePoint, en toute sécurité et sans quitter l'environnement Microsoft 365.

---

## Architecture

```
Utilisateur (Teams / Copilot Studio Web)
        │
        ▼
┌─────────────────────────────┐
│     Copilot Studio (AC360)  │  ← Topics, RAG, Actions
└──────────────┬──────────────┘
               │  OAuth / Entra ID SSO
               ▼
┌─────────────────────────────┐
│   SharePoint Online (GEREP) │  ← Dossiers_Clients_POC
└──────────────┬──────────────┘
               │  Entra ID JWT RS256
               ▼
┌─────────────────────────────┐
│     Microsoft Entra ID      │  ← Authentification & Permissions
└─────────────────────────────┘
               │ (optionnel / expérimental)
               ▼
┌─────────────────────────────┐
│  API Python (Azure App Svc) │  ← Audit PDF/Excel
│  Azure OCR · Azure Fabric   │
└─────────────────────────────┘
```

---

## Cas d'usage

| Cas d'usage | Description |
|---|---|
| 📋 **Résumé client** | Obtenir une synthèse des documents d'un client en 30 secondes |
| 📅 **Préparation RDV** | Générer un briefing structuré avant un rendez-vous de renouvellement |
| 📂 **Documents manquants** | Identifier les documents absents dans un dossier client |
| ✉️ **Brouillon mail** | Rédiger un e-mail commercial sourcé depuis les données SharePoint |
| ⚠️ **Points d'attention** | Repérer les alertes contractuelles ou risques à traiter en priorité |
| 🔍 **Recherche documentaire** | Retrouver une clause ou un document spécifique |
| ⚖️ **Recherche juridique** | Identifier les éléments réglementaires dans les documents (lecture seule) |

---

## Prérequis

| Composant | Requis |
|---|---|
| Microsoft Power Platform | Environnement DEV/TEST/PROD séparé |
| Copilot Studio (licence) | Plan Copilot Studio ou Microsoft 365 Copilot |
| SharePoint Online | Site `dev-assistant-client-360` avec Dossiers_Clients_POC |
| Microsoft Entra ID | Tenant GEREP — App registration AC360 |
| DLP Power Platform | Politique configurée (voir `docs/governance/DLP_POLICY_REQUIREMENTS.md`) |
| Compte utilisateur | Licence Microsoft 365 + droits SharePoint lecture |

---

## Limites du produit

> ⚠️ **À lire avant tout déploiement ou démonstration**

- 🔒 **Lecture seule** : AC360 ne peut pas modifier, supprimer ou créer de document SharePoint
- 📁 **SharePoint uniquement** : aucun accès à Outlook, OneDrive personnel, Fabric (hors action validée), ni au Web
- ⚖️ **Pas d'avis juridique définitif** : les réponses juridiques sont indicatives et ne se substituent pas à un conseiller juridique
- 👤 **Un seul client par réponse** : aucune agrégation multi-clients
- 🤖 **Pas de connaissances générales** : `useModelKnowledge = false` — toutes les réponses sont sourcées depuis SharePoint
- 📊 **Audit PDF/Excel** : fonctionnalité expérimentale, non activée en production

---

## Sécurité

| Mécanisme | Détail |
|---|---|
| **Authentification** | Microsoft Entra ID — SSO avec JWT RS256 vérifié via JWKS |
| **Permissions** | Utilisateur connecté uniquement (pas de service account global) |
| **DLP** | Politique Power Platform empêchant les connecteurs non autorisés |
| **Secrets** | Stockés dans Azure Key Vault — jamais en clair dans le repo |
| **Chiffrement** | TLS 1.2+ en transit — données au repos chiffrées par Microsoft 365 |
| **Logs** | Aucune donnée client dans les logs — conversation metadata uniquement |

Voir [`docs/security/SECURITY_BASELINE.md`](docs/security/SECURITY_BASELINE.md) pour la baseline complète.

---

## Documentation

| Document | Description |
|---|---|
| [`docs/architecture/ARCHITECTURE_TARGET.md`](docs/architecture/ARCHITECTURE_TARGET.md) | Architecture cible et flux |
| [`docs/copilot/TOPIC_MAP.md`](docs/copilot/TOPIC_MAP.md) | Cartographie des topics Copilot Studio |
| [`docs/copilot/COPILOT_SETTINGS_DECISIONS.md`](docs/copilot/COPILOT_SETTINGS_DECISIONS.md) | Décisions de configuration |
| [`docs/security/SECURITY_BASELINE.md`](docs/security/SECURITY_BASELINE.md) | Baseline sécurité enterprise |
| [`docs/security/SECURITY_GATE.md`](docs/security/SECURITY_GATE.md) | Gate de validation sécurité |
| [`docs/security/SECRET_ROTATION.md`](docs/security/SECRET_ROTATION.md) | Procédure de rotation des secrets |
| [`docs/governance/ENVIRONMENT_STRATEGY.md`](docs/governance/ENVIRONMENT_STRATEGY.md) | Stratégie DEV/TEST/PROD |
| [`docs/governance/DLP_POLICY_REQUIREMENTS.md`](docs/governance/DLP_POLICY_REQUIREMENTS.md) | Exigences DLP |
| [`docs/governance/RACI.md`](docs/governance/RACI.md) | Matrice RACI |
| [`docs/alm/DEPLOYMENT_RUNBOOK.md`](docs/alm/DEPLOYMENT_RUNBOOK.md) | Runbook de déploiement |
| [`docs/alm/RELEASE_CHECKLIST.md`](docs/alm/RELEASE_CHECKLIST.md) | Checklist de release |
| [`docs/rag/RAG_POLICY.md`](docs/rag/RAG_POLICY.md) | Politique RAG enterprise |
| [`docs/observability/MONITORING_PLAN.md`](docs/observability/MONITORING_PLAN.md) | Plan de monitoring |
| [`docs/support/RUNBOOK_INCIDENTS.md`](docs/support/RUNBOOK_INCIDENTS.md) | Runbook incidents |
| [`docs/product/PRODUCT_POSITIONING.md`](docs/product/PRODUCT_POSITIONING.md) | Positionnement produit |
| [`docs/product/DEMO_SCRIPT.md`](docs/product/DEMO_SCRIPT.md) | Script de démo (7 scénarios) |
| [`tests/red_team/RED_TEAM_PROMPTS.md`](tests/red_team/RED_TEAM_PROMPTS.md) | Tests red team (20 prompts) |
| [`tests/acceptance/ACCEPTANCE_TEST_MATRIX.md`](tests/acceptance/ACCEPTANCE_TEST_MATRIX.md) | Matrice de tests d'acceptance |

---

## Structure du repo

```
AC360/
├── README.md
├── .gitleaks.toml
├── .gitignore
├── docs/
│   ├── 00_PROJECT_INVENTORY.md
│   ├── architecture/
│   ├── copilot/
│   ├── security/
│   ├── governance/
│   ├── alm/
│   ├── rag/
│   ├── observability/
│   ├── support/
│   └── product/
├── src/
│   └── copilot/AC360/          ← Sources YAML Copilot Studio
├── scripts/
│   ├── validate_copilot_yaml.py
│   ├── package_release.ps1
│   └── cleanup_local_artifacts.ps1
└── tests/
    ├── red_team/
    └── acceptance/
```

---

## Statut du projet

| Phase | Description | Statut |
|---|---|---|
| Phase 1 | Infrastructure & Copilot Studio | ✅ En production (DEV) |
| Phase 2 | RAG SharePoint + Topics principaux | ✅ Fonctionnel |
| Phase 3 | Sécurité & Gouvernance | 🟡 En cours de validation |
| Phase 4 | ALM DEV→TEST→PROD | 🔴 À planifier |
| Phase 5 | Audit PDF/Excel (API Python) | 🔴 Expérimental |

---

*Dernière mise à jour : 2026-06-03 — Équipe Digital GEREP*
