# Politique de sécurité — AC360

## Signalement d'une vulnérabilité

Si vous découvrez une faille de sécurité dans AC360, **ne créez pas d'issue
publique**. Contactez l'équipe de manière responsable :

- Envoyez le détail (description, étapes de reproduction, impact estimé) au
  responsable sécurité du projet (RSSI GEREP).
- Délai de première réponse visé : **5 jours ouvrés**.
- Merci de laisser un délai raisonnable de correction avant toute divulgation.

## Périmètre

Composants concernés :
- API passerelle FastAPI (`scripts/api_server.py`) et authentification
  (`scripts/auth.py`).
- Backend d'orchestration Azure Durable Functions (`azure_functions/`).
- Pipeline OCR → Fabric → FIC (`scripts/`).
- Agent et topics Copilot Studio (`src/copilot/AC360/`).

## Contrôles de sécurité en place (vérifiables)

- Authentification Entra ID : JWT RS256, vérification issuer / audience /
  expiration / nbf, scopes & rôles ; cache JWKS avec TTL + rotation.
- Anti path-traversal : validation UUID des identifiants, confinement des
  chemins (`commonpath`), assainissement des noms de fichiers.
- Contrôle d'accès aux téléchargements (IDOR) : vérification de propriété
  *fail-closed*.
- Rate-limiting par utilisateur.
- En-têtes HTTP de sécurité (nosniff, X-Frame-Options, HSTS, no-store).
- Journalisation neutralisée (masquage secrets / PII via `safe_logger.redact`).
- Détection de secrets en CI (gitleaks, règles par défaut + règles Azure
  personnalisées) ; scan local `scripts/scan_secrets.ps1`.
- Tests de sécurité automatisés (`tests/security/`, `tests/red_team/`,
  `tests/backend/test_*`).

## Limites connues (transparence)

Certains contrôles dépendent d'une validation en environnement réel (Azure,
Entra ID, Microsoft Fabric, SharePoint, politiques DLP) — voir
`AC360_FINAL_ENTERPRISE_READINESS_REPORT.md`. AC360 n'est **pas** présenté comme
« production ready » tant que cette validation n'a pas été réalisée.

## Gestion des secrets

Aucun secret ne doit être commité. Utilisez `.env` (gitignoré) en local et Azure
Key Vault / variables d'application en déploiement. Voir `.env.example`.
