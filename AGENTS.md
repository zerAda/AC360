# AGENTS.md — AC360 : Assistant Client 360 (Microsoft Copilot Studio)

## Project Context

AC360 est un assistant conversationnel d'entreprise déployé sur **Microsoft Copilot Studio**.
Il permet aux commerciaux GEREP d'interroger les dossiers clients (documents SharePoint) via un chat Teams.

**Plateforme :** Microsoft Copilot Studio (Power Platform)  
**Langue :** Français (fr-FR)  
**Source de données :** SharePoint Online (documents PDF, DOCX, XLSX)  
**Authentification :** Microsoft Entra ID (Azure AD) — Integrated, Always  
**Modération :** High (contentModeration)  
**Base de connaissance :** Uniquement les documents SharePoint — pas de connaissance générale LLM (`useModelKnowledge: false`)

## Architecture

```
Utilisateur (Teams / Copilot Chat)
    ↓
Copilot Studio — Topics (AdaptiveDialog)
    ↓
SearchAndSummarizeContent ← SharePoint Online (Knowledge Source)
    ↓
[Optionnel] Power Automate → API FastAPI (scripts/api_server.py)
    ↓
Pipeline Python (OCR Azure → Audit Fabric → FIC → Post-Audit)
    ↓
Résultat → Notification Teams + Archivage RGPD
```

## Technology Stack

| Composant | Technologie |
|-----------|-------------|
| Chatbot | Microsoft Copilot Studio |
| Auth | Microsoft Entra ID (JWT RS256, JWKS) |
| Knowledge | SharePoint Online |
| API Backend | FastAPI (Python) + Uvicorn |
| OCR | Azure Document Intelligence |
| Audit Fabric | Microsoft Fabric / Artus |
| Documents FIC | python-docx |
| Pipeline | PowerShell 5.1+ |
| Base locale | SQLite (test_audits.db — non versionné) |

## Key Files

| Fichier | Rôle |
|---------|------|
| `src/copilot/AC360/agent.mcs.yml` | Définition de l'agent Copilot Studio |
| `src/copilot/AC360/settings.mcs.yml` | Paramètres de sécurité IA (modération, auth) |
| `src/copilot/AC360/topics/` | Tous les topics conversationnels |
| `src/copilot/AC360/knowledge/` | Sources de connaissance SharePoint |
| `src/copilot/AC360/actions/` | Actions personnalisées (Power Automate) |
| `scripts/api_server.py` | API FastAPI sécurisée (JWKS RS256) |
| `scripts/run_audit_pipeline.ps1` | Pipeline orchestrateur PowerShell |
| `scripts/audit_fabric_comparison.py` | Audit & croisement Fabric |
| `scripts/generate_fic_draft.py` | Génération de la FIC Word |
| `scripts/post_audit_workflow.py` | Alertes Teams + archivage RGPD |
| `scripts/cleanup_local_artifacts.ps1` | Nettoyage des artefacts locaux |
| `.gitignore` | Exclusions git (DB, logs, jobs, pyc) |
| `.env.example` | Template variables d'environnement |

## Topics Principaux

| Topic | Rôle |
|-------|------|
| `ConversationStart` | Message d'accueil |
| `Rsumdossierclient` | Synthèse commerciale d'un dossier client |
| `Recherchedocumentclient` | Recherche d'un document client dans SharePoint |
| `Argumentsdevente` | Arguments commerciaux pour un client |
| `Brouillonmailcommercial` | Rédaction d'un e-mail commercial |
| `Documentsmanquants` | Identification des documents manquants |
| `PreparationRDVRenouvellement` | Préparation de rendez-vous renouvellement |
| `LancerAudit` | Info déploiement en cours (audit pipeline) |
| `Recherchejuridiquedocumentaire` | Recherche dans documents juridiques SharePoint |
| `Search` | Fallback générique (OnUnknownIntent) |
| `Escalate` | Escalade vers un conseiller humain |

## Topics Désactivés (Doublons)

| Topic | Raison |
|-------|--------|
| `Clarificationclient__K_.mcs.yml` | Doublon — `displayName` vide, conflit routing |
| `Rsumdossierclient_iGk.mcs.yml` | Doublon — `displayName` vide, conflit routing |
| `Refusmodificationdocument_kg1.mcs.yml` | Doublon — `displayName` vide, conflit routing |

## Sécurité

- **JWT** : Vérification RS256 via JWKS (`/discovery/v2.0/keys`) — `verify_signature=False` supprimé
- **Path Traversal** : Supprimé — l'API accepte un `document_id` (UUID v4), jamais un chemin Windows
- **Bypass mock://** : Supprimé
- **Invoke-Expression** : Supprimé du pipeline PowerShell — remplacé par `& python @args`
- **TENANT_ID** : Fail-fast si manquant au démarrage de l'API
- **useModelKnowledge** : `false` — empêche les hallucinations hors-documents
- **contentModeration** : `High`

## Variables d'Environnement Requises

```bash
TENANT_ID=<azure-tenant-id>          # Obligatoire (fail-fast si absent)
CLIENT_ID=<app-registration-client-id>  # Obligatoire
JOBS_BASE_DIR=C:\AC360_Jobs           # Optionnel (défaut: ./jobs)
```

## Commands

```powershell
# Démarrer l'API FastAPI
cd scripts
uvicorn api_server:app --host 0.0.0.0 --port 8000

# Nettoyer les artefacts locaux
.\scripts\cleanup_local_artifacts.ps1

# Synchroniser Copilot Studio
.\scripts\sync_copilot.ps1
```

## Notes de Gouvernance

- L'agent est **lecture seule** sur SharePoint
- Il ne peut pas modifier, créer, supprimer ou déplacer des documents
- Les données clients ne doivent jamais quitter le périmètre Microsoft 365
- Les logs de pipeline contiennent l'UPN de l'utilisateur (conformité RGPD)
- Les fichiers `*.db`, `*.log`, `jobs/` sont exclus du git (`.gitignore`)

---

*AGENTS.md updated: 2026-06-03 — Version AC360 Copilot Studio*
