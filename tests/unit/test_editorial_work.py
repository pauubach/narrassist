"""
Tests para SP-3: Export/Import de trabajo editorial (.narrassist).

Cubre:
- Export: merges, alert decisions, verified attrs, suppression rules
- Import preview: matching, conflictos, LATEST_WINS
- Import confirm: aplicar cambios, section toggles, conflict overrides
- Roundtrip: export → import → all already_done
"""

import json
import os
import sys

import pytest

# api-server no es un paquete instalable; añadir al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api-server"))

from narrative_assistant.persistence.editorial_work import (
    FORMAT_VERSION,
    confirm_import,
    export_editorial_work,
    preview_import,
)

# ---- Helpers ----


def _insert_project(db, project_id=1, fingerprint="fp_test_abc"):
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO projects (id, name, document_fingerprint, document_format, "
            "created_at, updated_at) "
            "VALUES (?, 'Test Novel', ?, 'docx', datetime('now'), datetime('now'))",
            (project_id, fingerprint),
        )


def _reset_singletons():
    """Resetea singletons para que usen la BD del test."""
    import narrative_assistant.alerts.repository as ar
    import narrative_assistant.persistence.dismissal_repository as dr
    from narrative_assistant.entities.repository import reset_entity_repository

    ar._alert_repository = None
    dr._dismissal_repository = None
    reset_entity_repository()


def _insert_entity(db, entity_id, project_id, name, entity_type="character"):
    merged_data = json.dumps({"aliases": [], "merged_ids": []})
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO entities (id, project_id, entity_type, canonical_name, "
            "merged_from_ids, mention_count, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 5, datetime('now'), datetime('now'))",
            (entity_id, project_id, entity_type, name, merged_data),
        )


def _insert_alert(
    db, project_id, content_hash, status="new", alert_type="spelling_typo",
    resolution_note="", title="Test alert",
):
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO alerts (project_id, category, severity, alert_type, "
            "title, description, explanation, status, content_hash, "
            "source_module, resolution_note, created_at) "
            "VALUES (?, 'orthography', 'warning', ?, ?, 'Desc', 'Expl', ?, ?, "
            "'spelling', ?, datetime('now'))",
            (project_id, alert_type, title, status, content_hash, resolution_note),
        )


def _insert_merge_history(db, project_id, names_before, note=""):
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO review_history "
            "(project_id, action_type, target_type, target_id, "
            "old_value_json, new_value_json, note) "
            "VALUES (?, 'entity_merged', 'entity', 1, ?, ?, ?)",
            (
                project_id,
                json.dumps({
                    "source_entity_ids": list(range(len(names_before))),
                    "canonical_names_before": names_before,
                    "source_snapshots": [],
                }),
                json.dumps({"result_entity_id": 1, "merged_by": "user"}),
                note,
            ),
        )


def _insert_verified_attribute(db, entity_id, key, value, attr_type="physical"):
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO entity_attributes "
            "(entity_id, attribute_type, attribute_key, attribute_value, "
            "is_verified, confidence) "
            "VALUES (?, ?, ?, ?, 1, 0.95)",
            (entity_id, attr_type, key, value),
        )


def _insert_suppression_rule(db, project_id, rule_type, pattern, reason=""):
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO suppression_rules (project_id, rule_type, pattern, reason, is_active) "
            "VALUES (?, ?, ?, ?, 1)",
            (project_id, rule_type, pattern, reason),
        )


# ============================================================================
# Export tests
# ============================================================================


class TestExportEditorialWork:
    """Tests para el servicio de export."""

    def test_export_empty_project(self, isolated_database):
        """Proyecto sin trabajo editorial produce export válido pero vacío."""
        db = isolated_database
        _insert_project(db)
        _reset_singletons()

        result = export_editorial_work(1, "Test Novel", "fp_test_abc")
        assert result.is_success
        data = result.value
        assert data["format_version"] == FORMAT_VERSION
        assert data["project_name"] == "Test Novel"
        assert len(data["entity_merges"]) == 0
        assert len(data["alert_decisions"]) == 0
        assert len(data["verified_attributes"]) == 0
        assert len(data["suppression_rules"]) == 0
        assert data["statistics"]["total_entity_merges"] == 0

    def test_export_with_merges(self, isolated_database):
        """Merges de review_history se exportan correctamente."""
        db = isolated_database
        _insert_project(db)
        _insert_merge_history(db, 1, ["María", "Maria"], "User merge")
        _reset_singletons()

        result = export_editorial_work(1)
        assert result.is_success
        merges = result.value["entity_merges"]
        assert len(merges) == 1
        assert merges[0]["result_canonical_name"] == "María"
        assert "Maria" in merges[0]["result_aliases"]

    def test_export_skips_undone_merges(self, isolated_database):
        """Merges con [UNDONE] no se exportan."""
        db = isolated_database
        _insert_project(db)
        _insert_merge_history(db, 1, ["A", "B"], "merge [UNDONE at 2026-01-20]")
        _insert_merge_history(db, 1, ["C", "D"], "normal merge")
        _reset_singletons()

        result = export_editorial_work(1)
        assert result.is_success
        assert len(result.value["entity_merges"]) == 1
        assert result.value["entity_merges"][0]["result_canonical_name"] == "C"

    def test_export_alert_decisions(self, isolated_database):
        """Alertas dismissed se exportan con content_hash."""
        db = isolated_database
        _insert_project(db)
        _insert_alert(db, 1, "hash_001", status="dismissed", resolution_note="FP")
        _insert_alert(db, 1, "hash_002", status="new")  # No se exporta
        _insert_alert(db, 1, "hash_003", status="resolved", resolution_note="Fixed")
        _reset_singletons()

        result = export_editorial_work(1)
        assert result.is_success
        decisions = result.value["alert_decisions"]
        assert len(decisions) == 2
        hashes = {d["content_hash"] for d in decisions}
        assert "hash_001" in hashes
        assert "hash_003" in hashes
        assert "hash_002" not in hashes

    def test_export_verified_attributes(self, isolated_database):
        """Solo atributos is_verified=1 se exportan."""
        db = isolated_database
        _insert_project(db)
        _insert_entity(db, 1, 1, "María")
        _insert_verified_attribute(db, 1, "eye_color", "verdes")
        # Atributo no verificado
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO entity_attributes "
                "(entity_id, attribute_type, attribute_key, attribute_value, "
                "is_verified, confidence) VALUES (1, 'physical', 'hair', 'negro', 0, 0.8)"
            )
        _reset_singletons()

        result = export_editorial_work(1)
        assert result.is_success
        attrs = result.value["verified_attributes"]
        assert len(attrs) == 1
        assert attrs[0]["attribute_key"] == "eye_color"
        assert attrs[0]["entity_name"] == "María"

    def test_export_suppression_rules(self, isolated_database):
        """Reglas de supresión se exportan."""
        db = isolated_database
        _insert_project(db)
        _insert_suppression_rule(db, 1, "alert_type", "spelling_*", "too noisy")
        _reset_singletons()

        result = export_editorial_work(1)
        assert result.is_success
        rules = result.value["suppression_rules"]
        assert len(rules) == 1
        assert rules[0]["pattern"] == "spelling_*"

    def test_export_json_valid(self, isolated_database):
        """El export produce JSON válido serializable."""
        db = isolated_database
        _insert_project(db)
        _reset_singletons()

        result = export_editorial_work(1, "Test", "fp123")
        assert result.is_success
        json_str = json.dumps(result.value)
        parsed = json.loads(json_str)
        assert parsed["format_version"] == 1


# ============================================================================
# Import preview tests
# ============================================================================


class TestImportPreview:
    """Tests para el step 1 de import: preview."""

    @staticmethod
    def _make_import_data(**overrides) -> dict:
        base = {
            "format_version": 1,
            "app_version": "0.9.1",
            "exported_at": "2026-02-12T10:00:00",
            "exported_by": "editor",
            "project_fingerprint": "fp_test_abc",
            "project_name": "Test",
            "entity_merges": [],
            "alert_decisions": [],
            "verified_attributes": [],
            "suppression_rules": [],
            "statistics": {},
        }
        base.update(overrides)
        return base

    def test_preview_valid_empty_file(self, isolated_database):
        """Archivo válido vacío produce preview correcto."""
        _insert_project(isolated_database)
        _reset_singletons()

        result = preview_import(1, self._make_import_data())
        assert result.is_success
        preview = result.value
        assert preview.project_fingerprint_match is True
        assert preview.to_dict()["total_to_apply"] == 0

    def test_preview_invalid_format_version(self, isolated_database):
        """format_version incorrecto retorna error."""
        _insert_project(isolated_database)
        _reset_singletons()

        result = preview_import(1, {"format_version": 99})
        assert result.is_failure

    def test_preview_fingerprint_mismatch_warning(self, isolated_database):
        """Fingerprint diferente genera warning, no error."""
        _insert_project(isolated_database, fingerprint="fp_original")
        _reset_singletons()

        data = self._make_import_data(project_fingerprint="fp_different")
        result = preview_import(1, data)
        assert result.is_success
        assert not result.value.project_fingerprint_match
        assert len(result.value.warnings) > 0

    def test_preview_alert_matching_by_content_hash(self, isolated_database):
        """Alertas se matchean por content_hash."""
        db = isolated_database
        _insert_project(db)
        _insert_alert(db, 1, "hash_match", status="new")
        _reset_singletons()

        data = self._make_import_data(
            alert_decisions=[{
                "content_hash": "hash_match",
                "status": "dismissed",
                "resolution_note": "FP",
                "decided_at": "2026-02-12T10:00:00",
                "alert_type": "spelling_typo",
                "category": "orthography",
                "chapter": 1,
                "entity_names": [],
                "description_hint": "Test",
            }]
        )
        result = preview_import(1, data)
        assert result.is_success
        assert result.value.alert_decisions_to_apply == 1

    def test_preview_alert_already_done(self, isolated_database):
        """Alerta con mismo status = already_done."""
        db = isolated_database
        _insert_project(db)
        _insert_alert(db, 1, "hash_same", status="dismissed")
        # También en dismissals
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO alert_dismissals (project_id, content_hash, scope) "
                "VALUES (1, 'hash_same', 'instance')"
            )
        _reset_singletons()

        data = self._make_import_data(
            alert_decisions=[{
                "content_hash": "hash_same",
                "status": "dismissed",
                "decided_at": "",
                "alert_type": "", "category": "", "chapter": 0,
                "entity_names": [], "description_hint": "", "resolution_note": "",
            }]
        )
        result = preview_import(1, data)
        assert result.is_success
        assert result.value.alert_decisions_already_done == 1
        assert result.value.alert_decisions_to_apply == 0

    def test_preview_conflict_detection(self, isolated_database):
        """Decisiones conflictivas se detectan con LATEST_WINS."""
        db = isolated_database
        _insert_project(db)
        _insert_alert(db, 1, "hash_conflict", status="resolved",
                       resolution_note="local fix")
        _reset_singletons()

        data = self._make_import_data(
            alert_decisions=[{
                "content_hash": "hash_conflict",
                "status": "dismissed",
                "resolution_note": "imported FP",
                "decided_at": "2099-01-01T00:00:00",
                "alert_type": "", "category": "", "chapter": 0,
                "entity_names": [], "description_hint": "Conflicto",
            }]
        )
        result = preview_import(1, data)
        assert result.is_success
        assert result.value.alert_decisions_conflicts == 1
        assert len(result.value.conflicts) == 1
        assert result.value.conflicts[0].resolution == "imported_wins"

    def test_preview_suppression_rule_new(self, isolated_database):
        """Regla nueva se marca como to_add."""
        _insert_project(isolated_database)
        _reset_singletons()

        data = self._make_import_data(
            suppression_rules=[{
                "rule_type": "alert_type",
                "pattern": "spelling_*",
                "entity_name": None,
                "reason": "imported",
                "is_active": True,
            }]
        )
        result = preview_import(1, data)
        assert result.is_success
        assert result.value.suppression_rules_to_add == 1

    def test_preview_suppression_rule_existing(self, isolated_database):
        """Regla existente se marca como already_exist."""
        db = isolated_database
        _insert_project(db)
        _insert_suppression_rule(db, 1, "alert_type", "spelling_*")
        _reset_singletons()

        data = self._make_import_data(
            suppression_rules=[{
                "rule_type": "alert_type",
                "pattern": "spelling_*",
                "entity_name": None,
                "reason": "", "is_active": True,
            }]
        )
        result = preview_import(1, data)
        assert result.is_success
        assert result.value.suppression_rules_already_exist == 1
        assert result.value.suppression_rules_to_add == 0

    def test_preview_verified_attr_to_verify(self, isolated_database):
        """Atributo no verificado localmente → to_apply."""
        db = isolated_database
        _insert_project(db)
        _insert_entity(db, 1, 1, "María")
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO entity_attributes "
                "(entity_id, attribute_type, attribute_key, attribute_value, "
                "is_verified, confidence) VALUES (1, 'physical', 'eye_color', 'verdes', 0, 0.9)"
            )
        _reset_singletons()

        data = self._make_import_data(
            verified_attributes=[{
                "entity_name": "María",
                "entity_type": "character",
                "attribute_type": "physical",
                "attribute_key": "eye_color",
                "attribute_value": "verdes",
                "confidence": 0.95,
            }]
        )
        result = preview_import(1, data)
        assert result.is_success
        assert result.value.verified_attributes_to_apply == 1


# ============================================================================
# Import confirm tests
# ============================================================================


class TestImportConfirm:
    """Tests para el step 2 de import: confirm."""

    def test_confirm_applies_alert_dismissal(self, isolated_database):
        """Dismissals se aplican a alertas matching."""
        db = isolated_database
        _insert_project(db)
        _insert_alert(db, 1, "hash_apply", status="new")
        _reset_singletons()

        import_data = {
            "format_version": 1,
            "project_fingerprint": "fp_test_abc",
            "entity_merges": [],
            "alert_decisions": [{
                "content_hash": "hash_apply",
                "status": "dismissed",
                "resolution_note": "FP",
                "decided_at": "2026-02-12T10:00:00",
                "alert_type": "spelling_typo",
                "category": "orthography",
                "chapter": 1,
                "entity_names": [],
                "description_hint": "Test",
            }],
            "verified_attributes": [],
            "suppression_rules": [],
        }

        result = confirm_import(1, import_data)
        assert result.is_success
        assert result.value["alert_decisions_applied"] >= 1

        # Verificar en BD
        with db.connection() as conn:
            row = conn.execute(
                "SELECT status FROM alerts WHERE content_hash = 'hash_apply'"
            ).fetchone()
        assert row["status"] == "dismissed"

    def test_confirm_adds_suppression_rules(self, isolated_database):
        """Reglas nuevas se crean."""
        db = isolated_database
        _insert_project(db)
        _reset_singletons()

        import_data = {
            "format_version": 1,
            "project_fingerprint": "fp_test_abc",
            "entity_merges": [],
            "alert_decisions": [],
            "verified_attributes": [],
            "suppression_rules": [{
                "rule_type": "alert_type",
                "pattern": "grammar_*",
                "entity_name": None,
                "reason": "imported",
                "is_active": True,
            }],
        }

        result = confirm_import(1, import_data)
        assert result.is_success
        assert result.value["suppression_rules_added"] == 1

        with db.connection() as conn:
            row = conn.execute(
                "SELECT pattern FROM suppression_rules WHERE project_id = 1"
            ).fetchone()
        assert row["pattern"] == "grammar_*"

    def test_confirm_verifies_attributes(self, isolated_database):
        """Atributos no verificados se marcan como verificados."""
        db = isolated_database
        _insert_project(db)
        _insert_entity(db, 1, 1, "María")
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO entity_attributes "
                "(entity_id, attribute_type, attribute_key, attribute_value, "
                "is_verified, confidence) VALUES (1, 'physical', 'eye_color', 'verdes', 0, 0.9)"
            )
        _reset_singletons()

        import_data = {
            "format_version": 1,
            "project_fingerprint": "fp_test_abc",
            "entity_merges": [],
            "alert_decisions": [],
            "verified_attributes": [{
                "entity_name": "María",
                "entity_type": "character",
                "attribute_type": "physical",
                "attribute_key": "eye_color",
                "attribute_value": "verdes",
                "confidence": 0.95,
            }],
            "suppression_rules": [],
        }

        result = confirm_import(1, import_data)
        assert result.is_success
        assert result.value["verified_attributes_applied"] == 1

        with db.connection() as conn:
            row = conn.execute(
                "SELECT is_verified FROM entity_attributes WHERE attribute_key = 'eye_color'"
            ).fetchone()
        assert row["is_verified"] == 1

    def test_confirm_respects_section_toggles(self, isolated_database):
        """Secciones desactivadas no se aplican."""
        db = isolated_database
        _insert_project(db)
        _reset_singletons()

        import_data = {
            "format_version": 1,
            "project_fingerprint": "fp_test_abc",
            "entity_merges": [],
            "alert_decisions": [],
            "verified_attributes": [],
            "suppression_rules": [{
                "rule_type": "alert_type",
                "pattern": "spelling_*",
                "entity_name": None,
                "reason": "test",
                "is_active": True,
            }],
        }

        result = confirm_import(1, import_data, import_suppression_rules=False)
        assert result.is_success
        assert result.value["suppression_rules_added"] == 0

        with db.connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM suppression_rules WHERE project_id = 1"
            ).fetchone()[0]
        assert count == 0


# ============================================================================
# Roundtrip tests
# ============================================================================


class TestRoundtrip:
    """Export → import roundtrip tests."""

    def test_roundtrip_same_project(self, isolated_database):
        """Export e import en el mismo proyecto → all already_done."""
        db = isolated_database
        _insert_project(db)
        _insert_alert(db, 1, "hash_rt", status="dismissed", resolution_note="FP")
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO alert_dismissals (project_id, content_hash, scope) "
                "VALUES (1, 'hash_rt', 'instance')"
            )
        _insert_suppression_rule(db, 1, "alert_type", "spelling_*")
        _reset_singletons()

        # Export
        export_result = export_editorial_work(1, "Test", "fp_test_abc")
        assert export_result.is_success
        export_data = export_result.value

        # Preview import del mismo export
        preview_result = preview_import(1, export_data)
        assert preview_result.is_success
        preview = preview_result.value

        # Todo debería ser already_done
        assert preview.alert_decisions_to_apply == 0
        assert preview.suppression_rules_to_add == 0
        assert preview.to_dict()["total_to_apply"] == 0

    def test_export_produces_valid_format(self, isolated_database):
        """El export produce un formato que el import acepta."""
        db = isolated_database
        _insert_project(db)
        _insert_merge_history(db, 1, ["A", "B"])
        _insert_alert(db, 1, "h1", status="dismissed")
        _insert_entity(db, 1, 1, "María")
        _insert_verified_attribute(db, 1, "eyes", "blue")
        _insert_suppression_rule(db, 1, "alert_type", "test_*")
        _reset_singletons()

        export_result = export_editorial_work(1, "Test", "fp_test_abc")
        assert export_result.is_success

        # Verificar que es JSON serializable y re-parseable
        json_str = json.dumps(export_result.value)
        reparsed = json.loads(json_str)
        assert reparsed["format_version"] == FORMAT_VERSION

        # Preview debería funcionar sin error
        preview_result = preview_import(1, reparsed)
        assert preview_result.is_success


# ============================================================================
# Edge cases & QA tests
# ============================================================================


class TestEdgeCases:
    """Edge cases y escenarios límite desde perspectiva QA."""

    def test_preview_non_dict_input(self, isolated_database):
        """Input no-dict retorna error."""
        _insert_project(isolated_database)
        _reset_singletons()

        result = preview_import(1, "not a dict")
        assert result.is_failure

    def test_preview_list_input(self, isolated_database):
        """Lista en vez de dict retorna error."""
        _insert_project(isolated_database)
        _reset_singletons()

        result = preview_import(1, [{"format_version": 1}])
        assert result.is_failure

    def test_preview_missing_format_version(self, isolated_database):
        """Sin format_version retorna error."""
        _insert_project(isolated_database)
        _reset_singletons()

        result = preview_import(1, {"entity_merges": []})
        assert result.is_failure

    def test_preview_format_version_string(self, isolated_database):
        """format_version como string retorna error."""
        _insert_project(isolated_database)
        _reset_singletons()

        result = preview_import(1, {"format_version": "1"})
        assert result.is_failure

    def test_preview_missing_section_keys(self, isolated_database):
        """Archivo sin secciones opcionales no crashea."""
        _insert_project(isolated_database)
        _reset_singletons()

        data = {"format_version": 1}  # Sin entity_merges, etc.
        result = preview_import(1, data)
        assert result.is_success
        assert result.value.to_dict()["total_to_apply"] == 0

    def test_preview_alert_empty_content_hash_skipped(self, isolated_database):
        """Decisión con content_hash vacío se ignora."""
        _insert_project(isolated_database)
        _reset_singletons()

        data = {
            "format_version": 1,
            "alert_decisions": [{
                "content_hash": "",
                "status": "dismissed",
                "decided_at": "", "alert_type": "", "category": "",
                "chapter": 0, "entity_names": [],
                "description_hint": "", "resolution_note": "",
            }],
        }
        result = preview_import(1, data)
        assert result.is_success
        assert result.value.alert_decisions_to_apply == 0

    def test_preview_merge_single_source_skipped(self, isolated_database):
        """Merge con solo 1 source_name se ignora."""
        _insert_project(isolated_database)
        _reset_singletons()

        data = {
            "format_version": 1,
            "entity_merges": [{
                "result_canonical_name": "María",
                "source_canonical_names": ["María"],
                "result_aliases": [],
                "merged_at": "", "merged_by": "user", "note": "",
            }],
        }
        result = preview_import(1, data)
        assert result.is_success
        assert result.value.entity_merges_to_apply == 0

    def test_preview_merge_empty_canonical_name_skipped(self, isolated_database):
        """Merge con canonical_name vacío se ignora."""
        _insert_project(isolated_database)
        _reset_singletons()

        data = {
            "format_version": 1,
            "entity_merges": [{
                "result_canonical_name": "",
                "source_canonical_names": ["", "B"],
                "result_aliases": [],
                "merged_at": "", "merged_by": "user", "note": "",
            }],
        }
        result = preview_import(1, data)
        assert result.is_success
        assert result.value.entity_merges_to_apply == 0

    def test_preview_verified_attr_empty_entity_name_skipped(self, isolated_database):
        """Atributo con entity_name vacío se ignora."""
        _insert_project(isolated_database)
        _reset_singletons()

        data = {
            "format_version": 1,
            "verified_attributes": [{
                "entity_name": "",
                "entity_type": "character",
                "attribute_type": "physical",
                "attribute_key": "eyes",
                "attribute_value": "blue",
                "confidence": 0.9,
            }],
        }
        result = preview_import(1, data)
        assert result.is_success
        assert result.value.verified_attributes_to_apply == 0

    def test_export_empty_project_name(self, isolated_database):
        """Export con project_name vacío funciona."""
        db = isolated_database
        _insert_project(db)
        _reset_singletons()

        result = export_editorial_work(1, "", "fp_test_abc")
        assert result.is_success
        assert result.value["project_name"] == ""

    def test_export_merge_with_null_old_value(self, isolated_database):
        """Merge con old_value_json=NULL se ignora."""
        db = isolated_database
        _insert_project(db)
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO review_history "
                "(project_id, action_type, target_type, target_id, "
                "old_value_json, new_value_json, note) "
                "VALUES (1, 'entity_merged', 'entity', 1, NULL, '{}', '')"
            )
        _reset_singletons()

        result = export_editorial_work(1)
        assert result.is_success
        assert len(result.value["entity_merges"]) == 0

    def test_confirm_all_toggles_false(self, isolated_database):
        """Con todas las secciones desactivadas no se aplica nada."""
        db = isolated_database
        _insert_project(db)
        _insert_alert(db, 1, "hash_noop", status="new")
        _insert_suppression_rule(db, 1, "alert_type", "new_pattern")
        _reset_singletons()

        import_data = {
            "format_version": 1,
            "project_fingerprint": "fp_test_abc",
            "entity_merges": [],
            "alert_decisions": [{
                "content_hash": "hash_noop",
                "status": "dismissed",
                "decided_at": "", "alert_type": "",
                "category": "", "chapter": 0,
                "entity_names": [], "description_hint": "",
                "resolution_note": "",
            }],
            "verified_attributes": [],
            "suppression_rules": [{
                "rule_type": "alert_type",
                "pattern": "brand_new_*",
                "entity_name": None, "reason": "",
                "is_active": True,
            }],
        }

        result = confirm_import(
            1, import_data,
            import_entity_merges=False,
            import_alert_decisions=False,
            import_verified_attributes=False,
            import_suppression_rules=False,
        )
        assert result.is_success
        stats = result.value
        assert stats["entity_merges_applied"] == 0
        assert stats["alert_decisions_applied"] == 0
        assert stats["verified_attributes_applied"] == 0
        assert stats["suppression_rules_added"] == 0

    def test_resolve_latest_wins_invalid_timestamps(self, isolated_database):
        """LATEST_WINS con timestamps inválidos no crashea."""
        from narrative_assistant.persistence.editorial_work import (
            _resolve_latest_wins,
        )

        assert _resolve_latest_wins("", "") == "imported_wins"
        assert _resolve_latest_wins("invalid", "2026-01-01T00:00:00") == "imported_wins"
        assert _resolve_latest_wins("2026-01-01T00:00:00", "invalid") == "imported_wins"
        assert _resolve_latest_wins("bad", "bad") == "imported_wins"

    def test_export_statistics_accurate(self, isolated_database):
        """Estadísticas del export reflejan datos reales."""
        db = isolated_database
        _insert_project(db)
        _insert_merge_history(db, 1, ["A", "B"])
        _insert_merge_history(db, 1, ["C", "D"])
        _insert_alert(db, 1, "h1", status="dismissed")
        _insert_alert(db, 1, "h2", status="resolved")
        _insert_alert(db, 1, "h3", status="new")  # No exportada
        _insert_entity(db, 1, 1, "María")
        _insert_verified_attribute(db, 1, "eyes", "blue")
        _insert_suppression_rule(db, 1, "alert_type", "test_*")
        _reset_singletons()

        result = export_editorial_work(1)
        assert result.is_success
        stats = result.value["statistics"]
        assert stats["total_entity_merges"] == 2
        assert stats["total_alert_decisions"] == 2
        assert stats["total_verified_attributes"] == 1
        assert stats["total_suppression_rules"] == 1

    def test_export_import_different_fingerprint(self, isolated_database):
        """Import con fingerprint diferente genera warning pero funciona."""
        db = isolated_database
        _insert_project(db, fingerprint="fp_original")
        _reset_singletons()

        # Export de otro "proyecto"
        data = {
            "format_version": 1,
            "project_fingerprint": "fp_different_project",
            "entity_merges": [],
            "alert_decisions": [],
            "verified_attributes": [],
            "suppression_rules": [{
                "rule_type": "alert_type",
                "pattern": "cross_project_*",
                "entity_name": None, "reason": "test",
                "is_active": True,
            }],
        }

        # Preview tiene warning
        preview_result = preview_import(1, data)
        assert preview_result.is_success
        assert not preview_result.value.project_fingerprint_match
        assert len(preview_result.value.warnings) > 0

        # Confirm funciona igualmente
        confirm_result = confirm_import(1, data)
        assert confirm_result.is_success
        assert confirm_result.value["suppression_rules_added"] == 1

    def test_preview_total_to_apply_calculation(self, isolated_database):
        """total_to_apply suma todas las secciones correctamente."""
        db = isolated_database
        _insert_project(db)
        _insert_alert(db, 1, "h_apply", status="new")
        _insert_entity(db, 1, 1, "Test")
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO entity_attributes "
                "(entity_id, attribute_type, attribute_key, attribute_value, "
                "is_verified, confidence) VALUES (1, 'physical', 'hair', 'rojo', 0, 0.9)"
            )
        _reset_singletons()

        data = {
            "format_version": 1,
            "project_fingerprint": "fp_test_abc",
            "alert_decisions": [{
                "content_hash": "h_apply",
                "status": "dismissed",
                "decided_at": "", "alert_type": "",
                "category": "", "chapter": 0,
                "entity_names": [], "description_hint": "",
                "resolution_note": "",
            }],
            "verified_attributes": [{
                "entity_name": "Test",
                "entity_type": "character",
                "attribute_type": "physical",
                "attribute_key": "hair",
                "attribute_value": "rojo",
                "confidence": 0.9,
            }],
            "suppression_rules": [{
                "rule_type": "alert_type",
                "pattern": "new_rule_*",
                "entity_name": None,
                "reason": "", "is_active": True,
            }],
        }

        result = preview_import(1, data)
        assert result.is_success
        preview = result.value.to_dict()
        expected = (
            result.value.alert_decisions_to_apply
            + result.value.verified_attributes_to_apply
            + result.value.suppression_rules_to_add
        )
        assert preview["total_to_apply"] == expected
        assert expected >= 2  # Al menos alert + rule
