# Phase 6: Extraction PDF Robuste

**Phase:** 6 | **Milestone:** v2.0  
**Goal:** Remplacer l'extraction texte brute/pdftotext par pdfplumber pour une extraction fiable des IBAN, noms et montants

## Requirements

- PDF-01: Remplacer l'extraction texte brut par pdfplumber
- PDF-02: Extraire les montants PDF de manière fiable
- PDF-03: Gérer les PDF multi-pages
- PDF-04: Associer correctement chaque IBAN à son montant

## Current State

L'extraction actuelle dans `PDFParser.parse_content()` dépend de :
- `pdftotext` (outil externe, peut ne pas être installé)
- Fallback: lecture texte brute du fichier
- Extraction des montants par regex sur chaque ligne (algorithme naïf)
- Association montants par position dans la liste (fragile)

**Problèmes identifiés:**
1. `pdftotext` n'est pas toujours disponible sur Windows
2. La lecture texte brute échoue sur les PDF binaires
3. Les montants sont extraits indépendamment des IBAN/noms (pas d'association sûre)
4. Pas de gestion multi-pages

## Target State

Utiliser `pdfplumber` pour :
1. Ouvrir n'importe quel PDF bancaire
2. Extraire le texte structuré par page
3. Identifier les lignes contenant IBAN + nom
4. Extraire les montants situés à proximité (même ligne ou ligne suivante)
5. Associer chaque IBAN à son montant dans un seul passage

## Plan

### Task 1: Refactor PDFParser pour utiliser pdfplumber

**File:** `src/core.py`

**Changes:**
- Remplacer `parse_content(text_content)` par `parse_file(file_path)` qui utilise `pdfplumber.open()`
- Parser page par page
- Pour chaque ligne extraite par `page.extract_text()`:
  - Identifier IBAN (commence par FR + 25 chiffres)
  - Extraire le nom (reste de la ligne après l'IBAN)
  - Chercher le montant sur la même ligne ou la ligne suivante (format: `XXX XXX,XX` ou `XXXX,XX`)
- Retourner une liste de dicts avec `iban`, `nom`, `montant` déjà associés

**Validation:**
- Extraction fonctionne sans `pdftotext`
- Les montants sont correctement associés aux IBAN
- PDF multi-pages: tous les virements sont extraits

### Task 2: Supprimer l'ancienne logique d'extraction

**File:** `src/core.py`

**Changes:**
- Supprimer `extract_amounts()` (devient obsolète)
- Supprimer la logique de fallback texte brute dans `main.py`
- `PDFParser.parse_file()` devient la méthode unique d'extraction

**Validation:**
- `extract_amounts()` n'est plus appelé nulle part
- `main.py` appelle directement `PDFParser.parse_file(self.pdf_path.get())`

### Task 3: Gérer les formats de montants variés

**File:** `src/core.py`

**Changes:**
- Supporte les formats: `1 234,56`, `1234,56`, `1 234.56`, `1234.56`
- Convertir en `float` après nettoyage
- Gérer les montants négatifs (si présents)

**Validation:**
- Test avec montants contenant espaces, virgules, points
- Montants négatifs correctement parsés

### Task 4: Mettre à jour main.py

**File:** `src/main.py`

**Changes:**
- Remplacer le bloc d'extraction PDF (lignes 165-191) par un appel simple à `PDFParser.parse_file()`
- Supprimer la dépendance à `subprocess` et `pdftotext`
- Mettre à jour la progression: "Extraction PDF..." → "Analyse du PDF..."

**Validation:**
- `main.py` n'importe plus `subprocess`
- L'audit fonctionne de bout en bout avec pdfplumber

## Success Criteria

1. ✅ L'extraction fonctionne sur n'importe quel PDF bancaire sans dépendance externe
2. ✅ Les montants sont correctement associés aux IBAN/noms
3. ✅ Les PDF multi-pages sont entièrement parsés
4. ✅ L'ancien code `extract_amounts()` et `pdftotext` est supprimé
5. ✅ L'audit de bout en bout fonctionne avec le nouveau parser

## Dependencies

- **Requires:** `pdfplumber` (déjà installé: v0.11.9)
- **Updates:** `src/core.py`, `src/main.py`
- **Breaks:** Ancienne méthode `parse_content()` (à remplacer)

## Estimated Effort

1-2 jours

---
*Plan created: 2026-04-29*
