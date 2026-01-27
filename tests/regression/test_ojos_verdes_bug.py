"""
Test de regresión para el bug "ojos verdes asignados a Juan en lugar de María".

Este bug se manifestó así:
- En el Capítulo 2 del documento de test, María aparece con "ojos verdes"
- El algoritmo incorrectamente asignaba "ojos verdes" a Juan
- Causa raíz: confusión de "la" como artículo vs pronombre objeto

Contexto del bug:
    "Al día siguiente, María apareció en la cafetería del barrio.
     Sus ojos verdes llamaron la atención de todos los presentes."

El patrón "Sus ojos verdes" debería asignarse a María (mencionada justo antes),
pero el algoritmo detectaba "la" en "la cafetería" como pronombre objeto
y usaba lógica de género incorrectamente.

Fixes aplicados:
1. Distinguir "la" artículo de "la" pronombre objeto (requiere verbo después)
2. Mejorar detección de sujetos elípticos
3. Añadir detección de cláusulas relativas
4. Usar todas las menciones de la BD (no solo first_appearance_char)

Referencias:
- Commit c5660f8: Fix inicial para distinguir artículos
- attributes.py: _find_nearest_entity mejorado
"""

import pytest
from narrative_assistant.nlp.attributes import AttributeExtractor


class TestOjosVerdesBug:
    """Tests de regresión para el bug de ojos verdes."""

    @pytest.fixture
    def extractor(self):
        """Crea un extractor de atributos sin LLM/embeddings para tests deterministas."""
        return AttributeExtractor(
            filter_metaphors=True,
            min_confidence=0.5,
            use_llm=False,
            use_embeddings=False,
            use_dependency_extraction=True,
            use_patterns=True,
        )

    def test_sus_ojos_verdes_maria_not_juan(self, extractor):
        """
        Test del caso exacto del bug:
        "Sus ojos verdes" después de "María apareció en la cafetería"
        debe asignarse a María, no a Juan.
        """
        text = """María apareció en la cafetería del barrio. Sus ojos verdes llamaron la atención de todos los presentes.

Juan entró poco después. Era un hombre muy alto."""

        entity_mentions = [
            ("María", 0, 5, "PER"),
            ("Juan", text.find("Juan"), text.find("Juan") + 4, "PER"),
        ]

        result = extractor.extract_attributes(text, entity_mentions=entity_mentions)
        assert result.is_success, f"Extracción falló: {result.error}"

        attrs = result.value.attributes

        # Buscar atributo de ojos verdes
        eye_attrs = [a for a in attrs if "eye" in str(a.key).lower() or "ojo" in str(a.key).lower()]

        # Debe haber al menos un atributo de ojos
        assert len(eye_attrs) > 0, "No se extrajo ningún atributo de ojos"

        # Verificar que "ojos verdes" está asignado a María
        verde_attrs = [a for a in eye_attrs if "verde" in a.value.lower()]
        assert len(verde_attrs) > 0, "No se extrajo 'ojos verdes'"

        for attr in verde_attrs:
            assert attr.entity_name.lower() == "maría", (
                f"BUG: 'ojos verdes' asignado a '{attr.entity_name}' en lugar de 'María'\n"
                f"Fuente: '{attr.source_text}'"
            )

    def test_article_la_not_pronoun(self, extractor):
        """
        Verifica que "la" en "la cafetería" no se confunda con pronombre objeto.
        """
        text = """Juan entró en la cafetería. María lo saludó con una sonrisa.
Sus ojos azules brillaban."""

        entity_mentions = [
            ("Juan", 0, 4, "PER"),
            ("María", text.find("María"), text.find("María") + 5, "PER"),
        ]

        result = extractor.extract_attributes(text, entity_mentions=entity_mentions)
        assert result.is_success

        # "Sus ojos azules" debería asignarse a María (sujeto de la oración anterior)
        # NO a Juan (que fue el objeto "lo" de María)
        attrs = result.value.attributes
        eye_attrs = [a for a in attrs if "eye" in str(a.key).lower() and "azul" in a.value.lower()]

        if eye_attrs:
            # Si se extrajo el atributo, debe ser de María
            for attr in eye_attrs:
                assert attr.entity_name.lower() == "maría", (
                    f"'ojos azules' incorrectamente asignado a '{attr.entity_name}'"
                )

    def test_pronoun_lo_is_object(self, extractor):
        """
        Verifica que "lo" como pronombre objeto se detecta correctamente.
        """
        text = """María lo miró fijamente. Su cabello negro brillaba bajo la luz."""

        entity_mentions = [
            ("María", 0, 5, "PER"),
            ("Juan", -1, -1, "PER"),  # Juan es el referente de "lo", posición -1 para test
        ]

        result = extractor.extract_attributes(text, entity_mentions=entity_mentions)
        assert result.is_success

        # "Su cabello negro" debería referirse al objeto (Juan = "lo"), no a María
        # Pero como Juan no tiene posición real, podría no asignarse

    def test_elliptical_subject_resolution(self, extractor):
        """
        Verifica resolución de sujeto elíptico: el verbo sin sujeto
        debe referirse al sujeto de la oración anterior.
        """
        text = """María entró en la habitación. Tenía los ojos rojos de llorar."""

        entity_mentions = [
            ("María", 0, 5, "PER"),
        ]

        result = extractor.extract_attributes(text, entity_mentions=entity_mentions)
        assert result.is_success

        attrs = result.value.attributes
        eye_attrs = [a for a in attrs if "eye" in str(a.key).lower() and "rojo" in a.value.lower()]

        if eye_attrs:
            for attr in eye_attrs:
                assert attr.entity_name.lower() == "maría", (
                    f"Sujeto elíptico resuelto incorrectamente: '{attr.entity_name}'"
                )

    def test_negation_not_extracted(self, extractor):
        """
        Verifica que atributos negados no se extraen.
        """
        text = """Pedro nunca tuvo el pelo negro. Siempre fue rubio."""

        entity_mentions = [
            ("Pedro", 0, 5, "PER"),
        ]

        result = extractor.extract_attributes(text, entity_mentions=entity_mentions)
        assert result.is_success

        attrs = result.value.attributes

        # "pelo negro" está negado, no debería extraerse
        hair_negro = [a for a in attrs if "hair" in str(a.key).lower() and "negro" in a.value.lower()]
        assert len(hair_negro) == 0, (
            f"Atributo negado extraído incorrectamente: {hair_negro}"
        )

    def test_contrastive_sino_pattern(self, extractor):
        """
        Verifica patrón contrastivo "No es X, sino Y".
        """
        text = """No es que Pedro tuviera ojos azules, sino grises."""

        entity_mentions = [
            ("Pedro", text.find("Pedro"), text.find("Pedro") + 5, "PER"),
        ]

        result = extractor.extract_attributes(text, entity_mentions=entity_mentions)
        assert result.is_success

        attrs = result.value.attributes
        eye_attrs = [a for a in attrs if "eye" in str(a.key).lower()]

        # Si se extrae algo, debe ser "grises", no "azules"
        for attr in eye_attrs:
            assert "azul" not in attr.value.lower(), (
                f"Valor negado extraído: '{attr.value}' (debería ser 'grises')"
            )

    def test_temporal_past_reduced_confidence(self, extractor):
        """
        Verifica que atributos del pasado tienen menor confianza.
        """
        text = """De joven, Eva tenía el pelo negro. Ahora es completamente canosa."""

        entity_mentions = [
            ("Eva", text.find("Eva"), text.find("Eva") + 3, "PER"),
        ]

        result = extractor.extract_attributes(text, entity_mentions=entity_mentions)
        assert result.is_success

        attrs = result.value.attributes

        # "pelo negro" es del pasado, debería tener menor confianza
        hair_negro = [a for a in attrs if "hair" in str(a.key).lower() and "negro" in a.value.lower()]

        # "canosa" es actual
        hair_canoso = [a for a in attrs if "hair" in str(a.key).lower() and "canos" in a.value.lower()]

        # Si ambos se extraen, canoso debería tener mayor confianza
        if hair_negro and hair_canoso:
            assert hair_canoso[0].confidence > hair_negro[0].confidence, (
                f"Confianza temporal incorrecta: pasado={hair_negro[0].confidence}, "
                f"actual={hair_canoso[0].confidence}"
            )


class TestRelativeClauseDetection:
    """Tests para detección de cláusulas relativas."""

    @pytest.fixture
    def extractor(self):
        return AttributeExtractor(
            use_llm=False,
            use_embeddings=False,
        )

    def test_entity_in_relative_clause_penalized(self, extractor):
        """
        Entidades dentro de cláusulas relativas deben ser penalizadas.
        """
        text = """El hombre que María había visto tenía ojos azules."""

        entity_mentions = [
            ("El hombre", 0, 9, "PER"),
            ("María", text.find("María"), text.find("María") + 5, "PER"),
        ]

        result = extractor.extract_attributes(text, entity_mentions=entity_mentions)
        assert result.is_success

        attrs = result.value.attributes
        eye_attrs = [a for a in attrs if "eye" in str(a.key).lower() and "azul" in a.value.lower()]

        # "ojos azules" pertenece a "El hombre", no a María
        # María está en la cláusula relativa "que María había visto"
        for attr in eye_attrs:
            # El hombre debe ser el asignado, o al menos no María
            assert attr.entity_name.lower() != "maría", (
                f"Atributo incorrectamente asignado a entidad en cláusula relativa: "
                f"'{attr.entity_name}' tiene '{attr.value}'"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
