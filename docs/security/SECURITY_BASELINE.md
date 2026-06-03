# Baseline Sécurité Enterprise — AC360

> **Classification** : Interne — Confidentiel  
> **Approbateur** : RSSI GEREP  
> **Version** : 1.0  
> **Date** : 2026-06-03  
> **Révision** : Annuelle ou après tout incident de sécurité

---

## 1. Modèle d'authentification

### 1.1 Entra ID (Azure Active Directory)

AC360 utilise **Microsoft Entra ID** comme fournisseur d'identité unique. Toute interaction avec l'assistant nécessite une authentification préalable.

| Mécanisme | Détail |
|---|---|
| **Protocole** | OAuth 2.0 / OpenID Connect |
| **Tokens** | JWT (JSON Web Token) signé RS256 |
| **Vérification** | JWKS (JSON Web Key Set) publié par Entra ID |
| **Mode** | SSO — Single Sign-On via compte Microsoft 365 GEREP |
| **Expiration** | Tokens access : 1h — Refresh : 24h (configurable) |
| **MFA** | Requis selon la politique Entra ID GEREP |

### 1.2 Vérification JWT

```
Client → [JWT Bearer Token]
              ↓
Copilot Studio / API Python
              ↓
Fetch JWKS depuis https://login.microsoftonline.com/{tenant_id}/.well-known/openid-configuration
              ↓
Vérifier : signature RS256 | audience (aud) | expiration (exp) | issuer (iss)
              ↓
Autorisation accordée ou refusée (401/403)
```

> **CRITIQUE** : Aucun token ne doit être logué en clair. Le JWT contient des claims d'identité.

### 1.3 Permissions Copilot Studio

```
authenticationMode: IntegratedWindowsAuthentication (ou EntraID SSO)
authenticationTrigger: AlwaysAuthenticate
accessControlPolicy: AllowAll (restreindre à groupe AD en PROD)
```

---

## 2. Principe du moindre privilège

| Composant | Permission accordée | Permission refusée |
|---|---|---|
| **Copilot Studio** | Lecture SharePoint (site dédié) | Écriture, suppression SharePoint |
| **Utilisateur** | Accès aux documents de son périmètre | Accès aux documents hors périmètre |
| **App Registration Entra ID** | Scopes Microsoft Graph limités | Admin Graph, Entra ID write |
| **API Python** | Lecture fichiers uploadés temporairement | Accès SharePoint direct en prod |
| **Service Account** | Aucun service account global autorisé | — |

> **Règle** : Chaque utilisateur accède uniquement aux ressources SharePoint que ses droits Active Directory lui accordent. AC360 ne surpasse pas les permissions SharePoint existantes.

---

## 3. Gestion des secrets

### 3.1 Principe

**Aucun secret ne doit apparaître en clair dans le code, les fichiers de configuration ou l'historique Git.**

| Secret | Stockage | Accès |
|---|---|---|
| `AZURE_OCR_KEY` | Azure Key Vault | Via identité managée ou reference Key Vault |
| `ENTRA_CLIENT_SECRET` | Azure Key Vault | Via identité managée |
| `TEAMS_WEBHOOK_URL` | Variable d'environnement Power Platform (chiffrée) | Admin Power Platform uniquement |
| Chaînes de connexion | Variables d'environnement Power Platform | Admin Power Platform uniquement |

### 3.2 Règles de développement

```
# ✅ AUTORISÉ — Variables d'environnement
AZURE_OCR_KEY=${KEY_VAULT_REF}

# ❌ INTERDIT — Secret en clair
AZURE_OCR_KEY=abc123xyz...

# ✅ AUTORISÉ — Référence Key Vault dans ARM/Bicep
"[reference(resourceId('Microsoft.KeyVault/vaults/secrets', vaultName, secretName)).value]"
```

### 3.3 .gitignore obligatoire

```gitignore
.env
*.env.*
local.settings.json
appsettings.Development.json
*.pfx
*.p12
*.key
```

---

## 4. DLP (Data Loss Prevention) Power Platform

### 4.1 Politique requise

Une politique DLP doit être configurée dans l'Admin Center Power Platform pour chaque environnement.

| Environnement | DLP configurée | Validée |
|---|---|---|
| DEV | 🟡 En cours | ❌ |
| TEST | 🔴 À configurer | ❌ |
| PROD | 🔴 À configurer | ❌ |

### 4.2 Classification des connecteurs

Voir [`docs/governance/DLP_POLICY_REQUIREMENTS.md`](../governance/DLP_POLICY_REQUIREMENTS.md) pour le détail complet.

---

## 5. Permissions SharePoint

### 5.1 Site dédié

```
URL : https://gerep75008.sharepoint.com/sites/dev-assistant-client-360
Bibliothèque : Dossiers_Clients_POC
```

### 5.2 Modèle de permission

| Niveau | Rôle SharePoint | Utilisateurs |
|---|---|---|
| **Lecture** | Member (lecture seule) | Commerciaux GEREP |
| **Gestion** | Site Collection Admin | Admin Power Platform, DSI |
| **AC360** | Utilise les droits de l'utilisateur connecté | — |

> AC360 n'utilise pas de compte de service. Il agit toujours **au nom de l'utilisateur connecté** (delegation OAuth).

---

## 6. Audit Trail

### 6.1 Données loguées

| Source | Données loguées | Données non loguées |
|---|---|---|
| Copilot Studio Analytics | Intentions détectées, topics utilisés, taux de satisfaction | Contenu des questions, données client |
| API Python (Application Insights) | Job IDs, durées, codes HTTP, erreurs techniques | Contenu des PDF/Excel, noms de clients |
| Power Platform Admin | Connexions établies, erreurs DLP | Contenu des conversations |

### 6.2 Rétention

- **Logs techniques** : 90 jours maximum
- **Logs DLP** : 180 jours (conformité)
- **Logs d'audit Power Platform** : selon politique GEREP (RGPD)

---

## 7. Confidentialité des données client

- **Aucune donnée client** ne doit transiter dans les logs applicatifs
- Les documents SharePoint ne sont **jamais stockés en cache** dans Copilot Studio
- Les réponses générées ne sont **pas persistées** au-delà de la session
- Les résultats d'audit (API Python) sont **temporaires** et supprimés après 24h

---

## 8. Chiffrement

| Canal | Protocole | Statut |
|---|---|---|
| HTTPS (Teams → Copilot Studio) | TLS 1.2 minimum | ✅ Géré par Microsoft |
| SharePoint API | TLS 1.2 minimum | ✅ Géré par Microsoft |
| API Python (Azure App Service) | TLS 1.2 minimum | 🟡 À configurer en PROD |
| Stockage Azure (blobs) | AES-256 au repos | ✅ Géré par Microsoft |

---

## 9. Séparation des environnements

| Environnement | SharePoint | Entra ID App | Power Platform Env | DLP |
|---|---|---|---|---|
| **DEV** | `dev-assistant-client-360` | `AC360-DEV` | Environment DEV | Basic |
| **TEST/UAT** | Site TEST dédié | `AC360-TEST` | Environment TEST | Full |
| **PROD** | Site PROD dédié | `AC360-PROD` | Environment PROD | Full + stricte |

> **Règle** : les credentials DEV ne doivent jamais être utilisés en PROD et vice-versa.

---

## 10. Tests de sécurité requis

| Test | Fréquence | Responsable |
|---|---|---|
| Scan gitleaks | À chaque commit (CI/CD) | Développeur |
| Red team prompts (20 scénarios) | Avant chaque release | QA + RSSI |
| Test injection de prompt | Avant chaque release | QA |
| Audit DLP | Trimestriel | Admin Power Platform |
| Rotation des secrets | Trimestriel | Admin + RSSI |
| Revue des permissions SharePoint | Semestriel | Owner SharePoint |

---

## 11. Contacts sécurité

| Rôle | Responsabilité |
|---|---|
| **RSSI** | Validation sécurité, gestion incidents, rotation secrets |
| **DPO** | Conformité RGPD, minimisation des données |
| **Admin Power Platform** | DLP, environnements, connexions |
| **Owner Entra ID** | App registrations, permissions, MFA |

---

*Baseline approuvée par : [RSSI — à signer] — Date : [À compléter]*
