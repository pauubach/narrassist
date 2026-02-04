"""
Tests para el módulo de análisis de ritmo narrativo (pacing).
"""

import pytest

from narrative_assistant.analysis.pacing import (
    ACTION_VERBS,
    PacingAnalysisResult,
    PacingAnalyzer,
    PacingIssue,
    PacingIssueType,
    PacingMetrics,
    PacingSeverity,
    analyze_pacing,
    get_pacing_analyzer,
)

# =============================================================================
# Tests de Enums
# =============================================================================


class TestPacingIssueType:
    """Tests para PacingIssueType enum."""

    def test_all_issue_types_defined(self):
        """Verifica que todos los tipos de problema están definidos."""
        expected_types = [
            "CHAPTER_TOO_SHORT",
            "CHAPTER_TOO_LONG",
            "UNBALANCED_CHAPTERS",
            "TOO_MUCH_DIALOGUE",
            "TOO_LITTLE_DIALOGUE",
            "DENSE_TEXT_BLOCK",
            "SPARSE_TEXT_BLOCK",
            "RHYTHM_SHIFT",
            "SCENE_TOO_SHORT",
            "SCENE_TOO_LONG",
        ]
        for type_name in expected_types:
            assert hasattr(PacingIssueType, type_name)

    def test_issue_type_values(self):
        """Verifica valores de los tipos de problema."""
        assert PacingIssueType.CHAPTER_TOO_SHORT.value == "chapter_too_short"
        assert PacingIssueType.TOO_MUCH_DIALOGUE.value == "too_much_dialogue"
        assert PacingIssueType.DENSE_TEXT_BLOCK.value == "dense_text_block"


class TestPacingSeverity:
    """Tests para PacingSeverity enum."""

    def test_all_severities_defined(self):
        """Verifica que todos los niveles de severidad están definidos."""
        expected = ["INFO", "SUGGESTION", "WARNING", "ISSUE"]
        for sev in expected:
            assert hasattr(PacingSeverity, sev)

    def test_severity_values(self):
        """Verifica valores de severidad."""
        assert PacingSeverity.INFO.value == "info"
        assert PacingSeverity.SUGGESTION.value == "suggestion"
        assert PacingSeverity.WARNING.value == "warning"
        assert PacingSeverity.ISSUE.value == "issue"


# =============================================================================
# Tests de Dataclasses
# =============================================================================


class TestPacingMetrics:
    """Tests para PacingMetrics dataclass."""

    def test_default_values(self):
        """Verifica valores por defecto."""
        metrics = PacingMetrics(segment_id=1, segment_type="chapter")
        assert metrics.segment_id == 1
        assert metrics.segment_type == "chapter"
        assert metrics.title is None
        assert metrics.word_count == 0
        assert metrics.char_count == 0
        assert metrics.sentence_count == 0
        assert metrics.paragraph_count == 0
        assert metrics.dialogue_lines == 0
        assert metrics.dialogue_words == 0
        assert metrics.dialogue_ratio == 0.0
        assert metrics.avg_sentence_length == 0.0
        assert metrics.avg_paragraph_length == 0.0
        assert metrics.lexical_density == 0.0
        assert metrics.action_verb_ratio == 0.0

    def test_with_values(self):
        """Verifica creación con valores."""
        metrics = PacingMetrics(
            segment_id=2,
            segment_type="chapter",
            title="Capítulo 2",
            word_count=1500,
            sentence_count=75,
            dialogue_ratio=0.35,
        )
        assert metrics.segment_id == 2
        assert metrics.title == "Capítulo 2"
        assert metrics.word_count == 1500
        assert metrics.dialogue_ratio == 0.35

    def test_to_dict(self):
        """Verifica serialización a diccionario."""
        metrics = PacingMetrics(
            segment_id=1,
            segment_type="chapter",
            title="Test",
            word_count=100,
            dialogue_ratio=0.333333,
            lexical_density=0.666666,
        )
        d = metrics.to_dict()
        assert d["segment_id"] == 1
        assert d["segment_type"] == "chapter"
        assert d["title"] == "Test"
        assert d["word_count"] == 100
        # Verifica redondeo
        assert d["dialogue_ratio"] == 0.333
        assert d["lexical_density"] == 0.667


class TestPacingIssue:
    """Tests para PacingIssue dataclass."""

    def test_default_values(self):
        """Verifica valores por defecto."""
        issue = PacingIssue(
            issue_type=PacingIssueType.CHAPTER_TOO_SHORT,
            severity=PacingSeverity.WARNING,
            segment_id=1,
            segment_type="chapter",
        )
        assert issue.issue_type == PacingIssueType.CHAPTER_TOO_SHORT
        assert issue.severity == PacingSeverity.WARNING
        assert issue.title is None
        assert issue.description == ""
        assert issue.explanation == ""
        assert issue.suggestion == ""
        assert issue.actual_value == 0.0
        assert issue.expected_range == (0.0, 0.0)
        assert issue.comparison_value is None

    def test_with_full_values(self):
        """Verifica creación con todos los valores."""
        issue = PacingIssue(
            issue_type=PacingIssueType.CHAPTER_TOO_LONG,
            severity=PacingSeverity.SUGGESTION,
            segment_id=5,
            segment_type="chapter",
            title="El descenlace",
            description="Capítulo 5 tiene 12000 palabras",
            explanation="Muy largo para mantener atención",
            suggestion="Considere dividir el capítulo",
            actual_value=12000,
            expected_range=(500, 10000),
            comparison_value=3000,
        )
        assert issue.title == "El descenlace"
        assert issue.actual_value == 12000
        assert issue.expected_range == (500, 10000)
        assert issue.comparison_value == 3000

    def test_to_dict(self):
        """Verifica serialización a diccionario."""
        issue = PacingIssue(
            issue_type=PacingIssueType.TOO_LITTLE_DIALOGUE,
            severity=PacingSeverity.INFO,
            segment_id=3,
            segment_type="chapter",
            actual_value=0.05,
            comparison_value=0.333,
        )
        d = issue.to_dict()
        assert d["issue_type"] == "too_little_dialogue"
        assert d["severity"] == "info"
        assert d["segment_id"] == 3
        assert d["actual_value"] == 0.05
        assert d["comparison_value"] == 0.33  # Redondeado


class TestPacingAnalysisResult:
    """Tests para PacingAnalysisResult dataclass."""

    def test_default_values(self):
        """Verifica valores por defecto."""
        result = PacingAnalysisResult()
        assert result.document_metrics == {}
        assert result.chapter_metrics == []
        assert result.issues == []
        assert result.summary == {}

    def test_to_dict(self):
        """Verifica serialización a diccionario."""
        metrics = PacingMetrics(segment_id=1, segment_type="chapter", word_count=100)
        issue = PacingIssue(
            issue_type=PacingIssueType.CHAPTER_TOO_SHORT,
            severity=PacingSeverity.WARNING,
            segment_id=1,
            segment_type="chapter",
        )
        result = PacingAnalysisResult(
            document_metrics={"total_words": 100},
            chapter_metrics=[metrics],
            issues=[issue],
            summary={"total_chapters": 1},
        )
        d = result.to_dict()
        assert d["document_metrics"]["total_words"] == 100
        assert len(d["chapter_metrics"]) == 1
        assert d["chapter_metrics"][0]["word_count"] == 100
        assert len(d["issues"]) == 1
        assert d["issues"][0]["issue_type"] == "chapter_too_short"
        assert d["summary"]["total_chapters"] == 1


# =============================================================================
# Tests de PacingAnalyzer
# =============================================================================


class TestPacingAnalyzerInit:
    """Tests para inicialización del analizador."""

    def test_default_thresholds(self):
        """Verifica umbrales por defecto."""
        analyzer = PacingAnalyzer()
        assert analyzer.min_chapter_words == 500
        assert analyzer.max_chapter_words == 10000
        assert analyzer.dialogue_ratio_range == (0.15, 0.60)
        assert analyzer.chapter_variance_threshold == 2.0
        assert analyzer.dense_block_threshold == 500

    def test_custom_thresholds(self):
        """Verifica umbrales personalizados."""
        analyzer = PacingAnalyzer(
            min_chapter_words=300,
            max_chapter_words=15000,
            dialogue_ratio_range=(0.10, 0.70),
            chapter_variance_threshold=3.0,
            dense_block_threshold=800,
        )
        assert analyzer.min_chapter_words == 300
        assert analyzer.max_chapter_words == 15000
        assert analyzer.dialogue_ratio_range == (0.10, 0.70)
        assert analyzer.chapter_variance_threshold == 3.0
        assert analyzer.dense_block_threshold == 800


class TestPacingAnalyzerMetrics:
    """Tests para cálculo de métricas."""

    def test_compute_metrics_empty_text(self):
        """Verifica métricas para texto vacío."""
        analyzer = PacingAnalyzer()
        metrics = analyzer._compute_metrics("", 1, "chapter", "Empty")
        assert metrics.word_count == 0
        assert metrics.sentence_count == 0
        assert metrics.dialogue_ratio == 0.0

    def test_compute_metrics_simple_text(self):
        """Verifica métricas para texto simple."""
        analyzer = PacingAnalyzer()
        text = "Esta es una oración. Esta es otra oración más larga que la anterior."
        metrics = analyzer._compute_metrics(text, 1, "chapter", "Test")

        assert metrics.word_count > 0
        assert metrics.sentence_count == 2
        assert metrics.char_count == len(text)
        assert metrics.dialogue_ratio == 0.0  # Sin diálogo

    def test_compute_metrics_with_dialogue(self):
        """Verifica métricas con diálogo."""
        analyzer = PacingAnalyzer()
        text = """El protagonista llegó a la puerta.

—¿Quién está ahí? —preguntó.

—Soy yo —respondió la voz.

Nadie más habló."""
        metrics = analyzer._compute_metrics(text, 1, "chapter", "Diálogo")

        assert metrics.dialogue_lines >= 2
        assert metrics.dialogue_words > 0
        assert metrics.dialogue_ratio > 0.0

    def test_compute_metrics_lexical_density(self):
        """Verifica cálculo de densidad léxica."""
        analyzer = PacingAnalyzer()
        # Texto repetitivo
        repetitive = "el perro corre el perro salta el perro ladra"
        metrics_rep = analyzer._compute_metrics(repetitive, 1, "chapter")

        # Texto variado
        varied = "el perro corre la gata salta un pájaro canta"
        metrics_var = analyzer._compute_metrics(varied, 2, "chapter")

        # El texto variado debería tener mayor densidad léxica
        assert metrics_var.lexical_density > metrics_rep.lexical_density

    def test_compute_metrics_action_verbs(self):
        """Verifica detección de verbos de acción."""
        analyzer = PacingAnalyzer()
        # Usar infinitivos que están en ACTION_VERBS
        action_text = "Quería correr por el bosque, saltar el muro y huir del peligro."
        metrics = analyzer._compute_metrics(action_text, 1, "chapter")

        assert metrics.action_verb_ratio > 0.0

    def test_aggregate_metrics(self):
        """Verifica agregación de métricas."""
        analyzer = PacingAnalyzer()
        metrics_list = [
            PacingMetrics(
                segment_id=1,
                segment_type="chapter",
                word_count=1000,
                sentence_count=50,
                dialogue_words=300,
            ),
            PacingMetrics(
                segment_id=2,
                segment_type="chapter",
                word_count=2000,
                sentence_count=100,
                dialogue_words=600,
            ),
        ]
        aggregated = analyzer._aggregate_metrics(metrics_list)

        assert aggregated["total_words"] == 3000
        assert aggregated["total_sentences"] == 150
        assert aggregated["total_chapters"] == 2
        assert aggregated["avg_chapter_words"] == 1500
        assert aggregated["dialogue_ratio"] == 0.3


class TestPacingAnalyzerIssueDetection:
    """Tests para detección de problemas."""

    def test_detect_chapter_too_short(self):
        """Verifica detección de capítulo muy corto."""
        analyzer = PacingAnalyzer(min_chapter_words=500)
        metrics = [
            PacingMetrics(segment_id=1, segment_type="chapter", word_count=200),
        ]
        issues = analyzer._check_chapter_lengths(metrics)

        assert len(issues) == 1
        assert issues[0].issue_type == PacingIssueType.CHAPTER_TOO_SHORT
        assert issues[0].severity == PacingSeverity.WARNING

    def test_detect_chapter_too_long(self):
        """Verifica detección de capítulo muy largo."""
        analyzer = PacingAnalyzer(max_chapter_words=10000)
        metrics = [
            PacingMetrics(segment_id=1, segment_type="chapter", word_count=15000),
        ]
        issues = analyzer._check_chapter_lengths(metrics)

        assert len(issues) == 1
        assert issues[0].issue_type == PacingIssueType.CHAPTER_TOO_LONG
        assert issues[0].severity == PacingSeverity.SUGGESTION

    def test_detect_unbalanced_chapters(self):
        """Verifica detección de capítulos desbalanceados."""
        analyzer = PacingAnalyzer(chapter_variance_threshold=2.0)
        # Capítulos: 1000, 1000, 5000 (el tercero es 2.5x el promedio)
        metrics = [
            PacingMetrics(segment_id=1, segment_type="chapter", word_count=1000),
            PacingMetrics(segment_id=2, segment_type="chapter", word_count=1000),
            PacingMetrics(segment_id=3, segment_type="chapter", word_count=5000),
        ]
        issues = analyzer._check_chapter_balance(metrics)

        # El capítulo 3 debería ser detectado como desbalanceado
        assert len(issues) >= 1
        assert any(i.segment_id == 3 for i in issues)

    def test_detect_too_little_dialogue(self):
        """Verifica detección de poco diálogo."""
        analyzer = PacingAnalyzer(dialogue_ratio_range=(0.15, 0.60))
        metrics = [
            PacingMetrics(
                segment_id=1, segment_type="chapter", word_count=1000, dialogue_ratio=0.05
            ),
        ]
        issues = analyzer._check_dialogue_ratio(metrics)

        assert len(issues) == 1
        assert issues[0].issue_type == PacingIssueType.TOO_LITTLE_DIALOGUE

    def test_detect_too_much_dialogue(self):
        """Verifica detección de demasiado diálogo."""
        analyzer = PacingAnalyzer(dialogue_ratio_range=(0.15, 0.60))
        metrics = [
            PacingMetrics(
                segment_id=1, segment_type="chapter", word_count=1000, dialogue_ratio=0.80
            ),
        ]
        issues = analyzer._check_dialogue_ratio(metrics)

        assert len(issues) == 1
        assert issues[0].issue_type == PacingIssueType.TOO_MUCH_DIALOGUE

    def test_ignore_short_chapters_for_dialogue_check(self):
        """Verifica que capítulos muy cortos no generan alertas de diálogo."""
        analyzer = PacingAnalyzer()
        metrics = [
            PacingMetrics(segment_id=1, segment_type="chapter", word_count=50, dialogue_ratio=0.0),
        ]
        issues = analyzer._check_dialogue_ratio(metrics)

        # No debería haber issues porque el capítulo es muy corto (<100 palabras)
        assert len(issues) == 0

    def test_detect_dense_blocks(self):
        """Verifica detección de bloques densos."""
        analyzer = PacingAnalyzer(dense_block_threshold=100)

        # Texto sin diálogo con más de 100 palabras
        words = " ".join(["palabra"] * 150)
        chapters = [{"number": 1, "title": "Test", "content": words}]
        issues = analyzer._check_dense_blocks(chapters)

        assert len(issues) >= 1
        assert issues[0].issue_type == PacingIssueType.DENSE_TEXT_BLOCK


class TestPacingAnalyzerFullAnalysis:
    """Tests para análisis completo."""

    def test_analyze_empty_chapters(self):
        """Verifica análisis con lista de capítulos vacía."""
        analyzer = PacingAnalyzer()
        result = analyzer.analyze([])

        assert result.chapter_metrics == []
        assert result.issues == []

    def test_analyze_single_chapter(self):
        """Verifica análisis con un solo capítulo."""
        analyzer = PacingAnalyzer()
        chapters = [
            {
                "number": 1,
                "title": "Único",
                "content": "Este es el contenido del único capítulo. " * 100,
            }
        ]
        result = analyzer.analyze(chapters)

        assert len(result.chapter_metrics) == 1
        assert result.chapter_metrics[0].segment_id == 1
        assert result.chapter_metrics[0].title == "Único"

    def test_analyze_multiple_chapters(self):
        """Verifica análisis con múltiples capítulos."""
        analyzer = PacingAnalyzer()
        chapters = [
            {"number": 1, "title": "Primero", "content": "Contenido del primer capítulo. " * 50},
            {"number": 2, "title": "Segundo", "content": "Contenido del segundo capítulo. " * 100},
            {"number": 3, "title": "Tercero", "content": "Contenido del tercer capítulo. " * 75},
        ]
        result = analyzer.analyze(chapters)

        assert len(result.chapter_metrics) == 3
        assert result.summary["total_chapters"] == 3
        assert result.summary["total_words"] > 0

    def test_analyze_with_full_text(self):
        """Verifica análisis con texto completo."""
        analyzer = PacingAnalyzer()
        chapters = [
            {"number": 1, "title": "Uno", "content": "Texto del capítulo uno. " * 50},
        ]
        full_text = "Este es el texto completo del documento. " * 100
        result = analyzer.analyze(chapters, full_text)

        assert result.document_metrics["word_count"] > 0

    def test_summary_includes_all_fields(self):
        """Verifica que el resumen incluye todos los campos."""
        analyzer = PacingAnalyzer()
        chapters = [
            {"number": 1, "title": "Cap 1", "content": "Texto uno. " * 200},
            {"number": 2, "title": "Cap 2", "content": "Texto dos. " * 300},
        ]
        result = analyzer.analyze(chapters)

        summary = result.summary
        assert "total_chapters" in summary
        assert "total_words" in summary
        assert "avg_chapter_words" in summary
        assert "min_chapter_words" in summary
        assert "max_chapter_words" in summary
        assert "chapter_word_variance" in summary
        assert "issues_count" in summary
        assert "issues_by_type" in summary
        assert "issues_by_severity" in summary


# =============================================================================
# Tests de Funciones de Conveniencia
# =============================================================================


class TestAnalyzePacing:
    """Tests para función analyze_pacing."""

    def test_basic_usage(self):
        """Verifica uso básico."""
        chapters = [{"number": 1, "title": "Test", "content": "Contenido de prueba. " * 50}]
        result = analyze_pacing(chapters)

        assert isinstance(result, PacingAnalysisResult)
        assert len(result.chapter_metrics) == 1

    def test_with_custom_params(self):
        """Verifica uso con parámetros personalizados."""
        chapters = [{"number": 1, "title": "Corto", "content": "Texto. " * 10}]
        result = analyze_pacing(chapters, min_chapter_words=1000)

        # Debería detectar capítulo muy corto
        assert any(i.issue_type == PacingIssueType.CHAPTER_TOO_SHORT for i in result.issues)


class TestGetPacingAnalyzer:
    """Tests para función singleton get_pacing_analyzer."""

    def test_returns_analyzer(self):
        """Verifica que devuelve un analizador."""
        analyzer = get_pacing_analyzer()
        assert isinstance(analyzer, PacingAnalyzer)

    def test_singleton_pattern(self):
        """Verifica patrón singleton."""
        analyzer1 = get_pacing_analyzer()
        analyzer2 = get_pacing_analyzer()
        assert analyzer1 is analyzer2


# =============================================================================
# Tests de Constantes
# =============================================================================


class TestActionVerbs:
    """Tests para constantes de verbos de acción."""

    def test_action_verbs_not_empty(self):
        """Verifica que hay verbos de acción definidos."""
        assert len(ACTION_VERBS) > 0

    def test_common_verbs_present(self):
        """Verifica que verbos comunes están presentes."""
        common = ["correr", "saltar", "gritar", "huir", "luchar"]
        for verb in common:
            assert verb in ACTION_VERBS

    def test_verbs_are_lowercase(self):
        """Verifica que los verbos están en minúsculas."""
        for verb in ACTION_VERBS:
            assert verb == verb.lower()


# =============================================================================
# Tests de Integración
# =============================================================================


class TestPacingIntegration:
    """Tests de integración con textos realistas."""

    def test_narrative_with_dialogue(self):
        """Verifica análisis de narrativa con diálogo."""
        chapter_content = """
María entró en la habitación. La luz del atardecer iluminaba las paredes.

—¿Hay alguien aquí? —preguntó en voz baja.

Nadie respondió. El silencio era absoluto.

—Pedro, ¿eres tú? —insistió.

Un ruido en la cocina la sobresaltó. Se acercó con cautela.

—¡María! Me has asustado —dijo Pedro saliendo de las sombras.

—¿Qué hacías a oscuras? —preguntó ella.

—Esperándote —respondió él con una sonrisa.
"""
        chapters = [{"number": 1, "title": "El encuentro", "content": chapter_content}]
        result = analyze_pacing(chapters)

        assert result.chapter_metrics[0].dialogue_lines > 0
        assert result.chapter_metrics[0].dialogue_ratio > 0.0

    def test_dense_narrative_chapter(self):
        """Verifica detección de narrativa densa."""
        # Crear un capítulo largo sin diálogo
        dense_content = (
            "El bosque se extendía hasta donde alcanzaba la vista. "
            "Los árboles centenarios proyectaban sombras sobre el sendero. "
            "Las hojas crujían bajo los pies del caminante solitario. "
            "El viento susurraba secretos antiguos entre las ramas. "
        ) * 150  # Más de 500 palabras sin diálogo

        chapters = [{"number": 1, "title": "El bosque", "content": dense_content}]
        result = analyze_pacing(chapters, dense_block_threshold=200)

        # Debería detectar bloque denso
        assert any(i.issue_type == PacingIssueType.DENSE_TEXT_BLOCK for i in result.issues)

    def test_book_with_varied_chapters(self):
        """Verifica análisis de libro con capítulos variados."""
        chapters = [
            {"number": 1, "title": "Prólogo", "content": "Texto corto. " * 50},
            {"number": 2, "title": "El viaje", "content": "Narración extensa. " * 500},
            {
                "number": 3,
                "title": "El encuentro",
                "content": "—Diálogo —dijo uno.\n\n—Respuesta —contestó otro.\n\n" * 100,
            },
            {"number": 4, "title": "Final", "content": "Conclusión. " * 100},
        ]
        result = analyze_pacing(chapters)

        assert result.summary["total_chapters"] == 4
        # El capítulo 2 debería ser el más largo
        word_counts = [m.word_count for m in result.chapter_metrics]
        assert word_counts[1] == max(word_counts)
        # El capítulo 3 debería tener más diálogo
        dialogue_ratios = [m.dialogue_ratio for m in result.chapter_metrics]
        assert dialogue_ratios[2] == max(dialogue_ratios)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
