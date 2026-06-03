# Inventaire Complet du Projet AC360

> **Objectif** : Tracer l'ensemble des fichiers et dossiers du repo AC360, leur rôle, statut et niveau de risque.  
> **Mise à jour** : 2026-06-03  
> **Responsable** : Product Owner GEREP + Admin Power Platform

---

## Légende des statuts

| Statut | Signification |
|---|---|
| `UTILE` | Fichier actif, nécessaire au fonctionnement du produit |
| `EN_COURS` | Fichier en développement ou en cours de validation |
| `DANGEREUX` | Fichier contenant des données sensibles ou des secrets — action requise |
| `OBSOLÈTE` | Fichier dépassé mais non encore supprimé |
| `À_SUPPRIMER` | Fichier identifié pour suppression du repo |
| `À_CORRIGER` | Fichier présent mais nécessitant une correction avant mise en prod |

---

## Légende des risques

| Risque | Signification |
|---|---|
| `CRITIQUE` | Exposition de données client ou de secrets |
| `ÉLEVÉ` | Impact potentiel sur la sécurité ou la conformité |
| `MOYEN` | Impact fonctionnel ou qualité |
| `FAIBLE` | Impact limité, esthétique ou documentation |
| `AUCUN` | Aucun risque identifié |

---

## Racine du projet

| Chemin | Type | Rôle | Statut | Risque | Décision |
|---|---|---|---|---|---|
| `README.md` | Fichier | Documentation principale du projet | `UTILE` | `AUCUN` | Maintenir à jour |
| `.gitleaks.toml` | Fichier | Prévention des fuites de secrets dans le repo | `UTILE` | `AUCUN` | Intégrer dans CI/CD |
| `.gitignore` | Fichier | Exclusion des fichiers sensibles du versioning | `UTILE` | `MOYEN` | Vérifier les patterns |
| `.env` | Fichier | Variables d'environnement locales | `DANGEREUX` | `CRITIQUE` | Ne jamais committer — dans .gitignore |
| `test_audits.db` | Fichier | Base SQLite des audits de test | `À_SUPPRIMER` | `ÉLEVÉ` | Supprimer, ne pas committer |
| `matrice_classement_clients.xlsx` | Fichier | Données client sensibles | `DANGEREUX` | `CRITIQUE` | Supprimer du repo — stocker sur SharePoint |
| `docs_content.txt` | Fichier | Export brut de contenu documentaire | `À_SUPPRIMER` | `ÉLEVÉ` | Supprimer — données potentiellement sensibles |
| `final_audit_report.*` | Fichier | Rapport d'audit généré | `À_SUPPRIMER` | `ÉLEVÉ` | Exclure via .gitignore |
| `matrice_content.*` | Fichier | Contenu matrice exporté | `À_SUPPRIMER` | `ÉLEVÉ` | Exclure via .gitignore |

---

## Dossier `docs/`

| Chemin | Type | Rôle | Statut | Risque | Décision |
|---|---|---|---|---|---|
| `docs/00_PROJECT_INVENTORY.md` | Fichier | Inventaire du repo (ce document) | `UTILE` | `AUCUN` | Maintenir à jour |
| `docs/architecture/ARCHITECTURE_TARGET.md` | Fichier | Architecture cible et flux de données | `UTILE` | `AUCUN` | Valider avec DSI |
| `docs/copilot/TOPIC_MAP.md` | Fichier | Cartographie des topics Copilot Studio | `UTILE` | `AUCUN` | Maintenir synchronisé avec les YAML |
| `docs/copilot/COPILOT_SETTINGS_DECISIONS.md` | Fichier | Décisions de configuration Copilot Studio | `UTILE` | `FAIBLE` | Valider avant chaque release |
| `docs/copilot/ACTIONS_SECURITY_REVIEW.md` | Fichier | Review sécurité des actions et connecteurs | `UTILE` | `MOYEN` | Revalider à chaque ajout d'action |
| `docs/security/SECURITY_BASELINE.md` | Fichier | Baseline sécurité enterprise | `UTILE` | `AUCUN` | Approuver par RSSI |
| `docs/security/SECRET_ROTATION.md` | Fichier | Procédure de rotation des secrets | `UTILE` | `FAIBLE` | Planifier exécution trimestrielle |
| `docs/security/SECURITY_GATE.md` | Fichier | Checklist gate sécurité | `UTILE` | `AUCUN` | Exécuter avant chaque déploiement PROD |
| `docs/rag/RAG_POLICY.md` | Fichier | Politique des sources RAG | `UTILE` | `AUCUN` | Valider avec RSSI et DPO |
| `docs/governance/ENVIRONMENT_STRATEGY.md` | Fichier | Stratégie environnements DEV/TEST/PROD | `UTILE` | `AUCUN` | Implémenter avant passage en PROD |
| `docs/governance/DLP_POLICY_REQUIREMENTS.md` | Fichier | Exigences DLP Power Platform | `UTILE` | `MOYEN` | Configurer et tester |
| `docs/governance/RACI.md` | Fichier | Matrice RACI AC360 | `UTILE` | `AUCUN` | Valider avec toutes les parties prenantes |
| `docs/alm/DEPLOYMENT_RUNBOOK.md` | Fichier | Runbook de déploiement step-by-step | `UTILE` | `AUCUN` | Tester en environnement TEST |
| `docs/alm/RELEASE_CHECKLIST.md` | Fichier | Checklist release multi-gates | `UTILE` | `AUCUN` | Exécuter à chaque release |
| `docs/observability/MONITORING_PLAN.md` | Fichier | Plan de monitoring et alertes | `UTILE` | `AUCUN` | Configurer Application Insights |
| `docs/support/RUNBOOK_INCIDENTS.md` | Fichier | Procédures de résolution d'incidents | `UTILE` | `AUCUN` | Former l'équipe support |
| `docs/product/PRODUCT_POSITIONING.md` | Fichier | Positionnement produit et proposition de valeur | `UTILE` | `AUCUN` | Utiliser pour les présentations direction |
| `docs/product/DEMO_SCRIPT.md` | Fichier | Script de démonstration (7 scénarios) | `UTILE` | `FAIBLE` | Adapter avec données de démo fictives uniquement |

---

## Dossier `src/`

| Chemin | Type | Rôle | Statut | Risque | Décision |
|---|---|---|---|---|---|
| `src/copilot/AC360/` | Dossier | Sources YAML de l'agent Copilot Studio | `UTILE` | `MOYEN` | Valider via validate_copilot_yaml.py |
| `src/copilot/AC360/*.cognitiveServicesSetting.yml` | Fichier | Configuration cognitive services | `UTILE` | `MOYEN` | Vérifier absence de clés en clair |
| `src/copilot/AC360/topics/` | Dossier | Topics YAML (conversations) | `UTILE` | `FAIBLE` | Valider structure et triggers |
| `src/copilot/AC360/topics/*_disabled.yml` | Fichiers | Topics désactivés | `OBSOLÈTE` | `FAIBLE` | Archiver ou supprimer proprement |
| `src/copilot/AC360/actions/` | Dossier | Définitions des actions connecteurs | `UTILE` | `ÉLEVÉ` | Revalider preview connectors |
| `src/copilot/AC360/knowledgeSources/` | Dossier | Sources de connaissance (SharePoint) | `UTILE` | `MOYEN` | Vérifier URLs et permissions |
| `src/copilot/AC360/.entities/` | Dossier | Entités extraites (NLU) | `UTILE` | `FAIBLE` | Maintenir |
| `src/copilot/AC360/.schema/` | Dossier | Schémas de validation | `UTILE` | `AUCUN` | Maintenir |

---

## Dossier `src/api/` (expérimental)

| Chemin | Type | Rôle | Statut | Risque | Décision |
|---|---|---|---|---|---|
| `src/api/` | Dossier | API Python Flask/FastAPI pour audit PDF/Excel | `EN_COURS` | `ÉLEVÉ` | Non activée en PROD — expérimental |
| `src/api/app.py` | Fichier | Point d'entrée de l'API | `EN_COURS` | `ÉLEVÉ` | Valider auth JWT avant activation |
| `src/api/requirements.txt` | Fichier | Dépendances Python | `EN_COURS` | `MOYEN` | Figer les versions |
| `src/api/jobs/` | Dossier | Résultats temporaires de jobs d'audit | `À_SUPPRIMER` | `CRITIQUE` | Exclure du repo — données client potentielles |
| `src/api/Archives_Documentaires/` | Dossier | Archives de documents clients | `DANGEREUX` | `CRITIQUE` | Supprimer immédiatement du repo |

---

## Dossier `scripts/`

| Chemin | Type | Rôle | Statut | Risque | Décision |
|---|---|---|---|---|---|
| `scripts/validate_copilot_yaml.py` | Fichier | Validation syntaxique des YAML Copilot | `UTILE` | `AUCUN` | Intégrer en CI/CD |
| `scripts/package_release.ps1` | Fichier | Packaging propre d'une release | `UTILE` | `FAIBLE` | Utiliser avant chaque déploiement |
| `scripts/cleanup_local_artifacts.ps1` | Fichier | Nettoyage des artefacts locaux sensibles | `UTILE` | `FAIBLE` | Exécuter régulièrement en DEV |

---

## Dossier `tests/`

| Chemin | Type | Rôle | Statut | Risque | Décision |
|---|---|---|---|---|---|
| `tests/red_team/RED_TEAM_PROMPTS.md` | Fichier | 20 prompts de test d'adversarial robustness | `UTILE` | `FAIBLE` | Exécuter avant toute mise en prod |
| `tests/acceptance/ACCEPTANCE_TEST_MATRIX.md` | Fichier | Matrice UAT (20 cas de test) | `UTILE` | `AUCUN` | Faire valider par le métier |

---

## Fichiers à exclure du repo (à ajouter au .gitignore)

```gitignore
# Données locales sensibles
*.db
*.sqlite
.env
*.env.*

# Artefacts d'audit
temp_*.json
final_audit_report.*
matrice_content.*
docs_content.txt
matrice_classement_clients.xlsx

# Dossiers de données client
Archives_Documentaires/
jobs/

# Python
__pycache__/
*.pyc
*.pyo

# Logs
logs/
*.log
```

---

## Actions prioritaires

| Priorité | Action | Responsable | Délai |
|---|---|---|---|
| 🔴 CRITIQUE | Supprimer `Archives_Documentaires/` du repo | Admin Power Platform | Immédiat |
| 🔴 CRITIQUE | Supprimer `matrice_classement_clients.xlsx` du repo | Product Owner | Immédiat |
| 🔴 CRITIQUE | Vérifier et purger `jobs/` si commis | Admin Power Platform | Immédiat |
| 🟡 ÉLEVÉ | Auditer `src/api/` pour secrets en clair | RSSI | 1 semaine |
| 🟡 ÉLEVÉ | Configurer DLP Power Platform en environnement TEST | Admin Power Platform | 2 semaines |
| 🟢 MOYEN | Valider tous les YAML avec `validate_copilot_yaml.py` | Développeur | 1 semaine |

---

*Document généré le 2026-06-03 — à revalider à chaque sprint*
