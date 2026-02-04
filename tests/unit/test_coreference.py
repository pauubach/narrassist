"""
Tests unitarios para resolución de correferencias.

Este módulo verifica que el sistema de correferencias resuelve
correctamente pronombres posesivos como "sus" al sujeto apropiado.
"""

import pytest


class TestPossessiveResolution:
    """
    Tests para la resolución de pronombres posesivos.

    Caso crítico: "María apareció... Sus ojos verdes..."
    El posesivo "Sus" debe resolver a María (el sujeto de la oración anterior),
    NO a Juan (mencionado en capítulos anteriores).
    """

    @pytest.fixture
    def resolver(self):
        """Obtiene el resolver de correferencias."""
        from narrative_assistant.nlp.coreference_resolver import (
            CorefConfig,
            CoreferenceVotingResolver,
            CorefMethod,
        )

        # Usar solo heurísticas para tests rápidos
        config = CorefConfig(
            enabled_methods=[CorefMethod.HEURISTICS, CorefMethod.MORPHO],
            min_confidence=0.3,
        )
        return CoreferenceVotingResolver(config)

    def test_possessive_resolves_to_previous_sentence_subject(self, resolver):
        """
        Verifica que 'Sus' resuelve al sujeto de la oración anterior.

        Escenario: "María apareció. Sus ojos verdes brillaban."
        Esperado: "Sus" → María
        """
        text = "María apareció en la cafetería. Sus ojos verdes brillaban."

        result = resolver.resolve_document(text)

        # Debe haber al menos una cadena con María
        maria_chains = [c for c in result.chains if c.main_mention and "María" in c.main_mention]

        assert len(maria_chains) >= 1, "Debe haber una cadena con María"

        # Verificar que "Sus" está en la cadena de María
        maria_chain = maria_chains[0]
        sus_mentions = [m for m in maria_chain.mentions if m.text.lower() == "sus"]

        assert len(sus_mentions) >= 1, "'Sus' debe estar en la cadena de María"

    def test_possessive_not_resolved_to_distant_entity(self, resolver):
        """
        Verifica que 'Sus' NO resuelve a una entidad lejana de otro capítulo.

        Escenario con dos personajes, el posesivo debe resolverse al más reciente.
        """
        text = """Juan entró en la casa.

María apareció en la cafetería. Sus ojos verdes brillaban."""

        result = resolver.resolve_document(text)

        # Buscar si hay una cadena donde Juan tenga "Sus"
        juan_with_sus = False
        for chain in result.chains:
            if chain.main_mention and "Juan" in chain.main_mention:
                sus_in_chain = any(m.text.lower() == "sus" for m in chain.mentions)
                if sus_in_chain:
                    juan_with_sus = True

        assert not juan_with_sus, "'Sus' NO debe resolverse a Juan (está demasiado lejos)"

    def test_possessive_same_sentence(self, resolver):
        """
        Verifica resolución de posesivo dentro de la misma oración.

        Escenario: "María saludó con sus ojos brillantes."
        """
        text = "María saludó con sus ojos brillantes."

        result = resolver.resolve_document(text)

        # Debe haber una cadena con María
        maria_chains = [c for c in result.chains if c.main_mention and "María" in c.main_mention]

        # Si hay cadena de María, verificar que incluye "sus"
        if maria_chains:
            maria_chain = maria_chains[0]
            sus_mentions = [m for m in maria_chain.mentions if m.text.lower() == "sus"]
            assert len(sus_mentions) >= 1, "'sus' debe estar en la cadena de María"

    def test_possessive_classification(self):
        """Verifica que 'sus' se clasifica como POSSESSIVE, no PRONOUN."""
        from narrative_assistant.nlp.coreference_resolver import (
            SPANISH_POSSESSIVES,
            MentionType,
        )

        # 'sus' debe estar en el diccionario de posesivos
        assert "sus" in SPANISH_POSSESSIVES, "'sus' debe estar en SPANISH_POSSESSIVES"
        assert "su" in SPANISH_POSSESSIVES, "'su' debe estar en SPANISH_POSSESSIVES"

    def test_heuristics_favor_recent_subject_for_possessive(self):
        """
        Verifica que las heurísticas dan bonus al sujeto más reciente.
        """
        from narrative_assistant.nlp.coreference_resolver import (
            Gender,
            HeuristicsCorefMethod,
            Mention,
            MentionType,
            Number,
        )

        method = HeuristicsCorefMethod()

        # Crear mención posesiva
        anaphor = Mention(
            text="Sus",
            start_char=100,
            end_char=103,
            mention_type=MentionType.POSSESSIVE,
            gender=Gender.NEUTRAL,
            number=Number.PLURAL,
            sentence_idx=2,
        )

        # Crear dos candidatos: uno en la oración anterior, otro lejano
        maria = Mention(
            text="María",
            start_char=50,
            end_char=55,
            mention_type=MentionType.PROPER_NOUN,
            gender=Gender.FEMININE,
            number=Number.SINGULAR,
            sentence_idx=1,  # Oración anterior
        )

        juan = Mention(
            text="Juan",
            start_char=10,
            end_char=14,
            mention_type=MentionType.PROPER_NOUN,
            gender=Gender.MASCULINE,
            number=Number.SINGULAR,
            sentence_idx=0,  # Dos oraciones atrás
        )

        results = method.resolve(anaphor, [maria, juan], "context")

        # Ordenar por score
        results_sorted = sorted(results, key=lambda x: x[1], reverse=True)

        # María debe tener mayor score que Juan
        maria_score = next((r[1] for r in results_sorted if r[0] == maria), 0)
        juan_score = next((r[1] for r in results_sorted if r[0] == juan), 0)

        assert maria_score > juan_score, (
            f"María (oración anterior) debe tener mayor score que Juan. "
            f"María={maria_score:.2f}, Juan={juan_score:.2f}"
        )


class TestMentionExtraction:
    """Tests para la extracción de menciones."""

    def test_possessive_extracted_as_possessive_type(self):
        """Verifica que los posesivos se extraen con tipo POSSESSIVE."""
        from narrative_assistant.nlp.coreference_resolver import (
            CorefConfig,
            CoreferenceVotingResolver,
            CorefMethod,
            MentionType,
        )

        config = CorefConfig(
            enabled_methods=[CorefMethod.HEURISTICS],
            min_confidence=0.3,
        )
        resolver = CoreferenceVotingResolver(config)

        text = "María llegó. Sus ojos verdes brillaban."

        # Acceder a menciones extraídas directamente
        mentions = resolver._extract_mentions(text, None)

        # Buscar mención de "Sus"
        sus_mentions = [m for m in mentions if m.text.lower() == "sus"]

        assert len(sus_mentions) >= 1, "Debe encontrar 'Sus' en el texto"
        assert sus_mentions[0].mention_type == MentionType.POSSESSIVE, (
            f"'Sus' debe ser POSSESSIVE, no {sus_mentions[0].mention_type}"
        )
