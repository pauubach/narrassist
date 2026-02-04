"""Tests para el módulo de análisis de legibilidad."""

import pytest

from narrative_assistant.nlp.style.readability import (
    AGE_GROUP_THRESHOLDS,
    INFLESZ_SCALE,
    # Constantes
    SPANISH_SIGHT_WORDS,
    AgeGroup,
    AgeReadabilityReport,
    # Clase principal
    ReadabilityAnalyzer,
    # Tipos
    ReadabilityLevel,
    ReadabilityReport,
    SentenceStats,
    # Utilidades
    count_syllables_spanish,
    count_syllables_text,
    # Singleton
    get_readability_analyzer,
    get_readability_level,
    reset_readability_analyzer,
)


class TestReadabilityLevel:
    """Tests para ReadabilityLevel enum."""

    def test_values(self):
        """Verifica valores del enum."""
        assert ReadabilityLevel.VERY_EASY.value == "very_easy"
        assert ReadabilityLevel.EASY.value == "easy"
        assert ReadabilityLevel.NORMAL.value == "normal"
        assert ReadabilityLevel.DIFFICULT.value == "difficult"
        assert ReadabilityLevel.VERY_DIFFICULT.value == "very_difficult"


class TestAgeGroup:
    """Tests para AgeGroup enum."""

    def test_values(self):
        """Verifica valores del enum."""
        assert AgeGroup.BOARD_BOOK.value == "board_book"
        assert AgeGroup.PICTURE_BOOK.value == "picture_book"
        assert AgeGroup.EARLY_READER.value == "early_reader"
        assert AgeGroup.CHAPTER_BOOK.value == "chapter_book"
        assert AgeGroup.MIDDLE_GRADE.value == "middle_grade"
        assert AgeGroup.YOUNG_ADULT.value == "young_adult"
        assert AgeGroup.ADULT.value == "adult"


class TestSyllableCount:
    """Tests para conteo de sílabas en español."""

    def test_count_syllables_simple(self):
        """Test conteo de sílabas en palabras simples."""
        assert count_syllables_spanish("casa") == 2
        assert count_syllables_spanish("sol") == 1
        assert count_syllables_spanish("perro") == 2
        assert count_syllables_spanish("gato") == 2

    def test_count_syllables_long(self):
        """Test conteo en palabras largas."""
        assert count_syllables_spanish("extraordinario") == 6
        assert count_syllables_spanish("computadora") == 5
        assert count_syllables_spanish("universidad") == 5

    def test_count_syllables_diphthong(self):
        """Test conteo con diptongos (una sílaba)."""
        assert count_syllables_spanish("bueno") == 2  # bue-no
        assert count_syllables_spanish("tiene") == 2  # tie-ne
        assert count_syllables_spanish("puerta") == 2  # puer-ta

    def test_count_syllables_hiatus(self):
        """Test conteo con hiatos (dos sílabas)."""
        assert count_syllables_spanish("caer") == 2  # ca-er
        assert count_syllables_spanish("leer") == 2  # le-er
        assert count_syllables_spanish("poeta") == 3  # po-e-ta

    def test_count_syllables_accents(self):
        """Test conteo con acentos."""
        assert count_syllables_spanish("árbol") == 2
        assert count_syllables_spanish("música") == 3
        assert count_syllables_spanish("teléfono") == 4

    def test_count_syllables_minimum(self):
        """Test que siempre devuelve al menos 1."""
        assert count_syllables_spanish("a") == 1
        assert count_syllables_spanish("y") == 1

    def test_count_syllables_empty(self):
        """Test con palabra vacía."""
        assert count_syllables_spanish("") == 0
        assert count_syllables_spanish("   ") == 0

    def test_count_syllables_text(self):
        """Test conteo en texto completo."""
        text = "El gato negro"
        syllables, words = count_syllables_text(text)

        assert words == 3
        assert syllables >= 4  # el=1, ga-to=2, ne-gro=2


class TestReadabilityReport:
    """Tests para ReadabilityReport dataclass."""

    def test_create_empty(self):
        """Test creación de reporte vacío."""
        report = ReadabilityReport()

        assert report.flesch_szigriszt == 0.0
        assert report.total_words == 0
        assert report.level == ReadabilityLevel.NORMAL

    def test_to_dict(self):
        """Test conversión a diccionario."""
        report = ReadabilityReport(
            flesch_szigriszt=65.5,
            fernandez_huerta=62.3,
            level=ReadabilityLevel.EASY,
            level_description="Lectura fácil",
            total_words=500,
            total_sentences=25,
            avg_words_per_sentence=20.0,
        )

        d = report.to_dict()
        assert d["flesch_szigriszt"] == 65.5
        assert d["level"] == "easy"
        assert d["statistics"]["total_words"] == 500
        assert d["averages"]["avg_words_per_sentence"] == 20.0


class TestAgeReadabilityReport:
    """Tests para AgeReadabilityReport dataclass."""

    def test_create(self):
        """Test creación de reporte de edad."""
        report = AgeReadabilityReport(
            estimated_age_group=AgeGroup.EARLY_READER,
            estimated_age_range="5-8 años",
            estimated_grade_level="1º-2º Primaria",
            flesch_szigriszt=75.0,
            total_words=200,
            sight_word_ratio=0.45,
        )

        assert report.estimated_age_group == AgeGroup.EARLY_READER
        assert report.estimated_age_range == "5-8 años"
        assert report.sight_word_ratio == 0.45

    def test_to_dict(self):
        """Test conversión a diccionario."""
        report = AgeReadabilityReport(
            estimated_age_group=AgeGroup.PICTURE_BOOK,
            estimated_age_range="3-5 años",
            total_words=150,
            sight_word_count=80,
            sight_word_ratio=0.53,
            unique_words=50,
            vocabulary_diversity=0.33,
            simple_words_ratio=0.8,
            complex_words_ratio=0.05,
            repetition_score=45.0,
            is_appropriate=True,
            appropriateness_score=95.0,
        )

        d = report.to_dict()
        assert d["estimated_age_group"] == "picture_book"
        assert d["vocabulary"]["sight_word_ratio"] == 0.53
        assert d["vocabulary"]["simple_words_ratio"] == 0.8
        assert d["evaluation"]["is_appropriate"] is True


class TestReadabilityLevel:
    """Tests para get_readability_level."""

    def test_very_easy(self):
        """Test nivel muy fácil (>80)."""
        level, name, desc = get_readability_level(85)
        assert level == ReadabilityLevel.VERY_EASY
        assert "fácil" in name.lower()

    def test_easy(self):
        """Test nivel fácil (66-80)."""
        level, name, desc = get_readability_level(70)
        assert level == ReadabilityLevel.EASY

    def test_fairly_easy(self):
        """Test nivel algo fácil (56-65)."""
        level, name, desc = get_readability_level(60)
        assert level == ReadabilityLevel.FAIRLY_EASY

    def test_normal(self):
        """Test nivel normal (40-55)."""
        level, name, desc = get_readability_level(50)
        assert level == ReadabilityLevel.NORMAL

    def test_fairly_difficult(self):
        """Test nivel algo difícil (26-39)."""
        level, name, desc = get_readability_level(30)
        assert level == ReadabilityLevel.FAIRLY_DIFFICULT

    def test_difficult(self):
        """Test nivel difícil (11-25)."""
        level, name, desc = get_readability_level(20)
        assert level == ReadabilityLevel.DIFFICULT

    def test_very_difficult(self):
        """Test nivel muy difícil (0-10)."""
        level, name, desc = get_readability_level(5)
        assert level == ReadabilityLevel.VERY_DIFFICULT


class TestSpanishSightWords:
    """Tests para palabras de alta frecuencia."""

    def test_articles_present(self):
        """Test que artículos están incluidos."""
        assert "el" in SPANISH_SIGHT_WORDS
        assert "la" in SPANISH_SIGHT_WORDS
        assert "los" in SPANISH_SIGHT_WORDS
        assert "un" in SPANISH_SIGHT_WORDS

    def test_basic_verbs_present(self):
        """Test que verbos básicos están incluidos."""
        assert "es" in SPANISH_SIGHT_WORDS
        assert "tiene" in SPANISH_SIGHT_WORDS
        assert "va" in SPANISH_SIGHT_WORDS
        assert "come" in SPANISH_SIGHT_WORDS

    def test_pronouns_present(self):
        """Test que pronombres están incluidos."""
        assert "yo" in SPANISH_SIGHT_WORDS
        assert "tú" in SPANISH_SIGHT_WORDS
        assert "él" in SPANISH_SIGHT_WORDS
        assert "ella" in SPANISH_SIGHT_WORDS

    def test_numbers_present(self):
        """Test que números están incluidos."""
        assert "uno" in SPANISH_SIGHT_WORDS
        assert "dos" in SPANISH_SIGHT_WORDS
        assert "tres" in SPANISH_SIGHT_WORDS

    def test_colors_present(self):
        """Test que colores están incluidos."""
        assert "rojo" in SPANISH_SIGHT_WORDS
        assert "azul" in SPANISH_SIGHT_WORDS
        assert "verde" in SPANISH_SIGHT_WORDS


class TestAgeGroupThresholds:
    """Tests para umbrales de grupos de edad."""

    def test_board_book_thresholds(self):
        """Test umbrales para libros de cartón (0-3 años)."""
        thresholds = AGE_GROUP_THRESHOLDS[AgeGroup.BOARD_BOOK]

        assert thresholds["max_words"] == 300
        assert thresholds["max_words_per_sentence"] == 5
        assert thresholds["min_sight_word_ratio"] == 0.7
        assert "0-3" in thresholds["age_range"]

    def test_picture_book_thresholds(self):
        """Test umbrales para libros ilustrados (3-5 años)."""
        thresholds = AGE_GROUP_THRESHOLDS[AgeGroup.PICTURE_BOOK]

        assert thresholds["max_words"] == 1000
        assert thresholds["max_words_per_sentence"] == 8
        assert "3-5" in thresholds["age_range"]

    def test_early_reader_thresholds(self):
        """Test umbrales para primeros lectores (5-8 años)."""
        thresholds = AGE_GROUP_THRESHOLDS[AgeGroup.EARLY_READER]

        assert thresholds["max_words"] == 5000
        assert thresholds["max_words_per_sentence"] == 12
        assert "5-8" in thresholds["age_range"]

    def test_thresholds_progression(self):
        """Test que los umbrales progresan correctamente."""
        # max_words debe aumentar con la edad
        prev_words = 0
        for age_group in [
            AgeGroup.BOARD_BOOK,
            AgeGroup.PICTURE_BOOK,
            AgeGroup.EARLY_READER,
            AgeGroup.CHAPTER_BOOK,
            AgeGroup.MIDDLE_GRADE,
            AgeGroup.YOUNG_ADULT,
        ]:
            thresholds = AGE_GROUP_THRESHOLDS[age_group]
            assert thresholds["max_words"] > prev_words
            prev_words = thresholds["max_words"]


class TestReadabilityAnalyzer:
    """Tests para ReadabilityAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Crea analizador de legibilidad."""
        reset_readability_analyzer()
        return ReadabilityAnalyzer()

    def test_creation(self, analyzer):
        """Test creación del analizador."""
        assert analyzer is not None

    def test_analyze_empty(self, analyzer):
        """Test análisis de texto vacío."""
        result = analyzer.analyze("")
        assert result.is_success
        report = result.value
        assert report.total_words == 0

    def test_analyze_simple_text(self, analyzer):
        """Test análisis de texto simple."""
        text = "El sol brilla. La luna sale."
        result = analyzer.analyze(text)

        assert result.is_success
        report = result.value
        assert report.total_sentences == 2
        assert report.total_words > 0
        assert 0 <= report.flesch_szigriszt <= 100

    def test_analyze_easy_text(self, analyzer):
        """Test texto fácil de leer."""
        # Texto con oraciones cortas y palabras simples
        text = """
        El gato come. El perro corre.
        La niña juega. El sol brilla.
        """
        result = analyzer.analyze(text)

        assert result.is_success
        report = result.value
        # Texto simple debería tener alto flesch score
        assert report.flesch_szigriszt > 60

    def test_analyze_complex_text(self, analyzer):
        """Test texto complejo."""
        # Texto con oraciones largas y vocabulario complejo
        text = """
        La implementación de estrategias metodológicas interdisciplinarias
        constituye un desafío significativo para las instituciones educativas
        contemporáneas, particularmente cuando estas deben considerar
        las características socioeconómicas y culturales de la población estudiantil.
        """
        result = analyzer.analyze(text)

        assert result.is_success
        report = result.value
        # Texto complejo debería tener bajo flesch score
        assert report.flesch_szigriszt < 50

    def test_analyze_sentence_distribution(self, analyzer):
        """Test distribución de longitud de oraciones."""
        text = """
        Sí. Ok. Bien.
        Esta es una oración de longitud media para el análisis.
        Esta oración es mucho más larga porque necesitamos probar cómo el analizador
        clasifica las oraciones según su longitud en palabras y determinar si las
        métricas funcionan correctamente.
        """
        result = analyzer.analyze(text)

        assert result.is_success
        report = result.value
        assert report.short_sentences > 0
        assert report.medium_sentences >= 0

    def test_analyze_generates_recommendations(self, analyzer):
        """Test que genera recomendaciones cuando corresponde."""
        # Texto muy complejo
        text = """
        La conceptualización epistemológica de las representaciones
        fenomenológicas intersubjetivas constituye una problemática
        metodológica fundamental en el análisis contemporáneo de las
        estructuras cognitivas multidimensionales.
        """
        result = analyzer.analyze(text)

        assert result.is_success
        report = result.value
        # Texto tan complejo debería generar recomendaciones
        assert len(report.recommendations) > 0 or report.flesch_szigriszt < 40

    def test_analyze_fernandez_huerta(self, analyzer):
        """Test cálculo de índice Fernández-Huerta."""
        text = "El sol brilla en el cielo azul. Los pájaros cantan alegremente."
        result = analyzer.analyze(text)

        assert result.is_success
        report = result.value
        assert 0 <= report.fernandez_huerta <= 100

    def test_analyze_by_chapter(self, analyzer):
        """Test análisis por capítulo."""
        chapters = [
            ("Capítulo 1", "El gato duerme en la cama."),
            ("Capítulo 2", "El perro corre en el parque."),
        ]

        results = analyzer.analyze_by_chapter(chapters)

        assert "Capítulo 1" in results
        assert "Capítulo 2" in results
        assert isinstance(results["Capítulo 1"], ReadabilityReport)


class TestAgeReadabilityAnalysis:
    """Tests para análisis de legibilidad por edad."""

    @pytest.fixture
    def analyzer(self):
        """Crea analizador."""
        reset_readability_analyzer()
        return ReadabilityAnalyzer()

    def test_analyze_for_age_empty(self, analyzer):
        """Test análisis de edad con texto vacío."""
        result = analyzer.analyze_for_age("")
        assert result.is_success
        report = result.value
        assert report.total_words == 0

    def test_analyze_for_age_simple_text(self, analyzer):
        """Test análisis de edad con texto simple para niños."""
        # Texto típico de libro infantil
        text = """
        El gato es grande. El gato es rojo.
        El gato come. El gato duerme.
        El gato juega. El gato salta.
        """
        result = analyzer.analyze_for_age(text)

        assert result.is_success
        report = result.value
        assert report.total_words > 0
        assert report.sight_word_ratio > 0  # Debería tener muchas sight words

    def test_analyze_for_age_sight_words(self, analyzer):
        """Test detección de sight words."""
        # Texto con muchas sight words
        text = "El niño tiene un perro. La niña tiene un gato. Ellos son amigos."
        result = analyzer.analyze_for_age(text)

        assert result.is_success
        report = result.value
        assert report.sight_word_count > 5
        assert report.sight_word_ratio > 0.3

    def test_analyze_for_age_vocabulary_diversity(self, analyzer):
        """Test cálculo de diversidad de vocabulario."""
        # Texto con mucha repetición (baja diversidad)
        text = "El gato. El gato. El gato. El gato corre. El gato salta."
        result = analyzer.analyze_for_age(text)

        assert result.is_success
        report = result.value
        assert 0 <= report.vocabulary_diversity <= 1
        assert report.repetition_score > 0  # Debería detectar repetición

    def test_analyze_for_age_with_target(self, analyzer):
        """Test análisis con grupo de edad objetivo."""
        # Texto simple para niños
        text = """
        El sol brilla. El gato duerme.
        La niña juega. El perro corre.
        """
        result = analyzer.analyze_for_age(text, target_age_group=AgeGroup.PICTURE_BOOK)

        assert result.is_success
        report = result.value
        assert report.target_age_group == AgeGroup.PICTURE_BOOK
        assert "target_comparison" in report.to_dict()

    def test_analyze_for_age_complex_inappropriate(self, analyzer):
        """Test texto complejo inapropiado para niños pequeños."""
        # Texto muy complejo
        text = """
        La implementación de metodologías pedagógicas interdisciplinarias
        requiere una comprensión profunda de los paradigmas epistemológicos
        contemporáneos y su aplicación en contextos educativos diversos.
        """
        result = analyzer.analyze_for_age(
            text,
            target_age_group=AgeGroup.PICTURE_BOOK,  # 3-5 años
        )

        assert result.is_success
        report = result.value
        # Debería detectar problemas de adecuación
        assert report.appropriateness_score < 100
        assert len(report.issues) > 0 or not report.is_appropriate

    def test_analyze_for_age_estimates_age_group(self, analyzer):
        """Test estimación de grupo de edad."""
        # Texto muy simple
        text = "El sol. La luna. El gato. El perro."
        result = analyzer.analyze_for_age(text)

        assert result.is_success
        report = result.value
        # Debería estimar para niños pequeños
        assert report.estimated_age_group in [
            AgeGroup.BOARD_BOOK,
            AgeGroup.PICTURE_BOOK,
            AgeGroup.EARLY_READER,
        ]

    def test_analyze_for_age_complex_words_ratio(self, analyzer):
        """Test cálculo de ratio de palabras complejas."""
        # Texto con palabras complejas (4+ sílabas)
        text = "El extraordinario computador analiza información automáticamente."
        result = analyzer.analyze_for_age(text)

        assert result.is_success
        report = result.value
        assert report.complex_words_ratio > 0
        assert report.simple_words_ratio < 1

    def test_analyze_for_age_most_repeated(self, analyzer):
        """Test detección de palabras más repetidas."""
        text = """
        El gato salta. El gato corre. El gato duerme.
        El perro salta. El perro corre. El perro duerme.
        """
        result = analyzer.analyze_for_age(text)

        assert result.is_success
        report = result.value
        assert len(report.most_repeated_words) > 0
        # Las palabras más repetidas deberían incluir "gato" o "perro"


class TestSingleton:
    """Tests para el singleton del analizador."""

    def test_get_singleton(self):
        """Test obtención del singleton."""
        reset_readability_analyzer()
        analyzer1 = get_readability_analyzer()
        analyzer2 = get_readability_analyzer()

        assert analyzer1 is analyzer2

    def test_reset_singleton(self):
        """Test reseteo del singleton."""
        reset_readability_analyzer()
        analyzer1 = get_readability_analyzer()

        reset_readability_analyzer()
        analyzer2 = get_readability_analyzer()

        assert analyzer1 is not analyzer2


class TestIntegration:
    """Tests de integración."""

    @pytest.fixture
    def analyzer(self):
        """Crea analizador."""
        reset_readability_analyzer()
        return ReadabilityAnalyzer()

    def test_realistic_children_book(self, analyzer):
        """Test con texto realista de libro infantil."""
        text = """
        Había una vez un pequeño oso llamado Beto.
        Beto vivía en el bosque con su mamá y su papá.
        Un día, Beto salió a pasear.
        Vio un río grande y azul.
        ¡Qué bonito! -dijo Beto.
        Beto jugó todo el día.
        Al final, volvió a casa feliz.
        """
        result = analyzer.analyze_for_age(text)

        assert result.is_success
        report = result.value
        assert report.total_words > 30
        # Texto muy simple puede clasificarse para niños muy pequeños
        assert report.estimated_age_group in [
            AgeGroup.BOARD_BOOK,
            AgeGroup.PICTURE_BOOK,
            AgeGroup.EARLY_READER,
            AgeGroup.CHAPTER_BOOK,
        ]

    def test_realistic_adult_text(self, analyzer):
        """Test con texto realista para adultos."""
        text = """
        El desarrollo sostenible constituye uno de los principales desafíos
        de las sociedades contemporáneas. La interacción entre factores
        económicos, ambientales y sociales genera dinámicas complejas que
        requieren aproximaciones interdisciplinarias. Los investigadores
        deben considerar múltiples variables para comprender estos fenómenos.
        """
        result = analyzer.analyze(text)

        assert result.is_success
        report = result.value
        # Texto académico puede clasificarse como muy difícil
        assert report.level in [
            ReadabilityLevel.FAIRLY_DIFFICULT,
            ReadabilityLevel.DIFFICULT,
            ReadabilityLevel.VERY_DIFFICULT,
            ReadabilityLevel.NORMAL,
        ]

    def test_compare_simple_vs_complex(self, analyzer):
        """Test comparación entre texto simple y complejo."""
        simple = "El sol brilla. El perro corre. La niña juega."
        complex_text = """
        Las manifestaciones fenotípicas de las alteraciones genómicas
        requieren análisis multidimensionales especializados.
        """

        simple_result = analyzer.analyze(simple)
        complex_result = analyzer.analyze(complex_text)

        assert simple_result.is_success
        assert complex_result.is_success

        # El texto simple debe ser más fácil de leer
        assert simple_result.value.flesch_szigriszt > complex_result.value.flesch_szigriszt
