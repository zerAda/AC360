"""Garde la vraie échéance OCR : poller.result(timeout) ne lève pas de lui-même,
donc extract_document_azure doit lever explicitement si le poller n'est pas done."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import process_document_ocr as ocr  # noqa: E402


class _Result:
    pages = []
    key_value_pairs = []
    tables = []


class _PollerDone:
    def result(self, timeout=None):
        return _Result()

    def done(self):
        return True


class _PollerStuck:
    def result(self, timeout=None):
        return None  # azure-core rend la main sans lever à l'expiration

    def done(self):
        return False


class _Client:
    def __init__(self, poller):
        self._poller = poller

    def begin_analyze_document(self, *a, **k):
        return self._poller


@pytest.fixture(autouse=True)
def _stub_sdk(monkeypatch, tmp_path):
    monkeypatch.setattr(ocr, "AZURE_OCR_ENDPOINT", "https://x.cognitiveservices.azure.com/")
    monkeypatch.setattr(ocr, "AZURE_OCR_KEY", "k")
    monkeypatch.setattr(ocr, "AzureKeyCredential", lambda key: object())
    yield


def _make_file(tmp_path):
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4 test")
    return str(f)


def test_ocr_raises_on_timeout(monkeypatch, tmp_path):
    monkeypatch.setattr(ocr, "DocumentAnalysisClient", lambda **k: _Client(_PollerStuck()))
    with pytest.raises(TimeoutError):
        ocr.extract_document_azure(_make_file(tmp_path))


def test_ocr_completes_when_done(monkeypatch, tmp_path):
    monkeypatch.setattr(ocr, "DocumentAnalysisClient", lambda **k: _Client(_PollerDone()))
    out = ocr.extract_document_azure(_make_file(tmp_path))
    assert out["metadata"]["extraction_mode"] == "azure-prebuilt-document"
    assert out["metadata"]["pages"] == 0
