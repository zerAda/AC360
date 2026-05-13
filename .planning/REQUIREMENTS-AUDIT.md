# Requirements: Application d'Audit

**Defined:** 2026-04-28
**Core Value:** Audit fiable et rapide par comparaison PDF/Excel avec identification précise des écarts.

## v1 Requirements

### UI / UX

- [ ] **UI-01**: Bouton "Annuler l'audit" visible pendant le traitement
- [ ] **UI-02**: L'audit peut être interrompu à tout moment
- [ ] **UI-03**: Barre de progression affichant le % d'avancement
- [ ] **UI-04**: Barre de progression mise à jour en temps réel
- [ ] **UI-05**: Message de confirmation quand l'audit est terminé

### Performance

- [ ] **PERF-01**: Temps de traitement réduit (algorithme optimisé)
- [ ] **PERF-02**: Le traitement ne bloque pas l'interface
- [ ] **PERF-03**: Utilisation mémoire optimisée pour gros volumes

### Nettoyage de Données — Société / IBAN

- [ ] **DATA-01**: Dissocier nom société et IBAN concaténés dans Excel
- [ ] **DATA-02**: Traiter le nom de société séparément de l'IBAN
- [ ] **DATA-03**: Gérer les différences de nom entre PDF et Excel
- [ ] **DATA-04**: Correspondance fuzzy sur les noms de société

### Nettoyage de Données — Filtres

- [ ] **FILT-01**: Ignorer les lignes de récap/sommes par groupe Excel
- [ ] **FILT-02**: Ignorer les lignes contenant "bordereau"
- [ ] **FILT-03**: Distinguer lignes de test vs lignes réelles
- [ ] **FILT-04**: Conserver les données détaillées, exclure les agrégats

### Post-Audit

- [ ] **POST-01**: Vider les fichiers PDF uploadés après audit terminé
- [ ] **POST-02**: Vider les fichiers Excel uploadés après audit terminé
- [ ] **POST-03**: Possibilité de lancer un nouvel audit propre

### Correspondance / Écarts

- [ ] **MATCH-01**: Total d'écart Excel = Total affiché dans Dashboard
- [ ] **MATCH-02**: Les écarts identifiés sont cohérents entre les deux vues
- [ ] **MATCH-03**: Aucune donnée manquante ou dupliquée dans le calcul

## v2 Requirements

### Améliorations Futures

- **V2-01**: Historique des audits précédents
- **V2-02**: Export des résultats d'audit
- **V2-03**: Comparaison multi-fichiers PDF

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-utilisateur simultané | Complexité, un audit à la fois suffit |
| Modification des fichiers source | Lecture seule pour l'audit |
| Intégration API bancaire | Hors périmètre |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| UI-01 | Phase 1 | Pending |
| UI-02 | Phase 1 | Pending |
| UI-03 | Phase 1 | Pending |
| UI-04 | Phase 1 | Pending |
| UI-05 | Phase 1 | Pending |
| PERF-01 | Phase 3 | Pending |
| PERF-02 | Phase 3 | Pending |
| PERF-03 | Phase 3 | Pending |
| DATA-01 | Phase 2 | Pending |
| DATA-02 | Phase 2 | Pending |
| DATA-03 | Phase 2 | Pending |
| DATA-04 | Phase 2 | Pending |
| FILT-01 | Phase 2 | Pending |
| FILT-02 | Phase 2 | Pending |
| FILT-03 | Phase 2 | Pending |
| FILT-04 | Phase 2 | Pending |
| POST-01 | Phase 5 | Pending |
| POST-02 | Phase 5 | Pending |
| POST-03 | Phase 5 | Pending |
| MATCH-01 | Phase 4 | Pending |
| MATCH-02 | Phase 4 | Pending |
| MATCH-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-28*
*Last updated: 2026-04-28 after initial definition*
