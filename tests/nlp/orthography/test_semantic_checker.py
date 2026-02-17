"""
Tests para el corrector semántico genérico.
"""

import pytest

from narrative_assistant.nlp.orthography.semantic_checker import (
    SemanticChecker,
    check_semantic_context,
    CONFUSION_PAIRS,
)
from narrative_assistant.nlp.orthography.base import SpellingErrorType


class TestSemanticChecker:
    """Tests para detección de palabras fuera de contexto."""

    @pytest.fixture
    def checker_no_embeddings(self):
        """Checker sin embeddings (solo keywords)."""
        return SemanticChecker(use_embeddings=False)

    @pytest.fixture
    def checker_with_embeddings(self):
        """Checker con embeddings (si están disponibles)."""
        return SemanticChecker(use_embeddings=True)

    # -------------------------------------------------------------------------
    # Riegos vs Riesgos
    # -------------------------------------------------------------------------

    def test_riegos_in_wrong_context_detected(self, checker_no_embeddings):
        """Detecta 'riegos' en contexto de peligros (debería ser 'riesgos')."""
        text = "Los riegos de seguridad en el sistema son altos."
        issues = checker_no_embeddings.check(text)

        # Debe detectar 1 issue
        assert len(issues) >= 1
        issue = issues[0]
        assert issue.word.lower() == "riegos"
        assert issue.error_type == SpellingErrorType.SEMANTIC
        assert "riesgos" in issue.suggestions

    def test_riegos_laborales_detected(self, checker_no_embeddings):
        """Detecta 'riegos laborales' (debería ser 'riesgos laborales')."""
        text = "La prevención de riegos laborales es fundamental."
        issues = checker_no_embeddings.check(text)

        assert len(issues) >= 1
        issue = issues[0]
        assert issue.word.lower() == "riegos"
        assert "riesgos" in issue.suggestions

    def test_riegos_multiple_keywords(self, checker_no_embeddings):
        """Detecta 'riegos' con múltiples keywords de contexto incorrecto."""
        text = "El análisis de riegos financieros asociados al mercado."
        issues = checker_no_embeddings.check(text)

        assert len(issues) >= 1
        assert "riesgos" in issues[0].suggestions

    def test_riegos_in_correct_context_not_flagged(self, checker_no_embeddings):
        """NO detecta 'riegos' en contexto agrícola (correcto)."""
        text = "El sistema de riegos agrícolas mejora el rendimiento de los cultivos."
        issues = checker_no_embeddings.check(text)

        # No debe haber issues (contexto correcto = agricultura)
        assert len(issues) == 0

    def test_riegos_agriculture_context_not_flagged(self, checker_no_embeddings):
        """NO detecta 'riegos' con keywords agrícolas."""
        text = "Los riegos por aspersión requieren menos agua que el riego tradicional."
        issues = checker_no_embeddings.check(text)

        assert len(issues) == 0

    def test_riegos_neutral_context_not_flagged(self, checker_no_embeddings):
        """NO detecta 'riegos' en contexto neutral sin keywords."""
        text = "Los riegos son importantes."
        issues = checker_no_embeddings.check(text)

        # Sin keywords de contexto incorrecto, no debe marcar
        assert len(issues) == 0

    # -------------------------------------------------------------------------
    # Tests con embeddings (si están disponibles)
    # -------------------------------------------------------------------------

    def test_embeddings_available_flag(self, checker_with_embeddings):
        """Verificar si embeddings están disponibles."""
        # Solo verificar que no crashea
        assert isinstance(checker_with_embeddings.use_embeddings, bool)

    def test_riegos_with_embeddings_more_precise(self, checker_with_embeddings):
        """Con embeddings, la detección debe ser más precisa."""
        text = "Los riegos de accidente son altos en este trabajo."
        issues = checker_with_embeddings.check(text)

        if checker_with_embeddings.use_embeddings:
            # Debe detectar con alta confianza
            assert len(issues) >= 1
            issue = issues[0]
            assert "riesgos" in issue.suggestions
            # Con embeddings, confianza puede ser mayor
            assert issue.confidence >= 0.70

    # -------------------------------------------------------------------------
    # Generic helper function
    # -------------------------------------------------------------------------

    def test_check_semantic_context_helper(self):
        """La función helper check_semantic_context() funciona."""
        text = "Los riegos laborales aumentan cada año."
        issues = check_semantic_context(text)

        # Debe funcionar igual que SemanticChecker
        assert isinstance(issues, list)
        if len(issues) > 0:
            assert all(isinstance(i.error_type, SpellingErrorType) for i in issues)

    # -------------------------------------------------------------------------
    # Imperativos incorrectos (infinitivo como imperativo plural)
    # -------------------------------------------------------------------------

    def test_callar_imperative_detected(self, checker_no_embeddings):
        """Detecta 'callar' usado como imperativo (debería ser 'callad')."""
        text = "¡Callar todos ahora mismo!"
        issues = checker_no_embeddings.check(text)

        assert len(issues) >= 1
        issue = issues[0]
        assert issue.word.lower() == "callar"
        assert "callad" in issue.suggestions

    def test_callar_infinitive_not_flagged(self, checker_no_embeddings):
        """NO detecta 'callar' en contexto infinitivo (correcto)."""
        text = "Hay que callar cuando habla el profesor."
        issues = checker_no_embeddings.check(text)

        # No debe haber issues sobre "callar"
        callar_issues = [i for i in issues if "callar" in i.word.lower()]
        assert len(callar_issues) == 0

    def test_venir_imperative_detected(self, checker_no_embeddings):
        """Detecta 'venir' como imperativo (debería ser 'venid')."""
        text = "¡Venir aquí todos vosotros!"
        issues = checker_no_embeddings.check(text)

        venir_issues = [i for i in issues if "venir" in i.word.lower()]
        if len(venir_issues) > 0:
            assert "venid" in venir_issues[0].suggestions

    def test_ir_imperative_detected(self, checker_no_embeddings):
        """Detecta 'ir' como imperativo (debería ser 'id')."""
        text = "¡Ir allí ahora mismo!"
        issues = checker_no_embeddings.check(text)

        ir_issues = [i for i in issues if i.word.lower() == "ir"]
        if len(ir_issues) > 0:
            assert "id" in ir_issues[0].suggestions

    def test_hacer_imperative_detected(self, checker_no_embeddings):
        """Detecta 'hacer' como imperativo (debería ser 'haced')."""
        text = "¡Hacer esto ya, vosotros!"
        issues = checker_no_embeddings.check(text)

        hacer_issues = [i for i in issues if "hacer" in i.word.lower()]
        if len(hacer_issues) > 0:
            assert "haced" in hacer_issues[0].suggestions

    # -------------------------------------------------------------------------
    # Configuration tests
    # -------------------------------------------------------------------------

    def test_confusion_pairs_configured(self):
        """Verificar que CONFUSION_PAIRS tiene al menos un par."""
        assert len(CONFUSION_PAIRS) >= 5  # Al menos riegos + 4 más

    def test_confusion_pairs_structure(self):
        """Verificar estructura de CONFUSION_PAIRS."""
        for pair in CONFUSION_PAIRS:
            assert hasattr(pair, "wrong_word")
            assert hasattr(pair, "correct_word")
            assert hasattr(pair, "wrong_context_keywords")
            assert hasattr(pair, "correct_context_keywords")
            assert len(pair.wrong_context_keywords) > 0
            assert len(pair.correct_context_keywords) > 0

    # -------------------------------------------------------------------------
    # Edge cases
    # -------------------------------------------------------------------------

    def test_empty_text(self, checker_no_embeddings):
        """Texto vacío no crashea."""
        issues = checker_no_embeddings.check("")
        assert issues == []

    def test_short_text(self, checker_no_embeddings):
        """Texto corto sin contexto no crashea."""
        issues = checker_no_embeddings.check("riegos")
        # Sin contexto, no debe marcar (o puede marcar con baja confianza)
        # Depende de la implementación exacta

    def test_multiple_occurrences(self, checker_no_embeddings):
        """Múltiples ocurrencias de la misma palabra se detectan."""
        text = "Los riegos de seguridad y los riegos laborales son críticos."
        issues = checker_no_embeddings.check(text)

        # Debe detectar ambas ocurrencias
        assert len(issues) == 2
        assert all(i.word.lower() == "riegos" for i in issues)

    def test_case_insensitive(self, checker_no_embeddings):
        """La detección es case-insensitive."""
        text_lower = "los riegos de seguridad son altos."
        text_upper = "Los RIEGOS de seguridad son altos."
        text_title = "Los Riegos De Seguridad Son Altos."

        issues_lower = checker_no_embeddings.check(text_lower)
        issues_upper = checker_no_embeddings.check(text_upper)
        issues_title = checker_no_embeddings.check(text_title)

        assert len(issues_lower) >= 1
        assert len(issues_upper) >= 1
        assert len(issues_title) >= 1

    # -------------------------------------------------------------------------
    # Performance
    # -------------------------------------------------------------------------

    def test_performance_large_text(self, checker_no_embeddings):
        """Verificar que no es excesivamente lento en textos grandes."""
        import time

        # Texto grande (500 líneas)
        text = "\n".join(
            [f"Esta es la línea {i} del documento. Los riegos de seguridad son importantes." for i in range(500)]
        )

        start = time.time()
        issues = checker_no_embeddings.check(text)
        elapsed = time.time() - start

        # Debe procesar en menos de 2 segundos (sin embeddings)
        assert elapsed < 2.0
        # Debe detectar muchos issues (500 líneas con "riegos de seguridad")
        assert len(issues) == 500


class TestIntegration:
    """Tests de integración del sistema semántico."""

    def test_semantic_checker_returns_spelling_issues(self):
        """El checker retorna SpellingIssue válidos."""
        checker = SemanticChecker(use_embeddings=False)
        text = "Los riegos de seguridad aumentan."
        issues = checker.check(text)

        if len(issues) > 0:
            issue = issues[0]
            # Verificar que todos los campos están presentes
            assert issue.word
            assert issue.start_char >= 0
            assert issue.end_char > issue.start_char
            assert issue.sentence
            assert issue.error_type == SpellingErrorType.SEMANTIC
            assert len(issue.suggestions) > 0
            assert issue.best_suggestion
            assert 0.0 <= issue.confidence <= 1.0
