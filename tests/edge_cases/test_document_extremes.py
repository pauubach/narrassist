"""
Tests para casos extremos de documentos.

Cubre:
- Documentos vacíos
- Documentos con un solo carácter
- Documentos sin capítulos
- Documentos con miles de capítulos
- Capítulos vacíos
- Texto solo de puntuación
- Solo espacios en blanco
"""

import pytest
from pathlib import Path


# =============================================================================
# Tests de documentos vacíos y mínimos
# =============================================================================

class TestEmptyDocuments:
    """Tests para documentos vacíos o casi vacíos."""

    def test_dialogue_validator_empty_text(self):
        """El validador de diálogos maneja texto vacío."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()
        issues = validator.validate_chapter("", chapter_number=1)

        assert issues == []

    def test_duplicate_detector_empty_text(self):
        """El detector de duplicados maneja texto vacío."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()
        result = detector.detect_all("", [])

        assert result.is_success
        report = result.value
        assert report.sentences_analyzed == 0
        assert report.duplicates == []

    def test_narrative_structure_empty_text(self):
        """El detector de estructura maneja texto vacío."""
        from narrative_assistant.analysis.narrative_structure import NarrativeStructureDetector

        detector = NarrativeStructureDetector()
        report = detector.detect_all("", [])

        assert report.chapters_analyzed == 0
        assert report.prolepsis_found == []

    def test_single_character_document(self):
        """Maneja documento con un solo carácter."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()

        for char in ["a", ".", "—", "\n", "á"]:
            issues = validator.validate_chapter(char, chapter_number=1)
            assert isinstance(issues, list)

    def test_single_word_document(self):
        """Maneja documento con una sola palabra."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()
        result = detector.detect_all("Palabra", [{"number": 1, "content": "Palabra"}])

        assert result.is_success
        report = result.value
        # No debería haber duplicados con una sola palabra
        assert len(report.duplicates) == 0


# =============================================================================
# Tests de documentos sin estructura
# =============================================================================

class TestUnstructuredDocuments:
    """Tests para documentos sin estructura de capítulos."""

    def test_no_chapters(self):
        """Maneja lista vacía de capítulos."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()
        report = validator.validate_all([])

        assert report.chapters_analyzed == 0
        assert report.issues == []

    def test_only_whitespace_chapter(self):
        """Maneja capítulo solo con espacios en blanco."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()
        chapters = [
            {"number": 1, "content": "   \n\t\n   "},
            {"number": 2, "content": "\n\n\n"},
        ]

        result = detector.detect_all("   \n\t\n   \n\n\n", chapters)
        assert result.is_success
        report = result.value
        assert len(report.duplicates) == 0

    def test_only_punctuation(self):
        """Maneja texto solo con puntuación."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()
        text = "... ??? !!! ,,, --- *** +++ ==="

        issues = validator.validate_chapter(text, chapter_number=1)
        assert isinstance(issues, list)


# =============================================================================
# Tests de documentos con muchos capítulos
# =============================================================================

class TestManyChapters:
    """Tests para documentos con muchos capítulos."""

    def test_hundred_chapters(self):
        """Maneja 100 capítulos sin problemas."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()
        chapters = [
            {"number": i, "content": f"Contenido del capítulo {i}.", "start_char": i * 100}
            for i in range(1, 101)
        ]

        report = validator.validate_all(chapters)

        assert report.chapters_analyzed == 100
        # No debería haber issues de diálogos huérfanos (no hay diálogos)
        assert len(report.issues) == 0

    def test_chapters_with_empty_content(self):
        """Maneja mezcla de capítulos vacíos y con contenido."""
        from narrative_assistant.analysis.narrative_structure import NarrativeStructureDetector

        detector = NarrativeStructureDetector()
        chapters = [
            {"number": 1, "content": "Texto normal.", "start_char": 0},
            {"number": 2, "content": "", "start_char": 20},
            {"number": 3, "content": "   ", "start_char": 30},
            {"number": 4, "content": "Más texto.", "start_char": 40},
        ]

        report = detector.detect_all("Texto normal.\n\n   \n\nMás texto.", chapters)
        # No debería crashear
        assert report is not None


# =============================================================================
# Tests de contenido repetitivo extremo
# =============================================================================

class TestRepetitiveContent:
    """Tests para contenido extremadamente repetitivo."""

    def test_same_sentence_repeated_100_times(self):
        """Detecta correctamente oración repetida 100 veces."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()
        sentence = "Esta es una oración de prueba."
        text = "\n".join([sentence] * 100)

        chapters = [{"number": 1, "content": text}]
        result = detector.detect_all(text, chapters)

        assert result.is_success
        report = result.value
        # Debería detectar muchos duplicados
        assert len(report.duplicates) > 0

    def test_alternating_sentences(self):
        """Maneja oraciones alternantes (A-B-A-B-A-B)."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()
        pattern = ["María dijo hola.", "Pedro respondió adiós."] * 50
        text = " ".join(pattern)

        chapters = [{"number": 1, "content": text}]
        result = detector.detect_all(text, chapters)

        assert result.is_success
        report = result.value
        # Debería detectar las repeticiones
        assert report.sentences_analyzed >= 2


# =============================================================================
# Tests de caracteres especiales
# =============================================================================

class TestSpecialCharacters:
    """Tests para caracteres especiales y Unicode."""

    def test_emoji_heavy_text(self):
        """Maneja texto con muchos emojis."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()
        text = "—🎭 Hola 🎭— dijo 😀 María 🌟 feliz 🎉."

        issues = validator.validate_chapter(text, chapter_number=1)
        assert isinstance(issues, list)

    def test_mixed_scripts(self):
        """Maneja texto con múltiples sistemas de escritura."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()
        text = """
        María dijo: Привет мир. Pedro respondió: 你好世界.
        Luego añadió: مرحبا بالعالم. Y finalmente: שלום עולם.
        """

        chapters = [{"number": 1, "content": text}]
        result = detector.detect_all(text, chapters)

        # No debería crashear con scripts mixtos
        assert result is not None
        assert result.is_success or result.is_partial

    def test_combining_characters(self):
        """Maneja caracteres combinantes Unicode."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()
        # Letra 'a' con múltiples diacríticos combinantes
        text = "—\u0061\u0300\u0301\u0302— dijo alguien."

        issues = validator.validate_chapter(text, chapter_number=1)
        assert isinstance(issues, list)

    def test_right_to_left_text(self):
        """Maneja texto de derecha a izquierda."""
        from narrative_assistant.analysis.narrative_structure import NarrativeStructureDetector

        detector = NarrativeStructureDetector()
        # Texto en hebreo (RTL)
        text = "שלום עולם. זה טקסט בעברית."

        chapters = [{"number": 1, "content": text, "start_char": 0}]
        report = detector.detect_all(text, chapters)

        assert report is not None


# =============================================================================
# Tests de líneas extremadamente largas
# =============================================================================

class TestExtremeLengths:
    """Tests para longitudes extremas."""

    def test_very_long_line_no_breaks(self):
        """Maneja línea muy larga sin saltos."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()
        # 10000 caracteres en una sola línea
        text = "palabra " * 1250  # ~10000 chars

        issues = validator.validate_chapter(text, chapter_number=1)
        assert isinstance(issues, list)

    def test_very_long_sentence(self):
        """Maneja oración muy larga (500+ palabras)."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()
        # Oración de 500 palabras sin punto
        long_sentence = " ".join(["palabra"] * 500) + "."
        text = long_sentence

        chapters = [{"number": 1, "content": text}]
        result = detector.detect_all(text, chapters)

        assert result is not None
        assert result.is_success or result.is_partial

    def test_many_short_lines(self):
        """Maneja muchas líneas cortas."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()
        # 1000 líneas de 1 palabra
        text = "\n".join(["Hola."] * 1000)

        issues = validator.validate_chapter(text, chapter_number=1)
        assert isinstance(issues, list)


# =============================================================================
# Tests de números de capítulo extremos
# =============================================================================

class TestChapterNumbers:
    """Tests para números de capítulo inusuales."""

    def test_chapter_zero(self):
        """Maneja capítulo número 0."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()
        issues = validator.validate_chapter("Texto.", chapter_number=0)

        assert isinstance(issues, list)

    def test_negative_chapter(self):
        """Maneja número de capítulo negativo."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()
        issues = validator.validate_chapter("Texto.", chapter_number=-5)

        assert isinstance(issues, list)

    def test_very_large_chapter_number(self):
        """Maneja número de capítulo muy grande."""
        from narrative_assistant.analysis.narrative_structure import NarrativeStructureDetector

        detector = NarrativeStructureDetector()
        chapters = [
            {"number": 999999, "content": "Texto.", "start_char": 0}
        ]

        report = detector.detect_all("Texto.", chapters)
        assert report is not None


# =============================================================================
# Tests de diálogos extremos
# =============================================================================

class TestDialogueExtremes:
    """Tests para casos extremos de diálogos."""

    def test_only_dialogue_no_narration(self):
        """Maneja texto que es 100% diálogo."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()
        text = """—Hola.
—Adiós.
—Hasta luego.
—Nos vemos.
—Cuídate.
—Igualmente."""

        issues = validator.validate_chapter(text, chapter_number=1)
        # Debería detectar falta de atribución
        assert len(issues) > 0

    def test_nested_quotes(self):
        """Maneja comillas anidadas."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()
        text = '—Ella dijo: "Él respondió: «Nunca»"— explicó Juan.'

        issues = validator.validate_chapter(text, chapter_number=1)
        assert isinstance(issues, list)

    def test_dialogue_with_ellipsis(self):
        """Maneja diálogos con puntos suspensivos."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()
        text = """—Yo creía que...— empezó María.
—¿Qué creías?— interrumpió Pedro.
—Pues que... bueno... no sé...— balbuceó ella."""

        issues = validator.validate_chapter(text, chapter_number=1)
        assert isinstance(issues, list)
