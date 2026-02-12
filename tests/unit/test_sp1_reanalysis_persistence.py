"""
Tests para SP-1: Preservación de trabajo editorial entre re-análisis.

Cubre:
- SP1-01: content_hash no incluye posiciones para spelling/grammar
- SP1-02: run_cleanup no borra tablas de trabajo editorial
- SP1-03: _apply_saved_dismissals auto-descarta alertas conocidas
- SP1-04: Merges de entidades sobreviven re-análisis
- SP1-05: Atributos verificados (is_verified=1) se preservan
- SP1-06: Correcciones manuales (coref, speaker, focalization) sobreviven
"""

import json
import os
import sys

import pytest

# api-server no es un paquete instalable; añadir al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api-server"))

from narrative_assistant.alerts.models import (
    Alert,
    AlertCategory,
    AlertSeverity,
    AlertStatus,
)

# ---- Helpers comunes ----

def _insert_project(db, project_id: int = 1):
    """Inserta un proyecto base para tests."""
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO projects (id, name, document_fingerprint, document_format, "
            "created_at, updated_at) "
            "VALUES (?, 'Test', 'abc123', 'docx', datetime('now'), datetime('now'))",
            (project_id,),
        )


class _FakeTracker:
    """Tracker stub para run_cleanup."""
    def start_phase(self, *a, **kw): pass
    def end_phase(self, *a, **kw): pass
    def update_progress(self, *a, **kw): pass


def _run_cleanup(db, project_id: int):
    """Ejecuta run_cleanup con contexto simulado."""
    from routers._analysis_phases import run_cleanup
    run_cleanup({"project_id": project_id, "db_session": db}, _FakeTracker())


# ============================================================================
# SP1-01: content_hash estabilidad (sin posiciones)
# ============================================================================


class TestContentHashStability:
    """Verifica que content_hash no depende de posiciones en el documento."""

    def _make_spelling_alert(self, word: str, start_char: int = 0, chapter: int = 1) -> Alert:
        """Helper: crea alerta de spelling con posición variable."""
        return Alert(
            id=0,
            project_id=1,
            category=AlertCategory.ORTHOGRAPHY,
            severity=AlertSeverity.WARNING,
            alert_type="spelling_typo",
            title=f"Posible error: '{word}'",
            description=f"Palabra no reconocida: '{word}'",
            explanation="",
            chapter=chapter,
            start_char=start_char,
            end_char=start_char + len(word),
            extra_data={"word": word},
        )

    def test_spelling_hash_ignores_position(self):
        """SP1-01: Mismo typo en diferente posición produce mismo hash."""
        a1 = self._make_spelling_alert("tienpo", start_char=100)
        a2 = self._make_spelling_alert("tienpo", start_char=250)
        assert a1.content_hash == a2.content_hash

    def test_spelling_hash_differs_by_word(self):
        """Diferentes palabras producen diferente hash."""
        a1 = self._make_spelling_alert("tienpo")
        a2 = self._make_spelling_alert("hize")
        assert a1.content_hash != a2.content_hash

    def test_spelling_hash_differs_by_chapter(self):
        """Mismo typo en diferente capítulo produce diferente hash."""
        a1 = self._make_spelling_alert("tienpo", chapter=1)
        a2 = self._make_spelling_alert("tienpo", chapter=3)
        assert a1.content_hash != a2.content_hash

    def test_spelling_hash_deterministic(self):
        """El hash es determinista: mismos inputs, mismo resultado."""
        a1 = self._make_spelling_alert("tienpo", start_char=100)
        a2 = self._make_spelling_alert("tienpo", start_char=100)
        assert a1.content_hash == a2.content_hash

    def _make_grammar_alert(self, text: str, error_type: str, start_char: int = 0) -> Alert:
        """Helper: crea alerta de gramática."""
        return Alert(
            id=0,
            project_id=1,
            category=AlertCategory.GRAMMAR,
            severity=AlertSeverity.WARNING,
            alert_type="grammar_agreement",
            title=f"Error gramatical: '{text}'",
            description="Posible error de concordancia",
            explanation="",
            chapter=1,
            start_char=start_char,
            end_char=start_char + len(text),
            extra_data={"text": text, "error_type": error_type},
        )

    def test_grammar_hash_ignores_position(self):
        """SP1-01: Grammar alerts no incluyen posición en hash."""
        a1 = self._make_grammar_alert("los casa", "agreement", start_char=50)
        a2 = self._make_grammar_alert("los casa", "agreement", start_char=300)
        assert a1.content_hash == a2.content_hash

    def test_attribute_inconsistency_hash_stable(self):
        """Hash de attribute_inconsistency es determinista y no usa posición."""
        common = {
            "id": 0,
            "project_id": 1,
            "category": AlertCategory.CONSISTENCY,
            "severity": AlertSeverity.CRITICAL,
            "alert_type": "attribute_inconsistency",
            "title": "Color de ojos inconsistente",
            "description": "María: 'verdes' vs 'azules'",
            "explanation": "",
            "chapter": 2,
            "entity_ids": [1],
            "extra_data": {
                "entity_name": "María",
                "attribute_key": "color_ojos",
                "value1": "verdes",
                "value2": "azules",
            },
        }
        a1 = Alert(**common, start_char=100, end_char=120)
        a2 = Alert(**common, start_char=500, end_char=520)
        assert a1.content_hash == a2.content_hash


# ============================================================================
# SP1-02: run_cleanup preserva trabajo editorial
# ============================================================================


class TestCleanupPreservesWork:
    """Verifica que run_cleanup NO borra tablas de trabajo editorial."""

    @staticmethod
    def _count_rows(db, table: str, project_id: int) -> int:
        with db.connection() as conn:
            return conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE project_id = ?",
                (project_id,),
            ).fetchone()[0]

    def test_dismissals_survive_cleanup(self, isolated_database):
        """SP1-02: alert_dismissals NO se borran en cleanup."""
        db = isolated_database
        _insert_project(db)
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO alert_dismissals (project_id, content_hash, scope, alert_type) "
                "VALUES (1, 'abc123', 'instance', 'spelling_typo')"
            )
            conn.execute(
                "INSERT INTO alert_dismissals (project_id, content_hash, scope, alert_type) "
                "VALUES (1, 'def456', 'instance', 'spelling_typo')"
            )

        _run_cleanup(db, 1)

        assert self._count_rows(db, "alert_dismissals", 1) == 2

    def test_suppression_rules_survive_cleanup(self, isolated_database):
        """SP1-02: suppression_rules NO se borran en cleanup."""
        db = isolated_database
        _insert_project(db)
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO suppression_rules (project_id, rule_type, pattern, reason) "
                "VALUES (1, 'alert_type', 'spelling_*', 'too noisy')"
            )

        _run_cleanup(db, 1)

        assert self._count_rows(db, "suppression_rules", 1) == 1

    def test_coref_corrections_survive_cleanup(self, isolated_database):
        """SP1-02: coreference_corrections NO se borran en cleanup."""
        db = isolated_database
        _insert_project(db)
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO coreference_corrections "
                "(project_id, mention_start_char, mention_end_char, mention_text, "
                "chapter_number, correction_type) "
                "VALUES (1, 100, 110, 'ella', 1, 'reassign')"
            )

        _run_cleanup(db, 1)

        assert self._count_rows(db, "coreference_corrections", 1) == 1

    def test_speaker_corrections_survive_cleanup(self, isolated_database):
        """SP1-02: speaker_corrections NO se borran en cleanup."""
        db = isolated_database
        _insert_project(db)
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO speaker_corrections "
                "(project_id, chapter_number, dialogue_start_char, dialogue_end_char, "
                "dialogue_text) "
                "VALUES (1, 1, 200, 250, '—Vamos —dijo.')"
            )

        _run_cleanup(db, 1)

        assert self._count_rows(db, "speaker_corrections", 1) == 1

    def test_focalization_declarations_survive_cleanup(self, isolated_database):
        """SP1-02: focalization_declarations NO se borran en cleanup."""
        db = isolated_database
        _insert_project(db)
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO focalization_declarations "
                "(project_id, chapter, focalization_type) "
                "VALUES (1, 1, 'internal_fixed')"
            )

        _run_cleanup(db, 1)

        assert self._count_rows(db, "focalization_declarations", 1) == 1

    def test_alerts_are_cleared_on_cleanup(self, isolated_database):
        """Confirma que alerts SÍ se borran (comportamiento esperado)."""
        db = isolated_database
        _insert_project(db)
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO alerts (project_id, category, severity, alert_type, "
                "title, description, explanation, status, created_at) "
                "VALUES (1, 'consistency', 'critical', 'attribute_inconsistency', "
                "'Test', 'Desc', 'Expl', 'new', datetime('now'))"
            )

        _run_cleanup(db, 1)

        assert self._count_rows(db, "alerts", 1) == 0

    def test_entities_are_cleared_on_cleanup(self, isolated_database):
        """Confirma que entities SÍ se borran (se regeneran en NER)."""
        db = isolated_database
        _insert_project(db)
        merged_data = json.dumps({"aliases": [], "merged_ids": []})
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO entities (project_id, entity_type, canonical_name, "
                "merged_from_ids, created_at, updated_at) "
                "VALUES (1, 'character', 'María', ?, datetime('now'), datetime('now'))",
                (merged_data,),
            )

        _run_cleanup(db, 1)

        assert self._count_rows(db, "entities", 1) == 0


# ============================================================================
# SP1-03: _apply_saved_dismissals
# ============================================================================


def _reset_singletons():
    """Resetea singletons de repositorios para que usen la BD actual del test."""
    import narrative_assistant.alerts.repository as ar
    import narrative_assistant.persistence.dismissal_repository as dr
    ar._alert_repository = None
    dr._dismissal_repository = None


class TestApplySavedDismissals:
    """Verifica que _apply_saved_dismissals auto-descarta alertas conocidas."""

    @staticmethod
    def _setup_project_with_alerts(db, project_id: int = 1) -> list[str]:
        """Inserta proyecto + 3 alertas con content_hash conocidos."""
        _insert_project(db, project_id)
        hashes = ["hash_spelling_01", "hash_spelling_02", "hash_attr_01"]
        for i, h in enumerate(hashes):
            with db.connection() as conn:
                conn.execute(
                    "INSERT INTO alerts (project_id, category, severity, alert_type, "
                    "title, description, explanation, status, content_hash, "
                    "source_module, created_at) "
                    "VALUES (?, 'orthography', 'warning', 'spelling_typo', "
                    "?, 'Desc', 'Expl', 'new', ?, 'spelling', datetime('now'))",
                    (project_id, f"Alerta {i}", h),
                )
        return hashes

    def test_dismissals_applied_by_content_hash(self, isolated_database):
        """SP1-03: Alertas con content_hash en dismissals se auto-descartan."""
        db = isolated_database
        hashes = self._setup_project_with_alerts(db)

        with db.connection() as conn:
            conn.execute(
                "INSERT INTO alert_dismissals (project_id, content_hash, scope, alert_type) "
                "VALUES (1, ?, 'instance', 'spelling_typo')",
                (hashes[0],),
            )
            conn.execute(
                "INSERT INTO alert_dismissals (project_id, content_hash, scope, alert_type) "
                "VALUES (1, ?, 'instance', 'spelling_typo')",
                (hashes[2],),
            )

        _reset_singletons()
        from routers._analysis_phases import _apply_saved_dismissals
        _apply_saved_dismissals(1)

        with db.connection() as conn:
            dismissed = conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE project_id = 1 AND status = 'dismissed'"
            ).fetchone()[0]
            active = conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE project_id = 1 AND status = 'new'"
            ).fetchone()[0]

        assert dismissed == 2
        assert active == 1

    def test_suppression_rules_applied(self, isolated_database):
        """SP1-03: Suppression rules suprimen alertas activas."""
        db = isolated_database
        self._setup_project_with_alerts(db)

        with db.connection() as conn:
            conn.execute(
                "INSERT INTO suppression_rules (project_id, rule_type, pattern, is_active) "
                "VALUES (1, 'alert_type', 'spelling_*', 1)"
            )

        _reset_singletons()
        from routers._analysis_phases import _apply_saved_dismissals
        _apply_saved_dismissals(1)

        with db.connection() as conn:
            dismissed = conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE project_id = 1 AND status = 'dismissed'"
            ).fetchone()[0]

        assert dismissed == 3

    def test_inactive_rules_not_applied(self, isolated_database):
        """SP1-03: Reglas inactivas no se aplican."""
        db = isolated_database
        self._setup_project_with_alerts(db)

        with db.connection() as conn:
            conn.execute(
                "INSERT INTO suppression_rules (project_id, rule_type, pattern, is_active) "
                "VALUES (1, 'alert_type', 'spelling_*', 0)"
            )

        _reset_singletons()
        from routers._analysis_phases import _apply_saved_dismissals
        _apply_saved_dismissals(1)

        with db.connection() as conn:
            active = conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE project_id = 1 AND status = 'new'"
            ).fetchone()[0]

        assert active == 3

    def test_already_dismissed_not_double_processed(self, isolated_database):
        """SP1-03: Alertas ya dismissed no se procesan de nuevo."""
        db = isolated_database
        _insert_project(db)
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO alerts (project_id, category, severity, alert_type, "
                "title, description, explanation, status, content_hash, "
                "source_module, created_at) "
                "VALUES (1, 'orthography', 'warning', 'spelling_typo', "
                "'Test', 'Desc', 'Expl', 'dismissed', 'already_done', "
                "'spelling', datetime('now'))"
            )
            conn.execute(
                "INSERT INTO suppression_rules (project_id, rule_type, pattern, is_active) "
                "VALUES (1, 'alert_type', 'spelling_*', 1)"
            )

        _reset_singletons()
        from routers._analysis_phases import _apply_saved_dismissals
        _apply_saved_dismissals(1)

        with db.connection() as conn:
            row = conn.execute(
                "SELECT status FROM alerts WHERE project_id = 1"
            ).fetchone()
        assert row[0] == "dismissed"


# ============================================================================
# SP1-06: Correcciones manuales sobreviven re-análisis
# ============================================================================


class TestManualCorrectionsSurvive:
    """
    SP1-06: Correcciones manuales persisten después de cleanup.

    Las tablas coreference_corrections, speaker_corrections y
    focalization_declarations contienen trabajo del corrector que NO
    debe perderse entre re-análisis.
    """

    def test_multiple_coref_corrections_persist(self, isolated_database):
        """SP1-06: Múltiples correcciones de correferencia sobreviven."""
        db = isolated_database
        _insert_project(db)

        with db.connection() as conn:
            for i in range(5):
                conn.execute(
                    "INSERT INTO coreference_corrections "
                    "(project_id, mention_start_char, mention_end_char, mention_text, "
                    "chapter_number, correction_type, notes) "
                    "VALUES (1, ?, ?, ?, ?, 'reassign', ?)",
                    (100 + i * 50, 110 + i * 50, f"mención_{i}", i + 1, f"Nota {i}"),
                )

        _run_cleanup(db, 1)

        with db.connection() as conn:
            rows = conn.execute(
                "SELECT mention_text, notes FROM coreference_corrections WHERE project_id = 1"
            ).fetchall()
        assert len(rows) == 5
        assert rows[0]["mention_text"] == "mención_0"

    def test_speaker_corrections_with_entity_refs_persist(self, isolated_database):
        """SP1-06: Correcciones de speaker con referencias a entidades sobreviven."""
        db = isolated_database
        _insert_project(db)

        with db.connection() as conn:
            conn.execute(
                "INSERT INTO speaker_corrections "
                "(project_id, chapter_number, dialogue_start_char, dialogue_end_char, "
                "dialogue_text, notes) "
                "VALUES (1, 3, 500, 550, '—No me importa —dijo María.', "
                "'El hablante es María, no Juan')"
            )

        _run_cleanup(db, 1)

        with db.connection() as conn:
            row = conn.execute(
                "SELECT dialogue_text, notes FROM speaker_corrections WHERE project_id = 1"
            ).fetchone()
        assert row is not None
        assert "María" in row["dialogue_text"]

    def test_focalization_with_validation_persists(self, isolated_database):
        """SP1-06: Declaraciones de focalización validadas sobreviven."""
        db = isolated_database
        _insert_project(db)

        with db.connection() as conn:
            conn.execute(
                "INSERT INTO focalization_declarations "
                "(project_id, chapter, scene, focalization_type, "
                "focalizer_ids, is_validated, notes) "
                "VALUES (1, 2, 1, 'internal_fixed', '[1]', 1, "
                "'POV de María confirmado por editor')"
            )

        _run_cleanup(db, 1)

        with db.connection() as conn:
            row = conn.execute(
                "SELECT focalization_type, is_validated, notes "
                "FROM focalization_declarations WHERE project_id = 1"
            ).fetchone()
        assert row is not None
        assert row["focalization_type"] == "internal_fixed"
        assert row["is_validated"] == 1


# ============================================================================
# SP1-04: Merges de usuario sobreviven re-análisis
# ============================================================================


class TestUserMergesPreserved:
    """SP1-04: Las fusiones de usuario preservadas en review_history sobreviven."""

    def test_entity_merged_history_survives_cleanup(self, isolated_database):
        """SP1-04: review_history con action_type='entity_merged' NO se borra."""
        db = isolated_database
        _insert_project(db)

        # Insertar merge history
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO review_history "
                "(project_id, action_type, target_type, target_id, "
                "old_value_json, new_value_json, note) "
                "VALUES (1, 'entity_merged', 'entity', 1, "
                "'{\"canonical_names_before\": [\"María\", \"Maria\"]}', "
                "'{\"result_entity_id\": 1}', 'User merge')"
            )
            # Insertar otro tipo de review_history (debe borrarse)
            conn.execute(
                "INSERT INTO review_history "
                "(project_id, action_type, target_type, target_id, "
                "old_value_json, new_value_json) "
                "VALUES (1, 'attribute_edited', 'entity', 1, "
                "'{\"old\": \"azul\"}', '{\"new\": \"verde\"}')"
            )

        _run_cleanup(db, 1)

        with db.connection() as conn:
            merged = conn.execute(
                "SELECT COUNT(*) FROM review_history "
                "WHERE project_id = 1 AND action_type = 'entity_merged'"
            ).fetchone()[0]
            other = conn.execute(
                "SELECT COUNT(*) FROM review_history "
                "WHERE project_id = 1 AND action_type != 'entity_merged'"
            ).fetchone()[0]

        assert merged == 1, "entity_merged history should survive cleanup"
        assert other == 0, "non-merge history should be deleted"

    def test_reapply_user_merges(self, isolated_database):
        """SP1-04: _reapply_user_merges fusiona entidades que el usuario unió antes."""
        db = isolated_database
        _insert_project(db)

        # Crear merge history (María + Maria fusionadas por el usuario)
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO review_history "
                "(project_id, action_type, target_type, target_id, "
                "old_value_json, new_value_json) "
                "VALUES (1, 'entity_merged', 'entity', 1, ?, ?)",
                (
                    json.dumps({
                        "source_entity_ids": [1, 2],
                        "canonical_names_before": ["María", "Maria"],
                        "source_snapshots": [],
                    }),
                    json.dumps({"result_entity_id": 1, "merged_by": "user"}),
                ),
            )

        # Crear entidades como si NER las hubiera detectado de nuevo (sin fusionar)
        merged_data1 = json.dumps({"aliases": [], "merged_ids": []})
        merged_data2 = json.dumps({"aliases": [], "merged_ids": []})
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO entities (id, project_id, entity_type, canonical_name, "
                "merged_from_ids, mention_count, created_at, updated_at) "
                "VALUES (10, 1, 'character', 'María', ?, 5, datetime('now'), datetime('now'))",
                (merged_data1,),
            )
            conn.execute(
                "INSERT INTO entities (id, project_id, entity_type, canonical_name, "
                "merged_from_ids, mention_count, created_at, updated_at) "
                "VALUES (11, 1, 'character', 'Maria', ?, 3, datetime('now'), datetime('now'))",
                (merged_data2,),
            )

        # Simular entidades en memoria
        from narrative_assistant.entities.models import Entity, EntityType
        entities = [
            Entity(id=10, project_id=1, entity_type=EntityType.CHARACTER,
                   canonical_name="María", mention_count=5),
            Entity(id=11, project_id=1, entity_type=EntityType.CHARACTER,
                   canonical_name="Maria", mention_count=3),
        ]

        _reset_singletons()
        from narrative_assistant.entities.repository import get_entity_repository
        entity_repo = get_entity_repository()

        from routers._analysis_phases import _reapply_user_merges
        _reapply_user_merges(1, entity_repo, entities)

        # Verificar que "Maria" fue fusionada en "María"
        primary = entity_repo.get_entity(10)
        assert primary is not None
        assert "Maria" in primary.aliases

        secondary = entity_repo.get_entity(11)
        assert secondary is None or not secondary.is_active


# ============================================================================
# SP1-05: Atributos verificados sobreviven re-análisis
# ============================================================================


class TestVerifiedAttributesPreserved:
    """SP1-05: Atributos con is_verified=1 se restauran después del re-análisis."""

    def test_verified_attrs_saved_before_cleanup(self, isolated_database):
        """SP1-05: run_cleanup guarda atributos verificados en ctx."""
        db = isolated_database
        _insert_project(db)

        # Crear entidad + atributo verificado
        merged_data = json.dumps({"aliases": [], "merged_ids": []})
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO entities (id, project_id, entity_type, canonical_name, "
                "merged_from_ids, created_at, updated_at) "
                "VALUES (1, 1, 'character', 'María', ?, datetime('now'), datetime('now'))",
                (merged_data,),
            )
            conn.execute(
                "INSERT INTO entity_attributes "
                "(entity_id, attribute_type, attribute_key, attribute_value, "
                "is_verified, confidence) "
                "VALUES (1, 'physical', 'color_ojos', 'azules', 1, 0.95)"
            )
            # Atributo no verificado (no debería guardarse)
            conn.execute(
                "INSERT INTO entity_attributes "
                "(entity_id, attribute_type, attribute_key, attribute_value, "
                "is_verified, confidence) "
                "VALUES (1, 'physical', 'color_pelo', 'negro', 0, 0.8)"
            )

        ctx = {"project_id": 1, "db_session": db}
        from routers._analysis_phases import run_cleanup
        run_cleanup(ctx, _FakeTracker())

        assert "_sp1_verified_attrs" in ctx
        assert len(ctx["_sp1_verified_attrs"]) == 1
        assert ctx["_sp1_verified_attrs"][0]["attribute_key"] == "color_ojos"
        assert ctx["_sp1_verified_attrs"][0]["attribute_value"] == "azules"

    def test_restore_verified_attributes(self, isolated_database):
        """SP1-05: _restore_verified_attributes marca atributos como verificados."""
        db = isolated_database
        _insert_project(db)

        # Crear entidad + atributo no verificado (como si NER lo detectó de nuevo)
        merged_data = json.dumps({"aliases": [], "merged_ids": []})
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO entities (id, project_id, entity_type, canonical_name, "
                "merged_from_ids, created_at, updated_at) "
                "VALUES (1, 1, 'character', 'María', ?, datetime('now'), datetime('now'))",
                (merged_data,),
            )
            conn.execute(
                "INSERT INTO entity_attributes "
                "(entity_id, attribute_type, attribute_key, attribute_value, "
                "is_verified, confidence) "
                "VALUES (1, 'physical', 'color_ojos', 'azules', 0, 0.9)"
            )

        ctx = {
            "project_id": 1,
            "_sp1_verified_attrs": [
                {
                    "entity_name": "María",
                    "attribute_key": "color_ojos",
                    "attribute_value": "azules",
                    "attribute_type": "physical",
                    "confidence": 0.95,
                }
            ],
        }

        _reset_singletons()
        from routers._analysis_phases import _restore_verified_attributes
        _restore_verified_attributes(ctx)

        with db.connection() as conn:
            row = conn.execute(
                "SELECT is_verified FROM entity_attributes WHERE attribute_key = 'color_ojos'"
            ).fetchone()
        assert row is not None
        assert row["is_verified"] == 1

    def test_no_verified_attrs_no_error(self, isolated_database):
        """SP1-05: Sin atributos verificados previos, no hay error."""
        _insert_project(isolated_database)
        ctx = {"project_id": 1}

        from routers._analysis_phases import _restore_verified_attributes
        _restore_verified_attributes(ctx)  # Should not raise
