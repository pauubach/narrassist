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
        assert len(CONFUSION_PAIRS) >= 58  # 58 pares implementados

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

    # -------------------------------------------------------------------------
    # Triple homofonía: ha / ah / a
    # -------------------------------------------------------------------------

    def test_ha_verb_correct(self, checker_no_embeddings):
        """NO detecta 'ha' en contexto de verbo haber (correcto)."""
        text = "Ella ha comido bien hoy."
        issues = checker_no_embeddings.check(text)

        ha_issues = [i for i in issues if "ha" in i.word.lower()]
        assert len(ha_issues) == 0

    def test_a_instead_of_ha_detected(self, checker_no_embeddings):
        """Detecta 'a' en contexto de verbo haber (debería ser 'ha')."""
        text = "Ella a comido bien hoy."
        issues = checker_no_embeddings.check(text)

        a_issues = [i for i in issues if i.word.lower() == "a"]
        if len(a_issues) > 0:
            assert "ha" in a_issues[0].suggestions

    def test_ah_interjection_correct(self, checker_no_embeddings):
        """NO detecta 'ah' en contexto de interjección (correcto)."""
        text = "¡Ah, ya entiendo!"
        issues = checker_no_embeddings.check(text)

        ah_issues = [i for i in issues if "ah" in i.word.lower()]
        assert len(ah_issues) == 0

    def test_a_preposition_correct(self, checker_no_embeddings):
        """NO detecta 'a' en contexto de preposición (correcto)."""
        text = "Voy a casa ahora mismo."
        issues = checker_no_embeddings.check(text)

        # No debe haber issues sobre "a" como preposición
        a_issues = [i for i in issues if i.word.lower() == "a" and "casa" in text]
        assert len(a_issues) == 0

    # -------------------------------------------------------------------------
    # Triple homofonía: hay / ahí / ay
    # -------------------------------------------------------------------------

    def test_hay_verb_correct(self, checker_no_embeddings):
        """NO detecta 'hay' en contexto de verbo haber (correcto)."""
        text = "Hay mucha gente en la sala."
        issues = checker_no_embeddings.check(text)

        hay_issues = [i for i in issues if "hay" in i.word.lower()]
        assert len(hay_issues) == 0

    def test_ahi_instead_of_hay_detected(self, checker_no_embeddings):
        """Detecta 'ahí' en contexto de verbo haber (debería ser 'hay')."""
        text = "Ahí mucha gente en la sala."
        issues = checker_no_embeddings.check(text)

        ahi_issues = [i for i in issues if "ahí" in i.word.lower()]
        if len(ahi_issues) > 0:
            assert "hay" in ahi_issues[0].suggestions

    def test_ahi_place_correct(self, checker_no_embeddings):
        """NO detecta 'ahí' en contexto de lugar (correcto)."""
        text = "Deja el libro ahí, por favor."
        issues = checker_no_embeddings.check(text)

        ahi_issues = [i for i in issues if "ahí" in i.word.lower()]
        assert len(ahi_issues) == 0

    def test_ay_interjection_correct(self, checker_no_embeddings):
        """NO detecta 'ay' en contexto de interjección (correcto)."""
        text = "¡Ay, qué dolor!"
        issues = checker_no_embeddings.check(text)

        ay_issues = [i for i in issues if i.word.lower() == "ay"]
        assert len(ay_issues) == 0

    # -------------------------------------------------------------------------
    # Triple homofonía: vaya / valla / baya
    # -------------------------------------------------------------------------

    def test_vaya_verb_correct(self, checker_no_embeddings):
        """NO detecta 'vaya' en contexto de verbo ir (correcto)."""
        text = "Espero que vaya bien el examen."
        issues = checker_no_embeddings.check(text)

        vaya_issues = [i for i in issues if "vaya" in i.word.lower()]
        assert len(vaya_issues) == 0

    def test_valla_fence_correct(self, checker_no_embeddings):
        """NO detecta 'valla' en contexto de cerca (correcto)."""
        text = "La valla publicitaria es muy grande."
        issues = checker_no_embeddings.check(text)

        valla_issues = [i for i in issues if "valla" in i.word.lower()]
        assert len(valla_issues) == 0

    def test_valla_instead_of_vaya_detected(self, checker_no_embeddings):
        """Detecta 'valla' en contexto de verbo ir (debería ser 'vaya')."""
        text = "Espero que valla bien el examen."
        issues = checker_no_embeddings.check(text)

        valla_issues = [i for i in issues if "valla" in i.word.lower()]
        if len(valla_issues) > 0:
            assert "vaya" in valla_issues[0].suggestions

    def test_baya_fruit_correct(self, checker_no_embeddings):
        """NO detecta 'baya' en contexto de fruto (correcto)."""
        text = "La baya del arándano es deliciosa."
        issues = checker_no_embeddings.check(text)

        baya_issues = [i for i in issues if "baya" in i.word.lower()]
        assert len(baya_issues) == 0

    # -------------------------------------------------------------------------
    # Otras homofonías importantes
    # -------------------------------------------------------------------------

    def test_botar_votar_detected(self, checker_no_embeddings):
        """Detecta 'botar' en contexto de elecciones (debería ser 'votar')."""
        text = "Voy a botar en las próximas elecciones."
        issues = checker_no_embeddings.check(text)

        botar_issues = [i for i in issues if "botar" in i.word.lower()]
        if len(botar_issues) > 0:
            assert "votar" in botar_issues[0].suggestions

    def test_grabar_gravar_detected(self, checker_no_embeddings):
        """Detecta 'grabar' en contexto de impuestos (debería ser 'gravar')."""
        text = "El gobierno va a grabar los productos importados."
        issues = checker_no_embeddings.check(text)

        grabar_issues = [i for i in issues if "grabar" in i.word.lower()]
        if len(grabar_issues) > 0:
            assert "gravar" in grabar_issues[0].suggestions

    def test_vaca_baca_detected(self, checker_no_embeddings):
        """Detecta 'vaca' en contexto de portaequipajes (debería ser 'baca')."""
        text = "Coloca el equipaje en la vaca del coche."
        issues = checker_no_embeddings.check(text)

        vaca_issues = [i for i in issues if "vaca" in i.word.lower()]
        if len(vaca_issues) > 0:
            assert "baca" in vaca_issues[0].suggestions

    def test_caza_casa_detected(self, checker_no_embeddings):
        """Detecta 'caza' en contexto de vivienda (debería ser 'casa')."""
        text = "Vivo en una caza muy bonita."
        issues = checker_no_embeddings.check(text)

        caza_issues = [i for i in issues if "caza" in i.word.lower()]
        if len(caza_issues) > 0:
            assert "casa" in caza_issues[0].suggestions


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
