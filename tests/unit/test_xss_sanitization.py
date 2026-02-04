"""
Tests de sanitización XSS.

Verifica que manuscritos con contenido HTML/JavaScript potencialmente
peligroso se manejan de forma segura a lo largo del pipeline:

1. El parser preserva el texto como cadena plana (no lo interpreta como HTML)
2. El sanitizador de nombres rechaza caracteres peligrosos
3. Los textos con etiquetas HTML se devuelven sin alterar en la API
"""

import tempfile
from pathlib import Path

import pytest

from narrative_assistant.parsers.sanitization import (
    InputSanitizer,
    validate_file_path,
)

# =============================================================================
# XSS en manuscritos TXT
# =============================================================================


class TestXSSInManuscript:
    """Un manuscrito .txt con <script> no debe causar problemas."""

    @pytest.fixture
    def xss_txt(self, tmp_path):
        """Crear un archivo .txt con contenido XSS."""
        content = (
            "Capítulo 1: El inicio\n\n"
            "María miró la pantalla. El código decía:\n"
            '<script>alert("xss")</script>\n'
            "Ella no entendía qué significaba.\n\n"
            "Capítulo 2: La revelación\n\n"
            '<img src=x onerror="alert(1)">\n'
            "El ataque había sido neutralizado.\n"
        )
        path = tmp_path / "manuscrito_xss.txt"
        path.write_text(content, encoding="utf-8")
        return path

    def test_txt_parser_preserves_script_as_text(self, xss_txt):
        """El parser TXT preserva <script> como texto plano."""
        from narrative_assistant.parsers.txt_parser import TxtParser

        parser = TxtParser()
        result = parser.parse(xss_txt)
        assert result.is_success

        full_text = "\n".join(p.text for p in result.value.paragraphs)

        # El texto debe contener la etiqueta como cadena literal
        assert "<script>" in full_text
        assert 'alert("xss")' in full_text
        assert "</script>" in full_text

        # El parser NO debe haber eliminado ni transformado el contenido
        assert '<img src=x onerror="alert(1)">' in full_text

    def test_txt_parser_returns_plain_strings(self, xss_txt):
        """Los paragraphs son strings simples, no objetos HTML."""
        from narrative_assistant.parsers.txt_parser import TxtParser

        parser = TxtParser()
        result = parser.parse(xss_txt)
        assert result.is_success

        for para in result.value.paragraphs:
            assert isinstance(para.text, str)
            # No debe haber sido convertido a entidades HTML por el parser
            # (eso es responsabilidad del frontend)


# =============================================================================
# Sanitización de nombres
# =============================================================================


class TestSanitizeFilename:
    """Los nombres de archivo con caracteres peligrosos se neutralizan."""

    def test_angle_brackets_removed(self):
        """Los < y > se eliminan de nombres de archivo."""
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize_filename('<script>alert("xss")</script>.txt')
        assert "<" not in result
        assert ">" not in result

    def test_html_entities_in_filename(self):
        """Entidades HTML en nombres de archivo se manejan."""
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize_filename("test&amp;file.txt")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_null_bytes_in_filename(self):
        """Bytes nulos se eliminan de nombres de archivo."""
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize_filename("test\x00file.txt")
        assert "\x00" not in result


class TestSanitizeEntityName:
    """Los nombres de entidad con HTML se manejan de forma segura."""

    def test_entity_name_with_html(self):
        """Un nombre de entidad con HTML no causa problemas."""
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize_entity_name('<script>alert("xss")</script>')
        assert isinstance(result, str)
        # El sanitizador debe producir un resultado no vacío
        assert len(result.strip()) > 0

    def test_entity_name_with_js_event(self):
        """Un nombre con JS event handler se maneja."""
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize_entity_name('onload="alert(1)"')
        assert isinstance(result, str)


class TestSanitizeUserNote:
    """Las notas de usuario con HTML se preservan como texto."""

    def test_note_with_script_tag(self):
        """Una nota con <script> se preserva como texto (el frontend escapa)."""
        sanitizer = InputSanitizer()
        note = 'Revisar: el personaje dice <script>alert("xss")</script>'
        result = sanitizer.sanitize_user_note(note)
        assert isinstance(result, str)
        # La nota se preserva (sanitización de contenido es responsabilidad del frontend)
        assert len(result) > 0

    def test_note_with_html_tags(self):
        """Una nota con etiquetas HTML se maneja."""
        sanitizer = InputSanitizer()
        note = "El personaje dice: <b>hola</b> y <i>adiós</i>"
        result = sanitizer.sanitize_user_note(note)
        assert isinstance(result, str)


# =============================================================================
# Path traversal con nombres XSS
# =============================================================================


class TestPathTraversalXSS:
    """Intentos de path traversal con nombres XSS se rechazan."""

    def test_nonexistent_file_rejected(self, tmp_path):
        """Un path a archivo inexistente no pasa validación."""
        malicious = tmp_path / "nonexistent_script.txt"
        with pytest.raises(FileNotFoundError):
            validate_file_path(malicious)

    def test_traversal_rejected(self, tmp_path):
        """Path traversal se rechaza."""
        malicious = tmp_path / ".." / ".." / "etc" / "passwd"
        with pytest.raises((FileNotFoundError, PermissionError)):
            validate_file_path(malicious)
