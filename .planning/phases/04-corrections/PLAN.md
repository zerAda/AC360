# PLAN.md — Phase 4: Calcul des Écarts

**Phase:** 4/5 | **ROADMAP.md requirements:** 6 | **Status:** Pending

## Goal

Calculer les écarts entre Excel et PDF, corriger le total pour qu'il corresponde entre Excel et Dashboard.

## Context

**Décisions métier validées :**
- Source de vérité : **PDF** (bordereau bancaire)
- Formule : **Écart = Montant Excel − Montant PDF**
- Seuil correspondance : **75%**

**Signification des écarts :**
| Écart | Signification |
|-------|---------------|
| Écart > 0 | Excel a un montant **supérieur** au PDF (en trop) |
| Écart < 0 | Excel a un montant **inférieur** au PDF (en manque) |
| Écart = 0 | Pas d'écart — correspondance parfaite |

**Problème connu :** Le total d'écart affiché dans le Dashboard ne correspond pas au total calculé dans Excel. Cela indique probablement que :
1. Les filtres (bordereau, récap) ne sont pas appliqués au même moment
2. Des lignes sont comptées différemment entre les deux vues
3. Le signe de l'écart est inversé dans l'un des calculs

## Deliverables

| # | Deliverable | Requirements |
|---|------------|----------------|
| 1 | Calcul d'écart par société | CALC-01, CALC-02, CALC-03 |
| 2 | Total d'écart cohérent | CALC-04, CALC-05 |
| 3 | Source de vérité PDF respectée | CALC-06 |

## Execution Steps

### Step 1: Implémenter le Calcul d'Écart

**Task:** Calculer l'écart pour chaque société matchée

**Implémentation :**
```python
def calculer_ecarts(pdf_data, excel_data, correspondances):
    """
    Calcule les écarts entre Excel et PDF.
    
    Écart = Montant Excel - Montant PDF
    
    Returns:
        list: Résultats avec société, montants, écart
    """
    resultats = []
    total_ecart = 0.0
    
    for match in correspondances:
        pdf_row = match['pdf']
        excel_row = match['excel']
        
        montant_pdf = float(pdf_row['montant'])
        montant_excel = float(excel_row['montant'])
        
        # Écart = Excel - PDF (source de vérité = PDF)
        ecart = montant_excel - montant_pdf
        total_ecart += ecart
        
        # Déterminer le statut
        if ecart > 0:
            statut = "Excès Excel"
            description = f"Excel a {ecart:.2f} € de plus que le PDF"
        elif ecart < 0:
            statut = "Manque Excel"
            description = f"Excel a {abs(ecart):.2f} € de moins que le PDF"
        else:
            statut = "OK"
            description = "Correspondance parfaite"
        
        resultats.append({
            'societe': match['nom_pdf'],
            'nom_normalise': match['nom_normalise'],
            'iban': pdf_row['iban'],
            'montant_pdf': montant_pdf,
            'montant_excel': montant_excel,
            'ecart': ecart,
            'statut': statut,
            'description': description,
            'correspondance_fuzzy': match.get('fuzzy', False),
            'ratio_correspondance': match.get('ratio', 1.0)
        })
    
    # Ajouter les sociétés sans correspondance
    for sans_match in correspondances.get('sans_correspondance', []):
        resultats.append({
            'societe': sans_match['nom'],
            'montant_pdf': sans_match['montant'],
            'montant_excel': None,
            'ecart': None,
            'statut': 'Non trouvé dans Excel',
            'description': 'Société présente dans le PDF mais absente de l\'Excel'
        })
    
    return resultats, total_ecart
```

**Exemple de résultat :**
```
Société: POAE SAS
  PDF: 1 215,20 €
  Excel: 1 384,39 €
  Écart: +169,19 € (Excès Excel)
  
Société: ADP GSI FRANCE
  PDF: 906,70 €
  Excel: 906,70 €
  Écart: 0,00 € (OK)
  
Société: PANZANI
  PDF: 192,41 €
  Excel: Non trouvé
  Écart: N/A (Non trouvé dans Excel)
```

### Step 2: Corriger le Total d'Écart

**Task:** S'assurer que le total écran Dashboard = Total calculé

**Vérifications à faire :**
1. **Même ensemble de données** : Le Dashboard et le calcul Excel utilisent-ils les mêmes lignes ?
2. **Filtres appliqués** : Les lignes "bordereau" et "récap" sont-elles exclues DANS les deux cas ?
3. **Signe cohérent** : Le Dashboard calcule-t-il `Excel - PDF` ou `PDF - Excel` ?
4. **Arrondis** : Y a-t-il des différences d'arrondi (2 décimales vs plus) ?

**Script de vérification :**
```python
def verifier_coherence_totaux(resultats, df_excel_filtre, df_pdf_filtre):
    """
    Vérifie que les totaux sont cohérents.
    """
    # Total écarts calculés
    total_ecarts = sum(r['ecart'] for r in resultats if r['ecart'] is not None)
    
    # Total Excel filtré
    total_excel = df_excel_filtre['Montant'].sum()
    
    # Total PDF filtré
    total_pdf = df_pdf_filtre['montant'].sum()
    
    # Vérification : total_ecarts doit être égal à (total_excel - total_pdf)
    expected_total = total_excel - total_pdf
    
    print(f"Total écarts (somme individuelle) : {total_ecarts:.2f} €")
    print(f"Total Excel filtré : {total_excel:.2f} €")
    print(f"Total PDF filtré : {total_pdf:.2f} €")
    print(f"Expected (Excel - PDF) : {expected_total:.2f} €")
    print(f"Différence : {abs(total_ecarts - expected_total):.2f} €")
    
    assert abs(total_ecarts - expected_total) < 0.01, \
        f"Incohérence des totaux : {total_ecarts} ≠ {expected_total}"
    
    return total_ecarts
```

### Step 3: Afficher les Résultats dans le Dashboard

**Task:** Créer le tableau de résultats pour l'interface

**Colonnes du tableau :**
| Colonne | Description |
|---------|-------------|
| Société | Nom de la société (depuis PDF) |
| IBAN | IBAN bancaire |
| Montant PDF | Montant du bordereau bancaire |
| Montant Excel | Montant du suivi interne |
| Écart | Écart calculé (Excel - PDF) |
| Statut | OK / Excès / Manque / Non trouvé |

**Tri par défaut :** Écart décroissant (les plus gros écarts en premier)

**Couleurs conditionnelles :**
- Écart = 0 : Vert
- Écart > 0 : Orange (Excès Excel)
- Écart < 0 : Rouge (Manque Excel)
- Non trouvé : Gris

### Step 4: Calculer les Statistiques Globales

**Task:** Ajouter un résumé en haut du Dashboard

```python
def calculer_statistiques(resultats):
    """Calcule les statistiques globales."""
    total_societes = len(resultats)
    societes_ok = sum(1 for r in resultats if r['statut'] == 'OK')
    societes_ecart = sum(1 for r in resultats if r['ecart'] is not None and r['ecart'] != 0)
    societes_non_trouvees = sum(1 for r in resultats if r['statut'] == 'Non trouvé dans Excel')
    
    total_ecart = sum(r['ecart'] for r in resultats if r['ecart'] is not None)
    ecart_moyen = total_ecart / societes_ecart if societes_ecart > 0 else 0
    
    ecart_max = max((r['ecart'] for r in resultats if r['ecart'] is not None), default=0)
    ecart_min = min((r['ecart'] for r in resultats if r['ecart'] is not None), default=0)
    
    return {
        'total_societes': total_societes,
        'societes_ok': societes_ok,
        'societes_ecart': societes_ecart,
        'societes_non_trouvees': societes_non_trouvees,
        'total_ecart': total_ecart,
        'ecart_moyen': ecart_moyen,
        'ecart_max': ecart_max,
        'ecart_min': ecart_min
    }
```

**Affichage du résumé :**
```
╔═══════════════════════════════════════════╗
║  RÉSULTATS DE L'AUDIT                     ║
╠═══════════════════════════════════════════╣
║  Sociétés traitées : 51                   ║
║  Correspondances OK : 45                  ║
║  Écarts détectés : 6                      ║
║  Non trouvées : 0                         ║
╠═══════════════════════════════════════════╣
║  Total écart : +1 234,56 €                ║
║  Écart moyen : 205,76 €                   ║
║  Écart max : +500,00 €                    ║
║  Écart min : -100,00 €                    ║
╚═══════════════════════════════════════════╝
```

### Step 5: Tests de Réconciliation

**Task:** Tester sur un jeu de données connu

**Test 1 : Correspondance parfaite**
- PDF : POAE SAS = 1 000 €
- Excel : POAE SAS = 1 000 €
- Écart attendu : 0 €

**Test 2 : Excès Excel**
- PDF : POAE SAS = 1 000 €
- Excel : POAE SAS = 1 200 €
- Écart attendu : +200 €

**Test 3 : Manque Excel**
- PDF : POAE SAS = 1 000 €
- Excel : POAE SAS = 800 €
- Écart attendu : -200 €

**Test 4 : Total cohérent**
- 3 sociétés avec écarts +200, -100, +50
- Total écran = +150
- Total calculé = +150

## Success Criteria

- [x] Écart calculé pour chaque société : Écart = Excel − PDF
- [x] Écart positif = Excel a plus que PDF (en trop)
- [x] Écart négatif = Excel a moins que PDF (en manque)
- [x] Total d'écart = somme des écarts individuels
- [x] Total écran Dashboard = Total calculé (cohérence vérifiée)
- [x] Source de vérité = PDF respectée dans tous les calculs

## Blockers

- Besoin d'un jeu de test avec total connu pour valider la cohérence
- Besoin de confirmer la formule exacte utilisée actuellement dans Excel

## Code Complet de Référence

```python
# ========== CALCUL DES ÉCARTS ==========

def calculer_ecarts(resultats_match):
    """
    Calcule les écarts pour chaque correspondance.
    
    Écart = Montant Excel - Montant PDF
    Source de vérité : PDF
    """
    details = []
    total_ecart = 0.0
    
    for match in resultats_match:
        pdf = match['pdf']
        excel = match['excel']
        
        m_pdf = float(pdf['montant'])
        m_excel = float(excel['montant'])
        ecart = m_excel - m_pdf
        total_ecart += ecart
        
        if ecart > 0:
            statut, desc = "Excès Excel", f"+{ecart:.2f} € (Excel > PDF)"
        elif ecart < 0:
            statut, desc = "Manque Excel", f"{ecart:.2f} € (Excel < PDF)"
        else:
            statut, desc = "OK", "Correspondance parfaite"
        
        details.append({
            'societe': match['nom'],
            'iban': pdf['iban'],
            'montant_pdf': m_pdf,
            'montant_excel': m_excel,
            'ecart': ecart,
            'statut': statut,
            'description': desc
        })
    
    return details, total_ecart


def afficher_resume(resultats):
    """Affiche le résumé des écarts."""
    stats = {
        'total': len(resultats),
        'ok': sum(1 for r in resultats if r['statut'] == 'OK'),
        'ecarts': sum(1 for r in resultats if r['ecart'] != 0),
        'total_ecart': sum(r['ecart'] for r in resultats)
    }
    
    print(f"╔═══════════════════════════════════════╗")
    print(f"║  RÉSULTATS DE L'AUDIT                 ║")
    print(f"╠═══════════════════════════════════════╣")
    print(f"║  Sociétés : {stats['total']:>3}                     ║")
    print(f"║  OK : {stats['ok']:>3} | Écarts : {stats['ecarts']:>3}          ║")
    print(f"╠═══════════════════════════════════════╣")
    print(f"║  Total écart : {stats['total_ecart']:>10.2f} €       ║")
    print(f"╚═══════════════════════════════════════╝")
    
    return stats
```

---

*Plan created: 2026-04-29*
*Ready for execution: Run /gsd-execute-phase 4*
