"""
Test de integración: flujo completo de atributos ambiguos.

Verifica el flujo end-to-end desde la detección de ambigüedad en scope_resolver
hasta la creación de alertas interactivas para resolución del usuario.
"""

import pytest

from narrative_assistant.alerts.models import AlertCategory, AlertSeverity, AlertStatus
from narrative_assistant.nlp.scope_resolver import AmbiguousResult


class TestAmbiguousAttributeFlow:
    """Test end-to-end del flujo de atributos ambiguos."""

    def test_scope_resolver_returns_ambiguous_result(self, shared_spacy_nlp):
        """
        Test básico: Scope resolver detecta correctamente la ambigüedad
        y retorna AmbiguousResult en lugar de None o una asignación incorrecta.
        """
        from narrative_assistant.nlp.scope_resolver import ScopeResolver

        text = "Cuando Juan conoció a María tenía los ojos azules."
        doc = shared_spacy_nlp(text)

        # Crear menciones mock
        entity_mentions = [
            {"entity_name": "Juan", "start": 7, "end": 11, "entity_type": "PER"},
            {"entity_name": "María", "start": 22, "end": 27, "entity_type": "PER"},
        ]

        resolver = ScopeResolver(nlp=shared_spacy_nlp)

        # Posición de "ojos azules" (~38-49)
        # Debe detectar ambigüedad: ¿de Juan o de María?
        result = resolver.find_nearest_entity_by_scope(
            position=38,
            entity_mentions=entity_mentions,
            prefer_subject=True,
        )

        # Verificar que retorna AmbiguousResult
        assert isinstance(result, AmbiguousResult), (
            f"Debe retornar AmbiguousResult para texto ambiguo. Got: {result}"
        )
        assert set(result.candidates) == {"Juan", "María"}
        assert "ojos azules" in result.context_text.lower()

    def test_ambiguous_result_propagates_through_attribute_extraction(
        self, shared_spacy_nlp, shared_attribute_extractor
    ):
        """
        Test de integración: AmbiguousResult se propaga correctamente
        a través del AttributeExtractor sin asignación fallida.
        """
        text = "Juan le dijo a María que tenía el pelo sucio."

        # Menciones mock
        entity_mentions = [
            {"entity_name": "Juan", "start": 0, "end": 4, "entity_type": "PER"},
            {"entity_name": "María", "start": 15, "end": 20, "entity_type": "PER"},
        ]

        # Extraer atributos (debe detectar ambigüedad)
        attr_result = shared_attribute_extractor.extract_attributes(
            text=text,
            entity_mentions=entity_mentions,
        )

        # Verificar que NO se asignó el atributo incorrectamente
        # (debe estar en ambiguous_attributes, no en attributes)
        hair_attrs = [a for a in attr_result.attributes if "hair" in a.attribute_key]
        assert len(hair_attrs) == 0, (
            f"No debe asignar atributo ambiguo. Attributes asignados: {hair_attrs}"
        )

        # Verificar que se colectó en ambiguous_attributes
        assert hasattr(attr_result, "ambiguous_attributes"), (
            "AttributeExtractionResult debe tener campo ambiguous_attributes"
        )
        assert len(attr_result.ambiguous_attributes) >= 1, (
            f"Debe colectar atributo ambiguo. Encontrados: {len(attr_result.ambiguous_attributes)}"
        )

        ambig_attr = attr_result.ambiguous_attributes[0]
        assert "hair" in ambig_attr.attribute_key or "pelo" in ambig_attr.source_text.lower()
        assert set(ambig_attr.candidates) == {"Juan", "María"}

    def test_alert_creation_from_ambiguous_attribute(self):
        """
        Test unitario: Verificar que el alert engine crea correctamente
        alertas de tipo ambiguous_attribute con la estructura esperada.
        """
        from narrative_assistant.alerts.engine import get_alert_engine

        engine = get_alert_engine()

        # Simular candidatos con entity_id
        candidates = [
            {"entity_name": "Juan", "entity_id": 1},
            {"entity_name": "María", "entity_id": 2},
        ]

        # Crear alerta de atributo ambiguo
        alert_result = engine.create_from_ambiguous_attribute(
            project_id=999,
            attribute_key="eye_color",
            attribute_value="azules",
            candidates=candidates,
            source_text="Cuando Juan conoció a María tenía los ojos azules.",
            chapter=1,
            start_char=38,
            end_char=49,
        )

        assert alert_result.is_success, f"Failed to create alert: {alert_result.error}"
        alert = alert_result.value

        # Verificar estructura básica
        assert alert.project_id == 999
        assert alert.category == AlertCategory.CONSISTENCY
        assert alert.severity == AlertSeverity.WARNING
        assert alert.alert_type == "ambiguous_attribute"
        assert alert.status == AlertStatus.NEW

        # Verificar mensajes
        assert "color de ojos" in alert.title.lower()
        assert "azules" in alert.description.lower()

        # Verificar extra_data para resolución interactiva
        assert alert.extra_data["attribute_key"] == "eye_color"
        assert alert.extra_data["attribute_value"] == "azules"
        assert len(alert.extra_data["candidates"]) == 2

        # Verificar que los candidatos tienen entity_id (necesario para resolución)
        candidate_ids = {c["entity_id"] for c in alert.extra_data["candidates"]}
        assert candidate_ids == {1, 2}

        # Verificar content_hash (debe ser único y estable)
        assert len(alert.content_hash) == 16
        assert alert.content_hash.isalnum()
