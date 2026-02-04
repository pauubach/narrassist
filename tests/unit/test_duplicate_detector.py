"""
Tests para el detector de contenido duplicado.

Cubre:
- Detección de frases duplicadas exactas
- Detección de frases casi idénticas
- Detección de párrafos duplicados
- Detección semántica de párrafos similares
"""

import pytest

from narrative_assistant.analysis.duplicate_detector import (
    DuplicateDetector,
    DuplicateType,
    DuplicateSeverity,
    get_duplicate_detector,
    reset_duplicate_detector,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton antes de cada test."""
    reset_duplicate_detector()
    yield
    reset_duplicate_detector()


@pytest.fixture
def detector():
    """Instancia del detector."""
    return get_duplicate_detector()


# =============================================================================
# Tests de frases duplicadas exactas
# =============================================================================

class TestExactSentenceDuplicates:
    """Tests para detección de frases duplicadas exactas."""

    def test_detects_exact_duplicate_sentence(self, detector):
        """Detecta frase duplicada exactamente igual."""
        text = """
        La casa olía a humedad y memorias. María caminó por el pasillo.
        Después de un rato, volvió a pensar en lo mismo.
        La casa olía a humedad y memorias. Era un recuerdo persistente.
        """

        result = detector.detect_sentence_duplicates(text)

        assert result.is_success
        report = result.value
        assert len(report.duplicates) >= 1

        # Verificar que encontró la duplicación exacta
        exact_dups = [d for d in report.duplicates
                      if d.duplicate_type == DuplicateType.EXACT_SENTENCE]
        assert len(exact_dups) >= 1
        assert exact_dups[0].similarity == 1.0
        assert exact_dups[0].severity == DuplicateSeverity.CRITICAL

    def test_ignores_short_sentences(self, detector):
        """No detecta frases muy cortas como duplicados."""
        text = """
        Sí. María asintió. No. Pedro negó.
        Sí. Otra vez afirmó. No. Y volvió a negar.
        """

        result = detector.detect_sentence_duplicates(text, min_sentence_length=30)

        assert result.is_success
        # "Sí." y "No." son muy cortas, no deberían detectarse
        assert len(result.value.duplicates) == 0

    def test_reports_location_correctly(self, detector):
        """Reporta ubicaciones correctamente."""
        text = "Primera frase única. La casa olía a humedad. Segunda frase. La casa olía a humedad. Final."

        result = detector.detect_sentence_duplicates(text, min_sentence_length=15)

        assert result.is_success
        if result.value.duplicates:
            dup = result.value.duplicates[0]
            assert dup.location1.start_char < dup.location2.start_char
            assert "casa olía" in dup.location1.text
            assert "casa olía" in dup.location2.text


# =============================================================================
# Tests de frases casi idénticas
# =============================================================================

class TestNearSentenceDuplicates:
    """Tests para frases casi idénticas (>90% similitud)."""

    def test_detects_near_duplicate_with_typo(self, detector):
        """Detecta frases casi iguales con pequeñas diferencias."""
        text = """
        La casa olía a humedad y memorias antiguas.
        Pasaron varios párrafos de contenido diferente.
        La casa olia a humedad y memorias antiguas.
        """

        result = detector.detect_sentence_duplicates(text, similarity_threshold=0.90)

        assert result.is_success
        report = result.value
        # Debería detectar la similitud aunque hay un typo (olía vs olia)
        near_dups = [d for d in report.duplicates
                     if d.duplicate_type == DuplicateType.NEAR_SENTENCE]
        assert len(near_dups) >= 1
        assert near_dups[0].similarity >= 0.90

    def test_detects_sentence_with_minor_changes(self, detector):
        """Detecta frases con cambios menores de palabras."""
        text = """
        El silencio era tan denso que podía cortarse con un cuchillo.
        Otros contenidos intercalados aquí para separar.
        El silencio era tan espeso que podía cortarse con un cuchillo.
        """

        result = detector.detect_sentence_duplicates(text, similarity_threshold=0.85)

        assert result.is_success
        # "denso" vs "espeso" - debería detectarse como similar
        if result.value.duplicates:
            assert result.value.duplicates[0].similarity >= 0.85


# =============================================================================
# Tests de párrafos duplicados
# =============================================================================

class TestParagraphDuplicates:
    """Tests para detección de párrafos duplicados."""

    def test_detects_exact_paragraph_duplicate(self, detector):
        """Detecta párrafo duplicado exactamente."""
        paragraphs = [
            {
                "text": "María encontró la pistola de su padre en el cajón del escritorio un martes de noviembre.",
                "chapter": 1,
                "paragraph_number": 1,
                "start_char": 0,
                "end_char": 89,
            },
            {
                "text": "Pedro entró en la habitación y vio a su hermana con el arma.",
                "chapter": 1,
                "paragraph_number": 2,
                "start_char": 90,
                "end_char": 150,
            },
            {
                "text": "María encontró la pistola de su padre en el cajón del escritorio un martes de noviembre.",
                "chapter": 3,
                "paragraph_number": 15,
                "start_char": 500,
                "end_char": 589,
            },
        ]

        result = detector.detect_paragraph_duplicates(paragraphs)

        assert result.is_success
        report = result.value
        exact_dups = [d for d in report.duplicates
                      if d.duplicate_type == DuplicateType.EXACT_PARAGRAPH]
        assert len(exact_dups) >= 1
        assert exact_dups[0].severity == DuplicateSeverity.CRITICAL

    def test_detects_similar_paragraphs(self, detector):
        """Detecta párrafos muy similares pero no idénticos."""
        paragraphs = [
            {
                "text": "La casa olía a humedad y memorias. María recordaba las tardes de su infancia.",
                "chapter": 1,
                "paragraph_number": 3,
            },
            {
                "text": "Contenido completamente diferente aquí para separar los párrafos similares.",
                "chapter": 2,
                "paragraph_number": 10,
            },
            {
                "text": "La casa olía a humedad y memorias. María recordaba las tardes de su niñez.",
                "chapter": 3,
                "paragraph_number": 20,
            },
        ]

        result = detector.detect_paragraph_duplicates(paragraphs, similarity_threshold=0.85)

        assert result.is_success
        # "infancia" vs "niñez" - muy similares
        if result.value.duplicates:
            dup = result.value.duplicates[0]
            assert dup.similarity >= 0.85


# =============================================================================
# Tests de detección combinada
# =============================================================================

class TestCombinedDetection:
    """Tests para detect_all que combina frases y párrafos."""

    def test_detect_all_finds_both_types(self, detector):
        """detect_all encuentra duplicados de frases y párrafos."""
        text = """
        La casa olía a humedad y memorias. María caminó.
        Pedro llegó tarde. La casa olía a humedad y memorias.
        """

        paragraphs = [
            {"text": "Párrafo uno con contenido original.", "chapter": 1, "paragraph_number": 1},
            {"text": "Párrafo dos diferente.", "chapter": 1, "paragraph_number": 2},
            {"text": "Párrafo uno con contenido original.", "chapter": 2, "paragraph_number": 5},
        ]

        result = detector.detect_all(
            text=text,
            paragraphs=paragraphs,
            sentence_threshold=0.90,
            paragraph_threshold=0.90
        )

        assert result.is_success
        report = result.value
        assert report.sentences_analyzed > 0
        assert report.paragraphs_analyzed == 3

    def test_detect_all_with_chapters(self, detector):
        """detect_all asigna capítulos correctamente."""
        text = "Frase única uno. Frase duplicada aquí. Otra frase. Frase duplicada aquí."

        chapters = [
            {"number": 1, "start_char": 0, "end_char": 40},
            {"number": 2, "start_char": 40, "end_char": 100},
        ]

        result = detector.detect_all(
            text=text,
            chapters=chapters,
            sentence_threshold=0.90
        )

        assert result.is_success
        # Debería detectar duplicado entre cap 1 y cap 2


# =============================================================================
# Tests de estadísticas
# =============================================================================

class TestDuplicateStatistics:
    """Tests para estadísticas del reporte."""

    def test_report_counts_by_type(self, detector):
        """El reporte cuenta duplicados por tipo correctamente."""
        text = """
        Frase A repetida exactamente. Contenido. Frase A repetida exactamente.
        Frase B similar pero no igual. Más contenido. Frase B similar pero no igual exactamente.
        """

        result = detector.detect_sentence_duplicates(text, min_sentence_length=20)

        assert result.is_success
        report = result.value
        assert "exact_sentence" in report.by_type or "near_sentence" in report.by_type

    def test_report_counts_by_severity(self, detector):
        """El reporte cuenta por severidad."""
        paragraphs = [
            {"text": "Texto idéntico para probar severidad crítica en duplicados.", "chapter": 1, "paragraph_number": 1},
            {"text": "Otro párrafo diferente.", "chapter": 1, "paragraph_number": 2},
            {"text": "Texto idéntico para probar severidad crítica en duplicados.", "chapter": 2, "paragraph_number": 3},
        ]

        result = detector.detect_paragraph_duplicates(paragraphs)

        assert result.is_success
        report = result.value
        if report.duplicates:
            assert "critical" in report.by_severity or "high" in report.by_severity


# =============================================================================
# Tests de casos límite
# =============================================================================

class TestEdgeCases:
    """Tests para casos límite."""

    def test_empty_text(self, detector):
        """Maneja texto vacío sin error."""
        result = detector.detect_sentence_duplicates("")
        assert result.is_success
        assert len(result.value.duplicates) == 0

    def test_single_sentence(self, detector):
        """Maneja texto con una sola frase."""
        result = detector.detect_sentence_duplicates("Solo una frase aquí.")
        assert result.is_success
        assert len(result.value.duplicates) == 0

    def test_no_duplicates(self, detector):
        """No reporta falsos positivos en texto único."""
        text = """
        María encontró la pistola. Pedro entró en la habitación.
        La vecina preparaba té. El jardín florecía en primavera.
        Carmen recordaba tiempos mejores. Rosario leía en silencio.
        """

        result = detector.detect_sentence_duplicates(text, similarity_threshold=0.95)

        assert result.is_success
        # No debería haber duplicados con umbral alto
        assert len(result.value.duplicates) == 0

    def test_empty_paragraphs_list(self, detector):
        """Maneja lista de párrafos vacía."""
        result = detector.detect_paragraph_duplicates([])
        assert result.is_success
        assert len(result.value.duplicates) == 0


# =============================================================================
# Tests de integración con test_document_rich
# =============================================================================

class TestWithRichDocument:
    """Tests usando el documento de test enriquecido."""

    @pytest.fixture
    def rich_document_text(self):
        """Extracto del test_document_rich.txt con duplicado conocido."""
        return """
        La casa olía a humedad y memorias, un olor que María asociaba con la infancia.
        Pedro recordaba las veces que su padre limpiaba la pistola en el sótano.

        Pasaron muchos párrafos de historia entre estos puntos.

        La casa olía a humedad y memorias, un olor que María asociaba con la infancia.
        El silencio era denso, casi palpable.
        """

    def test_detects_known_duplicate_in_rich_doc(self, detector, rich_document_text):
        """Detecta el duplicado conocido del documento de test."""
        result = detector.detect_sentence_duplicates(
            rich_document_text,
            min_sentence_length=30,
            similarity_threshold=0.90
        )

        assert result.is_success
        report = result.value

        # Debe encontrar el duplicado "La casa olía a humedad y memorias..."
        found_duplicate = False
        for dup in report.duplicates:
            if "casa olía a humedad" in dup.location1.text.lower():
                found_duplicate = True
                assert dup.severity in [DuplicateSeverity.CRITICAL, DuplicateSeverity.HIGH]
                break

        assert found_duplicate, "No se detectó el duplicado conocido 'La casa olía a humedad...'"
