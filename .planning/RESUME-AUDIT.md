# RÉSUMÉ — Audit Application GSD Project

**Date :** 29/04/2026
**Projet :** Application d'Audit PDF/Excel
**Méthodologie :** GSD (Get Shit Done)

---

## 1. Livrables Créés (GSD)

### Structure du Projet

```
.planning/
├── PROJECT-AUDIT.md          # Contexte et besoins
├── REQUIREMENTS-AUDIT.md     # 22 exigences v1
├── ROADMAP-AUDIT.md          # 5 phases
├── ANALYSE-DATA.md           # Analyse données réelles
└── phases-audit/
    ├── PLAN-01-UI-UX.md           # Phase 1 : Bouton + Progression
    ├── PLAN-02-DATA-CLEANING.md   # Phase 2 : Nettoyage IBAN/Bordereau
    ├── PLAN-03-PERFORMANCE.md     # Phase 3 : Algorithmes optimisés
    ├── PLAN-04-ECARTS.md          # Phase 4 : Corrections écarts
    └── PLAN-05-POST-AUDIT.md      # Phase 5 : Vidage fichiers
```

---

## 2. Analyse des Données Réelles

### PDF (Bordereau de Virements)

**Format :** `IBAN + Nom Société` (concaténés)
```
FR76 30003031800002003128252 Sté LAVOLLE CHIMIE
FR76 30004021460001024426574 SOCIÉTÉ POAE SAS
```

**Lignes à exclure :**
```
Total 2 - Prestations prévoyance 92361.39
Total 10686 du 29/04/2026 - 51 virements 92361.39
Total Groupe Européen de Retraite et Prévoyanc 92361.39
```

**Total bordereau :** 92 361,39 € (51 virements)

### Excel

**Colonnes identifiées :**
| Colonne | Contenu |
|---------|---------|
| A | Numéro ID |
| B | ID + Nom |
| C | Prénom |
| D | **Nom Société** |
| G | **Montant** |
| I | Date |
| J | Assureur |

**Ligne à exclure :**
```
0,00 | bordereau | 52 190,21 €
```

### Problème de Noms (PDF vs Excel)

| PDF | Excel | Match |
|-----|-------|-------|
| `Sté LAVOLLE CHIMIE` | `SOCIETE LAVOLLEE SA` | ⚠️ Proche |
| `SOCIÉTÉ POAE SAS` | `POAE SAS` | ⚠️ Préfixe |
| `Sté ROLAND MONTERRAT` | `SOCIETE ROLAND MONTERRAT` | ⚠️ Préfixe |
| `SOCIÉTÉ PANZANI LYON` | `PANZANI` | ⚠️ Suffixe |

---

## 3. Recommandations Techniques

### A. Parsing IBAN + Nom Société (PDF)

```python
def parse_pdf_line(line):
    # Extraire IBAN (27 caractères pour FR)
    iban = line[0:27].strip()
    # Extraire nom
    nom = line[28:].strip()
    
    # Normaliser le nom
    nom = nom.replace("Sté ", "").replace("SOCIÉTÉ ", "")
    nom = nom.replace("SOCIETE ", "").replace("STÉ ", "")
    
    # Supprimer suffixes juridiques
    for suffix in [" SAS", " SNC", " SA", " SARL"]:
        nom = nom.replace(suffix, "")
    
    return iban, nom.strip()
```

### B. Correspondance Fuzzy

```python
from difflib import SequenceMatcher

def match_company_name(pdf_name, excel_name, threshold=0.75):
    """Compare deux noms de société normalisés"""
    ratio = SequenceMatcher(None, pdf_name, excel_name).ratio()
    return ratio >= threshold
```

### C. Filtres

**PDF :**
```python
# Exclure les lignes de total
if line.startswith("Total") or line.startswith("Bordereau"):
    continue
# Exclure les lignes sans IBAN
if not line.startswith("FR"):
    continue
```

**Excel :**
```python
# Exclure les lignes bordereau
df = df[~df['Société'].str.contains('bordereau', case=False, na=False)]
# Exclure les montants nuls
df = df[df['Montant'] != 0]
```

### D. Optimisation Algorithmique

**Avant (lent) :**
```python
# Boucles imbriquées O(n²)
for pdf_row in pdf_data:
    for excel_row in excel_data:
        if pdf_row['nom'] == excel_row['nom']:
            # comparaison
```

**Après (rapide) :**
```python
# Index par nom O(n)
excel_index = {row['nom']: row for row in excel_data}
for pdf_row in pdf_data:
    if pdf_row['nom'] in excel_index:
        excel_row = excel_index[pdf_row['nom']]
        # comparaison
```

---

## 4. Phases et Priorités

| Phase | Objectif | Priorité | Complexité |
|-------|----------|----------|------------|
| **1** | Bouton annuler + Barre progression | Haute | Moyenne |
| **2** | Dissocier IBAN/Nom + Filtres | Haute | Haute |
| **3** | Algorithmes optimisés | Critique | Moyenne |
| **4** | Correction écarts Excel/Dashboard | Critique | Haute |
| **5** | Vidage fichiers post-audit | Moyenne | Faible |

---

## 5. Prochaines Actions Concrètes

### Immédiat (Jour 1)
1. ✅ Implémenter le parsing IBAN + Nom sur vos données test
2. ✅ Tester la correspondance fuzzy avec 3-4 sociétés
3. ✅ Vérifier que les lignes "Total" du PDF sont bien exclues

### Court terme (Semaine 1)
4. Implémenter le bouton "Annuler" + barre de progression
5. Implémenter les filtres bordereau et récap
6. Optimiser l'algorithme de comparaison avec index

### Moyen terme (Semaine 2)
7. Corriger le calcul d'écart Excel vs Dashboard
8. Implémenter le vidage des fichiers post-audit
9. Tests complets avec plusieurs jeux de données

---

## 6. Questions à Résoudre

1. **Quel est le seuil de correspondance fuzzy acceptable ?** (75% ? 80% ?)
2. **Comment gérer les sociétés qui n'ont pas de correspondance ?** (ignorer, signaler, rapprochement manuel ?)
3. **La formule Excel de l'écart est-elle :** PDF - Excel ou Excel - PDF ?
4. **Quelle technologie utilise l'application actuelle ?** (Python, C#, JavaScript...)

---

## 7. Fichiers du Projet

**Tous les livrables sont dans :** `.planning/`

- Besoins et contexte → `PROJECT-AUDIT.md`
- Exigences détaillées → `REQUIREMENTS-AUDIT.md`
- Plan de phases → `ROADMAP-AUDIT.md`
- Analyse données → `ANALYSE-DATA.md`
- Plans d'exécution → `phases-audit/PLAN-0X-*.md`

---

*Résumé produit : 29/04/2026*
