# AC360 — Hypothèses de coût (P0-07)

> Transparence totale sur ce qui est **mesuré**, **estimé** ou **à valider**.

## Règle fondamentale

**Aucun prix Microsoft n'est codé en dur dans ce dépôt.** Les tarifs réels
(Copilot Studio, Document Intelligence, Fabric, App Service…) dépendent du
contrat GEREP, de la région et du modèle de licence (pay-as-you-go vs message
pack). Ils ne sont donc **pas** dans le code.

## Conséquence

| Élément | Statut par défaut |
|---|---|
| Grille tarifaire (`AC360_RATE_CARD`) | **vide** → tout poste `A_VALIDER`, montant 0.0 |
| Budget (`AC360_BUDGET_EUR`) | non défini → `check_budget` renvoie `unknown` |
| Tokens | **ESTIMÉS** (`estimated_tokens_*`) — Copilot Studio n'expose pas les tokens réels |

## Ce qui est RÉEL / mesurable vs À VALIDER

| Donnée | Statut |
|---|---|
| Volume de documents, pages OCR, conversations, actions | **mesurable** via usage tracker (`estimated_tokens_*` à part) |
| Coût unitaire par poste | **A_VALIDER** (à fournir via `AC360_RATE_CARD`) |
| Coût total / par commercial / par client | **calculable dès que la grille est fournie**, sinon 0.0 `A_VALIDER` |
| Tokens réels par message | **non disponible** (estimation uniquement) |

## Pour passer en coûts réels

1. Récupérer les tarifs réels (Power Platform Licensing Guide + Azure Pricing /
   Azure Cost Management export).
2. Renseigner `AC360_RATE_CARD` (app setting) et `AC360_BUDGET_EUR`.
3. Les coûts passent en `PARAMETRABLE` (puis `REEL_MESURE` une fois rapprochés des
   factures réelles).

## Estimation préalable recommandée

Microsoft fournit un **Copilot Studio agent usage estimator** pour forecaster la
consommation en Copilot Credits avant engagement. À utiliser pour cadrer le
budget initial. Résultat = `ESTIME`, jamais `REEL_MESURE`.
