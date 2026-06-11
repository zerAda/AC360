# AC360 — Audit de sécurité (environnement STAGING)

> Revue défense-en-profondeur de **toutes les ressources créées** pour AC360.
> Date : 2026-06-09. Vérifié par commande (`az` / Fabric / Graph). Tiers
> gratuits/dev, RG isolé `rg-ac360-staging`.

## Synthèse

| Domaine | Posture | Détail |
|---|---|---|
| Transport (TLS) | ✅ Fort | HTTPS-only + TLS 1.2 + FTPS off partout ; HSTS sur la passerelle |
| Secrets | ✅ Fort | Key Vault RBAC + **purge protection** + soft-delete ; références MI, **0 clé en clair** |
| Identité (runtime) | ✅ Moindre privilège | MI dédiées, rôles granulaires (SharePoint Sites.Selected, OneLake lecture seule) |
| Identité (setup) | ⚠️ À nettoyer | SP d'automatisation `AC360-Automation` (Sites.FullControl.All) à supprimer |
| Données | ✅ Fort | OneLake **lecture seule**, SharePoint **par site**, pas de blob public |
| Réseau | 🟡 Accepté (staging) | Endpoints publics ; Private Link recommandé en PROD |
| Journalisation | 🟢 Base | Application Insights actif |

## 1. Transport / chiffrement en transit

| Ressource | httpsOnly | TLS min | FTPS |
|---|---|---|---|
| `ac360-func-staging` (Function) | ✅ true | 1.2 | Disabled |
| `ac360-gateway-staging` (passerelle) | ✅ true | 1.2 | Disabled |
| `ac360stagingstore` (storage) | — | TLS1_2 | — |

- Passerelle : en-têtes `Strict-Transport-Security`, `X-Content-Type-Options:
  nosniff`, `X-Frame-Options: DENY`, `Cache-Control: no-store` (vérifiés).
- **Aucun chemin HTTP en clair** : tout `http://` est refusé.
- ⚠️ *Régression corrigée* : un redéploiement avait remis `httpsOnly=false` sur la
  Function → réactivé. **À re-vérifier après chaque redéploiement** (ou scripter).

## 2. Secrets (Azure Key Vault `ac360-kv-staging`)

- Mode **RBAC** (pas de policies héritées) ✅
- **Purge protection : ON** ✅ + soft-delete (rétention 90 j) ✅
- Secrets : `ocr-key`, `function-key` uniquement. `automation-sp-secret` **supprimé**.
- Consommation par **références Key Vault** (`@Microsoft.KeyVault(...)`) résolues
  via l'identité managée (rôle *Key Vault Secrets User*) → **aucune clé en clair**
  dans les app settings.
- Identifiants non secrets (`CLIENT_ID`, `TENANT_ID`, URLs) restent en app settings
  (corrects, ce ne sont pas des secrets).
- 🟡 Réseau Key Vault : `publicNetworkAccess=Enabled`. Acceptable en staging ;
  en PROD → Private Endpoint + `defaultAction=Deny` + exceptions services Azure.

## 3. Identités & accès

### Identités managées (runtime) — moindre privilège ✅
| Identité | Accès accordés |
|---|---|
| MI Function `710e845c-...` | SharePoint **Sites.Selected** + grant **par site** (DEV uniquement) ; Fabric **Viewer + OneLake DefaultReader (lecture seule)** ; KV **Secrets User** |
| MI Passerelle `be67f9db-...` | KV **Secrets User** |

→ Aucune permission large (`Files.Read.All`, `Contributor`, etc.) en runtime.

### App registration API
- `AC360-API-staging` (`5399f31e-...`) : **valide** des jetons (audience + scope
  `Audit.Trigger`). **Aucun secret** (une API n'en a pas besoin).

### ✅ SP d'automatisation — SUPPRIMÉ
- `AC360-Automation` (`794146cb-...`), créé pour le **setup** (grant SharePoint par
  site, dépôt du document de test), détenait **Graph Sites.FullControl.All** +
  un secret.
- **Application + service principal supprimés** d'Entra (vérifié : `az ad app list`
  → `[]`). Secret retiré de Key Vault. **Surface d'attaque éliminée.**

## 4. Données

- **Microsoft Fabric / OneLake** : la MI lit `tbl_super_product_client_api_gold`
  en **lecture seule** (rôle d'accès aux données OneLake `DefaultReader`), **sans
  accès en écriture** (rôle workspace **Viewer** uniquement). Les données client
  agrégées sont **pseudonymisées (hash)** côté GEREP — bonne pratique RGPD.
- **SharePoint** : accès **Sites.Selected** limité au seul site
  `DEV - Assistant Client 360` (pas d'accès tenant-wide aux fichiers).
- **Storage** : `allowBlobPublicAccess=false` ✅, TLS 1.2 ✅.
  - 🟡 `defaultAction=Allow` (réseau ouvert) + Shared Key activée (requis par
    Functions). PROD : envisager `Deny` + service endpoints + désactivation Shared
    Key avec accès MI.

## 5. Réseau (état staging)

| Ressource | Accès réseau | Reco PROD |
|---|---|---|
| Key Vault | Public | Private Endpoint + Deny |
| Storage | Public (Allow) | Service endpoints / Private Endpoint |
| OCR (F0) | Public | S0 + restrictions réseau |
| Function | Public (clé de fonction) | Restreindre l'ingress aux IP sortantes de la passerelle |
| Passerelle | Public (JWT Entra) | Front Door / WAF + IP allowlist si pertinent |

> Endpoints publics **acceptés en staging** ; tous protégés par auth (JWT Entra
> sur la passerelle, clé de fonction sur la Function, RBAC/MI sur les données).

## 6. Journalisation & supervision

- **Application Insights** actif (Function + passerelle).
- 🟡 Recommandé en PROD : diagnostic settings → Log Analytics pour Key Vault,
  Storage, Function ; activer **Microsoft Defender for Cloud** sur l'abonnement.

## 7. Code applicatif (SAST / dépendances / secrets)

Scan complet du code le 2026-06-09 :

| Scanner | Périmètre | Résultat |
|---|---|---|
| **bandit** (SAST Python, sévérité moyenne+) | `scripts/` + `azure_functions/` | ✅ **0 High, 0 Medium** après corrections |
| **pip-audit** (CVE dépendances) | `requirements.txt` | ✅ **Aucune vulnérabilité connue** |
| **scan_secrets** + recherche historique git | repo + `git log --all` | ✅ **Aucun secret en clair** (jamais commité) |
| Suite de tests sécurité (`tests/security|red_team|backend`) | — | ✅ 66 passés |

Corrections de code appliquées :
- `post_audit_workflow.py`, `ralphe_loop_tester.py` : ajout de `timeout` sur tous
  les appels réseau (anti-DoS / blocage de thread).
- `query_bot.py` : suppression de `shell=True` (arguments en liste, anti-injection
  CWE-78) + garde de schéma HTTPS sur `urlopen`.
- `read_docx.py` : passage à **`defusedxml`** (anti-XXE / Billion Laughs, CWE-20).
- `api_server.py` : bind `0.0.0.0` justifié (`# nosec B104`) — requis dans le
  conteneur App Service, l'ingress étant filtré par la plateforme + IP + JWT.
- Suppression du répertoire de travail `.build/` (contenait localement une clé de
  compte de stockage et des clés de webhook Durable — **jamais commité**, gitignoré).
- **CI** : ajout de `bandit` + `pip-audit` (bloquants) aux côtés de gitleaks.

> Note hors périmètre AC360 : l'abonnement Azure comporte plusieurs **Owners
> externes (#EXT#)** au niveau souscription (IAM GEREP préexistant, non créé par
> ce projet). Recommandation : revue d'accès périodique côté équipe sécurité GEREP.

## Corrections appliquées pendant l'audit ✅

| # | Action | État |
|---|---|---|
| 1 | Supprimer le SP `AC360-Automation` (Sites.FullControl.All) | ✅ Fait & vérifié |
| 2 | Réactiver `httpsOnly` sur la Function (régression) | ✅ Fait |
| 3 | Activer la **purge protection** Key Vault | ✅ Fait |
| 4 | Retirer `automation-sp-secret` du Key Vault | ✅ Fait |
| 5 | Restreindre l'ingress Function aux 22 IP de la passerelle | ✅ Fait & vérifié (IP externe → **403**) |
| 6 | Journalisation d'audit Key Vault (AuditEvent → storage) | ✅ Fait |
| 7 | MI Fabric en lecture seule OneLake (drop Contributor) | ✅ Fait |

## Plan d'action résiduel (PROD)

| # | Action | Sévérité | Quand |
|---|---|---|---|
| 1 | Private Endpoints (KV, Storage) | 🟡 Moyenne | Promotion PROD |
| 2 | Defender for Cloud + diagnostic settings → Log Analytics | 🟢 Basse | Promotion PROD |
| 3 | Re-vérifier `httpsOnly` après chaque redéploiement | 🟢 Basse | CI / script |
| 4 | Identité managée pour `AzureWebJobsStorage` (au lieu de la clé) | 🟢 Basse | Durcissement PROD |

## Conclusion

L'environnement staging est **solide en défense-en-profondeur** sur les axes qui
comptent le plus pour un système traitant des documents clients : **auth forte
(JWT Entra), secrets en Key Vault (0 clair), identités managées en moindre
privilège, données en lecture seule, TLS 1.2 partout, aucune donnée fabriquée**.
Le seul point à fermer côté identité est la **suppression du SP de setup**, qui
nécessite une réactivation PIM de votre part.

---

## Re-vérification live — 2026-06-11 (audit multi-équipes)

Posture re-confirmée par `az` (compte `a.zeriri@gerep.fr`, tenant GEREP) :

| Contrôle | État live | Verdict |
|---|---|---|
| Function/Gateway `httpsOnly` | true / true | ✅ |
| TLS min · FTPS | 1.2 / Disabled (les deux) | ✅ |
| Function ingress | 22 règles `allow-gw-*` + **Deny all** | ✅ verrouillé |
| MI Function / Gateway (RBAC Azure) | **Key Vault Secrets User** uniquement, scoped au vault | ✅ moindre privilège |
| Key Vault | purge-protection + soft-delete + RBAC = on ; `publicNetworkAccess=Enabled` | 🟡 réseau ouvert |
| Storage | `allowBlobPublicAccess=false`, TLS 1.2 | ✅ |
| Doc Intelligence | `publicNetworkAccess=Enabled`, **auth locale par clé active** (`disableLocalAuth=null`) | 🟡 |

### Résiduels infra — **À VALIDER EN ENVIRONNEMENT RÉEL** (fenêtre de maintenance requise)

Ces durcissements ne sont **pas** appliqués à chaud car ils risquent une coupure
du staging vivant (apps non intégrées à un VNet ; OCR auth par clé). À planifier :

1. **Key Vault privé** — nécessite l'intégration VNet des apps (App Service VNet
   integration + Private Endpoint KV). Sinon les références KV cassent.
   `az keyvault update -n ac360-kv-staging --public-network-access Disabled --default-action Deny` **après** VNet + PE.
2. **Doc Intelligence en Entra-only** — le code OCR supporte désormais la Managed
   Identity (repli clé) : accorder à la MI Function le rôle *Cognitive Services
   User* sur `ac360-docintel-staging`, retirer `AZURE_OCR_KEY` des app settings,
   puis `az cognitiveservices account update ... --custom-domain ... ` +
   `--api-properties` / portail → `disableLocalAuth=true`. Valider l'OCR end-to-end
   avant de retirer la clé.
3. **Storage `AzureWebJobsStorage` via MI** + `defaultAction=Deny` + service
   endpoints (Durable exige aujourd'hui la Shared Key).
4. **IaC** (Bicep/Terraform) pour figer cette posture et empêcher la dérive
   (ex. la régression `httpsOnly` déjà observée).
