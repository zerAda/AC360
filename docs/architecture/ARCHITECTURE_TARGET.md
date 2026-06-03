# Architecture Cible — AC360

> **Version** : 1.0  
> **Date** : 2026-06-03  
> **Propriétaire** : DSI + Architecte Digital GEREP  
> **Classification** : Interne

---

## 1. Vue d'ensemble

AC360 est un assistant commercial construit sur **Microsoft Copilot Studio**, intégré à l'écosystème **Microsoft 365** de GEREP. Il accède aux documents clients stockés dans **SharePoint Online** via des connexions OAuth authentifiées par **Microsoft Entra ID**.

---

## 2. Architecture logique

```mermaid
graph TB
    subgraph "Utilisateurs GEREP"
        U1[Commercial]
        U2[Responsable de compte]
        U3[Direction commerciale]
    end

    subgraph "Canaux d'accès"
        Teams[Microsoft Teams]
        Web[Copilot Studio Webchat]
    end

    subgraph "Microsoft Power Platform"
        CS[Copilot Studio<br/>Agent AC360]
        DLP[DLP Policy<br/>AC360-DLP-Policy]
    end

    subgraph "Connecteurs"
        WS[WorkIQ SharePoint MCP<br/>Preview]
        WU[WorkIQ User MCP<br/>Preview]
        SPK[SharePoint Search<br/>Knowledge Source]
    end

    subgraph "Microsoft 365"
        SP[SharePoint Online<br/>dev-assistant-client-360<br/>Dossiers_Clients_POC]
        EntraID[Microsoft Entra ID<br/>App Registration AC360]
    end

    subgraph "Azure - Expérimental"
        API[API Python<br/>Azure App Service]
        OCR[Azure Cognitive Services<br/>OCR]
        AKV[Azure Key Vault<br/>Secrets]
    end

    subgraph "Observabilité"
        CA[Copilot Analytics]
        AI[Application Insights]
        PBI[Power BI Dashboard]
    end

    U1 --> Teams
    U2 --> Teams
    U3 --> Web
    Teams --> CS
    Web --> CS
    CS --> DLP
    DLP --> WS
    DLP --> WU
    DLP --> SPK
    WS --> SP
    WU --> EntraID
    SPK --> SP
    SP --> EntraID
    CS -.->|Expérimental| API
    API -.-> OCR
    API -.-> AKV
    CS --> CA
    API -.-> AI
    CA --> PBI

    style CS fill:#0078d4,color:#fff
    style SP fill:#038387,color:#fff
    style EntraID fill:#5c2d91,color:#fff
    style API fill:#ff8c00,color:#fff
    style DLP fill:#d13438,color:#fff
```

---

## 3. Flux utilisateur (conversation standard)

```mermaid
sequenceDiagram
    participant U as Utilisateur (Teams)
    participant T as Microsoft Teams
    participant CS as Copilot Studio AC360
    participant EID as Microsoft Entra ID
    participant SP as SharePoint Online

    U->>T: Ouvre l'app AC360 dans Teams
    T->>CS: Démarre une conversation
    CS->>EID: Déclenche authentification (AlwaysAuthenticate)
    EID->>U: Demande de consentement OAuth (si première fois)
    U->>EID: Accepte
    EID->>CS: JWT Access Token (RS256)
    CS->>CS: Vérifie JWT via JWKS
    U->>CS: "Résume le dossier du client Alpha"
    CS->>CS: Topic Rsumdossierclient déclenché
    CS->>SP: Requête SharePoint (avec token utilisateur)
    SP->>SP: Vérifie permissions utilisateur
    SP->>CS: Documents trouvés (contenu)
    CS->>CS: Génération réponse (RAG)
    CS->>U: Réponse sourcée avec citations
```

---

## 4. Flux d'authentification

```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant CS as Copilot Studio
    participant EID as Entra ID (JWKS)
    participant SP as SharePoint

    Note over CS,EID: Authentification OAuth 2.0 / OIDC

    U->>CS: Démarre session
    CS->>EID: Redirect vers login.microsoftonline.com
    EID->>U: Page de connexion GEREP (SSO)
    U->>EID: Credentials (MFA si requis)
    EID->>CS: Authorization Code
    CS->>EID: Échange code → Access Token + ID Token
    EID->>CS: JWT (RS256, exp=1h)
    CS->>EID: Fetch JWKS (/.well-known/openid-configuration)
    CS->>CS: Vérifie signature JWT (RS256)
    CS->>CS: Vérifie aud, iss, exp

    Note over CS,SP: Appels SharePoint avec token délégué

    CS->>SP: GET /sites/.../Dossiers_Clients_POC (Bearer JWT)
    SP->>EID: Valide le token
    SP->>CS: Documents selon permissions utilisateur
```

---

## 5. Flux RAG (Retrieval-Augmented Generation)

```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant CS as Copilot Studio
    participant SP as SharePoint Search
    participant LLM as Modèle de langage

    U->>CS: "Quels sont les points d'attention pour Alpha ?"
    CS->>CS: Détection du topic : Pointsattentionclient
    CS->>SP: Recherche sémantique "points attention Alpha"
    SP->>SP: Index SharePoint Dossiers_Clients_POC
    SP->>CS: Top 5 documents pertinents (extraits)
    CS->>LLM: Prompt = [Instructions système] + [Documents SharePoint] + [Question]
    Note over LLM: useModelKnowledge=false<br/>Réponse basée uniquement sur les documents
    LLM->>CS: Réponse structurée avec citations
    CS->>U: Réponse + sources (📄 Nom_Fichier — Section X)
```

---

## 6. Flux API Audit (optionnel — expérimental)

```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant CS as Copilot Studio
    participant API as API Python (Azure)
    participant OCR as Azure OCR

    Note over CS,API: LancerAudit topic (NON ACTIVÉ EN PROD v1)

    U->>CS: Upload PDF + Excel
    CS->>CS: Topic LancerAudit déclenché
    CS->>API: POST /audit avec fichiers (JWT Bearer)
    API->>API: Valider JWT (JWKS Entra ID)
    API->>API: Parser Excel (pandas)
    API->>OCR: Extraire texte PDF
    OCR->>API: Texte structuré (IBAN, Nom, Montant)
    API->>API: Fuzzy matching (difflib, seuil 75%)
    API->>API: Calculer écarts (Excel - PDF)
    API->>CS: job_id + rapport d'audit
    CS->>U: Résultats avec écarts identifiés
    Note over API: Fichiers supprimés après 24h
```

---

## 7. Composants et responsabilités

### Composants actifs (v1)

| Composant | Rôle | Owner | Environnement |
|---|---|---|---|
| **Copilot Studio Agent AC360** | Agent conversationnel, orchestrateur | Admin Power Platform | Power Platform |
| **SharePoint Online** | Source de vérité documentaire | Owner SharePoint | Microsoft 365 |
| **Microsoft Entra ID** | Authentification et autorisation | Owner Entra ID | Azure AD / Entra |
| **Microsoft Teams** | Canal de déploiement principal | Admin Teams | Microsoft 365 |
| **WorkIQ SharePoint MCP** | Connecteur SharePoint (Preview) | Admin Power Platform | Power Platform |
| **SharePoint Search** | Knowledge source RAG | Admin Power Platform | Power Platform |
| **DLP Policy** | Gouvernance des données | Admin Power Platform | Power Platform |

### Composants futurs / expérimentaux (v2+)

| Composant | Rôle | Prérequis activation |
|---|---|---|
| **API Python (Azure App Service)** | Moteur d'audit PDF/Excel | Approbation RSSI + tests complets |
| **Azure Cognitive Services (OCR)** | Extraction texte PDF | Avec API Python |
| **Azure Key Vault** | Gestion des secrets | Recommandé en PROD dès v1 |
| **Application Insights** | Monitoring API | Avec API Python |
| **Microsoft Fabric** | Analytics avancés | Approbation RSSI + service principal |
| **Power BI** | Dashboard de pilotage | Copilot Analytics suffisant en v1 |

---

## 8. Décisions d'architecture clés

| Décision | Choix | Justification | Alternative écartée |
|---|---|---|---|
| Canal principal | Microsoft Teams | Intégration native M365, SSO transparent | Interface web standalone |
| Authentification | Entra ID SSO | Standard GEREP, MFA, délégation OAuth | Service account global |
| Source RAG | SharePoint uniquement | Données gouvernées GEREP, contrôle des accès | Web search, Outlook |
| Connecteur SharePoint | WorkIQ MCP (Preview) | Riche fonctionnellement | HTTP custom (risque DLP) |
| Secrets | Azure Key Vault (cible) | Aucun secret en clair | Variables d'env uniquement |
| Modèle de langage | GPT-4 via Copilot Studio | Gestion par Microsoft, RGPD | GPT Azure direct |

---

*Document d'architecture v1.0 — Valider avec DSI avant déploiement PROD*
