import pytest
from fastapi import HTTPException
from api_server import _validate_document_id


def test_validate_document_id_invalid_uuid():
    with pytest.raises(HTTPException) as exc:
        _validate_document_id("../../../windows/system32/cmd.exe")
    assert exc.value.status_code == 400
    assert "UUID" in exc.value.detail


def test_validate_document_id_nonexistent():
    # A valid UUID but not in registry
    with pytest.raises(HTTPException) as exc:
        _validate_document_id("12345678-1234-5678-1234-567812345678")
    assert exc.value.status_code == 404
