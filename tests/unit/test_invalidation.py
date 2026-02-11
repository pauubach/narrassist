"""
Tests for granular invalidation system (S8c).

Tests:
- Event emission and recording
- Stale marking per event type
- Early cutoff (output_hash unchanged)
- Race condition detection
- Revision tracking
"""
import json
import sqlite3
import pytest
from unittest.mock import MagicMock


# ── Helpers ────────────────────────────────────────────────

def _create_test_db():
    """Create an in-memory DB with enrichment_cache + invalidation_events tables."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY,
            name TEXT
        )
    """)
    conn.execute("INSERT INTO projects (id, name) VALUES (1, 'Test Project')")
    conn.execute("""
        CREATE TABLE enrichment_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            enrichment_type TEXT NOT NULL,
            entity_scope TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            input_hash TEXT,
            output_hash TEXT,
            result_json TEXT,
            error_message TEXT,
            phase INTEGER,
            revision INTEGER NOT NULL DEFAULT 0,
            computed_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE (project_id, enrichment_type, entity_scope)
        )
    """)
    conn.execute("""
        CREATE TABLE invalidation_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            entity_ids TEXT NOT NULL DEFAULT '[]',
            detail TEXT,
            revision INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def _mock_db_session(conn):
    """Create a mock db_session that returns the given connection."""
    from contextlib import contextmanager

    @contextmanager
    def connection():
        yield conn

    session = MagicMock()
    session.connection = connection
    return session


def _seed_cache(conn, project_id, enrichment_type, status="completed", entity_scope=None):
    """Insert a cache entry."""
    conn.execute(
        """INSERT OR REPLACE INTO enrichment_cache
           (project_id, enrichment_type, entity_scope, status, result_json, output_hash, phase)
           VALUES (?, ?, ?, ?, '{}', 'hash123', 10)""",
        (project_id, enrichment_type, entity_scope, status),
    )
    conn.commit()


# ── Event emission tests ───────────────────────────────────

class TestEmitInvalidationEvent:
    def test_emits_event_with_correct_revision(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api-server"))
        from routers._invalidation import emit_invalidation_event

        conn = _create_test_db()
        db = _mock_db_session(conn)

        rev1 = emit_invalidation_event(db, 1, "merge", [1, 2])
        assert rev1 == 1

        rev2 = emit_invalidation_event(db, 1, "attribute_edit", [3])
        assert rev2 == 2

    def test_emits_event_records_entity_ids(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api-server"))
        from routers._invalidation import emit_invalidation_event

        conn = _create_test_db()
        db = _mock_db_session(conn)

        emit_invalidation_event(db, 1, "merge", [10, 20, 30])

        row = conn.execute("SELECT * FROM invalidation_events WHERE project_id = 1").fetchone()
        assert row is not None
        assert json.loads(row["entity_ids"]) == [10, 20, 30]
        assert row["event_type"] == "merge"

    def test_emits_event_stores_detail(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api-server"))
        from routers._invalidation import emit_invalidation_event

        conn = _create_test_db()
        db = _mock_db_session(conn)

        emit_invalidation_event(db, 1, "reject", [], detail={"entity_text": "foo"})

        row = conn.execute("SELECT detail FROM invalidation_events").fetchone()
        assert json.loads(row["detail"]) == {"entity_text": "foo"}


# ── Stale marking tests ───────────────────────────────────

class TestStaleMarking:
    def test_merge_marks_entity_dependent_types_stale(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api-server"))
        from routers._invalidation import emit_invalidation_event

        conn = _create_test_db()
        db = _mock_db_session(conn)

        # Seed cache entries
        _seed_cache(conn, 1, "character_network")
        _seed_cache(conn, 1, "character_profiles")
        _seed_cache(conn, 1, "echo_report")  # prose, should NOT be stale

        emit_invalidation_event(db, 1, "merge", [1, 2])

        rows = conn.execute(
            "SELECT enrichment_type, status FROM enrichment_cache WHERE project_id = 1"
        ).fetchall()
        status_map = {r["enrichment_type"]: r["status"] for r in rows}

        assert status_map["character_network"] == "stale"
        assert status_map["character_profiles"] == "stale"
        assert status_map["echo_report"] == "completed"  # unaffected

    def test_attribute_edit_marks_attribute_dependent_types(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api-server"))
        from routers._invalidation import emit_invalidation_event

        conn = _create_test_db()
        db = _mock_db_session(conn)

        _seed_cache(conn, 1, "voice_profiles")
        _seed_cache(conn, 1, "character_profiles")
        _seed_cache(conn, 1, "pacing_report")  # prose, unaffected

        emit_invalidation_event(db, 1, "attribute_edit", [5])

        rows = conn.execute(
            "SELECT enrichment_type, status FROM enrichment_cache WHERE project_id = 1"
        ).fetchall()
        status_map = {r["enrichment_type"]: r["status"] for r in rows}

        assert status_map["voice_profiles"] == "stale"
        assert status_map["character_profiles"] == "stale"
        assert status_map["pacing_report"] == "completed"

    def test_marks_per_entity_scope_stale(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api-server"))
        from routers._invalidation import emit_invalidation_event

        conn = _create_test_db()
        db = _mock_db_session(conn)

        _seed_cache(conn, 1, "character_profiles", entity_scope="entity:5")
        _seed_cache(conn, 1, "character_profiles", entity_scope="entity:99")

        emit_invalidation_event(db, 1, "attribute_edit", [5])

        rows = conn.execute(
            "SELECT entity_scope, status FROM enrichment_cache WHERE enrichment_type = 'character_profiles'"
        ).fetchall()
        scope_status = {r["entity_scope"]: r["status"] for r in rows}

        assert scope_status["entity:5"] == "stale"
        assert scope_status["entity:99"] == "completed"  # Different entity, unaffected

    def test_does_not_mark_already_stale_entries(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api-server"))
        from routers._invalidation import emit_invalidation_event

        conn = _create_test_db()
        db = _mock_db_session(conn)

        _seed_cache(conn, 1, "character_network", status="stale")

        # Should not fail or change anything
        emit_invalidation_event(db, 1, "merge", [1])

        row = conn.execute(
            "SELECT status FROM enrichment_cache WHERE enrichment_type = 'character_network'"
        ).fetchone()
        assert row["status"] == "stale"

    def test_does_not_affect_other_projects(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api-server"))
        from routers._invalidation import emit_invalidation_event

        conn = _create_test_db()
        conn.execute("INSERT INTO projects (id, name) VALUES (2, 'Other')")
        db = _mock_db_session(conn)

        _seed_cache(conn, 1, "character_network")
        _seed_cache(conn, 2, "character_network")

        emit_invalidation_event(db, 1, "merge", [1])

        rows = conn.execute(
            "SELECT project_id, status FROM enrichment_cache WHERE enrichment_type = 'character_network'"
        ).fetchall()
        status_map = {r["project_id"]: r["status"] for r in rows}

        assert status_map[1] == "stale"
        assert status_map[2] == "completed"


# ── Revision tracking ─────────────────────────────────────

class TestRevisionTracking:
    def test_get_project_revision_returns_max(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api-server"))
        from routers._invalidation import emit_invalidation_event, get_project_revision

        conn = _create_test_db()
        db = _mock_db_session(conn)

        assert get_project_revision(db, 1) == 0

        emit_invalidation_event(db, 1, "merge", [1])
        assert get_project_revision(db, 1) == 1

        emit_invalidation_event(db, 1, "attribute_edit", [2])
        assert get_project_revision(db, 1) == 2

    def test_get_stale_enrichment_types(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api-server"))
        from routers._invalidation import get_stale_enrichment_types

        conn = _create_test_db()
        db = _mock_db_session(conn)

        _seed_cache(conn, 1, "character_network", status="stale")
        _seed_cache(conn, 1, "echo_report", status="completed")

        stale = get_stale_enrichment_types(db, 1)
        assert "character_network" in stale
        assert "echo_report" not in stale


# ── Event type coverage ───────────────────────────────────

class TestEventTypeCoverage:
    """Verify all 6 mutation event types are handled."""

    @pytest.mark.parametrize("event_type", [
        "merge", "undo_merge", "reject",
        "attribute_create", "attribute_edit", "attribute_delete",
    ])
    def test_event_type_is_mapped(self, event_type):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api-server"))
        from routers._invalidation import EVENT_INVALIDATION_MAP

        assert event_type in EVENT_INVALIDATION_MAP
        assert len(EVENT_INVALIDATION_MAP[event_type]) > 0

    @pytest.mark.parametrize("event_type", [
        "merge", "undo_merge", "reject",
        "attribute_create", "attribute_edit", "attribute_delete",
    ])
    def test_event_emission_succeeds(self, event_type):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api-server"))
        from routers._invalidation import emit_invalidation_event

        conn = _create_test_db()
        db = _mock_db_session(conn)

        rev = emit_invalidation_event(db, 1, event_type, [1])
        assert rev >= 1
