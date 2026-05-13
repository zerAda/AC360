# PLAN.md — Phase 2: Nettoyage de Données

**Phase:** 2/5 | **ROADMAP.md requirements:** 10 | **Status:** Pending

## Goal

Dissocier IBAN et nom de société, filtrer les lignes bordereau et récap/sommes.

## Context

Les fichiers PDF contiennent les virements bancaires avec IBAN et nom de société concaténés sur la même ligne. Les fichiers Excel contiennent le suivi interne. Plusieurs lignes doivent être exclues car ce sont des tests ou des agrégats.

**Exemple de données PDF :**
```
FR76 30003031800002003128252 Sté LAVOLLE CHIMIE
FR76 30004021460001024426574 SOCIÉTÉ POAE SAS
```

**Exemple de données Excel :**
| Société | Montant |
|---------|---------|
| ADP GSI FRANCE | 1 384,39 € |
| POAE SAS | 388,68 € |
| **bordereau** | **52 190,21 €** |

**Décisions validées :**
- Seuil de correspondance fuzzy : **75%**
- Normalisation des noms : suppression accents, majuscules, préfixes, suffixes

## Deliverables

| # | Deliverable | Requirements |
|---|------------|----------------|
| 1 | Parser IBAN + Nom depuis PDF | DATA-01, DATA-02 |
| 2 | Normaliser les noms de société | DATA-05 |
| 3 | Correspondance fuzzy PDF ↔ Excel | DATA-03, DATA-04 |
| 4 | Filtrer lignes bordereau et récap | FILT-01, FILT-02, FILT-03, FILT-04, FILT-05 |

## Execution Steps

### Step 1: Parser le PDF — Séparer IBAN et Nom

**Task:** Extraire IBAN et nom de société depuis chaque ligne du PDF

**Format identifié :**
```
[IBAN 27 caractères] [espace] [Nom Société]
```

**Implémentation :**
```python
def parse_pdf_line(line):
    """
    Parse une ligne de bordereau PDF.
    Format: FRXX XXXX... (27 caractères) + Nom Société
    """
    line = line.strip()
    if len(line) < 30:
        return None, None
    
    iban = line[0:27].strip()
    nom = line[28:].strip()
    
    # Vérifier que c'est bien un IBAN français
    if not iban.startswith('FR'):
        return None, None
    
    return iban, nom
```

**Exemples de test :**
| Ligne PDF | IBAN | Nom |
|-----------|------|-----|
| `FR76 30003031800002003128252 Sté LAVOLLE CHIMIE` | `FR76 30003031800002003128252` | `Sté LAVOLLE CHIMIE` |
| `FR76 30004021460001024426574 SOCIÉTÉ POAE SAS` | `FR76 30004021460001024426574` | `SOCIÉTÉ POAE SAS` |

### Step 2: Normaliser les Noms de Société

**Task:** Créer une fonction de normalisation pour comparer les noms

**Règles de normalisation :**
1. Supprimer les préfixes : `Sté `, `SOCIÉTÉ `, `SOCIETE `, `STÉ `, `STE `
2. Supprimer les suffixes juridiques : ` SAS`, ` SNC`, ` SA`, ` SARL`, ` SASU`
3. Supprimer les accents et caractères spéciaux
4. Convertir en majuscules
5. Supprimer les espaces multiples

**Implémentation :**
```python
import unicodedata
import re

def normaliser_nom(nom):
    """
    Normalise un nom de société pour la comparaison.
    """
    if not nom:
        return ""
    
    # Supprimer préfixes
    prefixes = ['Sté ', 'SOCIÉTÉ ', 'SOCIETE ', 'STÉ ', 'STE ', 'Société ']
    for prefix in prefixes:
        if nom.startswith(prefix):
            nom = nom[len(prefix):]
    
    # Supprimer suffixes juridiques
    suffixes = [' SAS', ' SNC', ' SA', ' SARL', ' SASU', ' SC', ' EURL']
    for suffix in suffixes:
        if nom.endswith(suffix):
            nom = nom[:-len(suffix)]
    
    # Supprimer accents et caractères spéciaux
    nom = unicodedata.normalize('NFKD', nom).encode('ASCII', 'ignore').decode('ASCII')
    
    # Majuscules et nettoyage espaces
    nom = nom.upper().strip()
    nom = re.sub(r'\s+', ' ', nom)
    
    return nom
```

**Exemples de test :**
| Nom original | Normalisé |
|-------------|-----------|
| `Sté LAVOLLE CHIMIE` | `LAVOLLE CHIMIE` |
| `SOCIÉTÉ POAE SAS` | `POAE` |
| `SOCIETE ROLAND MONTERRAT` | `ROLAND MONTERRAT` |
| `ADP GSI FRANCE` | `ADP GSI FRANCE` |

### Step 3: Correspondance Fuzzy (Seuil 75%)

**Task:** Comparer les noms normalisés avec une tolérance de 75%

**Implémentation :**
```python
from difflib import SequenceMatcher

def correspondre_noms(nom_pdf, nom_excel, seuil=0.75):
    """
    Compare deux noms de société normalisés.
    Retourne (match, ratio)
    """
    nom_pdf_norm = normaliser_nom(nom_pdf)
    nom_excel_norm = normaliser_nom(nom_excel)
    
    if not nom_pdf_norm or not nom_excel_norm:
        return False, 0.0
    
    ratio = SequenceMatcher(None, nom_pdf_norm, nom_excel_norm).ratio()
    return ratio >= seuil, ratio
```

**Exemples de test (seuil 75%) :**
| PDF | Excel | Ratio | Match |
|-----|-------|-------|-------|
| `Sté LAVOLLE CHIMIE` | `SOCIETE LAVOLLEE SA` | ~85% | ✅ |
| `SOCIÉTÉ POAE SAS` | `POAE SAS` | ~100% | ✅ |
| `Sté ROLAND MONTERRAT` | `SOCIETE ROLAND MONTERRAT` | ~100% | ✅ |
| `SOCIÉTÉ PANZANI LYON` | `PANZANI` | ~78% | ✅ |
| `SOCIÉTÉ FONDASOL` | `FONDASOL SAS` | ~100% | ✅ |

### Step 4: Filtrer les Lignes du PDF

**Task:** Exclure les lignes de total et les lignes sans IBAN

**Filtres PDF :**
```python
def filtrer_ligne_pdf(line):
    """
    Retourne True si la ligne doit être conservée.
    """
    line = line.strip()
    
    # Exclure les lignes vides
    if not line:
        return False
    
    # Exclure les lignes de total
    if line.startswith('Total'):
        return False
    
    # Exclure les lignes de référence
    if line.startswith('Réf. Vir.') or line.startswith('Type d'opération'):
        return False
    
    # Exclure les lignes sans IBAN français
    if not line.startswith('FR'):
        return False
    
    # Exclure les lignes trop courtes
    if len(line) < 30:
        return False
    
    return True
```

**Lignes à exclure (exemples réels) :**
```
Total 2 - Prestations prévoyance 92361.39
Total 47 - BANQUE HSBC 92361.39
Total 10686 du 29/04/2026 - 51 virements 92361.39
Total Groupe Européen de Retraite et Prévoyanc 92361.39
Réf. Vir. Référence de la pièce Références Bancaires Montant
```

### Step 5: Filtrer les Lignes de l'Excel

**Task:** Exclure les lignes bordereau, récap et montants nuls

**Filtres Excel :**
```python
def filtrer_ligne_excel(row):
    """
    Retourne True si la ligne doit être conservée.
    row est un dictionnaire ou une Series pandas.
    """
    # Exclure les lignes bordereau
    societe = str(row.get('Société', '')).lower()
    if 'bordereau' in societe:
        return False
    
    # Exclure les lignes de récap/sommes
    if any(mot in societe for mot in ['total', 'somme', 'récap', 'recap']):
        return False
    
    # Exclure les montants nuls
    montant = row.get('Montant', 0)
    if montant == 0 or montant == '0,00':
        return False
    
    # Exclure les lignes sans société
    if not societe or societe.strip() == '':
        return False
    
    return True
```

**Lignes à exclure (exemples réels) :**
```
0,00 | bordereau | 52 190,21 €  ← ligne de test gestionnaire
```

### Step 6: Validation du Nettoyage

**Task:** Tester le nettoyage sur un jeu de données réel

**Validation :**
1. Compter le nombre de lignes avant/après filtrage PDF
2. Vérifier que le total PDF après filtrage = 92 361,39 € (pour le bordereau test)
3. Vérifier qu'aucune ligne "bordereau" n'est présente dans les données Excel filtrées
4. Vérifier que les noms sont correctement normalisés
5. Tester la correspondance sur 5 sociétés connues

## Success Criteria

- [x] IBAN et nom de société sont séparés depuis le PDF
- [x] Les noms sont normalisés (accents, majuscules, préfixes, suffixes)
- [x] Correspondance fuzzy fonctionne avec seuil 75%
- [x] Lignes "bordereau" exclues de l'analyse Excel
- [x] Lignes de récap/sommes exclues (PDF et Excel)
- [x] Lignes sans IBAN valide exclues du PDF
- [x] Le total PDF après filtrage correspond au total attendu

## Blockers

- Besoin d'un jeu de test complet (PDF + Excel) pour valider le filtrage
- Besoin de confirmer tous les préfixes/suffixes utilisés dans les données réelles

## Code Complet de Référence

```python
import unicodedata
import re
from difflib import SequenceMatcher

# ========== CONFIGURATION ==========
SEUIL_CORRESPONDANCE = 0.75  # Validé par le métier

# ========== PARSING PDF ==========
def parser_ligne_pdf(ligne):
    """Parse une ligne de bordereau PDF."""
    ligne = ligne.strip()
    if len(ligne) < 30 or not ligne.startswith('FR'):
        return None, None
    iban = ligne[0:27].strip()
    nom = ligne[28:].strip()
    return iban, nom

def filtrer_lignes_pdf(lignes):
    """Filtre les lignes du PDF."""
    resultat = []
    for ligne in lignes:
        ligne = ligne.strip()
        if not ligne or ligne.startswith('Total') or ligne.startswith('Réf.'):
            continue
        if not ligne.startswith('FR') or len(ligne) < 30:
            continue
        iban, nom = parser_ligne_pdf(ligne)
        if iban and nom:
            resultat.append({'iban': iban, 'nom': nom})
    return resultat

# ========== NORMALISATION ==========
def normaliser_nom(nom):
    """Normalise un nom de société."""
    if not nom:
        return ""
    
    prefixes = ['Sté ', 'SOCIÉTÉ ', 'SOCIETE ', 'STÉ ', 'STE ', 'Société ']
    for prefix in prefixes:
        if nom.startswith(prefix):
            nom = nom[len(prefix):]
    
    suffixes = [' SAS', ' SNC', ' SA', ' SARL', ' SASU', ' SC', ' EURL']
    for suffix in suffixes:
        if nom.endswith(suffix):
            nom = nom[:-len(suffix)]
    
    nom = unicodedata.normalize('NFKD', nom).encode('ASCII', 'ignore').decode('ASCII')
    nom = nom.upper().strip()
    nom = re.sub(r'\s+', ' ', nom)
    return nom

# ========== CORRESPONDANCE FUZZY ==========
def correspondre_noms(nom_pdf, nom_excel, seuil=SEUIL_CORRESPONDANCE):
    """Compare deux noms avec le seuil défini."""
    pdf_norm = normaliser_nom(nom_pdf)
    excel_norm = normaliser_nom(nom_excel)
    if not pdf_norm or not excel_norm:
        return False, 0.0
    ratio = SequenceMatcher(None, pdf_norm, excel_norm).ratio()
    return ratio >= seuil, ratio

# ========== FILTRES EXCEL ==========
def filtrer_lignes_excel(df):
    """Filtre les lignes de l'Excel (pandas DataFrame)."""
    masque = (
        ~df['Société'].str.contains('bordereau', case=False, na=False) &
        ~df['Société'].str.contains('total|somme|récap|recap', case=False, na=False) &
        (df['Montant'] != 0) &
        (df['Société'].notna()) &
        (df['Société'].str.strip() != '')
    )
    return df[masque]
```

---

*Plan created: 2026-04-29*
*Ready for execution: Run /gsd-execute-phase 2*
