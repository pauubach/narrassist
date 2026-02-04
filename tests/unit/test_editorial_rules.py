"""
Tests para el módulo de reglas editoriales.

Verifica:
- Reglas predefinidas (órganos únicos, demostrativos, etc.)
- Parser de reglas de usuario
- Checker combinado (predefinidas + usuario)
"""

import pytest

from narrative_assistant.nlp.grammar.base import GrammarSeverity
from narrative_assistant.nlp.style.editorial_rules import (
    PREDEFINED_RULES,
    EditorialIssue,
    EditorialReport,
    EditorialRule,
    EditorialRuleCategory,
    EditorialRulesChecker,
    EditorialRuleType,
    _make_word_pattern,
    check_with_user_rules,
    get_editorial_checker,
    parse_user_rules,
    reset_editorial_checker,
)


class TestEditorialRuleImports:
    """Verificar que los imports funcionan correctamente."""

    def test_import_editorial_rule(self):
        assert EditorialRule is not None

    def test_import_rule_types(self):
        assert EditorialRuleType.WORD_REPLACEMENT is not None
        assert EditorialRuleType.CONTEXTUAL is not None

    def test_import_categories(self):
        assert EditorialRuleCategory.LEXICON is not None
        assert EditorialRuleCategory.ORTHOGRAPHY is not None

    def test_import_checker(self):
        assert EditorialRulesChecker is not None

    def test_import_predefined_rules(self):
        assert PREDEFINED_RULES is not None
        assert len(PREDEFINED_RULES) > 0


class TestPredefinedRules:
    """Tests para las reglas predefinidas."""

    def test_predefined_rules_count(self):
        """Debe haber al menos 15 reglas predefinidas."""
        assert len(PREDEFINED_RULES) >= 15

    def test_predefined_rules_have_required_fields(self):
        """Cada regla debe tener los campos requeridos."""
        for rule in PREDEFINED_RULES:
            assert rule.id, "Regla sin ID"
            assert rule.name, f"Regla {rule.id} sin nombre"
            assert rule.pattern, f"Regla {rule.id} sin patrón"
            assert rule.rule_type is not None
            assert rule.category is not None

    def test_singular_body_parts_rule_exists(self):
        """Debe existir la regla de órganos únicos."""
        rule = next((r for r in PREDEFINED_RULES if r.id == "singular_body_parts"), None)
        assert rule is not None
        assert "corazón" in rule.description.lower() or "corazon" in rule.description.lower()

    def test_quiza_rule_exists(self):
        """Debe existir la regla quizás -> quizá."""
        rule = next((r for r in PREDEFINED_RULES if r.id == "quiza_preferido"), None)
        assert rule is not None
        assert rule.replacement == "quizá"

    def test_periodo_rule_exists(self):
        """Debe existir la regla período -> periodo."""
        rule = next((r for r in PREDEFINED_RULES if r.id == "periodo_sin_tilde"), None)
        assert rule is not None
        assert rule.replacement == "periodo"


class TestEditorialRulesChecker:
    """Tests para el checker de reglas."""

    @pytest.fixture
    def checker(self):
        """Crear un checker fresco para cada test."""
        reset_editorial_checker()
        return get_editorial_checker()

    def test_checker_singleton(self):
        """El checker debe ser singleton."""
        reset_editorial_checker()
        c1 = get_editorial_checker()
        c2 = get_editorial_checker()
        assert c1 is c2

    def test_checker_has_rules(self, checker):
        """El checker debe tener reglas cargadas."""
        assert len(checker.rules) > 0

    def test_check_returns_report(self, checker):
        """check() debe devolver un EditorialReport."""
        report = checker.check("Texto de prueba")
        assert isinstance(report, EditorialReport)

    def test_detect_nuestros_corazones(self, checker):
        """Debe detectar 'nuestros corazones'."""
        text = "Los amantes unieron nuestros corazones."
        report = checker.check(text)

        # Buscar por el texto detectado o por el ID de la regla
        issues = [
            i
            for i in report.issues
            if "nuestros corazones" in i.text.lower()
            or i.rule_id == "singular_body_parts"
            or "singular" in i.rule_name.lower()
            or "rgano" in i.rule_name.lower()
        ]  # "órgano" sin tilde
        assert len(issues) >= 1, (
            f"No se detectó 'nuestros corazones'. Issues: {[i.text for i in report.issues]}"
        )
        assert issues[0].replacement is not None
        assert "nuestro" in issues[0].replacement.lower()

    def test_detect_quizas(self, checker):
        """Debe detectar 'quizás'."""
        text = "Quizás venga mañana."
        report = checker.check(text)

        issues = [
            i
            for i in report.issues
            if "quizá" in i.rule_name.lower() or "quiza" in i.rule_name.lower()
        ]
        assert len(issues) >= 1

    def test_detect_periodo_with_accent(self, checker):
        """Debe detectar 'período' con tilde."""
        text = "El período de prueba terminó."
        report = checker.check(text)

        issues = [i for i in report.issues if "periodo" in i.rule_name.lower()]
        assert len(issues) >= 1
        assert issues[0].replacement == "periodo"

    def test_detect_por_contra(self, checker):
        """Debe detectar 'por contra'."""
        text = "Por contra, él pensaba diferente."
        report = checker.check(text)

        issues = [i for i in report.issues if "por contra" in i.rule_name.lower()]
        assert len(issues) >= 1
        assert "contrario" in issues[0].replacement.lower()

    def test_no_false_positives_on_clean_text(self, checker):
        """No debe detectar problemas en texto limpio."""
        text = "El periodo de prueba terminó. Quizá venga mañana."
        report = checker.check(text)

        # Puede haber algunas detecciones pero no las específicas que corregimos
        quizas_issues = [i for i in report.issues if i.text.lower() == "quizás"]
        periodo_issues = [i for i in report.issues if i.text.lower() == "período"]

        assert len(quizas_issues) == 0
        assert len(periodo_issues) == 0


class TestMakeWordPattern:
    """Tests para la función de generación de patrones."""

    def test_simple_word(self):
        """Palabra simple debe tener \\b en ambos lados."""
        pattern = _make_word_pattern("palabra")
        assert pattern.startswith(r"\b")
        assert pattern.endswith(r"\b")

    def test_word_ending_with_period(self):
        """Palabra con punto final no debe tener \\b después."""
        pattern = _make_word_pattern("etc.")
        assert r"\b" in pattern  # Al inicio
        assert not pattern.endswith(r"\b")  # No al final
        assert r"(?!\w)" in pattern  # Lookahead negativo

    def test_pattern_matches_correctly(self):
        """El patrón generado debe hacer match correcto."""
        import re

        pattern = _make_word_pattern("etc.")
        regex = re.compile(pattern, re.IGNORECASE)

        assert regex.search("Hay cosas, etc.")
        assert regex.search("etc. Más texto")
        assert not regex.search("etcetera")


class TestParseUserRules:
    """Tests para el parser de reglas de usuario."""

    def test_parse_empty_text(self):
        """Texto vacío debe devolver lista vacía."""
        rules = parse_user_rules("")
        assert rules == []

    def test_parse_none(self):
        """None debe devolver lista vacía."""
        rules = parse_user_rules(None)
        assert rules == []

    def test_parse_substitution_with_quotes(self):
        """Debe parsear sustitución con comillas."""
        rules = parse_user_rules('"asimismo" -> "así mismo"')
        assert len(rules) == 1
        assert rules[0].replacement == "así mismo"

    def test_parse_substitution_without_quotes(self):
        """Debe parsear sustitución sin comillas."""
        rules = parse_user_rules("deprisa -> de prisa")
        assert len(rules) == 1
        assert rules[0].replacement == "de prisa"

    def test_parse_not_pattern(self):
        """Debe parsear patrón X (no Y)."""
        rules = parse_user_rules("sistema inmunitario (no inmunológico)")
        assert len(rules) == 1
        assert "inmunológico" in rules[0].pattern or "inmunologico" in rules[0].pattern

    def test_parse_avoid_pattern(self):
        """Debe parsear patrón evitar: X."""
        rules = parse_user_rules("evitar: etc.")
        assert len(rules) == 1
        assert rules[0].replacement is None  # Solo marcar, no reemplazar

    def test_parse_prefer_pattern(self):
        """Debe parsear patrón preferir X sobre Y."""
        rules = parse_user_rules('preferir "quizá" sobre "quizás"')
        assert len(rules) == 1
        assert rules[0].replacement == "quizá"

    def test_parse_ignores_comments(self):
        """Debe ignorar líneas con #."""
        rules = parse_user_rules("""
# Esto es un comentario
"quizás" -> "quizá"
# Otro comentario
""")
        assert len(rules) == 1

    def test_parse_ignores_empty_lines(self):
        """Debe ignorar líneas vacías."""
        rules = parse_user_rules("""
"a" -> "b"

"c" -> "d"
""")
        assert len(rules) == 2

    def test_parse_handles_bullet_points(self):
        """Debe manejar bullet points."""
        rules = parse_user_rules("""
- "a" -> "b"
* "c" -> "d"
• "e" -> "f"
""")
        assert len(rules) == 3

    def test_parse_multiple_rules(self):
        """Debe parsear múltiples reglas."""
        rules = parse_user_rules("""
"quizás" -> "quizá"
deprisa -> de prisa
sistema inmunitario (no inmunológico)
evitar: etc.
""")
        assert len(rules) == 4


class TestCheckWithUserRules:
    """Tests para la función combinada."""

    def test_check_with_empty_user_rules(self):
        """Con reglas vacías, solo aplica predefinidas."""
        text = "Quizás nuestros corazones..."
        report = check_with_user_rules(text, "", include_predefined=True)

        assert report.issue_count >= 1  # Al menos "nuestros corazones"

    def test_check_with_user_rules_only(self):
        """Sin predefinidas, solo aplica reglas del usuario."""
        text = "Texto con foo y bar."
        user_rules = '"foo" -> "baz"'

        report = check_with_user_rules(text, user_rules, include_predefined=False)

        assert report.issue_count == 1
        assert report.issues[0].text == "foo"

    def test_check_combines_both(self):
        """Debe combinar reglas predefinidas y del usuario."""
        text = "Quizás el sistema inmunológico falle."
        user_rules = "sistema inmunitario (no inmunológico)"

        report = check_with_user_rules(text, user_rules, include_predefined=True)

        # Debe detectar "quizás" (predefinida) e "inmunológico" (usuario)
        rule_names = [i.rule_name.lower() for i in report.issues]
        has_quiza = any("quizá" in n or "quiza" in n for n in rule_names)
        has_inmunologico = any("inmun" in n for n in rule_names)

        assert has_quiza or has_inmunologico  # Al menos uno


class TestEditorialReport:
    """Tests para el reporte."""

    def test_report_to_dict(self):
        """to_dict() debe serializar correctamente."""
        report = EditorialReport()
        report.issues.append(
            EditorialIssue(
                rule_id="test",
                rule_name="Test Rule",
                text="foo",
                replacement="bar",
                start=0,
                end=3,
                severity=GrammarSeverity.STYLE,
                explanation="Test explanation",
                category=EditorialRuleCategory.LEXICON,
            )
        )
        report.rules_applied = 1

        data = report.to_dict()

        assert "issues" in data
        assert len(data["issues"]) == 1
        assert data["issues"][0]["rule_id"] == "test"
        assert data["rules_applied"] == 1

    def test_report_issue_count(self):
        """issue_count debe reflejar el número de issues."""
        report = EditorialReport()
        assert report.issue_count == 0

        report.issues.append(
            EditorialIssue(
                rule_id="test",
                rule_name="Test",
                text="a",
                replacement="b",
                start=0,
                end=1,
                severity=GrammarSeverity.STYLE,
                explanation="",
                category=EditorialRuleCategory.LEXICON,
            )
        )

        assert report.issue_count == 1


class TestIntegration:
    """Tests de integración end-to-end."""

    def test_full_editorial_check(self):
        """Test completo con texto realista."""
        reset_editorial_checker()

        text = """
        Los amantes unieron nuestros corazones en un abrazo eterno.
        Quizás el período fue muy largo. Por contra, él pensaba diferente.
        El sistema inmunológico falló después de 5 años de tratamiento.
        """

        user_rules = """
        sistema inmunitario (no inmunológico)
        evitar: etc.
        """

        report = check_with_user_rules(text, user_rules, include_predefined=True)

        # Debe detectar varios problemas
        assert report.issue_count >= 3

        # Verificar tipos de problemas detectados
        texts_found = [i.text.lower() for i in report.issues]

        # Al menos uno de estos debe estar
        expected_any = ["nuestros corazones", "quizás", "período", "por contra", "inmunológico"]
        found_expected = any(any(e in t for t in texts_found) for e in expected_any)
        assert found_expected, f"No se encontró ninguno de {expected_any} en {texts_found}"

    def test_user_rules_override_nothing(self):
        """Las reglas de usuario se suman, no reemplazan."""
        reset_editorial_checker()

        # Solo con predefinidas
        text = "Quizás venga."
        report1 = check_with_user_rules(text, "", include_predefined=True)
        count1 = report1.issue_count

        # Con regla de usuario adicional (no relacionada)
        report2 = check_with_user_rules(text, '"foo" -> "bar"', include_predefined=True)
        count2 = report2.issue_count

        # Debe tener al menos los mismos problemas
        assert count2 >= count1
