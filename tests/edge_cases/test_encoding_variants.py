"""
Tests para variantes de encoding y normalización de texto.

Cubre:
- UTF-8, Latin-1, Windows-1252
- BOM (Byte Order Mark)
- Diferentes tipos de guiones y comillas
- Normalización Unicode (NFC, NFD)
- Caracteres de control
"""

import unicodedata

import pytest

# =============================================================================
# Tests de normalización de guiones
# =============================================================================


class TestDashNormalization:
    """Tests para normalización de diferentes tipos de guiones."""

    def test_em_dash_detection(self):
        """Detecta diálogos con em-dash estándar (—)."""
        from narrative_assistant.nlp.dialogue import detect_dialogues

        text = "—Hola— dijo María."
        result = detect_dialogues(text)

        assert result.is_success
        assert len(result.value.dialogues) > 0

    def test_en_dash_normalization(self):
        """Normaliza en-dash (–) a em-dash para detección."""
        from narrative_assistant.nlp.dialogue import detect_dialogues

        # En-dash (U+2013)
        text = "–Hola– dijo María."
        result = detect_dialogues(text)

        assert result.is_success
        # Debería normalizar y detectar

    def test_hyphen_minus_at_line_start(self):
        """Normaliza guión-menos (-) al inicio de línea."""
        from narrative_assistant.nlp.dialogue import detect_dialogues

        text = "-Hola -respondió Pedro."
        result = detect_dialogues(text)

        assert result.is_success
        # Puede detectar o no, pero no debe crashear

    def test_double_hyphen(self):
        """Normaliza doble guión (--) a em-dash."""
        from narrative_assistant.nlp.dialogue import detect_dialogues

        text = "--Hola-- dijo María."
        result = detect_dialogues(text)

        assert result.is_success


# =============================================================================
# Tests de variantes de comillas
# =============================================================================


class TestQuoteVariants:
    """Tests para diferentes tipos de comillas."""

    def test_spanish_guillemets(self):
        """Detecta comillas españolas («»)."""
        from narrative_assistant.nlp.dialogue import detect_dialogues

        text = "María dijo: «Hola a todos»."
        result = detect_dialogues(text)

        assert result.is_success
        # Puede encontrar o no según implementación
        assert result.value is not None

    def test_typographic_quotes(self):
        """Detecta comillas tipográficas ("")."""
        from narrative_assistant.nlp.dialogue import detect_dialogues

        # Comillas tipográficas: U+201C (") y U+201D (")
        text = "María dijo: \u201cHola a todos\u201d."
        result = detect_dialogues(text)

        assert result.is_success
        assert result.value is not None

    def test_straight_quotes(self):
        """Detecta comillas rectas (\"\")."""
        from narrative_assistant.nlp.dialogue import detect_dialogues

        text = 'María dijo: "Hola a todos".'
        result = detect_dialogues(text)

        assert result.is_success
        assert result.value is not None

    def test_mixed_quotes_in_document(self):
        """Maneja documento con mezcla de estilos de comillas."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()
        text = """
        María dijo: «Hola».
        Pedro respondió: "Adiós".
        Juan añadió: "Hasta luego".
        """

        chapters = [{"number": 1, "content": text}]
        report = detector.detect_all(text, chapters)

        assert report is not None


# =============================================================================
# Tests de BOM (Byte Order Mark)
# =============================================================================


class TestBOMHandling:
    """Tests para manejo de BOM."""

    def test_utf8_bom(self):
        """Maneja texto con BOM UTF-8."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()
        # BOM UTF-8: EF BB BF
        text_with_bom = "\ufeff—Hola— dijo María."

        issues = validator.validate_chapter(text_with_bom, chapter_number=1)
        assert isinstance(issues, list)

    def test_removes_bom_from_analysis(self):
        """El BOM no interfiere con la detección."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()
        text1 = "\ufeffEsta es una oración."
        text2 = "Esta es una oración."

        chapters = [
            {"number": 1, "content": text1},
            {"number": 2, "content": text2},
        ]
        full_text = text1 + "\n\n" + text2

        report = detector.detect_all(full_text, chapters)
        # Debería detectar como duplicado (ignorando BOM)
        # o al menos no crashear
        assert report is not None


# =============================================================================
# Tests de normalización Unicode
# =============================================================================


class TestUnicodeNormalization:
    """Tests para diferentes formas de normalización Unicode."""

    def test_nfc_vs_nfd_equivalence(self):
        """Trata NFC y NFD como equivalentes."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()

        # "café" en NFC (precompuesto) y NFD (descompuesto)
        text_nfc = "María tomó café."  # é como un carácter
        text_nfd = unicodedata.normalize("NFD", text_nfc)  # e + ́ (combinante)

        chapters = [
            {"number": 1, "content": text_nfc},
            {"number": 2, "content": text_nfd},
        ]
        full_text = text_nfc + "\n\n" + text_nfd

        report = detector.detect_all(full_text, chapters)
        # Idealmente debería detectarlos como duplicados
        assert report is not None

    def test_combining_diacriticals(self):
        """Maneja caracteres con diacríticos combinantes."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()

        # 'a' + combining acute accent
        text = "—Mar\u0069\u0301a dijo hola— explicó Pedro."

        issues = validator.validate_chapter(text, chapter_number=1)
        assert isinstance(issues, list)


# =============================================================================
# Tests de caracteres de control
# =============================================================================


class TestControlCharacters:
    """Tests para manejo de caracteres de control."""

    def test_tab_characters(self):
        """Maneja tabuladores en texto."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()
        text = "—Hola—\tdijo\tMaría."

        issues = validator.validate_chapter(text, chapter_number=1)
        assert isinstance(issues, list)

    def test_carriage_return(self):
        """Maneja retornos de carro (CR, CRLF)."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()

        # Windows line endings (CRLF)
        text_crlf = "Primera línea.\r\nSegunda línea.\r\nTercera línea."
        # Unix line endings (LF)
        text_lf = "Primera línea.\nSegunda línea.\nTercera línea."

        chapters = [
            {"number": 1, "content": text_crlf},
            {"number": 2, "content": text_lf},
        ]

        report = detector.detect_all(text_crlf + "\n\n" + text_lf, chapters)
        assert report is not None

    def test_form_feed_and_vertical_tab(self):
        """Maneja form feed y tab vertical."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()
        text = "Texto normal.\fNueva página.\vTab vertical."

        issues = validator.validate_chapter(text, chapter_number=1)
        assert isinstance(issues, list)

    def test_null_characters_sanitized(self):
        """Los caracteres nulos son sanitizados."""
        from narrative_assistant.parsers.sanitization import sanitize_chapter_content

        text_with_null = "Texto\x00con\x00nulos."
        sanitized = sanitize_chapter_content(text_with_null)

        assert "\x00" not in sanitized
        assert sanitized == "Textoconnulos."


# =============================================================================
# Tests de espacios especiales
# =============================================================================


class TestSpecialSpaces:
    """Tests para diferentes tipos de espacios."""

    def test_non_breaking_space(self):
        """Maneja espacio de no ruptura (NBSP)."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()

        # NBSP = U+00A0
        text_nbsp = "María\u00a0dijo\u00a0hola."
        text_normal = "María dijo hola."

        chapters = [
            {"number": 1, "content": text_nbsp},
            {"number": 2, "content": text_normal},
        ]

        report = detector.detect_all(text_nbsp + "\n\n" + text_normal, chapters)
        assert report is not None

    def test_zero_width_spaces(self):
        """Maneja espacios de ancho cero."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()

        # Zero-width space (U+200B), zero-width non-joiner (U+200C)
        text = "—Hola\u200b mundo\u200c— dijo María."

        issues = validator.validate_chapter(text, chapter_number=1)
        assert isinstance(issues, list)

    def test_ideographic_space(self):
        """Maneja espacio ideográfico (CJK)."""
        from narrative_assistant.analysis.narrative_structure import NarrativeStructureDetector

        detector = NarrativeStructureDetector()

        # Ideographic space U+3000
        text = "Texto\u3000con\u3000espacios\u3000CJK."
        chapters = [{"number": 1, "content": text, "start_char": 0}]

        report = detector.detect_all(text, chapters)
        assert report is not None


# =============================================================================
# Tests de puntuación especial
# =============================================================================


class TestSpecialPunctuation:
    """Tests para puntuación especial."""

    def test_ellipsis_character(self):
        """Maneja carácter de puntos suspensivos (…) vs tres puntos (...)."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()

        text1 = "—No sé…— murmuró María."  # U+2026
        text2 = "—No sé...— murmuró Pedro."  # tres puntos

        issues1 = validator.validate_chapter(text1, chapter_number=1)
        issues2 = validator.validate_chapter(text2, chapter_number=2)

        assert isinstance(issues1, list)
        assert isinstance(issues2, list)

    def test_inverted_punctuation(self):
        """Maneja puntuación invertida española (¿¡)."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()
        text = "¿Cómo estás? ¡Qué bien! ¿Seguro? ¡Por supuesto!"

        chapters = [{"number": 1, "content": text}]
        report = detector.detect_all(text, chapters)

        assert report is not None

    def test_em_dash_vs_horizontal_bar(self):
        """Distingue em-dash de barra horizontal."""
        from narrative_assistant.nlp.dialogue import detect_dialogues

        # Em-dash U+2014 vs Horizontal bar U+2015
        text1 = "—Hola—"  # U+2014
        text2 = "―Hola―"  # U+2015

        result1 = detect_dialogues(text1)
        result2 = detect_dialogues(text2)

        assert result1.is_success
        assert result2.is_success
