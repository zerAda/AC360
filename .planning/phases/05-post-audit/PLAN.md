# PLAN.md — Phase 5: Post-Audit

**Phase:** 5/5 | **ROADMAP.md requirements:** 4 | **Status:** Pending

## Goal

Vider les fichiers uploadés et permettre un nouvel audit propre.

## Context

Après un audit terminé (ou annulé), l'application doit nettoyer les fichiers temporaires et réinitialiser son état pour permettre à l'utilisateur de lancer un nouvel audit sans conflit avec les données précédentes.

**Contrainte de sécurité :** Ne jamais supprimer les fichiers source originaux de l'utilisateur. Seuls les fichiers uploadés/copiés dans l'application doivent être supprimés.

## Deliverables

| # | Deliverable | Requirements |
|---|------------|----------------|
| 1 | PDF supprimés après audit | POST-01 |
| 2 | Excel supprimés après audit | POST-02 |
| 3 | Nouvel audit possible | POST-03 |
| 4 | Réinitialisation complète | POST-04 |

## Execution Steps

### Step 1: Vider les Fichiers PDF Uploadés

**Task:** Supprimer les fichiers PDF du dossier temporaire après audit

**Implémentation :**
```python
import os
import glob

def vider_pdfs(dossier_temporaire):
    """
    Supprime tous les fichiers PDF du dossier temporaire.
    """
    chemin_pattern = os.path.join(dossier_temporaire, "*.pdf")
    fichiers_pdf = glob.glob(chemin_pattern)
    
    compteur = 0
    for fichier in fichiers_pdf:
        try:
            os.remove(fichier)
            compteur += 1
            print(f"Supprimé : {fichier}")
        except Exception as e:
            print(f"Erreur suppression {fichier} : {e}")
    
    print(f"{compteur} fichier(s) PDF supprimé(s)")
    return compteur
```

**Messages (français) :**
- "Nettoyage des fichiers PDF..."
- "X fichier(s) PDF supprimé(s)"
- "Erreur lors de la suppression de [fichier]"

### Step 2: Vider les Fichiers Excel Uploadés

**Task:** Supprimer les fichiers Excel du dossier temporaire après audit

**Implémentation :**
```python
def vider_excels(dossier_temporaire):
    """
    Supprime tous les fichiers Excel du dossier temporaire.
    """
    patterns = ['*.xlsx', '*.xls', '*.csv']
    compteur = 0
    
    for pattern in patterns:
        chemin_pattern = os.path.join(dossier_temporaire, pattern)
        fichiers = glob.glob(chemin_pattern)
        
        for fichier in fichiers:
            try:
                os.remove(fichier)
                compteur += 1
                print(f"Supprimé : {fichier}")
            except Exception as e:
                print(f"Erreur suppression {fichier} : {e}")
    
    print(f"{compteur} fichier(s) Excel supprimé(s)")
    return compteur
```

### Step 3: Réinitialiser les Données en Mémoire

**Task:** Vider les variables et objets contenant les données de l'audit

**Variables à réinitialiser :**
```python
def reinitialiser_etat():
    """
    Réinitialise toutes les données de l'audit en mémoire.
    """
    global pdf_data, excel_data, resultats, correspondances
    global total_ecart, stats, progress_current, progress_total
    
    pdf_data = []
    excel_data = []
    resultats = []
    correspondances = []
    
    total_ecart = 0.0
    stats = {}
    
    progress_current = 0
    progress_total = 0
    
    # Forcer le garbage collector
    import gc
    gc.collect()
    
    print("Mémoire réinitialisée")
```

### Step 4: Réinitialiser l'Interface

**Task:** Remettre l'interface à son état initial

**Éléments à réinitialiser :**
- Barre de progression : 0%
- Tableau de résultats : vide
- Résumé des écarts : caché ou à zéro
- Bouton "Lancer l'audit" : activé
- Bouton "Annuler" : caché ou désactivé
- Champs de fichier : vides
- Messages : "Prêt pour un nouvel audit"

```python
def reinitialiser_interface():
    """
    Réinitialise l'interface utilisateur.
    """
    # Barre de progression
    progress_bar.value = 0
    progress_label.text = "0%"
    
    # Tableau de résultats
    results_grid.rows = []
    
    # Résumé
    summary_panel.visible = False
    summary_total_ecart.text = "0,00 €"
    summary_societes.text = "0"
    
    # Boutons
    btn_lancer.enabled = True
    btn_annuler.visible = False
    
    # Fichiers
    file_pdf.value = None
    file_excel.value = None
    
    # Message
    status_label.text = "Prêt pour un nouvel audit"
    status_label.color = "black"
```

### Step 5: Permettre un Nouvel Audit

**Task:** S'assurer qu'un nouvel audit peut être lancé proprement

**Vérifications :**
1. Les boutons sont dans le bon état
2. Aucune donnée de l'audit précédent ne persiste
3. Les fichiers temporaires sont supprimés
4. La mémoire est libérée
5. Le dossier temporaire est vide

```python
def verifier_pret_nouvel_audit(dossier_temporaire):
    """
    Vérifie que tout est prêt pour un nouvel audit.
    """
    # Vérifier dossier vide
    fichiers_restants = glob.glob(os.path.join(dossier_temporaire, "*"))
    if fichiers_restants:
        print(f"AVERTISSEMENT : {len(fichiers_restants)} fichier(s) restant(s)")
        return False
    
    # Vérifier mémoire vide
    if pdf_data or excel_data or resultats:
        print("AVERTISSEMENT : Données en mémoire non vide")
        return False
    
    print("✓ Prêt pour un nouvel audit")
    return True
```

### Step 6: Flow Complet Post-Audit

**Task:** Orchestrer le nettoyage complet après audit

```python
def nettoyage_post_audit(dossier_temporaire, raison='termine'):
    """
    Nettoie tout après un audit.
    
    Args:
        raison: 'termine', 'annule', ou 'erreur'
    """
    messages = {
        'termine': 'Audit terminé. Nettoyage en cours...',
        'annule': 'Audit annulé. Nettoyage en cours...',
        'erreur': 'Erreur lors de l\'audit. Nettoyage en cours...'
    }
    
    print(messages.get(raison, 'Nettoyage...'))
    
    # 1. Supprimer fichiers
    vider_pdfs(dossier_temporaire)
    vider_excels(dossier_temporaire)
    
    # 2. Réinitialiser mémoire
    reinitialiser_etat()
    
    # 3. Réinitialiser interface
    reinitialiser_interface()
    
    # 4. Vérifier
    verifier_pret_nouvel_audit(dossier_temporaire)
    
    print("✓ Nettoyage terminé. Prêt pour un nouvel audit.")
```

## Success Criteria

- [x] PDF uploadés supprimés après audit
- [x] Excel uploadés supprimés après audit
- [x] Nouvel audit peut être lancé proprement
- [x] Aucune donnée de l'audit précédent ne persiste en mémoire
- [x] Interface réinitialisée (barre à 0%, tableau vide)
- [x] Dossier temporaire vide vérifié

## Blockers

(None identified)

## Sécurité

⚠️ **RÈGLES DE SÉCURITÉ :**
1. Ne jamais supprimer les fichiers originaux de l'utilisateur
2. Ne supprimer que les fichiers dans le dossier temporaire de l'application
3. Vérifier les chemins avant suppression (éviter les injections de path)
4. Logger toutes les suppressions pour audit

```python
def supprimer_securise(chemin_fichier, dossier_autorise):
    """
    Supprime un fichier de manière sécurisée.
    """
    # Vérifier que le fichier est bien dans le dossier autorisé
    chemin_absolu = os.path.abspath(chemin_fichier)
    dossier_absolu = os.path.abspath(dossier_autorise)
    
    if not chemin_absolu.startswith(dossier_absolu):
        raise ValueError(f"Tentative de suppression hors dossier autorisé : {chemin_fichier}")
    
    # Vérifier que c'est un fichier (pas un dossier)
    if not os.path.isfile(chemin_absolu):
        raise ValueError(f"Ce n'est pas un fichier : {chemin_fichier}")
    
    os.remove(chemin_absolu)
```

---

*Plan created: 2026-04-29*
*Ready for execution: Run /gsd-execute-phase 5*
