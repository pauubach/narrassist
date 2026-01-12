# -*- coding: utf-8 -*-
"""
Debug de extracción de atributos con pronombres posesivos.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from narrative_assistant.nlp.attributes import AttributeExtractor

# Texto exacto del documento (más completo)
text = """María Sánchez se despertó temprano. Sus ojos azules brillaban con la luz del amanecer.

Juan Pérez, su vecino, tocó a la puerta. Él era un hombre bajo y fornido.

Al día siguiente, María apareció en la cafetería del barrio. Sus ojos verdes llamaron la atención de todos los presentes."""

# Menciones de entidades (simulando lo que detecta NER)
mentions = [
    ("María Sánchez", text.find("María Sánchez"), text.find("María Sánchez") + len("María Sánchez")),
    ("Juan Pérez", text.find("Juan Pérez"), text.find("Juan Pérez") + len("Juan Pérez")),
    ("Él", text.find("Él"), text.find("Él") + len("Él")),
    ("María", text.find("Al día siguiente, María") + len("Al día siguiente, "), text.find("Al día siguiente, María") + len("Al día siguiente, María")),
]

print("="*80)
print("DEBUG: Extracción de atributos")
print("="*80)
print(f"\nTexto: {text}")
print(f"\nMenciones: {mentions}")

extractor = AttributeExtractor(
    filter_metaphors=True,
    min_confidence=0.4,
    use_dependency_extraction=True
)

result = extractor.extract_attributes(text, mentions)

if result.is_success:
    attrs = result.value.attributes
    print(f"\n✓ Extraídos {len(attrs)} atributos:\n")
    for attr in attrs:
        print(f"  {attr.entity_name} -> {attr.key.value} = {attr.value}")
        print(f"    Fuente: '{attr.source_text}'")
        print(f"    Confianza: {attr.confidence:.2f}")
        print()
else:
    print(f"ERROR: {result.error}")
