# -*- coding: utf-8 -*-
"""
Script de prueba para verificar extraccion de atributos.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from narrative_assistant.nlp.attributes import AttributeExtractor

# Texto de prueba del documento
text = """María era una mujer de ojos azules que vivía en Madrid. Tenía el cabello negro y largo.

Juan la conoció en el parque del Retiro. Él era alto y delgado.

María apareció en la fiesta con sus ojos verdes brillantes. Llevaba un vestido rojo.

Juan la saludó, sorprendido por su cabello rubio y corto."""

# Menciones de entidades (nombre, start, end)
mentions = [
    ("María", 0, 5),   # Primera mención
    ("Madrid", 49, 55),
    ("Juan", 96, 100),
    ("parque del Retiro", 118, 137),
    ("María", 179, 184),  # Segunda mención
    ("Juan", 251, 255),   # Segunda mención
]

# Crear extractor
extractor = AttributeExtractor(
    filter_metaphors=True,
    min_confidence=0.4,  # Bajar el umbral para ver más resultados
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
        print(f"   Fuente: {attr.source_text[:60]}...")
        print()
else:
    print(f"Error: {result.error}")
