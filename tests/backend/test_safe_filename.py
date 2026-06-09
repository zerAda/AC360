"""
Tests de sécurité P0-05 : Path Traversal dans generate_fiche_rdv.py
Prouve que safe_filename() est robuste contre les attaques.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from generate_fiche_rdv import safe_filename


class TestSafeFilename:
    """Tests exhaustifs de la fonction safe_filename() — bloque le Path Traversal."""

    def test_normal_name(self):
        assert safe_filename("Client Alpha") == "Client_Alpha"

    def test_path_traversal_dots(self):
        result = safe_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result
        assert "\\" not in result

    def test_windows_path_traversal(self):
        result = safe_filename("..\\..\\windows\\system32\\cmd.exe")
        assert ".." not in result
        assert "\\" not in result

    def test_null_byte(self):
        result = safe_filename("client\x00evil")
        assert "\x00" not in result

    def test_accents_normalized(self):
        result = safe_filename("Société Générale")
        # After normalization, accents should be stripped
        assert "é" not in result
        assert "è" not in result

    def test_max_length_enforced(self):
        long_name = "A" * 200
        result = safe_filename(long_name)
        assert len(result) <= 64

    def test_special_chars_stripped(self):
        result = safe_filename("client|rm -rf /|client")
        assert "|" not in result
        assert " " not in result

    def test_empty_name_fallback(self):
        result = safe_filename("!@#$%^&*()")
        assert result == "client_inconnu"

    def test_semicolon_injection(self):
        result = safe_filename("client; DROP TABLE users;")
        assert ";" not in result

    def test_backtick_injection(self):
        result = safe_filename("client`whoami`")
        assert "`" not in result

    def test_angle_brackets(self):
        result = safe_filename("<script>alert(1)</script>")
        assert "<" not in result
        assert ">" not in result

    def test_unicode_control_chars(self):
        result = safe_filename("client\u0000\u001f\u007f")
        assert "\u0000" not in result
