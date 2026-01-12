"""
Tests unitarios para los parsers de documentos.
"""

import pytest
from pathlib import Path
from narrative_assistant.parsers import (
    get_parser,
    TxtParser,
    DocxParser,
    detect_format,
    DocumentFormat,
)


class TestFormatDetection:
    """Tests para detección de formato de documentos."""

    def test_detect_txt(self, test_data_dir):
        """Detecta formato TXT correctamente."""
        txt_file = test_data_dir / "test_document.txt"
        if txt_file.exists():
            fmt = detect_format(txt_file)
            assert fmt == DocumentFormat.TXT

    def test_detect_docx(self, test_data_dir):
        """Detecta formato DOCX correctamente."""
        docx_file = test_data_dir / "la_regenta_sample.docx"
        if docx_file.exists():
            fmt = detect_format(docx_file)
            assert fmt == DocumentFormat.DOCX

    def test_detect_epub(self, test_data_dir):
        """Detecta formato EPUB correctamente."""
        epub_file = test_data_dir / "don_quijote.epub"
        if epub_file.exists():
            fmt = detect_format(epub_file)
            assert fmt == DocumentFormat.EPUB

    def test_detect_pdf(self, test_data_dir):
        """Detecta formato PDF correctamente."""
        pdf_file = test_data_dir / "lazarillo_de_tormes.pdf"
        if pdf_file.exists():
            fmt = detect_format(pdf_file)
            assert fmt == DocumentFormat.PDF

    def test_detect_unsupported(self, tmp_path):
        """Detecta archivos con extensión desconocida (fallback a TXT o UNKNOWN)."""
        unknown_file = tmp_path / "test.xyz"
        unknown_file.write_text("test")
        fmt = detect_format(unknown_file)
        # Puede detectarse como TXT (fallback) o UNKNOWN
        assert fmt in [DocumentFormat.TXT, DocumentFormat.UNKNOWN]


class TestTxtParser:
    """Tests para el parser de archivos TXT."""

    def test_parse_simple_txt(self, test_data_dir):
        """Parsea archivo TXT simple."""
        txt_file = test_data_dir / "test_document.txt"
        if not txt_file.exists():
            pytest.skip("Test file not found")

        parser = TxtParser()
        result = parser.parse(txt_file)

        assert result.is_success
        doc = result.value
        assert doc is not None
        assert len(doc.full_text) > 0
        assert len(doc.paragraphs) > 0

    def test_parse_with_chapters(self, test_data_dir):
        """Parsea archivo con capítulos."""
        txt_file = test_data_dir / "test_document_rich.txt"
        if not txt_file.exists():
            pytest.skip("Test file not found")

        parser = TxtParser()
        result = parser.parse(txt_file)

        assert result.is_success
        doc = result.value
        assert len(doc.full_text) > 0
        # Verificar que contiene "Capítulo"
        assert "Capítulo" in doc.full_text or "Capítulo" in doc.full_text

    def test_reject_large_file(self, tmp_path):
        """Rechaza archivo excesivamente grande."""
        large_file = tmp_path / "large.txt"
        # Crear archivo > 50 MB
        with open(large_file, "w", encoding="utf-8") as f:
            f.write("x" * (51 * 1024 * 1024))

        parser = TxtParser()
        result = parser.parse(large_file)

        assert result.is_failure
        # Mensaje puede estar en inglés o español
        error_msg = result.error.message.lower()
        assert "large" in error_msg or "grande" in error_msg

    def test_reject_nonexistent_file(self):
        """Rechaza archivo inexistente."""
        parser = TxtParser()
        result = parser.parse(Path("/nonexistent/file.txt"))

        assert result.is_failure


class TestDocxParser:
    """Tests para el parser de archivos DOCX."""

    def test_parse_docx(self, test_data_dir):
        """Parsea archivo DOCX correctamente."""
        docx_file = test_data_dir / "la_regenta_sample.docx"
        if not docx_file.exists():
            pytest.skip("Test file not found")

        parser = DocxParser()
        result = parser.parse(docx_file)

        assert result.is_success
        doc = result.value
        assert doc is not None
        assert len(doc.full_text) > 0
        assert len(doc.paragraphs) > 0

    def test_docx_metadata(self, test_data_dir):
        """Extrae metadatos de DOCX."""
        docx_file = test_data_dir / "la_regenta_sample.docx"
        if not docx_file.exists():
            pytest.skip("Test file not found")

        parser = DocxParser()
        result = parser.parse(docx_file)

        assert result.is_success
        doc = result.value
        # Verificar que tiene metadata
        assert doc.metadata is not None

    def test_reject_corrupted_docx(self, tmp_path):
        """Rechaza DOCX corrupto."""
        corrupt_file = tmp_path / "corrupt.docx"
        corrupt_file.write_bytes(b"not a real docx file")

        parser = DocxParser()
        result = parser.parse(corrupt_file)

        assert result.is_failure


class TestGetParser:
    """Tests para la función get_parser."""

    def test_get_txt_parser(self):
        """Obtiene parser TXT."""
        parser = get_parser(DocumentFormat.TXT)
        assert isinstance(parser, TxtParser)

    def test_get_docx_parser(self):
        """Obtiene parser DOCX."""
        parser = get_parser(DocumentFormat.DOCX)
        assert isinstance(parser, DocxParser)

    def test_unsupported_format(self):
        """Rechaza formato no soportado con excepción."""
        from narrative_assistant.core.errors import UnsupportedFormatError

        with pytest.raises(UnsupportedFormatError):
            get_parser(DocumentFormat.UNKNOWN)
