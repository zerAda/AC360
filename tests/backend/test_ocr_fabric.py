import pytest
from unittest.mock import patch, MagicMock

from process_document_ocr import extract_document_azure
from audit_fabric_comparison import fetch_artus_data, match_client_name, perform_audit
import pandas as pd

# ==========================================
# Tests OCR (process_document_ocr.py)
# ==========================================


@patch("process_document_ocr.AzureKeyCredential")
@patch("process_document_ocr.DocumentAnalysisClient")
def test_extract_document_azure_success(mock_client, mock_cred, tmp_path):
    # Setup credential mock
    mock_cred.return_value = MagicMock()

    # Setup client mock
    mock_poller = MagicMock()
    mock_result = MagicMock()
    mock_result.pages = [1]
    mock_result.key_value_pairs = []
    mock_result.tables = []
    mock_poller.result.return_value = mock_result

    mock_instance = mock_client.return_value
    mock_instance.begin_analyze_document.return_value = mock_poller

    # Create dummy file
    test_file = tmp_path / "dummy.pdf"
    test_file.write_text("dummy")

    result = extract_document_azure(str(test_file))

    assert result["metadata"]["extraction_mode"] == "azure-prebuilt-document"
    assert result["metadata"]["pages"] == 1
    assert "fields" in result
    assert "tables" in result

# ==========================================
# Tests Fabric / Audit (audit_fabric_comparison.py)
# ==========================================


@patch("audit_fabric_comparison.get_fabric_connection")
def test_fetch_artus_data_fail_fast_on_missing_db(mock_conn):
    # En production, on veut une erreur si pas de DB, pas de fallback silencieux
    mock_conn.return_value = None
    with pytest.raises(ConnectionError) as exc:
        fetch_artus_data()
    assert "ERREUR CRITIQUE" in str(exc.value)


def test_match_client_name_strictness():
    # Création d'un dataframe mock
    df = pd.DataFrame({
        "client_id": [1, 2],
        "nom_client": ["GEREP SA", "BETA Corp"],
        "plafond_hospitalisation": ["1000", "500"]
    })

    # Matching réussi (Score > 85%)
    match, score = match_client_name("GEREP SA", df)
    assert match is not None
    assert score >= 85

    # Matching échoué (Penalité stricte avec mot rejet)
    match_reject, score_reject = match_client_name("Groupe GEREP SA", df)
    assert match_reject is None
    assert score_reject < 85


def test_perform_audit_logic():
    ocr_data = {
        "fields": {
            "nom_client": {"value": "GEREP SA"}
        },
        "keyValuePairs": [
            {"key": {"content": "Hospitalisation"}, "value": {"content": "1000"}}
        ]
    }
    artus_df = pd.DataFrame({
        "client_id": [1],
        "nom_client": ["GEREP SA"],
        "plafond_hospitalisation": ["1000"]
    })

    result = perform_audit(ocr_data, artus_df)
    assert result["meilleur_match_fabric"] == "GEREP SA"

    # Vérifie qu'il n'y a pas d'écart
    details = result["details_ecarts"]
    assert len(details) == 1
    assert details[0]["ecart_detecte"] is False
    assert details[0]["commentaire"] == "Conforme"
