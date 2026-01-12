"""
CLI para Narrative Assistant.

Punto de entrada de línea de comandos para el asistente de corrección narrativa.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .core.config import get_config

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configura el logging para la CLI."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main() -> int:
    """
    Punto de entrada principal de la CLI.

    Returns:
        Código de salida (0 = éxito, 1 = error)
    """
    parser = argparse.ArgumentParser(
        prog="narrative-assistant",
        description="Asistente de corrección narrativa para detectar inconsistencias en manuscritos.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Mostrar mensajes de debug",
    )

    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # Subcomando: analyze
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analizar un documento",
    )
    analyze_parser.add_argument(
        "document",
        type=Path,
        help="Ruta al documento a analizar (.docx, .txt, .md)",
    )
    analyze_parser.add_argument(
        "--project",
        type=str,
        help="Nombre del proyecto (opcional)",
    )

    # Subcomando: verify
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verificar el entorno de desarrollo",
    )

    # Subcomando: info
    info_parser = subparsers.add_parser(
        "info",
        help="Mostrar información del sistema",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.command == "verify":
        return cmd_verify()
    elif args.command == "info":
        return cmd_info()
    elif args.command == "analyze":
        return cmd_analyze(args.document, args.project)
    else:
        parser.print_help()
        return 0


def cmd_verify() -> int:
    """Verifica que el entorno esté configurado correctamente."""
    print("Verificando entorno de Narrative Assistant...")
    print()

    errors = []

    # Verificar spaCy
    try:
        import spacy
        print(f"[OK] spaCy {spacy.__version__}")
        try:
            nlp = spacy.load("es_core_news_lg")
            print(f"[OK] Modelo es_core_news_lg cargado")
        except OSError:
            errors.append("Modelo spaCy no encontrado. Ejecutar: python -m spacy download es_core_news_lg")
            print("[ERROR] Modelo es_core_news_lg NO encontrado")
    except ImportError:
        errors.append("spaCy no instalado")
        print("[ERROR] spaCy no instalado")

    # Verificar sentence-transformers
    try:
        import sentence_transformers
        print(f"[OK] sentence-transformers {sentence_transformers.__version__}")
    except ImportError:
        errors.append("sentence-transformers no instalado")
        print("[ERROR] sentence-transformers no instalado")

    # Verificar PyTorch y GPU
    try:
        import torch
        print(f"[OK] PyTorch {torch.__version__}")

        if torch.cuda.is_available():
            print(f"[OK] CUDA disponible: {torch.cuda.get_device_name(0)}")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            print("[OK] MPS (Apple Silicon) disponible")
        else:
            print("[INFO] GPU no disponible, usando CPU")
    except ImportError:
        errors.append("PyTorch no instalado")
        print("[ERROR] PyTorch no instalado")

    print()
    if errors:
        print(f"Se encontraron {len(errors)} error(es):")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("Entorno verificado correctamente.")
        return 0


def cmd_info() -> int:
    """Muestra información del sistema y configuración."""
    config = get_config()

    print("Narrative Assistant - Información del Sistema")
    print("=" * 50)
    print()

    # Configuración
    print("Configuración:")
    print(f"  Dispositivo preferido: {config.gpu.device_preference}")
    print(f"  Batch size GPU: {config.gpu.embeddings_batch_size_gpu}")
    print(f"  Batch size CPU: {config.gpu.embeddings_batch_size_cpu}")
    print(f"  spaCy GPU: {config.gpu.spacy_gpu_enabled}")
    print(f"  Embeddings GPU: {config.gpu.embeddings_gpu_enabled}")
    print()

    print("NLP:")
    print(f"  Modelo spaCy: {config.nlp.spacy_model}")
    print(f"  Modelo embeddings: {config.nlp.embedding_model}")
    print()

    print("Directorios:")
    print(f"  Datos: {config.persistence.data_dir}")
    print(f"  Base de datos: {config.persistence.db_name}")

    return 0


def cmd_analyze(document: Path, project_name: Optional[str]) -> int:
    """
    Analiza un documento completo.

    Args:
        document: Ruta al documento
        project_name: Nombre del proyecto (opcional)

    Returns:
        Código de salida
    """
    from .pipelines import run_full_analysis, PipelineConfig

    if not document.exists():
        print(f"Error: El archivo '{document}' no existe.")
        return 1

    print("=" * 70)
    print("NARRATIVE ASSISTANT - Análisis de Manuscrito")
    print("=" * 70)
    print()
    print(f"Documento: {document.name}")
    print(f"Ruta: {document.absolute()}")
    if project_name:
        print(f"Proyecto: {project_name}")
    print()
    print("Iniciando análisis completo...")
    print("-" * 70)
    print()

    # Configuración del pipeline
    config = PipelineConfig(
        run_ner=True,
        run_attributes=True,
        run_consistency=True,
        create_alerts=True,
        min_confidence=0.5,
    )

    # Ejecutar análisis
    result = run_full_analysis(
        document_path=document,
        project_name=project_name,
        config=config,
    )

    # Procesar resultado
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

    # Mostrar resultados
    print()
    print("=" * 70)
    print("ANÁLISIS COMPLETADO")
    print("=" * 70)
    print()

    # Estadísticas básicas
    print("Estadísticas del Documento:")
    print(f"  Caracteres: {report.stats.get('total_characters', 0):,}")
    print(f"  Capítulos detectados: {report.stats.get('chapters', 0)}")
    print(f"  Duración: {report.duration_seconds:.2f}s")
    print()

    # Entidades
    print("Extracción de Entidades:")
    print(f"  Total entidades: {len(report.entities)}")
    if report.entities:
        entity_types = {}
        for e in report.entities:
            entity_types[e.entity_type] = entity_types.get(e.entity_type, 0) + 1
        for etype, count in sorted(entity_types.items(), key=lambda x: -x[1]):
            print(f"    - {etype}: {count}")
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

    # Mostrar alertas críticas
    if report.critical_alerts:
        print("=" * 70)
        print("ALERTAS CRÍTICAS")
        print("=" * 70)
        print()
        for i, alert in enumerate(report.critical_alerts[:10], 1):  # Máximo 10
            print(f"{i}. {alert.title}")
            print(f"   {alert.description}")
            if alert.chapter:
                print(f"   Ubicación: Capítulo {alert.chapter}")
            print(f"   Confianza: {alert.confidence:.0%}")
            print()

        if len(report.critical_alerts) > 10:
            print(f"... y {len(report.critical_alerts) - 10} alertas críticas más")
            print()

    # Mostrar advertencias
    if report.warning_alerts:
        print("=" * 70)
        print(f"ADVERTENCIAS ({len(report.warning_alerts)} total)")
        print("=" * 70)
        print()
        for i, alert in enumerate(report.warning_alerts[:5], 1):  # Máximo 5
            print(f"{i}. {alert.title}")
            print(f"   {alert.description}")
            if alert.chapter:
                print(f"   Ubicación: Capítulo {alert.chapter}")
            print()

        if len(report.warning_alerts) > 5:
            print(f"... y {len(report.warning_alerts) - 5} advertencias más")
            print()

    # Errores no fatales
    if report.errors:
        print("=" * 70)
        print("ADVERTENCIAS DEL SISTEMA")
        print("=" * 70)
        print()
        for i, error in enumerate(report.errors, 1):
            print(f"{i}. {error.user_message}")
        print()

    # Resumen final
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print()
    print(f"Proyecto ID: {report.project_id}")
    print(f"Sesión ID: {report.session_id}")
    print(f"Fingerprint: {report.document_fingerprint[:16]}...")
    print()

    if report.alerts:
        print("Las alertas han sido guardadas en la base de datos.")
        print("Usa 'narrative-assistant export' para exportar el informe completo.")
    else:
        print("No se detectaron problemas en el manuscrito.")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
