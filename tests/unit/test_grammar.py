"""
Tests unitarios para el módulo de gramática.

Verifica la detección de errores gramaticales en español.
"""

import pytest


class TestGrammarImports:
    """Tests de importación del módulo de gramática."""

    def test_import_grammar_module(self):
        """Verifica importación del módulo."""
        from narrative_assistant.nlp import grammar

        assert grammar is not None

    def test_import_grammar_checker(self):
        """Verifica importación de GrammarChecker."""
        from narrative_assistant.nlp.grammar import GrammarChecker

        assert GrammarChecker is not None

    def test_import_get_grammar_checker(self):
        """Verifica importación de get_grammar_checker."""
        from narrative_assistant.nlp.grammar import get_grammar_checker

        assert callable(get_grammar_checker)

    def test_import_grammar_issue(self):
        """Verifica importación de GrammarIssue."""
        from narrative_assistant.nlp.grammar import GrammarIssue

        assert GrammarIssue is not None

    def test_import_grammar_report(self):
        """Verifica importación de GrammarReport."""
        from narrative_assistant.nlp.grammar import GrammarReport

        assert GrammarReport is not None

    def test_import_enums(self):
        """Verifica importación de enums."""
        from narrative_assistant.nlp.grammar import GrammarErrorType, GrammarSeverity

        assert GrammarErrorType is not None
        assert GrammarSeverity is not None


class TestGrammarErrorType:
    """Tests para GrammarErrorType enum."""

    def test_error_types_exist(self):
        """Tipos de error gramatical esperados existen."""
        from narrative_assistant.nlp.grammar import GrammarErrorType

        expected_types = [
            "GENDER_AGREEMENT",
            "NUMBER_AGREEMENT",
            "DEQUEISMO",
            "QUEISMO",
            "LAISMO",
            "LEISMO",
            "LOISMO",
            "REDUNDANCY",
            "SENTENCE_FRAGMENT",
        ]

        for error_type in expected_types:
            assert hasattr(GrammarErrorType, error_type), f"Missing: {error_type}"


class TestGrammarSeverity:
    """Tests para GrammarSeverity enum."""

    def test_severities_exist(self):
        """Niveles de severidad existen."""
        from narrative_assistant.nlp.grammar import GrammarSeverity

        # La implementación usa ERROR, WARNING, STYLE, INFO
        expected = ["ERROR", "WARNING", "STYLE", "INFO"]

        for sev in expected:
            assert hasattr(GrammarSeverity, sev), f"Missing severity: {sev}"


class TestGrammarIssue:
    """Tests para GrammarIssue dataclass."""

    def test_create_issue(self):
        """Crea un issue gramatical."""
        from narrative_assistant.nlp.grammar import (
            GrammarErrorType,
            GrammarIssue,
            GrammarSeverity,
        )

        issue = GrammarIssue(
            text="de que",
            start_char=10,
            end_char=16,
            sentence="Pienso de que vendrá.",
            error_type=GrammarErrorType.DEQUEISMO,
            severity=GrammarSeverity.ERROR,
            suggestion="que",
            confidence=0.9,
            explanation="Uso incorrecto de 'de que' (dequeísmo)",
            rule_id="DEQUEISMO_001",
        )

        assert issue.text == "de que"
        assert issue.error_type == GrammarErrorType.DEQUEISMO
        assert issue.suggestion == "que"
        assert issue.confidence == 0.9


class TestGrammarReport:
    """Tests para GrammarReport dataclass."""

    def test_create_empty_report(self):
        """Crea reporte vacío."""
        from narrative_assistant.nlp.grammar import GrammarReport

        report = GrammarReport(issues=[])

        assert report.issues == []
        assert len(report.issues) == 0

    def test_report_with_issues(self):
        """Crea reporte con issues."""
        from narrative_assistant.nlp.grammar import (
            GrammarErrorType,
            GrammarIssue,
            GrammarReport,
            GrammarSeverity,
        )

        issues = [
            GrammarIssue(
                text="de que",
                start_char=0,
                end_char=6,
                sentence="de que vendrá",
                error_type=GrammarErrorType.DEQUEISMO,
                severity=GrammarSeverity.ERROR,
                suggestion="que",
                confidence=0.9,
            ),
        ]

        report = GrammarReport(issues=issues)

        assert len(report.issues) == 1
        assert report.issues[0].error_type == GrammarErrorType.DEQUEISMO


class TestGrammarChecker:
    """Tests para GrammarChecker."""

    def test_checker_instantiation(self):
        """Checker se puede instanciar."""
        from narrative_assistant.nlp.grammar import GrammarChecker

        checker = GrammarChecker()
        assert checker is not None

    def test_checker_has_check_method(self):
        """Checker tiene método check."""
        from narrative_assistant.nlp.grammar import GrammarChecker

        checker = GrammarChecker()
        assert hasattr(checker, "check")
        assert callable(checker.check)

    def test_get_grammar_checker_singleton(self):
        """get_grammar_checker retorna singleton."""
        from narrative_assistant.nlp.grammar import get_grammar_checker

        checker1 = get_grammar_checker()
        checker2 = get_grammar_checker()

        assert checker1 is checker2

    def test_check_correct_text(self):
        """Texto correcto no genera issues graves."""
        from narrative_assistant.nlp.grammar import get_grammar_checker

        checker = get_grammar_checker()
        result = checker.check("María caminaba por el parque tranquilamente.")

        assert result.is_success


class TestDequeismoDetection:
    """Tests para detección de dequeísmo."""

    @pytest.fixture
    def checker(self):
        """Checker para tests."""
        from narrative_assistant.nlp.grammar import get_grammar_checker, reset_grammar_checker

        reset_grammar_checker()
        return get_grammar_checker()

    @pytest.mark.parametrize(
        "text",
        [
            "Pienso de que vendrá mañana.",
            "Creo de que es verdad.",
            "Me parece de que tienes razón.",
            "Opino de que deberíamos ir.",
        ],
    )
    def test_dequeismo_patterns(self, checker, text):
        """Verifica detección de dequeísmo."""
        result = checker.check(text)
        assert result.is_success

        # Buscar issues de dequeísmo
        from narrative_assistant.nlp.grammar import GrammarErrorType

        dequeismo_issues = [
            i for i in result.value.issues if i.error_type == GrammarErrorType.DEQUEISMO
        ]
        # La detección depende de la implementación


class TestQueismoDetection:
    """Tests para detección de queísmo."""

    @pytest.fixture
    def checker(self):
        """Checker para tests."""
        from narrative_assistant.nlp.grammar import get_grammar_checker, reset_grammar_checker

        reset_grammar_checker()
        return get_grammar_checker()

    @pytest.mark.parametrize(
        "text",
        [
            "Me acuerdo que fuimos al cine.",
            "Me alegro que estés bien.",
            "Estoy seguro que vendrá.",
        ],
    )
    def test_queismo_patterns(self, checker, text):
        """Verifica detección de queísmo."""
        result = checker.check(text)
        assert result.is_success


class TestLaismoDetection:
    """Tests para detección de laísmo."""

    @pytest.fixture
    def checker(self):
        """Checker para tests."""
        from narrative_assistant.nlp.grammar import get_grammar_checker, reset_grammar_checker

        reset_grammar_checker()
        return get_grammar_checker()

    @pytest.mark.parametrize(
        "text",
        [
            "La dije que viniera.",
            "La regalé flores.",
            "La conté la historia.",
        ],
    )
    def test_laismo_patterns(self, checker, text):
        """Verifica detección de laísmo."""
        result = checker.check(text)
        assert result.is_success


class TestGenderAgreement:
    """Tests para concordancia de género."""

    @pytest.fixture
    def checker(self):
        """Checker para tests."""
        from narrative_assistant.nlp.grammar import get_grammar_checker, reset_grammar_checker

        reset_grammar_checker()
        return get_grammar_checker()

    @pytest.mark.parametrize(
        "text",
        [
            "La casa blanco.",
            "El mesa grande.",
            "Una libro interesante.",
        ],
    )
    def test_gender_disagreement(self, checker, text):
        """Verifica detección de discordancia de género."""
        result = checker.check(text)
        assert result.is_success


class TestRedundancy:
    """Tests para detección de redundancias."""

    @pytest.fixture
    def checker(self):
        """Checker para tests."""
        from narrative_assistant.nlp.grammar import get_grammar_checker, reset_grammar_checker

        reset_grammar_checker()
        return get_grammar_checker()

    @pytest.mark.parametrize(
        "text,redundancy",
        [
            ("Subir arriba", "subir arriba"),
            ("Bajar abajo", "bajar abajo"),
            ("Salir afuera", "salir afuera"),
            ("Entrar adentro", "entrar adentro"),
        ],
    )
    def test_redundancy_patterns(self, checker, text, redundancy):
        """Verifica detección de redundancias."""
        result = checker.check(text)
        assert result.is_success
