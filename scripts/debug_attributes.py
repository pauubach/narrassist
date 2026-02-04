# -*- coding: utf-8 -*-
"""Script para debugear la extracción de atributos."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Full test text
FULL_TEXT = """Capítulo 1: El Despertar

María Sánchez se despertó temprano aquella mañana de martes. Sus ojos azules brillaban con la luz del amanecer que entraba por la ventana. Tenía el cabello largo y negro, recogido en una trenza. Era una mujer alta, de aproximadamente treinta años.

Juan Pérez, su vecino, tocó a la puerta. Él era un hombre bajo y fornido, con barba espesa y ojos marrones. Trabajaba como carpintero en el centro de Madrid.

Capítulo 2: La Revelación

María apareció en la cafetería del barrio. Sus ojos verdes llamaron la atención de todos los presentes. Llevaba el cabello corto y rubio, completamente diferente a como la recordaban.

Juan entró poco después. Era un hombre muy alto, delgado como un junco. Sus ojos azules miraban con curiosidad a María.
"""


def test_attribute_extraction():
    """Test full attribute extraction."""
    from narrative_assistant.nlp.attributes import AttributeExtractor

    # Entity mentions with CANONICAL names and entity_type
    # Format: (name, start, end, entity_type)
    # entity_type: "PER" for person, "LOC" for location, "ORG" for organization
    # The real pipeline resolves "María" -> "María Sánchez", "Juan" -> "Juan Pérez"
    #
    # POSICIONES CALCULADAS del texto FULL_TEXT:
    # - "María Sánchez" Chapter 1: 26-39
    # - "Juan Pérez" Chapter 1: 275-285
    # - "Madrid": 425-431
    # - "María" Chapter 2 ("María apareció"): 461-466
    # - "Juan" Chapter 2 ("Juan entró"): 646-650
    # - "María" at end ("a María"): 759-764
    # - "Llevaba el cabello corto": 565 (between María@461 and Juan@646)
    entity_mentions = [
        ("María Sánchez", 26, 39, "PER"),      # Chapter 1: "María Sánchez se despertó..."
        ("Juan Pérez", 275, 285, "PER"),       # Chapter 1: "Juan Pérez, su vecino..."
        ("Madrid", 425, 431, "LOC"),           # Location - should NOT get physical attributes
        ("María Sánchez", 461, 466, "PER"),    # Chapter 2: "María apareció..."
        ("Juan Pérez", 646, 650, "PER"),       # Chapter 2: "Juan entró poco después"
        ("María Sánchez", 759, 764, "PER"),    # Chapter 2: "a María" at the end (object)
    ]

    extractor = AttributeExtractor(
        use_llm=False,  # Disable LLM for faster testing
        use_embeddings=True,
        use_dependency_extraction=True,
        use_patterns=True,
    )

    result = extractor.extract_attributes(
        text=FULL_TEXT,
        entity_mentions=entity_mentions,
        chapter_id=None,
    )

    if result.is_failure:
        print(f"ERROR: {result.error}")
        return

    attrs = result.value.attributes

    print("=" * 70)
    print("ATRIBUTOS EXTRAÍDOS:")
    print("=" * 70)

    # Group by entity
    by_entity = {}
    for attr in attrs:
        name = attr.entity_name.lower()
        if name not in by_entity:
            by_entity[name] = []
        by_entity[name].append(attr)

    for entity, entity_attrs in sorted(by_entity.items()):
        print(f"\n{entity.upper()}:")
        for attr in entity_attrs:
            print(f"  - {attr.key.value}: {attr.value} (conf={attr.confidence:.2f})")
            print(f"    Fuente: \"{attr.source_text[:60]}...\"")


if __name__ == "__main__":
    test_attribute_extraction()
