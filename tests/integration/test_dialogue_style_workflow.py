"""
Tests de integración para el workflow completo de estilo de diálogo.

Cubre el flujo end-to-end:
1. Crear proyecto con correction_config
2. Analizar documento → detecta diálogos, guarda en DB
3. Inicializa dialogue_style_preference desde correction_config
4. Cambiar preferencia → regenera alertas sin re-análisis
5. Verificar alertas generadas dinámicamente
"""

import json

import pytest

from narrative_assistant.nlp.dialogue import detect_dialogues
from narrative_assistant.nlp.dialogue_config_mapper import (
    map_correction_config_to_dialogue_preference,
)
from narrative_assistant.nlp.dialogue_preference_manager import (
    get_dialogue_preference_manager,
)
from narrative_assistant.nlp.dialogue_style_checker import DialogueStyleChecker
from narrative_assistant.persistence.dialogue import DialogueRepository


@pytest.fixture
def sample_text_mixed_styles():
    """Texto con estilos mixtos de diálogo."""
    return """
Capítulo 1

María entró en la habitación.

—Hola —dijo ella.
—¿Cómo estás? —respondió Pedro.

Más tarde, en el jardín:

« ¿Vamos a salir? » preguntó María.
« No lo sé » dijo Pedro.

Al final del día:

"Fue un día interesante" comentó María.
"Sí, lo fue" asintió Pedro.
    """


@pytest.fixture
def sample_text_uniform_dash():
    """Texto con solo rayas (formato uniforme)."""
    return """
Capítulo 1

—Hola —dijo María.
—¿Cómo estás? —respondió Pedro.
—Muy bien, gracias —sonrió ella.
—Me alegro —asintió él.
    """


# =============================================================================
# Tests de workflow completo
# =============================================================================


class TestDialogueStyleWorkflow:
    """Tests del workflow end-to-end."""

    def test_complete_workflow_change_preference(
        self, isolated_database, sample_text_mixed_styles
    ):
        """
        Workflow completo: crear proyecto → analizar → cambiar preferencia → verificar alertas.
        """
        db = isolated_database
        repo = DialogueRepository(db)
        checker = DialogueStyleChecker(db)

        # 1. Crear proyecto con correction_config (preferencia inicial: dash)
        with db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO projects (
                    name, document_path, document_fingerprint, document_format,
                    settings_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "Test Project",
                    "/test.docx",
                    "test-fp",
                    "docx",
                    json.dumps(
                        {
                            "correction_config": {
                                "dialogue_dash": "em",
                                "quote_style": "none",
                            }
                        }
                    ),
                ),
            )
            project_id = cursor.lastrowid

            # Crear capítulo
            cursor = conn.execute(
                """
                INSERT INTO chapters (
                    project_id, chapter_number, title, content,
                    start_char, end_char
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project_id, 1, "Capítulo 1", sample_text_mixed_styles, 0, len(sample_text_mixed_styles)),
            )
            chapter_id = cursor.lastrowid

        # 2. Detectar diálogos (simula Phase 3 del análisis)
        dialogue_result = detect_dialogues(sample_text_mixed_styles)

        assert dialogue_result.is_success
        assert len(dialogue_result.value.dialogues) > 0

        # Guardar diálogos en DB
        dialogues_saved = []
        for dlg_span in dialogue_result.value.dialogues:
            from narrative_assistant.persistence.dialogue import DialogueData

            dialogue_data = DialogueData(
                id=None,
                project_id=project_id,
                chapter_id=chapter_id,
                start_char=dlg_span.start_char,
                end_char=dlg_span.end_char,
                text=dlg_span.text,
                dialogue_type=dlg_span.dialogue_type.value,
                original_format=dlg_span.original_format,
                confidence=dlg_span.confidence,
            )
            dialogues_saved.append(repo.create(dialogue_data))

        # Verificar que se guardaron
        assert len(dialogues_saved) >= 6  # Texto tiene al menos 6 diálogos

        # 3. Inicializar dialogue_style_preference desde correction_config
        preference = map_correction_config_to_dialogue_preference("em", "none")
        assert preference == "dash"

        # Guardar preferencia en settings
        with db.connection() as conn:
            conn.execute(
                """
                UPDATE projects
                SET settings_json = json_set(settings_json, '$.dialogue_style_preference', ?)
                WHERE id = ?
                """,
                (preference, project_id),
            )

        # 4. Validar estilo inicial (debería crear alertas para guillemets y quotes)
        result = checker.validate_and_create_alerts(project_id, min_severity="info")

        assert result.is_success
        initial_alerts = result.value
        assert initial_alerts > 0  # Hay diálogos que no son dash

        # 5. Cambiar preferencia a guillemets
        with db.connection() as conn:
            conn.execute(
                """
                UPDATE projects
                SET settings_json = json_set(settings_json, '$.dialogue_style_preference', ?)
                WHERE id = ?
                """,
                ("guillemets", project_id),
            )

            # Invalidar alertas anteriores
            conn.execute(
                """
                DELETE FROM alerts
                WHERE project_id = ? AND alert_type = 'dialogue_style'
                """,
                (project_id,),
            )

        # 6. Validar con nueva preferencia (ahora alertas para dash y quotes)
        result = checker.validate_and_create_alerts(project_id, min_severity="info")

        assert result.is_success
        new_alerts = result.value

        # Debe haber alertas diferentes (ahora dash y quotes son incorrectos)
        assert new_alerts > 0

        # 7. Verificar que las alertas son correctas
        with db.connection() as conn:
            conn.row_factory = lambda c, r: dict(
                zip([col[0] for col in c.description], r)
            )
            alerts = conn.execute(
                """
                SELECT * FROM alerts
                WHERE project_id = ? AND alert_type = 'dialogue_style'
                """,
                (project_id,),
            ).fetchall()

            # Debe haber alertas para diálogos que NO son guillemets
            assert len(alerts) == new_alerts
            for alert in alerts:
                assert "inconsistente" in alert["description"].lower()

    def test_no_reanalysis_required_on_preference_change(
        self, isolated_database, sample_text_uniform_dash
    ):
        """
        Verificar que cambiar preferencia NO requiere re-análisis.
        """
        db = isolated_database
        repo = DialogueRepository(db)
        checker = DialogueStyleChecker(db)

        # 1. Crear proyecto y capítulo
        with db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO projects (
                    name, document_path, document_fingerprint, document_format,
                    settings_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "Uniform Project",
                    "/test.docx",
                    "uniform-fp",
                    "docx",
                    json.dumps({"dialogue_style_preference": "dash"}),
                ),
            )
            project_id = cursor.lastrowid

            cursor = conn.execute(
                """
                INSERT INTO chapters (
                    project_id, chapter_number, title, content,
                    start_char, end_char
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project_id, 1, "Capítulo 1", sample_text_uniform_dash, 0, len(sample_text_uniform_dash)),
            )
            chapter_id = cursor.lastrowid

        # 2. Detectar y guardar diálogos UNA VEZ
        dialogue_result = detect_dialogues(sample_text_uniform_dash)
        assert dialogue_result.is_success

        for dlg_span in dialogue_result.value.dialogues:
            from narrative_assistant.persistence.dialogue import DialogueData

            repo.create(
                DialogueData(
                    id=None,
                    project_id=project_id,
                    chapter_id=chapter_id,
                    start_char=dlg_span.start_char,
                    end_char=dlg_span.end_char,
                    text=dlg_span.text,
                    dialogue_type=dlg_span.dialogue_type.value,
                    original_format=dlg_span.original_format,
                    confidence=dlg_span.confidence,
                )
            )

        initial_dialogue_count = len(repo.get_by_project(project_id))
        assert initial_dialogue_count > 0

        # 3. Validar con preferencia "dash" (todos OK)
        result = checker.validate_and_create_alerts(project_id, min_severity="info")
        assert result.is_success
        assert result.value == 0  # No alertas, todo es dash

        # 4. Cambiar preferencia a guillemets (SIN re-analizar)
        with db.connection() as conn:
            conn.execute(
                """
                UPDATE projects
                SET settings_json = json_set(settings_json, '$.dialogue_style_preference', ?)
                WHERE id = ?
                """,
                ("guillemets", project_id),
            )

        # 5. Validar con nueva preferencia (CONSULTA DB, no re-análisis)
        result = checker.validate_and_create_alerts(project_id, min_severity="info")
        assert result.is_success
        assert result.value == initial_dialogue_count  # Todos son dash, todos generan alerta

        # 6. CRUCIAL: Verificar que NO se re-analizó (mismo número de diálogos en DB)
        final_dialogue_count = len(repo.get_by_project(project_id))
        assert final_dialogue_count == initial_dialogue_count  # NO cambió

    def test_severity_calculation_in_workflow(
        self, isolated_database
    ):
        """
        Verificar cálculo de severidad en workflow real.
        """
        db = isolated_database
        repo = DialogueRepository(db)
        checker = DialogueStyleChecker(db)

        # Crear proyecto
        with db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO projects (
                    name, document_path, document_fingerprint, document_format,
                    settings_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "Severity Test",
                    "/test.docx",
                    "severity-fp",
                    "docx",
                    json.dumps({"dialogue_style_preference": "dash"}),
                ),
            )
            project_id = cursor.lastrowid

            cursor = conn.execute(
                """
                INSERT INTO chapters (
                    project_id, chapter_number, title, content,
                    start_char, end_char
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project_id, 1, "Capítulo 1", "Test content", 0, 100),
            )
            chapter_id = cursor.lastrowid

        # Crear 95 dash + 5 guillemets (5% inconsistente → HIGH severity)
        from narrative_assistant.persistence.dialogue import DialogueData

        for i in range(95):
            repo.create(
                DialogueData(
                    id=None,
                    project_id=project_id,
                    chapter_id=chapter_id,
                    start_char=i * 10,
                    end_char=(i + 1) * 10,
                    text="—Texto",
                    dialogue_type="dash",
                    original_format="em_dash",
                    confidence=0.9,
                )
            )

        for i in range(5):
            repo.create(
                DialogueData(
                    id=None,
                    project_id=project_id,
                    chapter_id=chapter_id,
                    start_char=(i + 95) * 10,
                    end_char=(i + 96) * 10,
                    text="« Texto »",
                    dialogue_type="guillemets",
                    original_format="guillemets",
                    confidence=0.9,
                )
            )

        # Validar
        result = checker.validate_and_create_alerts(project_id, min_severity="info")
        assert result.is_success
        assert result.value == 5  # 5 alertas para los guillemets

        # Verificar severidad
        with db.connection() as conn:
            conn.row_factory = lambda c, r: dict(
                zip([col[0] for col in c.description], r)
            )
            alerts = conn.execute(
                """
                SELECT severity FROM alerts
                WHERE project_id = ? AND alert_type = 'dialogue_style'
                """,
                (project_id,),
            ).fetchall()

            # 5% inconsistente → severidad HIGH
            for alert in alerts:
                assert alert["severity"] == "high"


# =============================================================================
# Tests de integración con DialoguePreferenceManager
# =============================================================================


class TestPreferenceManagerIntegration:
    """Tests de integración con DialoguePreferenceManager."""

    def test_manager_updates_preference_and_creates_alerts(
        self, isolated_database
    ):
        """
        El manager actualiza preferencia y crea alertas en una operación.
        """
        db = isolated_database
        repo = DialogueRepository(db)
        manager = get_dialogue_preference_manager(db)

        # Crear proyecto con diálogos
        with db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO projects (
                    name, document_path, document_fingerprint, document_format,
                    settings_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "Manager Test",
                    "/test.docx",
                    "manager-fp",
                    "docx",
                    json.dumps({"dialogue_style_preference": "dash"}),
                ),
            )
            project_id = cursor.lastrowid

            cursor = conn.execute(
                """
                INSERT INTO chapters (
                    project_id, chapter_number, title, content,
                    start_char, end_char
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project_id, 1, "Capítulo 1", "Test", 0, 100),
            )
            chapter_id = cursor.lastrowid

        # Crear diálogos mixtos
        from narrative_assistant.persistence.dialogue import DialogueData

        for i in range(3):
            repo.create(
                DialogueData(
                    id=None,
                    project_id=project_id,
                    chapter_id=chapter_id,
                    start_char=i * 10,
                    end_char=(i + 1) * 10,
                    text="—Dash",
                    dialogue_type="dash",
                    original_format="em_dash",
                    confidence=0.9,
                )
            )

        for i in range(2):
            repo.create(
                DialogueData(
                    id=None,
                    project_id=project_id,
                    chapter_id=chapter_id,
                    start_char=(i + 3) * 10,
                    end_char=(i + 4) * 10,
                    text="« Guillemets »",
                    dialogue_type="guillemets",
                    original_format="guillemets",
                    confidence=0.9,
                )
            )

        # Cambiar preferencia a guillemets usando el manager
        result = manager.update_preference(project_id, "guillemets", min_severity="info")

        assert result.is_success
        assert result.value["preference"] == "guillemets"
        assert result.value["alerts_created"] == 3  # 3 dash generan alerta

        # Verificar que la preferencia se guardó
        with db.connection() as conn:
            conn.row_factory = lambda c, r: dict(
                zip([col[0] for col in c.description], r)
            )
            row = conn.execute(
                "SELECT settings_json FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()

            settings = json.loads(row["settings_json"])
            assert settings["dialogue_style_preference"] == "guillemets"
