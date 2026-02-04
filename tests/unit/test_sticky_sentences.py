"""Tests para el módulo de detección de oraciones pesadas (Sticky Sentences)."""

import pytest

from narrative_assistant.nlp.style.sticky_sentences import (
    ARTICLES,
    CONJUNCTIONS,
    # Conjuntos de palabras
    GLUE_WORDS,
    PREPOSITIONS,
    PRONOUNS,
    # Tipos
    StickinessSeverity,
    StickyReport,
    StickySentence,
    # Clase principal
    StickySentenceDetector,
    calculate_glue_index,
    get_glue_words,
    # Singleton
    get_sticky_sentence_detector,
    # Utilidades
    is_glue_word,
    reset_sticky_sentence_detector,
)


class TestStickinessSeverity:
    """Tests para StickinessSeverity enum."""

    def test_values(self):
        """Verifica valores del enum."""
        assert StickinessSeverity.CRITICAL.value == "critical"
        assert StickinessSeverity.HIGH.value == "high"
        assert StickinessSeverity.MEDIUM.value == "medium"
        assert StickinessSeverity.LOW.value == "low"


class TestStickySentence:
    """Tests para StickySentence dataclass."""

    def test_create(self):
        """Test creación de oración pegajosa."""
        sentence = StickySentence(
            text="El hecho de que la situación de la empresa se encuentre en un estado de crisis",
            start_char=0,
            end_char=80,
            total_words=16,
            glue_words=10,
            glue_percentage=0.625,
            severity=StickinessSeverity.CRITICAL,
            glue_word_list=["el", "de", "que", "la", "de", "la", "se", "en", "un", "de"],
            content_word_list=["hecho", "situación", "empresa", "encuentre", "estado", "crisis"],
            chapter=1,
        )

        assert sentence.total_words == 16
        assert sentence.glue_words == 10
        assert sentence.glue_percentage == 0.625
        assert sentence.severity == StickinessSeverity.CRITICAL

    def test_glue_percentage_display(self):
        """Test formato de porcentaje."""
        sentence = StickySentence(
            text="Test",
            start_char=0,
            end_char=4,
            total_words=10,
            glue_words=5,
            glue_percentage=0.5,
            severity=StickinessSeverity.HIGH,
        )

        assert sentence.glue_percentage_display == "50.0%"

    def test_recommendation_critical(self):
        """Test recomendación para severidad crítica."""
        sentence = StickySentence(
            text="Test",
            start_char=0,
            end_char=4,
            total_words=10,
            glue_words=7,
            glue_percentage=0.7,
            severity=StickinessSeverity.CRITICAL,
        )

        assert "muy difícil de leer" in sentence.recommendation
        assert "reescribirla" in sentence.recommendation

    def test_recommendation_high(self):
        """Test recomendación para severidad alta."""
        sentence = StickySentence(
            text="Test",
            start_char=0,
            end_char=4,
            total_words=10,
            glue_words=5,
            glue_percentage=0.5,
            severity=StickinessSeverity.HIGH,
        )

        assert "densa" in sentence.recommendation.lower()

    def test_recommendation_medium(self):
        """Test recomendación para severidad media."""
        sentence = StickySentence(
            text="Test",
            start_char=0,
            end_char=4,
            total_words=10,
            glue_words=5,
            glue_percentage=0.47,
            severity=StickinessSeverity.MEDIUM,
        )

        assert "pesada" in sentence.recommendation.lower()

    def test_recommendation_low(self):
        """Test recomendación para severidad baja."""
        sentence = StickySentence(
            text="Test",
            start_char=0,
            end_char=4,
            total_words=10,
            glue_words=4,
            glue_percentage=0.42,
            severity=StickinessSeverity.LOW,
        )

        assert "aceptable" in sentence.recommendation.lower()

    def test_to_dict(self):
        """Test conversión a diccionario."""
        sentence = StickySentence(
            text="La oración de prueba",
            start_char=100,
            end_char=120,
            total_words=4,
            glue_words=2,
            glue_percentage=0.5,
            severity=StickinessSeverity.HIGH,
            glue_word_list=["la", "de"],
            chapter=3,
        )

        d = sentence.to_dict()
        assert d["text"] == "La oración de prueba"
        assert d["start_char"] == 100
        assert d["total_words"] == 4
        assert d["glue_percentage"] == 0.5
        assert d["severity"] == "high"
        assert d["chapter"] == 3

    def test_to_dict_truncates_long_text(self):
        """Test que to_dict trunca textos largos."""
        long_text = "palabra " * 50  # >200 caracteres
        sentence = StickySentence(
            text=long_text,
            start_char=0,
            end_char=len(long_text),
            total_words=50,
            glue_words=25,
            glue_percentage=0.5,
            severity=StickinessSeverity.HIGH,
        )

        d = sentence.to_dict()
        assert len(d["text"]) <= 203  # 200 + "..."
        assert d["text"].endswith("...")


class TestStickyReport:
    """Tests para StickyReport dataclass."""

    def test_create_empty(self):
        """Test creación de reporte vacío."""
        report = StickyReport()

        assert len(report.sticky_sentences) == 0
        assert report.total_sentences == 0
        assert report.total_words == 0
        assert report.stickiness_score == 100.0  # Perfecto si no hay oraciones

    def test_add_sticky(self):
        """Test añadir oración pegajosa."""
        report = StickyReport()

        sentence = StickySentence(
            text="Test",
            start_char=0,
            end_char=4,
            total_words=10,
            glue_words=6,
            glue_percentage=0.6,
            severity=StickinessSeverity.CRITICAL,
        )

        report.add_sticky(sentence)

        assert len(report.sticky_sentences) == 1
        assert report.by_severity.get("critical") == 1

    def test_stickiness_score(self):
        """Test cálculo de puntuación de pegajosidad."""
        report = StickyReport()
        report.total_sentences = 10

        # Sin oraciones pegajosas = puntuación perfecta
        assert report.stickiness_score == 100.0

        # Añadir oraciones con distintas severidades
        critical = StickySentence(
            text="A",
            start_char=0,
            end_char=1,
            total_words=10,
            glue_words=7,
            glue_percentage=0.7,
            severity=StickinessSeverity.CRITICAL,
        )
        report.add_sticky(critical)

        # La puntuación debe bajar
        assert report.stickiness_score < 100.0

    def test_to_dict(self):
        """Test conversión a diccionario."""
        report = StickyReport(
            total_sentences=100,
            total_words=1000,
            total_glue_words=350,
            avg_glue_percentage=0.35,
            clean_sentences=70,
            borderline_sentences=20,
            sticky_sentences_count=10,
        )

        d = report.to_dict()
        assert d["statistics"]["total_sentences"] == 100
        assert d["statistics"]["total_words"] == 1000
        assert d["distribution"]["clean"] == 70
        assert d["distribution"]["sticky"] == 10


class TestGlueWords:
    """Tests para conjuntos de glue words."""

    def test_articles_present(self):
        """Test que artículos españoles están presentes."""
        assert "el" in ARTICLES
        assert "la" in ARTICLES
        assert "los" in ARTICLES
        assert "las" in ARTICLES
        assert "un" in ARTICLES
        assert "una" in ARTICLES

    def test_prepositions_present(self):
        """Test que preposiciones españolas están presentes."""
        assert "de" in PREPOSITIONS
        assert "en" in PREPOSITIONS
        assert "a" in PREPOSITIONS
        assert "por" in PREPOSITIONS
        assert "para" in PREPOSITIONS
        assert "con" in PREPOSITIONS

    def test_conjunctions_present(self):
        """Test que conjunciones españolas están presentes."""
        assert "y" in CONJUNCTIONS
        assert "o" in CONJUNCTIONS
        assert "pero" in CONJUNCTIONS
        assert "que" in CONJUNCTIONS
        assert "si" in CONJUNCTIONS

    def test_pronouns_present(self):
        """Test que pronombres españoles están presentes."""
        assert "se" in PRONOUNS
        assert "lo" in PRONOUNS
        assert "le" in PRONOUNS
        assert "yo" in PRONOUNS
        assert "él" in PRONOUNS

    def test_glue_words_combined(self):
        """Test que GLUE_WORDS contiene todos los conjuntos."""
        assert ARTICLES.issubset(GLUE_WORDS)
        assert PREPOSITIONS.issubset(GLUE_WORDS)
        assert CONJUNCTIONS.issubset(GLUE_WORDS)
        assert PRONOUNS.issubset(GLUE_WORDS)


class TestStickySentenceDetector:
    """Tests para StickySentenceDetector."""

    @pytest.fixture
    def detector(self):
        """Crea detector de oraciones pesadas."""
        reset_sticky_sentence_detector()
        return StickySentenceDetector()

    def test_creation(self, detector):
        """Test creación del detector."""
        assert detector is not None
        assert detector.threshold == 0.40
        assert detector.min_words == 5

    def test_custom_threshold(self):
        """Test con umbral personalizado."""
        detector = StickySentenceDetector(threshold=0.50)
        assert detector.threshold == 0.50

    def test_analyze_empty_text(self, detector):
        """Test análisis de texto vacío."""
        result = detector.analyze("")
        assert result.is_success
        report = result.value
        assert report.total_sentences == 0

    def test_analyze_clean_sentence(self, detector):
        """Test análisis de oración limpia (pocas glue words)."""
        text = "El dragón rojo atacó ferozmente las murallas del castillo medieval."
        result = detector.analyze(text)

        assert result.is_success
        report = result.value
        # Esta oración debería ser bastante limpia (muchas palabras de contenido)
        assert report.total_sentences >= 1

    def test_analyze_sticky_sentence(self, detector):
        """Test análisis de oración pegajosa."""
        # Oración diseñada para ser muy pegajosa
        text = "El hecho de que la situación de la empresa en la que él estaba se encuentre en un estado de crisis."
        result = detector.analyze(text)

        assert result.is_success
        report = result.value

        # Debería detectar la oración como pegajosa
        if report.sticky_sentences:
            assert report.sticky_sentences[0].glue_percentage >= 0.40

    def test_analyze_multiple_sentences(self, detector):
        """Test análisis de múltiples oraciones."""
        text = """
        El sol brillaba intensamente sobre las montañas nevadas.
        Era un día perfecto para escalar.
        Los alpinistas prepararon su equipo cuidadosamente.
        """
        result = detector.analyze(text)

        assert result.is_success
        report = result.value
        assert report.total_sentences >= 3

    def test_analyze_with_chapter(self, detector):
        """Test análisis con número de capítulo."""
        text = "La oración de prueba para el análisis del capítulo."
        result = detector.analyze(text, chapter=5)

        assert result.is_success
        report = result.value
        if report.sticky_sentences:
            assert report.sticky_sentences[0].chapter == 5

    def test_severity_critical(self, detector):
        """Test detección de severidad crítica (>60%)."""
        severity = detector._get_severity(0.65)
        assert severity == StickinessSeverity.CRITICAL

    def test_severity_high(self, detector):
        """Test detección de severidad alta (50-60%)."""
        severity = detector._get_severity(0.55)
        assert severity == StickinessSeverity.HIGH

    def test_severity_medium(self, detector):
        """Test detección de severidad media (45-50%)."""
        severity = detector._get_severity(0.47)
        assert severity == StickinessSeverity.MEDIUM

    def test_severity_low(self, detector):
        """Test detección de severidad baja (40-45%)."""
        severity = detector._get_severity(0.42)
        assert severity == StickinessSeverity.LOW

    def test_tokenize(self, detector):
        """Test tokenización de texto."""
        text = "El gato negro saltó sobre la mesa."
        words = detector._tokenize(text)

        assert "gato" in words
        assert "negro" in words
        assert "saltó" in words
        assert "mesa" in words

    def test_tokenize_handles_accents(self, detector):
        """Test tokenización con acentos."""
        text = "El niño pequeño comió un plátano."
        words = detector._tokenize(text)

        assert "niño" in words
        assert "pequeño" in words
        assert "comió" in words
        assert "plátano" in words

    def test_split_sentences(self, detector):
        """Test división en oraciones."""
        text = "Primera oración. Segunda oración. Tercera oración!"
        sentences = detector._split_sentences(text)

        assert len(sentences) == 3

    def test_split_sentences_question_marks(self, detector):
        """Test división con signos de interrogación."""
        text = "¿Cómo estás? Bien, gracias."
        sentences = detector._split_sentences(text)

        assert len(sentences) >= 2

    def test_glue_category_article(self, detector):
        """Test categoría de artículo."""
        assert detector._get_glue_category("el") == "article"
        assert detector._get_glue_category("la") == "article"

    def test_glue_category_preposition(self, detector):
        """Test categoría de preposición."""
        assert detector._get_glue_category("de") == "preposition"
        assert detector._get_glue_category("en") == "preposition"

    def test_glue_category_conjunction(self, detector):
        """Test categoría de conjunción."""
        assert detector._get_glue_category("y") == "conjunction"
        assert detector._get_glue_category("pero") == "conjunction"

    def test_glue_category_pronoun(self, detector):
        """Test categoría de pronombre."""
        assert detector._get_glue_category("se") == "pronoun"
        assert detector._get_glue_category("lo") == "pronoun"

    def test_get_sentence_analysis(self, detector):
        """Test análisis detallado de oración."""
        sentence = "El gato está en la mesa."
        analysis = detector.get_sentence_analysis(sentence)

        assert analysis["total_words"] == 6
        assert analysis["glue_words"] >= 4  # el, está, en, la
        assert isinstance(analysis["words"], list)
        assert len(analysis["words"]) == 6

    def test_get_sentence_analysis_word_details(self, detector):
        """Test detalles de palabras en análisis."""
        sentence = "El gato negro."
        analysis = detector.get_sentence_analysis(sentence)

        # Buscar la palabra "el" - debe ser glue
        el_word = next((w for w in analysis["words"] if w["word"].lower() == "el"), None)
        assert el_word is not None
        assert el_word["is_glue"] is True

        # Buscar "gato" - no debe ser glue
        gato_word = next((w for w in analysis["words"] if w["word"].lower() == "gato"), None)
        assert gato_word is not None
        assert gato_word["is_glue"] is False

    def test_analyze_by_chapter(self, detector):
        """Test análisis por capítulo."""
        chapters = [
            (1, "El primer capítulo tiene oraciones interesantes."),
            (2, "El segundo capítulo continúa la historia."),
        ]

        results = detector.analyze_by_chapter(chapters)

        assert 1 in results
        assert 2 in results
        assert isinstance(results[1], StickyReport)

    def test_generate_recommendations_many_sticky(self, detector):
        """Test generación de recomendaciones con muchas oraciones pegajosas."""
        report = StickyReport(total_sentences=10)

        # Añadir 4 oraciones pegajosas (40%)
        for i in range(4):
            report.add_sticky(
                StickySentence(
                    text=f"Test {i}",
                    start_char=0,
                    end_char=10,
                    total_words=10,
                    glue_words=5,
                    glue_percentage=0.5,
                    severity=StickinessSeverity.HIGH,
                )
            )

        recommendations = detector._generate_recommendations(report)
        assert len(recommendations) > 0

    def test_generate_recommendations_critical(self, detector):
        """Test recomendaciones con severidad crítica."""
        report = StickyReport(total_sentences=10)

        report.add_sticky(
            StickySentence(
                text="Test",
                start_char=0,
                end_char=4,
                total_words=10,
                glue_words=7,
                glue_percentage=0.7,
                severity=StickinessSeverity.CRITICAL,
            )
        )

        recommendations = detector._generate_recommendations(report)
        assert any("crítica" in r.lower() for r in recommendations)


class TestSingleton:
    """Tests para el singleton del detector."""

    def test_get_singleton(self):
        """Test obtención del singleton."""
        reset_sticky_sentence_detector()
        detector1 = get_sticky_sentence_detector()
        detector2 = get_sticky_sentence_detector()

        assert detector1 is detector2

    def test_reset_singleton(self):
        """Test reseteo del singleton."""
        reset_sticky_sentence_detector()
        detector1 = get_sticky_sentence_detector()

        reset_sticky_sentence_detector()
        detector2 = get_sticky_sentence_detector()

        assert detector1 is not detector2


class TestUtilityFunctions:
    """Tests para funciones de utilidad."""

    def test_is_glue_word_true(self):
        """Test identificación de glue words."""
        assert is_glue_word("el") is True
        assert is_glue_word("de") is True
        assert is_glue_word("que") is True
        assert is_glue_word("se") is True

    def test_is_glue_word_false(self):
        """Test identificación de palabras de contenido."""
        assert is_glue_word("gato") is False
        assert is_glue_word("caminar") is False
        assert is_glue_word("hermoso") is False
        assert is_glue_word("rápidamente") is False

    def test_is_glue_word_case_insensitive(self):
        """Test que la función es insensible a mayúsculas."""
        assert is_glue_word("EL") is True
        assert is_glue_word("De") is True
        assert is_glue_word("QUE") is True

    def test_get_glue_words_returns_copy(self):
        """Test que get_glue_words retorna una copia."""
        words1 = get_glue_words()
        words2 = get_glue_words()

        assert words1 == words2
        assert words1 is not words2  # Son copias distintas

    def test_calculate_glue_index_empty(self):
        """Test índice de pegajosidad con texto vacío."""
        index = calculate_glue_index("")
        assert index == 0.0

    def test_calculate_glue_index_all_glue(self):
        """Test índice con solo glue words."""
        text = "el de la que en"
        index = calculate_glue_index(text)
        assert index == 1.0  # 100% glue words

    def test_calculate_glue_index_no_glue(self):
        """Test índice sin glue words."""
        text = "gato perro casa árbol"
        index = calculate_glue_index(text)
        assert index == 0.0  # 0% glue words

    def test_calculate_glue_index_mixed(self):
        """Test índice con mezcla de palabras."""
        text = "el gato negro"  # 1 glue (el) de 3 palabras
        index = calculate_glue_index(text)
        assert 0.3 <= index <= 0.4  # ~33%


class TestIntegration:
    """Tests de integración."""

    @pytest.fixture
    def detector(self):
        """Crea detector."""
        reset_sticky_sentence_detector()
        return StickySentenceDetector()

    def test_realistic_text_analysis(self, detector):
        """Test con texto realista."""
        text = """
        El viejo marinero observaba el horizonte con melancolía.
        Las olas rompían contra el casco del barco con fuerza implacable.
        Había navegado durante treinta años por estos mares.
        Conocía cada corriente, cada estrella del cielo nocturno.
        """

        result = detector.analyze(text)

        assert result.is_success
        report = result.value
        assert report.total_sentences >= 4
        assert report.total_words > 30
        assert 0 <= report.avg_glue_percentage <= 1

    def test_very_sticky_paragraph(self, detector):
        """Test con párrafo muy pegajoso."""
        # Texto diseñado para ser extremadamente pegajoso
        text = """
        En el caso de que la situación de la empresa se encuentre
        en un estado en el que los recursos de los que dispone
        sean insuficientes para el cumplimiento de las obligaciones
        que tiene con los proveedores a los que debe dinero.
        """

        result = detector.analyze(text)

        assert result.is_success
        report = result.value

        # Debería detectar oraciones pegajosas
        assert len(report.sticky_sentences) >= 1 or report.avg_glue_percentage > 0.4

    def test_clean_paragraph(self, detector):
        """Test con párrafo limpio."""
        # Texto con muchas palabras de contenido
        text = """
        Dragones escarlatas volaban majestuosamente.
        Guerreros valientes defendían murallas ancestrales.
        Magos poderosos conjuraban hechizos devastadores.
        """

        result = detector.analyze(text)

        assert result.is_success
        report = result.value

        # Debería tener pocas o ninguna oración pegajosa
        critical_count = report.by_severity.get("critical", 0)
        assert critical_count == 0
