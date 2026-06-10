# AC360 — Alertes budget (P0-07)

> Détection de seuils budgétaires **sans blocage automatique**. Implémentation :
> `cost_tracker.check_budget()`. Le blocage reste une **décision admin** explicite
> (kill-switch), jamais une coupure automatique surprise.

## Configuration

| Variable | Rôle | Défaut |
|---|---|---|
| `AC360_BUDGET_EUR` | budget mensuel cible | non défini |
| `AC360_BUDGET_WARN_PCT` | seuil d'avertissement (%) | `80` |

## Niveaux retournés

| Niveau | Condition |
|---|---|
| `unknown` | aucun budget configuré |
| `ok` | dépense < seuil d'avertissement |
| `warning` | dépense ≥ `AC360_BUDGET_WARN_PCT` % du budget |
| `exceeded` | dépense ≥ 100 % du budget |

```python
from cost_tracker import check_budget
status = check_budget(spent_eur=160.0)   # lit AC360_BUDGET_EUR / WARN_PCT
# {"level": "warning", "ratio_pct": 80.0, ...}
```

## Chaîne d'alerte (recommandée)

1. Un job d'agrégation périodique additionne les `cost_event` (`estimated_cost_eur`).
2. `check_budget(total)` évalue le niveau.
3. Sur `warning`/`exceeded` → émettre l'événement usage `budget_warning_triggered`
   et notifier (Teams / Application Insights — cf. `docs/observability/ALERTING_RULES.md`).
4. **Décision humaine** : un admin peut alors activer le kill-switch
   (`EMERGENCY_SHUTDOWN_RUNBOOK.md`). Aucune coupure automatique.

## Garantie (prouvée)

`tests/finops/test_budget_thresholds.py` :
- niveaux `ok`/`warning`/`exceeded`/`unknown` corrects ;
- **`check_budget` ne contient aucune action de blocage** (`no auto-block`).

## À valider en environnement réel

- Le budget chiffré (`AC360_BUDGET_EUR`) dépend du contrat GEREP → **À VALIDER**.
- Les seuils d'alerte fins (latence, pics) → cf. `ALERTING_RULES.md`.
