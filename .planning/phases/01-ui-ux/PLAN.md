# PLAN.md — Phase 1: UI/UX et Contrôle Audit

**Phase:** 1/5 | **ROADMAP.md requirements:** 5 | **Status:** In Progress

## Goal

Ajouter le bouton d'annulation et la barre de progression à l'interface de l'application d'audit.

## Context

L'application d'audit compare des fichiers PDF (bordereaux de virements bancaires) avec des fichiers Excel (suivi des règlements). Actuellement, le traitement est lent et l'utilisateur n'a aucun retour visuel sur l'avancement. Il est impossible d'interrompre un audit en cours.

## Deliverables

| # | Deliverable | Requirements |
|---|------------|----------------|
| 1 | Bouton "Annuler l'audit" fonctionnel | UI-01, UI-02 |
| 2 | Barre de progression temps réel | UI-03, UI-04 |
| 3 | Messages de fin d'audit | UI-05 |

## Execution Steps

### Step 1: Ajouter le Bouton Annuler

**Task:** Ajouter un bouton "Annuler l'audit" dans l'interface

**Details:**
- Le bouton doit être visible uniquement pendant le traitement
- Implémenter une variable/thread flag d'interruption (`should_cancel = False`)
- Au clic, mettre `should_cancel = True`
- L'algorithme principal vérifie `should_cancel` régulièrement et s'arrête proprement
- Gérer la libération des ressources (fichiers, mémoire) en cas d'annulation

**Messages (français) :**
- "Audit en cours..."
- "Annuler l'audit"
- "Audit annulé par l'utilisateur"

### Step 2: Implémenter la Barre de Progression

**Task:** Ajouter une barre de progression visible

**Details:**
- Calculer le nombre total d'étapes : `total = nombre de lignes PDF à traiter + nombre de lignes Excel à traiter`
- Mettre à jour la barre à chaque étape complétée : `progress = (traités / total) × 100`
- Afficher le pourcentage d'avancement en temps réel
- Afficher le fichier/étape en cours de traitement (ex: "Traitement de POAE SAS...")
- La barre ne doit pas bloquer l'interface (mettre à jour depuis le thread principal ou via callback)

**Exemple visuel :**
```
[██████████░░░░░░░░░░] 45%
Traitement : 23 / 51 virements
Société en cours : POAE SAS
```

### Step 3: Ajouter les Messages de Fin

**Task:** Afficher un message de confirmation quand l'audit se termine

**Details:**
- Quand l'audit se termine normalement :
  - "Audit terminé — {X} écarts détectés sur {Y} sociétés traitées"
- Quand l'audit est annulé :
  - "Audit annulé — {Y} sociétés traitées avant l'annulation"
- Quand aucun écart n'est trouvé :
  - "Aucun écart détecté — correspondance parfaite entre PDF et Excel"
- Afficher un résumé : nombre de sociétés traitées, écarts trouvés, total des écarts

### Step 4: Tests UI

**Task:** Tester toutes les interactions utilisateur

**Test cases :**
1. Lancer un audit → vérifier que la barre progresse
2. Cliquer "Annuler" au début → vérifier arrêt immédiat
3. Cliquer "Annuler" à 50% → vérifier arrêt avec message approprié
4. Laisser l'audit terminer → vérifier message de succès
5. Vérifier que l'interface reste cliquable pendant le traitement

## Success Criteria

- [x] Bouton "Annuler" visible et fonctionnel
- [x] L'audit s'arrête proprement quand on clique annuler
- [x] Barre de progression visible avec % d'avancement
- [x] Progression mise à jour en temps réel
- [x] Message de confirmation à la fin (écarts ou aucun écart)

## Blockers

(None identified)

## Code Snippets (Référence)

### Python (Threading + Progress Bar)
```python
import threading

class AuditThread(threading.Thread):
    def __init__(self, pdf_path, excel_path, progress_callback):
        super().__init__()
        self.pdf_path = pdf_path
        self.excel_path = excel_path
        self.progress_callback = progress_callback
        self.should_cancel = False
        self.daemon = True
    
    def run(self):
        # Lecture PDF
        pdf_data = self.read_pdf(self.pdf_path)
        total = len(pdf_data)
        
        for i, row in enumerate(pdf_data):
            if self.should_cancel:
                self.progress_callback("Annulé", 0, "Audit annulé")
                return
            
            # Traitement
            self.process_row(row)
            
            # Mise à jour progression
            progress = int((i + 1) / total * 100)
            self.progress_callback(progress, i + 1, total, row.get('nom', ''))
    
    def cancel(self):
        self.should_cancel = True
```

---

*Plan created: 2026-04-29*
*Ready for execution: Run /gsd-execute-phase 1*
