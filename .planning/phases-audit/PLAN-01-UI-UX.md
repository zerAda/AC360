# PLAN.md — Phase 1: UI/UX et Contrôle Audit

**Phase:** 1/5 | **Requirements:** 5 | **Status:** In Progress

## Goal

Ajouter le bouton d'annulation et la barre de progression à l'interface.

## Deliverables

| # | Deliverable | Requirements |
|---|------------|----------------|
| 1 | Bouton "Annuler" fonctionnel | UI-01, UI-02 |
| 2 | Barre de progression | UI-03, UI-04 |
| 3 | Message de fin | UI-05 |

## Execution Steps

### Step 1: Ajouter le Bouton Annuler

1. Ajouter un bouton "Annuler l'audit" dans l'interface
2. Le bouton doit être visible uniquement pendant le traitement
3. Implémenter la logique d'interruption (flag/thread cancel)
4. S'assurer que l'audit s'arrête proprement (pas de corruption)

### Step 2: Implémenter la Barre de Progression

1. Calculer le nombre total d'étapes/fichiers à traiter
2. Mettre à jour la barre à chaque étape complétée
3. Afficher le pourcentage d'avancement
4. Afficher le fichier/étape en cours de traitement

### Step 3: Ajouter le Message de Confirmation

1. Afficher un message quand l'audit se termine normalement
2. Afficher un message quand l'audit est annulé
3. Afficher un résumé (fichiers traités, écarts trouvés)

### Step 4: Tests UI

1. Tester l'annulation à différents moments (début, milieu, fin)
2. Vérifier que la progression est fluide
3. Vérifier que les messages sont clairs

## Success Criteria

- [ ] Bouton "Annuler" visible et fonctionnel
- [ ] L'audit s'arrête proprement quand on clique annuler
- [ ] Barre de progression visible avec %
- [ ] Progression mise à jour en temps réel
- [ ] Message de confirmation à la fin

## Blockers

(None identified)

---

*Plan created: 2026-04-28*
