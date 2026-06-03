# Actions & Connecteurs — Review de Sécurité AC360

> **Version** : 1.0  
> **Date** : 2026-06-03  
> **Approbateur** : RSSI + Admin Power Platform  
> **Révision** : À chaque ajout ou modification d'action/connecteur

---

## Contexte

Ce document recense chaque action et connecteur utilisé dans AC360, évalue les risques associés et documente les décisions de gouvernance. Il est particulièrement important pour les connecteurs en **Preview**, qui sont soumis à une surveillance renforcée.

---

## Principe de sécurité

1. **Minimiser la surface d'attaque** : N'activer que les connecteurs strictement nécessaires
2. **Gouvernance DLP** : Chaque connecteur doit être classifié dans la politique DLP
3. **Connecteurs Preview** : Soumis à une gouvernance renforcée et à une approbation RSSI
4. **Données sortantes** : Aucune donnée client ne doit sortir du périmètre Microsoft 365

---

## Tableau des actions et connecteurs

| Action / Connecteur | Preview ? | Nécessité | Auth | Données sortantes | Risque | Statut | DLP requise | Action requise |
|---|---|---|---|---|---|---|---|---|
| **WorkIQ SharePoint MCP** | ✅ OUI — Preview | Essentielle — Accès aux documents clients SharePoint | OAuth 2.0 (Entra ID — utilisateur connecté) | Aucune — lecture seule dans tenant M365 | 🟡 MOYEN — Connecteur Preview non certifié | ⚠️ NÉCESSITE GOUVERNANCE DLP | Classer dans "Business" DLP — Approuver en PROD | Valider classification DLP + approbation RSSI |
| **WorkIQ User MCP** | ✅ OUI — Preview | Utile — Informations utilisateur connecté (nom, email) | OAuth 2.0 (Entra ID — utilisateur connecté) | Aucune — metadata utilisateur uniquement | 🟡 MOYEN — Connecteur Preview non certifié | ⚠️ NÉCESSITE GOUVERNANCE DLP | Classer dans "Business" DLP — Approuver en PROD | Valider si vraiment nécessaire vs claims JWT |
| **SharePoint Search (knowledge source)** | ❌ NON — GA | Essentielle — Source RAG principale | OAuth 2.0 (Entra ID — utilisateur connecté) | Aucune — contenu retourné dans la session uniquement | 🟢 FAIBLE — Connecteur certifié Microsoft | ✅ AUTORISÉ | Classer dans "Business" DLP | Maintenir — aucune action requise |
| **Microsoft Teams (publication)** | ❌ NON — GA | Essentielle — Canal de déploiement principal | OAuth 2.0 (Entra ID) | Aucune | 🟢 FAIBLE | ✅ AUTORISÉ | Classer dans "Business" DLP | Maintenir |
| **API Python (Azure App Service)** | N/A — Custom | Expérimentale — Audit PDF/Excel | JWT RS256 (Entra ID) | Fichiers uploadés temporairement (24h max) | 🟡 ÉLEVÉ — Non activée en PROD | ⚠️ EXPÉRIMENTAL — NON ACTIVÉ | Gouvernance HTTP connector requise | Ne pas activer en PROD sans validation RSSI complète |
| **HTTP (Webhook Teams)** | ❌ NON — GA | Optionnelle — Notifications internes | Webhook URL | URL de destination uniquement | 🟡 MOYEN — Connector HTTP générique | ⚠️ SOUS SURVEILLANCE | Approuver explicitement ou bloquer par DLP | Valider si nécessaire ou remplacer par connecteur Teams natif |

---

## Analyse des connecteurs Preview

### WorkIQ SharePoint MCP (Preview)

**Risques spécifiques aux connecteurs Preview** :
- Non certifié Microsoft — comportement peut changer sans préavis
- Peut être retiré du marketplace sans préavis
- Pas de SLA garanti
- Scope d'accès potentiellement plus large que nécessaire

**Mesures de mitigation** :
- [ ] Vérifier les scopes OAuth demandés par le connecteur
- [ ] Tester le comportement avec un utilisateur non autorisé
- [ ] Monitorer les mises à jour du connecteur dans le marketplace
- [ ] Prévoir un connecteur alternatif (SharePoint Search natif) en cas de retrait

**Classification DLP recommandée** : `Business` (pas `Non-Business`)

---

### WorkIQ User MCP (Preview)

**Question stratégique** : Est-ce réellement nécessaire ?

Les informations utilisateur (nom, email, UPN) sont disponibles via les claims du JWT Entra ID. Si l'usage se limite à afficher le nom de l'utilisateur connecté, ce connecteur n'est pas nécessaire.

**Recommandation** : Évaluer la nécessité réelle. Si uniquement utilisé pour les claims basiques, **désactiver le connecteur** et utiliser les variables système Copilot Studio (`System.User.DisplayName`).

---

## Connecteurs interdits

Les connecteurs suivants sont **explicitement interdits** dans AC360 :

| Connecteur | Raison du blocage |
|---|---|
| OneDrive Personnel | Données hors périmètre GEREP |
| Gmail / Google Workspace | Données hors périmètre M365 |
| Outlook (écriture) | AC360 ne doit pas envoyer d'emails autonomement |
| HTTP générique (non approuvé) | Surface d'attaque externe non contrôlée |
| Connectors tiers non approuvés | Non gouvernés par la DLP GEREP |

---

## Flux de données — Vue d'ensemble

```
Utilisateur (Teams)
      │
      ▼ [OAuth JWT RS256]
Copilot Studio AC360
      │
      ├──→ WorkIQ SharePoint MCP ──→ SharePoint (Dossiers_Clients_POC)
      │         [OAuth — user identity]        [Lecture seule]
      │
      ├──→ WorkIQ User MCP ──→ Entra ID
      │         [OAuth — user claims]
      │
      └──→ SharePoint Search ──→ SharePoint (knowledge source)
                [OAuth — user identity]

(optionnel / expérimental)
      │
      └──→ API Python (Azure App Svc) ──→ Azure OCR / Fichiers temporaires
                [JWT RS256]                    [Suppression 24h]
```

**Données qui ne sortent jamais du périmètre M365** :
- Contenu des documents clients
- Données personnelles des clients GEREP
- Informations contractuelles sensibles

---

## Checklist de validation — Avant activation PROD

- [ ] Tous les connecteurs Preview approuvés par RSSI
- [ ] Classification DLP vérifiée pour chaque connecteur
- [ ] Scopes OAuth documentés et minimaux
- [ ] Test avec utilisateur non autorisé — accès refusé confirmé
- [ ] Monitoring des erreurs de connecteurs configuré
- [ ] Plan de fallback si connecteur Preview retiré

---

## Historique des révisions

| Date | Connecteur | Action | Raison | Approuvé par |
|---|---|---|---|---|
| 2026-06-03 | WorkIQ SharePoint MCP | Ajout — sous surveillance | Nécessaire pour RAG | À valider RSSI |
| 2026-06-03 | WorkIQ User MCP | Ajout — sous évaluation | Potentiellement remplaçable | À valider RSSI |
| 2026-06-03 | SharePoint Search | Approuvé | Source RAG principale | Product Owner |

---

*Document maintenu par l'Admin Power Platform — Révision RSSI requise avant PROD*
