"""Test NER directamente en el pipeline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from narrative_assistant.nlp.ner import NERExtractor
from narrative_assistant.entities.repository import get_entity_repository
from narrative_assistant.entities.models import Entity

text = """
María Sánchez es una mujer alta de Madrid. Sus ojos azules brillaban.
Juan Pérez es un hombre bajo de Barcelona.
"""

print("=" * 70)
print("TEST NER + PERSISTENCIA")
print("=" * 70)
print()

# Test NER
ner = NERExtractor()
result = ner.extract_entities(text)

print(f"NER Success: {result.is_success}")
print(f"NER Value type: {type(result.value)}")

if result.is_success and result.value:
    ner_result = result.value
    print(f"NER Result has entities: {hasattr(ner_result, 'entities')}")

    if hasattr(ner_result, 'entities'):
        entities_data = ner_result.entities
        print(f"Entities found: {len(entities_data)}")

        for i, entity_obj in enumerate(entities_data, 1):
            print(f"\n{i}. {entity_obj.text}")
            print(f"   Label: {entity_obj.label}")
            print(f"   Label.value: {entity_obj.label.value}")
            print(f"   Canonical: {entity_obj.canonical_form}")
            print(f"   Confidence: {entity_obj.confidence}")

            # Test creación de Entity
            entity = Entity(
                id=0,
                project_id=999,  # Test project ID
                entity_type=entity_obj.label.value,
                canonical_name=entity_obj.canonical_form,
                aliases=[],
                confidence=entity_obj.confidence,
            )
            print(f"   Entity created: {entity}")
    else:
        print("ERROR: NER result doesn't have 'entities' attribute")
        print(f"NER result attributes: {dir(ner_result)}")
else:
    print(f"NER failed or returned None")
    if result.errors:
        print(f"Errors: {result.errors}")

print()
print("=" * 70)
