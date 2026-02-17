"""
Tests para DialogueRepository.

Cubre:
- CRUD básico (create, create_batch, get, delete)
- Consultas por tipo (get_by_type, get_by_type_not)
- Conteo por tipo (count_by_type)
- Preservación de original_format
"""

import pytest

from narrative_assistant.persistence.dialogue import DialogueData, DialogueRepository


def _create_project(db, name: str = "test-project") -> int:
    """Helper para crear un proyecto de prueba."""
    with db.connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO projects (name, document_path, document_fingerprint, document_format)
            VALUES (?, ?, ?, ?)
            """,
            (name, "/tmp/test.docx", f"{name}-fp", "docx"),
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
            (project_id, chapter_number, "Capítulo", "Contenido de prueba", 0, 100),
        )
        return cursor.lastrowid


@pytest.fixture
def repo(isolated_database):
    """Instancia del repositorio con DB aislada."""
    return DialogueRepository(isolated_database)


@pytest.fixture
def sample_project(isolated_database):
    """Proyecto de prueba con un capítulo."""
    project_id = _create_project(isolated_database, "dialogue-test")
    chapter_id = _create_chapter(isolated_database, project_id)
    return {"project_id": project_id, "chapter_id": chapter_id}


# =============================================================================
# Tests de creación
# =============================================================================


class TestCreate:
    """Tests para create() y create_batch()."""

    def test_create_single_dialogue(self, repo, sample_project):
        """Crea un diálogo correctamente."""
        dialogue = DialogueData(
            id=None,
            project_id=sample_project["project_id"],
            chapter_id=sample_project["chapter_id"],
            start_char=10,
            end_char=30,
            text="—Hola, ¿cómo estás?",
            dialogue_type="dash",
            original_format="em_dash",
            confidence=0.95,
        )

        created = repo.create(dialogue)

        assert created.id is not None
        assert created.text == "—Hola, ¿cómo estás?"
        assert created.dialogue_type == "dash"
        assert created.original_format == "em_dash"
        assert created.confidence == 0.95

    def test_create_batch(self, repo, sample_project):
        """Crea múltiples diálogos en batch."""
        dialogues = [
            DialogueData(
                id=None,
                project_id=sample_project["project_id"],
                chapter_id=sample_project["chapter_id"],
                start_char=i * 20,
                end_char=(i + 1) * 20,
                text=f"—Diálogo {i + 1}",
                dialogue_type="dash",
                original_format="em_dash" if i % 2 == 0 else "minus",
                confidence=0.9,
            )
            for i in range(5)
        ]

        created_list = repo.create_batch(dialogues)

        assert len(created_list) == 5
        for created in created_list:
            assert created.id is not None

    def test_create_preserves_original_format(self, repo, sample_project):
        """Preserva el campo original_format correctamente."""
        formats = ["em_dash", "en_dash", "minus", "double_minus", "guillemets", "quotes_straight"]

        for fmt in formats:
            dialogue = DialogueData(
                id=None,
                project_id=sample_project["project_id"],
                chapter_id=sample_project["chapter_id"],
                start_char=0,
                end_char=10,
                text="—Test",
                dialogue_type="dash",
                original_format=fmt,
                confidence=0.9,
            )

            created = repo.create(dialogue)
            assert created.original_format == fmt

    def test_create_with_optional_fields(self, repo, sample_project):
        """Crea diálogo con campos opcionales (attribution, speaker)."""
        dialogue = DialogueData(
            id=None,
            project_id=sample_project["project_id"],
            chapter_id=sample_project["chapter_id"],
            start_char=0,
            end_char=20,
            text="—Hola",
            dialogue_type="dash",
            original_format="em_dash",
            attribution_text="dijo María",
            speaker_hint="María",
            speaker_entity_id=None,  # No establecer FK si no existe la entidad
            confidence=0.85,
        )

        created = repo.create(dialogue)

        assert created.attribution_text == "dijo María"
        assert created.speaker_hint == "María"
        assert created.speaker_entity_id is None  # Verificar que es None


# =============================================================================
# Tests de lectura
# =============================================================================


class TestRead:
    """Tests para get() y consultas."""

    def test_get_by_project(self, repo, sample_project):
        """Obtiene todos los diálogos de un proyecto."""
        # Crear 3 diálogos
        for i in range(3):
            repo.create(
                DialogueData(
                    id=None,
                    project_id=sample_project["project_id"],
                    chapter_id=sample_project["chapter_id"],
                    start_char=i * 10,
                    end_char=(i + 1) * 10,
                    text=f"—Diálogo {i}",
                    dialogue_type="dash",
                    original_format="em_dash",
                    confidence=0.9,
                )
            )

        dialogues = repo.get_by_project(sample_project["project_id"])

        assert len(dialogues) == 3
        # Deben estar ordenados por chapter_id, start_char
        assert dialogues[0].start_char == 0
        assert dialogues[1].start_char == 10
        assert dialogues[2].start_char == 20

    def test_get_by_type(self, repo, sample_project):
        """Filtra diálogos por tipo."""
        # Crear diálogos de diferentes tipos
        types = ["dash", "dash", "guillemets", "quotes"]
        for i, dlg_type in enumerate(types):
            repo.create(
                DialogueData(
                    id=None,
                    project_id=sample_project["project_id"],
                    chapter_id=sample_project["chapter_id"],
                    start_char=i * 10,
                    end_char=(i + 1) * 10,
                    text=f"Diálogo {i}",
                    dialogue_type=dlg_type,
                    original_format="em_dash",
                    confidence=0.9,
                )
            )

        dash_dialogues = repo.get_by_type(sample_project["project_id"], "dash")

        assert len(dash_dialogues) == 2
        for dlg in dash_dialogues:
            assert dlg.dialogue_type == "dash"

    def test_get_by_type_not(self, repo, sample_project):
        """Obtiene diálogos que NO son de un tipo específico."""
        # Crear 3 dash y 2 guillemets
        for i in range(3):
            repo.create(
                DialogueData(
                    id=None,
                    project_id=sample_project["project_id"],
                    chapter_id=sample_project["chapter_id"],
                    start_char=i * 10,
                    end_char=(i + 1) * 10,
                    text=f"—Diálogo {i}",
                    dialogue_type="dash",
                    original_format="em_dash",
                    confidence=0.9,
                )
            )

        for i in range(2):
            repo.create(
                DialogueData(
                    id=None,
                    project_id=sample_project["project_id"],
                    chapter_id=sample_project["chapter_id"],
                    start_char=(i + 10) * 10,
                    end_char=(i + 11) * 10,
                    text=f"«Comillas {i}»",
                    dialogue_type="guillemets",
                    original_format="guillemets",
                    confidence=0.9,
                )
            )

        # Obtener todo lo que NO es dash (debe ser guillemets)
        non_dash = repo.get_by_type_not(sample_project["project_id"], "dash")

        assert len(non_dash) == 2
        for dlg in non_dash:
            assert dlg.dialogue_type == "guillemets"

    def test_count_by_type(self, repo, sample_project):
        """Cuenta diálogos por tipo."""
        # Crear 3 dash, 2 guillemets, 1 quotes
        counts = {"dash": 3, "guillemets": 2, "quotes": 1}

        for dlg_type, count in counts.items():
            for i in range(count):
                repo.create(
                    DialogueData(
                        id=None,
                        project_id=sample_project["project_id"],
                        chapter_id=sample_project["chapter_id"],
                        start_char=i * 10,
                        end_char=(i + 1) * 10,
                        text="Texto",
                        dialogue_type=dlg_type,
                        original_format="em_dash",
                        confidence=0.9,
                    )
                )

        dash_count = repo.count_by_type(sample_project["project_id"], "dash")
        guillemets_count = repo.count_by_type(sample_project["project_id"], "guillemets")
        quotes_count = repo.count_by_type(sample_project["project_id"], "quotes")

        assert dash_count == 3
        assert guillemets_count == 2
        assert quotes_count == 1


# =============================================================================
# Tests de eliminación
# =============================================================================


class TestDelete:
    """Tests para delete_by_project()."""

    def test_delete_by_project(self, repo, sample_project, isolated_database):
        """Elimina todos los diálogos de un proyecto."""
        # Crear 5 diálogos
        for i in range(5):
            repo.create(
                DialogueData(
                    id=None,
                    project_id=sample_project["project_id"],
                    chapter_id=sample_project["chapter_id"],
                    start_char=i * 10,
                    end_char=(i + 1) * 10,
                    text=f"Diálogo {i}",
                    dialogue_type="dash",
                    original_format="em_dash",
                    confidence=0.9,
                )
            )

        # Verificar que se crearon
        before = repo.get_by_project(sample_project["project_id"])
        assert len(before) == 5

        # Eliminar
        deleted = repo.delete_by_project(sample_project["project_id"])
        assert deleted == 5

        # Verificar que se eliminaron
        after = repo.get_by_project(sample_project["project_id"])
        assert len(after) == 0

    def test_delete_by_project_only_affects_target_project(
        self, repo, isolated_database
    ):
        """delete_by_project no afecta a otros proyectos."""
        # Crear 2 proyectos
        project1_id = _create_project(isolated_database, "project1")
        project2_id = _create_project(isolated_database, "project2")
        chapter1_id = _create_chapter(isolated_database, project1_id)
        chapter2_id = _create_chapter(isolated_database, project2_id)

        # Crear diálogos en ambos proyectos
        for pid, cid in [(project1_id, chapter1_id), (project2_id, chapter2_id)]:
            for i in range(3):
                repo.create(
                    DialogueData(
                        id=None,
                        project_id=pid,
                        chapter_id=cid,
                        start_char=i * 10,
                        end_char=(i + 1) * 10,
                        text=f"Diálogo {i}",
                        dialogue_type="dash",
                        original_format="em_dash",
                        confidence=0.9,
                    )
                )

        # Eliminar solo project1
        deleted = repo.delete_by_project(project1_id)
        assert deleted == 3

        # Verificar que project2 no se afectó
        project1_dialogues = repo.get_by_project(project1_id)
        project2_dialogues = repo.get_by_project(project2_id)

        assert len(project1_dialogues) == 0
        assert len(project2_dialogues) == 3


# =============================================================================
# Tests de casos límite
# =============================================================================


class TestEdgeCases:
    """Tests para casos límite."""

    def test_get_by_project_empty(self, repo, sample_project):
        """get_by_project devuelve [] si no hay diálogos."""
        dialogues = repo.get_by_project(sample_project["project_id"])
        assert dialogues == []

    def test_count_by_type_zero(self, repo, sample_project):
        """count_by_type devuelve 0 si no hay diálogos de ese tipo."""
        count = repo.count_by_type(sample_project["project_id"], "dash")
        assert count == 0

    def test_delete_by_project_when_empty(self, repo, sample_project):
        """delete_by_project devuelve 0 si no hay diálogos."""
        deleted = repo.delete_by_project(sample_project["project_id"])
        assert deleted == 0

    def test_original_format_can_be_none(self, repo, sample_project):
        """original_format puede ser None (legacy data)."""
        dialogue = DialogueData(
            id=None,
            project_id=sample_project["project_id"],
            chapter_id=sample_project["chapter_id"],
            start_char=0,
            end_char=10,
            text="—Test",
            dialogue_type="dash",
            original_format=None,  # None es válido
            confidence=0.9,
        )

        created = repo.create(dialogue)
        assert created.original_format is None
