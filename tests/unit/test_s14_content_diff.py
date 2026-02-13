"""
Tests for Sprint S14 Phase 1: Content diffing (BK-25).

S14-01: Tests for content_diff module.
S14-02: Tests for pass 3 proximity matching in ComparisonService.
S14-03: Tests for snapshot chapter text persistence.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from narrative_assistant.analysis.content_diff import (
    ChapterDiff,
    DocumentDiff,
    TextRange,
    compute_chapter_diffs,
    diff_chapter_texts,
    is_position_in_modified_area,
    is_position_in_removed_range,
)

# ============================================================================
# S14-01: content_diff module tests
# ============================================================================


class TestDiffChapterTexts:
    """Tests para diff_chapter_texts a nivel párrafo."""

    def test_identical_texts_returns_unchanged(self):
        """Textos idénticos → status unchanged, similarity 1.0."""
        text = "Primer párrafo.\n\nSegundo párrafo.\n\nTercer párrafo."
        diff = diff_chapter_texts(text, text, chapter_number=1)

        assert diff.status == "unchanged"
        assert diff.similarity == 1.0
        assert diff.paragraphs_unchanged == 3
        assert diff.paragraphs_added == 0
        assert diff.paragraphs_removed == 0
        assert len(diff.added_ranges) == 0
        assert len(diff.removed_ranges) == 0

    def test_paragraph_added(self):
        """Añadir un párrafo → detectado como added."""
        old = "Primer párrafo.\n\nSegundo párrafo."
        new = "Primer párrafo.\n\nNuevo párrafo insertado.\n\nSegundo párrafo."
        diff = diff_chapter_texts(old, new, chapter_number=1)

        assert diff.status == "modified"
        assert diff.paragraphs_added >= 1
        assert len(diff.added_ranges) >= 1
        assert any("Nuevo párrafo" in r.text for r in diff.added_ranges)

    def test_paragraph_removed(self):
        """Eliminar un párrafo → detectado como removed."""
        old = "Primer párrafo.\n\nPárrafo que será eliminado.\n\nTercer párrafo."
        new = "Primer párrafo.\n\nTercer párrafo."
        diff = diff_chapter_texts(old, new, chapter_number=1)

        assert diff.status == "modified"
        assert diff.paragraphs_removed >= 1
        assert len(diff.removed_ranges) >= 1
        assert any("eliminado" in r.text for r in diff.removed_ranges)

    def test_paragraph_modified(self):
        """Modificar un párrafo → detectado como replace (removed + added)."""
        old = "Primer párrafo.\n\nSegundo párrafo original.\n\nTercer párrafo."
        new = "Primer párrafo.\n\nSegundo párrafo completamente reescrito.\n\nTercer párrafo."
        diff = diff_chapter_texts(old, new, chapter_number=1)

        assert diff.status == "modified"
        assert diff.similarity > 0.0
        assert diff.similarity < 1.0

    def test_completely_different_texts(self):
        """Textos totalmente distintos → baja similarity."""
        old = "Este es el texto original del capítulo uno."
        new = "Contenido completamente nuevo y diferente para otro capítulo."
        diff = diff_chapter_texts(old, new, chapter_number=1)

        assert diff.status == "modified"
        assert diff.similarity < 0.5

    def test_empty_old_text(self):
        """Texto vacío → todo es 'added'."""
        diff = diff_chapter_texts("", "Nuevo contenido.\n\nOtro párrafo.", chapter_number=1)

        assert diff.status == "modified"
        assert diff.paragraphs_added >= 1

    def test_empty_new_text(self):
        """Texto nuevo vacío → todo es 'removed'."""
        diff = diff_chapter_texts("Contenido anterior.\n\nOtro párrafo.", "", chapter_number=1)

        assert diff.status == "modified"
        assert diff.paragraphs_removed >= 1

    def test_removed_range_has_valid_positions(self):
        """Rangos eliminados tienen posiciones válidas."""
        old = "Inicio.\n\nPárrafo medio que se elimina.\n\nFinal."
        new = "Inicio.\n\nFinal."
        diff = diff_chapter_texts(old, new, chapter_number=2)

        for r in diff.removed_ranges:
            assert r.start_char >= 0
            assert r.end_char > r.start_char
            assert r.length > 0

    def test_chapter_number_preserved(self):
        """El número de capítulo se preserva en el diff."""
        diff = diff_chapter_texts("A", "B", chapter_number=42)
        assert diff.chapter_number == 42


class TestComputeChapterDiffs:
    """Tests para compute_chapter_diffs (documento completo)."""

    def test_no_changes(self):
        """Sin cambios → no has_changes."""
        chapters = {1: "Capítulo uno.", 2: "Capítulo dos."}
        doc_diff = compute_chapter_diffs(chapters, chapters)

        assert not doc_diff.has_changes
        assert len(doc_diff.chapters_added) == 0
        assert len(doc_diff.chapters_removed) == 0

    def test_chapter_added(self):
        """Capítulo nuevo → chapters_added."""
        old = {1: "Cap uno.", 2: "Cap dos."}
        new = {1: "Cap uno.", 2: "Cap dos.", 3: "Cap tres nuevo."}
        doc_diff = compute_chapter_diffs(old, new)

        assert doc_diff.has_changes
        assert 3 in doc_diff.chapters_added
        assert any(d.chapter_number == 3 and d.status == "added"
                    for d in doc_diff.chapter_diffs)

    def test_chapter_removed(self):
        """Capítulo eliminado → chapters_removed."""
        old = {1: "Cap uno.", 2: "Cap dos.", 3: "Cap tres."}
        new = {1: "Cap uno.", 3: "Cap tres."}
        doc_diff = compute_chapter_diffs(old, new)

        assert doc_diff.has_changes
        assert 2 in doc_diff.chapters_removed
        assert any(d.chapter_number == 2 and d.status == "removed"
                    for d in doc_diff.chapter_diffs)

    def test_chapter_modified(self):
        """Capítulo modificado → status modified."""
        old = {1: "Primer párrafo.\n\nSegundo párrafo."}
        new = {1: "Primer párrafo.\n\nPárrafo reescrito."}
        doc_diff = compute_chapter_diffs(old, new)

        assert doc_diff.has_changes
        ch1 = [d for d in doc_diff.chapter_diffs if d.chapter_number == 1][0]
        assert ch1.status == "modified"

    def test_mixed_operations(self):
        """Combinación: capítulo añadido + eliminado + modificado."""
        old = {1: "Cap uno original.", 2: "Cap dos.", 3: "Cap tres."}
        new = {1: "Cap uno modificado.", 3: "Cap tres.", 4: "Cap cuatro nuevo."}
        doc_diff = compute_chapter_diffs(old, new)

        assert 4 in doc_diff.chapters_added
        assert 2 in doc_diff.chapters_removed
        # Chapter 1 modified, chapter 3 unchanged
        ch1 = [d for d in doc_diff.chapter_diffs if d.chapter_number == 1][0]
        ch3 = [d for d in doc_diff.chapter_diffs if d.chapter_number == 3][0]
        assert ch1.status == "modified"
        assert ch3.status == "unchanged"

    def test_empty_old_document(self):
        """Documento vacío anterior → todos los capítulos son nuevos."""
        doc_diff = compute_chapter_diffs({}, {1: "Cap uno.", 2: "Cap dos."})
        assert doc_diff.chapters_added == [1, 2]

    def test_empty_new_document(self):
        """Documento nuevo vacío → todos los capítulos eliminados."""
        doc_diff = compute_chapter_diffs({1: "Cap uno.", 2: "Cap dos."}, {})
        assert doc_diff.chapters_removed == [1, 2]

    def test_diffs_sorted_by_chapter(self):
        """Diffs ordenados por chapter_number."""
        old = {3: "Tres.", 1: "Uno.", 5: "Cinco."}
        new = {1: "Uno.", 3: "Tres modificado.", 5: "Cinco."}
        doc_diff = compute_chapter_diffs(old, new)

        nums = [d.chapter_number for d in doc_diff.chapter_diffs]
        assert nums == sorted(nums)


class TestPositionChecks:
    """Tests para funciones de comprobación de posición."""

    def _make_doc_diff_with_removed(self, chapter, start, end):
        """Crea DocumentDiff con un rango eliminado."""
        return DocumentDiff(
            chapter_diffs=[
                ChapterDiff(
                    chapter_number=chapter,
                    status="modified",
                    removed_ranges=[TextRange(start_char=start, end_char=end, text="removed")],
                )
            ]
        )

    def test_position_in_removed_range(self):
        """Alerta dentro de rango eliminado → True."""
        doc_diff = self._make_doc_diff_with_removed(chapter=1, start=100, end=200)
        assert is_position_in_removed_range(1, 120, 150, doc_diff)

    def test_position_outside_removed_range(self):
        """Alerta fuera de rango eliminado → False."""
        doc_diff = self._make_doc_diff_with_removed(chapter=1, start=100, end=200)
        assert not is_position_in_removed_range(1, 300, 400, doc_diff)

    def test_position_partially_overlaps_removed(self):
        """Alerta parcialmente superpuesta → True."""
        doc_diff = self._make_doc_diff_with_removed(chapter=1, start=100, end=200)
        assert is_position_in_removed_range(1, 150, 250, doc_diff)

    def test_position_different_chapter(self):
        """Alerta en otro capítulo → False."""
        doc_diff = self._make_doc_diff_with_removed(chapter=1, start=100, end=200)
        assert not is_position_in_removed_range(2, 120, 150, doc_diff)

    def test_position_in_modified_area_with_margin(self):
        """Alerta cerca de rango eliminado (dentro de margen) → True."""
        doc_diff = self._make_doc_diff_with_removed(chapter=1, start=100, end=200)
        # Position 250-300 is 50 chars away, within default margin of 200
        assert is_position_in_modified_area(1, 250, 300, doc_diff, margin=200)

    def test_position_far_from_modified_area(self):
        """Alerta lejos de área modificada → False."""
        doc_diff = self._make_doc_diff_with_removed(chapter=1, start=100, end=200)
        assert not is_position_in_modified_area(1, 1000, 1100, doc_diff, margin=200)


# ============================================================================
# S14-02: ComparisonService pass 3 tests
# ============================================================================


class TestComparisonServicePass3:
    """Tests para pass 3 (proximity matching) en ComparisonService."""

    def test_resolved_alert_in_removed_text_gets_text_changed_reason(self):
        """Alerta resuelta en texto eliminado → resolution_reason='text_changed'."""
        from narrative_assistant.analysis.comparison import AlertDiff, ComparisonService
        from narrative_assistant.persistence.snapshot import SnapshotAlert

        # Old alert at chapter 1, position 100-200
        old_alerts = [
            SnapshotAlert(
                alert_type="inconsistency", category="character",
                severity="medium", title="Error en nombre",
                chapter=1, start_char=120, end_char=180,
                content_hash="old_hash_1",
            ),
        ]

        # No current alerts (the alert was resolved)
        current_rows = []

        # Doc diff: text was removed at chapter 1, 100-250
        doc_diff = DocumentDiff(
            chapter_diffs=[
                ChapterDiff(
                    chapter_number=1,
                    status="modified",
                    removed_ranges=[TextRange(start_char=100, end_char=250)],
                )
            ]
        )

        service = ComparisonService(db=MagicMock())
        mock_conn = MagicMock()
        alerts_new, alerts_resolved, unchanged = service._diff_alerts(
            old_alerts, current_rows, mock_conn, doc_diff=doc_diff
        )

        assert len(alerts_resolved) == 1
        assert alerts_resolved[0].resolution_reason == "text_changed"
        assert alerts_resolved[0].match_confidence >= 0.7

    def test_resolved_alert_no_position_gets_detector_improved(self):
        """Alerta sin posición → resolution_reason='detector_improved'."""
        from narrative_assistant.analysis.comparison import ComparisonService
        from narrative_assistant.persistence.snapshot import SnapshotAlert

        old_alerts = [
            SnapshotAlert(
                alert_type="inconsistency", category="character",
                severity="medium", title="Error vago",
                chapter=1, start_char=None, end_char=None,
                content_hash="old_hash_2",
            ),
        ]

        service = ComparisonService(db=MagicMock())
        mock_conn = MagicMock()
        _, alerts_resolved, _ = service._diff_alerts(
            old_alerts, [], mock_conn,
            doc_diff=DocumentDiff(chapter_diffs=[
                ChapterDiff(chapter_number=1, status="modified")
            ]),
        )

        assert len(alerts_resolved) == 1
        assert alerts_resolved[0].resolution_reason == "detector_improved"
        assert alerts_resolved[0].match_confidence == 0.5

    def test_matched_alerts_not_in_resolved(self):
        """Alertas que matchean (pass 1/2) no aparecen como resolved."""
        from narrative_assistant.analysis.comparison import ComparisonService
        from narrative_assistant.persistence.snapshot import SnapshotAlert

        old_alerts = [
            SnapshotAlert(
                alert_type="inconsistency", category="character",
                severity="medium", title="Error persistente",
                chapter=1, content_hash="same_hash",
            ),
        ]

        # Current alert with same hash
        current_rows = [
            ("inconsistency", "character", "medium", "Error persistente",
             "desc", 1, "same_hash", 0.8, "[]", None, None),
        ]

        service = ComparisonService(db=MagicMock())
        mock_conn = MagicMock()
        alerts_new, alerts_resolved, unchanged = service._diff_alerts(
            old_alerts, current_rows, mock_conn, doc_diff=None
        )

        assert len(alerts_new) == 0
        assert len(alerts_resolved) == 0
        assert unchanged == 1

    def test_alert_near_modified_area_gets_text_changed(self):
        """Alerta cerca de área modificada (con margen) → text_changed."""
        from narrative_assistant.analysis.comparison import ComparisonService
        from narrative_assistant.persistence.snapshot import SnapshotAlert

        old_alerts = [
            SnapshotAlert(
                alert_type="temporal", category="timeline",
                severity="low", title="Anacronismo",
                chapter=2, start_char=350, end_char=400,
                content_hash="unique_hash",
            ),
        ]

        # Text removed at 100-200 — alert at 350 is within margin (200)
        doc_diff = DocumentDiff(
            chapter_diffs=[
                ChapterDiff(
                    chapter_number=2,
                    status="modified",
                    removed_ranges=[TextRange(start_char=100, end_char=200)],
                )
            ]
        )

        service = ComparisonService(db=MagicMock())
        mock_conn = MagicMock()
        _, alerts_resolved, _ = service._diff_alerts(
            old_alerts, [], mock_conn, doc_diff=doc_diff
        )

        assert len(alerts_resolved) == 1
        assert alerts_resolved[0].resolution_reason == "text_changed"
        # Near but not in range → lower confidence
        assert alerts_resolved[0].match_confidence == 0.7


# ============================================================================
# S14-03: Snapshot chapter text persistence tests
# ============================================================================


class TestSnapshotChapterTexts:
    """Tests para persistencia de textos de capítulos en snapshots."""

    def _make_repo(self):
        """Crea SnapshotRepository con DB mockeada."""
        from narrative_assistant.persistence.snapshot import SnapshotRepository

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 42
        mock_conn.execute.return_value = mock_cursor

        mock_db = MagicMock()
        mock_db.connection.return_value.__enter__ = lambda s: mock_conn
        mock_db.connection.return_value.__exit__ = MagicMock(return_value=False)

        repo = SnapshotRepository(db=mock_db)
        return repo, mock_conn

    def test_get_snapshot_chapter_texts_returns_dict(self):
        """get_snapshot_chapter_texts retorna dict {chapter_number: text}."""
        from narrative_assistant.persistence.snapshot import SnapshotRepository

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [
            (1, "Texto capítulo 1"),
            (2, "Texto capítulo 2"),
            (3, "Texto capítulo 3"),
        ]

        mock_db = MagicMock()
        mock_db.connection.return_value.__enter__ = lambda s: mock_conn
        mock_db.connection.return_value.__exit__ = MagicMock(return_value=False)

        repo = SnapshotRepository(db=mock_db)
        result = repo.get_snapshot_chapter_texts(42)

        assert result == {
            1: "Texto capítulo 1",
            2: "Texto capítulo 2",
            3: "Texto capítulo 3",
        }

    def test_get_snapshot_chapter_texts_empty(self):
        """Sin capítulos → dict vacío."""
        from narrative_assistant.persistence.snapshot import SnapshotRepository

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []

        mock_db = MagicMock()
        mock_db.connection.return_value.__enter__ = lambda s: mock_conn
        mock_db.connection.return_value.__exit__ = MagicMock(return_value=False)

        repo = SnapshotRepository(db=mock_db)
        result = repo.get_snapshot_chapter_texts(99)

        assert result == {}

    def test_create_snapshot_persists_chapter_texts(self):
        """create_snapshot inserta textos de capítulos."""
        repo, mock_conn = self._make_repo()

        # Mock responses in order:
        # 1. SELECT document_fingerprint → ("fp123",)
        # 2. SELECT COUNT(*) alerts → (5,)
        # 3. SELECT COUNT(*) entities → (3,)
        # 4. INSERT analysis_snapshots → cursor with lastrowid=42
        # 5. SELECT alerts → []
        # 6. SELECT entities → []
        # 7. SELECT chapters → [(1, "Cap 1 text"), (2, "Cap 2 text")]
        # 8+. INSERT snapshot_chapters calls

        call_count = [0]
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 42

        def mock_execute(sql, params=None):
            call_count[0] += 1
            result = MagicMock()
            result.lastrowid = 42

            if "document_fingerprint" in sql:
                result.fetchone.return_value = ("fp123",)
            elif "COUNT(*) FROM alerts" in sql:
                result.fetchone.return_value = (5,)
            elif "COUNT(*) FROM entities" in sql:
                result.fetchone.return_value = (3,)
            elif "FROM alerts WHERE" in sql:
                result.fetchall.return_value = []
            elif "FROM entities WHERE" in sql:
                result.fetchall.return_value = []
            elif "FROM chapters WHERE" in sql:
                result.fetchall.return_value = [
                    (1, "Texto del capítulo 1"),
                    (2, "Texto del capítulo 2"),
                ]
            return result

        mock_conn.execute.side_effect = mock_execute

        snapshot_id = repo.create_snapshot(project_id=1)
        assert snapshot_id == 42

        # Verify snapshot_chapters INSERT was called
        insert_calls = [
            c for c in mock_conn.execute.call_args_list
            if len(c[0]) > 0 and "snapshot_chapters" in str(c[0][0])
        ]
        assert len(insert_calls) == 2  # 2 chapters


# ============================================================================
# AlertDiff serialization with new fields
# ============================================================================


class TestAlertDiffSerialization:
    """Tests para serialización de AlertDiff con campos S14."""

    def test_to_dict_includes_resolution_fields(self):
        """ComparisonReport.to_dict() incluye resolution_reason y match_confidence."""
        from narrative_assistant.analysis.comparison import (
            AlertDiff,
            ComparisonReport,
        )

        report = ComparisonReport(
            project_id=1,
            snapshot_id=1,
            snapshot_created_at="2026-01-01",
            document_fingerprint_changed=True,
            alerts_resolved=[
                AlertDiff(
                    alert_type="inconsistency",
                    category="character",
                    severity="medium",
                    title="Error resuelto",
                    resolution_reason="text_changed",
                    match_confidence=0.9,
                    start_char=100,
                    end_char=200,
                ),
            ],
        )

        d = report.to_dict()
        resolved = d["alerts"]["resolved"]
        assert len(resolved) == 1
        assert resolved[0]["resolution_reason"] == "text_changed"
        assert resolved[0]["match_confidence"] == 0.9
        assert resolved[0]["start_char"] == 100
        assert resolved[0]["end_char"] == 200

    def test_to_dict_new_alerts_have_positions(self):
        """Alertas nuevas también tienen start_char/end_char."""
        from narrative_assistant.analysis.comparison import (
            AlertDiff,
            ComparisonReport,
        )

        report = ComparisonReport(
            project_id=1,
            snapshot_id=1,
            snapshot_created_at="2026-01-01",
            document_fingerprint_changed=False,
            alerts_new=[
                AlertDiff(
                    alert_type="temporal",
                    category="timeline",
                    severity="low",
                    title="Nuevo error",
                    start_char=50,
                    end_char=100,
                ),
            ],
        )

        d = report.to_dict()
        new_alerts = d["alerts"]["new"]
        assert len(new_alerts) == 1
        assert new_alerts[0]["start_char"] == 50
        assert new_alerts[0]["end_char"] == 100


# ============================================================================
# S14-06/07/08: Alert linking + API endpoint tests
# ============================================================================


class TestAlertLinking:
    """Tests para alert linking (S14-06)."""

    def test_write_alert_links_by_hash(self):
        """Links por content_hash exacto → confidence 1.0."""
        from narrative_assistant.analysis.comparison import ComparisonService
        from narrative_assistant.persistence.snapshot import SnapshotAlert

        # Setup mock DB
        mock_conn = MagicMock()
        mock_db = MagicMock()
        mock_db.connection.return_value.__enter__ = lambda s: mock_conn
        mock_db.connection.return_value.__exit__ = MagicMock(return_value=False)

        # Current alerts in DB
        mock_conn.execute.return_value.fetchall.return_value = [
            (101, "hash_abc", "inconsistency", 1, "Error nombre", "[]"),
        ]

        # Snapshot alerts
        snapshot_alerts = [
            SnapshotAlert(
                alert_type="inconsistency", category="character",
                severity="medium", title="Error nombre",
                content_hash="hash_abc", snapshot_alert_id=50,
            ),
        ]

        service = ComparisonService(db=mock_db)
        with patch.object(service, '_get_db', return_value=mock_db):
            with patch(
                "narrative_assistant.persistence.snapshot.SnapshotRepository.get_snapshot_alerts",
                return_value=snapshot_alerts,
            ):
                links = service._write_alert_links(project_id=1, snapshot_id=1)

        # Should have written 1 link
        assert links == 1
        # Verify UPDATE was called with correct params
        update_calls = [
            c for c in mock_conn.execute.call_args_list
            if "UPDATE alerts" in str(c[0][0])
        ]
        assert len(update_calls) == 1
        _, params = update_calls[0][0]
        assert params == (50, 1.0, 101)  # (snap_alert_id, confidence, alert_id)

    def test_write_alert_links_by_fuzzy_key(self):
        """Links por key (type+chapter+title) → confidence 0.7."""
        from narrative_assistant.analysis.comparison import ComparisonService
        from narrative_assistant.persistence.snapshot import SnapshotAlert

        mock_conn = MagicMock()
        mock_db = MagicMock()
        mock_db.connection.return_value.__enter__ = lambda s: mock_conn
        mock_db.connection.return_value.__exit__ = MagicMock(return_value=False)

        # Current alert with different hash
        mock_conn.execute.return_value.fetchall.return_value = [
            (102, "new_hash_xyz", "temporal", 3, "Anacronismo detectado", "[]"),
        ]

        snapshot_alerts = [
            SnapshotAlert(
                alert_type="temporal", category="timeline",
                severity="low", title="Anacronismo detectado",
                chapter=3, content_hash="old_hash_different",
                snapshot_alert_id=60,
            ),
        ]

        service = ComparisonService(db=mock_db)
        with patch.object(service, '_get_db', return_value=mock_db):
            with patch(
                "narrative_assistant.persistence.snapshot.SnapshotRepository.get_snapshot_alerts",
                return_value=snapshot_alerts,
            ):
                links = service._write_alert_links(project_id=1, snapshot_id=1)

        assert links == 1
        update_calls = [
            c for c in mock_conn.execute.call_args_list
            if "UPDATE alerts" in str(c[0][0])
        ]
        assert len(update_calls) == 1
        _, params = update_calls[0][0]
        assert params == (60, 0.7, 102)

    def test_write_alert_links_no_match(self):
        """Sin match → no se escriben links."""
        from narrative_assistant.analysis.comparison import ComparisonService
        from narrative_assistant.persistence.snapshot import SnapshotAlert

        mock_conn = MagicMock()
        mock_db = MagicMock()
        mock_db.connection.return_value.__enter__ = lambda s: mock_conn
        mock_db.connection.return_value.__exit__ = MagicMock(return_value=False)

        # Current alert with no matching hash/key
        mock_conn.execute.return_value.fetchall.return_value = [
            (103, "unique_hash", "style", 5, "Error de estilo", "[]"),
        ]

        snapshot_alerts = [
            SnapshotAlert(
                alert_type="inconsistency", category="character",
                severity="high", title="Otro error distinto",
                chapter=1, content_hash="other_hash",
                snapshot_alert_id=70,
            ),
        ]

        service = ComparisonService(db=mock_db)
        with patch.object(service, '_get_db', return_value=mock_db):
            with patch(
                "narrative_assistant.persistence.snapshot.SnapshotRepository.get_snapshot_alerts",
                return_value=snapshot_alerts,
            ):
                links = service._write_alert_links(project_id=1, snapshot_id=1)

        assert links == 0


class TestMarkResolvedEndpoint:
    """Tests para endpoint mark-resolved (S14-07)."""

    def test_mark_resolved_endpoint_exists(self):
        """Verificar que el endpoint mark-resolved existe."""
        import sys
        sys.path.insert(0, "api-server")
        try:
            from routers.alerts import mark_alert_resolved
            assert callable(mark_alert_resolved)
        finally:
            sys.path.pop(0)

    def test_comparison_detail_endpoint_exists(self):
        """Verificar que el endpoint comparison/detail existe."""
        import sys
        sys.path.insert(0, "api-server")
        try:
            from routers.alerts import get_comparison_detail
            assert callable(get_comparison_detail)
        finally:
            sys.path.pop(0)

    def test_alert_response_has_revision_fields(self):
        """AlertResponse incluye campos de Revision Intelligence."""
        import sys
        sys.path.insert(0, "api-server")
        try:
            from deps import AlertResponse
            fields = AlertResponse.model_fields
            assert "previous_alert_summary" in fields
            assert "match_confidence" in fields
            assert "resolution_reason" in fields
        finally:
            sys.path.pop(0)

    def test_mark_resolved_request_model(self):
        """MarkResolvedRequest tiene campo resolution_reason."""
        import sys
        sys.path.insert(0, "api-server")
        try:
            from deps import MarkResolvedRequest
            req = MarkResolvedRequest()
            assert req.resolution_reason == "manual"
            req2 = MarkResolvedRequest(resolution_reason="text_changed")
            assert req2.resolution_reason == "text_changed"
        finally:
            sys.path.pop(0)
