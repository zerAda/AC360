# AC360 — SEC-04 : Posture dépendances & vulnérabilités

> Livrable de la **Phase 5 (RGPD & Security Evidence Pack)** — composant **SEC-04**
> du pack de preuves de sécurité. Date : 2026-06-15.
>
> **But :** écrire noir sur blanc la posture supply-chain d'AC360 — Dependabot
> ACTIVÉ (pip + GitHub Actions) et la **politique d'épinglage** des dépendances à
> risque identifiées dans `.planning/codebase/CONCERNS.md` §« Dependencies at Risk ».
>
> **Couvre OWASP LLM03 (Supply Chain)** — voir **SEC-03** (matrice de couverture).
>
> **Note :** cette phase **n'installe aucun paquet** (RESEARCH §Package Legitimacy
> Audit : no-op ; aucun `pip install` ce cycle). SEC-04 *documente* la posture
> existante et la politique d'épinglage ; il ne modifie pas l'ensemble des
> dépendances (`requirements.txt`, `azure_functions/requirements.txt` inchangés).

---

## 1. Dependabot — ACTIVÉ

Dependabot est **déjà configuré** dans le repo via **`.github/dependabot.yml`**
(ce document décrit le fichier existant — il ne le recrée pas). Configuration en
place (`version: 2`) :

| Écosystème | Répertoire | Cadence | PR max ouvertes | Labels |
|------------|-----------|---------|-----------------|--------|
| `pip` | `/` (racine — `requirements.txt`) | hebdomadaire | 5 | `dependencies`, `security` |
| `pip` | `/azure_functions` (backend Functions) | hebdomadaire | 5 | `dependencies` |
| `pip` | `/scripts` | hebdomadaire | 5 | `dependencies`, `security` |
| `github-actions` | `/` (workflows CI/CD) | hebdomadaire | (défaut) | `ci` |

- Les mises à jour pip couvrent les **trois** manifestes Python du projet
  (racine, `/azure_functions`, `/scripts`).
- L'écosystème `github-actions` couvre la supply-chain CI/CD (épinglage d'actions).
- Le label `security` permet de filtrer/prioriser les PR à incidence sécurité.

**Optionnel — durcissement par `groups`.** Le fichier `.github/dependabot.yml`
peut être resserré en regroupant les mises à jour de sécurité pip dans un groupe
dédié (`groups: { security: { applies-to: security-updates } }`) afin de séparer
les PR de **sécurité** (à traiter en priorité) des mises à jour de version
routinières. Si le fichier est édité, **toutes les entrées existantes sont
conservées** et il **reste un YAML valide** (vérifié par
`python -c "import yaml; yaml.safe_load(open('.github/dependabot.yml'))"`).

---

## 2. Politique d'épinglage — dépendances à risque (CONCERNS.md)

Source : `.planning/codebase/CONCERNS.md` §« Dependencies at Risk ». Pour chaque
dépendance critique, l'épinglage et la procédure de mise à jour :

| Dépendance | Contrainte actuelle | Politique d'épinglage / migration | Rationale (risque) |
|------------|---------------------|-----------------------------------|--------------------|
| **PyJWT** | `>= 2.8.0` | Épingler à **2.9.0+** dès disponible/testé. Mise à jour gardée par Dependabot (label `security`) ; audit de sécurité **trimestriel** (cadence rotation GOVERNANCE §3). Ne jamais rétrograder sous 2.8.0. | JWT est critique pour l'auth (RS256/JWKS, `scripts/auth.py`) ; les versions anciennes présentaient des attaques de **confusion d'algorithme de clé** ; une faille de validation JWT contournerait l'auth entièrement. |
| **deltalake** | `>= 0.18.0` | Épingler `>= 0.18.0` ; surveiller les releases ; **valider** les colonnes du DataFrame en entrée ; tester avant montée de version (bindings Rust = surface native). | Bindings Rust — risques de sûreté en code natif ; l'accès Fabric/OneLake peut crasher si des données corrompues/malveillantes sont retournées. |
| **azure-functions-durable** | `>= 1.2.9` | **Épingler une version spécifique** ; tester soigneusement avant montée ; documenter les breaking changes ; ne pas mettre à jour automatiquement sans validation d'orchestration. | Les versions du SDK Azure changent fréquemment ; la logique d'orchestration est fortement couplée à la version du SDK ; incompatibilité possible après une mise à jour du runtime Azure. |
| **python-Levenshtein** | `>= 0.25.0` (optionnel) | Surveiller les releases ; **dégradation gracieuse** si absent (thefuzz a un fallback pur-Python) ; envisager une bibliothèque de distance pur-Python. | Extension C avec historique de **buffer overflow** ; impact faible (optionnel, fuzzy matching) ; non launch-blocking (voir SEC-05). |

> **Single source of truth des contraintes :** `requirements.txt` (racine) et
> `azure_functions/requirements.txt`. SEC-04 ne modifie pas ces fichiers ce cycle.

---

## 3. Posture de réponse aux vulnérabilités

- **Détection :** Dependabot ouvre des PR automatiques sur vulnérabilité connue
  (alertes activées via `.github/dependabot.yml`), labellisées `security` pour
  l'écosystème racine et `/scripts`.
- **Gate CI :** `pip-audit` s'exécute en CI (`.github/workflows/ci.yml`) ; toute
  install de paquet est gardée par ce job (cf. registres `<threat_model>` `T-0x-SC`).
- **Cadence de revue :** audit de sécurité **trimestriel** des dépendances
  (aligné sur la cadence de rotation des secrets, GOVERNANCE §3) — vérification de
  PyJWT 2.9.0+, deltalake, azure-functions-durable.
- **Procédure de montée de version :** PR Dependabot → CI verte (`pip-audit` +
  suite de tests) → revue → merge. Pour `deltalake` / `azure-functions-durable`,
  validation manuelle d'orchestration/Fabric avant merge.
- **Aucune install ce cycle :** Phase 5 = no-op supply-chain (RESEARCH §Package
  Legitimacy Audit) ; aucun paquet ajouté, aucune substitution.

---

## 4. Renvois croisés

- **SEC-03** (`docs/security/SEC-03-threat-coverage-matrix.md`) — ligne OWASP
  **LLM03 Supply Chain** + STRIDE `T-05-13` (dépendance vulnérable/compromise)
  pointent vers ce document et `.github/dependabot.yml`.
- **SEC-05** (`docs/security/SEC-05-accepted-risk-register.md`) — `python-Levenshtein`
  classé `accepted-deferred` (optionnel, dégradation gracieuse).
- `.github/workflows/ci.yml` — gate `pip-audit`.

---

*SEC-04 — pack de preuves de sécurité Phase 5 — 2026-06-15.*
