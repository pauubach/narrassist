# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from narrative_assistant.nlp.attributes import AttributeExtractor

# Texto de prueba - solo las dos primeras oraciones
text = """María era una mujer de ojos azules que vivía en Madrid. Tenía el cabello negro y largo."""

# Menciones de entidades (nombre, start, end)
mentions = [
    ("María", 0, 5),   # Primera mención
    ("Madrid", 49, 55),
]

# Crear extractor
extractor = AttributeExtractor(
    filter_metaphors=True,
    min_confidence=0.4,
    use_dependency_extraction=True
)

# Extraer atributos
result = extractor.extract_attributes(text, mentions)

if result.is_success:
    extraction = result.value
    print(f"\nExtraccion exitosa!")
    print(f"Total de atributos encontrados: {len(extraction.attributes)}\n")

    for i, attr in enumerate(extraction.attributes, 1):
        print(f"{i}. {attr.entity_name} -> {attr.key.value} = {attr.value}")
        print(f"   Confianza: {attr.confidence:.2f}")
        print(f"   Fuente: {attr.source_text}")
        print(f"   Start: {attr.start_char}, End: {attr.end_char}")
        print()

    print("\n--- Análisis del texto ---")
    print(f"Texto completo: {text}")
    print(f"\nMenciones:")
    for name, start, end in mentions:
        print(f"  {name}: posición {start}-{end}")
        print(f"    Texto: '{text[start:end]}'")
else:
    print(f"Error: {result.error}")
