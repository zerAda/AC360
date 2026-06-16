"""e2e_smoke.py — Harnais E2E contrôlé en prod réelle avec données SYNTHÉTIQUES (GO-01).

Pilote la passerelle de PRODUCTION (`/api/audit` -> statut -> résultat) sur un
**client/document de test clairement factice** (aucune PII client réelle) et vérifie
le verdict attendu sur le chemin nominal + les chemins d'échec (OCR timeout,
CLIENT_NON_TROUVE, Fabric-down, ECART+FIC).

Conception testable : l'HTTP est INJECTABLE (`http_post`/`http_get`/`sleep`) afin que
la logique (construction de requête + classification de verdict + boucle de polling)
soit testée hors-ligne avec des fakes — AUCUN appel réseau réel dans les tests.

⚠️ L'exécution LIVE (`main()` contre la prod) est un POINT DE CONTRÔLE OPÉRATEUR
(bloqué sur le sign-off DPO du DPIA + la stack live). Voir
docs/production/runbooks/07-go-no-go-checklist.md.
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Optional

__all__ = [
    "SYNTHETIC_CLIENT",
    "SCENARIOS",
    "build_audit_request",
    "classify_result",
    "run_scenario",
    "no_pii_kql",
]

# Données SYNTHÉTIQUES — clairement factices, aucune PII réelle (GO-01 / T-06-02).
SYNTHETIC_CLIENT = "ZZZ-TEST-CLIENT-SYNTHETIQUE"
_SYNTHETIC_DOC_PREFIX = "e2e-synthetic-"

# Scénarios E2E : verdict attendu par chemin. Le `inject` côté serveur (timeout/fabric)
# est piloté en prod via des flags de test dédiés ; ici on déclare le contrat attendu.
SCENARIOS = [
    {"name": "happy_conforme", "doc": _SYNTHETIC_DOC_PREFIX + "conforme", "expected": "CONFORME"},
    {"name": "ecart_fic", "doc": _SYNTHETIC_DOC_PREFIX + "ecart", "expected": "ECART"},
    {"name": "client_non_trouve", "doc": _SYNTHETIC_DOC_PREFIX + "unknown", "expected": "CLIENT_NON_TROUVE"},
    {"name": "ocr_timeout", "doc": _SYNTHETIC_DOC_PREFIX + "ocrtimeout", "expected": "INCERTAIN"},
    {"name": "fabric_down", "doc": _SYNTHETIC_DOC_PREFIX + "fabricdown", "expected": "INCERTAIN"},
]


def build_audit_request(client: str, document_id: str) -> dict:
    """Construit le corps de la requête /api/audit (données synthétiques uniquement)."""
    return {"client_context": client, "document_id": document_id}


def classify_result(result: dict) -> Optional[str]:
    """Extrait le verdict du résultat d'audit (schemas/audit_result.schema.json)."""
    if not isinstance(result, dict):
        return None
    return result.get("verdict")


def run_scenario(
    scenario: dict,
    *,
    base_url: str,
    token: str,
    http_post: Callable[..., Any],
    http_get: Callable[..., Any],
    sleep: Callable[[float], None] = time.sleep,
    max_polls: int = 30,
    poll_delay: float = 2.0,
) -> dict:
    """Pilote un scénario : POST /api/audit -> poll statut -> récupère le verdict.

    Tous les seams réseau sont injectés. Retourne
    {name, verdict, expected, ok} où ok = (verdict == expected).
    """
    headers = {"Authorization": f"Bearer {token}"}
    body = build_audit_request(SYNTHETIC_CLIENT, scenario["doc"])
    start = http_post(f"{base_url}/api/audit", json=body, headers=headers)
    job = start.json() if hasattr(start, "json") else start
    job_id = job.get("id") or job.get("job_id")

    verdict: Optional[str] = None
    for _ in range(max_polls):
        st = http_get(f"{base_url}/api/audit/{job_id}/status", headers=headers)
        data = st.json() if hasattr(st, "json") else st
        status = (data or {}).get("runtimeStatus") or (data or {}).get("status")
        if status in ("Completed", "Failed", "Terminated", "done"):
            verdict = classify_result((data or {}).get("output") or (data or {}))
            break
        sleep(poll_delay)

    return {
        "name": scenario["name"],
        "verdict": verdict,
        "expected": scenario["expected"],
        "ok": verdict == scenario["expected"],
    }


def no_pii_kql(correlation_id: str) -> str:
    """Requête KQL de contrôle no-PII (GO-01) : aucune trace de l'E2E ne doit contenir
    de motif PII (email/IBAN). Exécutée par l'opérateur contre App Insights après le run
    live ; preuve attachée dans docs/security/GUARDRAILS_VALIDATION.md §2."""
    return (
        f"union traces, requests, dependencies, exceptions\n"
        f"| where operation_Id == '{correlation_id}'\n"
        f"| where * matches regex @'[\\w.+-]+@[\\w-]+\\.[\\w.-]+'"
        f" or * matches regex @'[A-Z]{{2}}\\d{{2}}[A-Z0-9]{{10,30}}'\n"
        f"| count  // ATTENDU : 0 (aucune PII en clair dans la télémétrie)"
    )


def main() -> int:  # pragma: no cover - chemin opérateur live uniquement
    """Point d'entrée OPÉRATEUR (live). Nécessite la stack prod + un jeton de test.
    NON exécuté par la CI (chemin live, hors-ligne exclu)."""
    import httpx

    base_url = os.environ["AC360_E2E_BASE_URL"].rstrip("/")
    token = os.environ["AC360_E2E_TOKEN"]
    with httpx.Client(timeout=30.0) as client:
        results = [
            run_scenario(s, base_url=base_url, token=token,
                         http_post=client.post, http_get=client.get)
            for s in SCENARIOS
        ]
    failed = [r for r in results if not r["ok"]]
    for r in results:
        print(f"  {'OK ' if r['ok'] else 'KO '} {r['name']}: {r['verdict']} (attendu {r['expected']})")
    print(f"E2E: {len(results) - len(failed)}/{len(results)} scénarios conformes.")
    print("Contrôle no-PII : exécuter no_pii_kql(<correlation_id>) contre App Insights (attendu 0).")
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
