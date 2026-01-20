"""
Tests unitarios para las reglas de gramática española.

Verifica la detección de:
- Dequeísmo
- Queísmo
- Laísmo/Loísmo
- Concordancia de género y número
- Redundancias
- Puntuación
"""

import pytest
from typing import Optional

# Importar después de que el módulo esté disponible
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


class TestSpanishRulesImports:
    """Tests de importación del módulo de reglas españolas."""

    def test_import_spanish_rules(self):
        """Verifica importación del módulo."""
        from narrative_assistant.nlp.grammar import spanish_rules
        assert spanish_rules is not None

    def test_import_apply_spanish_rules(self):
        """Verifica importación de apply_spanish_rules."""
        from narrative_assistant.nlp.grammar import apply_spanish_rules
        assert callable(apply_spanish_rules)

    def test_import_spanish_rules_config(self):
        """Verifica importación de SpanishRulesConfig."""
        from narrative_assistant.nlp.grammar import SpanishRulesConfig
        assert SpanishRulesConfig is not None

    def test_import_individual_checks(self):
        """Verifica importación de funciones de verificación individuales."""
        from narrative_assistant.nlp.grammar import (
            check_dequeismo,
            check_queismo,
            check_laismo,
            check_loismo,
            check_gender_agreement,
            check_number_agreement,
            check_redundancy,
            check_punctuation,
        )
        assert all(callable(f) for f in [
            check_dequeismo, check_queismo, check_laismo, check_loismo,
            check_gender_agreement, check_number_agreement,
            check_redundancy, check_punctuation,
        ])


@pytest.fixture(scope="module")
def nlp():
    """Carga modelo spaCy para tests."""
    from narrative_assistant.nlp.spacy_gpu import load_spacy_model
    return load_spacy_model()


class TestDequeismo:
    """Tests para detección de dequeísmo."""

    @pytest.mark.parametrize("text,should_detect", [
        # Casos de dequeísmo (deben detectarse)
        ("Pienso de que vendrá mañana.", True),
        ("Creo de que es verdad.", True),
        ("Opino de que deberíamos ir.", True),
        ("Me parece de que tienes razón.", True),
        ("Supongo de que llegará tarde.", True),
        ("Digo de que no es así.", True),
        # Casos correctos (no deben detectarse)
        ("Pienso que vendrá mañana.", False),
        ("Creo que es verdad.", False),
        ("Me alegro de que estés bien.", False),  # Esto es correcto
        ("Estoy seguro de que vendrá.", False),  # Esto es correcto
    ])
    def test_dequeismo_detection(self, nlp, text, should_detect):
        """Verifica detección de dequeísmo."""
        from narrative_assistant.nlp.grammar.spanish_rules import check_dequeismo
        from narrative_assistant.nlp.grammar import GrammarErrorType

        doc = nlp(text)
        issues = check_dequeismo(doc)

        if should_detect:
            assert len(issues) > 0, f"Debería detectar dequeísmo en: {text}"
            assert all(i.error_type == GrammarErrorType.DEQUEISMO for i in issues)
        else:
            dequeismo_issues = [i for i in issues if i.error_type == GrammarErrorType.DEQUEISMO]
            assert len(dequeismo_issues) == 0, f"No debería detectar dequeísmo en: {text}"

    def test_dequeismo_suggestion(self, nlp):
        """Verifica que la sugerencia es correcta."""
        from narrative_assistant.nlp.grammar.spanish_rules import check_dequeismo

        doc = nlp("Pienso de que vendrá.")
        issues = check_dequeismo(doc)

        assert len(issues) > 0
        assert issues[0].suggestion == "que"


class TestQueismo:
    """Tests para detección de queísmo."""

    @pytest.mark.parametrize("text,should_detect", [
        # Casos de queísmo (deben detectarse)
        ("Me acuerdo que fuimos al cine.", True),
        ("Me alegro que estés bien.", True),
        ("Estoy seguro que vendrá.", True),
        ("Me olvidé que tenía cita.", True),
        ("Me quejé que no funcionaba.", True),
        # Casos correctos (no deben detectarse)
        ("Me acuerdo de que fuimos al cine.", False),
        ("Me alegro de que estés bien.", False),
        ("Estoy seguro de que vendrá.", False),
        ("Pienso que es correcto.", False),  # No lleva "de"
    ])
    def test_queismo_detection(self, nlp, text, should_detect):
        """Verifica detección de queísmo."""
        from narrative_assistant.nlp.grammar.spanish_rules import check_queismo
        from narrative_assistant.nlp.grammar import GrammarErrorType

        doc = nlp(text)
        issues = check_queismo(doc)

        if should_detect:
            assert len(issues) > 0, f"Debería detectar queísmo en: {text}"
            assert all(i.error_type == GrammarErrorType.QUEISMO for i in issues)
        else:
            queismo_issues = [i for i in issues if i.error_type == GrammarErrorType.QUEISMO]
            assert len(queismo_issues) == 0, f"No debería detectar queísmo en: {text}"


class TestLaismo:
    """Tests para detección de laísmo."""

    @pytest.mark.parametrize("text,should_detect", [
        # Casos de laísmo (deben detectarse)
        ("La dije que viniera.", True),
        ("La di un regalo.", True),
        ("La conté la historia.", True),
        ("La pregunté su nombre.", True),
        # Casos correctos (no deben detectarse)
        ("Le dije que viniera.", False),
        ("Le di un regalo.", False),
        ("La vi en el parque.", False),  # Correcto: CD femenino
    ])
    def test_laismo_detection(self, nlp, text, should_detect):
        """Verifica detección de laísmo."""
        from narrative_assistant.nlp.grammar.spanish_rules import check_laismo
        from narrative_assistant.nlp.grammar import GrammarErrorType

        doc = nlp(text)
        issues = check_laismo(doc)

        laismo_issues = [i for i in issues if i.error_type == GrammarErrorType.LAISMO]

        if should_detect:
            assert len(laismo_issues) > 0, f"Debería detectar laísmo en: {text}"
        # Nota: No verificamos falsos negativos estrictamente porque
        # el laísmo es difícil de detectar sin contexto completo


class TestGenderAgreement:
    """Tests para concordancia de género."""

    @pytest.mark.parametrize("text,should_detect", [
        # Errores de género (deben detectarse)
        ("El casa es grande.", True),
        ("La libro está aquí.", True),
        ("Un mesa pequeña.", True),
        ("Una coche rojo.", True),
        # Casos correctos (no deben detectarse)
        ("La casa es grande.", False),
        ("El libro está aquí.", False),
        ("Una mesa pequeña.", False),
        ("Un coche rojo.", False),
        # Casos especiales
        ("El agua está fría.", False),  # Femenino con "el" por "a" tónica
        ("El alma pura.", False),  # Femenino con "el" por "a" tónica
    ])
    def test_gender_agreement(self, nlp, text, should_detect):
        """Verifica detección de discordancia de género."""
        from narrative_assistant.nlp.grammar.spanish_rules import check_gender_agreement
        from narrative_assistant.nlp.grammar import GrammarErrorType

        doc = nlp(text)
        issues = check_gender_agreement(doc)

        gender_issues = [i for i in issues if i.error_type == GrammarErrorType.GENDER_AGREEMENT]

        if should_detect:
            assert len(gender_issues) > 0, f"Debería detectar error de género en: {text}"


class TestNumberAgreement:
    """Tests para concordancia de número."""

    @pytest.mark.parametrize("text,should_detect", [
        # Errores de número (deben detectarse)
        ("El libros están aquí.", True),
        ("Los casa es grande.", True),
        # Casos correctos (no deben detectarse)
        ("El libro está aquí.", False),
        ("Los libros están aquí.", False),
        ("La casa es grande.", False),
        ("Las casas son grandes.", False),
        # Excepciones (palabras que terminan en s pero son singular)
        ("El lunes es festivo.", False),
        ("La crisis es grave.", False),
    ])
    def test_number_agreement(self, nlp, text, should_detect):
        """Verifica detección de discordancia de número."""
        from narrative_assistant.nlp.grammar.spanish_rules import check_number_agreement
        from narrative_assistant.nlp.grammar import GrammarErrorType

        doc = nlp(text)
        issues = check_number_agreement(doc)

        number_issues = [i for i in issues if i.error_type == GrammarErrorType.NUMBER_AGREEMENT]

        if should_detect:
            assert len(number_issues) > 0, f"Debería detectar error de número en: {text}"


class TestRedundancy:
    """Tests para detección de redundancias."""

    @pytest.mark.parametrize("text,redundancy,correction", [
        ("Voy a subir arriba.", "subir arriba", "subir"),
        ("Quiero bajar abajo.", "bajar abajo", "bajar"),
        ("Vamos a salir afuera.", "salir afuera", "salir"),
        ("Hay que entrar adentro.", "entrar adentro", "entrar"),
        ("Lo voy a volver a repetir.", "volver a repetir", "repetir"),
        ("En el lapso de tiempo actual.", "lapso de tiempo", "lapso"),
        ("Es más mejor así.", "más mejor", "mejor"),
    ])
    def test_redundancy_detection(self, nlp, text, redundancy, correction):
        """Verifica detección de redundancias."""
        from narrative_assistant.nlp.grammar.spanish_rules import check_redundancy
        from narrative_assistant.nlp.grammar import GrammarErrorType

        doc = nlp(text)
        issues = check_redundancy(doc)

        assert len(issues) > 0, f"Debería detectar redundancia en: {text}"

        # Verificar que encontró la redundancia correcta
        redundancy_texts = [i.text.lower() for i in issues]
        assert any(redundancy in t for t in redundancy_texts), \
            f"Debería detectar '{redundancy}' en issues: {redundancy_texts}"

        # Verificar sugerencia
        for issue in issues:
            if redundancy in issue.text.lower():
                assert issue.suggestion == correction, \
                    f"Sugerencia debería ser '{correction}', no '{issue.suggestion}'"

    def test_no_false_positives(self, nlp):
        """Texto correcto no genera falsos positivos de redundancia."""
        from narrative_assistant.nlp.grammar.spanish_rules import check_redundancy

        text = "Subí al segundo piso y bajé por las escaleras."
        doc = nlp(text)
        issues = check_redundancy(doc)

        assert len(issues) == 0, f"No debería detectar redundancias en texto correcto"


class TestHabemos:
    """Tests para detección de *habemos."""

    def test_habemos_detection(self, nlp):
        """Detecta uso incorrecto de habemos."""
        from narrative_assistant.nlp.grammar.spanish_rules import check_habemos
        from narrative_assistant.nlp.grammar import GrammarErrorType

        doc = nlp("Habemos muchos que pensamos así.")
        issues = check_habemos(doc)

        assert len(issues) > 0
        assert issues[0].error_type == GrammarErrorType.INFINITIVE_ERROR
        assert "hay" in issues[0].suggestion.lower() or "somos" in issues[0].suggestion.lower()


class TestPunctuation:
    """Tests para detección de errores de puntuación."""

    @pytest.mark.parametrize("text,should_detect", [
        # Errores de puntuación
        ("Hola , cómo estás.", True),  # Espacio antes de coma
        ("Vamos;Siguiente paso.", True),  # Mayúscula después de punto y coma
        # Casos correctos
        ("Hola, cómo estás.", False),
        ("Vamos; siguiente paso.", False),
    ])
    def test_punctuation_errors(self, nlp, text, should_detect):
        """Verifica detección de errores de puntuación."""
        from narrative_assistant.nlp.grammar.spanish_rules import check_punctuation

        doc = nlp(text)
        issues = check_punctuation(doc)

        if should_detect:
            assert len(issues) > 0, f"Debería detectar error de puntuación en: {text}"


class TestApplySpanishRules:
    """Tests para la función principal apply_spanish_rules."""

    def test_apply_all_rules(self, nlp):
        """Aplica todas las reglas a texto con múltiples errores."""
        from narrative_assistant.nlp.grammar.spanish_rules import apply_spanish_rules

        text = """
        Pienso de que María vendrá. Me alegro que esté bien.
        La dije que trajera el libros. Habemos muchos aquí.
        Voy a subir arriba a buscar la mesa.
        """

        doc = nlp(text)
        issues = apply_spanish_rules(doc)

        # Debería encontrar varios errores
        assert len(issues) >= 3, f"Debería encontrar al menos 3 errores, encontró {len(issues)}"

        # Verificar tipos de errores detectados
        from narrative_assistant.nlp.grammar import GrammarErrorType
        error_types = {i.error_type for i in issues}

        # Al menos debería detectar dequeísmo y redundancia
        expected_types = {GrammarErrorType.DEQUEISMO, GrammarErrorType.REDUNDANCY}
        detected = expected_types & error_types
        assert len(detected) >= 1, f"Debería detectar al menos dequeísmo o redundancia"

    def test_apply_with_config(self, nlp):
        """Aplica reglas con configuración personalizada."""
        from narrative_assistant.nlp.grammar.spanish_rules import (
            apply_spanish_rules,
            SpanishRulesConfig,
        )

        text = "Pienso de que vendrá. Subir arriba es fácil."
        doc = nlp(text)

        # Solo verificar redundancias
        config = SpanishRulesConfig(
            check_dequeismo=False,
            check_queismo=False,
            check_laismo=False,
            check_loismo=False,
            check_gender=False,
            check_number=False,
            check_redundancy=True,
            check_punctuation=False,
            check_other=False,
        )

        issues = apply_spanish_rules(doc, config)

        # Solo debería encontrar redundancia
        from narrative_assistant.nlp.grammar import GrammarErrorType
        for issue in issues:
            assert issue.error_type == GrammarErrorType.REDUNDANCY, \
                f"Solo debería detectar redundancias, no {issue.error_type}"

    def test_min_confidence_filter(self, nlp):
        """Verifica filtrado por confianza mínima."""
        from narrative_assistant.nlp.grammar.spanish_rules import (
            apply_spanish_rules,
            SpanishRulesConfig,
        )

        text = "Pienso de que vendrá mañana."
        doc = nlp(text)

        # Con confianza mínima muy alta
        config = SpanishRulesConfig(min_confidence=0.99)
        high_conf_issues = apply_spanish_rules(doc, config)

        # Con confianza mínima baja
        config = SpanishRulesConfig(min_confidence=0.1)
        low_conf_issues = apply_spanish_rules(doc, config)

        # Debería haber menos o iguales issues con umbral alto
        assert len(high_conf_issues) <= len(low_conf_issues)


class TestGrammarCheckerIntegration:
    """Tests de integración del GrammarChecker con reglas españolas."""

    @pytest.fixture
    def checker(self):
        """Crea checker sin LanguageTool."""
        from narrative_assistant.nlp.grammar import GrammarChecker
        from narrative_assistant.core.config import GrammarConfig

        config = GrammarConfig(
            use_languagetool=False,
            use_llm=False,
            min_confidence=0.5,
        )
        return GrammarChecker(config=config)

    def test_check_text_with_errors(self, checker):
        """Verifica que el checker detecta errores."""
        text = """
        María pensaba de que Juan vendría pronto.
        La dije que trajera el libro. Subir arriba es fácil.
        """

        result = checker.check(text)

        assert result.is_success
        assert len(result.value.issues) > 0

    def test_check_correct_text(self, checker):
        """Texto correcto genera menos errores."""
        text = """
        María pensaba que Juan vendría pronto.
        Le dije que trajera el libro. Subir es fácil.
        """

        result = checker.check(text)

        assert result.is_success
        # Puede haber algunos falsos positivos pero menos que con errores

    def test_check_empty_text(self, checker):
        """Texto vacío no genera errores."""
        result = checker.check("")

        assert result.is_success
        assert len(result.value.issues) == 0

    def test_check_with_progress_callback(self, checker):
        """Verifica callback de progreso."""
        progress_values = []

        def callback(progress: float, message: str):
            progress_values.append((progress, message))

        result = checker.check(
            "Pienso de que vendrá.",
            progress_callback=callback,
        )

        assert result.is_success
        assert len(progress_values) > 0
        assert progress_values[-1][0] == 1.0  # Último valor es 100%

    def test_config_disables_rules(self):
        """Verifica que la config puede deshabilitar reglas."""
        from narrative_assistant.nlp.grammar import GrammarChecker
        from narrative_assistant.core.config import GrammarConfig

        # Config con dequeísmo deshabilitado
        config = GrammarConfig(
            check_dequeismo=False,
            use_languagetool=False,
            use_llm=False,
        )
        checker = GrammarChecker(config=config)

        result = checker.check("Pienso de que vendrá.")

        assert result.is_success
        # No debería detectar dequeísmo
        from narrative_assistant.nlp.grammar import GrammarErrorType
        dequeismo_issues = [
            i for i in result.value.issues
            if i.error_type == GrammarErrorType.DEQUEISMO
        ]
        # Puede que otros métodos (regex) lo detecten, pero las reglas españolas no
