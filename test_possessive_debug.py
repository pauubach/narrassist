# -*- coding: utf-8 -*-
"""
Debug test para pronombres posesivos.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from narrative_assistant.nlp.attributes import AttributeExtractor

# Texto con "su cabello" que debería referirse a María (el objeto "la")
text = """Juan la saludó, sorprendido por su cabello rubio y corto."""

# Menciones
mentions = [
    ("Juan", 0, 4),
]

print("="*80)
print("DEBUG: Pronombre posesivo 'su' después de objeto 'la'")
print("="*80)
print(f"\nTexto: {text}")
print(f"\nEl pronombre 'su' debería referirse a 'la' (María), no a Juan (sujeto)")

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
        print(f"  Confianza: {attr.confidence:.2f}")
        print(f"  Fuente: {attr.source_text}")
        print()
else:
    print(f"ERROR: {result.error}")

# Ahora probar con ambas menciones
print("\n" + "="*80)
print("Ahora con ambas menciones (María y Juan):")
print("="*80)

mentions2 = [
    ("Juan", 0, 4),
    ("María", 100, 105),  # Mención ficticia para simular que María está antes
]

result2 = extractor.extract_attributes(text, mentions2)

if result2.is_success:
    attrs2 = result2.value.attributes
    print(f"\n✓ Extraídos {len(attrs2)} atributos:\n")
    for attr in attrs2:
        print(f"  {attr.entity_name} -> {attr.key.value} = {attr.value}")
        print(f"  Confianza: {attr.confidence:.2f}")
        print()
else:
    print(f"ERROR: {result2.error}")
