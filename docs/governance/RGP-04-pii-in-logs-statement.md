# RGP-04 — Déclaration de traitement des PII dans les journaux

**Exigence :** RGP-04 (PII-in-logs : déclaration + processeur de télémétrie + rétention courte EU délibérée).
**Statut :** appliqué (code Phase 3 + rétention paramétrée Phase 5).
**Dernière MAJ :** 2026-06-14.

---

## 1. Principe

Aucune **PII brute** ni aucun **secret** ne doit atteindre les journaux applicatifs ni la télémétrie Application Insights / Log Analytics. La redaction est appliquée par une **surface unique auditée** avant toute sortie ou export.

## 2. Surface de redaction unique (le processeur de télémétrie)

| Composant | Rôle | Emplacement |
|-----------|------|-------------|
| `safe_logger.redact` / `redact_mapping` | masque PII/secrets (IBAN, email, JWT, clés…) dans les messages et dicts de log | `scripts/safe_logger.py` |
| `RedactingSpanProcessor` | route le **nom de span** et **chaque valeur d'attribut `str`** par `safe_logger.redact` AVANT export vers Azure Monitor (OpenTelemetry) | `scripts/telemetry.py` (Phase 3, OBS-01) |
| `AppInsightsMiddleware` (gateway) | route les dimensions de télémétrie par `redact_mapping` | `scripts/api_server.py` |

**Aucun nouveau regex** n'est introduit : `RedactingSpanProcessor` réutilise exactement les motifs de `safe_logger` (AUD-06 — surface unique). Le `try/except` du processeur garantit que la redaction ne lève jamais dans le chemin de requête.

**Preuve (test) :** `tests/backend/test_telemetry_redaction.py` — un attribut de span contenant un email/secret ressort masqué ; valeurs non-`str` intactes.

## 3. Piste d'audit sans PII brute (AUD-07)

L'événement d'accès document (`scripts/audit_trail.py`) porte **exactement 4 champs** : `user_id_hash` (SHA-256 de l'oid Entra — jamais l'identité en clair), `document_id`, `ts_utc`, `verdict`. Aucune PII brute, aucun contenu document.

## 4. Rétention courte EU délibérée

| Réglage | Valeur | Emplacement |
|---------|--------|-------------|
| Log Analytics `retentionInDays` | **90 jours** (param `logAnalyticsRetentionDays`, `@minValue(30) @maxValue(730)`) | `infra/observability.bicep` ← threadé depuis `infra/main.bicep` |
| App Insights (workspace-based) | gouverné par le workspace ci-dessus (pas de propriété de rétention propre) | — |
| Région | EU (France Central, cf. RGP-06) | — |

90 jours = arbitrage minimisation des données ↔ besoin d'investigation d'incident (triage OPS-04). Le DPO peut imposer une rétention par-table différente (option `workspaces/tables`) pour la piste d'audit si la conformité l'exige.

## 5. Vérification

- Offline : `pytest tests/backend/test_telemetry_redaction.py` (redaction) ; `az bicep build -f infra/observability.bicep` (param de rétention compile).
- Live (opérateur) : confirmer `retentionInDays=90` sur le workspace prod ; vérifier dans App Insights que les dimensions sont masquées (cross-ref GO-01 « no PII leak »).

## 6. Références croisées

- AUD-06 (redaction des erreurs + télémétrie), AUD-07 (piste d'audit 4 champs) — `docs/security/SECURITY_POSTURE.md`.
- SEC-03 (threat-coverage : LLM06 sensitive info disclosure → cette redaction).
- DPIA (RGP-02) — mesure de réduction du risque « journalisation de PII ».
