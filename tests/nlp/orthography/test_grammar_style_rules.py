"""
Tests para reglas de gramática y estilo (Quick Wins + Phase 2).

Cubre:
- Quick Wins: etc..., espacio antes puntuación, redundancias, riegos/riesgos
- Phase 2: repetición palabras, dequeísmo, queísmo, números, gerundios
"""

import pytest

from narrative_assistant.nlp.orthography.base import (
    SpellingErrorType,
    SpellingSeverity,
)
from narrative_assistant.nlp.orthography.spelling_checker import SpellingChecker
from narrative_assistant.nlp.orthography.voting_checker import VotingSpellingChecker


# =============================================================================
# QUICK WINS - Reglas de patrones simples (spelling_checker.py)
# =============================================================================


class TestQuickWinsPatterns:
    """Tests para reglas Quick Win implementadas en spelling_checker.py."""

    @pytest.fixture
    def checker(self):
        """Spelling checker básico."""
        return SpellingChecker()

    # -------------------------------------------------------------------------
    # 1. "etc..." - redundancia
    # -------------------------------------------------------------------------

    def test_etc_redundancy_detected(self, checker):
        """Detecta 'etc...' como redundancia."""
        text = "Compró manzanas, naranjas, etc..."
        issues = checker._check_patterns(text)

        redundancy_issues = [i for i in issues if i.error_type == SpellingErrorType.TYPO]
        assert len(redundancy_issues) >= 1
        assert any("etc." in i.word.lower() for i in redundancy_issues)

    def test_etc_correct_not_flagged(self, checker):
        """'etc.' correcto no se marca."""
        text = "Compró manzanas, naranjas, etc."
        issues = checker._check_patterns(text)

        etc_issues = [i for i in issues if "etc" in i.word.lower()]
        # No debe haber issues con etc (solo 1 punto)
        assert len(etc_issues) == 0

    def test_etcetera_redundancy(self, checker):
        """Detecta 'etcétera...' como redundancia."""
        text = "Frutas, verduras, etcétera..."
        issues = checker._check_patterns(text)

        redundancy_issues = [i for i in issues if i.error_type == SpellingErrorType.TYPO]
        assert len(redundancy_issues) >= 1

    # -------------------------------------------------------------------------
    # 2. Espacio antes de puntuación
    # -------------------------------------------------------------------------

    def test_space_before_comma(self, checker):
        """Detecta espacio antes de coma."""
        text = "Hola , ¿cómo estás?"
        issues = checker._check_patterns(text)

        space_issues = [i for i in issues if i.error_type == SpellingErrorType.TYPO]
        assert len(space_issues) >= 1
        assert any("puntuación" in i.explanation.lower() for i in space_issues)

    def test_space_before_semicolon(self, checker):
        """Detecta espacio antes de punto y coma."""
        text = "Era tarde ; no había tiempo."
        issues = checker._check_patterns(text)

        space_issues = [i for i in issues if i.error_type == SpellingErrorType.TYPO]
        assert len(space_issues) >= 1

    def test_space_before_colon(self, checker):
        """Detecta espacio antes de dos puntos."""
        text = "Lista de compras : manzanas, peras."
        issues = checker._check_patterns(text)

        space_issues = [i for i in issues if i.error_type == SpellingErrorType.TYPO]
        assert len(space_issues) >= 1

    def test_space_before_exclamation(self, checker):
        """Detecta espacio antes de signo de exclamación."""
        text = "¡Hola !"
        issues = checker._check_patterns(text)

        space_issues = [i for i in issues if i.error_type == SpellingErrorType.TYPO]
        assert len(space_issues) >= 1

    def test_correct_punctuation_not_flagged(self, checker):
        """Puntuación correcta (sin espacio antes) no se marca."""
        text = "Hola, ¿cómo estás? Todo bien; gracias."
        issues = checker._check_patterns(text)

        # No debe haber issues de espacio antes de puntuación
        space_issues = [
            i
            for i in issues
            if i.error_type == SpellingErrorType.TYPO
            and "puntuación" in i.explanation.lower()
        ]
        assert len(space_issues) == 0

    # -------------------------------------------------------------------------
    # 3. Redundancias espaciales
    # -------------------------------------------------------------------------

    def test_subir_arriba_redundancy(self, checker):
        """Detecta 'subir arriba' como redundancia."""
        text = "Voy a subir arriba a mi habitación."
        issues = checker._check_patterns(text)

        redundancy_issues = [
            i for i in issues if i.error_type == SpellingErrorType.REDUNDANCY
        ]
        assert len(redundancy_issues) >= 1
        assert any("subir" in i.explanation.lower() for i in redundancy_issues)

    def test_bajar_abajo_redundancy(self, checker):
        """Detecta 'bajar abajo' como redundancia."""
        text = "Voy a bajar abajo al sótano."
        issues = checker._check_patterns(text)

        redundancy_issues = [
            i for i in issues if i.error_type == SpellingErrorType.REDUNDANCY
        ]
        assert len(redundancy_issues) >= 1
        assert any("bajar" in i.explanation.lower() for i in redundancy_issues)

    def test_salir_fuera_redundancy(self, checker):
        """Detecta 'salir fuera' como redundancia."""
        text = "Necesito salir fuera de la casa."
        issues = checker._check_patterns(text)

        redundancy_issues = [
            i for i in issues if i.error_type == SpellingErrorType.REDUNDANCY
        ]
        assert len(redundancy_issues) >= 1
        assert any("salir" in i.explanation.lower() for i in redundancy_issues)

    def test_entrar_dentro_redundancy(self, checker):
        """Detecta 'entrar dentro' como redundancia."""
        text = "Vamos a entrar dentro del edificio."
        issues = checker._check_patterns(text)

        redundancy_issues = [
            i for i in issues if i.error_type == SpellingErrorType.REDUNDANCY
        ]
        assert len(redundancy_issues) >= 1
        assert any("entrar" in i.explanation.lower() for i in redundancy_issues)

    def test_volver_regresar_redundancy(self, checker):
        """Detecta 'volver a regresar' como redundancia."""
        text = "Decidió volver a regresar a su país."
        issues = checker._check_patterns(text)

        redundancy_issues = [
            i for i in issues if i.error_type == SpellingErrorType.REDUNDANCY
        ]
        assert len(redundancy_issues) >= 1
        assert any("volver" in i.explanation.lower() for i in redundancy_issues)

    def test_correct_spatial_not_flagged(self, checker):
        """Usos correctos no se marcan como redundancia."""
        text = "Subió las escaleras. Bajó la pendiente. Salió corriendo. Entró rápido."
        issues = checker._check_patterns(text)

        redundancy_issues = [
            i for i in issues if i.error_type == SpellingErrorType.REDUNDANCY
        ]
        assert len(redundancy_issues) == 0


# =============================================================================
# VOTING CHECKER - Reglas complejas (voting_checker.py)
# =============================================================================


class TestVotingCheckerRules:
    """Tests para reglas implementadas en voting_checker.py."""

    @pytest.fixture
    def error_patterns(self):
        """Obtener ERROR_PATTERNS del PatternVoter."""
        from narrative_assistant.nlp.orthography.voting_checker import PatternVoter

        return PatternVoter.ERROR_PATTERNS

    # -------------------------------------------------------------------------
    # 4. Riegos vs riesgos - NOTA: Ahora se detecta en semantic_checker.py
    # -------------------------------------------------------------------------

    def test_riegos_detection_moved_to_semantic_checker(self):
        """
        La detección de 'riegos vs riesgos' ahora se hace en semantic_checker.py
        con análisis contextual más robusto.

        Este test verifica que NO esté hardcodeado en voting_checker.
        """
        from narrative_assistant.nlp.orthography.voting_checker import PatternVoter

        error_patterns = PatternVoter.ERROR_PATTERNS

        # NO debe haber patterns de tipo "semantic" para riegos en voting_checker
        semantic_patterns = [
            p for p in error_patterns if p[1] == "semantic" and "riegos?" in p[0]
        ]
        assert len(semantic_patterns) == 0, (
            "Los patterns de 'riegos' deben estar en semantic_checker.py, "
            "no hardcodeados en voting_checker.py"
        )

    def test_riegos_semantic_checker_works(self):
        """Verificar que semantic_checker detecta 'riegos' correctamente."""
        from narrative_assistant.nlp.orthography.semantic_checker import SemanticChecker

        checker = SemanticChecker(use_embeddings=False)

        # Detecta en contexto incorrecto
        text_wrong = "Hay riegos de seguridad en el sistema."
        issues_wrong = checker.check(text_wrong)
        assert len(issues_wrong) >= 1
        assert "riesgos" in issues_wrong[0].suggestions

        # NO detecta en contexto correcto (agrícola)
        text_correct = "Sistema de riegos agrícolas para el campo."
        issues_correct = checker.check(text_correct)
        assert len(issues_correct) == 0

    # -------------------------------------------------------------------------
    # 5. Repetición de palabras
    # -------------------------------------------------------------------------

    def test_repetition_pattern_exists(self, error_patterns):
        """Verifica que existe pattern para repetición de palabras."""
        import re

        # Debe haber pattern de tipo "repetition"
        repetition_patterns = [p for p in error_patterns if p[1] == "repetition"]
        assert len(repetition_patterns) >= 1

        # Verificar que detecta "casa casa"
        text = "La casa casa está muy bonita."
        pattern = repetition_patterns[0][0]
        match = re.search(pattern, text, re.IGNORECASE)
        assert match is not None

    def test_repetition_short_words_ignored(self, error_patterns):
        """Palabras cortas no se marcan como repetición."""
        import re

        text = "El el problema es grave."
        repetition_patterns = [p for p in error_patterns if p[1] == "repetition"]

        if repetition_patterns:
            pattern = repetition_patterns[0][0]
            match = re.search(pattern, text, re.IGNORECASE)
            # Pattern debe requerir palabras largas (4+ chars)
            assert match is None

    # -------------------------------------------------------------------------
    # 6. Dequeísmo
    # -------------------------------------------------------------------------

    def test_dequeismo_pattern_exists(self, error_patterns):
        """Verifica que existe pattern para dequeísmo."""
        import re

        # Debe haber pattern de tipo "dequeismo"
        dequeismo_patterns = [p for p in error_patterns if p[1] == "dequeismo"]
        assert len(dequeismo_patterns) >= 1

        # Verificar que detecta "pienso de que"
        text = "Pienso de que es una buena idea."
        pattern = dequeismo_patterns[0][0]
        match = re.search(pattern, text, re.IGNORECASE)
        assert match is not None

    def test_dequeismo_correct_not_flagged(self, error_patterns):
        """'pienso que' correcto no se marca."""
        import re

        text = "Pienso que es una buena idea."
        dequeismo_patterns = [p for p in error_patterns if p[1] == "dequeismo"]

        if dequeismo_patterns:
            pattern = dequeismo_patterns[0][0]
            match = re.search(pattern, text, re.IGNORECASE)
            assert match is None

    # -------------------------------------------------------------------------
    # 7. Queísmo
    # -------------------------------------------------------------------------

    def test_queismo_pattern_exists(self, error_patterns):
        """Verifica que existe pattern para queísmo."""
        import re

        # Debe haber pattern de tipo "queismo"
        queismo_patterns = [p for p in error_patterns if p[1] == "queismo"]
        assert len(queismo_patterns) >= 1

        # Verificar que detecta "me acuerdo que"
        text = "Me acuerdo que fuimos al parque."
        pattern = queismo_patterns[0][0]
        match = re.search(pattern, text, re.IGNORECASE)
        assert match is not None

    def test_queismo_correct_not_flagged(self, error_patterns):
        """'me acuerdo de que' correcto no se marca."""
        import re

        text = "Me acuerdo de que fuimos al parque."
        queismo_patterns = [p for p in error_patterns if p[1] == "queismo"]

        if queismo_patterns:
            pattern = queismo_patterns[0][0]
            match = re.search(pattern, text, re.IGNORECASE)
            assert match is None

    # -------------------------------------------------------------------------
    # 8. Números en narrativa (1-10 deben ir en letras)
    # -------------------------------------------------------------------------

    def test_number_in_narrative_pattern_exists(self, error_patterns):
        """Verifica que existe pattern para números en narrativa."""
        import re

        # Buscar pattern de tipo "style" que tenga "personas?" u otro sustantivo
        number_patterns = [
            p
            for p in error_patterns
            if p[1] == "style" and re.search(r"\[1-9\].*personas?", p[0])
        ]
        assert len(number_patterns) >= 1

        # Verificar que detecta "3 personas"
        text = "Había 3 personas en la sala."
        pattern = number_patterns[0][0]
        match = re.search(pattern, text, re.IGNORECASE)
        assert match is not None

    def test_number_written_not_flagged(self, error_patterns):
        """Números escritos en letras no se marcan."""
        import re

        text = "Había tres personas en la sala."
        number_patterns = [
            p
            for p in error_patterns
            if p[1] == "style" and re.search(r"\[1-9\].*personas?", p[0])
        ]

        if number_patterns:
            pattern = number_patterns[0][0]
            match = re.search(pattern, text, re.IGNORECASE)
            assert match is None

    # -------------------------------------------------------------------------
    # 9. Gerundios excesivos (3+ gerundios en proximidad)
    # -------------------------------------------------------------------------

    def test_gerund_pattern_exists(self, error_patterns):
        """Verifica que existe pattern para gerundios excesivos."""
        # Buscar pattern que contenga "ndo" y sea de tipo "style"
        gerund_patterns = [
            p
            for p in error_patterns
            if p[1] == "style"
            and "ndo" in p[0]
            and (r"\w+ndo" in p[0] or r"\\w+ndo" in p[0])
        ]
        assert len(gerund_patterns) >= 1


# =============================================================================
# INTEGRATION TESTS - Flujo completo
# =============================================================================


class TestGrammarStyleIntegration:
    """Tests de integración para el flujo completo."""

    @pytest.fixture
    def spelling_checker(self):
        """Spelling checker para tests."""
        return SpellingChecker()

    @pytest.fixture
    def voting_checker(self):
        """Voting checker para tests."""
        return VotingSpellingChecker()

    def test_multiple_errors_detected(self, spelling_checker):
        """Detecta múltiples errores en un solo texto."""
        text = "Voy a subir arriba etc... , porque pienso de que es necesario ."

        issues = spelling_checker._check_patterns(text)

        # Debe detectar:
        # 1. "subir arriba" (redundancia)
        # 2. "etc..." (redundancia)
        # 3. " ," (espacio antes de puntuación) - 2 veces
        # Total: 4 issues
        assert len(issues) >= 3

        # Verificar tipos de error
        error_types = {i.error_type for i in issues}
        assert SpellingErrorType.REDUNDANCY in error_types
        assert SpellingErrorType.TYPO in error_types

    def test_clean_text_no_errors(self, spelling_checker):
        """Texto limpio no genera errores."""
        text = "Subió las escaleras rápidamente, pensando en la reunión."

        issues = spelling_checker._check_patterns(text)

        # No debe haber issues de las reglas nuevas
        assert len(issues) == 0

    def test_edge_cases(self, spelling_checker):
        """Casos límite no generan falsos positivos de las reglas nuevas."""
        # Texto con "etc." correcto, puntuación correcta, sin redundancias
        text = "La casa tiene ventanas, puertas, etc. Todo está en orden. Bajó por las escaleras sin problemas."

        issues = spelling_checker._check_patterns(text)

        # No debe haber issues de las reglas nuevas (REDUNDANCY, etc...)
        new_rule_issues = [
            i
            for i in issues
            if i.error_type == SpellingErrorType.REDUNDANCY
            or "etc." in i.explanation.lower()
            or "puntuación" in i.explanation.lower()
        ]
        assert len(new_rule_issues) == 0


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================


class TestPerformance:
    """Tests de rendimiento para las nuevas reglas."""

    @pytest.fixture
    def large_text(self):
        """Texto grande para test de rendimiento."""
        # 1000 líneas de texto
        return "\n".join(
            [
                f"Esta es la línea {i} del documento de prueba. "
                f"Contiene texto normal sin errores ortográficos."
                for i in range(1000)
            ]
        )

    def test_pattern_checking_performance(self, large_text):
        """Verificar que pattern checking no es excesivamente lento."""
        import time

        checker = SpellingChecker()

        start = time.time()
        issues = checker._check_patterns(large_text)
        elapsed = time.time() - start

        # Debe procesar 1000 líneas en menos de 1 segundo
        assert elapsed < 1.0

    def test_voting_patterns_performance(self, large_text):
        """Verificar rendimiento de voting patterns."""
        import re
        import time

        from narrative_assistant.nlp.orthography.voting_checker import PatternVoter

        patterns = PatternVoter.ERROR_PATTERNS

        start = time.time()
        for pattern, _, _ in patterns:
            re.findall(pattern, large_text, re.IGNORECASE)
        elapsed = time.time() - start

        # Debe procesar todos los patterns en menos de 2 segundos
        assert elapsed < 2.0
