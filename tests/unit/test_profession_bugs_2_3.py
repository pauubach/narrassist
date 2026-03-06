"""
Tests de regresión para Bugs #2 y #3 - Extracción errónea de profesiones.

Bug #2: "médico" asignado como profesión de Isabel cuando en realidad
        "El médico forense" es el sujeto (otra persona distinta).

Bug #3: "exactamente" detectado como profesión cuando es un adverbio.
"""

import pytest

from narrative_assistant.nlp.attributes import AttributeExtractor, AttributeKey


class TestProfessionBug2MedicoIsabel:
    """
    Bug #2: "médico" se asigna erróneamente a Isabel.

    Frase problemática:
    "El médico forense determinó que Isabel había muerto por envenenamiento..."

    Problema: El patrón "médico" captura la profesión, pero el scope resolver
    asigna el atributo a "Isabel" (el objeto de la oración) en vez de al sujeto
    "médico forense" (que no está reconocido como entidad).

    Solución esperada: NO asignar "médico" a Isabel. Opciones:
    1. Detectar que "médico" está dentro de un NP sujeto y no es un predicado nominal
    2. Solo asignar profesiones cuando hay verbo copulativo ("era/es/fue X")
    3. Validar que la profesión esté después del nombre, no antes
    """

    def test_medico_forense_not_assigned_to_isabel(self):
        """
        "El médico forense determinó..." NO debe asignar médico a Isabel.
        """
        text = (
            "El médico forense determinó que Isabel había muerto por "
            "envenenamiento con belladona al menos cinco días antes de ser encontrada."
        )

        # Simular menciones de entidades detectadas
        entity_mentions = [
            ("Isabel", 32, 38, "PERSON"),  # Isabel aparece en posición 32
        ]

        extractor = AttributeExtractor()
        result = extractor.extract_attributes(
            text=text,
            entity_mentions=entity_mentions,
            chapter_id=1,
        )

        assert result.is_success

        # result.value es AttributeExtractionResult con campo 'attributes'
        attributes = result.value.attributes

        # Filtrar solo atributos de profesión para Isabel
        isabel_professions = [
            attr for attr in attributes
            if attr.entity_name == "Isabel" and attr.key == AttributeKey.PROFESSION
        ]

        # NO debe haber asignado "médico" a Isabel
        assert len(isabel_professions) == 0, (
            f"Se asignó erróneamente profesión a Isabel: {isabel_professions}"
        )

    def test_copulative_profession_is_correctly_assigned(self):
        """
        Las profesiones con verbo copulativo SÍ deben asignarse correctamente.
        """
        text = "Isabel era médico forense en el hospital municipal."

        entity_mentions = [
            ("Isabel", 0, 6, "PERSON"),
        ]

        extractor = AttributeExtractor()
        result = extractor.extract_attributes(
            text=text,
            entity_mentions=entity_mentions,
            chapter_id=1,
        )

        assert result.is_success

        # result.value es AttributeExtractionResult con campo 'attributes'
        attributes = result.value.attributes

        # Filtrar profesiones de Isabel
        isabel_professions = [
            attr for attr in attributes
            if attr.entity_name == "Isabel" and attr.key == AttributeKey.PROFESSION
        ]

        # Debe haber detectado "médico" como profesión de Isabel
        assert len(isabel_professions) >= 1, "No detectó la profesión con verbo copulativo"
        assert any(
            "médico" in attr.value.lower() or "forense" in attr.value.lower()
            for attr in isabel_professions
        ), f"Profesión incorrecta: {isabel_professions}"


class TestProfessionBug3ExactamenteAdverb:
    """
    Bug #3: "exactamente" detectado como profesión.

    Frase problemática:
    "La solución... no era otra que... era exactamente aquella respuesta..."

    Problema: El patrón r"[Ee]ra\\s+(?:un\\s+)?(\\w+...mente)\\b" captura "exactamente"
    porque termina en "-mente" (sufijo de profesión en el regex).

    El filtro _is_valid_profession_context debería rechazarlo por:
    - Capa 1 (POS-tag): spaCy debería etiquetar "exactamente" como ADV
    - Capa 2 (-mente): Filtro de adverbios -mente debería rechazarlo
    - Capa 3 (post-match): "exactamente aquella" tiene artículo después
    """

    def test_exactamente_not_detected_as_profession(self):
        """
        "exactamente" NO debe ser detectado como profesión.
        """
        text = (
            "La solución al enigma residía en que la solución al enigma no era otra "
            "que la respuesta al misterio que constituía el enigma cuya solución "
            "buscaban, es decir, la respuesta que resolvería el misterio era "
            "exactamente aquella respuesta que daba solución al enigma planteado "
            "desde el principio de la investigación."
        )

        entity_mentions = [
            ("Isabel", 0, 0, "PERSON"),  # Entidad ficticia para forzar asignación
        ]

        extractor = AttributeExtractor()
        result = extractor.extract_attributes(
            text=text,
            entity_mentions=entity_mentions,
            chapter_id=7,
        )

        assert result.is_success

        # result.value es AttributeExtractionResult con campo 'attributes'
        attributes = result.value.attributes

        # No debe haber detectado "exactamente" como profesión
        exactamente_attrs = [
            attr for attr in attributes
            if "exactamente" in attr.value.lower() and attr.key == AttributeKey.PROFESSION
        ]

        assert len(exactamente_attrs) == 0, (
            f"Se detectó erróneamente 'exactamente' como profesión: {exactamente_attrs}"
        )

    def test_validate_profession_rejects_adverbs_with_mente(self):
        """
        El validador _validate_value debe rechazar adverbios en -mente.
        """
        from narrative_assistant.nlp.attr_entity_resolution import AttributeEntityResolutionMixin

        class DummyExtractor(AttributeEntityResolutionMixin):
            pass

        dummy = DummyExtractor()

        # Adverbios en -mente deben ser rechazados
        assert not dummy._validate_value(AttributeKey.PROFESSION, "exactamente")
        assert not dummy._validate_value(AttributeKey.PROFESSION, "solamente")
        assert not dummy._validate_value(AttributeKey.PROFESSION, "simplemente")
        assert not dummy._validate_value(AttributeKey.PROFESSION, "realmente")

        # Profesiones legítimas deben pasar
        assert dummy._validate_value(AttributeKey.PROFESSION, "médico")
        assert dummy._validate_value(AttributeKey.PROFESSION, "carpintero")
        assert dummy._validate_value(AttributeKey.PROFESSION, "ingeniera")

    def test_pos_tag_gating_rejects_adverbs(self):
        """
        La capa 1 de POS-tag gating debe rechazar ADV antes del regex.
        """
        # Este test requiere spaCy doc, lo verificamos en el test principal
        # (test_exactamente_not_detected_as_profession ya lo cubre)
        pass


class TestAbsenceValueRejection:
    """Valores de ausencia/negación generados por el LLM deben rechazarse."""

    def test_validate_value_rejects_absence_phrases(self):
        from narrative_assistant.nlp.attr_entity_resolution import AttributeEntityResolutionMixin

        class DummyExtractor(AttributeEntityResolutionMixin):
            pass

        dummy = DummyExtractor()

        # Frases de ausencia típicas de alucinación LLM
        assert not dummy._validate_value(AttributeKey.PROFESSION, "nunca se mencionó")
        assert not dummy._validate_value(AttributeKey.PROFESSION, "no se menciona")
        assert not dummy._validate_value(AttributeKey.PROFESSION, "desconocido")
        assert not dummy._validate_value(AttributeKey.PROFESSION, "no especificado")
        assert not dummy._validate_value(AttributeKey.PROFESSION, "sin especificar")
        assert not dummy._validate_value(AttributeKey.PROFESSION, "no aplica")
        assert not dummy._validate_value(AttributeKey.PROFESSION, "no tiene profesión")

        # También para otros tipos de atributo
        assert not dummy._validate_value(AttributeKey.EYE_COLOR, "nunca se mencionó")
        assert not dummy._validate_value(AttributeKey.PERSONALITY, "desconocido")

        # Valores legítimos siguen pasando
        assert dummy._validate_value(AttributeKey.PROFESSION, "médico")
        assert dummy._validate_value(AttributeKey.PROFESSION, "carpintero")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
