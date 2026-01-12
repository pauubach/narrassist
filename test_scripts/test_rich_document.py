"""
Script de prueba con documento rico que contiene inconsistencias reales.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from narrative_assistant.pipelines import run_full_analysis, PipelineConfig, export_report_markdown

def main():
    document_path = Path(__file__).parent.parent / "test_books" / "test_document_rich.txt"

    print("=" * 70)
    print("TEST: Documento Rico con Inconsistencias")
    print("=" * 70)
    print()
    print(f"Documento: {document_path.name}")
    print()

    # Leer y mostrar contenido
    with open(document_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print("Inconsistencias esperadas:")
    print("  - Maria: ojos azules -> verdes -> azules")
    print("  - Maria: cabello negro largo -> rubio corto -> negro largo")
    print("  - Juan: bajo y fornido -> muy alto y delgado")
    print("  - Juan: ojos marrones -> azules")
    print("  - Juan: ~30 anos -> 50 anos")
    print()
    print("Iniciando análisis...")
    print("-" * 70)
    print()

    config = PipelineConfig(
        run_ner=True,
        run_attributes=True,
        run_consistency=True,
        create_alerts=True,
        min_confidence=0.3,  # Más bajo para capturar más inconsistencias
    )

    result = run_full_analysis(
        document_path=document_path,
        project_name="Test Rico",
        config=config,
    )

    if result.is_failure:
        print()
        print("=" * 70)
        print("ERROR")
        print("=" * 70)
        print()
        print(f"Motivo: {result.error.user_message}")
        return 1

    report = result.value

    print()
    print("=" * 70)
    print("ANÁLISIS COMPLETADO")
    print("=" * 70)
    print()

    # Estadísticas
    print("Estadísticas:")
    print(f"  Caracteres: {report.stats.get('total_characters', 0):,}")
    print(f"  Capítulos: {report.stats.get('chapters', 0)}")
    print(f"  Duración: {report.duration_seconds:.2f}s")
    print()

    # Entidades
    print("Entidades Detectadas:")
    print(f"  Total: {len(report.entities)}")
    if report.entities:
        entity_types = {}
        for e in report.entities:
            entity_types[e.entity_type] = entity_types.get(e.entity_type, 0) + 1

        for etype, count in sorted(entity_types.items(), key=lambda x: -x[1]):
            print(f"    {etype}: {count}")
            # Mostrar nombres
            entities_of_type = [e for e in report.entities if e.entity_type == etype]
            for entity in entities_of_type[:5]:  # Máximo 5
                print(f"      - {entity.canonical_name} (importancia: {entity.importance})")
    print()

    # Atributos
    if "attributes_extracted" in report.stats:
        print(f"Atributos extraídos: {report.stats['attributes_extracted']}")
        print()

    # Inconsistencias
    if "inconsistencies_found" in report.stats:
        print(f"Inconsistencias detectadas: {report.stats['inconsistencies_found']}")
        print()

    # Alertas
    print("Alertas Generadas:")
    print(f"  Total: {len(report.alerts)}")
    print(f"  Críticas: {len(report.critical_alerts)}")
    print(f"  Advertencias: {len(report.warning_alerts)}")
    print()

    # Mostrar todas las alertas
    if report.alerts:
        print("=" * 70)
        print("DETALLE DE ALERTAS")
        print("=" * 70)
        print()

        for i, alert in enumerate(report.alerts, 1):
            print(f"{i}. [{alert.severity.value.upper()}] {alert.title}")
            print(f"   Categoría: {alert.category.value}")
            print(f"   Descripción: {alert.description}")
            print(f"   Explicación: {alert.explanation}")
            if alert.suggestion:
                print(f"   Sugerencia: {alert.suggestion}")
            if alert.chapter:
                print(f"   Ubicación: Capítulo {alert.chapter}")
            print(f"   Confianza: {alert.confidence:.0%}")
            if alert.excerpt:
                print(f"   Extracto: {alert.excerpt[:100]}...")
            print()

    # Errores
    if report.errors:
        print("=" * 70)
        print("ERRORES/ADVERTENCIAS DEL SISTEMA")
        print("=" * 70)
        print()
        for i, error in enumerate(report.errors, 1):
            print(f"{i}. {error.user_message}")
        print()

    # Exportar a Markdown
    output_path = Path("test_report_rich.md")
    export_result = export_report_markdown(report, output_path)
    if export_result.is_success:
        print(f"Informe exportado a: {output_path}")
        print()

    # Resumen
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print()
    print(f"Proyecto ID: {report.project_id}")
    print(f"Sesión ID: {report.session_id}")
    print()

    if report.alerts:
        print(f"[OK] Se detectaron {len(report.alerts)} alertas")
        print("     Las alertas estan guardadas en la base de datos")
    else:
        print("[WARNING] No se detectaron alertas")
        print("          Esto podria indicar problemas en:")
        print("          - Extraccion de entidades (NER)")
        print("          - Extraccion de atributos")
        print("          - Analisis de consistencia")

    print()
    return 0

if __name__ == "__main__":
    sys.exit(main())
