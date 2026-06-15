# AC360 — Runbook de rotation des secrets (OPS-03)

> Objectif : faire tourner chaque secret avant son expiration, sans interruption
> ni secret en clair, en suivant les dates d'expiration — par un seul opérateur.

## Principe

AC360 applique le **zéro-cleartext** : les secrets vivent dans **Key Vault**
(`ac360-kv-prod`) et sont consommés par les apps via des références
`@Microsoft.KeyVault(SecretUri=...)`. L'app d'audience (`AC360-API-prod`) **ne porte
aucun secret** ; seul le client confidentiel OBO (`AC360-OBO-prod`) en a un, stocké
**uniquement** dans Key Vault sous `OBO-CLIENT-SECRET` (décision STATE 02-02).

Le déploiement, lui, n'a **aucun secret à faire tourner** : il utilise OIDC fédéré
(bénéfice OIDC — T-03-20 : plus de secret de déploiement longue durée à expirer).

| Secret | Emplacement | Rotation | Bénéfice |
|---|---|---|---|
| `OBO-CLIENT-SECRET` | Key Vault `ac360-kv-prod` (réf KV sur la gateway) | reset credential app-reg OBO → KV → restart | secret confidentiel OBO |
| `AZURE_OCR_KEY` | Key Vault (réf KV) | régénérer la clé DocIntel → KV | clé Document Intelligence |
| Identifiants Fabric | Key Vault (réf KV) | régénérer côté Fabric → KV | accès référentiel ARTUS |
| OIDC déploiement | — (fédéré, **pas de secret**) | **rien à faire tourner** | OIDC = pas de secret stocké |

## Suivi des expirations

> À tenir à jour à chaque rotation. Cible : rotation **avant** la date d'expiration.

| Secret | Dernière rotation | Expire le | Prochaine rotation | Responsable |
|---|---|---|---|---|
| `OBO-CLIENT-SECRET` | `__________` | `__________` | `__________` | opérateur |
| `AZURE_OCR_KEY` | `__________` | n/a (clé régénérable) | `__________` | opérateur |
| Identifiants Fabric | `__________` | `__________` | `__________` | opérateur |
| OIDC déploiement | n/a | **n/a (OIDC)** | n/a | — |

## Procédure — Rotation du secret OBO (`OBO-CLIENT-SECRET`)

```powershell
# 1. Générer un nouveau secret sur l'app-registration OBO (client confidentiel)
$new = az ad app credential reset --id <OBO_APP_ID> `
  --display-name "obo-$(Get-Date -Format yyyyMMdd)" --years 1 `
  --query password -o tsv

# 2. Écrire la nouvelle valeur dans Key Vault (la seule source du secret)
az keyvault secret set --vault-name ac360-kv-prod `
  --name OBO-CLIENT-SECRET --value $new
$new = $null   # ne pas laisser le secret en variable

# 3. Recycler la gateway pour relire la référence KV
az webapp restart -g rg-ac360-prod -n ac360-gateway-prod

# 4. Confirmer que la référence KV résout (pas le littéral) + OBO smoke
az webapp config appsettings list -g rg-ac360-prod -n ac360-gateway-prod `
  --query "[?name=='OBO_CLIENT_SECRET']"
#    → un appel OBO doit réussir (pas d'AADSTS65001 / 401)
```

> Mettre à jour la ligne `OBO-CLIENT-SECRET` du tableau de suivi (nouvelle date
> d'expiration = `+1 an`).

## Procédure — Rotation de la clé OCR (DocIntel)

```powershell
# 1. Régénérer key2 côté DocIntel (laisse key1 active le temps du basculement)
az cognitiveservices account keys regenerate -g rg-ac360-prod `
  -n ac360-docintel-prod --key-name key2
$ocr = az cognitiveservices account keys list -g rg-ac360-prod `
  -n ac360-docintel-prod --query key2 -o tsv

# 2. Écrire dans Key Vault, recycler le worker, vérifier
az keyvault secret set --vault-name ac360-kv-prod --name AZURE-OCR-KEY --value $ocr
$ocr = $null
az webapp restart -g rg-ac360-prod -n ac360-func-prod
```

## Procédure — Rotation des identifiants Fabric

```powershell
# 1. Régénérer le credential côté Fabric/référentiel ARTUS (selon le mécanisme retenu
#    à l'INF-06 : grant workspace vs RBAC). 2. Écrire la nouvelle valeur en KV.
az keyvault secret set --vault-name ac360-kv-prod --name FABRIC-CLIENT-SECRET --value <new>
# 3. Recycler le worker, confirmer une requête Fabric (audit de bout en bout).
az webapp restart -g rg-ac360-prod -n ac360-func-prod
```

## Vérifications post-action

| Vérif | Attendu |
|---|---|
| Réf KV résout | l'app setting n'affiche **pas** le littéral `@Microsoft.KeyVault(...)` |
| OBO smoke | appel OBO réussi, **pas** d'`AADSTS65001` |
| OCR smoke | un audit déclenche l'OCR sans 401 DocIntel |
| `/health` | reste 200 pendant/après le restart |
| Tableau de suivi | dates de rotation + expiration mises à jour |

## Dry-run / validation (exerçable hors ligne)

```powershell
# 1. Lister les secrets attendus (forme, sans valeur) — sans toucher au cloud
'OBO-CLIENT-SECRET','AZURE-OCR-KEY','FABRIC-CLIENT-SECRET' | ForEach-Object { $_ }

# 2. Vérifier que les apps consomment des RÉFÉRENCES KV (pas des littéraux) dans l'IaC
Select-String -Path infra/main.bicep -Pattern "@Microsoft.KeyVault"

# 3. Confirmer que le déploiement n'a AUCUN secret à faire tourner (OIDC)
Select-String -Path .github/workflows/cd-prod.yml -Pattern "id-token: write"
#    (aucun AZURE_CLIENT_SECRET référencé)

# 4. Checklist hors-ligne :
#    [ ] OBO-CLIENT-SECRET vit en Key Vault uniquement (jamais sur AC360-API-prod)
#    [ ] chaque secret a une date d'expiration + prochaine rotation au tableau
#    [ ] OIDC déploiement = rien à faire tourner
```

## Garanties

- **Zéro-cleartext** : les secrets ne quittent jamais Key Vault ; les apps lisent des références.
- **OBO isolé** : seul `AC360-OBO-prod` porte un secret ; `AC360-API-prod` n'en a aucun.
- **Expiry tracé** : tableau de suivi → pas d'expiration silencieuse (T-03-20).
- **Pas de secret de déploiement** : OIDC supprime le secret longue durée du CD.
