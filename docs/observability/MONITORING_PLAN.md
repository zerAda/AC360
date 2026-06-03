# Plan de Monitoring — AC360

> **Version** : 1.0  
> **Date** : 2026-06-03  
> **Propriétaire** : Admin Power Platform + Équipe Digital  
> **Révision** : Mensuelle

---

## Objectifs du monitoring

1. **Disponibilité** : Détecter toute interruption de service AC360
2. **Performance** : Identifier les dégradations de latence
3. **Qualité** : Mesurer la satisfaction utilisateur et le taux de fallback
4. **Sécurité** : Détecter les incidents DLP et les échecs d'authentification
5. **Conformité** : Garantir qu'aucune donnée client n'est loguée

---

## 1. Métriques Copilot Studio Analytics

### Métriques principales à suivre

| Métrique | Description | Seuil alerte | Fréquence lecture |
|---|---|---|---|
| **Conversations/jour** | Nombre de conversations démarrées | < 5 (possible problème d'accès) | Quotidienne |
| **Taux de satisfaction** | % de réponses notées positivement par les utilisateurs | < 70% → action requise | Hebdomadaire |
| **Taux de fallback** | % de messages renvoyés au topic Fallback (non compris) | > 15% → améliorer les topics | Hebdomadaire |
| **Taux d'escalade** | % de conversations escaladées vers un humain | > 20% → réviser les sujets couverts | Hebdomadaire |
| **Top intents (topics)** | Topics les plus utilisés | — | Mensuelle |
| **Taux d'erreur** | % de conversations terminées en erreur | > 5% → alerte | Quotidienne |
| **Latence moyenne** | Temps de réponse moyen du bot | > 5 secondes → alerte | Quotidienne |
| **Utilisateurs uniques** | Nombre d'utilisateurs distincts | — | Mensuelle |

### Dashboard Copilot Analytics recommandé

```
Copilot Studio → Analytics → Overview
Onglets clés :
- Sessions (vue globale)
- Topics (performances par topic)
- Satisfaction (CSAT)
- Escalation (transfert vers humain)
```

---

## 2. Application Insights — API Python (si activée)

### Métriques à tracker

| Métrique | Description | Seuil alerte |
|---|---|---|
| **Requests/heure** | Nombre d'appels API | — (baseline à établir) |
| **Taux d'erreur HTTP** | % de réponses 4xx / 5xx | > 5% → alerte |
| **Latence P95** | 95e percentile du temps de réponse | > 10 secondes → alerte |
| **Durée des jobs d'audit** | Temps de traitement PDF/Excel | > 120 secondes → alerte |
| **Erreurs JWT** | Échecs de validation de token | > 3 consécutifs → alerte RSSI |
| **Codes 500** | Erreurs serveur internes | Toute occurrence → alerte |

### Configuration Application Insights recommandée

```python
# Dans app.py (API Python)
from applicationinsights import TelemetryClient
tc = TelemetryClient(APPINSIGHTS_INSTRUMENTATIONKEY)

# Logger les événements sans données client
tc.track_event('AuditJobStarted', {'job_id': job_id, 'duration_ms': duration})
tc.track_exception()  # Uniquement les exceptions techniques
```

> ⚠️ **IMPORTANT** : Ne jamais logger de noms de clients, contenu de documents, ou données d'identification.

---

## 3. Alertes à configurer

### Alertes prioritaires (P1 — Critique)

| Alerte | Condition | Canal | Destinataire |
|---|---|---|---|
| **Bot indisponible** | 0 conversation réussie en 30 min pendant les heures ouvrées | Teams / Email | Admin PP + DSI |
| **Taux d'erreur critique** | > 20% d'erreurs sur 15 minutes | Teams / Email | Admin PP |
| **Incident DLP** | Violation DLP détectée (connecteur non autorisé) | Email | RSSI + Admin PP |
| **Échecs auth répétés** | > 3 échecs JWT consécutifs | Email | RSSI |
| **Erreur 500 API** | Toute erreur 500 (si API activée) | Teams | DEV + Admin PP |

### Alertes secondaires (P2 — Important)

| Alerte | Condition | Canal | Destinataire |
|---|---|---|---|
| **Latence dégradée** | > 5 secondes de latence moyenne sur 10 min | Teams | Admin PP |
| **Taux fallback élevé** | > 15% de fallback sur 1 heure | Teams | Product Owner |
| **Satisfaction basse** | Score CSAT < 60% sur la journée | Email | Product Owner |
| **Latence API** | P95 > 10s sur 15 minutes (si API) | Teams | DEV |

### Alertes de sécurité (P1 — Sécurité)

| Alerte | Condition | Canal | Destinataire |
|---|---|---|---|
| **Injection de prompt** | Patterns d'injection détectés en volume | Email | RSSI |
| **Accès non autorisé** | 401/403 répétés depuis même IP | Email | RSSI + OWN_ENTRA |
| **DLP incident** | Log DLP violation | Email urgent | RSSI |

---

## 4. Dashboard Power BI recommandé

### Pages recommandées

```
Page 1 — Vue Executive
- KPIs : conversations/semaine, satisfaction %, taux adoption
- Graphique tendance : conversations sur 30 jours

Page 2 — Performance opérationnelle
- Topics les plus utilisés (bar chart)
- Taux de fallback par topic
- Latence moyenne par topic

Page 3 — Sécurité & Conformité
- Incidents DLP (si applicable)
- Échecs d'authentification
- Uptime mensuel

Page 4 — Feedback utilisateur
- CSAT score sur 30 jours
- Top plaintes / escalades
- Comparaison semaine/semaine
```

---

## 5. Logs — Ce qu'il faut et ne faut pas collecter

### ✅ Logs AUTORISÉS

| Type de log | Contenu | Rétention |
|---|---|---|
| Conversation metadata | Session ID, durée, topic déclenchée, résultat (succès/fallback) | 90 jours |
| Erreurs techniques | Stack trace, code erreur HTTP, exception type | 90 jours |
| Métriques de performance | Latence, durée traitement | 90 jours |
| Logs DLP | Type de violation, connecteur impliqué, timestamp | 180 jours |
| Logs d'authentification | Succès/échec, UPN hashé, timestamp | 90 jours |

### ❌ Logs INTERDITS

| Type de donnée | Raison |
|---|---|
| Contenu des questions utilisateurs | Peut contenir des noms de clients |
| Contenu des réponses générées | Contient des données client SharePoint |
| Contenu des documents SharePoint | Données confidentielles client GEREP |
| Noms de clients dans les logs | Données nominatives — RGPD |
| Tokens JWT complets | Secret — permet l'usurpation d'identité |
| Clés API ou secrets | Secret — voir SECRET_ROTATION.md |

---

## 6. Rétention des logs

| Source | Durée de rétention | Justification |
|---|---|---|
| Copilot Analytics | 90 jours (maximum configuré) | Conformité et audit opérationnel |
| Application Insights | 90 jours | Standard Azure |
| Logs DLP Power Platform | 180 jours | Conformité réglementaire |
| Logs Entra ID (sign-in) | 90 jours (standard Entra) | Audit sécurité |
| Logs d'audit Power Platform | 365 jours | Gouvernance |

> **Rappel RGPD** : Toute donnée personnelle (UPN, nom d'utilisateur) dans les logs doit avoir une base légale et être couverte par la politique de confidentialité GEREP.

---

## 7. Revues périodiques

| Revue | Fréquence | Participants | Livrables |
|---|---|---|---|
| Métriques opérationnelles | Hebdomadaire | Admin PP | Rapport dans Teams |
| Satisfaction et adoption | Mensuelle | PO + Équipe commerciale | Rapport Power BI |
| Sécurité et DLP | Mensuelle | RSSI + Admin PP | Rapport sécurité |
| Revue complète | Trimestrielle | PO + RSSI + DSI | Rapport executive |

---

*Plan de monitoring v1.0 — À activer dès le déploiement en TEST*
