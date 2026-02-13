"""
Tests for Sprint S14 Phase 4: Track changes parser (BK-25).

S14-14: Tests for docx_revisions.py parser.
S14-15: Tests for pass 4 matching in ComparisonService.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from zipfile import ZipFile

import pytest

from narrative_assistant.parsers.docx_revisions import (
    DocxRevisions,
    Revision,
    get_deletion_char_ranges,
    parse_docx_revisions,
)


# ============================================================================
# Helper: create minimal .docx with track changes
# ============================================================================

def _create_docx_with_revisions(path: Path, insertions: list[str] = None, deletions: list[str] = None):
    """Crea un .docx mínimo con marcas de revisión."""
    w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

    runs = []

    # Normal text
    runs.append(f'''
        <w:r>
            <w:t xml:space="preserve">Texto normal del documento. </w:t>
        </w:r>
    ''')

    # Insertions
    for text in (insertions or []):
        runs.append(f'''
        <w:ins w:id="1" w:author="Editor" w:date="2026-01-15T10:00:00Z">
            <w:r>
                <w:t xml:space="preserve">{text}</w:t>
            </w:r>
        </w:ins>
        ''')

    # Deletions
    for text in (deletions or []):
        runs.append(f'''
        <w:del w:id="2" w:author="Corrector" w:date="2026-01-15T11:00:00Z">
            <w:r>
                <w:delText xml:space="preserve">{text}</w:delText>
            </w:r>
        </w:del>
        ''')

    xml_content = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{w_ns}">
  <w:body>
    <w:p>
      {"".join(runs)}
    </w:p>
    <w:p>
      <w:r>
        <w:t>Segundo párrafo sin cambios.</w:t>
      </w:r>
    </w:p>
  </w:body>
</w:document>'''

    with ZipFile(str(path), "w") as zf:
        zf.writestr("word/document.xml", xml_content)
        # Minimal content types
        zf.writestr("[Content_Types].xml", '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
</Types>''')


# ============================================================================
# S14-14: docx_revisions parser tests
# ============================================================================


class TestParseDocxRevisions:
    """Tests para parse_docx_revisions."""

    def test_no_revisions(self, tmp_path):
        """Documento sin revisiones → has_revisions=False."""
        docx_path = tmp_path / "clean.docx"
        _create_docx_with_revisions(docx_path)
        result = parse_docx_revisions(docx_path)

        assert not result.has_revisions
        assert result.total_changes == 0
        assert result.revisions == []

    def test_insertions_detected(self, tmp_path):
        """Inserciones (w:ins) detectadas correctamente."""
        docx_path = tmp_path / "with_ins.docx"
        _create_docx_with_revisions(docx_path, insertions=["texto añadido"])
        result = parse_docx_revisions(docx_path)

        assert result.has_revisions
        assert result.total_insertions == 1
        assert result.total_deletions == 0
        ins = [r for r in result.revisions if r.revision_type == "insert"]
        assert len(ins) == 1
        assert ins[0].text == "texto añadido"
        assert ins[0].author == "Editor"

    def test_deletions_detected(self, tmp_path):
        """Eliminaciones (w:del) detectadas correctamente."""
        docx_path = tmp_path / "with_del.docx"
        _create_docx_with_revisions(docx_path, deletions=["texto eliminado"])
        result = parse_docx_revisions(docx_path)

        assert result.has_revisions
        assert result.total_deletions == 1
        assert result.total_insertions == 0
        dels = [r for r in result.revisions if r.revision_type == "delete"]
        assert len(dels) == 1
        assert dels[0].text == "texto eliminado"
        assert dels[0].author == "Corrector"

    def test_mixed_revisions(self, tmp_path):
        """Inserciones + eliminaciones combinadas."""
        docx_path = tmp_path / "mixed.docx"
        _create_docx_with_revisions(
            docx_path,
            insertions=["nuevo contenido"],
            deletions=["viejo contenido"],
        )
        result = parse_docx_revisions(docx_path)

        assert result.has_revisions
        assert result.total_insertions == 1
        assert result.total_deletions == 1
        assert result.total_changes == 2

    def test_authors_extracted(self, tmp_path):
        """Autores de revisiones extraídos."""
        docx_path = tmp_path / "authors.docx"
        _create_docx_with_revisions(
            docx_path,
            insertions=["añadido"],
            deletions=["eliminado"],
        )
        result = parse_docx_revisions(docx_path)

        assert "Editor" in result.authors
        assert "Corrector" in result.authors

    def test_nonexistent_file(self, tmp_path):
        """Archivo inexistente → resultado vacío."""
        result = parse_docx_revisions(tmp_path / "noexiste.docx")
        assert not result.has_revisions
        assert result.revisions == []

    def test_invalid_zip(self, tmp_path):
        """Archivo corrupto → resultado vacío."""
        bad_path = tmp_path / "corrupt.docx"
        bad_path.write_text("not a zip file")
        result = parse_docx_revisions(bad_path)
        assert not result.has_revisions

    def test_zip_without_document_xml(self, tmp_path):
        """ZIP sin word/document.xml → resultado vacío."""
        docx_path = tmp_path / "no_doc.docx"
        with ZipFile(str(docx_path), "w") as zf:
            zf.writestr("other.xml", "<root/>")
        result = parse_docx_revisions(docx_path)
        assert not result.has_revisions


class TestGetDeletionCharRanges:
    """Tests para get_deletion_char_ranges."""

    def test_with_paragraph_offsets(self):
        """Con offsets de párrafos → rangos absolutos correctos."""
        revisions = DocxRevisions(
            revisions=[
                Revision(
                    revision_type="delete", text="eliminado",
                    paragraph_index=2, char_offset=10,
                ),
            ],
            has_revisions=True,
            total_deletions=1,
        )
        offsets = {0: 0, 1: 500, 2: 1000}
        ranges = get_deletion_char_ranges(revisions, offsets)

        assert len(ranges) == 1
        assert ranges[0] == (1010, 1010 + len("eliminado"))

    def test_without_paragraph_offsets(self):
        """Sin offsets → usa estimación de 500 chars/párrafo."""
        revisions = DocxRevisions(
            revisions=[
                Revision(
                    revision_type="delete", text="borrado",
                    paragraph_index=3, char_offset=5,
                ),
            ],
            has_revisions=True,
            total_deletions=1,
        )
        ranges = get_deletion_char_ranges(revisions)

        assert len(ranges) == 1
        assert ranges[0] == (3 * 500 + 5, 3 * 500 + 5 + len("borrado"))

    def test_skips_non_delete_revisions(self):
        """Solo incluye revisiones de tipo 'delete'."""
        revisions = DocxRevisions(
            revisions=[
                Revision(revision_type="insert", text="añadido", paragraph_index=0),
                Revision(revision_type="delete", text="eliminado", paragraph_index=1),
                Revision(revision_type="format_change", text="formateado", paragraph_index=2),
            ],
            has_revisions=True,
            total_insertions=1,
            total_deletions=1,
        )
        ranges = get_deletion_char_ranges(revisions)
        assert len(ranges) == 1  # Only the delete


# ============================================================================
# S14-15: Pass 4 matching tests
# ============================================================================


class TestComparisonPass4TrackChanges:
    """Tests para pass 4 (track changes) en ComparisonService."""

    def test_alert_in_docx_del_range_gets_text_changed(self):
        """Alerta en rango w:del → resolution_reason='text_changed', confidence=0.95."""
        from narrative_assistant.analysis.comparison import ComparisonService
        from narrative_assistant.persistence.snapshot import SnapshotAlert

        old_alerts = [
            SnapshotAlert(
                alert_type="inconsistency", category="character",
                severity="medium", title="Error en nombre",
                chapter=1, start_char=1050, end_char=1100,
                content_hash="hash_unique",
            ),
        ]

        # w:del range overlaps with alert position
        docx_del_ranges = [(1000, 1200)]

        service = ComparisonService(db=MagicMock())
        mock_conn = MagicMock()
        _, alerts_resolved, _ = service._diff_alerts(
            old_alerts, [], mock_conn,
            doc_diff=None,
            docx_del_ranges=docx_del_ranges,
        )

        assert len(alerts_resolved) == 1
        assert alerts_resolved[0].resolution_reason == "text_changed"
        assert alerts_resolved[0].match_confidence == 0.95

    def test_alert_outside_docx_del_range_gets_detector_improved(self):
        """Alerta fuera de w:del → fallback 'detector_improved'."""
        from narrative_assistant.analysis.comparison import ComparisonService
        from narrative_assistant.persistence.snapshot import SnapshotAlert

        old_alerts = [
            SnapshotAlert(
                alert_type="temporal", category="timeline",
                severity="low", title="Anacronismo",
                chapter=2, start_char=5000, end_char=5100,
                content_hash="hash_other",
            ),
        ]

        docx_del_ranges = [(100, 200)]  # Far from alert

        service = ComparisonService(db=MagicMock())
        mock_conn = MagicMock()
        _, alerts_resolved, _ = service._diff_alerts(
            old_alerts, [], mock_conn,
            doc_diff=None,
            docx_del_ranges=docx_del_ranges,
        )

        assert len(alerts_resolved) == 1
        assert alerts_resolved[0].resolution_reason == "detector_improved"
        assert alerts_resolved[0].match_confidence == 0.5

    def test_pass3_takes_priority_over_pass4(self):
        """Si pass 3 ya asignó razón, pass 4 no la sobreescribe."""
        from narrative_assistant.analysis.comparison import ComparisonService
        from narrative_assistant.analysis.content_diff import (
            ChapterDiff,
            DocumentDiff,
            TextRange,
        )
        from narrative_assistant.persistence.snapshot import SnapshotAlert

        old_alerts = [
            SnapshotAlert(
                alert_type="inconsistency", category="character",
                severity="high", title="Error grave",
                chapter=1, start_char=150, end_char=180,
                content_hash="unique_x",
            ),
        ]

        # Pass 3: content diff says removed
        doc_diff = DocumentDiff(
            chapter_diffs=[
                ChapterDiff(
                    chapter_number=1,
                    status="modified",
                    removed_ranges=[TextRange(start_char=100, end_char=200)],
                )
            ]
        )

        # Pass 4: also in docx del range
        docx_del_ranges = [(100, 200)]

        service = ComparisonService(db=MagicMock())
        mock_conn = MagicMock()
        _, alerts_resolved, _ = service._diff_alerts(
            old_alerts, [], mock_conn,
            doc_diff=doc_diff,
            docx_del_ranges=docx_del_ranges,
        )

        assert len(alerts_resolved) == 1
        # Pass 3 assigned 0.9, pass 4 would assign 0.95 but pass 3 was first
        assert alerts_resolved[0].resolution_reason == "text_changed"
        assert alerts_resolved[0].match_confidence == 0.9  # From pass 3
