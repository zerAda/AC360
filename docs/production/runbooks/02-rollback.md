# AC360 — Runbook de rollback production (OPS-02)

> Objectif : revenir à la **dernière version connue-bonne** en **< 10 minutes**,
> par re-déploiement d'un tag git `prod-*` immuable, sans slot de déploiement
> (B1 n'en a pas) — par un seul opérateur.

## Principe

AC360 tourne sur un App Service **B1** mono-instance (pin AUD-04, état en mémoire
load-bearing). **B1 n'a PAS de slots de déploiement** (les slots exigent S1+, ce qui
casserait le pin mono-instance). Le rollback n'est donc **pas un slot-swap** : c'est un
**re-déploiement du tag `prod-*` précédent connu-bon** via `cd-prod.yml`.

Chaque déploiement production est marqué par un tag git immuable `prod-YYYYMMDD-N`
(le déclencheur du pipeline). Ce tag **est** le marqueur connu-bon : pour revenir en
arrière, on re-déploie le tag précédent.

| Aspect | Valeur |
|---|---|
| Marqueur connu-bon | tag git `prod-YYYYMMDD-N` (immuable, signé) |
| Mécanisme | re-run `cd-prod.yml` (workflow_dispatch `ref`) sur le tag précédent |
| Slots | **AUCUN** (B1 ; slots = S1+ → casse le pin AUD-04 mono-instance) |
| Cible < 10 min | oui (le pipeline rejoue build → what-if → deploy gardé) |

## Procédure — Décider de rollback (déclencheur)

Déclencher un rollback si **au moins un** des cas suivants est avéré après un déploiement :

| Déclencheur | Source |
|---|---|
| Alerte 5xx gateway soutenue | metricAlert `gw5xx` (Plan 03) |
| Test de disponibilité `/health` en échec | webtest availability alert |
| `/ready` reste 503 (degraded) après stabilisation | check post-deploy |
| `ModuleNotFoundError` / déploiement Functions Flex cassé | logs App Insights (Pitfall 1) |

> Règle solo-opérateur : si le déploiement vient de passer et la prod est dégradée,
> **rollback d'abord, diagnostic ensuite** (le tag précédent est connu-bon).

## Procédure — Rollback < 10 min

```powershell
# 1. Lister les tags connus-bons et identifier le PRÉCÉDENT (avant le déploiement fautif)
git tag --list "prod-*" --sort=-creatordate | Select-Object -First 5
#    ex. fautif = prod-20260701-2  →  cible rollback = prod-20260701-1

# 2. Re-déployer le tag précédent via workflow_dispatch
#    GitHub → Actions → "AC360 CD — Production" → Run workflow
#      ref = prod-20260701-1   (le tag connu-bon précédent)
#    → build → what-if (diff posté) → APPROBATION (Environment production) → deploy
```

Le what-if affiche le diff inverse (retour à l'état du tag précédent) ; l'opérateur
approuve l'Environment `production`, puis le déploiement rejoue main.bicep + budget +
gateway + Functions sur la révision connue-bonne.

> **Pas de slot-swap** : sur B1 il n'existe aucun slot ; le rollback **est** ce
> re-déploiement de tag. Ne pas chercher de bouton "swap".

## Vérifications post-action

| Vérif | Commande / lieu | Attendu |
|---|---|---|
| `/health` rétabli | `Invoke-WebRequest https://ac360-gateway-prod.azurewebsites.net/health` | 200 |
| `/ready` rétabli | appel authentifié `/ready` | 200 ready |
| Alerte 5xx retombée | metricAlert `gw5xx` (workbook one-pane) | resolved |
| Durée chronométrée | horodatage début → `/health` 200 | **< 10 min** |
| Functions OK | logs App Insights | pas de `ModuleNotFoundError` |

## Dry-run / validation (exerçable hors ligne)

```powershell
# 1. Les tags connus-bons existent et sont triables (sans Azure)
git tag --list "prod-*" --sort=-creatordate

# 2. Identifier la cible de rollback = le tag prod-* immédiatement antérieur au fautif
#    (simulation : si HEAD-deploy = N, cible = N-1)

# 3. Le pipeline accepte un ref arbitraire (rollback = ref d'un tag précédent)
Select-String -Path .github/workflows/cd-prod.yml -Pattern "workflow_dispatch"
Select-String -Path .github/workflows/cd-prod.yml -Pattern "inputs.ref"

# 4. Checklist hors-ligne :
#    [ ] le tag cible existe (git tag --list 'prod-*')
#    [ ] AUCUN slot attendu (B1) — le rollback est un re-deploy de tag
#    [ ] le diff what-if sera revu avant approbation
#    [ ] objectif chronométré < 10 min
```

## Garanties

- **< 10 min** : re-run du pipeline sur un tag connu-bon (pas de rebuild manuel).
- **Cible immuable** : un tag `prod-*` signé (T-03-19 — pas de rollback vers un état trafiqué).
- **Diff avant action** : le what-if reste posté avant l'approbation, même en rollback.
- **Mono-instance préservé** : aucun slot introduit (AUD-04 intact).
