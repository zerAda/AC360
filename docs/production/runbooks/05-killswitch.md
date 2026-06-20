# AC360 — Runbook kill-switch (feature flags) (OPS-05)

> Objectif : couper instantanément l'audit / l'OCR / le RAG, ou bloquer un
> utilisateur / une équipe, **sans redéploiement**, de façon réversible et tracée —
> par un seul opérateur.

## Principe

Le kill-switch est piloté par **variables d'environnement** lues à chaud par
`scripts/feature_flags.py` (aucun redéploiement de code). Sur Azure App Service ce
sont des **app settings** (`az webapp config appsettings set -g rg-ac360-prod`),
modifiables uniquement par un administrateur ayant accès à la ressource. Un commercial
**ne peut pas** se débloquer lui-même (cf. `docs/security/ADMIN_CONTROLS.md`).

> Ce runbook est le **kill-switch rapide** (arbre de décision OPS-05). Pour la
> procédure d'**arrêt d'urgence** complète, voir **`docs/production/EMERGENCY_SHUTDOWN_RUNBOOK.md`**
> (P0-09) — c'est la procédure profonde dont ce runbook est la version d'action rapide.

| Variable | Effet | Défaut |
|---|---|---|
| `AC360_GLOBAL_ENABLED=false` | **Arrêt total** (toutes fonctionnalités) | `true` |
| `AC360_OCR_ENABLED=false` | Coupe l'OCR (poste coûteux) | `true` |
| `AC360_RAG_ENABLED=false` | Coupe la recherche RAG | `true` |
| `AC360_EMAIL_DRAFT_ENABLED=false` | Coupe les brouillons mail | `true` |
| `AC360_AUDIT_ENABLED=false` | Coupe l'audit documentaire | `true` |
| `AC360_BLOCKED_USERS_HASHED=<hash,…>` | Bloque des utilisateurs (hash SHA-256) | vide |
| `AC360_BLOCKED_TEAMS=<id,…>` | Bloque des équipes | vide |
| `AC360_ALLOWED_USERS_HASHED=<hash,…>` | **Allowlist — deny-by-default quand renseignée** : seuls ces utilisateurs passent. La rétrécir = endiguement instantané du périmètre. | vide (= pas de restriction) |
| `AC360_ALLOWED_TEAMS=<id,…>` | Allowlist d'équipes (deny-by-default quand renseignée) | vide |

> **Levier de périmètre le plus rapide** : l'allowlist (`AC360_ALLOWED_*`,
> garde testée dans `tests/backend/test_feature_flags_allowlist.py`) contient le
> rayon d'action sans couper de fonctionnalité — la réduire à zéro pilote bloque
> tout accès (cf. runbook **08 — rollout/rollback**, « shrink to zero »).

## Procédure — Quel switch actionner ? (arbre de décision)

| Situation | Action |
|---|---|
| Incident majeur, tout couper | `AC360_GLOBAL_ENABLED=false` |
| Coût OCR qui dérive (alerte budget) | `AC360_OCR_ENABLED=false` |
| RAG bruyant / abusé | `AC360_RAG_ENABLED=false` |
| Audit fautif uniquement | `AC360_AUDIT_ENABLED=false` |
| Un commercial précis abuse | ajouter son hash à `AC360_BLOCKED_USERS_HASHED` |
| Une équipe entière | ajouter son id à `AC360_BLOCKED_TEAMS` |

## Procédure — Couper un poste coûteux (ex. OCR)

```powershell
# Couper sur les DEUX apps (gateway + worker Functions)
az webapp config appsettings set -g rg-ac360-prod -n ac360-func-prod `
  --settings AC360_OCR_ENABLED=false
az webapp config appsettings set -g rg-ac360-prod -n ac360-gateway-prod `
  --settings AC360_OCR_ENABLED=false
```

## Procédure — Arrêt total (incident majeur)

```powershell
az webapp config appsettings set -g rg-ac360-prod -n ac360-gateway-prod `
  --settings AC360_GLOBAL_ENABLED=false
# La passerelle reste UP (/health=200) ; l'audit renvoie 403.
```

## Procédure — Bloquer un commercial précis

```powershell
# 1. Calculer le hash (jamais l'UPN en clair dans la config)
python -c "from scripts.feature_flags import hash_id; print(hash_id('prenom.nom@gerep.fr'))"

# 2. Ajouter le hash (CSV) sur la gateway
az webapp config appsettings set -g rg-ac360-prod -n ac360-gateway-prod `
  --settings AC360_BLOCKED_USERS_HASHED="<hash1>,<hash2>"
```

## Procédure — Réactivation (déblocage contrôlé)

```powershell
az webapp config appsettings set -g rg-ac360-prod -n ac360-gateway-prod `
  --settings AC360_GLOBAL_ENABLED=true
# ou retirer le hash de AC360_BLOCKED_USERS_HASHED / remettre AC360_OCR_ENABLED=true
```

## Vérifications post-action

| Vérif | Attendu |
|---|---|
| `GET /health` | 200 (le bot n'est pas supprimé) |
| `POST /api/audit` (jeton valide) pendant blocage | **403** + message propre |
| Après réactivation | l'audit repart (202/200) |
| Logs | événement `*_blocked` / `bot_emergency_stopped` tracé, **sans PII** |

## Dry-run / validation (exerçable hors ligne)

```powershell
# 1. Le mécanisme est prouvé par les tests (sans Azure)
#    tests/admin/ + tests/backend/test_killswitch_gate.py
python -m pytest tests/backend/test_killswitch_gate.py -q

# 2. Calculer un hash de blocage localement (pas d'UPN en clair en config)
python -c "from scripts.feature_flags import hash_id; print(hash_id('prenom.nom@gerep.fr'))"

# 3. Vérifier que les commandes ciblent bien rg-ac360-prod (pas staging)
Select-String -Path docs/production/runbooks/05-killswitch.md -Pattern "rg-ac360-prod"

# 4. Checklist hors-ligne :
#    [ ] OCR/RAG/AUDIT coupables indépendamment + arrêt global
#    [ ] blocage par hash SHA-256 (jamais l'UPN en clair)
#    [ ] cross-link vers EMERGENCY_SHUTDOWN_RUNBOOK.md présent
```

## Garanties

- **Sans redéploiement** : changement d'app setting uniquement (effet en secondes).
- **Réversible** : aucun composant supprimé ; réactivation par un admin.
- **Tracé** : chaque action admin produit un événement (`admin_controls.apply_control`).
- **Sans PII** : utilisateurs identifiés par hash SHA-256 (T-03-17).
