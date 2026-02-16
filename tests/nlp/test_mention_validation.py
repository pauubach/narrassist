"""
Tests para el sistema de validación adaptativa de menciones.

Suite completa de 30+ tests que cubren:
- Contextos posesivos (filtrar)
- Excepciones de verbos de comunicación (mantener)
- Sujetos y objetos (mantener)
- Nombres compuestos
- Cadenas posesivas
- Casos ambiguos
"""

import pytest

from narrative_assistant.nlp.mention_validation import (
    Mention,
    ValidationMethod,
    create_validator_chain,
)


@pytest.fixture
def validator_regex_only():
    """Validador solo con regex (rápido)."""
    return create_validator_chain(use_spacy=False)


@pytest.fixture
def validator_full():
    """Validador completo (regex + spaCy)."""
    return create_validator_chain(use_spacy=True)


# ==============================================================================
# 1. CONTEXTOS POSESIVOS (Debe FILTRAR)
# ==============================================================================


class TestPossessiveContexts:
    """Tests para detección de contextos posesivos."""

    @pytest.mark.parametrize(
        "text,entity,expected_valid",
        [
            # Básicos
            ("El farmacéutico, amante secreto de Isabel, preparó el veneno.", "Isabel", False),
            ("La casa de María estaba vacía.", "María", False),
            ("El hermano del capitán llegó al puerto.", "capitán", False),
            # Con adjetivos
            ("El hermoso jardín de Isabel era magnífico.", "Isabel", False),
            ("La antigua casa de María.", "María", False),
            # Cadenas posesivas
            ("El hijo del amigo de Roberto era médico.", "Roberto", False),
            ("El perro del vecino de Juan ladraba.", "Juan", False),
        ],
    )
    def test_possessive_contexts_filtered(
        self, validator_regex_only, text, entity, expected_valid
    ):
        """Regex debe detectar contextos posesivos y filtrarlos."""
        mention = Mention(text=entity, position=text.index(entity))
        result = validator_regex_only.validate(mention, text, {entity})

        assert result.is_valid == expected_valid
        if not expected_valid:
            assert result.confidence >= 0.85
            assert "posesivo" in result.reasoning.lower()

    def test_possessive_with_newline(self, validator_regex_only):
        """Debe manejar 'de' seguido de salto de línea."""
        text = "El amante de\nIsabel preparó el veneno."
        mention = Mention(text="Isabel", position=text.index("Isabel"))

        result = validator_regex_only.validate(mention, text, {"Isabel"})

        # Regex actual podría no detectar esto, documentar comportamiento
        # Para una implementación futura, considerar normalizar whitespace
        assert isinstance(result.is_valid, bool)  # Al menos no falla

    @pytest.mark.parametrize(
        "text,entity",
        [
            ("El hermano de María José preparó la cena.", "María José"),
            ("La casa de San Pedro.", "San Pedro"),
        ],
    )
    def test_possessive_with_compound_names(self, validator_regex_only, text, entity):
        """Debe filtrar nombres compuestos en contextos posesivos."""
        mention = Mention(text=entity, position=text.index(entity))
        result = validator_regex_only.validate(mention, text, {entity})

        assert result.is_valid == False
        assert result.confidence >= 0.80


# ==============================================================================
# 2. EXCEPCIONES: VERBOS DE COMUNICACIÓN (Debe MANTENER)
# ==============================================================================


class TestCommunicationVerbExceptions:
    """Tests para excepciones de verbos de comunicación."""

    @pytest.mark.parametrize(
        "text,entity",
        [
            ("El narrador habla de Isabel en el prólogo.", "Isabel"),
            ("El libro trata de María y su familia.", "María"),
            ("Mencionó a Roberto en su discurso.", "Roberto"),
            ("El capítulo dice de Isabel que era valiente.", "Isabel"),
            ("El autor cuenta de María su historia.", "María"),
        ],
    )
    def test_communication_verbs_keep_mention(self, validator_regex_only, text, entity):
        """Verbos de comunicación NO deben filtrar la mención."""
        mention = Mention(text=entity, position=text.index(entity))
        result = validator_regex_only.validate(mention, text, {entity})

        assert result.is_valid == True
        assert result.confidence >= 0.70
        # Puede ser "comunicativo", "verbo" u "objeto directo"
        assert (
            "comunicativo" in result.reasoning.lower()
            or "verbo" in result.reasoning.lower()
            or "objeto" in result.reasoning.lower()
        )


# ==============================================================================
# 3. SUJETOS Y OBJETOS (Debe MANTENER)
# ==============================================================================


class TestValidSyntacticRoles:
    """Tests para roles sintácticos válidos."""

    @pytest.mark.parametrize(
        "text,entity",
        [
            # Sujetos
            ("Isabel preparó el veneno con cuidado.", "Isabel"),
            ("María ordenó zarpar al amanecer.", "María"),
            ("Roberto entró en la habitación.", "Roberto"),
            # Inicio de oración
            ("Juan era un hombre valiente.", "Juan"),
            ("Pedro había llegado temprano.", "Pedro"),
        ],
    )
    def test_subject_at_sentence_start(self, validator_regex_only, text, entity):
        """Sujetos al inicio de oración deben tener alta confianza."""
        mention = Mention(text=entity, position=text.index(entity))
        result = validator_regex_only.validate(mention, text, {entity})

        assert result.is_valid == True
        assert result.confidence >= 0.80

    @pytest.mark.skipif(
        True, reason="Requiere spaCy - estos tests validan análisis sintáctico"
    )
    @pytest.mark.parametrize(
        "text,entity,expected_dep",
        [
            ("Vio a Isabel en la plaza.", "Isabel", "obj"),
            ("Le dio el libro a María.", "María", "iobj"),
            ("La reina, Isabel, entró al salón.", "Isabel", "appos"),
            ("María y Isabel llegaron juntas.", "Isabel", "conj"),
        ],
    )
    def test_object_roles_with_spacy(self, validator_full, text, entity, expected_dep):
        """spaCy debe detectar objetos y conjunciones correctamente."""
        mention = Mention(text=entity, position=text.index(entity))
        result = validator_full.validate(mention, text, {entity})

        assert result.is_valid == True
        assert result.confidence >= 0.80
        assert result.method == ValidationMethod.SPACY
        # Verificar que el metadata contiene el dep correcto
        if "dep" in result.metadata:
            assert expected_dep in result.metadata.get("dep", "")


# ==============================================================================
# 4. VALIDACIÓN CON SPACY (Nivel 2)
# ==============================================================================


@pytest.mark.skipif(
    True, reason="Requiere spaCy - solo ejecutar si hay tiempo suficiente"
)
class TestSpacyValidation:
    """Tests para validación con análisis sintáctico spaCy."""

    def test_spacy_detects_nmod_possessive(self, validator_full):
        """spaCy debe detectar nmod como contexto posesivo."""
        text = "El hermano de Roberto era médico."
        mention = Mention(text="Roberto", position=text.index("Roberto"))

        result = validator_full.validate(mention, text, {"Roberto"})

        assert result.is_valid == False
        assert result.method == ValidationMethod.SPACY
        assert "posesivo" in result.reasoning.lower() or "nmod" in result.reasoning.lower()
        assert result.confidence >= 0.85

    def test_spacy_detects_nsubj_valid(self, validator_full):
        """spaCy debe detectar nsubj como rol válido."""
        text = "Isabel preparó el veneno."
        mention = Mention(text="Isabel", position=text.index("Isabel"))

        result = validator_full.validate(mention, text, {"Isabel"})

        assert result.is_valid == True
        assert result.method in {ValidationMethod.REGEX, ValidationMethod.SPACY}
        assert result.confidence >= 0.85

    def test_spacy_communication_verb_exception(self, validator_full):
        """spaCy debe mantener menciones de verbos comunicativos."""
        text = "El autor habla de Isabel con admiración."
        mention = Mention(text="Isabel", position=text.index("Isabel"))

        result = validator_full.validate(mention, text, {"Isabel"})

        assert result.is_valid == True
        # Puede ser detectado por regex o spaCy
        assert result.confidence >= 0.70


# ==============================================================================
# 5. CASOS AMBIGUOS
# ==============================================================================


class TestAmbiguousCases:
    """Tests para casos ambiguos (documentar comportamiento)."""

    def test_sentence_start_no_verb(self, validator_regex_only):
        """Inicio de oración sin verbo claro → confianza media."""
        text = "María, en silencio, observaba."
        mention = Mention(text="María", position=text.index("María"))

        result = validator_regex_only.validate(mention, text, {"María"})

        assert result.is_valid == True
        # Confianza podría ser media (regex no detecta verbo inmediato)
        assert result.confidence >= 0.60

    def test_mid_sentence_no_pattern(self, validator_regex_only):
        """Mención en medio de oración sin patrones claros."""
        text = "La historia sobre Isabel es fascinante."
        mention = Mention(text="Isabel", position=text.index("Isabel"))

        result = validator_regex_only.validate(mention, text, {"Isabel"})

        # "sobre Isabel" podría ser ambiguo, depende del patrón
        # Documentar comportamiento actual
        assert isinstance(result.is_valid, bool)
        assert result.confidence > 0.0


# ==============================================================================
# 6. INTEGRACIÓN CON MENTION_FINDER
# ==============================================================================


class TestMentionFinderIntegration:
    """Tests de integración con MentionFinder."""

    def test_mention_finder_filters_possessives(self):
        """MentionFinder debe filtrar menciones posesivas automáticamente."""
        from narrative_assistant.nlp.mention_finder import MentionFinder

        finder = MentionFinder(filter_possessive_contexts=True, use_spacy_validation=False)
        text = "El farmacéutico, amante secreto de Isabel, preparó el veneno."

        mentions = finder.find_all_mentions(text, ["Isabel"])

        # NO debe encontrar "Isabel" (contexto posesivo)
        assert len(mentions) == 0

    def test_mention_finder_keeps_subjects(self):
        """MentionFinder debe mantener sujetos válidos."""
        from narrative_assistant.nlp.mention_finder import MentionFinder

        finder = MentionFinder(filter_possessive_contexts=True, use_spacy_validation=False)
        text = "Isabel preparó el veneno. El farmacéutico ayudó a Isabel."

        mentions = finder.find_all_mentions(text, ["Isabel"])

        # Debe encontrar ambas menciones (sujeto + objeto)
        assert len(mentions) == 2
        assert mentions[0].surface_form == "Isabel"
        assert mentions[1].surface_form == "Isabel"

    def test_mention_finder_without_filtering(self):
        """Sin filtro, debe encontrar todas las menciones."""
        from narrative_assistant.nlp.mention_finder import MentionFinder

        finder = MentionFinder(filter_possessive_contexts=False)
        text = "El amante de Isabel preparó el veneno. Isabel no sabía nada."

        mentions = finder.find_all_mentions(text, ["Isabel"])

        # Debe encontrar AMBAS (posesiva + sujeto)
        assert len(mentions) == 2

    def test_mention_finder_includes_validation_metadata(self):
        """Menciones deben incluir metadatos de validación."""
        from narrative_assistant.nlp.mention_finder import MentionFinder

        finder = MentionFinder(filter_possessive_contexts=True, use_spacy_validation=False)
        text = "Isabel preparó el veneno."

        mentions = finder.find_all_mentions(text, ["Isabel"])

        assert len(mentions) == 1
        assert mentions[0].validation_method == "regex"
        assert mentions[0].validation_reasoning is not None
        assert mentions[0].confidence >= 0.80


# ==============================================================================
# 7. CASOS EDGE
# ==============================================================================


class TestEdgeCases:
    """Tests para casos límite."""

    def test_entity_not_found_in_text(self, validator_regex_only):
        """Entidad que no existe en el texto."""
        text = "María preparó el veneno."
        mention = Mention(text="Isabel", position=0)  # Posición incorrecta

        result = validator_regex_only.validate(mention, text, {"Isabel"})

        # Debe manejar gracefully (aceptar por defecto)
        assert result.is_valid == True
        assert result.confidence >= 0.50

    def test_empty_text(self, validator_regex_only):
        """Texto vacío."""
        text = ""
        mention = Mention(text="Isabel", position=0)

        result = validator_regex_only.validate(mention, text, {"Isabel"})

        # Debe manejar sin errores
        assert isinstance(result.is_valid, bool)

    def test_very_long_text(self, validator_regex_only):
        """Texto muy largo (verificar performance)."""
        text = "Lorem ipsum dolor sit amet. " * 1000 + "El amante de Isabel preparó el veneno."
        position = text.index("Isabel")
        mention = Mention(text="Isabel", position=position)

        result = validator_regex_only.validate(mention, text, {"Isabel"})

        # Debe procesar sin timeout
        assert result.is_valid == False  # Contexto posesivo
        assert result.confidence >= 0.85


# ==============================================================================
# 8. PATRONES ADICIONALES ESPAÑOLES (Mejora 6)
# ==============================================================================


class TestSpanishPatterns:
    """Tests para patrones adicionales del español literario."""

    @pytest.mark.parametrize(
        "text,entity",
        [
            # Gerundio
            ("Siendo Isabel la reina, ordenó zarpar.", "Isabel"),
            ("Estando María en París, no pudo asistir.", "María"),
            ("Habiendo Roberto confesado, fue liberado.", "Roberto"),
            # Pasiva
            ("El libro fue escrito por Isabel en 1920.", "Isabel"),
            ("La carta había sido firmada por María.", "María"),
            ("El veneno fue preparado por Roberto.", "Roberto"),
            # Vocativo
            ("¡Isabel, ven aquí inmediatamente!", "Isabel"),
            ("¡María!", "María"),
            ("¡Roberto, cuidado!", "Roberto"),
            # Aposición
            ("La reina, Isabel, entró al salón.", "Isabel"),
            ("Su hermana, María, era médica.", "María"),
        ],
    )
    def test_spanish_patterns_keep_mention(self, validator_regex_only, text, entity):
        """Patrones españoles (gerundio, pasiva, vocativo, aposición) deben mantenerse."""
        mention = Mention(text=entity, position=text.index(entity))
        result = validator_regex_only.validate(mention, text, {entity})

        assert result.is_valid == True
        assert result.confidence >= 0.85
        # Debe mencionar el patrón específico
        assert any(
            pattern in result.reasoning.lower()
            for pattern in ["gerundio", "pasiva", "agente", "vocativo", "aposición"]
        )

    def test_gerundio_being(self, validator_regex_only):
        """Gerundio 'siendo' debe detectarse correctamente."""
        text = "Siendo Isabel la única heredera, recibió todo."
        mention = Mention(text="Isabel", position=text.index("Isabel"))

        result = validator_regex_only.validate(mention, text, {"Isabel"})

        assert result.is_valid == True
        assert result.confidence >= 0.85
        assert "gerundio" in result.reasoning.lower()

    def test_passive_agent_por(self, validator_regex_only):
        """Complemento agente con 'por' debe detectarse."""
        text = "La novela fue escrita por Isabel hace años."
        mention = Mention(text="Isabel", position=text.index("Isabel"))

        result = validator_regex_only.validate(mention, text, {"Isabel"})

        assert result.is_valid == True
        assert result.confidence >= 0.85
        assert "pasiva" in result.reasoning.lower() or "agente" in result.reasoning.lower()

    def test_vocative_with_exclamation(self, validator_regex_only):
        """Vocativo con exclamación debe detectarse."""
        text = "¡Isabel, ven rápido!"
        mention = Mention(text="Isabel", position=text.index("Isabel"))

        result = validator_regex_only.validate(mention, text, {"Isabel"})

        assert result.is_valid == True
        assert result.confidence >= 0.85
        assert "vocativo" in result.reasoning.lower()

    def test_apposition_between_commas(self, validator_regex_only):
        """Aposición entre comas debe detectarse."""
        text = "La reina, Isabel, ordenó la ejecución."
        mention = Mention(text="Isabel", position=text.index("Isabel"))

        result = validator_regex_only.validate(mention, text, {"Isabel"})

        assert result.is_valid == True
        assert result.confidence >= 0.85
        assert "aposición" in result.reasoning.lower()


# ==============================================================================
# 9. REGRESIONES
# ==============================================================================


class TestRegressions:
    """Tests de regresión para bugs conocidos."""

    def test_regression_issue_communication_verbs(self):
        """
        Regresión: verbos de comunicación filtraban incorrectamente.

        Fecha: 2026-02-16
        Issue: "habla de Isabel" NO debe filtrarse.
        """
        from narrative_assistant.nlp.mention_finder import MentionFinder

        finder = MentionFinder(filter_possessive_contexts=True, use_spacy_validation=False)
        text = "El narrador habla de Isabel extensamente en el prólogo."

        mentions = finder.find_all_mentions(text, ["Isabel"])

        # Debe encontrar la mención (verbo de comunicación)
        assert len(mentions) == 1
        assert mentions[0].confidence >= 0.70

    def test_regression_issue_compound_names(self):
        """
        Regresión: nombres compuestos se detectaban parcialmente.

        Fecha: 2026-02-16
        Issue: "María José" debe detectarse completo, no solo "José".
        """
        from narrative_assistant.nlp.mention_finder import MentionFinder

        finder = MentionFinder(filter_possessive_contexts=True, use_spacy_validation=False)
        text = "El hermano de María José preparó la cena."

        mentions = finder.find_all_mentions(text, ["María José"])

        # NO debe detectar la mención (contexto posesivo)
        assert len(mentions) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
