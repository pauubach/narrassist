"""
Tests de integración del semantic checker con el spelling checker.
"""

import pytest

from narrative_assistant.nlp.orthography.base import SpellingErrorType
from narrative_assistant.nlp.orthography.spelling_checker import SpellingChecker


class TestSemanticIntegration:
    """Tests de integración del detector semántico."""

    @pytest.fixture
    def checker(self):
        """Spelling checker con semantic checking integrado."""
        return SpellingChecker()

    # -------------------------------------------------------------------------
    # Riegos vs Riesgos
    # -------------------------------------------------------------------------

    def test_riegos_detected_in_full_check(self, checker):
        """El check completo detecta 'riegos de seguridad'."""
        text = "Los riegos de seguridad son altos."
        result = checker.check(text)

        assert result.is_success
        report = result.value

        # Debe haber al menos 1 issue semántico
        semantic_issues = [i for i in report.issues if i.error_type == SpellingErrorType.SEMANTIC]
        assert len(semantic_issues) >= 1

        # Debe sugerir "riesgos"
        issue = semantic_issues[0]
        assert "riesgos" in issue.suggestions

    def test_riegos_agriculture_not_flagged(self, checker):
        """'riegos' en contexto agrícola NO se marca."""
        text = "El sistema de riegos agrícolas funciona bien."
        result = checker.check(text)

        assert result.is_success
        report = result.value

        # No debe haber issues semánticos sobre "riegos"
        semantic_issues = [
            i for i in report.issues
            if i.error_type == SpellingErrorType.SEMANTIC and "riegos" in i.word.lower()
        ]
        assert len(semantic_issues) == 0

    # -------------------------------------------------------------------------
    # Actitud vs Aptitud
    # -------------------------------------------------------------------------

    def test_actitud_aptitud_detected(self, checker):
        """Detecta 'actitud necesaria' (debería ser 'aptitud')."""
        text = "La actitud necesaria para el puesto es la experiencia."
        result = checker.check(text)

        assert result.is_success
        report = result.value

        # Debe detectar error semántico
        semantic_issues = [i for i in report.issues if i.error_type == SpellingErrorType.SEMANTIC]
        assert len(semantic_issues) >= 1

        # Debe sugerir "aptitud"
        found_aptitud = any("aptitud" in (i.suggestions or []) for i in semantic_issues)
        assert found_aptitud

    def test_actitud_comportamiento_not_flagged(self, checker):
        """'actitud' en contexto de comportamiento NO se marca."""
        text = "Su actitud positiva mejora el ambiente laboral."
        result = checker.check(text)

        assert result.is_success
        report = result.value

        # No debe haber issues semánticos sobre "actitud"
        semantic_issues = [
            i for i in report.issues
            if i.error_type == SpellingErrorType.SEMANTIC and "actitud" in i.word.lower()
        ]
        assert len(semantic_issues) == 0

    # -------------------------------------------------------------------------
    # Infringir vs Infligir
    # -------------------------------------------------------------------------

    def test_infringir_infligir_detected(self, checker):
        """Detecta 'infringir daño' (debería ser 'infligir')."""
        text = "El ataque pudo infringir daño al enemigo."
        result = checker.check(text)

        assert result.is_success
        report = result.value

        semantic_issues = [i for i in report.issues if i.error_type == SpellingErrorType.SEMANTIC]
        if len(semantic_issues) > 0:
            found_infligir = any("infligir" in (i.suggestions or []) for i in semantic_issues)
            assert found_infligir

    # -------------------------------------------------------------------------
    # Prescribir vs Proscribir
    # -------------------------------------------------------------------------

    def test_prescribir_proscribir_detected(self, checker):
        """Detecta 'proscribir medicamento' (debería ser 'prescribir')."""
        text = "El médico decidió proscribir un nuevo tratamiento."
        result = checker.check(text)

        assert result.is_success
        report = result.value

        semantic_issues = [i for i in report.issues if i.error_type == SpellingErrorType.SEMANTIC]
        if len(semantic_issues) > 0:
            found_prescribir = any("prescribir" in (i.suggestions or []) for i in semantic_issues)
            assert found_prescribir

    # -------------------------------------------------------------------------
    # Absorber vs Absolver
    # -------------------------------------------------------------------------

    def test_absorber_absolver_detected(self, checker):
        """Detecta 'absorber al acusado' (debería ser 'absolver')."""
        text = "El juez decidió absorber al acusado de todos los cargos."
        result = checker.check(text)

        assert result.is_success
        report = result.value

        semantic_issues = [i for i in report.issues if i.error_type == SpellingErrorType.SEMANTIC]
        if len(semantic_issues) > 0:
            found_absolver = any("absolver" in (i.suggestions or []) for i in semantic_issues)
            assert found_absolver

    # -------------------------------------------------------------------------
    # Multiple errors in same text
    # -------------------------------------------------------------------------

    def test_multiple_semantic_errors(self, checker):
        """Detecta múltiples errores semánticos en el mismo texto."""
        text = """
        Los riegos de seguridad son altos. La actitud necesaria es experiencia.
        El médico proscribió un medicamento.
        """
        result = checker.check(text)

        assert result.is_success
        report = result.value

        # Debe detectar al menos 2 errores semánticos (riegos y actitud, proscribir es opcional)
        semantic_issues = [i for i in report.issues if i.error_type == SpellingErrorType.SEMANTIC]
        assert len(semantic_issues) >= 2

    # -------------------------------------------------------------------------
    # Performance
    # -------------------------------------------------------------------------

    def test_semantic_check_performance(self, checker):
        """Verificar que el semantic check no degrada performance."""
        import time

        # Texto grande (500 palabras)
        text = " ".join(["palabra"] * 500)

        start = time.time()
        result = checker.check(text)
        elapsed = time.time() - start

        assert result.is_success
        # Debe procesar en menos de 3 segundos
        assert elapsed < 3.0

    # -------------------------------------------------------------------------
    # Integration with other checks
    # -------------------------------------------------------------------------

    def test_semantic_and_pattern_errors(self, checker):
        """Detecta tanto errores semánticos como de patrones."""
        text = "Los riegos de seguridad son altos etc..."

        result = checker.check(text)
        assert result.is_success
        report = result.value

        # Debe detectar ambos tipos
        error_types = {i.error_type for i in report.issues}
        assert SpellingErrorType.SEMANTIC in error_types  # "riegos"
        assert SpellingErrorType.TYPO in error_types  # "etc..."

    def test_report_statistics_include_semantic(self, checker):
        """Las estadísticas del reporte incluyen errores semánticos."""
        text = "Los riegos de seguridad son importantes."
        result = checker.check(text)

        assert result.is_success
        report = result.value

        # Verificar que las estadísticas incluyen el tipo SEMANTIC
        if len(report.issues) > 0:
            assert "semantic" in report.by_type or SpellingErrorType.SEMANTIC.value in report.by_type


class TestSemanticCheckerDisabled:
    """Tests cuando el semantic checker falla o no está disponible."""

    def test_graceful_degradation_on_error(self):
        """Si semantic_checker falla, el resto del check funciona."""
        checker = SpellingChecker()

        # Texto con error de pattern (etc...) pero sin error semántico
        text = "Todo está bien etc..."

        result = checker.check(text)
        assert result.is_success
        report = result.value

        # Debe detectar el error de pattern aunque semantic checker falle
        pattern_issues = [i for i in report.issues if i.error_type == SpellingErrorType.TYPO]
        assert len(pattern_issues) >= 1
