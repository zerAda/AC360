# Mémo Responsable — Décision Go/No-Go

## Contexte

**Date** : 28 Avril 2026
**De** : Équipe projet POC
**À** : Direction / Responsable
**Objet** : Lancement POC Assistant Client 360

---

## Problème Actuel

Nos équipes commerciales passent **30 à 60 minutes** pour préparer chaque rendez-vous client. La recherche dans les dossiers SharePoint est manuelle et inefficace.

**Impact** : Temps perdu, risque d'oublier des informations clés, préparation incomplète avant les rendez-vous.

---

## Opportunité

Copilot Studio permet de créer un agent conversationnel connecté aux dossiers SharePoint existants. Les commerciaux peuvent poser des questions en langage naturel et obtenir des réponses synthétisées instantanément.

---

## Solution Proposée

**Agent "Assistant Client 360"** via Copilot Studio + SharePoint (Scénario A uniquement).

### Ce que fait l'agent

1. **Résumé de dossier** : "Résume-moi le dossier du client ABC"
2. **Recherche documentaire** : "Quel est le dernier contrat ?"
3. **Préparation rendez-vous** : "Prépare-moi une synthèse"
4. **Points d'attention** : "Quels sont les risques ?"
5. **Génération mail** : "Rédige-moi un mail de suivi"

### Ce que NE fait PAS l'agent

- Pas d'accès à des données hors SharePoint
- Pas de modification de données
- Pas d'automatisation complexe
- Pas d'outil externe

---

## Périmètre POC

| Élément | Détail |
|---------|--------|
| Dossiers clients | 10-20 maximum |
| Bibliothèques | 1-2 |
| Utilisateurs pilotes | 3-5 |
| Cas d'usage | 3-5 |
| Durée | 2 semaines |
| Budget | Temps équipe uniquement |

---

## Valeur Métier

| Métrique | Avant | Après | Amélioration |
|---------|-------|-------|--------------|
| Temps de préparation | 45 min | 10 min | -78% |
| Réponses useful | - | >80% | - |
| Satisfaction commerciale | - | >4/5 | - |

---

## Sécurité

- ✅ Permissions SharePoint existantes utilisées
- ✅ Checklist sécurité SharePoint de base
- ✅ Tests de permissions avec plusieurs profils
- ✅ Validation IT requise avant extension

**Points vérifiés** :
- Droits des commerciaux pilotes
- Liens de partage nettoyés
- Documents sensibles exclus

---

## Effort Estimatif

| Ressource | Estimation |
|-----------|-------------|
| Chef de projet | 0.5 ETP (10 jours) |
| Tech Lead | 0.5 ETP (10 jours) |
| Commercial (nettoyage) | 1 jour |
| IT (permissions) | 0.25 ETP |
| **Total** | ~0.3 ETP sur 2 semaines |

---

## Décision Demandée

Nous proposons de lancer ce POC pour démontrer rapidement la valeur métier.

**Merci de valider :**

- [ ] **Go** — Lancer le POC
- [ ] **Go avec modifications** — Préciser ci-dessous
- [ ] **No-Go** — Reason ci-dessous

### Commentaires

---

### Signature

| Rôle | Nom | Date | Signature |
|------|-----|------|-----------|
| Responsable | | | |
| Chef de projet | | | |

---

*Document créé : 2026-04-28 - Mémo Responsable*