# Gouvernance AC360

Ce document régit les règles de cycle de vie, les rôles et les processus de sécurité autour de l'assistant AC360.

## 1. Rôles et Responsabilités

| Rôle | Responsabilité | Entités Autorisées |
|---|---|---|
| **Product Owner** | Définition des règles métier (Topics) et matrice de classement. | Équipe Commerciale |
| **Architecte Copilot** | Maintien du code Copilot Studio (YAML), des prompts système et des flux (Topics). | Équipe IT / Dev |
| **Sécurité (RSSI/DPO)** | Validation des gates de sécurité, audits réguliers, RAG Policy. | DSI / Cyber |
| **Développeur Backend** | Maintien de l'API FastAPI et du pipeline OCR/Fabric. | Équipe IT / Dev |

## 2. Processus de Mise à Jour (ALM)

Toute modification apportée à AC360 (que ce soit via l'UI Copilot Studio ou le code local) doit suivre ce flux strict :

1. **Pull (Synchronisation Initiale)** : Exécution de `sync_copilot.ps1 -Mode Pull` pour rapatrier l'état cloud (et commiter sur Git).
2. **Modifications locales ou validation** : Modifications des scripts ou du comportement.
3. **Packaging / CI-CD** : Exécution de `package_release.ps1`.
   - *Bloquant* : Présence de secrets (`scan_secrets.ps1`).
   - *Bloquant* : `useModelKnowledge` détecté à `true` ou conflit Fallback (`validate_copilot_yaml.py`).
   - *Bloquant* : Échec des tests backend/OCR (`pytest`).
4. **Push / Déploiement** : Si le package est généré avec succès, l'administrateur peut faire un `sync_copilot.ps1 -Mode Push`.

## 3. Audits et Red-Teaming (Continuité de Sécurité)

La cible de posture de sécurité d'AC360 (à atteindre avant production) exige une surveillance continue :
- **Bimestriel** : Tentative de Jailbreak / Prompt Injection par un acteur interne indépendant. Les `additionalInstructions` du RAG doivent être testées (Domaine 7).
- **Semestriel** : Rotation des clés (Azure OCR, Secrets Fabric, JWT). Inscription dans le registre `docs/security/SECRET_ROTATION.md`.
- **En continu** : Scan PowerShell pour interdire l'ajout d'injections potentielles (`Invoke-Expression`).

## 4. Politique de Traitement des Données (RGPD)

- **Rétention bornée (30 jours)** : Les artefacts contenant potentiellement de la PII (documents téléchargés pour OCR, sorties OCR, brouillons FIC) sont conservés **30 jours** puis supprimés, à deux points d'application : la politique de cycle de vie Storage côté serveur (`managementPolicies`, `infra/main.bicep`) et le timer Functions `prune_jobs_dir`. Les journaux/télémétrie sont conservés **90 jours** (Log Analytics). La **fenêtre d'effacement effective est d'environ 37 jours** (soft-delete/versioning, arbitrage sécurité-opérationnelle assumé). **Sources canoniques** : `docs/governance/RGP-03-retention-policy.md` (artefacts) et `docs/governance/RGP-04-pii-in-logs-statement.md` (journaux) — ce document s'y réfère et n'introduit aucune autre valeur de rétention.
- **Logs Anonymisés** : L'API FastAPI utilise `safe_logger.py` pour masquer tout numéro de sécurité sociale ou donnée financière potentiellement captée.
- **Accès Délégué (Entra ID)** : L'IA ne voit *jamais* de documents que l'utilisateur n'aurait pas le droit d'ouvrir lui-même.
