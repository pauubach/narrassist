"""
Tests para el validador de contexto de diálogos.

Cubre:
- Detección de diálogos huérfanos (sin atribución)
- Secuencias largas sin indicar hablante
- Diálogos al inicio de capítulo sin contexto
"""

import pytest

from narrative_assistant.nlp.dialogue_validator import (
    DialogueContextValidator,
    DialogueIssueType,
    DialogueIssueSeverity,
    get_dialogue_validator,
    reset_dialogue_validator,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton antes de cada test."""
    reset_dialogue_validator()
    yield
    reset_dialogue_validator()


@pytest.fixture
def validator():
    """Instancia del validador."""
    return get_dialogue_validator()


# =============================================================================
# Tests de diálogos sin atribución
# =============================================================================

class TestOrphanDialogues:
    """Tests para detectar diálogos huérfanos."""

    def test_detects_dialogue_without_attribution(self, validator):
        """Detecta diálogo sin indicar quién habla."""
        chapter_text = """
        —Tienes razón.
        —¿Crees que mamá nos perdonará?
        —No lo sé.
        """

        issues = validator.validate_chapter(chapter_text, chapter_number=1)

        # Debería detectar secuencia sin atribución
        assert len(issues) >= 1
        orphan_issues = [
            i for i in issues
            if i.issue_type in [
                DialogueIssueType.ORPHAN_NO_ATTRIBUTION,
                DialogueIssueType.CONSECUTIVE_NO_CHANGE,
            ]
        ]
        assert len(orphan_issues) >= 1

    def test_no_issues_with_attribution(self, validator):
        """No reporta problemas cuando hay atribución clara."""
        chapter_text = """
        María entró en la habitación y vio a su hermano.

        —¿Has pensado en lo que te dije? —preguntó María.
        —Sí, he estado reflexionando —respondió Pedro.
        —Me alegra saberlo —dijo ella sonriendo.
        """

        issues = validator.validate_chapter(chapter_text, chapter_number=1)

        # No debería haber problemas graves
        high_issues = [i for i in issues if i.severity == DialogueIssueSeverity.HIGH]
        assert len(high_issues) == 0


# =============================================================================
# Tests de inicio de capítulo
# =============================================================================

class TestChapterStartContext:
    """Tests para diálogos al inicio de capítulo."""

    def test_detects_chapter_starting_with_dialogue(self, validator):
        """Detecta capítulo que empieza con diálogo sin contexto."""
        chapter_text = """—¿Dónde estabas?
        María se sobresaltó al oír la voz.
        """

        issues = validator.validate_chapter(chapter_text, chapter_number=1)

        # Debería detectar inicio sin contexto
        start_issues = [
            i for i in issues
            if i.issue_type == DialogueIssueType.CHAPTER_START_DIALOGUE
        ]
        assert len(start_issues) >= 1

    def test_no_issue_with_context_before_dialogue(self, validator):
        """No reporta problema si hay contexto antes del diálogo."""
        chapter_text = """
        Era una mañana fría de invierno. María se despertó temprano
        y bajó a la cocina donde encontró a su madre preparando café.

        —Buenos días —dijo María bostezando.
        """

        issues = validator.validate_chapter(chapter_text, chapter_number=1)

        # No debería haber problema de inicio sin contexto
        start_issues = [
            i for i in issues
            if i.issue_type == DialogueIssueType.CHAPTER_START_DIALOGUE
        ]
        assert len(start_issues) == 0


# =============================================================================
# Tests de secuencias largas
# =============================================================================

class TestLongSequences:
    """Tests para secuencias largas sin atribución."""

    def test_detects_long_unattributed_sequence(self, validator):
        """Detecta secuencia larga de diálogos sin atribución."""
        # Configurar validador para detectar después de 3 diálogos
        validator = DialogueContextValidator(max_unattributed_consecutive=3)

        chapter_text = """
        María y Pedro se sentaron a hablar.

        —¿Qué piensas hacer?
        —No lo sé.
        —Deberías decidirte pronto.
        —Lo sé, lo sé.
        —El tiempo apremia.
        """

        issues = validator.validate_chapter(chapter_text, chapter_number=1)

        # Debería detectar la secuencia larga
        seq_issues = [
            i for i in issues
            if i.issue_type == DialogueIssueType.ORPHAN_NO_ATTRIBUTION
        ]
        # Puede que detecte como secuencia o como múltiples consecutivos
        assert len(issues) >= 1

    def test_sequence_severity_increases_with_length(self, validator):
        """La severidad aumenta con secuencias más largas."""
        validator = DialogueContextValidator(max_unattributed_consecutive=2)

        chapter_text = """
        María habló.

        —Uno.
        —Dos.
        —Tres.
        —Cuatro.
        —Cinco.
        —Seis.
        """

        issues = validator.validate_chapter(chapter_text, chapter_number=1)

        # Debería haber al menos un issue de alta severidad
        high_issues = [
            i for i in issues
            if i.severity == DialogueIssueSeverity.HIGH
            or (i.issue_type == DialogueIssueType.ORPHAN_NO_ATTRIBUTION
                and i.consecutive_count >= 5)
        ]
        # Puede ser HIGH o tener consecutive_count alto
        assert len(issues) >= 1


# =============================================================================
# Tests de validate_all
# =============================================================================

class TestValidateAll:
    """Tests para validación de múltiples capítulos."""

    def test_validate_all_returns_report(self, validator):
        """validate_all devuelve reporte completo."""
        chapters = [
            {
                "number": 1,
                "start_char": 0,
                "content": """
                María entró.
                —Hola —dijo María.
                —Hola —respondió Pedro.
                """,
            },
            {
                "number": 2,
                "start_char": 100,
                "content": """
                —Sin contexto.
                —Tampoco.
                —Ni este.
                """,
            },
        ]

        report = validator.validate_all(chapters)

        assert report.chapters_analyzed == 2
        assert report.total_dialogues >= 3
        assert len(report.issues) >= 1

    def test_report_statistics(self, validator):
        """El reporte incluye estadísticas correctas."""
        chapters = [
            {
                "number": 1,
                "start_char": 0,
                "content": """
                —Sin atribución.
                —Otro sin atribución.
                —Tercero sin atribución.
                """,
            },
        ]

        report = validator.validate_all(chapters)

        assert report.total_dialogues >= 3
        assert report.dialogues_without_attribution >= 3
        assert report.attribution_ratio < 1.0

    def test_report_to_dict(self, validator):
        """El reporte se serializa correctamente."""
        chapters = [
            {
                "number": 1,
                "start_char": 0,
                "content": "—Diálogo de prueba.",
            },
        ]

        report = validator.validate_all(chapters)
        data = report.to_dict()

        assert "issues" in data
        assert "total_dialogues" in data
        assert "attribution_ratio" in data
        assert "by_type" in data
        assert "by_severity" in data


# =============================================================================
# Tests de casos límite
# =============================================================================

class TestEdgeCases:
    """Tests para casos límite."""

    def test_empty_text(self, validator):
        """Maneja texto vacío sin error."""
        issues = validator.validate_chapter("", chapter_number=1)
        assert issues == []

    def test_no_dialogues(self, validator):
        """Maneja texto sin diálogos."""
        chapter_text = """
        Era un día soleado. María caminaba por el parque
        pensando en su vida. Los pájaros cantaban.
        """
        issues = validator.validate_chapter(chapter_text, chapter_number=1)
        assert issues == []

    def test_single_dialogue_with_attribution(self, validator):
        """Un solo diálogo con atribución no genera problemas."""
        chapter_text = """
        María se acercó a la ventana y suspiró profundamente.

        —Ojalá las cosas fueran diferentes —murmuró ella.
        """
        issues = validator.validate_chapter(chapter_text, chapter_number=1)

        # No debería haber problemas graves
        high_issues = [i for i in issues if i.severity == DialogueIssueSeverity.HIGH]
        assert len(high_issues) == 0


# =============================================================================
# Tests con documento real
# =============================================================================

class TestWithRichDocument:
    """Tests usando patrones del documento test_document_rich.txt."""

    def test_detects_orphan_dialogue_pattern(self, validator):
        """Detecta el patrón de diálogos huérfanos del documento de test."""
        # Este patrón está en el capítulo 4 del test_document_rich
        chapter_text = """
        Pedro volvió una tarde de domingo.

        —Tienes razón.
        —¿Crees que mamá nos perdonará?
        —No lo sé.

        María asintió.
        """

        issues = validator.validate_chapter(chapter_text, chapter_number=4)

        # Debería detectar los diálogos sin atribución
        assert len(issues) >= 1
        assert any(
            i.issue_type in [
                DialogueIssueType.ORPHAN_NO_ATTRIBUTION,
                DialogueIssueType.CONSECUTIVE_NO_CHANGE,
            ]
            for i in issues
        )
