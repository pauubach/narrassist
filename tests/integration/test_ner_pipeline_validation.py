"""
Tests de integración para verificar que el pipeline NER genera menciones con metadata de validación.

Este test verifica que:
1. El pipeline NER integra correctamente el sistema de validación adaptativa
2. Las menciones se guardan con metadata JSON (validation_method, validation_reasoning)
3. Las menciones en contextos posesivos tienen metadata con información de validación
"""

import json

import pytest

from narrative_assistant.entities.models import EntityMention
from narrative_assistant.entities.repository import EntityRepository
from narrative_assistant.persistence.database import get_database


def test_ner_validation_metadata_serialization():
    """
    Test unitario que verifica que el método _validate_ner_mention funciona correctamente.
    """
    from narrative_assistant.pipelines.unified_analysis import UnifiedAnalysisPipeline

    # Crear instancia del pipeline (que incluye el mixin)
    pipeline = UnifiedAnalysisPipeline()

    # Texto de test
    text = "Isabel era una detective privada. La casa de Isabel estaba en el centro."

    # Validar mención 1: "Isabel" en posición de sujeto (debe ser válida)
    metadata1 = pipeline._validate_ner_mention(
        entity_name="Isabel",
        surface_form="Isabel",
        start_char=0,
        end_char=6,
        full_text=text,
    )

    assert metadata1 is not None, "Metadata no debe ser None"
    data1 = json.loads(metadata1)
    assert "validation_method" in data1
    assert "validation_reasoning" in data1

    # Validar mención 2: "Isabel" en contexto posesivo "La casa de Isabel"
    pos_isabel = text.index("de Isabel")
    metadata2 = pipeline._validate_ner_mention(
        entity_name="Isabel",
        surface_form="Isabel",
        start_char=pos_isabel + 3,  # Después de "de "
        end_char=pos_isabel + 9,
        full_text=text,
    )

    assert metadata2 is not None, "Metadata no debe ser None"
    data2 = json.loads(metadata2)
    assert "validation_method" in data2
    assert "validation_reasoning" in data2

    # El reasoning debe indicar contexto posesivo
    reasoning2 = data2["validation_reasoning"].lower()
    assert (
        "posesivo" in reasoning2 or "genitivo" in reasoning2
    ), f"Debe detectar contexto posesivo, reasoning: {data2['validation_reasoning']}"


def test_backward_compatibility_mentions_without_metadata():
    """
    Verifica que las menciones sin metadata (legacy) siguen funcionando.
    """
    # Obtener base de datos
    db = get_database()

    # Crear un proyecto de test
    from narrative_assistant.persistence.project import ProjectManager

    project_manager = ProjectManager(db=db)
    result = project_manager.create_from_document(
        text="Test document content.",
        name="Test Backward Compat",
        document_format="txt",
        description="Test de compatibilidad hacia atrás",
    )

    assert result.is_success, f"Fallo al crear proyecto: {result.error}"
    project = result.value

    # Crear una entidad
    from narrative_assistant.entities.models import Entity, EntityType

    entity_repo = EntityRepository(db)
    entity = Entity(
        project_id=project.id,
        canonical_name="Test Entity",
        entity_type=EntityType.CHARACTER,
    )
    entity_id = entity_repo.create_entity(entity)

    # Crear una mención sin metadata (legacy)
    legacy_mention = EntityMention(
        entity_id=entity_id,
        surface_form="Test",
        start_char=0,
        end_char=4,
        confidence=1.0,
        source="manual",
        metadata=None,  # Sin metadata (legacy)
    )

    # Guardar mención legacy
    saved_count = entity_repo.create_mentions_batch([legacy_mention])
    assert saved_count == 1, "Debe poder guardar mención sin metadata"

    # Recuperar mención
    mentions = entity_repo.get_mentions_by_entity(entity_id)
    assert len(mentions) == 1, "Debe haber una mención"
    assert mentions[0].metadata is None, "Metadata debe ser None (legacy)"

    # Crear una mención con metadata
    metadata_dict = {
        "validation_method": "regex",
        "validation_reasoning": "Sujeto al inicio de oración",
    }
    modern_mention = EntityMention(
        entity_id=entity_id,
        surface_form="Test2",
        start_char=10,
        end_char=15,
        confidence=0.9,
        source="ner",
        metadata=json.dumps(metadata_dict),
    )

    saved_count = entity_repo.create_mentions_batch([modern_mention])
    assert saved_count == 1, "Debe poder guardar mención con metadata"

    # Recuperar ambas menciones
    all_mentions = entity_repo.get_mentions_by_entity(entity_id)
    assert len(all_mentions) == 2, "Debe haber dos menciones"

    # Verificar que ambas coexisten
    legacy_found = any(m.metadata is None for m in all_mentions)
    modern_found = any(m.metadata is not None for m in all_mentions)

    assert legacy_found, "Debe haber mención legacy sin metadata"
    assert modern_found, "Debe haber mención moderna con metadata"
