# ANALYSE-DATA.md — Analyse des Données PDF/Excel

## Structure PDF (Bordereau de Virements)

### Format d'une ligne de virement
```
[IBAN] [Nom Société]
```

Exemples réels :
- `FR76 30003031800002003128252 Sté LAVOLLE CHIMIE`
- `FR12 30002007430000001270H45 SOCIÉTÉ FONDASOL`
- `FR76 30004021460001024426574 SOCIÉTÉ POAE SAS`

### Lignes à EXCLURE (Récap/Sommes)
```
Total 2 - Prestations prévoyance 92361.39
Total 47 - BANQUE HSBC 92361.39
Total 10686 du 29/04/2026 - 51 virements 92361.39
Total Groupe Européen de Retraite et Prévoyanc 92361.39
```

### Total du Bordereau
- **51 virements**
- **Total : 92 361,39 €**

## Structure Excel

### Colonnes identifiées
| Colonne | Contenu | Exemple |
|---------|---------|---------|
| A | Numéro ID | 180024504 |
| B | ID + Nom | 89959 DEMOUGE |
| C | Prénom | Catherine |
| D | **Nom Société** | ADP GSI FRANCE |
| E-F | Type | IJ |
| G | **Montant** | 1 384,39 € |
| H | Statut | Suite |
| I | Date | 17/04/26 |
| J | Assureur | AXA |
| K | Commentaires | Contrôle PBE |
| L | Code | SA |

### Lignes à EXCLURE
```
0,00 | bordereau | 52 190,21 €
```

## Différences de Noms (PDF vs Excel)

| PDF | Excel | Match ? |
|-----|-------|---------|
| `Sté LAVOLLE CHIMIE` | `SOCIETE LAVOLLEE SA` | ⚠️ Proche |
| `SOCIÉTÉ POAE SAS` | `POAE SAS` | ⚠️ Préfixe différent |
| `SOCIÉTÉ FONDASOL` | ? | À vérifier |
| `SOCIÉTÉ PANZANI LYON` | `PANZANI` | ⚠️ Suffixe différent |
| `Sté ROLAND MONTERRAT` | `SOCIETE ROLAND MONTERRAT` | ⚠️ Préfixe |

## Règles de Parsing PDF

### Étape 1 : Séparer IBAN et Nom
```python
# Pattern IBAN FR : FR + 25 caractères
iban = line[0:27]  # ex: FR76 30003031800002003128252
nom = line[28:].strip()  # ex: Sté LAVOLLE CHIMIE
```

### Étape 2 : Normaliser le Nom
```python
# Supprimer préfixes
nom = nom.replace("Sté ", "")
nom = nom.replace("SOCIÉTÉ ", "")
nom = nom.replace("SOCIETE ", "")
nom = nom.replace("STÉ ", "")

# Supprimer suffixes juridiques
suffixes = [" SAS", " SNC", " SA", " SARL"]
for suffix in suffixes:
    nom = nom.replace(suffix, "")

# Nettoyer accents et majuscules
nom = unidecode(nom).upper().strip()
```

### Étape 3 : Correspondance Fuzzy
```python
from difflib import SequenceMatcher

def match_names(pdf_name, excel_name, threshold=0.75):
    """Seuil validé par le métier : 75%"""
    ratio = SequenceMatcher(None, pdf_name, excel_name).ratio()
    return ratio >= threshold
```

## Filtres à Appliquer

### Filtre PDF
- Exclure les lignes commençant par `Total`
- Exclure les lignes sans IBAN

### Filtre Excel
- Exclure les lignes où la colonne société = `bordereau`
- Exclure les lignes où le montant = `0,00`
- Exclure les lignes de récap (à identifier par pattern)

## Calcul de l'Écart

**Source de vérité : PDF** (validé par le métier)

```python
# Après nettoyage et matching :
for each company:
    # Écart = ce que dit Excel vs la vérité PDF
    ecart = montant_excel - montant_pdf
    
    # Si écart > 0 : Excel a un montant supérieur au PDF (en trop)
    # Si écart < 0 : Excel a un montant inférieur au PDF (en manque)
    # Si écart = 0 : Pas d'écart
    
# Total écart = somme des écarts individuels
# Doit correspondre entre Excel et Dashboard
```

---

*Analyse créée : 2026-04-29*
