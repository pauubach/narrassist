"""Tests para HI-09: enrichment invalidation granular."""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

import pytest

# Ensure api-server is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api-server"))


class TestRunCleanupStaleMarking:
    """run_cleanup debe marcar enrichment como stale (no borrar)."""

    def _create_test_db(self):
        """Create an in-memory DB with enrichment_cache table."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("""
            CREATE TABLE enrichment_cache (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                enrichment_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'completed',
                schema_version INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        return conn

    def test_stale_marking_only_affects_completed_entries(self):
        """El UPDATE solo debe marcar 'completed' como 'stale', no 'running'."""
        conn = self._create_test_db()
        project_id = 42

        # Insert entries with different statuses
        conn.execute(
            "INSERT INTO enrichment_cache (project_id, enrichment_type, status) VALUES (?, ?, ?)",
            (project_id, "character_profiles", "completed"),
        )
        conn.execute(
            "INSERT INTO enrichment_cache (project_id, enrichment_type, status) VALUES (?, ?, ?)",
            (project_id, "network_graph", "running"),
        )
        conn.execute(
            "INSERT INTO enrichment_cache (project_id, enrichment_type, status) VALUES (?, ?, ?)",
            (project_id, "voice_analysis", "completed"),
        )
        conn.commit()

        # Simulate the HI-09 UPDATE query from run_cleanup
        stale_count = conn.execute(
            """
            UPDATE enrichment_cache
            SET status = 'stale', updated_at = datetime('now')
            WHERE project_id = ? AND status = 'completed'
            """,
            (project_id,),
        ).rowcount
        conn.commit()

        assert stale_count == 2  # Only the two 'completed' entries

        # Verify statuses
        rows = conn.execute(
            "SELECT enrichment_type, status FROM enrichment_cache WHERE project_id = ? ORDER BY enrichment_type",
            (project_id,),
        ).fetchall()

        statuses = {row[0]: row[1] for row in rows}
        assert statuses["character_profiles"] == "stale"
        assert statuses["network_graph"] == "running"  # Not touched
        assert statuses["voice_analysis"] == "stale"


class TestEnrichmentFallbackStaleNotDelete:
    """HI-09: El fallback debe hacer UPDATE stale, no DELETE."""

    def test_fallback_preserves_cache_structure(self):
        """Fallback stale mark preserves rows (not DELETE)."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("""
            CREATE TABLE enrichment_cache (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                enrichment_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'completed',
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        project_id = 7

        conn.execute(
            "INSERT INTO enrichment_cache (project_id, enrichment_type, status) VALUES (?, ?, ?)",
            (project_id, "prose_metrics", "completed"),
        )
        conn.execute(
            "INSERT INTO enrichment_cache (project_id, enrichment_type, status) VALUES (?, ?, ?)",
            (project_id, "health_report", "completed"),
        )
        conn.commit()

        # Simulate the HI-09 fallback (UPDATE, not DELETE)
        conn.execute(
            """UPDATE enrichment_cache
               SET status = 'stale', updated_at = datetime('now')
               WHERE project_id = ? AND status = 'completed'""",
            (project_id,),
        )
        conn.commit()

        # Rows still exist (not deleted)
        count = conn.execute(
            "SELECT COUNT(*) FROM enrichment_cache WHERE project_id = ?",
            (project_id,),
        ).fetchone()[0]
        assert count == 2

        # All marked as stale
        stale_count = conn.execute(
            "SELECT COUNT(*) FROM enrichment_cache WHERE project_id = ? AND status = 'stale'",
            (project_id,),
        ).fetchone()[0]
        assert stale_count == 2

    def test_fallback_does_not_affect_other_projects(self):
        """Stale marking is scoped to the target project."""
        conn = sqlite3.connect(":memory:")
        conn.execute("""
            CREATE TABLE enrichment_cache (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                enrichment_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'completed',
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        conn.execute(
            "INSERT INTO enrichment_cache (project_id, enrichment_type, status) VALUES (?, ?, ?)",
            (1, "network_graph", "completed"),
        )
        conn.execute(
            "INSERT INTO enrichment_cache (project_id, enrichment_type, status) VALUES (?, ?, ?)",
            (2, "network_graph", "completed"),
        )
        conn.commit()

        # Mark only project 1 as stale
        conn.execute(
            """UPDATE enrichment_cache
               SET status = 'stale', updated_at = datetime('now')
               WHERE project_id = ? AND status = 'completed'""",
            (1,),
        )
        conn.commit()

        # Project 2 unaffected
        status = conn.execute(
            "SELECT status FROM enrichment_cache WHERE project_id = 2",
        ).fetchone()[0]
        assert status == "completed"
