# SPEC-FINALE.md — Spécifications Validées

**Date :** 29/04/2026
**Projet :** Application d'Audit PDF/Excel
**Statut :** Prêt pour développement

---

## 1. Décisions Validées

| # | Question | Réponse |
|---|----------|---------|
| 1 | Langue | Français |
| 2 | Seuil correspondance noms | **75%** |
| 3 | Source de vérité | **PDF** |

---

## 2. Calcul de l'Écart (Validé)

```
Écart = Montant Excel − Montant PDF
```

| Situation | Signification |
|-----------|---------------|
| Écart > 0 | Excel a un montant **supérieur** au PDF (en trop) |
| Écart < 0 | Excel a un montant **inférieur** au PDF (en manque) |
| Écart = 0 | Pas d'écart — correspondance parfaite |

**Total écart** = Somme de tous les écarts individuels

---

## 3. Algorithme de Correspondance (Validé — Seuil 75%)

### Étape 1 : Parser le PDF
```python
def parse_pdf_line(line):
    iban = line[0:27].strip()      # FR + 25 caractères
    nom = line[28:].strip()         # Le reste = nom société
    return iban, nom
```

### Étape 2 : Normaliser le nom (PDF et Excel)
```python
import unicodedata
from difflib import SequenceMatcher

def normaliser_nom(nom):
    # Supprimer préfixes
    nom = nom.replace("Sté ", "")
    nom = nom.replace("SOCIÉTÉ ", "")
    nom = nom.replace("SOCIETE ", "")
    nom = nom.replace("STÉ ", "")
    
    # Supprimer suffixes juridiques
    for suffix in [" SAS", " SNC", " SA", " SARL"]:
        nom = nom.replace(suffix, "")
    
    # Nettoyer accents et majuscules
    nom = unicodedata.normalize('NFKD', nom).encode('ASCII', 'ignore').decode('ASCII')
    nom = nom.upper().strip()
    
    return nom
```

### Étape 3 : Correspondance Fuzzy (Seuil 75%)
```python
def correspondre_noms(nom_pdf, nom_excel, seuil=0.75):
    """
    Compare deux noms de société normalisés.
    Seuil validé par le métier : 75%
    """
    ratio = SequenceMatcher(None, nom_pdf, nom_excel).ratio()
    return ratio >= seuil, ratio
```

### Exemples de Test

| Nom PDF | Nom Excel | Normalisé PDF | Normalisé Excel | Ratio | Match (≥75%) |
|---------|-----------|---------------|-----------------|-------|--------------|
| Sté LAVOLLE CHIMIE | SOCIETE LAVOLLEE SA | LAVOLLE CHIMIE | LAVOLLEE | ~85% | ✅ |
| SOCIÉTÉ POAE SAS | POAE SAS | POAE | POAE | 100% | ✅ |
| Sté ROLAND MONTERRAT | SOCIETE ROLAND MONTERRAT | ROLAND MONTERRAT | ROLAND MONTERRAT | 100% | ✅ |
| SOCIÉTÉ PANZANI LYON | PANZANI | PANZANI LYON | PANZANI | ~78% | ✅ |

---

## 4. Filtres Validés

### PDF — Lignes à exclure
```python
lignes_pdf_exclure = [
    line.startswith("Total"),
    line.startswith("Bordereau N°"),
    not line.startswith("FR"),     # Pas un IBAN = pas un virement
    len(line) < 30                 # Trop court
]
```

### Excel — Lignes à exclure
```python
lignes_excel_exclure = [
    df['Société'].str.contains('bordereau', case=False, na=False),
    df['Montant'] == 0,
    df['Société'].str.contains('recap|total|somme', case=False, na=False)
]
```

---

## 5. Structure des Données Attendue

### PDF parsé
```python
pdf_data = [
    {
        'iban': 'FR76 30003031800002003128252',
        'nom': 'Sté LAVOLLE CHIMIE',
        'nom_normalise': 'LAVOLLE CHIMIE',
        'montant': 906.70
    },
    # ...
]
```

### Excel parsé
```python
excel_data = [
    {
        'id': '180024504',
        'nom': 'ADP GSI FRANCE',
        'nom_normalise': 'ADP GSI FRANCE',
        'montant': 1384.39,
        'date': '17/04/26',
        'assureur': 'AXA'
    },
    # ...
]
```

### Résultat final
```python
resultats = [
    {
        'societe': 'POAE SAS',
        'montant_pdf': 1215.20,
        'montant_excel': 1384.39,
        'ecart': 169.19,        # Excel - PDF
        'statut': 'Écart détecté'
    },
    # ...
]
```

---

## 6. Flow Complet de l'Audit

```
1. UPLOAD PDF + EXCEL
         ↓
2. PARSER PDF (extraire IBAN + Nom + Montant)
         ↓
3. PARSER EXCEL (extraire Nom + Montant)
         ↓
4. FILTRER (exclure bordereaux, récaps, totaux)
         ↓
5. NORMALISER les noms (PDF et Excel)
         ↓
6. CORRESPONDRE par nom (fuzzy, seuil 75%)
         ↓
7. CALCULER Écart = Excel - PDF (pour chaque match)
         ↓
8. AGGÉRER les écarts (total et détail)
         ↓
9. AFFICHER Résultats (dashboard)
```

---

## 7. Messages Utilisateur (Français)

| Situation | Message |
|-----------|---------|
| Audit terminé | "Audit terminé — {X} écarts détectés sur {Y} sociétés" |
| Pas d'écart | "Aucun écart détecté — correspondance parfaite" |
| Société sans correspondance | "Société '{nom}' non trouvée dans l'autre fichier" |
| Écart positif | "Écart de +{montant} € (Excel > PDF)" |
| Écart négatif | "Écart de {montant} € (Excel < PDF)" |
| Audit annulé | "Audit annulé par l'utilisateur" |

---

## 8. Prochaines Étapes

### Priorité 1 — Code (Jour 1)
- [ ] Implémenter `parse_pdf_line()`
- [ ] Implémenter `normaliser_nom()`
- [ ] Implémenter `correspondre_noms()` avec seuil 75%
- [ ] Tester sur 5 sociétés du bordereau

### Priorité 2 — Filtres (Jour 1-2)
- [ ] Filtrer lignes "Total" du PDF
- [ ] Filtrer lignes "bordereau" de l'Excel
- [ ] Vérifier que le total PDF = 92 361,39 € après filtre

### Priorité 3 — Calcul Écart (Jour 2)
- [ ] Calculer Écart = Excel − PDF
- [ ] Vérifier le signe sur 3 exemples connus
- [ ] Comparer total écart avec Excel

### Priorité 4 — UI (Jour 3)
- [ ] Bouton "Annuler l'audit"
- [ ] Barre de progression (%)
- [ ] Tableau de résultats

### Priorité 5 — Nettoyage (Jour 4)
- [ ] Vider PDF après audit
- [ ] Vider Excel après audit
- [ ] Bouton "Nouvel audit"

---

*Spécifications validées : 29/04/2026*
*Source de vérité : PDF | Seuil fuzzy : 75% | Langue : Français*
