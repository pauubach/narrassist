# -*- coding: utf-8 -*-
"""
Test directo del pipeline de análisis.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
from narrative_assistant.pipelines.analysis_pipeline import DocumentAnalysisPipeline

# Crear pipeline
pipeline = DocumentAnalysisPipeline()

# Leer documento
doc_path = Path("test_books/test_document_rich.txt")
with open(doc_path, 'r', encoding='utf-8') as f:
    text = f.read()

print("="*80)
print("PIPELINE ANALYSIS TEST")
print("="*80)
print(f"\nDocumento: {doc_path.name}")
print(f"Longitud: {len(text)} chars")

# Analizar
print("\nIniciando análisis...")
result = pipeline.analyze(text, project_id=999)  # ID ficticio

if result.is_failure:
    print(f"\nERROR: {result.error}")
else:
    analysis = result.value
    print(f"\n✓ Análisis completado exitosamente")
    print(f"\nEntidades: {len(analysis.entities)}")
    for entity in analysis.entities[:10]:
        print(f"  - {entity.canonical_name} ({entity.entity_type})")

    print(f"\nAtributos: {len(analysis.attributes)}")
    for attr in analysis.attributes[:15]:
        print(f"  - {attr.entity_name} -> {attr.key.value} = {attr.value} (conf: {attr.confidence:.2f})")

    print(f"\nInconsistencias: {len(analysis.inconsistencies)}")
    for inc in analysis.inconsistencies:
        print(f"  - {inc.entity_name}: {inc.attribute_key.value} '{inc.value1}' vs '{inc.value2}' (conf: {inc.confidence:.2f})")
