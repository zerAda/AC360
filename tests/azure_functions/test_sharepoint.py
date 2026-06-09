"""Tests du téléchargement SharePoint sécurisé (Graph injecté, sans tenant réel)."""
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "azure_functions", "shared"))

from sharepoint import download_document, _safe_filename  # noqa: E402


def _resp(json_body=None, content=b"", status_ok=True):
    r = MagicMock()
    r.raise_for_status = MagicMock() if status_ok else MagicMock(side_effect=Exception("HTTP"))
    r.json = MagicMock(return_value=json_body or {})
    r.content = content
    return r


def _fake_get(meta, content=b"%PDF-1.7 data"):
    """Retourne un http_get qui répond métadonnées puis contenu."""
    calls = {"n": 0}

    def get(url, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _resp(json_body=meta)
        return _resp(content=content)

    return get


def test_safe_filename_blocks_traversal():
    assert _safe_filename("../../etc/passwd", "fb") == "passwd"
    assert _safe_filename("a/b/c.pdf", "fb") == "c.pdf"
    assert _safe_filename("", "fallback.bin") == "fallback.bin"
    assert _safe_filename("...", "fb") == "fb"


def test_download_writes_confined_file(tmp_path):
    meta = {"name": "contrat.pdf", "size": 12,
            "@microsoft.graph.downloadUrl": "https://signed.example/blob"}
    dest = download_document(
        item_id="item1", drive_id="drive1", dest_dir=str(tmp_path),
        access_token="tok", http_get=_fake_get(meta),
    )
    assert os.path.isfile(dest)
    assert os.path.dirname(os.path.abspath(dest)) == os.path.abspath(str(tmp_path))
    assert dest.endswith("contrat.pdf")


def test_download_rejects_disallowed_extension(tmp_path):
    meta = {"name": "malware.exe", "size": 10,
            "@microsoft.graph.downloadUrl": "https://signed.example/blob"}
    with pytest.raises(ValueError, match="Extension"):
        download_document(item_id="i", drive_id="d", dest_dir=str(tmp_path),
                          access_token="tok", http_get=_fake_get(meta))


def test_download_rejects_oversize_metadata(tmp_path):
    meta = {"name": "big.pdf", "size": 999_999_999,
            "@microsoft.graph.downloadUrl": "https://signed.example/blob"}
    with pytest.raises(ValueError, match="volumineux"):
        download_document(item_id="i", drive_id="d", dest_dir=str(tmp_path),
                          access_token="tok", http_get=_fake_get(meta))


def test_download_rejects_oversize_content(tmp_path):
    meta = {"name": "ok.pdf", "size": 0,
            "@microsoft.graph.downloadUrl": "https://signed.example/blob"}
    big = b"x" * 100
    with pytest.raises(ValueError, match="volumineux"):
        download_document(item_id="i", drive_id="d", dest_dir=str(tmp_path),
                          access_token="tok", http_get=_fake_get(meta, content=big),
                          max_bytes=50)


def test_download_requires_ids(tmp_path):
    with pytest.raises(ValueError, match="obligatoires"):
        download_document(item_id="", drive_id="d", dest_dir=str(tmp_path),
                          access_token="tok", http_get=_fake_get({}))


def test_traversal_filename_from_graph_is_neutralised(tmp_path):
    # Graph renvoie un nom malicieux -> doit être réduit au basename sûr.
    meta = {"name": "../../../evil.pdf", "size": 5,
            "@microsoft.graph.downloadUrl": "https://signed.example/blob"}
    dest = download_document(item_id="i", drive_id="d", dest_dir=str(tmp_path),
                             access_token="tok", http_get=_fake_get(meta))
    assert os.path.basename(dest) == "evil.pdf"
    assert os.path.dirname(os.path.abspath(dest)) == os.path.abspath(str(tmp_path))
