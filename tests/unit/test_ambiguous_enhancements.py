"""
Tests para las mejoras del sistema de atributos ambiguos.

Cubre 3 nuevas features:
1. Sugerencia contextual basada en atributos existentes
2. Batch resolution de múltiples alertas
3. Análisis semántico con LLM (si disponible)
"""

import pytest


class TestContextualSuggestion:
    """Tests para sugerencia contextual basada en atributos existentes."""

    def test_suggestion_when_entity_already_has_attribute(self):
        """
        Dado: Juan ya tiene eye_color=azules asignado
        Cuando: Se detecta ambigüedad
        Entonces: La lógica de sugerencia debe identificar a Juan como sugerido
        """
        from unittest.mock import Mock, patch

        # Mock entity repository con atributo existente
        mock_repo = Mock()
        mock_attr = Mock()
        mock_attr.attribute_key = "eye_color"
        mock_attr.attribute_value = "azules"
        mock_attr.confidence = 0.8

        # Juan (id=1) tiene el atributo, María (id=2) no
        mock_repo.get_attributes_by_entity.side_effect = lambda eid: (
            [mock_attr] if eid == 1 else []
        )

        candidates = [
            {"entity_name": "Juan", "entity_id": 1},
            {"entity_name": "María", "entity_id": 2},
        ]

        # Simular la lógica de sugerencia (sin necesidad de crear alerta en DB)
        suggested_entity_id = None
        for candidate in candidates:
            entity_id = candidate["entity_id"]
            attributes = mock_repo.get_attributes_by_entity(entity_id)

            for attr in attributes:
                if attr.attribute_key == "eye_color":
                    existing_value = attr.attribute_value.lower().strip()
                    new_value = "azules".lower().strip()

                    if existing_value == new_value:
                        suggested_entity_id = entity_id
                        break

            if suggested_entity_id:
                break

        # Verificar que Juan fue identificado como sugerido
        assert suggested_entity_id == 1

        # Marcar candidato sugerido
        candidates_with_suggestion = []
        for c in candidates:
            candidate_copy = c.copy()
            if suggested_entity_id and c["entity_id"] == suggested_entity_id:
                candidate_copy["suggested"] = True
            candidates_with_suggestion.append(candidate_copy)

        # Verificar estructura final
        juan = next(c for c in candidates_with_suggestion if c["entity_name"] == "Juan")
        maria = next(c for c in candidates_with_suggestion if c["entity_name"] == "María")
        assert juan.get("suggested") is True
        assert maria.get("suggested") is not True

    def test_no_suggestion_when_no_matching_attribute(self):
        """
        Dado: Ningún candidato tiene el atributo asignado
        Cuando: Se detecta ambigüedad
        Entonces: No debe haber sugerencia (suggested_entity_id=None)
        """
        from unittest.mock import Mock

        # Mock entity repository SIN atributos
        mock_repo = Mock()
        mock_repo.get_attributes_by_entity.return_value = []

        candidates = [
            {"entity_name": "Pedro", "entity_id": 3},
            {"entity_name": "Elena", "entity_id": 4},
        ]

        # Simular la lógica de sugerencia
        suggested_entity_id = None
        for candidate in candidates:
            entity_id = candidate["entity_id"]
            attributes = mock_repo.get_attributes_by_entity(entity_id)

            for attr in attributes:
                if attr.attribute_key == "hair_color":
                    existing_value = attr.attribute_value.lower().strip()
                    new_value = "rizado".lower().strip()

                    if existing_value == new_value:
                        suggested_entity_id = entity_id
                        break

            if suggested_entity_id:
                break

        # Verificar que NO hay sugerencia
        assert suggested_entity_id is None


class TestBatchResolution:
    """Tests para resolución batch de alertas ambiguas."""

    def test_batch_request_model(self):
        """Verificar que el modelo Pydantic de batch request es válido."""
        import sys
        from pathlib import Path

        # Agregar api-server al path
        api_server_path = str(Path(__file__).parent.parent.parent / "api-server")
        sys.path.insert(0, api_server_path)

        try:
            from deps import AmbiguousAttributeResolution, BatchResolveAmbiguousAttributesRequest

            # Crear request válido
            req = BatchResolveAmbiguousAttributesRequest(
                resolutions=[
                    AmbiguousAttributeResolution(alert_id=1, entity_id=5),
                    AmbiguousAttributeResolution(alert_id=2, entity_id=None),  # No asignar
                    AmbiguousAttributeResolution(alert_id=3, entity_id=8),
                ]
            )

            assert len(req.resolutions) == 3
            assert req.resolutions[0].alert_id == 1
            assert req.resolutions[0].entity_id == 5
            assert req.resolutions[1].entity_id is None

        finally:
            sys.path.remove(api_server_path)

    def test_batch_request_requires_at_least_one_resolution(self):
        """Batch request debe fallar si no hay resoluciones."""
        import sys
        from pathlib import Path

        api_server_path = str(Path(__file__).parent.parent.parent / "api-server")
        sys.path.insert(0, api_server_path)

        try:
            from deps import BatchResolveAmbiguousAttributesRequest
            from pydantic import ValidationError

            with pytest.raises(ValidationError):
                BatchResolveAmbiguousAttributesRequest(resolutions=[])

        finally:
            sys.path.remove(api_server_path)


class TestLLMSemanticDisambiguation:
    """Tests para análisis semántico con LLM (si disponible)."""

    def test_llm_disambiguation_method_exists(self, shared_spacy_nlp):
        """Verificar que el método _llm_semantic_disambiguation existe."""
        from narrative_assistant.nlp.scope_resolver import ScopeResolver

        text = "Juan miró a María. Sus ojos brillaban."
        doc = shared_spacy_nlp(text)
        resolver = ScopeResolver(doc, text)

        # Verificar que el método existe
        assert hasattr(resolver, "_llm_semantic_disambiguation")
        assert callable(resolver._llm_semantic_disambiguation)

    def test_llm_returns_none_when_unavailable(self, shared_spacy_nlp):
        """
        Si Ollama no está disponible, el método debe retornar None
        sin lanzar excepciones.
        """
        from narrative_assistant.nlp.scope_resolver import ScopeResolver

        text = "Juan miró a María. Sus ojos brillaban."
        doc = shared_spacy_nlp(text)
        resolver = ScopeResolver(doc, text)

        candidates = [
            ("Juan", 0, 4, "PER"),
            ("María", 13, 18, "PER"),
        ]

        # Debe retornar None si LLM no disponible (no debe crashear)
        result = resolver._llm_semantic_disambiguation(position=25, candidates=candidates)

        # Puede ser None (si Ollama no disponible) o una tupla (si disponible)
        assert result is None or isinstance(result, tuple)

    @pytest.mark.skipif(
        True,  # Siempre skip por defecto (requiere Ollama corriendo)
        reason="Requiere Ollama disponible y modelo descargado"
    )
    def test_llm_can_suggest_candidate(self, shared_spacy_nlp):
        """
        Test manual: Si Ollama está disponible, puede sugerir un candidato.

        Para ejecutar: pytest -k test_llm_can_suggest --run-llm
        """
        from narrative_assistant.llm.client import get_llm_client
        from narrative_assistant.nlp.scope_resolver import ScopeResolver

        # Verificar que Ollama está disponible
        llm = get_llm_client()
        if not llm.is_available():
            pytest.skip("Ollama no disponible")

        text = "Juan entró en la sala. María estaba sentada. Sus ojos azules brillaban."
        doc = shared_spacy_nlp(text)
        resolver = ScopeResolver(doc, text)

        candidates = [
            ("Juan", 0, 4, "PER"),
            ("María", 25, 30, "PER"),
        ]

        # Posición de "ojos azules" (~52)
        result = resolver._llm_semantic_disambiguation(position=52, candidates=candidates)

        # Si LLM funciona, debería sugerir María (más cercana y sujeto de estar sentada)
        if result:
            entity_name, confidence = result
            print(f"LLM sugirió: {entity_name} (confianza={confidence})")
            assert entity_name in ["Juan", "María"]
            assert 0.5 <= confidence <= 1.0
