"""Tests d'invariant de localité JOBS_BASE_DIR (AUD-08) — Wave 0 RED scaffold.

Ces tests verrouillent, comme spécification exécutable, deux invariants que les
vagues ultérieures de la Phase 1 doivent préserver :

1. **Localité intra-activité** : dans un même appel ``run_audit``, l'étape
   ``download`` et l'étape ``ocr`` partagent le MÊME répertoire
   ``JOBS_BASE_DIR/{document_id}``. Aucune étape ne consomme un chemin produit
   par une *autre* activité (ce qui, sur un plan multi-VM sans état, atterrirait
   sur une VM différente avec un JOBS_BASE_DIR vide — l'anti-pattern AUD-08).

2. **Activité unique (structurel)** : ``function_app._audit_orchestration``
   pilote EXACTEMENT une activité, et uniquement ``activity_run_audit`` — garde
   contre un futur fan-out qui ferait traverser une frontière d'activité à un
   chemin de fichier.

DI uniquement : aucun import ``azure.durable_functions``, aucun SDK cloud vivant.
Le bootstrap de path est inline (le dossier tests/azure_functions n'a pas de
conftest), à l'identique de test_audit_pipeline.py / test_function_app.py.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "azure_functions", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "azure_functions"))

from audit_pipeline import AuditDeps, run_audit  # noqa: E402


def _ocr_shape():
    """Sortie OCR minimale et conforme au schéma attendu par run_audit."""
    return {
        "metadata": {"source_file": "doc.pdf", "extraction_mode": "test"},
        "fields": {
            "Raison sociale": {"value": "GEREP SA", "confidence": 0.98},
        },
        "tables": [],
    }


def test_download_and_ocr_share_jobs_base_dir(tmp_path, monkeypatch):
    """AUD-08 — localité : download() et ocr() observent le même
    JOBS_BASE_DIR/{document_id} dans un unique appel run_audit."""
    monkeypatch.setenv("JOBS_BASE_DIR", str(tmp_path))
    document_id = "job-uuid-001"
    seen = {}

    def fake_download(doc_id):
        # Le document est écrit sous JOBS_BASE_DIR/{doc_id}/, comme le ferait la
        # vraie activité de téléchargement.
        base = tmp_path / doc_id
        base.mkdir(parents=True, exist_ok=True)
        p = base / "doc.pdf"
        p.write_bytes(b"%PDF-1.4 minimal")
        seen["download"] = str(p.parent)
        return str(p)

    def fake_ocr(path):
        # L'étape OCR doit voir le MÊME répertoire que le téléchargement, donc
        # le dirname du chemin reçu == JOBS_BASE_DIR/{doc_id}.
        seen["ocr"] = os.path.dirname(path)
        return _ocr_shape()

    deps = AuditDeps(
        download=fake_download,
        ocr=fake_ocr,
        fetch_reference=lambda _identity: None,  # client absent -> chaîne courte
        make_fic=None,
    )

    out = run_audit(document_id, None, deps)

    # La chaîne ne lève jamais ; on s'assure que les deux étapes ont bien tourné.
    assert "download" in seen, "l'étape download n'a pas été invoquée"
    assert "ocr" in seen, "l'étape ocr n'a pas été invoquée"
    # Invariant de localité : même répertoire d'artefacts dans une activité.
    assert seen["download"] == seen["ocr"], (
        "AUD-08 viole : download et ocr ne partagent pas le même "
        f"JOBS_BASE_DIR/{{document_id}} ({seen['download']} != {seen['ocr']})"
    )
    # Et ce répertoire EST bien JOBS_BASE_DIR/{document_id}.
    expected = str(tmp_path / document_id)
    assert seen["download"] == expected, (
        f"répertoire d'artefact attendu {expected}, observé {seen['download']}"
    )
    assert out["document_id"] == document_id


def test_orchestration_drives_exactly_one_activity():
    """AUD-08 — structurel : _audit_orchestration appelle call_activity
    EXACTEMENT une fois, et uniquement avec 'activity_run_audit'.

    Garde contre un futur fan-out qui ferait traverser une frontière d'activité
    à un chemin de fichier (ce qui casserait l'invariant de localité ci-dessus).
    """
    import function_app as fa

    calls = []

    class _FakeContext:
        def __init__(self, payload):
            self._payload = payload

        def get_input(self):
            return self._payload

        def call_activity(self, name, payload):
            calls.append((name, payload))
            # L'orchestration est un générateur : on renvoie ce que yield
            # consomme (le résultat de l'activité). Ici un dict factice suffit.
            return {"status": "Completed", "document_id": payload.get("document_id")}

    payload = {"document_id": "job-uuid-002", "client_context": None, "document_path": None}
    gen = fa._audit_orchestration(_FakeContext(payload))

    # Déroule le générateur d'orchestration sans runtime Durable.
    result = None
    try:
        sent = None
        while True:
            activity_result = gen.send(sent)
            sent = activity_result  # le yield renvoie le résultat de l'activité
    except StopIteration as stop:
        result = stop.value

    assert len(calls) == 1, (
        f"AUD-08 viole : l'orchestration doit piloter EXACTEMENT une activité, "
        f"observé {len(calls)} appels : {[c[0] for c in calls]}"
    )
    assert calls[0][0] == "activity_run_audit", (
        f"activité attendue 'activity_run_audit', observée {calls[0][0]!r}"
    )
    # Le résultat de l'activité unique est bien remonté tel quel.
    assert result == {"status": "Completed", "document_id": "job-uuid-002"}


def test_orchestration_payload_carries_no_cross_activity_file_path():
    """AUD-08 — la charge transmise à l'activité unique ne contient QUE des
    identifiants/contexte (document_id, client_context, document_path d'entrée),
    jamais un chemin de SORTIE (OCR/FIC) produit par une autre activité."""
    import function_app as fa

    seen_payload = {}

    class _Ctx:
        def get_input(self):
            return {"document_id": "d", "client_context": "c", "document_path": None}

        def call_activity(self, name, payload):
            seen_payload.update(payload)
            return {"status": "Completed"}

    gen = fa._audit_orchestration(_Ctx())
    try:
        sent = None
        while True:
            sent = gen.send(sent)
    except StopIteration:
        pass

    # Aucune clé de chemin de sortie ne traverse la frontière d'activité.
    forbidden = {"fic_path", "ocr_path", "output_path", "result_path"}
    assert not (forbidden & set(seen_payload.keys())), (
        f"un chemin de sortie traverse la frontière d'activité : {seen_payload.keys()}"
    )
    assert set(seen_payload.keys()) <= {"document_id", "client_context", "document_path"}


def test_function_app_documents_audit_trail_choice():
    """AUD-07 — function_app référence le seam audit_trail et documente que
    l'émission de la piste d'accès vit au site porteur de l'oid (api_server),
    l'entrée Durable ne portant que l'owner_hash (hash à sens unique)."""
    import os as _os
    fa_path = _os.path.join(_os.path.dirname(__file__), "..", "..",
                            "azure_functions", "function_app.py")
    src = open(fa_path, encoding="utf-8").read()
    assert "audit_trail" in src, "function_app doit référencer le seam audit_trail (AUD-07)"
    # La justification du choix de site d'émission est documentée dans le source.
    assert "owner_hash" in src and "oid" in src
