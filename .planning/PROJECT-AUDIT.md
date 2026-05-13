# Application d'Audit — PROJECT.md

## What This Is

Application d'audit automatisée qui compare des données entre des fichiers PDF (extraits de relevés bancaires) et des fichiers Excel (suivis internes). L'application identifie les écarts entre les deux sources pour réconcilier les transactions.

## Core Value

Fournir une analyse d'audit fiable et rapide en comparant automatiquement les données PDF et Excel, avec identification précise des écarts.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Bouton pour annuler l'audit en cours
- [ ] Barre de progression affichant l'état d'avancement
- [ ] Vidage des fichiers PDF et Excel après audit terminé
- [ ] Algorithmes optimisés (traitement trop lent actuellement)
- [ ] Dissociation nom société / IBAN (actuellement concaténés)
- [ ] Gestion des différences de nom entre PDF et Excel
- [ ] Ignorer les lignes de récap/sommes par groupe Excel
- [ ] Ignorer les lignes "bordereau" (tests des gestionnaires)
- [ ] Correction du total d'écart (Excel ≠ Dashboard)

### Out of Scope

- Intégration avec d'autres sources de données
- Export vers des formats autres que ceux existants
- Historique multi-audits (un audit à la fois)

## Context

L'application lit des fichiers PDF et Excel pour les comparer. Les données contiennent des noms de sociétés, des IBANs, des montants et des dates. Les gestionnaires utilisent des techniques comme les bordereaux et les récaps pour leurs propres calculs, mais ces lignes ne doivent pas être prises en compte dans l'analyse.

## Constraints

- **Tech Stack**: Langage existant à identifier
- **Performance**: Le traitement actuel est trop lent
- **Data Quality**: Noms de société peuvent différer entre PDF et Excel
- **Data Cleaning**: Lignes spécifiques à exclure (bordereau, récap)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Dissocier société/IBAN avant traitement | Données actuellement concaténées | — Pending |
| Exclure lignes "bordereau" | Ce sont des tests gestionnaires | — Pending |
| Exclure récaps/sommes Excel | Doublons avec données détaillées | — Pending |
| Optimiser algorithmes | Temps de traitement trop long | — Pending |

---

*Last updated: 2026-04-28 after audit requirements capture*
