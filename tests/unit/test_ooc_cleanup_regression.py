"""
Regression test: empty OOC report must clear stale rows from ooc_events.

Before the fix, `analyze_ooc_subphase()` only issued DELETE when
`ooc_report.events` was non-empty, so a re-analysis that found zero
events would leave stale rows in the database.
"""

import sqlite3
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure api-server is importable
_api_server = str(Path(__file__).resolve().parents[2] / "api-server")
if _api_server not in sys.path:
    sys.path.insert(0, _api_server)


# ── Helpers ──────────────────────────────────────────────────────────────


def _create_ooc_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ooc_events (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            entity_id INTEGER,
            entity_name TEXT,
            deviation_type TEXT,
            severity TEXT,
            description TEXT,
            expected TEXT,
            actual TEXT,
            chapter INTEGER,
            excerpt TEXT,
            confidence REAL,
            is_intentional INTEGER DEFAULT 0
        )
    """)
    conn.commit()


def _seed_ooc_event(conn: sqlite3.Connection, project_id: int, entity_name: str = "Don Quijote"):
    conn.execute(
        """INSERT INTO ooc_events
           (project_id, entity_id, entity_name, deviation_type, severity,
            description, expected, actual, chapter, excerpt, confidence, is_intentional)
           VALUES (?, 1, ?, 'speech', 'high', 'test', 'formal', 'vulgar', 1, '...', 0.9, 0)""",
        (project_id, entity_name),
    )
    conn.commit()


def _count_ooc(conn: sqlite3.Connection, project_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM ooc_events WHERE project_id = ?", (project_id,)
    ).fetchone()
    return row[0]


def _mock_db_session(conn: sqlite3.Connection):
    @contextmanager
    def connection():
        yield conn

    session = MagicMock()
    session.connection = connection
    return session


@dataclass
class FakeEntity:
    entity_type: str = "PER"
    name: str = "Don Quijote"


@dataclass
class FakeProfile:
    name: str = "Don Quijote"


@dataclass
class FakeOOCReport:
    events: list = field(default_factory=list)
    characters_analyzed: int = 1
    total_deviations: int = 0


# ── Tests ────────────────────────────────────────────────────────────────


class TestOOCCleanupOnEmptyReport:
    """Verify that a re-analysis with 0 OOC events clears stale DB rows."""

    def test_empty_report_deletes_stale_events(self):
        """Core regression: OOC report with events=[] must DELETE old rows."""
        conn = sqlite3.connect(":memory:")
        _create_ooc_table(conn)

        project_id = 42
        _seed_ooc_event(conn, project_id, "Don Quijote")
        _seed_ooc_event(conn, project_id, "Sancho")
        assert _count_ooc(conn, project_id) == 2

        db_session = _mock_db_session(conn)
        empty_report = FakeOOCReport(events=[], characters_analyzed=2, total_deviations=0)

        with (
            patch(
                "narrative_assistant.analysis.character_profiling.CharacterProfiler"
            ) as MockProfiler,
            patch(
                "narrative_assistant.analysis.out_of_character.OutOfCharacterDetector"
            ) as MockDetector,
        ):
            MockProfiler.return_value.build_profiles.return_value = [FakeProfile()]
            MockDetector.return_value.detect.return_value = empty_report

            from routers._consistency_subphases import analyze_ooc_subphase

            result = analyze_ooc_subphase(
                project_id=project_id,
                entities=[FakeEntity()],
                chapters_data=[{"chapter_number": 1, "content": "texto de prueba"}],
                db_session=db_session,
            )

        assert result is not None
        assert result.events == []
        assert _count_ooc(conn, project_id) == 0, "Stale OOC rows should have been deleted"

    def test_report_with_events_replaces_old(self):
        """Normal case: new events replace old ones."""
        conn = sqlite3.connect(":memory:")
        _create_ooc_table(conn)

        project_id = 42
        _seed_ooc_event(conn, project_id, "OldEntity")
        assert _count_ooc(conn, project_id) == 1

        db_session = _mock_db_session(conn)

        @dataclass
        class FakeEvent:
            entity_id: int = 2
            entity_name: str = "Dulcinea"
            deviation_type: str = "speech"
            severity: str = "medium"
            description: str = "new deviation"
            expected: str = "gentle"
            actual: str = "aggressive"
            chapter: int = 3
            excerpt: str = "..."
            confidence: float = 0.8
            is_intentional: bool = False

        new_report = FakeOOCReport(
            events=[FakeEvent()], characters_analyzed=1, total_deviations=1
        )

        with (
            patch(
                "narrative_assistant.analysis.character_profiling.CharacterProfiler"
            ) as MockProfiler,
            patch(
                "narrative_assistant.analysis.out_of_character.OutOfCharacterDetector"
            ) as MockDetector,
        ):
            MockProfiler.return_value.build_profiles.return_value = [FakeProfile()]
            MockDetector.return_value.detect.return_value = new_report

            from routers._consistency_subphases import analyze_ooc_subphase

            result = analyze_ooc_subphase(
                project_id=project_id,
                entities=[FakeEntity()],
                chapters_data=[{"chapter_number": 1, "content": "texto"}],
                db_session=db_session,
            )

        assert _count_ooc(conn, project_id) == 1
        row = conn.execute(
            "SELECT entity_name FROM ooc_events WHERE project_id = ?", (project_id,)
        ).fetchone()
        assert row[0] == "Dulcinea", "Old event should be replaced by new one"

    def test_no_character_entities_skips_everything(self):
        """When no character entities exist, return None without touching DB."""
        conn = sqlite3.connect(":memory:")
        _create_ooc_table(conn)

        project_id = 42
        _seed_ooc_event(conn, project_id, "Stale")
        db_session = _mock_db_session(conn)

        from routers._consistency_subphases import analyze_ooc_subphase

        result = analyze_ooc_subphase(
            project_id=project_id,
            entities=[],  # No character entities
            chapters_data=[{"chapter_number": 1, "content": "texto"}],
            db_session=db_session,
        )

        assert result is None
        assert _count_ooc(conn, project_id) == 1, "Stale rows untouched when skipping"

    def test_other_project_rows_untouched(self):
        """DELETE only affects the target project_id, not others."""
        conn = sqlite3.connect(":memory:")
        _create_ooc_table(conn)

        _seed_ooc_event(conn, project_id=1, entity_name="Project1Entity")
        _seed_ooc_event(conn, project_id=2, entity_name="Project2Entity")
        assert _count_ooc(conn, 1) == 1
        assert _count_ooc(conn, 2) == 1

        db_session = _mock_db_session(conn)
        empty_report = FakeOOCReport(events=[])

        with (
            patch(
                "narrative_assistant.analysis.character_profiling.CharacterProfiler"
            ) as MockProfiler,
            patch(
                "narrative_assistant.analysis.out_of_character.OutOfCharacterDetector"
            ) as MockDetector,
        ):
            MockProfiler.return_value.build_profiles.return_value = [FakeProfile()]
            MockDetector.return_value.detect.return_value = empty_report

            from routers._consistency_subphases import analyze_ooc_subphase

            analyze_ooc_subphase(
                project_id=1,
                entities=[FakeEntity()],
                chapters_data=[{"chapter_number": 1, "content": "texto"}],
                db_session=db_session,
            )

        assert _count_ooc(conn, 1) == 0, "Target project rows cleared"
        assert _count_ooc(conn, 2) == 1, "Other project rows untouched"
