# AC360 — Modèle de coût (P0-07)

> Modèle **paramétrable**. Implémentation : `scripts/cost_tracker.py`.
> **Aucun prix n'est inventé** : la grille par défaut est vide (0.0) et tout
> montant non tarifé est marqué `A_VALIDER`.

## Qualification de chaque coût (`cost_source`)

| Valeur | Sens |
|---|---|
| `REEL_MESURE` | mesuré sur facture réelle (jamais par défaut ici) |
| `ESTIME` | estimation à partir d'un tarif fourni |
| `PARAMETRABLE` | tarif fourni via configuration (`AC360_RATE_CARD`) |
| `A_VALIDER` | aucun tarif fourni → montant 0.0, à valider en environnement réel |

## Postes de coût (matrice)

| Poste (`cost_center`) | Source mesure | Méthode de calcul | Niveau de confiance | Dashboard | Alerte |
|---|---|---|---|---|---|
| `copilot_studio_message` | Power Platform admin / facturation | messages × tarif | A_VALIDER | Coûts | Budget |
| `copilot_studio_action` | Power Platform admin | actions × tarif | A_VALIDER | Coûts | Budget |
| `ocr_document_intelligence` | Azure Cost Mgmt | pages × tarif | A_VALIDER | OCR | Budget + volume |
| `fabric_onelake` | Azure / Fabric capacity | requêtes × tarif | A_VALIDER | Données | Budget |
| `backend_api` | Azure App Service / Functions | exécutions × tarif | A_VALIDER | Backend | Latence |
| `storage` | Azure Cost Mgmt | Go × tarif | A_VALIDER | Infra | — |
| `application_insights` | Azure Cost Mgmt | ingestion × tarif | A_VALIDER | Infra | Ingestion |
| `power_automate` | Power Platform | exécutions × tarif | A_VALIDER | Flows | — |
| `premium_connector` | Power Platform | appels × tarif | A_VALIDER | Connecteurs | — |

> Tous les niveaux de confiance sont `A_VALIDER` tant que la grille réelle Microsoft
> n'est pas injectée — voir `COST_ASSUMPTIONS.md`.

## Fournir la grille réelle (sans modifier le code)

```bash
# JSON {cost_center: eur_par_unite} en variable d'environnement / app setting
AC360_RATE_CARD={"ocr_document_intelligence":0.0015,"copilot_studio_message":0.01}
```
Dès qu'un tarif > 0 est fourni, les coûts de ce poste passent de `A_VALIDER` à
`PARAMETRABLE` et le montant est calculé `quantité × tarif`.

## API

```python
from cost_tracker import estimate_cost, load_rate_card, check_budget
ev = estimate_cost("ocr_document_intelligence", page_count, unit="page",
                   commercial_id="c@gerep.fr", client_id="ACME")
# ev["estimated_cost_eur"], ev["cost_source"], identifiants hashés
```

## Garanties (prouvées par tests `tests/finops/`, `tests/usage/test_cost_tracker.py`)

- Défaut sans grille → `A_VALIDER`, montant 0.0 (aucun prix inventé).
- Grille mal formée → ignorée proprement (pas de crash, pas de prix inventé).
- Poste inconnu / quantité négative → erreur explicite.
- Conformité au schéma `schemas/cost_event.schema.json`.
- Identifiants commercial/client **hashés** (jamais en clair).
