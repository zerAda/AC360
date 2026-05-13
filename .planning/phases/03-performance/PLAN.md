# PLAN.md — Phase 3: Optimisation Performance

**Phase:** 3/5 | **ROADMAP.md requirements:** 3 | **Status:** Pending

## Goal

Accélérer le traitement avec des algorithmes optimisés — objectif : < 30 secondes pour 50+ virements.

## Context

L'application actuelle est trop lente. Le traitement prend plusieurs minutes pour comparer un PDF et un Excel. L'analyse montre que l'algorithme utilise probablement des boucles imbriquées (complexité O(n²)) pour comparer chaque ligne PDF avec chaque ligne Excel.

**Problème identifié :** Algorithme actuel probablement :
```python
# AVANT — Lent (O(n²))
for pdf_row in pdf_data:           # n itérations
    for excel_row in excel_data:   # n itérations
        if comparer(pdf_row, excel_row):
            # ...
```

**Solution :** Utiliser un index/dictionnaire (complexité O(n)) :
```python
# APRÈS — Rapide (O(n))
excel_index = {normaliser_nom(row['nom']): row for row in excel_data}
for pdf_row in pdf_data:           # n itérations
    nom_norm = normaliser_nom(pdf_row['nom'])
    if nom_norm in excel_index:    # O(1) — recherche instantanée
        excel_row = excel_index[nom_norm]
        # ...
```

## Deliverables

| # | Deliverable | Requirements |
|---|------------|----------------|
| 1 | Algorithme de traitement optimisé | PERF-01 |
| 2 | Traitement asynchrone/non-bloquant | PERF-02 |
| 3 | Gestion mémoire optimisée | PERF-03 |

## Execution Steps

### Step 1: Profiler le Code Actuel

**Task:** Mesurer le temps par étape pour identifier les goulots d'étranglement

**Méthode :**
```python
import time

def profiler_etape(nom_etape, fonction, *args):
    debut = time.time()
    resultat = fonction(*args)
    duree = time.time() - debut
    print(f"{nom_etape}: {duree:.2f}s")
    return resultat

# Usage :
pdf_data = profiler_etape("Lecture PDF", read_pdf, pdf_path)
excel_data = profiler_etape("Lecture Excel", read_excel, excel_path)
matches = profiler_etape("Correspondance", match_data, pdf_data, excel_data)
```

**Étapes à profiler :**
1. Lecture du PDF (parsing ligne par ligne)
2. Lecture de l'Excel (pandas read_excel ou équivalent)
3. Nettoyage et normalisation des noms
4. Correspondance PDF ↔ Excel
5. Calcul des écarts
6. Génération du dashboard/résultats

### Step 2: Optimiser la Lecture des Fichiers

**Task:** Lire les fichiers une seule fois et utiliser des structures efficaces

**Optimisations :**
- Lire le PDF une seule fois et stocker en mémoire
- Utiliser `pandas.read_excel()` si Python (vectorisé, rapide)
- Éviter les lectures répétées du disque
- Ne pas stocker les lignes exclues en mémoire (filtrer pendant la lecture)

```python
import pandas as pd

# Lecture optimisée Excel
df_excel = pd.read_excel(excel_path, usecols=['Société', 'Montant', 'Date'])
# Filtrer immédiatement
df_excel = df_excel[df_excel['Montant'] != 0]
df_excel = df_excel[~df_excel['Société'].str.contains('bordereau', case=False, na=False)]
```

### Step 3: Optimiser l'Algorithme de Comparaison (CRITIQUE)

**Task:** Remplacer la boucle O(n²) par une recherche O(n)

**Implémentation optimisée :**
```python
def matcher_optimise(pdf_data, excel_data):
    """
    Algorithme optimisé O(n) avec index par nom normalisé.
    """
    # Étape 1 : Créer un index Excel (nom_normalisé → ligne)
    excel_index = {}
    for row in excel_data:
        nom_norm = normaliser_nom(row['nom'])
        if nom_norm:
            excel_index[nom_norm] = row
    
    # Étape 2 : Parcourir le PDF et chercher dans l'index
    resultats = []
    for pdf_row in pdf_data:
        nom_pdf_norm = normaliser_nom(pdf_row['nom'])
        
        # Recherche directe O(1)
        if nom_pdf_norm in excel_index:
            excel_row = excel_index[nom_pdf_norm]
            ecart = excel_row['montant'] - pdf_row['montant']
            resultats.append({
                'societe': pdf_row['nom'],
                'montant_pdf': pdf_row['montant'],
                'montant_excel': excel_row['montant'],
                'ecart': ecart,
                'iban': pdf_row['iban']
            })
        else:
            # Fallback : recherche fuzzy si pas de match exact
            for nom_excel_norm, excel_row in excel_index.items():
                match, ratio = correspondre_noms(nom_pdf_norm, nom_excel_norm)
                if match:
                    ecart = excel_row['montant'] - pdf_row['montant']
                    resultats.append({
                        'societe': pdf_row['nom'],
                        'montant_pdf': pdf_row['montant'],
                        'montant_excel': excel_row['montant'],
                        'ecart': ecart,
                        'iban': pdf_row['iban'],
                        'correspondance_fuzzy': True,
                        'ratio': ratio
                    })
                    break
            else:
                # Aucun match trouvé
                resultats.append({
                    'societe': pdf_row['nom'],
                    'montant_pdf': pdf_row['montant'],
                    'montant_excel': None,
                    'ecart': None,
                    'iban': pdf_row['iban'],
                    'sans_correspondance': True
                })
    
    return resultats
```

**Gains de performance attendus :**
- Avant : O(n²) = 2500 comparaisons pour 50 lignes
- Après : O(n) = 50 recherches directes + quelques fuzzy
- Gain théorique : **50x plus rapide**

### Step 4: Traitement Asynchrone

**Task:** Ne pas bloquer l'interface pendant l'audit

**Implémentation (Python threading) :**
```python
import threading

def run_audit_async(pdf_path, excel_path, progress_callback, result_callback):
    """Lance l'audit dans un thread séparé."""
    def audit_worker():
        try:
            resultats = run_audit(pdf_path, excel_path, progress_callback)
            result_callback(success=True, data=resultats)
        except Exception as e:
            result_callback(success=False, error=str(e))
    
    thread = threading.Thread(target=audit_worker, daemon=True)
    thread.start()
    return thread
```

**Implémentation (JavaScript Promise/Web Worker) :**
```javascript
async function runAudit(pdfFile, excelFile, onProgress) {
    return new Promise((resolve, reject) => {
        const worker = new Worker('audit-worker.js');
        worker.postMessage({ pdfFile, excelFile });
        worker.onmessage = (e) => {
            if (e.data.type === 'progress') onProgress(e.data);
            if (e.data.type === 'result') resolve(e.data);
        };
        worker.onerror = reject;
    });
}
```

### Step 5: Optimisation Mémoire

**Task:** Libérer la mémoire des objets intermédiaires

**Techniques :**
- Supprimer les variables intermédiaires après usage : `del variable`
- Utiliser des générateurs (`yield`) au lieu de listes pour les gros volumes
- Forcer le garbage collector si nécessaire : `import gc; gc.collect()`
- Ne pas stocker les lignes filtrées (exclure pendant la lecture)

```python
import gc

def audit_avec_gc(pdf_path, excel_path):
    # Lecture et traitement
    pdf_data = read_pdf(pdf_path)
    excel_data = read_excel(excel_path)
    
    # Match
    resultats = matcher_optimise(pdf_data, excel_data)
    
    # Libérer mémoire
    del pdf_data
    del excel_data
    gc.collect()
    
    return resultats
```

### Step 6: Mesurer les Gains

**Task:** Comparer le temps avant/après optimisation

**Script de benchmark :**
```python
import time

def benchmark():
    # Avant optimisation (si possible)
    # ...
    
    # Après optimisation
    debut = time.time()
    resultats = run_audit_optimise(pdf_path, excel_path)
    duree = time.time() - debut
    
    print(f"Temps de traitement : {duree:.2f} secondes")
    print(f"Nombre de sociétés : {len(resultats)}")
    print(f"Temps par société : {duree/len(resultats):.3f}s")
    
    assert duree < 30, f"Trop lent : {duree}s (objectif < 30s)"
```

## Success Criteria

- [x] Traitement de 50+ virements en moins de 30 secondes
- [x] Interface reste réactive pendant l'audit (pas de blocage)
- [x] Pas de surcharge mémoire (RAM stable)
- [x] Résultats identiques à l'ancien algorithme (mêmes écarts)
- [x] Temps mesuré et documenté (avant/après)

## Blockers

- Besoin de mesurer le temps actuel comme baseline
- Besoin de confirmer la technologie utilisée (Python, JS, C#, etc.)

## Performance Targets

| Métrique | Avant (estimé) | Après (objectif) |
|----------|---------------|------------------|
| 50 virements | > 2 minutes | < 30 secondes |
| 100 virements | > 5 minutes | < 45 secondes |
| Mémoire | Inconnue | < 200 MB |
| UI bloquée | Oui | Non |

---

*Plan created: 2026-04-29*
*Ready for execution: Run /gsd-execute-phase 3*
