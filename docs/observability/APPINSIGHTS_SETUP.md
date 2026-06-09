# Intégration Application Insights — AC360

Ce document explique comment l'API Backend remonte ses télémétries et logs de sécurité vers Azure Application Insights pour le monitoring Enterprise.

## 1. Comment fonctionne le Middleware ?

Dans `scripts/api_server.py`, un middleware FastAPI (starlette) intercepte toutes les requêtes HTTP.
- Il mesure le temps d'exécution (processing time).
- Il récupère le code de statut HTTP.
- Si une clé `APPINSIGHTS_INSTRUMENTATIONKEY` est trouvée dans l'environnement, les logs sont structurés et formatés pour remonter dans les tableaux de bord Azure.
- Toutes les opérations sensibles (erreurs d'authentification, path traversal bloqué, rate-limit atteint) sont loguées via `log_security()`.

## 2. Configuration côté Azure

Pour visualiser ces logs dans un tableau de bord, l'équipe IT doit suivre ces étapes (temps estimé : 15 min) :

### Étape A : Créer la ressource Application Insights
1. Connectez-vous au portail Azure : [portal.azure.com](https://portal.azure.com).
2. Cherchez "Application Insights" dans la barre de recherche.
3. Cliquez sur **Créer**.
4. Renseignez :
   - Abonnement : *Votre abonnement GEREP*
   - Groupe de ressources : *ex: RG_AC360_Prod*
   - Nom : `ac360-api-insights`
   - Région : *France Central* (ou celle de vos ressources existantes)
   - Mode de ressource : Basé sur l'espace de travail (Workspace-based)
5. Cliquez sur **Vérifier + Créer** puis **Créer**.

### Étape B : Récupérer la clé d'instrumentation
1. Une fois la ressource créée, allez sur la page Vue d'ensemble (Overview).
2. Copiez la valeur du champ **Clé d'instrumentation** (Instrumentation Key) ou de la **Chaîne de connexion** (Connection String).

### Étape C : Configurer le backend AC360
Sur le serveur hébergeant l'API (FastAPI) :
1. Éditez le fichier `.env` de production.
2. Ajoutez la variable suivante :
```bash
APPINSIGHTS_INSTRUMENTATIONKEY=votre_cle_copiee_a_letape_B
```
3. Redémarrez le processus uvicorn/FastAPI.

## 3. Visualisation des données dans Azure

Dès que le backend redémarre avec la clé configurée :
- Allez dans votre ressource Application Insights -> **Performances** pour voir le temps de réponse moyen de l'endpoint `/api/audit`.
- Allez dans **Échecs (Failures)** pour visualiser les codes HTTP 4xx (bloqués par la sécurité) ou 5xx (erreurs internes).
- Allez dans **Journaux (Logs)** et tapez la requête Kusto suivante pour voir les alertes de sécurité de `safe_logger` :
```kusto
traces
| where message contains "SECURITY" or message contains "Path traversal"
| order by timestamp desc
```
