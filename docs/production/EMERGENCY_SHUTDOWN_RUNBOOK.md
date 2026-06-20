# AC360 — Runbook d'arrêt d'urgence / blocage de consommation (P0-09)

> Objectif : **couper la consommation du bot sans le supprimer**, en < 2 minutes,
> par un administrateur, de façon tracée et réversible.

## Principe

Le blocage est piloté par **variables d'environnement** lues à chaud par
`scripts/feature_flags.py` (aucun redéploiement de code requis). Sur Azure App
Service, ce sont des **app settings** — modifiables uniquement par un
administrateur ayant accès à la ressource. Un commercial **ne peut pas** se
débloquer lui-même (cf. `docs/security/ADMIN_CONTROLS.md`).

| Variable | Effet | Défaut |
|---|---|---|
| `AC360_GLOBAL_ENABLED=false` | **Arrêt total** (toutes fonctionnalités) | `true` |
| `AC360_OCR_ENABLED=false` | Coupe l'OCR (poste coûteux) | `true` |
| `AC360_RAG_ENABLED=false` | Coupe la recherche RAG | `true` |
| `AC360_EMAIL_DRAFT_ENABLED=false` | Coupe les brouillons mail | `true` |
| `AC360_AUDIT_ENABLED=false` | Coupe l'audit documentaire | `true` |
| `AC360_BLOCKED_USERS_HASHED=<hash,…>` | Bloque des utilisateurs (hash SHA-256) | vide |
| `AC360_BLOCKED_TEAMS=<id,…>` | Bloque des équipes | vide |

Quand une action est bloquée, l'utilisateur reçoit un message propre (HTTP 403
côté passerelle) et l'événement `*_blocked` est tracé (sans donnée sensible).

## Cible — définir l'environnement AVANT toute commande

> ⚠️ **Par défaut ce runbook vise la PRODUCTION.** Définissez ces variables en
> premier, puis copiez les commandes ci-dessous telles quelles. Ne jamais
> copier-coller une commande avec un nom de ressource en dur — un arrêt appliqué
> au mauvais environnement laisserait la prod consommer en plein incident.

```powershell
# PRODUCTION (par défaut)
$RG   = "rg-ac360-prod"
$GW   = "ac360-gateway-prod"
$FUNC = "ac360-func-prod"

# STAGING / pré-production — décommenter UNIQUEMENT si l'incident y est cantonné
# $RG = "rg-ac360-staging"; $GW = "ac360-gateway-staging"; $FUNC = "ac360-func-staging"
```

## Procédure — Arrêt total (incident majeur)

```powershell
# 1. Couper la consommation globale (effet immédiat, pas de redéploiement)
az webapp config appsettings set -g $RG -n $GW `
  --settings AC360_GLOBAL_ENABLED=false

# 2. Vérifier : un appel /api/audit authentifié doit renvoyer 403
#    (la passerelle reste UP, /health = 200, mais l'audit est refusé)
```
> Effet en quelques secondes (l'app setting déclenche un recyclage). La passerelle
> **reste en ligne** (`/health` 200) ; seules les fonctionnalités sont coupées.

## Procédure — Couper uniquement un poste coûteux (ex. OCR)

```powershell
az webapp config appsettings set -g $RG -n $FUNC `
  --settings AC360_OCR_ENABLED=false
az webapp config appsettings set -g $RG -n $GW `
  --settings AC360_OCR_ENABLED=false
```

## Procédure — Bloquer un commercial précis

1. Calculer le hash (jamais l'UPN en clair dans la config) :
   ```python
   python -c "from scripts.feature_flags import hash_id; print(hash_id('prenom.nom@gerep.fr'))"
   ```
2. Ajouter le hash (CSV) :
   ```powershell
   az webapp config appsettings set -g $RG -n $GW `
     --settings AC360_BLOCKED_USERS_HASHED="<hash1>,<hash2>"
   ```

## Réactivation (déblocage contrôlé)

```powershell
az webapp config appsettings set -g $RG -n $GW `
  --settings AC360_GLOBAL_ENABLED=true
# ou retirer le hash de AC360_BLOCKED_USERS_HASHED / remettre AC360_OCR_ENABLED=true
```
> Réservé à un administrateur. Toute action de contrôle doit être enregistrée
> (audit log, cf. `admin_controls.apply_control`).

## Vérifications post-action

| Vérif | Attendu |
|---|---|
| `GET /health` | 200 (le bot n'est pas supprimé) |
| `POST /api/audit` (jeton valide) pendant blocage | **403** + message propre |
| Après réactivation | l'audit repart (202/200) |
| Logs | événement `bot_emergency_stopped` / `user_blocked` tracé, **sans PII** |

## Garanties

- **Réversible** : aucun composant n'est supprimé.
- **Sans redéploiement** : changement d'app setting uniquement.
- **Tracé** : chaque action admin produit un événement conforme à
  `schemas/admin_control.schema.json`.
- **Sans PII** : utilisateurs identifiés par hash SHA-256.
- **No block by default** : tout est activé tant qu'un admin n'agit pas.

## Statuts

- Mécanisme code + tests : **PROUVÉ** (`tests/admin/`, `tests/backend/test_killswitch_gate.py`).
- Effet réel des app settings sur l'instance Azure : **À VALIDER EN ENVIRONNEMENT RÉEL**
  (le recyclage App Service est attendu en quelques secondes mais non chronométré ici).
