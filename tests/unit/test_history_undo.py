"""
Tests para el sistema universal de undo/redo (HistoryManager).

Cobertura:
- record() y get_entry()
- undo(), undo_last(), undo_batch()
- can_undo() y check_dependencies()
- Todos los handlers: entity (merge, create, delete, update),
  alert (resolve, dismiss), attribute (add, update, verify, delete),
  relationship (create, update, delete)
- Edge cases: double undo, entry inexistente, acción no-undoable,
  dependencias, batch parcial
"""
import json
import sqlite3

import pytest

from narrative_assistant.persistence.history import (
    ChangeType,
    HistoryEntry,
    HistoryManager,
    UNDOABLE_ACTIONS,
    UndoResult,
)


# ─── Fixture: DB en memoria con schema completo ────────────────────────

@pytest.fixture()
def db():
    """Crea una DB SQLite :memory: con las tablas necesarias para undo."""
    from unittest.mock import MagicMock

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=OFF")  # Simplificar tests

    # --- review_history (tabla principal del sistema de undo) ---
    conn.execute("""
        CREATE TABLE review_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            target_type TEXT,
            target_id INTEGER,
            old_value_json TEXT,
            new_value_json TEXT,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            batch_id TEXT,
            depends_on_ids TEXT DEFAULT '[]',
            schema_version INTEGER DEFAULT 25,
            undone_at TEXT
        )
    """)

    # --- entities ---
    conn.execute("""
        CREATE TABLE entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            canonical_name TEXT NOT NULL,
            entity_type TEXT DEFAULT 'character',
            importance TEXT DEFAULT 'primary',
            mention_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            merged_from_ids TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # --- entity_mentions ---
    conn.execute("""
        CREATE TABLE entity_mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER NOT NULL,
            text TEXT,
            chapter_id INTEGER
        )
    """)

    # --- entity_attributes ---
    conn.execute("""
        CREATE TABLE entity_attributes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER NOT NULL,
            attribute_key TEXT,
            attribute_value TEXT,
            is_verified INTEGER DEFAULT 0,
            confidence REAL DEFAULT 0.0,
            chapter_id INTEGER
        )
    """)

    # --- attribute_evidences (referenced in merge undo JOIN) ---
    conn.execute("""
        CREATE TABLE attribute_evidences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attribute_id INTEGER NOT NULL,
            evidence_text TEXT,
            chapter_id INTEGER
        )
    """)

    # --- alerts ---
    conn.execute("""
        CREATE TABLE alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            status TEXT DEFAULT 'open',
            content_hash TEXT,
            category TEXT DEFAULT 'consistency',
            severity TEXT DEFAULT 'medium',
            description TEXT
        )
    """)

    # --- alert_dismissals ---
    conn.execute("""
        CREATE TABLE alert_dismissals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            content_hash TEXT NOT NULL
        )
    """)

    # --- interactions (relationships) ---
    conn.execute("""
        CREATE TABLE interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            entity1_id INTEGER,
            entity2_id INTEGER,
            relationship_type TEXT,
            detail TEXT,
            chapter_id INTEGER
        )
    """)

    conn.commit()

    # Mock de Database que usa la conexión compartida
    mock_db = MagicMock()
    mock_db.connection.return_value.__enter__ = lambda _: conn
    mock_db.connection.return_value.__exit__ = lambda *_: None

    def fetchall(sql, params=()):
        return conn.execute(sql, params).fetchall()

    def fetchone(sql, params=()):
        return conn.execute(sql, params).fetchone()

    mock_db.fetchall = fetchall
    mock_db.fetchone = fetchone

    # Attach real conn for direct queries in tests
    mock_db._conn = conn

    return mock_db


@pytest.fixture()
def hm(db):
    """HistoryManager para project_id=1."""
    return HistoryManager(project_id=1, db=db)


@pytest.fixture()
def _seed_entity(db):
    """Inserta una entidad activa con menciones."""
    conn = db._conn
    conn.execute(
        "INSERT INTO entities (id, project_id, canonical_name, entity_type, mention_count, is_active) "
        "VALUES (10, 1, 'Juan', 'character', 5, 1)"
    )
    for i in range(5):
        conn.execute(
            "INSERT INTO entity_mentions (entity_id, text) VALUES (10, ?)",
            (f"mención-{i}",),
        )
    conn.commit()


@pytest.fixture()
def _seed_alert(db):
    """Inserta una alerta abierta."""
    conn = db._conn
    conn.execute(
        "INSERT INTO alerts (id, project_id, status, content_hash) "
        "VALUES (20, 1, 'open', 'hash123')"
    )
    conn.commit()


@pytest.fixture()
def _seed_attribute(db):
    """Inserta un atributo."""
    conn = db._conn
    conn.execute(
        "INSERT INTO entity_attributes (id, entity_id, attribute_key, attribute_value, is_verified) "
        "VALUES (30, 10, 'edad', '35', 0)"
    )
    conn.commit()


@pytest.fixture()
def _seed_relationship(db):
    """Inserta una relación."""
    conn = db._conn
    conn.execute(
        "INSERT INTO interactions (id, project_id, entity1_id, entity2_id, relationship_type, detail) "
        "VALUES (40, 1, 10, 11, 'ally', 'Compañeros de aventura')"
    )
    conn.commit()


# ═══════════════════════════════════════════════════════════════════════
# 1. RECORD & GET
# ═══════════════════════════════════════════════════════════════════════

class TestRecord:
    def test_record_creates_entry(self, hm):
        entry = hm.record(
            action_type=ChangeType.ENTITY_DELETED,
            target_type="entity",
            target_id=10,
            old_value={"canonical_name": "Juan"},
            note="Test delete",
        )
        assert entry.id is not None
        assert entry.action_type == ChangeType.ENTITY_DELETED
        assert entry.target_id == 10
        assert entry.note == "Test delete"

    def test_record_with_batch_id(self, hm):
        entry = hm.record(
            action_type=ChangeType.ALERT_RESOLVED,
            target_type="alert",
            target_id=1,
            old_value={"status": "open"},
            batch_id="batch-001",
        )
        assert entry.batch_id == "batch-001"

    def test_record_with_depends_on_ids(self, hm):
        e1 = hm.record(action_type=ChangeType.ENTITY_CREATED, target_type="entity", target_id=1)
        e2 = hm.record(
            action_type=ChangeType.ATTRIBUTE_ADDED,
            target_type="attribute",
            target_id=2,
            old_value={"_was_new": True},
            depends_on_ids=[e1.id],
        )
        fetched = hm.get_entry(e2.id)
        assert e1.id in fetched.depends_on_ids

    def test_get_entry_not_found(self, hm):
        assert hm.get_entry(99999) is None

    def test_get_history_respects_limit(self, hm):
        for i in range(10):
            hm.record(action_type=ChangeType.ALERT_CREATED, target_type="alert", target_id=i)
        entries = hm.get_history(limit=3)
        assert len(entries) == 3

    def test_get_history_filters_by_action_types(self, hm):
        hm.record(action_type=ChangeType.ALERT_CREATED, target_type="alert")
        hm.record(action_type=ChangeType.ENTITY_DELETED, target_type="entity", target_id=1, old_value={"name": "x"})
        entries = hm.get_history(action_types=[ChangeType.ENTITY_DELETED])
        assert len(entries) == 1
        assert entries[0].action_type == ChangeType.ENTITY_DELETED


# ═══════════════════════════════════════════════════════════════════════
# 2. CAN_UNDO
# ═══════════════════════════════════════════════════════════════════════

class TestCanUndo:
    def test_undoable_entry(self, hm):
        entry = hm.record(
            action_type=ChangeType.ENTITY_DELETED,
            target_type="entity",
            target_id=10,
            old_value={"canonical_name": "Juan"},
        )
        ok, msg = hm.can_undo(entry.id)
        assert ok is True

    def test_not_undoable_if_no_old_value(self, hm):
        entry = hm.record(
            action_type=ChangeType.ENTITY_DELETED,
            target_type="entity",
            target_id=10,
            old_value=None,
        )
        ok, msg = hm.can_undo(entry.id)
        assert ok is False
        assert "no es reversible" in msg.lower()

    def test_not_undoable_if_non_undoable_action(self, hm):
        entry = hm.record(
            action_type=ChangeType.ALERT_CREATED,
            target_type="alert",
            target_id=1,
            old_value={"x": 1},
        )
        ok, msg = hm.can_undo(entry.id)
        assert ok is False

    def test_not_undoable_if_already_undone(self, hm, db, _seed_entity):
        entry = hm.record(
            action_type=ChangeType.ENTITY_DELETED,
            target_type="entity",
            target_id=10,
            old_value={"canonical_name": "Juan"},
        )
        hm.undo(entry.id)
        ok, msg = hm.can_undo(entry.id)
        assert ok is False
        assert "ya fue deshecha" in msg.lower()

    def test_not_undoable_if_entry_not_found(self, hm):
        ok, msg = hm.can_undo(99999)
        assert ok is False
        assert "no encontrada" in msg.lower()

    def test_blocked_by_dependency(self, hm):
        e1 = hm.record(
            action_type=ChangeType.ENTITY_CREATED,
            target_type="entity",
            target_id=10,
            old_value={"canonical_name": "Juan"},
        )
        _e2 = hm.record(
            action_type=ChangeType.ATTRIBUTE_ADDED,
            target_type="attribute",
            target_id=30,
            old_value={"_was_new": True, "entity_id": 10},
            depends_on_ids=[e1.id],
        )
        ok, msg = hm.can_undo(e1.id)
        assert ok is False
        assert "dependen" in msg.lower()


# ═══════════════════════════════════════════════════════════════════════
# 3. UNDO HANDLERS
# ═══════════════════════════════════════════════════════════════════════

class TestUndoEntityCreate:
    def test_undo_entity_create_soft_deletes(self, hm, db, _seed_entity):
        entry = hm.record(
            action_type=ChangeType.ENTITY_CREATED,
            target_type="entity",
            target_id=10,
            old_value={"canonical_name": "Juan"},
        )
        result = hm.undo(entry.id)
        assert result.success is True

        row = db._conn.execute("SELECT is_active FROM entities WHERE id = 10").fetchone()
        assert row["is_active"] == 0


class TestUndoEntityDelete:
    def test_undo_entity_delete_reactivates(self, hm, db, _seed_entity):
        # Soft-delete first
        db._conn.execute("UPDATE entities SET is_active = 0 WHERE id = 10")
        db._conn.commit()

        entry = hm.record(
            action_type=ChangeType.ENTITY_DELETED,
            target_type="entity",
            target_id=10,
            old_value={"canonical_name": "Juan"},
        )
        result = hm.undo(entry.id)
        assert result.success is True

        row = db._conn.execute("SELECT is_active FROM entities WHERE id = 10").fetchone()
        assert row["is_active"] == 1


class TestUndoEntityUpdate:
    def test_undo_entity_update_restores_name(self, hm, db, _seed_entity):
        entry = hm.record(
            action_type=ChangeType.ENTITY_UPDATED,
            target_type="entity",
            target_id=10,
            old_value={"canonical_name": "Juan Original"},
            new_value={"canonical_name": "Juan Modificado"},
        )
        # Simulate the update
        db._conn.execute("UPDATE entities SET canonical_name = 'Juan Modificado' WHERE id = 10")
        db._conn.commit()

        result = hm.undo(entry.id)
        assert result.success is True

        row = db._conn.execute("SELECT canonical_name FROM entities WHERE id = 10").fetchone()
        assert row["canonical_name"] == "Juan Original"

    def test_undo_entity_update_restores_type_and_importance(self, hm, db, _seed_entity):
        entry = hm.record(
            action_type=ChangeType.ENTITY_UPDATED,
            target_type="entity",
            target_id=10,
            old_value={"entity_type": "character", "importance": "primary"},
            new_value={"entity_type": "location", "importance": "secondary"},
        )
        db._conn.execute("UPDATE entities SET entity_type = 'location', importance = 'secondary' WHERE id = 10")
        db._conn.commit()

        result = hm.undo(entry.id)
        assert result.success is True

        row = db._conn.execute("SELECT entity_type, importance FROM entities WHERE id = 10").fetchone()
        assert row["entity_type"] == "character"
        assert row["importance"] == "primary"


class TestUndoEntityMerge:
    def test_undo_merge_reactivates_sources(self, hm, db):
        conn = db._conn
        # Setup: entity 10 (result), entities 11, 12 (sources, deactivated)
        conn.execute(
            "INSERT INTO entities (id, project_id, canonical_name, mention_count, is_active, merged_from_ids) "
            "VALUES (10, 1, 'Juan', 8, 1, ?)",
            (json.dumps({"aliases": ["Juanito", "J"], "merged_ids": [11, 12]}),),
        )
        conn.execute(
            "INSERT INTO entities (id, project_id, canonical_name, mention_count, is_active) "
            "VALUES (11, 1, 'Juanito', 0, 0)"
        )
        conn.execute(
            "INSERT INTO entities (id, project_id, canonical_name, mention_count, is_active) "
            "VALUES (12, 1, 'J', 0, 0)"
        )
        # Mentions — all on entity 10
        for i in range(8):
            conn.execute("INSERT INTO entity_mentions (entity_id, text) VALUES (10, ?)", (f"m-{i}",))
        conn.commit()

        entry = hm.record(
            action_type=ChangeType.ENTITY_MERGED,
            target_type="entity",
            target_id=10,
            old_value={
                "source_entity_ids": [11, 12],
                "source_snapshots": [
                    {"id": 11, "canonical_name": "Juanito", "mention_count": 3, "aliases": []},
                    {"id": 12, "canonical_name": "J", "mention_count": 2, "aliases": []},
                ],
                "canonical_names_before": ["Juanito", "J"],
            },
            new_value={"result_entity_id": 10, "merged_by": "user"},
        )

        result = hm.undo(entry.id)
        assert result.success is True

        # Sources reactivated
        for eid in (11, 12):
            row = conn.execute("SELECT is_active FROM entities WHERE id = ?", (eid,)).fetchone()
            assert row["is_active"] == 1

        # Mentions redistributed
        m11 = conn.execute("SELECT COUNT(*) as c FROM entity_mentions WHERE entity_id = 11").fetchone()["c"]
        m12 = conn.execute("SELECT COUNT(*) as c FROM entity_mentions WHERE entity_id = 12").fetchone()["c"]
        m10 = conn.execute("SELECT COUNT(*) as c FROM entity_mentions WHERE entity_id = 10").fetchone()["c"]
        assert m11 == 3
        assert m12 == 2
        assert m10 == 3  # 8 - 3 - 2

    def test_undo_merge_fails_without_source_ids(self, hm, db):
        entry = hm.record(
            action_type=ChangeType.ENTITY_MERGED,
            target_type="entity",
            target_id=10,
            old_value={"source_entity_ids": [], "source_snapshots": []},
        )
        result = hm.undo(entry.id)
        assert result.success is False
        assert "entidades fuente" in result.message.lower() or "error" in result.message.lower()


class TestUndoAlertStatusChange:
    def test_undo_alert_resolve_reopens(self, hm, db, _seed_alert):
        # Resolve the alert
        db._conn.execute("UPDATE alerts SET status = 'resolved' WHERE id = 20")
        db._conn.commit()

        entry = hm.record(
            action_type=ChangeType.ALERT_RESOLVED,
            target_type="alert",
            target_id=20,
            old_value={"status": "open"},
            new_value={"status": "resolved"},
        )
        result = hm.undo(entry.id)
        assert result.success is True

        row = db._conn.execute("SELECT status FROM alerts WHERE id = 20").fetchone()
        assert row["status"] == "open"

    def test_undo_alert_dismiss_removes_dismissal(self, hm, db, _seed_alert):
        # Dismiss the alert
        db._conn.execute("UPDATE alerts SET status = 'dismissed' WHERE id = 20")
        db._conn.execute(
            "INSERT INTO alert_dismissals (project_id, content_hash) VALUES (1, 'hash123')"
        )
        db._conn.commit()

        entry = hm.record(
            action_type=ChangeType.ALERT_DISMISSED,
            target_type="alert",
            target_id=20,
            old_value={"status": "open"},
        )
        result = hm.undo(entry.id)
        assert result.success is True

        # Alert reopened
        row = db._conn.execute("SELECT status FROM alerts WHERE id = 20").fetchone()
        assert row["status"] == "open"

        # Dismissal record removed
        dismissals = db._conn.execute(
            "SELECT COUNT(*) as c FROM alert_dismissals WHERE content_hash = 'hash123'"
        ).fetchone()["c"]
        assert dismissals == 0


class TestUndoAttributeAdd:
    def test_undo_attribute_add_deletes(self, hm, db, _seed_entity, _seed_attribute):
        entry = hm.record(
            action_type=ChangeType.ATTRIBUTE_ADDED,
            target_type="attribute",
            target_id=30,
            old_value={"_was_new": True, "entity_id": 10, "attribute_key": "edad", "attribute_value": "35"},
        )
        result = hm.undo(entry.id)
        assert result.success is True

        row = db._conn.execute("SELECT COUNT(*) as c FROM entity_attributes WHERE id = 30").fetchone()
        assert row["c"] == 0


class TestUndoAttributeUpdate:
    def test_undo_attribute_update_restores_value(self, hm, db, _seed_entity, _seed_attribute):
        # Update the attribute
        db._conn.execute("UPDATE entity_attributes SET attribute_value = '40' WHERE id = 30")
        db._conn.commit()

        entry = hm.record(
            action_type=ChangeType.ATTRIBUTE_UPDATED,
            target_type="attribute",
            target_id=30,
            old_value={"attribute_value": "35", "attribute_key": "edad"},
            new_value={"attribute_value": "40"},
        )
        result = hm.undo(entry.id)
        assert result.success is True

        row = db._conn.execute("SELECT attribute_value FROM entity_attributes WHERE id = 30").fetchone()
        assert row["attribute_value"] == "35"


class TestUndoAttributeVerify:
    def test_undo_attribute_verification(self, hm, db, _seed_entity, _seed_attribute):
        # Verify the attribute
        db._conn.execute("UPDATE entity_attributes SET is_verified = 1 WHERE id = 30")
        db._conn.commit()

        entry = hm.record(
            action_type=ChangeType.ATTRIBUTE_VERIFIED,
            target_type="attribute",
            target_id=30,
            old_value={"is_verified": False, "attribute_value": "35"},
        )
        result = hm.undo(entry.id)
        assert result.success is True

        row = db._conn.execute("SELECT is_verified FROM entity_attributes WHERE id = 30").fetchone()
        assert row["is_verified"] == 0


class TestUndoAttributeDelete:
    def test_undo_attribute_delete_recreates(self, hm, db, _seed_entity):
        # Attribute was deleted
        entry = hm.record(
            action_type=ChangeType.ATTRIBUTE_DELETED,
            target_type="attribute",
            target_id=30,
            old_value={
                "entity_id": 10,
                "attribute_key": "edad",
                "attribute_value": "35",
                "is_verified": 0,
                "confidence": 0.9,
                "chapter_id": None,
            },
        )
        result = hm.undo(entry.id)
        assert result.success is True

        row = db._conn.execute("SELECT * FROM entity_attributes WHERE id = 30").fetchone()
        assert row is not None
        assert row["attribute_key"] == "edad"
        assert row["attribute_value"] == "35"


class TestUndoRelationshipCreate:
    def test_undo_relationship_create_deletes(self, hm, db, _seed_relationship):
        entry = hm.record(
            action_type=ChangeType.RELATIONSHIP_CREATED,
            target_type="relationship",
            target_id=40,
            old_value={"entity1_id": 10, "entity2_id": 11, "relationship_type": "ally"},
        )
        result = hm.undo(entry.id)
        assert result.success is True

        row = db._conn.execute("SELECT COUNT(*) as c FROM interactions WHERE id = 40").fetchone()
        assert row["c"] == 0


class TestUndoRelationshipDelete:
    def test_undo_relationship_delete_recreates(self, hm, db):
        entry = hm.record(
            action_type=ChangeType.RELATIONSHIP_DELETED,
            target_type="relationship",
            target_id=40,
            old_value={
                "entity1_id": 10,
                "entity2_id": 11,
                "relationship_type": "ally",
                "detail": "Compañeros",
                "chapter_id": 1,
            },
        )
        result = hm.undo(entry.id)
        assert result.success is True

        row = db._conn.execute("SELECT * FROM interactions WHERE id = 40").fetchone()
        assert row is not None
        assert row["relationship_type"] == "ally"
        assert row["detail"] == "Compañeros"


class TestUndoRelationshipUpdate:
    def test_undo_relationship_update_restores(self, hm, db, _seed_relationship):
        # Update the relationship
        db._conn.execute("UPDATE interactions SET relationship_type = 'enemy', detail = 'Rivals' WHERE id = 40")
        db._conn.commit()

        entry = hm.record(
            action_type=ChangeType.RELATIONSHIP_UPDATED,
            target_type="relationship",
            target_id=40,
            old_value={"relationship_type": "ally", "detail": "Compañeros de aventura"},
        )
        result = hm.undo(entry.id)
        assert result.success is True

        row = db._conn.execute("SELECT relationship_type, detail FROM interactions WHERE id = 40").fetchone()
        assert row["relationship_type"] == "ally"
        assert row["detail"] == "Compañeros de aventura"


# ═══════════════════════════════════════════════════════════════════════
# 4. UNDO_LAST & UNDO_BATCH
# ═══════════════════════════════════════════════════════════════════════

class TestUndoLast:
    def test_undo_last_picks_most_recent(self, hm, db, _seed_entity):
        hm.record(
            action_type=ChangeType.ENTITY_DELETED,
            target_type="entity",
            target_id=10,
            old_value={"canonical_name": "First"},
        )
        # Soft-delete
        db._conn.execute("UPDATE entities SET is_active = 0 WHERE id = 10")
        db._conn.commit()

        result = hm.undo_last()
        assert result.success is True

        # Entity reactivated
        row = db._conn.execute("SELECT is_active FROM entities WHERE id = 10").fetchone()
        assert row["is_active"] == 1

    def test_undo_last_skips_already_undone(self, hm, db, _seed_entity, _seed_alert):
        e1 = hm.record(
            action_type=ChangeType.ENTITY_DELETED,
            target_type="entity",
            target_id=10,
            old_value={"canonical_name": "Juan"},
        )
        db._conn.execute("UPDATE entities SET is_active = 0 WHERE id = 10")

        # Resolve an alert
        db._conn.execute("UPDATE alerts SET status = 'resolved' WHERE id = 20")
        db._conn.commit()
        e2 = hm.record(
            action_type=ChangeType.ALERT_RESOLVED,
            target_type="alert",
            target_id=20,
            old_value={"status": "open"},
        )

        # Undo e2 (most recent)
        hm.undo(e2.id)

        # Now undo_last should pick e1
        result = hm.undo_last()
        assert result.success is True
        assert result.entry_id == e1.id

    def test_undo_last_when_nothing_to_undo(self, hm):
        result = hm.undo_last()
        assert result.success is False
        assert "no hay" in result.message.lower()


class TestUndoBatch:
    def test_undo_batch_undoes_all_entries(self, hm, db, _seed_entity, _seed_alert):
        batch = "batch-test-001"
        db._conn.execute("UPDATE entities SET is_active = 0 WHERE id = 10")
        db._conn.execute("UPDATE alerts SET status = 'resolved' WHERE id = 20")
        db._conn.commit()

        hm.record(
            action_type=ChangeType.ENTITY_DELETED,
            target_type="entity",
            target_id=10,
            old_value={"canonical_name": "Juan"},
            batch_id=batch,
        )
        hm.record(
            action_type=ChangeType.ALERT_RESOLVED,
            target_type="alert",
            target_id=20,
            old_value={"status": "open"},
            batch_id=batch,
        )

        result = hm.undo_batch(batch)
        assert result.success is True

        # Both undone
        e_row = db._conn.execute("SELECT is_active FROM entities WHERE id = 10").fetchone()
        a_row = db._conn.execute("SELECT status FROM alerts WHERE id = 20").fetchone()
        assert e_row["is_active"] == 1
        assert a_row["status"] == "open"

    def test_undo_batch_nonexistent(self, hm):
        result = hm.undo_batch("nonexistent-batch")
        assert result.success is False


# ═══════════════════════════════════════════════════════════════════════
# 5. EDGE CASES
# ═══════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_double_undo_fails(self, hm, db, _seed_entity):
        entry = hm.record(
            action_type=ChangeType.ENTITY_DELETED,
            target_type="entity",
            target_id=10,
            old_value={"canonical_name": "Juan"},
        )
        db._conn.execute("UPDATE entities SET is_active = 0 WHERE id = 10")
        db._conn.commit()

        r1 = hm.undo(entry.id)
        assert r1.success is True

        r2 = hm.undo(entry.id)
        assert r2.success is False
        assert "ya fue deshecha" in r2.message.lower()

    def test_undo_nonexistent_entry(self, hm):
        result = hm.undo(99999)
        assert result.success is False
        assert "no encontrada" in result.message.lower()

    def test_undo_non_undoable_action_type(self, hm):
        entry = hm.record(
            action_type=ChangeType.ALERT_CREATED,
            target_type="alert",
            target_id=1,
            old_value={"x": 1},
        )
        result = hm.undo(entry.id)
        assert result.success is False

    def test_undo_records_undo_entry(self, hm, db, _seed_entity):
        entry = hm.record(
            action_type=ChangeType.ENTITY_DELETED,
            target_type="entity",
            target_id=10,
            old_value={"canonical_name": "Juan"},
        )
        db._conn.execute("UPDATE entities SET is_active = 0 WHERE id = 10")
        db._conn.commit()

        hm.undo(entry.id)

        # An UNDO entry should be recorded
        undo_entries = hm.get_history(action_types=[ChangeType.UNDO])
        assert len(undo_entries) == 1
        assert undo_entries[0].old_value["undone_entry_id"] == entry.id

    def test_undo_sets_undone_at(self, hm, db, _seed_entity):
        entry = hm.record(
            action_type=ChangeType.ENTITY_DELETED,
            target_type="entity",
            target_id=10,
            old_value={"canonical_name": "Juan"},
        )
        db._conn.execute("UPDATE entities SET is_active = 0 WHERE id = 10")
        db._conn.commit()

        hm.undo(entry.id)

        fetched = hm.get_entry(entry.id)
        assert fetched.undone_at is not None
        assert fetched.is_undone is True
        assert fetched.is_undoable is False

    def test_dependency_blocks_undo(self, hm, db, _seed_entity):
        e1 = hm.record(
            action_type=ChangeType.ENTITY_CREATED,
            target_type="entity",
            target_id=10,
            old_value={"canonical_name": "Juan"},
        )
        _e2 = hm.record(
            action_type=ChangeType.ATTRIBUTE_ADDED,
            target_type="attribute",
            target_id=30,
            old_value={"_was_new": True, "entity_id": 10},
            depends_on_ids=[e1.id],
        )

        result = hm.undo(e1.id)
        assert result.success is False
        assert "dependen" in result.message.lower()

    def test_dependency_unblocked_after_dependent_undone(self, hm, db, _seed_entity, _seed_attribute):
        e1 = hm.record(
            action_type=ChangeType.ENTITY_CREATED,
            target_type="entity",
            target_id=10,
            old_value={"canonical_name": "Juan"},
        )
        e2 = hm.record(
            action_type=ChangeType.ATTRIBUTE_ADDED,
            target_type="attribute",
            target_id=30,
            old_value={"_was_new": True, "entity_id": 10, "attribute_key": "edad"},
            depends_on_ids=[e1.id],
        )

        # Undo e2 first (the dependent)
        r2 = hm.undo(e2.id)
        assert r2.success is True

        # Now e1 can be undone
        r1 = hm.undo(e1.id)
        assert r1.success is True


# ═══════════════════════════════════════════════════════════════════════
# 6. UNDOABLE COUNT & STATS
# ═══════════════════════════════════════════════════════════════════════

class TestUndoableCount:
    def test_undoable_count_basic(self, hm, db, _seed_entity):
        hm.record(
            action_type=ChangeType.ENTITY_DELETED,
            target_type="entity",
            target_id=10,
            old_value={"canonical_name": "Juan"},
        )
        assert hm.get_undoable_count() == 1

    def test_undoable_count_excludes_undone(self, hm, db, _seed_entity):
        entry = hm.record(
            action_type=ChangeType.ENTITY_DELETED,
            target_type="entity",
            target_id=10,
            old_value={"canonical_name": "Juan"},
        )
        db._conn.execute("UPDATE entities SET is_active = 0 WHERE id = 10")
        db._conn.commit()

        assert hm.get_undoable_count() == 1
        hm.undo(entry.id)
        assert hm.get_undoable_count() == 0

    def test_undoable_count_excludes_non_undoable_types(self, hm):
        hm.record(action_type=ChangeType.ALERT_CREATED, target_type="alert", old_value={"x": 1})
        assert hm.get_undoable_count() == 0

    def test_undoable_count_excludes_null_old_value(self, hm):
        hm.record(action_type=ChangeType.ENTITY_DELETED, target_type="entity", target_id=10)
        assert hm.get_undoable_count() == 0

    def test_stats(self, hm):
        hm.record(action_type=ChangeType.ALERT_RESOLVED, target_type="alert", target_id=1, old_value={"status": "open"})
        hm.record(action_type=ChangeType.ALERT_RESOLVED, target_type="alert", target_id=2, old_value={"status": "open"})
        hm.record(action_type=ChangeType.ENTITY_DELETED, target_type="entity", target_id=10, old_value={"name": "x"})
        stats = hm.get_stats()
        assert stats["alert_resolved"] == 2
        assert stats["entity_deleted"] == 1
        assert stats["total"] == 3


# ═══════════════════════════════════════════════════════════════════════
# 7. HISTORY ENTRY MODEL
# ═══════════════════════════════════════════════════════════════════════

class TestHistoryEntryModel:
    def test_is_undoable_property(self):
        entry = HistoryEntry(
            id=1,
            project_id=1,
            action_type=ChangeType.ENTITY_DELETED,
            old_value={"name": "x"},
        )
        assert entry.is_undoable is True
        assert entry.is_undone is False

    def test_is_not_undoable_without_old_value(self):
        entry = HistoryEntry(
            id=1,
            project_id=1,
            action_type=ChangeType.ENTITY_DELETED,
            old_value=None,
        )
        assert entry.is_undoable is False

    def test_is_not_undoable_when_undone(self):
        from datetime import datetime
        entry = HistoryEntry(
            id=1,
            project_id=1,
            action_type=ChangeType.ENTITY_DELETED,
            old_value={"name": "x"},
            undone_at=datetime.now(),
        )
        assert entry.is_undoable is False
        assert entry.is_undone is True

    def test_to_dict_serialization(self):
        from datetime import datetime
        entry = HistoryEntry(
            id=42,
            project_id=1,
            action_type=ChangeType.ALERT_RESOLVED,
            target_type="alert",
            target_id=20,
            old_value={"status": "open"},
            new_value={"status": "resolved"},
            note="Test",
            created_at=datetime(2025, 6, 15, 12, 0),
            batch_id="b1",
            depends_on_ids=[1, 2],
        )
        d = entry.to_dict()
        assert d["id"] == 42
        assert d["action_type"] == "alert_resolved"
        assert d["is_undoable"] is True
        assert d["is_undone"] is False
        assert d["batch_id"] == "b1"
        assert d["depends_on_ids"] == [1, 2]

    def test_undoable_actions_frozenset(self):
        """Verifica que entity_created está en UNDOABLE_ACTIONS."""
        assert "entity_created" in UNDOABLE_ACTIONS
        assert "entity_merged" in UNDOABLE_ACTIONS
        assert "alert_created" not in UNDOABLE_ACTIONS


# ═══════════════════════════════════════════════════════════════════════
# 8. CLEAR_OLD_ENTRIES DEPRECATED
# ═══════════════════════════════════════════════════════════════════════

class TestDeprecated:
    def test_clear_old_entries_raises(self, hm):
        with pytest.raises(NotImplementedError):
            hm.clear_old_entries()
