# Phase 1 : Socle AC360 Sécurisé (Étape A)

## Objectif
S'assurer que le bot Copilot Studio actuellement synchronisé est parfaitement en phase avec les exigences de sécurité et de "Read-Only" édictées par l'architecture.

## Tâches d'Exécution

1. **Revue de `agent.mcs.yml`**
   - S'assurer que les "instructions" générales interdisent bien l'usage de OneDrive, Outlook, ou WebSearch.
   - S'assurer que le message de Fallback défini dans la charte ("Je n’ai pas trouvé d’information accessible sur ce client dans les documents disponibles.") est bien le message par défaut s'il manque des données.

2. **Revue des rubriques (Topics)**
   - Vérifier `Refusmodificationdocument.mcs.yml` : S'assurer que l'AC360 refuse bien explicitement toute création/modification/suppression.
   - Vérifier `Documentsmanquants.mcs.yml` (Checklist de complétude) : S'assurer que le prompt intègre la logique : lire les documents présents vs la liste des documents attendus.

3. **Mise à jour et Synchronisation**
   - Appliquer les modifications dans les fichiers YAML locaux.
   - Pousser les modifications via `scripts/sync_copilot.ps1 -Mode Push`.

## Critères de Validation
- Le bot doit répondre strictement sans hallucination, en citant ses documents SharePoint.
- Toute tentative de manipulation documentaire (écriture) doit être rejetée courtoisement.
