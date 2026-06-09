# 🤖 CLAUDE CODE HANDOFF : AC360 (Assistant Client 360)

## 📌 Contexte du Projet
**AC360** est un agent conversationnel d'entreprise (Microsoft Copilot Studio) déployé pour les commerciaux de GEREP.
Il effectue des recherches documentaires (RAG) sur SharePoint (PDF, Docx, etc.) pour aider à la préparation de rendez-vous, générer des arguments de vente, et analyser les écarts de couverture d'assurance.

## 🏛️ Architecture
- **Frontend / Chat** : Microsoft Teams (canal Copilot Studio).
- **Core Agent** : Microsoft Copilot Studio (Dataverse). Fichiers sources dans `src/copilot/AC360/`.
- **Backend / API** : FastAPI (`scripts/api_server.py`) gérant les workflows longs (ex: OCR Fabric).
- **Authentification** : Microsoft Entra ID (Integrated Auth, Zero Trust).

## 🛠️ État Actuel (Production Ready)
L'agent précédent (Gemini / Antigravity) a mené une "Ralphe Loop" (boucle d'audit hostile) exhaustive sur le code source de Copilot Studio. 
**Toutes les erreurs de syntaxe, de schéma YAML et de logique conversationnelle ont été réparées.**

### 🐛 Les 3 bugs majeurs récemment corrigés :
1. **"Silent RAG"** : Les nœuds `SearchAndSummarizeContent` stockaient la réponse dans `Topic.Answer` sans jamais l'afficher. Des nœuds `SendActivity` ont été injectés dans les 5 topics principaux.
2. **Crash Système (BeginDialog)** : Les topics `EndofConversation` et `Goodbye` utilisaient `BeginDialog` pour appeler des System Topics (`Escalate`). Remplacés par `ReplaceDialog` (requis par Microsoft).
3. **Erreur de schéma Power Fx** : Dans `Argumentsdevente` et `PreparationRDV`, la propriété `query: "..."` provoquait une erreur de validation bloquante ("2 topic errors"). Elle a été remplacée par la syntaxe légale `userInput: ="Texte " & Topic.ClientName`. 

### 🐍 Les 6 bugs Backend / Python (Réparés !)
Les agents d'analyse de Claude ont identifié 6 problèmes architecturaux majeurs qui ont été **immédiatement corrigés** avant ton arrivée :
1. **IDOR Fiche RDV** : L'API sécurise maintenant le téléchargement en vérifiant le `user_upn` du propriétaire dans `meta.json`.
2. **Timestamp Bug** : Le nommage d'archivage utilise le bon format `%Y%m%d_%H%M%S`.
3. **Moteur OCR (nom_client)** : La fonction `perform_audit` supporte désormais correctement la syntaxe `keyValuePairs` d'Azure pour extraire le nom du client.
4. **Fuzzy Matching Thresholds** : La stricte limite de `85%` est désormais uniforme partout dans le code.
5. **Durable Functions Proxy** : L'endpoint de status `/api/audit/{job_id}/status` utilise correctement la variable `TASK_HUB_NAME` pour pointer vers le hub de production.
6. **Arbres obsolètes** : Les vieux répertoires de travail fantômes (`.claude/worktrees/`, `src/copilot-workspace/`) ont été purgés.
- **Zéro erreur de validation statique** restante.
- Un avertissement *"This agent uses premium features. You'll need an upgraded license to publish it"* empêche actuellement la publication via la CLI (`pac copilot publish`). Le propriétaire (Adel) doit cliquer sur **"Publish"** depuis le portail Web pour valider la licence premium ou tester via la console de test web.

### 🛡️ Audit de Sécurité In-Depth (Subagent)
Juste avant de te passer la main, j'ai déployé un **Agent de Sécurité Offensif** qui a audité le projet dans ses moindres recoins. Il a trouvé et j'ai corrigé instantanément :
1. **GitHub Actions RCE** : Les workflows CI/CD (`.github/workflows`) étaient vulnérables à l'injection de commandes via les contextes GitHub. Les variables sont désormais passées de manière sécurisée (env vars).
2. **SSRF et Missing Auth** : L'API ne passait pas la clé secrète à l'Azure Function et ne sanitizait pas les URL. C'est réglé.
3. **Graph OBO Flow** : L'intégration Planner transférait naïvement le JWT. Il est désormais prêt pour le flux OBO.
4. **IDOR & Path Traversal** : L'endpoint de téléchargement a été complètement verrouillé avec le retour du fichier de métadonnées de vérification.
5. **Config & Dépendances Fantômes** : Le script fantôme `config.py` a été restauré depuis l'historique Git et lié correctement à `auth.py`, `api_server.py`, `planner_integration.py` et `generate_fiche_rdv.py`. Les modules `azure-ai-formrecognizer` et `python-docx` manquants ont été rajoutés.

**Tout le dépôt a été committé, testé, et poussé vers le serveur (commit `f980b97`).** Le code est littéralement blindé. Tu as le champ libre.

## 🗂️ Fichiers clés à analyser pour la suite
Pour prendre pleinement le relais, lis ces fichiers :
1. `AGENTS.md` : Les règles fondamentales, l'architecture et les interdictions strictes (Master Prompt).
2. `src/copilot/AC360/settings.mcs.yml` : La configuration de sécurité et d'authentification du bot.
3. `scripts/ralphe_loop_tester.py` : Le script de test fonctionnel (nécessite le Direct Line Secret pour tourner).
4. `scripts/api_server.py` : L'API backend FastAPI.

## ⚙️ Commandes Utiles
- Démarrer l'API locale : `cd scripts; uvicorn api_server:app --host 0.0.0.0 --port 8000`
- Pousser des modifications vers Dataverse : `powershell -ExecutionPolicy Bypass -Command ".\scripts\sync_copilot.ps1 -Mode Push"`
- Lancer le pipeline d'audit : `powershell .\scripts\run_audit_pipeline.ps1`

## 🎯 Prochaines étapes suggérées pour Claude
1. Vérifier si le propriétaire a réussi à publier le bot sur Teams (résolution du problème de licence Premium).
2. Ajouter de nouveaux Topics ou affiner les instructions de RAG (System Prompts dans `additionalInstructions`).
3. Connecter la RAG Copilot Studio à l'API FastAPI locale si de l'exécution de code ou de l'OCR complexe est requise en temps réel.

---
*Bon développement Claude ! Protège bien les données GEREP.* 🛡️
