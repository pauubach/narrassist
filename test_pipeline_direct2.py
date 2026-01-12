# -*- coding: utf-8 -*-
"""
Test directo del pipeline de análisis.
"""
import sys
import io
import time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
from narrative_assistant.pipelines.analysis_pipeline import run_full_analysis

# Leer documento
doc_path = Path("test_books/test_document_fresh.txt")

# Nombre único para evitar colisiones con proyectos anteriores
project_name = f"Test_{int(time.time())}"

print("="*80)
print("PIPELINE ANALYSIS TEST")
print("="*80)
print(f"\nDocumento: {doc_path.name}")
print(f"Proyecto: {project_name}")

# Analizar
print("\nIniciando análisis...")
result = run_full_analysis(
    document_path=doc_path,
    project_name=project_name,
)

if result.is_failure:
    print(f"\nERROR: {result.error}")
    if hasattr(result, 'errors') and result.errors:
        for err in result.errors:
            print(f"  - {err}")
else:
    report = result.value
    print(f"\n✓ Análisis completado exitosamente")
    print(f"Project ID: {report.project_id}")
    print(f"Duración: {report.duration_seconds:.2f}s")

    print(f"\nEntidades: {len(report.entities)}")
    for i, entity in enumerate(report.entities[:15], 1):
        print(f"  {i}. {entity.canonical_name} ({entity.entity_type})")

    print(f"\nAlertas: {len(report.alerts)}")
    for i, alert in enumerate(report.alerts, 1):
        print(f"  {i}. [{alert.severity.value}] {alert.title}")
        print(f"     {alert.message[:100]}...")

    print(f"\nEstadísticas:")
    for key, value in report.stats.items():
        print(f"  - {key}: {value}")

    if report.errors:
        print(f"\nErrores no fatales: {len(report.errors)}")
        for err in report.errors[:5]:
            print(f"  - {err}")

    if report.warnings:
        print(f"\nAdvertencias: {len(report.warnings)}")
        for warn in report.warnings[:5]:
            print(f"  - {warn}")
