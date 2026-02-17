"""
Tests para los endpoints de la API de historial/undo.

Verifica la lógica de los routers sin levantar el servidor HTTP.
Usa mocks de HistoryManager para aislar el comportamiento.
"""
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Añadir api-server al path para importar routers
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api-server"))

from narrative_assistant.persistence.history import (  # noqa: E402
    ChangeType,
    HistoryEntry,
    UndoResult,
)


# ─── Helpers ──────────────────────────────────────────────────────────

def _make_entry(**kwargs) -> HistoryEntry:
    """Crea un HistoryEntry con defaults sensatos."""
    defaults = {
        "id": 1,
        "project_id": 1,
        "action_type": ChangeType.ENTITY_DELETED,
        "target_type": "entity",
        "target_id": 10,
        "old_value": {"canonical_name": "Juan"},
        "new_value": None,
        "note": "test",
        "created_at": datetime(2025, 6, 15, 12, 0),
    }
    defaults.update(kwargs)
    return HistoryEntry(**defaults)


# ═══════════════════════════════════════════════════════════════════════
# GET /api/projects/{id}/history
# ═══════════════════════════════════════════════════════════════════════

class TestGetHistory:
    @patch("narrative_assistant.persistence.history.HistoryManager")
    def test_returns_serialized_entries(self, MockHM):
        from routers.history import get_history

        entry = _make_entry()
        MockHM.return_value.get_history.return_value = [entry]

        resp = get_history(project_id=1)
        assert resp.success is True
        assert len(resp.data) == 1
        assert resp.data[0]["id"] == 1
        assert resp.data[0]["action_type"] == "entity_deleted"

    @patch("narrative_assistant.persistence.history.HistoryManager")
    def test_empty_history(self, MockHM):
        from routers.history import get_history

        MockHM.return_value.get_history.return_value = []

        resp = get_history(project_id=1)
        assert resp.success is True
        assert resp.data == []

    @patch("narrative_assistant.persistence.history.HistoryManager")
    def test_error_handling(self, MockHM):
        from routers.history import get_history

        MockHM.return_value.get_history.side_effect = RuntimeError("DB error")

        resp = get_history(project_id=1)
        assert resp.success is False
        assert "error" in resp.error.lower()


# ═══════════════════════════════════════════════════════════════════════
# GET /api/projects/{id}/history/count
# ═══════════════════════════════════════════════════════════════════════

class TestGetUndoableCount:
    @patch("narrative_assistant.persistence.history.HistoryManager")
    def test_returns_count(self, MockHM):
        from routers.history import get_undoable_count

        MockHM.return_value.get_undoable_count.return_value = 7

        resp = get_undoable_count(project_id=1)
        assert resp.success is True
        assert resp.data["count"] == 7

    @patch("narrative_assistant.persistence.history.HistoryManager")
    def test_error_returns_zero(self, MockHM):
        from routers.history import get_undoable_count

        MockHM.return_value.get_undoable_count.side_effect = RuntimeError("DB")

        resp = get_undoable_count(project_id=1)
        assert resp.success is True
        assert resp.data["count"] == 0


# ═══════════════════════════════════════════════════════════════════════
# GET /api/projects/{id}/history/{entry_id}/can-undo
# ═══════════════════════════════════════════════════════════════════════

class TestCanUndo:
    @patch("narrative_assistant.persistence.history.HistoryManager")
    def test_can_undo_true(self, MockHM):
        from routers.history import can_undo

        MockHM.return_value.can_undo.return_value = (True, "OK")

        resp = can_undo(project_id=1, entry_id=1)
        assert resp.success is True
        assert resp.data["can_undo"] is True

    @patch("narrative_assistant.persistence.history.HistoryManager")
    def test_can_undo_false(self, MockHM):
        from routers.history import can_undo

        MockHM.return_value.can_undo.return_value = (False, "Ya fue deshecha")

        resp = can_undo(project_id=1, entry_id=1)
        assert resp.success is True
        assert resp.data["can_undo"] is False
        assert "deshecha" in resp.data["reason"].lower()


# ═══════════════════════════════════════════════════════════════════════
# POST /api/projects/{id}/undo (Ctrl+Z)
# ═══════════════════════════════════════════════════════════════════════

class TestUndoLast:
    @patch("narrative_assistant.persistence.history.HistoryManager")
    def test_undo_last_success(self, MockHM):
        from routers.history import undo_last

        MockHM.return_value.undo_last.return_value = UndoResult(
            success=True, message="Eliminación deshecha", entry_id=42
        )

        resp = undo_last(project_id=1)
        assert resp.success is True
        assert resp.data["entry_id"] == 42
        assert "deshecha" in resp.data["message"].lower()

    @patch("narrative_assistant.persistence.history.HistoryManager")
    def test_undo_last_nothing_to_undo(self, MockHM):
        from routers.history import undo_last

        MockHM.return_value.undo_last.return_value = UndoResult(
            success=False, message="No hay acciones para deshacer"
        )

        resp = undo_last(project_id=1)
        assert resp.success is False
        assert "no hay" in resp.error.lower()


# ═══════════════════════════════════════════════════════════════════════
# POST /api/projects/{id}/undo/{entry_id}
# ═══════════════════════════════════════════════════════════════════════

class TestUndoEntry:
    @patch("narrative_assistant.persistence.history.HistoryManager")
    def test_undo_entry_success(self, MockHM):
        from routers.history import undo_entry

        MockHM.return_value.undo.return_value = UndoResult(
            success=True, message="Resolución deshecha", entry_id=5
        )

        resp = undo_entry(project_id=1, entry_id=5)
        assert resp.success is True
        assert resp.data["entry_id"] == 5

    @patch("narrative_assistant.persistence.history.HistoryManager")
    def test_undo_entry_blocked_by_dependency(self, MockHM):
        from routers.history import undo_entry

        MockHM.return_value.undo.return_value = UndoResult(
            success=False,
            message="No se puede deshacer: 1 acciones dependen de esta",
            conflicts=[{"id": 99, "action": "attribute_added"}],
        )

        resp = undo_entry(project_id=1, entry_id=5)
        assert resp.success is False
        assert "dependen" in resp.error.lower()
        assert resp.data["conflicts"] is not None


# ═══════════════════════════════════════════════════════════════════════
# POST /api/projects/{id}/undo-batch/{batch_id}
# ═══════════════════════════════════════════════════════════════════════

class TestUndoBatch:
    @patch("narrative_assistant.persistence.history.HistoryManager")
    def test_undo_batch_success(self, MockHM):
        from routers.history import undo_batch

        MockHM.return_value.undo_batch.return_value = UndoResult(
            success=True, message="Batch abc deshecho (3 acciones)"
        )

        resp = undo_batch(project_id=1, batch_id="abc")
        assert resp.success is True
        assert resp.data["batch_id"] == "abc"

    @patch("narrative_assistant.persistence.history.HistoryManager")
    def test_undo_batch_not_found(self, MockHM):
        from routers.history import undo_batch

        MockHM.return_value.undo_batch.return_value = UndoResult(
            success=False, message="No hay acciones en este batch"
        )

        resp = undo_batch(project_id=1, batch_id="xyz")
        assert resp.success is False


# ═══════════════════════════════════════════════════════════════════════
# POST /api/projects/{id}/entities/undo-merge/{merge_id} (unified)
# ═══════════════════════════════════════════════════════════════════════

class TestUndoMergeEndpoint:
    @patch("narrative_assistant.persistence.history.HistoryManager")
    def test_undo_merge_routes_through_history_manager(self, MockHM):
        """Verifica que el endpoint de undo-merge usa HistoryManager.undo()."""
        from routers.entities import undo_entity_merge

        mock_entry = _make_entry(
            action_type=ChangeType.ENTITY_MERGED,
            target_id=10,
            old_value={"source_entity_ids": [11, 12]},
        )
        MockHM.return_value.undo.return_value = UndoResult(
            success=True, message="Fusión deshecha", entry_id=1
        )
        MockHM.return_value.get_entry.return_value = mock_entry

        resp = undo_entity_merge(project_id=1, merge_id=1)
        assert resp.success is True
        assert resp.data["restored_entity_ids"] == [11, 12]
        MockHM.return_value.undo.assert_called_once_with(1)

    @patch("narrative_assistant.persistence.history.HistoryManager")
    def test_undo_merge_failure(self, MockHM):
        from routers.entities import undo_entity_merge

        MockHM.return_value.undo.return_value = UndoResult(
            success=False, message="Ya fue deshecha"
        )

        resp = undo_entity_merge(project_id=1, merge_id=1)
        assert resp.success is False
        assert "deshecha" in resp.error.lower()
