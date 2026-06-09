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

### ⚠️ SP d'automatisation — À SUPPRIMER
- `AC360-Automation` (`794146cb-...`) a été créé pour le **setup** (grant par site
  SharePoint, dépôt du document de test). Il détient **Graph Sites.FullControl.All**
  (tenant-wide) + un secret.
- Sa copie de secret en Key Vault a été supprimée. **Son credential Entra existe
  encore.**
- **Action requise** (privilège annuaire / PIM) :
  ```bash
  az ad app delete --id 794146cb-bc80-4612-a6d3-e90875531e95
  ```
  → Réactivez le rôle PIM (Global Admin / Application Administrator) puis exécutez,
  ou demandez-moi de le faire pendant la fenêtre d'activation. **Tant qu'il existe,
  c'est la plus grosse surface d'attaque résiduelle.**

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

## Plan d'action résiduel (par priorité)

| # | Action | Sévérité | Qui |
|---|---|---|---|
| 1 | Supprimer le SP `AC360-Automation` | 🟠 Haute | Vous (réactiver PIM) ou moi pendant la fenêtre |
| 2 | Restreindre l'ingress Function aux IP de la passerelle | 🟡 Moyenne | Moi (sur demande) |
| 3 | Private Endpoints (KV, Storage) en PROD | 🟡 Moyenne | À la promotion PROD |
| 4 | Diagnostic settings → Log Analytics + Defender for Cloud | 🟢 Basse | À la promotion PROD |
| 5 | Re-vérifier `httpsOnly` après chaque redéploiement | 🟢 Basse | CI / script |

## Conclusion

L'environnement staging est **solide en défense-en-profondeur** sur les axes qui
comptent le plus pour un système traitant des documents clients : **auth forte
(JWT Entra), secrets en Key Vault (0 clair), identités managées en moindre
privilège, données en lecture seule, TLS 1.2 partout, aucune donnée fabriquée**.
Le seul point à fermer côté identité est la **suppression du SP de setup**, qui
nécessite une réactivation PIM de votre part.
