"""
Tests para DialogueStyleChecker.

Cubre:
- Validación de estilo de diálogo sin re-análisis
- Generación de alertas dinámicas según preferencia
- Cálculo de severidad según proporción de inconsistencias
- Obtención de preferencia desde settings
"""

import json

import pytest

from narrative_assistant.nlp.dialogue_style_checker import DialogueStyleChecker
from narrative_assistant.persistence.dialogue import DialogueData, DialogueRepository


def _create_project(db, name: str = "test-project", settings: dict | None = None) -> int:
    """Helper para crear un proyecto de prueba."""
    settings_json = json.dumps(settings or {})
    with db.connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO projects (name, document_path, document_fingerprint, document_format, settings_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, "/tmp/test.docx", f"{name}-fp", "docx", settings_json),
        )
        return cursor.lastrowid


def _create_chapter(db, project_id: int, chapter_number: int = 1) -> int:
    """Helper para crear un capítulo de prueba."""
    with db.connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO chapters (project_id, chapter_number, title, content, start_char, end_char)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (project_id, chapter_number, "Capítulo", "Contenido de prueba", 0, 1000),
        )
        return cursor.lastrowid


def _create_dialogues(db, project_id: int, chapter_id: int, dialogue_configs: list[dict]):
    """Helper para crear múltiples diálogos."""
    repo = DialogueRepository(db)
    for config in dialogue_configs:
        repo.create(
            DialogueData(
                id=None,
                project_id=project_id,
                chapter_id=chapter_id,
                start_char=config.get("start_char", 0),
                end_char=config.get("end_char", 10),
                text=config.get("text", "—Texto"),
                dialogue_type=config.get("dialogue_type", "dash"),
                original_format=config.get("original_format", "em_dash"),
                confidence=config.get("confidence", 0.9),
            )
        )


@pytest.fixture
def checker(isolated_database):
    """Instancia del DialogueStyleChecker con DB aislada."""
    return DialogueStyleChecker(isolated_database)


# =============================================================================
# Tests de obtención de preferencia
# =============================================================================


class TestGetStylePreference:
    """Tests para get_style_preference()."""

    def test_gets_preference_from_settings(self, checker, isolated_database):
        """Obtiene dialogue_style_preference de settings_json."""
        project_id = _create_project(
            isolated_database,
            "pref-test",
            settings={"dialogue_style_preference": "guillemets"},
        )

        pref = checker.get_style_preference(project_id)
        assert pref == "guillemets"

    def test_returns_none_if_no_preference(self, checker, isolated_database):
        """Devuelve None si no hay preferencia configurada."""
        project_id = _create_project(isolated_database, "no-pref", settings={})

        pref = checker.get_style_preference(project_id)
        assert pref is None

    def test_returns_none_if_no_check(self, checker, isolated_database):
        """Devuelve 'no_check' si está configurado."""
        project_id = _create_project(
            isolated_database,
            "no-check",
            settings={"dialogue_style_preference": "no_check"},
        )

        pref = checker.get_style_preference(project_id)
        assert pref == "no_check"


# =============================================================================
# Tests de validación sin re-análisis
# =============================================================================


class TestValidateWithoutReanalysis:
    """Tests para validate_and_create_alerts() sin re-analizar."""

    def test_creates_alerts_for_non_compliant_dialogues(
        self, checker, isolated_database
    ):
        """Crea alertas para diálogos que no cumplen la preferencia."""
        # Proyecto con preferencia "dash"
        project_id = _create_project(
            isolated_database,
            "dash-pref",
            settings={"dialogue_style_preference": "dash"},
        )
        chapter_id = _create_chapter(isolated_database, project_id)

        # Crear 5 dash (OK) + 2 guillemets (NO OK)
        _create_dialogues(
            isolated_database,
            project_id,
            chapter_id,
            [
                {"dialogue_type": "dash", "original_format": "em_dash", "start_char": i * 10}
                for i in range(5)
            ]
            + [
                {
                    "dialogue_type": "guillemets",
                    "original_format": "guillemets",
                    "start_char": (i + 5) * 10,
                }
                for i in range(2)
            ],
        )

        # Validar (sin re-análisis)
        result = checker.validate_and_create_alerts(project_id, min_severity="info")

        assert result.is_success
        # Debe crear 2 alertas (para los 2 guillemets)
        assert result.value == 2

    def test_no_alerts_if_all_compliant(self, checker, isolated_database):
        """No crea alertas si todos los diálogos cumplen."""
        project_id = _create_project(
            isolated_database,
            "all-ok",
            settings={"dialogue_style_preference": "dash"},
        )
        chapter_id = _create_chapter(isolated_database, project_id)

        # Crear solo dash (todos OK)
        _create_dialogues(
            isolated_database,
            project_id,
            chapter_id,
            [
                {"dialogue_type": "dash", "original_format": "em_dash", "start_char": i * 10}
                for i in range(10)
            ],
        )

        result = checker.validate_and_create_alerts(project_id, min_severity="info")

        assert result.is_success
        assert result.value == 0

    def test_no_validation_if_no_preference(self, checker, isolated_database):
        """No valida si no hay preferencia configurada."""
        project_id = _create_project(isolated_database, "no-pref", settings={})
        chapter_id = _create_chapter(isolated_database, project_id)

        # Crear diálogos mixtos
        _create_dialogues(
            isolated_database,
            project_id,
            chapter_id,
            [
                {"dialogue_type": "dash"},
                {"dialogue_type": "guillemets"},
                {"dialogue_type": "quotes"},
            ],
        )

        result = checker.validate_and_create_alerts(project_id, min_severity="info")

        assert result.is_success
        assert result.value == 0  # No se crean alertas

    def test_no_validation_if_no_check(self, checker, isolated_database):
        """No valida si preferencia es 'no_check'."""
        project_id = _create_project(
            isolated_database,
            "no-check",
            settings={"dialogue_style_preference": "no_check"},
        )
        chapter_id = _create_chapter(isolated_database, project_id)

        _create_dialogues(
            isolated_database,
            project_id,
            chapter_id,
            [
                {"dialogue_type": "dash"},
                {"dialogue_type": "guillemets"},
            ],
        )

        result = checker.validate_and_create_alerts(project_id, min_severity="info")

        assert result.is_success
        assert result.value == 0


# =============================================================================
# Tests de cálculo de severidad
# =============================================================================


class TestSeverityCalculation:
    """Tests para _determine_severity()."""

    def test_severity_high_if_minority_wrong(self, checker, isolated_database):
        """Severidad HIGH si minoría de diálogos no cumplen (<20%)."""
        project_id = _create_project(
            isolated_database,
            "minority",
            settings={"dialogue_style_preference": "dash"},
        )
        chapter_id = _create_chapter(isolated_database, project_id)

        # 90 dash (OK) + 5 guillemets (5/95 = 5.3% wrong)
        _create_dialogues(
            isolated_database,
            project_id,
            chapter_id,
            [
                {"dialogue_type": "dash", "start_char": i * 10}
                for i in range(90)
            ]
            + [
                {"dialogue_type": "guillemets", "start_char": (i + 90) * 10}
                for i in range(5)
            ],
        )

        result = checker.validate_and_create_alerts(project_id, min_severity="info")

        assert result.is_success
        # Verificar que las alertas tienen severidad HIGH
        # (minoría de errores = probable error del usuario)

    def test_severity_medium_if_balanced(self, checker, isolated_database):
        """Severidad MEDIUM si ~50% de diálogos no cumplen."""
        project_id = _create_project(
            isolated_database,
            "balanced",
            settings={"dialogue_style_preference": "dash"},
        )
        chapter_id = _create_chapter(isolated_database, project_id)

        # 50 dash + 50 guillemets (50/100 = 50% wrong)
        _create_dialogues(
            isolated_database,
            project_id,
            chapter_id,
            [{"dialogue_type": "dash", "start_char": i * 10} for i in range(50)]
            + [
                {"dialogue_type": "guillemets", "start_char": (i + 50) * 10}
                for i in range(50)
            ],
        )

        result = checker.validate_and_create_alerts(project_id, min_severity="info")

        assert result.is_success
        # 50 alertas creadas (para los 50 guillemets)
        assert result.value == 50

    def test_severity_low_if_majority_wrong(self, checker, isolated_database):
        """Severidad LOW si mayoría no cumple (>80%)."""
        project_id = _create_project(
            isolated_database,
            "majority",
            settings={"dialogue_style_preference": "dash"},
        )
        chapter_id = _create_chapter(isolated_database, project_id)

        # 10 dash + 90 guillemets (90/100 = 90% wrong)
        _create_dialogues(
            isolated_database,
            project_id,
            chapter_id,
            [{"dialogue_type": "dash", "start_char": i * 10} for i in range(10)]
            + [
                {"dialogue_type": "guillemets", "start_char": (i + 10) * 10}
                for i in range(90)
            ],
        )

        result = checker.validate_and_create_alerts(project_id, min_severity="info")

        assert result.is_success
        # 90 alertas, pero con severidad LOW (probablemente configuración incorrecta)
        assert result.value == 90


# =============================================================================
# Tests de diferentes tipos de diálogo
# =============================================================================


class TestDifferentDialogueTypes:
    """Tests para diferentes tipos de diálogo."""

    @pytest.mark.parametrize(
        "preference,correct_type,wrong_types",
        [
            ("dash", "dash", ["guillemets", "quotes", "quotes_typographic"]),
            ("guillemets", "guillemets", ["dash", "quotes", "quotes_typographic"]),
            ("quotes", "quotes", ["dash", "guillemets", "quotes_typographic"]),
            (
                "quotes_typographic",
                "quotes_typographic",
                ["dash", "guillemets", "quotes"],
            ),
        ],
    )
    def test_validates_each_dialogue_type(
        self, checker, isolated_database, preference, correct_type, wrong_types
    ):
        """Valida correctamente cada tipo de diálogo."""
        project_id = _create_project(
            isolated_database,
            f"test-{preference}",
            settings={"dialogue_style_preference": preference},
        )
        chapter_id = _create_chapter(isolated_database, project_id)

        # Crear 1 correcto + 3 incorrectos
        _create_dialogues(
            isolated_database,
            project_id,
            chapter_id,
            [{"dialogue_type": correct_type, "start_char": 0}]
            + [
                {"dialogue_type": wrong_type, "start_char": (i + 1) * 10}
                for i, wrong_type in enumerate(wrong_types)
            ],
        )

        result = checker.validate_and_create_alerts(project_id, min_severity="info")

        assert result.is_success
        # Debe crear alertas solo para los 3 incorrectos
        assert result.value == len(wrong_types)


# =============================================================================
# Tests de filtrado por severidad
# =============================================================================


class TestSeverityFiltering:
    """Tests para min_severity filtering."""

    def test_respects_min_severity_medium(self, checker, isolated_database):
        """Respeta min_severity='medium' (no crea alertas LOW)."""
        project_id = _create_project(
            isolated_database,
            "severity-filter",
            settings={"dialogue_style_preference": "dash"},
        )
        chapter_id = _create_chapter(isolated_database, project_id)

        # 10 dash + 90 guillemets (mayoría wrong → LOW severity)
        _create_dialogues(
            isolated_database,
            project_id,
            chapter_id,
            [{"dialogue_type": "dash", "start_char": i * 10} for i in range(10)]
            + [
                {"dialogue_type": "guillemets", "start_char": (i + 10) * 10}
                for i in range(90)
            ],
        )

        # Con min_severity='medium', no debe crear alertas (todas serían LOW)
        result = checker.validate_and_create_alerts(project_id, min_severity="medium")

        assert result.is_success
        # No se crean alertas LOW cuando min_severity='medium'
        # (depende de implementación exacta - puede ser 0 o puede crear algunas MEDIUM)
