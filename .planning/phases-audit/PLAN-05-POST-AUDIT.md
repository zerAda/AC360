# PLAN.md — Phase 5: Post-Audit

**Phase:** 5/5 | **Requirements:** 3 | **Status:** Pending

## Goal

Vider les fichiers uploadés et permettre un nouvel audit propre.

## Deliverables

| # | Deliverable | Requirements |
|---|------------|----------------|
| 1 | PDF supprimés après audit | POST-01 |
| 2 | Excel supprimés après audit | POST-02 |
| 3 | Nouvel audit possible | POST-03 |

## Execution Steps

### Step 1: Vider les Fichiers PDF

1. Après audit terminé, lister les PDF uploadés
2. Supprimer les fichiers PDF du dossier temporaire
3. Vider les variables contenant les données PDF en mémoire

### Step 2: Vider les Fichiers Excel

1. Après audit terminé, lister les Excel uploadés
2. Supprimer les fichiers Excel du dossier temporaire
3. Vider les variables contenant les données Excel en mémoire

### Step 3: Réinitialiser l'État

1. Réinitialiser les compteurs (progression, stats)
2. Vider les tableaux de résultats
3. Réinitialiser l'interface (vider la grille, les totaux)

### Step 4: Permettre Nouvel Audit

1. Réactiver le bouton "Lancer l'audit"
2. Réactiver le bouton d'upload de fichiers
3. S'assurer qu'aucune donnée de l'audit précédent ne persiste

### Step 5: Sécurité

1. Confirmer avant suppression (optionnel)
2. Vérifier que seuls les fichiers temporaires sont supprimés
3. Ne jamais supprimer les fichiers source originaux

## Success Criteria

- [ ] PDF uploadés supprimés après audit
- [ ] Excel uploadés supprimés après audit
- [ ] Nouvel audit peut être lancé proprement
- [ ] Aucune donnée de l'audit précédent ne persiste

## Blockers

(None identified)

---

*Plan created: 2026-04-28*
