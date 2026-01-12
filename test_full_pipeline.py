# -*- coding: utf-8 -*-
"""
Test completo del pipeline de análisis con detección de inconsistencias.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from narrative_assistant.nlp.attributes import AttributeExtractor
from narrative_assistant.analysis.attribute_consistency import AttributeConsistencyChecker

# Texto con inconsistencias claras
text = """María era una mujer de ojos azules que vivía en Madrid. Tenía el cabello negro y largo.

Juan la conoció en el parque del Retiro. Él era alto y delgado.

María apareció en la fiesta con sus ojos verdes brillantes. Llevaba un vestido rojo.

Juan la saludó, sorprendido por su cabello rubio y corto."""

# Menciones de entidades
mentions = [
    ("María", 0, 5),
    ("Madrid", 49, 55),
    ("Juan", 96, 100),
    ("parque del Retiro", 118, 137),
    ("María", 179, 184),
    ("Juan", 251, 255),
]

print("="*80)
print("TEST COMPLETO DEL PIPELINE")
print("="*80)

# PASO 1: Extraer atributos
print("\n[1/2] Extrayendo atributos...")
extractor = AttributeExtractor(
    filter_metaphors=True,
    min_confidence=0.4,
    use_dependency_extraction=True
)

result = extractor.extract_attributes(text, mentions)

if result.is_failure:
    print(f"ERROR: {result.error}")
    sys.exit(1)

extraction = result.value
attributes = extraction.attributes

print(f"✓ Extraídos {len(attributes)} atributos:\n")
for i, attr in enumerate(attributes, 1):
    print(f"  {i}. {attr.entity_name} -> {attr.key.value} = {attr.value}")
    print(f"     Confianza: {attr.confidence:.2f}")
    print()

# PASO 2: Verificar consistencia
print("\n[2/2] Verificando consistencia...")
checker = AttributeConsistencyChecker(
    use_embeddings=True,
    min_confidence=0.5
)

consistency_result = checker.check_consistency(attributes)

if consistency_result.is_failure:
    print(f"ERROR: {consistency_result.error}")
    sys.exit(1)

inconsistencies = consistency_result.value

print(f"✓ Detectadas {len(inconsistencies)} inconsistencias:\n")

if len(inconsistencies) == 0:
    print("  (ninguna)")
else:
    for i, inc in enumerate(inconsistencies, 1):
        print(f"  {i}. {inc.entity_name} - {inc.attribute_key.value}")
        print(f"     Valor 1: '{inc.value1}' (fuente: {inc.value1_excerpt[:40]}...)")
        print(f"     Valor 2: '{inc.value2}' (fuente: {inc.value2_excerpt[:40]}...)")
        print(f"     Tipo: {inc.inconsistency_type.value}")
        print(f"     Confianza: {inc.confidence:.2f}")
        print(f"     Explicación: {inc.explanation}")
        print()

# RESUMEN
print("\n" + "="*80)
print("RESUMEN")
print("="*80)
print(f"Atributos extraídos: {len(attributes)}")
print(f"Inconsistencias detectadas: {len(inconsistencies)}")

# Verificar que se detectaron las inconsistencias esperadas
expected_inconsistencies = {
    ("maría", "eye_color"): {"azul", "verde"},
    ("maría", "hair_color"): {"negro", "rubio"},
}

found_inconsistencies = {}
for inc in inconsistencies:
    key = (inc.entity_name.lower(), inc.attribute_key.value)
    if key not in found_inconsistencies:
        found_inconsistencies[key] = set()
    found_inconsistencies[key].add(inc.value1.lower())
    found_inconsistencies[key].add(inc.value2.lower())

print("\nVerificación de inconsistencias esperadas:")
all_found = True
for key, values in expected_inconsistencies.items():
    if key in found_inconsistencies:
        print(f"✓ {key[0]} - {key[1]}: {values}")
    else:
        print(f"✗ {key[0]} - {key[1]}: NO DETECTADO")
        all_found = False

if all_found:
    print("\n✓ TODAS LAS INCONSISTENCIAS FUERON DETECTADAS CORRECTAMENTE")
else:
    print("\n✗ FALTAN INCONSISTENCIAS POR DETECTAR")
