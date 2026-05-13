# Assistant Client 360 — Cadrage Initial

## Problème Actuel

Les équipes commerciales passent trop de temps à rechercher des informations dans les dossiers clients SharePoint. Chaque dossier contient des dizaines de documents (contrats, propositions, comptes rendus, échanges) mais sans structure중앙isée permettant de répondre rapidement aux questions.
Les commerciaux doivent :
- naviguer manuellement dans les dossiers SharePoint
- ouvrir plusieurs documents pour trouver une information
- parcourir les archives pour retrouver un contrat ancien
- synthétiser les informations avant chaque rendez-vous
- rédigersouvent des mails de suivi manuellement

**Impact estimé** : 30-60 min por client avant rendez-vous uniquement pour la recherche documentaire.

## Utilisateurs Cibles

**Utilisateurs directs** :
- Commerciaux terrain (3-5 pilotes)
- Assistant(e)s commerciaux

**Bénéficiaires indirects** :
- Managers commerciaux (meilleure visibilité)
- Direction (KPI simplifiés)

## Bénéfices Attendus

1. **Réduction du temps de préparation** : gain estimé 20-40 min par dossier client
2. **Réponses rapides** : questions sur un client en quelques secondes
3. **Synthèses automatisées** : résumé avant rendez-vous en un clic
4. **Brouillons de mails** : génération basée sur les documents disponibles
5. **Points dattention** : identification rapide des risques ou points bloquants

## Limites du POC

- 10 à 20 dossiers clients maximum
- 1 à 2 bibliothèques SharePoint
- 3 à 5 utilisateurs pilotes
- 3 à 5 cas dusage métier uniquement
- Aucune modification de larchitecture existante
- Aucun outil externe à Microsoft 365 / Copilot Studio / SharePoint
- Pas de Microsoft Purview
- Pas dAzure AI Search
- Pas de refonte SharePoint

## Prérequis

1. **SharePoint** : dossiers clients existants dans une bibliothèque documentaire
2. **Licences** : Microsoft 365 Business/Enterprise pour les pilotes
3. **Copilot Studio** : accès au portail Copilot Studio
4. **Permissions** : droits SharePoint adaptés pour les pilotes
5. **Validation IT** : accord pour tester lagent avec des données réelles

## Risques Identifiés

| Risque | Probabilité | Impact | Mitigation |
|-------|------------|--------|------------|
| Permissions SharePoint trop larges | Haute | Moyen | Vérifier et nettoyer avant POC |
| Documents non structurés | Haute | Moyen | Nettoyage léger, nommage simple |
| Mauvaise compréhension des questions | Moyenne | Moyen | Prompt système adapté, tests |
| Mélange entre clients | Faible | Critique | Instructions claires, validation |
| Information manquante | Haute | Faible | Réponse "non trouvé" explicite |
| Fuite documentaire | Faible | Critique | Vérifier les permissions |

## Décisions à Faire Valider par le Responsable

1. **Validation du besoin** : Est-ce que le cas dusage correspond à la réalité commerciale ?
2. **Sélection des pilotes** : Quels commerciaux participent au POC ?
3. **Sélection des dossiers** : Quels clients/dossiers pour le test ?
4. **Site SharePoint cible** : Quelle bibliothèque ?
5. **Cas dusage prioritaires** : Les 3-5 cas sont-ils les bons ?
6. **Go/No-go sécurité** : Validation IT despermissions ?
7. **Calendrier** : Accord sur les 2 semaines ?
8. **Budget temps** : Disponibilité des équipes ?

## Hypothèses de Départ

- Les documents clients sont déjà stockés dans SharePoint
- Les commerciaux utilisent Microsoft 365 au quotidien
- Les droits SharePoint existants serviront de base de sécurité
- Lentreprise ne dispose pas de Microsoft Purview
- Lentreprise ne veut pas dAzure AI Search pour linstant
- Lobjectifest de tester rapidement la valeur métier

## Prochaines Étapes

1. Valider ce cadrage avec le responsable
2. Phase 1 : Vérification documentation Microsoft
3. Phase 2 : Architecture POC Scenario A

---

*Document créé : 2026-04-28 - Cadrage initial POC Assistant Client 360*