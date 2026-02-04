"""
Tests para el CESPAttributeResolver.

Verifica que la arquitectura CESP:
1. Prioriza evidencia sintáctica (genitivo, nsubj) sobre proximidad
2. Elimina falsos positivos en deduplicación
3. Resuelve conflictos correctamente
"""

import pytest

from narrative_assistant.nlp.cesp_resolver import (
    CONFIDENCE_GENITIVE,
    CONFIDENCE_PROXIMITY_MAX,
    AssignmentSource,
    AttributeCandidate,
    AttributeDeduplicator,
    CESPAttributeResolver,
    ConflictResolver,
    ConflictStatus,
    EntityMention,
    ExtractorType,
)


class TestAttributeDeduplicator:
    """Tests para el deduplicador de atributos."""

    def test_elimina_falso_positivo_ojos_azules_de_pedro(self):
        """
        CASO CRÍTICO: "ojos azules de Pedro"

        Si el DependencyExtractor asigna a Pedro (genitivo, conf=0.92)
        y el RegexExtractor asigna a Juan (proximidad, conf=0.65)

        El deduplicador DEBE:
        - Conservar solo Pedro (mayor prioridad por genitivo)
        - Eliminar Juan (falso positivo)
        """
        from narrative_assistant.nlp.cesp_resolver import ResolvedAttribute

        deduplicator = AttributeDeduplicator()

        # Simular atributos resueltos
        pedro_attr = ResolvedAttribute(
            attribute_type="color_ojos",
            value="azules",
            entity_id="pedro_1",
            final_confidence=0.92,
            conflict_status=ConflictStatus.CONFIRMED,
            assignment_source=AssignmentSource.GENITIVE,
            is_dubious=False,
            text_evidence="Pedro tenía los ojos azules de Pedro.",
            sentence_idx=0,
            resolution_notes=[],
        )

        juan_attr = ResolvedAttribute(
            attribute_type="color_ojos",
            value="azules",
            entity_id="juan_1",
            final_confidence=0.65,
            conflict_status=ConflictStatus.UNANIMOUS,
            assignment_source=AssignmentSource.PROXIMITY,
            is_dubious=True,
            text_evidence="Pedro tenía los ojos azules de Pedro.",
            sentence_idx=0,
            resolution_notes=[],
        )

        # Deduplicar
        result = deduplicator.deduplicate([pedro_attr, juan_attr])

        # Verificar
        assert len(result) == 1, "Debe haber solo 1 atributo después de deduplicar"
        assert result[0].entity_id == "pedro_1", "Debe conservar Pedro (genitivo)"
        assert result[0].assignment_source == AssignmentSource.GENITIVE

    def test_conserva_atributos_diferentes_entidades_diferentes_oraciones(self):
        """
        Si Pedro tiene ojos azules en oración 1 y María tiene ojos verdes en oración 2,
        AMBOS deben conservarse (son atributos diferentes).
        """
        from narrative_assistant.nlp.cesp_resolver import ResolvedAttribute

        deduplicator = AttributeDeduplicator()

        pedro_attr = ResolvedAttribute(
            attribute_type="color_ojos",
            value="azules",
            entity_id="pedro_1",
            final_confidence=0.92,
            conflict_status=ConflictStatus.CONFIRMED,
            assignment_source=AssignmentSource.GENITIVE,
            is_dubious=False,
            text_evidence="Pedro tiene los ojos azules.",
            sentence_idx=0,
            resolution_notes=[],
        )

        maria_attr = ResolvedAttribute(
            attribute_type="color_ojos",
            value="verdes",
            entity_id="maria_1",
            final_confidence=0.90,
            conflict_status=ConflictStatus.CONFIRMED,
            assignment_source=AssignmentSource.EXPLICIT_SUBJECT,
            is_dubious=False,
            text_evidence="María tiene los ojos verdes.",
            sentence_idx=1,
            resolution_notes=[],
        )

        result = deduplicator.deduplicate([pedro_attr, maria_attr])

        assert len(result) == 2, "Ambos atributos deben conservarse"
        entity_ids = {r.entity_id for r in result}
        assert entity_ids == {"pedro_1", "maria_1"}


class TestConflictResolver:
    """Tests para el resolutor de conflictos."""

    def test_confirmed_con_evidencia_sintactica(self):
        """
        Si hay un candidato con evidencia sintáctica (genitivo/nsubj),
        debe clasificarse como CONFIRMED.
        """
        resolver = ConflictResolver()

        candidates = [
            AttributeCandidate(
                attribute_type="color_ojos",
                value="azules",
                text_evidence="ojos azules de Pedro",
                sentence_idx=0,
                start=0,
                end=20,
                extractor_type=ExtractorType.DEPENDENCY,
                assigned_entity_id="pedro_1",
                assignment_source=AssignmentSource.GENITIVE,
                base_confidence=0.92,
                syntactic_evidence="nmod:de->Pedro",
                is_dubious=False,
            ),
            AttributeCandidate(
                attribute_type="color_ojos",
                value="azules",
                text_evidence="ojos azules de Pedro",
                sentence_idx=0,
                start=0,
                end=20,
                extractor_type=ExtractorType.REGEX,
                assigned_entity_id="juan_1",  # Asignación incorrecta por proximidad
                assignment_source=AssignmentSource.PROXIMITY,
                base_confidence=0.65,
                syntactic_evidence=None,
                is_dubious=True,
            ),
        ]

        status = resolver.classify_conflict_status(candidates)
        assert status == ConflictStatus.CONFIRMED

    def test_unanimous_todos_coinciden(self):
        """
        Si todos los candidatos apuntan a la misma entidad,
        debe clasificarse como UNANIMOUS.
        """
        resolver = ConflictResolver()

        candidates = [
            AttributeCandidate(
                attribute_type="color_ojos",
                value="azules",
                text_evidence="María tiene ojos azules",
                sentence_idx=0,
                start=0,
                end=25,
                extractor_type=ExtractorType.DEPENDENCY,
                assigned_entity_id="maria_1",
                assignment_source=AssignmentSource.IMPLICIT_SUBJECT,
                base_confidence=0.78,
                is_dubious=True,
            ),
            AttributeCandidate(
                attribute_type="color_ojos",
                value="azules",
                text_evidence="María tiene ojos azules",
                sentence_idx=0,
                start=15,
                end=25,
                extractor_type=ExtractorType.REGEX,
                assigned_entity_id="maria_1",
                assignment_source=AssignmentSource.PROXIMITY,
                base_confidence=0.70,
                is_dubious=True,
            ),
        ]

        status = resolver.classify_conflict_status(candidates)
        assert status == ConflictStatus.UNANIMOUS

    def test_conflict_entidades_diferentes(self):
        """
        Si hay candidatos apuntando a entidades diferentes sin evidencia
        sintáctica fuerte, debe clasificarse como CONFLICT.
        """
        resolver = ConflictResolver()

        candidates = [
            AttributeCandidate(
                attribute_type="color_ojos",
                value="azules",
                text_evidence="test",
                sentence_idx=0,
                start=0,
                end=10,
                extractor_type=ExtractorType.REGEX,
                assigned_entity_id="pedro_1",
                assignment_source=AssignmentSource.PROXIMITY,
                base_confidence=0.65,
                is_dubious=True,
            ),
            AttributeCandidate(
                attribute_type="color_ojos",
                value="azules",
                text_evidence="test",
                sentence_idx=0,
                start=0,
                end=10,
                extractor_type=ExtractorType.EMBEDDINGS,
                assigned_entity_id="juan_1",
                assignment_source=AssignmentSource.PROXIMITY,
                base_confidence=0.60,
                is_dubious=True,
            ),
        ]

        status = resolver.classify_conflict_status(candidates)
        assert status == ConflictStatus.CONFLICT


class TestCESPAttributeResolver:
    """Tests de integración para el resolutor CESP completo."""

    def test_caso_ojos_azules_de_pedro(self):
        """
        CASO PRINCIPAL: "Juan miró a Pedro. Tenía los ojos azules de Pedro."

        El sistema DEBE asignar "ojos azules" a Pedro, NO a Juan.
        """
        resolver = CESPAttributeResolver()

        entity_mentions = [
            EntityMention(entity_id="juan_1", text="Juan", start=0, end=4, sentence_idx=0),
            EntityMention(entity_id="pedro_1", text="Pedro", start=14, end=19, sentence_idx=0),
        ]

        # Simular candidatos de múltiples extractores
        candidates = [
            # DependencyExtractor: detecta el genitivo "de Pedro"
            AttributeCandidate(
                attribute_type="color_ojos",
                value="azules",
                text_evidence="Tenía los ojos azules de Pedro.",
                sentence_idx=1,
                start=32,
                end=52,
                extractor_type=ExtractorType.DEPENDENCY,
                assigned_entity_id="pedro_1",
                assignment_source=AssignmentSource.GENITIVE,
                base_confidence=CONFIDENCE_GENITIVE,
                syntactic_evidence="nmod:de->Pedro",
                is_dubious=False,
            ),
            # RegexExtractor: asigna por proximidad (incorrectamente a Juan)
            AttributeCandidate(
                attribute_type="color_ojos",
                value="azules",
                text_evidence="Tenía los ojos azules de Pedro.",
                sentence_idx=1,
                start=32,
                end=52,
                extractor_type=ExtractorType.REGEX,
                assigned_entity_id="juan_1",  # Asignación incorrecta
                assignment_source=AssignmentSource.PROXIMITY,
                base_confidence=0.65,
                syntactic_evidence=None,
                is_dubious=True,
            ),
        ]

        text = "Juan miró a Pedro. Tenía los ojos azules de Pedro."

        results = resolver.resolve(candidates, entity_mentions, text)

        # VERIFICACIONES
        assert len(results) == 1, "Solo debe haber 1 atributo (deduplicado)"
        assert results[0].entity_id == "pedro_1", "Debe asignarse a Pedro"
        assert results[0].attribute_type == "color_ojos"
        assert results[0].value == "azules"
        assert results[0].assignment_source == AssignmentSource.GENITIVE
        assert results[0].final_confidence >= 0.90

    def test_caso_ojos_azules_con_juan(self):
        """
        CASO: "Pedro miraba con sus ojos azules. Juan estaba nervioso."

        Los ojos azules pertenecen a Pedro (sujeto de la oración).
        Juan no tiene relación con los ojos.
        """
        resolver = CESPAttributeResolver()

        entity_mentions = [
            EntityMention(entity_id="pedro_1", text="Pedro", start=0, end=5, sentence_idx=0),
            EntityMention(entity_id="juan_1", text="Juan", start=38, end=42, sentence_idx=1),
        ]

        candidates = [
            AttributeCandidate(
                attribute_type="color_ojos",
                value="azules",
                text_evidence="Pedro miraba con sus ojos azules.",
                sentence_idx=0,
                start=21,
                end=33,
                extractor_type=ExtractorType.DEPENDENCY,
                assigned_entity_id="pedro_1",
                assignment_source=AssignmentSource.EXPLICIT_SUBJECT,
                base_confidence=0.92,
                syntactic_evidence="nsubj:Pedro->miraba",
                is_dubious=False,
            )
        ]

        text = "Pedro miraba con sus ojos azules. Juan estaba nervioso."

        results = resolver.resolve(candidates, entity_mentions, text)

        assert len(results) == 1
        assert results[0].entity_id == "pedro_1"
        assert results[0].attribute_type == "color_ojos"

    def test_asignacion_por_proximidad_sin_conflicto(self):
        """
        Si solo hay candidatos de proximidad y no hay conflicto,
        se acepta la asignación.
        """
        resolver = CESPAttributeResolver()

        entity_mentions = [
            EntityMention(entity_id="maria_1", text="María", start=0, end=5, sentence_idx=0)
        ]

        candidates = [
            AttributeCandidate(
                attribute_type="altura",
                value="alta",
                text_evidence="María es muy alta.",
                sentence_idx=0,
                start=13,
                end=17,
                extractor_type=ExtractorType.REGEX,
                assigned_entity_id="maria_1",
                assignment_source=AssignmentSource.PROXIMITY,
                base_confidence=0.68,
                is_dubious=True,
            )
        ]

        text = "María es muy alta."

        results = resolver.resolve(candidates, entity_mentions, text)

        assert len(results) == 1
        assert results[0].entity_id == "maria_1"
        assert results[0].is_dubious  # Proximidad siempre es dudosa

    def test_estadisticas(self):
        """Test del método de estadísticas."""
        from narrative_assistant.nlp.cesp_resolver import ResolvedAttribute

        resolver = CESPAttributeResolver()

        results = [
            ResolvedAttribute(
                attribute_type="color_ojos",
                value="azules",
                entity_id="pedro_1",
                final_confidence=0.92,
                conflict_status=ConflictStatus.CONFIRMED,
                assignment_source=AssignmentSource.GENITIVE,
                is_dubious=False,
                resolution_notes=[],
            ),
            ResolvedAttribute(
                attribute_type="altura",
                value="alto",
                entity_id="pedro_1",
                final_confidence=0.65,
                conflict_status=ConflictStatus.UNANIMOUS,
                assignment_source=AssignmentSource.PROXIMITY,
                is_dubious=True,
                resolution_notes=[],
            ),
        ]

        stats = resolver.get_statistics(results)

        assert stats["total"] == 2
        assert stats["dubious_count"] == 1
        assert stats["by_source"]["genitive"] == 1
        assert stats["by_source"]["proximity"] == 1


class TestIntegracionCasoReal:
    """
    Tests de integración que simulan el caso real del bug original.
    """

    def test_juan_detecta_azules_y_marrones(self):
        """
        CASO DEL BUG ORIGINAL:

        Texto: "Juan tenía los ojos marrones. Pedro, con sus ojos azules de Pedro, lo miraba."

        ESPERADO:
        - Juan: ojos marrones (sujeto explícito)
        - Pedro: ojos azules (genitivo "de Pedro")

        BUG ANTERIOR: Juan recibía también ojos azules por proximidad
        """
        resolver = CESPAttributeResolver()

        entity_mentions = [
            EntityMention(entity_id="juan_1", text="Juan", start=0, end=4, sentence_idx=0),
            EntityMention(entity_id="pedro_1", text="Pedro", start=30, end=35, sentence_idx=1),
        ]

        candidates = [
            # Ojos marrones de Juan (DependencyExtractor)
            AttributeCandidate(
                attribute_type="color_ojos",
                value="marrones",
                text_evidence="Juan tenía los ojos marrones.",
                sentence_idx=0,
                start=15,
                end=28,
                extractor_type=ExtractorType.DEPENDENCY,
                assigned_entity_id="juan_1",
                assignment_source=AssignmentSource.EXPLICIT_SUBJECT,
                base_confidence=0.92,
                syntactic_evidence="nsubj:Juan->tenía",
                is_dubious=False,
            ),
            # Ojos azules de Pedro (DependencyExtractor - genitivo)
            AttributeCandidate(
                attribute_type="color_ojos",
                value="azules",
                text_evidence="Pedro, con sus ojos azules de Pedro, lo miraba.",
                sentence_idx=1,
                start=46,
                end=66,
                extractor_type=ExtractorType.DEPENDENCY,
                assigned_entity_id="pedro_1",
                assignment_source=AssignmentSource.GENITIVE,
                base_confidence=0.92,
                syntactic_evidence="nmod:de->Pedro",
                is_dubious=False,
            ),
            # BUG: RegexExtractor asigna azules a Juan por proximidad
            AttributeCandidate(
                attribute_type="color_ojos",
                value="azules",
                text_evidence="Pedro, con sus ojos azules de Pedro, lo miraba.",
                sentence_idx=1,
                start=46,
                end=66,
                extractor_type=ExtractorType.REGEX,
                assigned_entity_id="juan_1",  # INCORRECTO
                assignment_source=AssignmentSource.PROXIMITY,
                base_confidence=0.65,
                syntactic_evidence=None,
                is_dubious=True,
            ),
        ]

        text = "Juan tenía los ojos marrones. Pedro, con sus ojos azules de Pedro, lo miraba."

        results = resolver.resolve(candidates, entity_mentions, text)

        # VERIFICAR CORRECCIÓN DEL BUG
        # Debe haber exactamente 2 atributos: marrones para Juan, azules para Pedro
        assert len(results) == 2, f"Esperado 2 atributos, obtenido {len(results)}"

        # Buscar atributos por entidad
        juan_attrs = [r for r in results if r.entity_id == "juan_1"]
        pedro_attrs = [r for r in results if r.entity_id == "pedro_1"]

        # Juan solo tiene ojos marrones
        assert len(juan_attrs) == 1, "Juan debe tener exactamente 1 atributo"
        assert juan_attrs[0].value == "marrones", "Juan debe tener ojos marrones"

        # Pedro tiene ojos azules
        assert len(pedro_attrs) == 1, "Pedro debe tener exactamente 1 atributo"
        assert pedro_attrs[0].value == "azules", "Pedro debe tener ojos azules"

        # Verificar que NO hay falso positivo
        juan_azules = [r for r in results if r.entity_id == "juan_1" and r.value == "azules"]
        assert len(juan_azules) == 0, "BUG: Juan no debe tener ojos azules"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
