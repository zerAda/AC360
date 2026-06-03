# Runbook Incidents — AC360

> **Version** : 1.0  
> **Date** : 2026-06-03  
> **Propriétaire** : Support N2 + Admin Power Platform  
> **Distribution** : Équipe support, Admin PP, RSSI

---

## Matrice de sévérité

| Sévérité | Définition | Délai de réponse | Délai de résolution |
|---|---|---|---|
| **P1 — Critique** | Service indisponible / Incident sécurité | 15 minutes | 2 heures |
| **P2 — Élevé** | Fonctionnalité dégradée, plusieurs utilisateurs impactés | 30 minutes | 4 heures |
| **P3 — Moyen** | Comportement incorrect, utilisateur unique | 2 heures | 24 heures |
| **P4 — Faible** | Question, amélioration, documentation | 24 heures | 1 semaine |

---

## Scénario 1 — Bot ne répond plus

**Sévérité** : P1  
**Symptômes** : Les utilisateurs voient une erreur dans Teams ou le bot ne répond plus du tout.

### Diagnostic

```
1. Vérifier Copilot Studio → Agent AC360 → Status
   → Le bot est-il publié ? (Published = vert)

2. Vérifier Power Platform → Environnement PROD → Service health
   → Y a-t-il une panne Power Platform annoncée ?
   → Vérifier https://status.microsoft.com

3. Vérifier les logs Application Insights (si API activée)
   → Y a-t-il des erreurs 500 en masse ?

4. Vérifier Teams → Apps → AC360
   → Le bot apparaît-il dans la liste ?
   → Essayer de l'ouvrir dans un navigateur (webchat)
```

### Résolution

```
Si Copilot Studio non publié :
→ Republier l'agent (Publish → Publish now)
→ Attendre 5 minutes et re-tester

Si panne Microsoft :
→ Attendre résolution Microsoft
→ Communiquer aux utilisateurs via Teams (canal Digital GEREP)
→ Ouvrir un ticket Microsoft si SLA critique

Si erreur applicative :
→ Rollback vers la version précédente (voir DEPLOYMENT_RUNBOOK.md)
→ Notifier RSSI si incident de sécurité suspecté
```

**Escalade** : Admin PP → DSI si non résolu en 1h

---

## Scénario 2 — Sources SharePoint non accessibles

**Sévérité** : P2  
**Symptômes** : AC360 répond "Je n'ai pas trouvé d'information" pour des documents qui existent.

### Diagnostic

```
1. Vérifier SharePoint → Site dev-assistant-client-360
   → Le site est-il accessible manuellement (navigateur) ?
   → Y a-t-il des erreurs SharePoint ?

2. Vérifier la Connection Reference SharePoint dans Power Platform
   → Admin Center → Environnement → Connections
   → La connexion SharePoint est-elle verte (Connected) ?

3. Vérifier les permissions du compte de service (si utilisé)
   → Entra ID → App Registrations → AC360-PROD
   → Les scopes SharePoint sont-ils toujours accordés ?

4. Vérifier que la knowledge source pointe vers le bon site
   → Copilot Studio → Knowledge → SharePoint URL
```

### Résolution

```
Si connection SharePoint déconnectée :
→ Admin Center → Connections → SharePoint → Reconnecter
→ Republier l'agent

Si permissions révoquées :
→ Owner SharePoint → Restaurer les permissions du compte de service
→ Ou re-consentir les scopes OAuth dans Entra ID

Si URL knowledge source incorrecte :
→ Copilot Studio → Knowledge → Modifier l'URL
→ Republier l'agent
```

**Escalade** : Admin PP → Owner SharePoint → OWN_ENTRA

---

## Scénario 3 — Action Copilot échoue (WorkIQ, connecteur)

**Sévérité** : P2  
**Symptômes** : AC360 renvoie une erreur lors d'une action spécifique (ex: résumé dossier).

### Diagnostic

```
1. Identifier l'action en échec (quel topic ?)
2. Vérifier Power Platform → Connections → WorkIQ SharePoint MCP
   → Status de la connexion ?
3. Vérifier les logs Application Insights ou Power Automate (si flow impliqué)
4. Tester l'action manuellement depuis Copilot Studio (Test panel)
5. Vérifier si Microsoft a mis à jour le connecteur Preview
   → Power Platform Admin → Connectors → WorkIQ
```

### Résolution

```
Si connexion déconnectée :
→ Reconnecter le connecteur (Power Platform Admin → Connections)
→ Republier l'agent

Si connecteur Preview mis à jour avec breaking change :
→ Analyser les changements de l'API du connecteur
→ Adapter les paramètres d'appel dans le topic
→ Contacter Microsoft si comportement anormal

Si l'action retourne des erreurs de scope :
→ Re-consentir les permissions OAuth
→ Notifier RSSI
```

---

## Scénario 4 — Erreur auth / JWT rejeté

**Sévérité** : P1 (si massif) / P2 (si isolé)  
**Symptômes** : Les utilisateurs voient "Authentification requise" ou une erreur 401/403 en boucle.

### Diagnostic

```
1. Vérifier Entra ID → Sign-in logs
   → Y a-t-il des échecs en masse ?
   → Quel est le message d'erreur exact ? (AADSTS codes)

2. Vérifier App Registration AC360-PROD
   → Client Secret non expiré ?
   → Redirect URIs correctes ?
   → Scopes accordés ?

3. Vérifier que le groupe AD "AC360-Users" est actif
   → Entra ID → Groups → AC360-Users → Members

4. Vérifier si une politique de Conditional Access bloque l'accès
```

### Résolution

```
Si Client Secret expiré :
→ Suivre SECRET_ROTATION.md → Procédure ENTRA_CLIENT_SECRET
→ Urgent : Créer nouveau secret, déployer, tester

Si utilisateur hors groupe AD :
→ Owner Entra ID → Ajouter l'utilisateur au groupe AC360-Users

Si Conditional Access bloque :
→ OWN_ENTRA → Vérifier et ajuster la politique CA
→ Notifier RSSI si changement de politique intentionnel
```

**Escalade immédiate si > 5 utilisateurs bloqués** : Admin PP → OWN_ENTRA → DSI

---

## Scénario 5 — Suspicion de fuite de données

**Sévérité** : P1 — Incident de sécurité critique  
**Symptômes** : Un utilisateur rapporte avoir reçu des données d'un autre client, ou un log suspect est identifié.

### PROCÉDURE D'URGENCE

```
⚠️ NE PAS ATTENDRE — Agir immédiatement

1. ISOLER : Dépublier l'agent immédiatement
   Copilot Studio → Agent AC360 → Settings → Depublish
   
2. NOTIFIER : Contacter RSSI (appel direct si possible)
   rssi@gerep.fr — Sujet : [URGENT SÉCURITÉ] Suspicion fuite données AC360
   
3. PRÉSERVER LES PREUVES : Exporter les logs disponibles
   - Copilot Analytics (conversations du jour)
   - Entra ID Sign-in logs
   - Power Platform Admin logs
   
4. ANALYSER : Identifier le périmètre exact
   - Quelles données ? Quel client ? Quel utilisateur ?
   - Depuis quand ? Combien de fois ?
   
5. NOTIFIER DPO si données personnelles impliquées
   → Délai légal : 72h max pour notification CNIL si violation confirmée
   
6. NE PAS REDÉPLOYER sans approbation RSSI
```

**Contact RSSI** : rssi@gerep.fr — Si pas de réponse en 15min : appel direct

---

## Scénario 6 — Hallucination signalée

**Sévérité** : P2  
**Symptômes** : Un utilisateur reporte une réponse inventée (non sourcée depuis SharePoint).

### Diagnostic

```
1. Récupérer le prompt exact et la réponse obtenue
2. Vérifier si `useModelKnowledge = false` est toujours configuré
3. Vérifier si la réponse cite des sources
   → Si non citée : hallucination confirmée
4. Vérifier si Microsoft a mis à jour le modèle de langage
   → optInUseLatestModels : actif ?
```

### Résolution

```
Si useModelKnowledge a été activé par erreur :
→ Remettre à false immédiatement
→ Republier l'agent

Si hallucination malgré useModelKnowledge=false :
→ Analyser la réponse exacte — peut-être une déduction légitime mal formulée
→ Améliorer le prompt système du topic concerné
→ Signaler à Microsoft si comportement anormal du modèle

Action préventive :
→ Mettre à jour le prompt système pour forcer les citations
→ Ajouter un contrôle de citation dans la réponse du topic
```

---

## Scénario 7 — Mauvais client dans la réponse

**Sévérité** : P1  
**Symptômes** : AC360 mélange les données de deux clients dans une réponse.

### Diagnostic

```
1. Récupérer le prompt exact et la réponse complète
2. Vérifier si l'utilisateur a posé une question multi-client
   → "Résume Alpha et Beta" → AC360 devrait refuser
3. Vérifier si deux dossiers SharePoint portent des noms similaires
   → Ambiguïté de recherche sémantique
4. Vérifier les sources citées dans la réponse
```

### Résolution

```
Si l'utilisateur a contourné la règle mono-client :
→ Renforcer le topic de clarification et de refus multi-client
→ Documenter le cas dans RED_TEAM_PROMPTS.md

Si ambiguïté SharePoint :
→ Informer l'utilisateur de la demande de clarification
→ Améliorer le topic Clarification Client

Si cross-contamination confirmée (scénario 5) :
→ Activer immédiatement le Scénario 5
```

---

## Scénario 8 — Pipeline audit échoue (API Python)

**Sévérité** : P3 (fonctionnalité expérimentale)  
**Symptômes** : Le topic LancerAudit retourne une erreur ou le job reste bloqué.

### Diagnostic

```
1. Vérifier Azure App Service → Logs en temps réel
2. Vérifier le job_id retourné → Appeler GET /jobs/{job_id}
3. Vérifier les limites de fichiers (taille max)
4. Vérifier la validité du JWT envoyé à l'API
5. Vérifier Azure OCR (si utilisé) → Quota dépassé ?
```

### Résolution

```
Si job bloqué > 120 secondes :
→ Supprimer le job (cleanup)
→ Demander à l'utilisateur de réessayer avec un fichier plus petit

Si erreur JWT :
→ L'utilisateur doit se reconnecter (token expiré)
→ Si systématique : vérifier la configuration auth de l'API

Si quota Azure OCR dépassé :
→ Azure Portal → Cognitive Services → Augmenter le quota
→ Informer PO du besoin de mise à niveau
```

---

## Scénario 9 — Connecteur désactivé par DLP

**Sévérité** : P2  
**Symptômes** : Un connecteur (ex: WorkIQ) ne fonctionne plus — erreur DLP dans les logs.

### Diagnostic

```
1. Power Platform Admin Center → Data policies → AC360-DLP-Policy
2. Vérifier la classification du connecteur impliqué
3. Vérifier si une politique a été modifiée récemment (audit logs)
4. Identifier qui a modifié la politique DLP
```

### Résolution

```
Si connecteur reclassé par erreur :
→ RSSI + Admin PP → Reclasser correctement dans la politique DLP
→ Redéployer l'agent si nécessaire

Si désactivation intentionnelle (décision RSSI) :
→ Analyser l'impact sur les fonctionnalités AC360
→ Trouver un connecteur alternatif ou adapter les topics

Si désactivation par Microsoft (connecteur Preview retiré) :
→ Analyser les alternatives disponibles
→ Adapter l'architecture si nécessaire (prévu dans ACTIONS_SECURITY_REVIEW.md)
```

---

## Contacts d'escalade

| Niveau | Contact | Délai |
|---|---|---|
| Support N1 | Équipe support IT GEREP | Immédiat |
| Support N2 | Admin Power Platform | 30 min |
| Sécurité | RSSI — rssi@gerep.fr | 15 min (P1) |
| Direction | DSI | 1h (P1 majeur) |
| Microsoft | Support Microsoft 365 (ticket) | Variable |

---

## Log des incidents

| Date | Sévérité | Scénario | Description | Résolution | Durée | Rapport |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

---

*Runbook v1.0 — Distribuer à l'équipe support avant déploiement PROD*
