"""
Script de prueba del pipeline completo.
"""

import sys
from pathlib import Path

# Añadir src al path para importar
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from narrative_assistant.pipelines import run_full_analysis, PipelineConfig

def main():
    document_path = Path(__file__).parent.parent / "test_books" / "test_document.txt"

    print("=" * 70)
    print("NARRATIVE ASSISTANT - Test Pipeline End-to-End")
    print("=" * 70)
    print()
    print(f"Documento: {document_path.name}")
    print()
    print("Iniciando análisis completo...")
    print("-" * 70)
    print()

    config = PipelineConfig(
        run_ner=True,
        run_attributes=True,
        run_consistency=True,
        create_alerts=True,
        min_confidence=0.5,
    )

    result = run_full_analysis(
        document_path=document_path,
        project_name="Test Novela",
        config=config,
    )

    if result.is_failure:
        print()
        print("=" * 70)
        print("ERROR: El análisis falló")
        print("=" * 70)
        print()
        print(f"Motivo: {result.error.user_message}")
        if hasattr(result.error, 'context') and result.error.context:
            print(f"Contexto: {result.error.context}")
        return 1

    report = result.value

    print()
    print("=" * 70)
    print("ANÁLISIS COMPLETADO")
    print("=" * 70)
    print()

    print("Estadísticas del Documento:")
    print(f"  Caracteres: {report.stats.get('total_characters', 0):,}")
    print(f"  Capítulos detectados: {report.stats.get('chapters', 0)}")
    print(f"  Duración: {report.duration_seconds:.2f}s")
    print()

    print("Extracción de Entidades:")
    print(f"  Total entidades: {len(report.entities)}")
    if report.entities:
        entity_types = {}
        for e in report.entities:
            entity_types[e.entity_type] = entity_types.get(e.entity_type, 0) + 1
        for etype, count in sorted(entity_types.items(), key=lambda x: -x[1]):
            print(f"    - {etype}: {count}")
    print()

    if "attributes_extracted" in report.stats:
        print(f"Atributos extraídos: {report.stats['attributes_extracted']}")
        print()

    if "inconsistencies_found" in report.stats:
        print(f"Inconsistencias detectadas: {report.stats['inconsistencies_found']}")
        print()

    print("Alertas Generadas:")
    print(f"  Total: {len(report.alerts)}")
    print(f"  Críticas: {len(report.critical_alerts)}")
    print(f"  Advertencias: {len(report.warning_alerts)}")
    print()

    if report.critical_alerts:
        print("=" * 70)
        print("ALERTAS CRÍTICAS")
        print("=" * 70)
        print()
        for i, alert in enumerate(report.critical_alerts[:5], 1):
            print(f"{i}. {alert.title}")
            print(f"   {alert.description}")
            if alert.chapter:
                print(f"   Ubicación: Capítulo {alert.chapter}")
            print(f"   Confianza: {alert.confidence:.0%}")
            print()

    if report.errors:
        print("=" * 70)
        print("ADVERTENCIAS DEL SISTEMA")
        print("=" * 70)
        print()
        for i, error in enumerate(report.errors, 1):
            print(f"{i}. {error.user_message}")
        print()

    print("=" * 70)
    print("PRUEBA EXITOSA")
    print("=" * 70)
    print()
    print(f"Proyecto ID: {report.project_id}")
    print(f"Sesión ID: {report.session_id}")
    print(f"Fingerprint: {report.document_fingerprint[:16]}...")
    print()

    return 0

if __name__ == "__main__":
    sys.exit(main())
