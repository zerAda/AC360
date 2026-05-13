# Structure SharePoint Recommandée — Phase 3

## Contexte

Le POC nécessite une structure SharePoint simple et lisibilité. L'objectif n'est PAS de refondre SharePoint mais d'améliorer légèrement la lisibilité pour l'agent Copilot Studio.

## Structure Recommandée par Dossier Client

### Organisation Type

```
DossiersClients/
└── Client_ABC/
    ├── 01_Contrats/
    ├── 02_Propositions_Commerciales/
    ├── 03_Comptes_Rendus/
    ├── 04_Documents_Administratifs/
    └── 05_Archives/
```

### Détail des Dossiers

| Dossier | Contenu | Exemples |
|---------|---------|---------|
| 01_Contrats | Contrats signés, avenants | Contrat_cadre.pdf, Avenant_2025.pdf |
| 02_Propositions_Commerciales | Propales, devis | Propale_2026_V1.docx |
| 03_Comptes_Rendus | CR réunions, notes | CR_RendezVous_2026-01-15.docx |
| 04_Documents_Administratifs | Factures, KC | Facture_2025-123.pdf |
| 05_Archives | Anciens documents | Ancien_contrat_2020.pdf |

## Règles de Nommage

### Format Recommandé

```
YYYY-MM-DD_Client_TypeDocument_Description.ext
```

### Exemples

```
2026-04-28_ClientABC_Contrat_Cadre_Signe.pdf
2026-04-15_ClientABC_Proposition_Commerciale_V1.docx
2026-03-10_ClientABC_CR_RendezVous_Tech.docx
2025-12-20_ClientABC_Facture_AC-2025-456.pdf
2025-06-15_ClientABC_Contrat_Ancien_2020.pdf
```

### Conventions

| Élément | Format | Exemple |
|---------|--------|---------|
| Date | YYYY-MM-DD | 2026-04-28 |
| Client | Nom court | ClientABC |
| Type | Contrat, Proposition, CR, Facture | Contrat |
| Description | Libre mais court | Cadre_Signe |
| Extension | .pdf, .docx, .xlsx | .pdf |

## Métadonnées Optionnelles

### Recommandées mais NON obligatoires pour le POC

Ces métadonnées peuvent aider mais ne sont pas requises :

| Métadonnée | Type | Description |
|------------|------|-------------|
| NomClient | Texte | Nom du client |
| TypeDocument | Sélection | Contrat, Proposition, CR, Facture... |
| DateDocument | Date | Date du document |
| StatutDocument | Sélection | Actif, Archivé, Expiré |
| CommercialResponsable | Texte | Nom du commercial |

### Note Importante

**Si les métadonnées ne sont pas disponibles, le POC doit quand même pouvoir commencer.**

Le modèle Copilot Studio peut fonctionner sans métadonnées structurées. Il sera moins précis mais fonctionnel.

## Améliorations Minimes Recommandées

### Priorité 1 - Nettoyage Léger

1. Identifier les documents essentiels (5-10 par client)
2. Les déplacer dans les bons dossiers
3. Vérifier le nommage

### Priorité 2 - Archives

1. Créer un dossier Archives si inexistant
2. Déplacer les documents de plus de 2 ans
3. Réduire le bruit pour l'agent

### Priorité 3 - Conventions

1. Appliquer le format de nommage pour les nouveaux documents
2. Ne pas renommer les anciens (trop de travail)

## Structure Multi-Clients

### Si une seule bibliothèque

```
Bibliothèque_DossiersClients/
├── Client_ABC/
├── Client_XYZ/
├── Client_123/
└── ...
```

### Principes

1. **Un dossier par client** : Nom unique
2. **Sous-dossiers par catégorie** : 01 à 05
3. **Pas de limite** : Peut grandir avec le temps

## Checklist Pré-POC

- [ ] Identifier 10-20 dossiers clients cibles
- [ ] Vérifier que chaque dossier a une structure lisible
- [ ] Nettoyer les noms de documents les plus importants
- [ ] Identifier les documents sensibles à exclure
- [ ] Documenter la structure existante

---

*Document créé : 2026-04-28 - Structure SharePoint Phase 3*