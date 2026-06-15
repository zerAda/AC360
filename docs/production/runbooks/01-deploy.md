# AC360 — Runbook de déploiement production (OPS-01)

> Objectif : déployer AC360 en production via le pipeline `cd-prod.yml`, en
> **OIDC sans secret stocké**, après une approbation humaine, et **vérifier** que
> l'identité managée et les références Key Vault résolvent — par un seul opérateur.

## Principe

Le déploiement production est piloté par GitHub Actions (`.github/workflows/cd-prod.yml`) :
`build → what-if (gate de diff) → deploy` (Environment GitHub `production`, approbation
manuelle d'un reviewer requis). L'authentification Azure est **OIDC fédéré** — aucun
mot de passe de service principal n'est stocké (cf. décision STATE : T-03-13).

Les **prérequis opérateur** ci-dessous sont volontairement **hors du YAML** (cf. en-tête
de `cd-prod.yml`) : ils touchent à l'Entra ID, à l'Environment GitHub et aux rôles RBAC,
et ne doivent être posés **qu'une fois** par l'opérateur.

| Élément | Où | Rôle |
|---|---|---|
| Environment GitHub `production` + reviewer requis | GitHub repo settings | Gate d'approbation manuelle du job `deploy` |
| Secrets `AZURE_CLIENT_ID` / `AZURE_TENANT_ID` / `AZURE_SUBSCRIPTION_ID` | GitHub repo/Environment secrets | Cibles OIDC (pas de mot de passe SP) |
| Credential fédéré `:environment:production` | Entra app de déploiement | OIDC du job `deploy` |
| Credential fédéré `:ref:refs/tags/prod-*` | Entra app de déploiement | OIDC du job `whatif` (hors Environment) |
| Rôle Contributor sur `rg-ac360-prod` | Azure RBAC | Moindre privilège (pas Owner d'abonnement) |

## Procédure — Prérequis opérateur (une seule fois)

### 1. Environment GitHub `production` + reviewer

Dans **GitHub → Settings → Environments → New environment → `production`** :

- Cocher **Required reviewers** et ajouter l'opérateur (gate d'approbation manuelle CD-01).
- (Optionnel) Restreindre les branches de déploiement aux tags `prod-*`.

### 2. Les trois secrets OIDC (aucun mot de passe stocké)

Dans **GitHub → Settings → Secrets and variables → Actions** (ou Environment `production`) :

```powershell
# Valeurs récupérées une fois (app de déploiement + abonnement prod)
az ad app show --id <APP_CLIENT_ID> --query appId -o tsv          # → AZURE_CLIENT_ID
az account show --query tenantId -o tsv                           # → AZURE_TENANT_ID
az account show --query id -o tsv                                 # → AZURE_SUBSCRIPTION_ID
```

Créer les 3 secrets : `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.
**Aucun `AZURE_CLIENT_SECRET`** — c'est un déploiement OIDC fédéré.

### 3. Les credentials fédérés Entra (décision OPS-01 / Pitfall 5)

Le job `deploy` tourne **dans** l'Environment `production` ; son token OIDC porte le sujet
`:environment:production`. Le job `whatif` tourne **hors** Environment (pour afficher le diff
**avant** l'approbation) ; son token porte un sujet **différent**. Il faut donc **deux**
credentials fédérés sur l'app de déploiement.

```powershell
# (a) Credential du job deploy — sujet :environment:production
az ad app federated-credential create --id <APP_OBJECT_ID> --parameters `
  '{\"name\":\"ac360-gh-prod\",\"issuer\":\"https://token.actions.githubusercontent.com\",\"subject\":\"repo:<ORG>/<REPO>:environment:production\",\"audiences\":[\"api://AzureADTokenExchange\"]}'

# (b) Credential du job whatif — sujet tag prod-* (hors Environment)
az ad app federated-credential create --id <APP_OBJECT_ID> --parameters `
  '{\"name\":\"ac360-gh-prod-whatif\",\"issuer\":\"https://token.actions.githubusercontent.com\",\"subject\":\"repo:<ORG>/<REPO>:ref:refs/tags/prod-*\",\"audiences\":[\"api://AzureADTokenExchange\"]}'
```

> **Décision OPS-01 (Open Q1 / Pitfall 5) — résolue : DEUX credentials.** Le what-if
> reste un job séparé pré-approbation pour préserver la visibilité du diff. Comme il
> s'exécute hors de l'Environment `production`, son sujet OIDC diffère (`ref:refs/tags/prod-*`)
> et exige son **propre** credential fédéré. Le sujet du job `deploy` **doit** rester
> `:environment:production`. (Alternative écartée : replier le what-if dans le job gardé
> — cela masquerait le diff avant l'approbation.)

### 4. Rôle de moindre privilège sur le groupe de ressources prod

```powershell
# Contributor sur rg-ac360-prod UNIQUEMENT (pas Owner d'abonnement) — T-03-14
az role assignment create --assignee <APP_CLIENT_ID> --role Contributor `
  --scope /subscriptions/<SUB_ID>/resourceGroups/rg-ac360-prod

# Le sub-deploy du budget (Microsoft.Consumption/budgets) est subscription-scoped :
# rôle suffisant à l'échelle abonnement pour CE déploiement uniquement.
az role assignment create --assignee <APP_CLIENT_ID> --role "Cost Management Contributor" `
  --scope /subscriptions/<SUB_ID>
```

## Procédure — Déclencher un déploiement production

```powershell
# Option A : tag immuable (déclenche cd-prod.yml automatiquement)
git tag prod-20260701-1
git push origin prod-20260701-1

# Option B : workflow_dispatch (saisir le tag/SHA à déployer ; aussi le chemin de rollback)
#   GitHub → Actions → "AC360 CD — Production" → Run workflow → ref = prod-20260701-1
```

Le pipeline enchaîne : `build` (zip gateway + source Functions) → `whatif` (diff Bicep
posté dans le run summary) → **approbation manuelle** (Environment `production`) → `deploy`
(`az deployment group create` main.bicep + `az deployment sub create` budget + gateway
App Service B1 + Functions Flex remote-build).

## Procédure — Folder-in des checkpoints opérateur Phase 2 (pré-go-live)

Avant le **premier** déploiement, les checkpoints live de Phase 2 (`02-06-SUMMARY.md`)
doivent être confirmés :

| Checkpoint Phase 2 | Action | Confirmé |
|---|---|---|
| Résidence EU (RGP-06) | M365 geo, Fabric region, Power Platform region = EU | [ ] |
| France Central / DocIntel S0 | Flex dispo francecentral ; sinon `docIntelLocation=westeurope` | [ ] |
| What-if d'évidence | `az deployment group what-if` posture B1 + Flex + storage GRS | [ ] |
| Consentement admin OBO (INF-06) | `az ad app permission admin-consent --id <obo-appId>` ; pas d'AADSTS65001 | [ ] |
| Grant Fabric/OneLake (MI Functions) | workspace grant ou Azure RBAC — mécanisme enregistré | [ ] |

## Procédure — Post-premier-déploiement : armer l'ingress deny-all

Le déni d'ingress explicite dépend des IP sortantes de la gateway, **inconnues avant**
que l'App Service existe (cf. `02-06-SUMMARY` Runtime State + STATE) :

```powershell
# 1. Récupérer les IP sortantes possibles de la gateway (existe après le 1er deploy)
az webapp show -g rg-ac360-prod -n ac360-gateway-prod `
  --query possibleOutboundIpAddresses -o tsv

# 2. Renseigner gatewayOutboundIps dans infra/prod.parameters.json, puis re-déployer
#    (re-run cd-prod.yml) pour armer le deny-all d'ingress.
```

## Vérifications post-action (MI / référence Key Vault)

| Vérif | Commande / lieu | Attendu |
|---|---|---|
| `OBO_CLIENT_SECRET` résout la réf KV | `az webapp config appsettings list -g rg-ac360-prod -n ac360-gateway-prod --query "[?name=='OBO_CLIENT_SECRET']"` | valeur résolue (PAS le littéral `@Microsoft.KeyVault(...)`) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` résout | idem (les deux apps) | référence KV résolue, pas de littéral |
| `/health` anonyme | `Invoke-WebRequest https://ac360-gateway-prod.azurewebsites.net/health` | 200 |
| `/ready` (TLS gardé Entra) | appel authentifié `/ready` | 200 ready (ou 503 degraded), `keyvault_ref` = ok |
| Functions Flex | logs App Insights | pas de `ModuleNotFoundError` (Pitfall 1) |
| Identité managée | `az webapp identity show -g rg-ac360-prod -n ac360-func-prod` | identité présente (rôles Durable + KV Secrets User) |

## Dry-run / validation (exerçable hors ligne)

```powershell
# 1. Le pipeline existe et porte le gate OIDC + Environment
Select-String -Path .github/workflows/cd-prod.yml -Pattern "id-token: write"
Select-String -Path .github/workflows/cd-prod.yml -Pattern "environment: production"

# 2. Valider la FORME du JSON du credential fédéré (sans Azure)
'{"name":"ac360-gh-prod","issuer":"https://token.actions.githubusercontent.com","subject":"repo:<ORG>/<REPO>:environment:production","audiences":["api://AzureADTokenExchange"]}' `
  | ConvertFrom-Json | Format-List   # parse OK = forme valide

# 3. Dry-run Bicep (référence — what-if est non destructif)
az deployment group what-if -g rg-ac360-prod -f infra/main.bicep -p @infra/prod.parameters.json

# 4. Checklist hors-ligne (sans Azure live) :
#    [ ] 3 secrets OIDC nommés (pas de AZURE_CLIENT_SECRET)
#    [ ] 2 credentials fédérés (deploy :environment:production + whatif :ref:refs/tags/prod-*)
#    [ ] reviewer requis sur l'Environment production
#    [ ] rôle Contributor sur rg-ac360-prod uniquement
```

## Garanties

- **Sans secret stocké** : OIDC fédéré (rien à faire fuir, rien à faire expirer côté deploy).
- **Diff avant action** : le what-if est posté et un humain approuve avant tout apply.
- **Moindre privilège** : Contributor sur le RG, pas Owner d'abonnement.
- **Référence Key Vault** : aucun secret en clair dans les app settings (zéro-cleartext).
