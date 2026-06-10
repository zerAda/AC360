# AC360 — Contrôles administrateur (P0-09)

> Qui peut bloquer/débloquer la consommation, comment c'est autorisé, et pourquoi
> un commercial ne peut pas se débloquer lui-même.

## Modèle d'autorisation

Implémenté dans `scripts/admin_controls.py`.

- Une **action de contrôle** (bloquer/débloquer) n'est appliquée que si l'appelant
  possède le **rôle admin** Entra (`AC360_ADMIN_ROLE`, défaut `AC360.Admin`).
- `is_admin(roles)` vérifie la présence du rôle dans les `roles` du jeton Entra.
- `apply_control(...)` renvoie une action auditée avec `result` :
  - `applied` — appelant admin + action/scope cohérents ;
  - `denied_not_admin` — appelant **non admin** (ex. un commercial) ;
  - `noop` — action inconnue ou scope incohérent.

### Pourquoi un commercial ne peut pas se débloquer
1. **Couche applicative** : `apply_control` renvoie `denied_not_admin` sans le rôle
   `AC360.Admin` — prouvé par `tests/admin/test_admin_authorization.py::test_commercial_cannot_self_unblock`.
2. **Couche infrastructure** : l'application effective d'un blocage = modification
   d'**app setting Azure**, accessible aux seuls administrateurs de la ressource.
   Un commercial n'a aucun accès à l'app setting → ne peut pas le remettre à `true`.

→ Double barrière : rôle applicatif **et** RBAC Azure.

## Périmètres de contrôle (`scope`)

| Action | Scope | Effet |
|---|---|---|
| `block_global` / `unblock_global` | `global` | tout le bot |
| `emergency_stop` | `global` | arrêt d'urgence |
| `block_feature` / `unblock_feature` | `ocr`/`rag`/`email_draft`/`audit` | une fonctionnalité |
| `block_user` / `unblock_user` | `user` | un utilisateur (hash) |
| `block_team` / `unblock_team` | `team` | une équipe |

## Traçabilité & confidentialité

- Chaque action produit un événement conforme à `schemas/admin_control.schema.json`.
- `admin_id_hash` et `target_hash` sont des **SHA-256** : aucun UPN/email en clair.
- `reason` est libre mais ne doit pas contenir de donnée sensible.

## Rôle Entra requis

- Définir `AC360_ADMIN_ROLE` (défaut `AC360.Admin`) et l'**app role** correspondant
  sur l'app registration `AC360-API-staging`, assigné aux administrateurs.
- Statut : modèle de code **PROUVÉ** (tests) ; assignation réelle de l'app role
  Entra = **À VALIDER EN ENVIRONNEMENT RÉEL**.

## Lien

Procédures opérationnelles → `docs/production/EMERGENCY_SHUTDOWN_RUNBOOK.md`.
