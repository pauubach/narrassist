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
from .core.utils import format_duration

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
        version="%(prog)s 0.1.1",
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

    # Subcomando: project
    project_parser = subparsers.add_parser(
        "project",
        help="Gestionar proyectos",
    )
    project_sub = project_parser.add_subparsers(dest="subcommand")

    project_list = project_sub.add_parser("list", help="Listar proyectos")
    project_info_cmd = project_sub.add_parser("info", help="Info de un proyecto")
    project_info_cmd.add_argument("id", type=int, help="ID del proyecto")
    project_delete = project_sub.add_parser("delete", help="Eliminar un proyecto")
    project_delete.add_argument("id", type=int, help="ID del proyecto")

    # Subcomando: alerts
    alerts_parser = subparsers.add_parser(
        "alerts",
        help="Gestionar alertas",
    )
    alerts_sub = alerts_parser.add_subparsers(dest="subcommand")

    alerts_list = alerts_sub.add_parser("list", help="Listar alertas")
    alerts_list.add_argument("--project", "-p", type=int, help="ID del proyecto")
    alerts_list.add_argument(
        "--severity", "-s",
        choices=["critical", "warning", "info", "hint"],
        help="Filtrar por severidad"
    )
    alerts_list.add_argument(
        "--status",
        choices=["open", "resolved", "dismissed"],
        help="Filtrar por estado"
    )

    alerts_show = alerts_sub.add_parser("show", help="Mostrar alerta")
    alerts_show.add_argument("id", type=int, help="ID de la alerta")

    alerts_resolve = alerts_sub.add_parser("resolve", help="Resolver alerta")
    alerts_resolve.add_argument("id", type=int, help="ID de la alerta")
    alerts_resolve.add_argument("--note", "-n", type=str, default="", help="Nota de resolución")

    alerts_dismiss = alerts_sub.add_parser("dismiss", help="Descartar alerta")
    alerts_dismiss.add_argument("id", type=int, help="ID de la alerta")
    alerts_dismiss.add_argument("--note", "-n", type=str, default="", help="Motivo de descarte")

    # Subcomando: entities
    entities_parser = subparsers.add_parser(
        "entities",
        help="Gestionar entidades",
    )
    entities_sub = entities_parser.add_subparsers(dest="subcommand")

    entities_list = entities_sub.add_parser("list", help="Listar entidades")
    entities_list.add_argument("--project", "-p", type=int, help="ID del proyecto")
    entities_list.add_argument("--type", "-t", choices=["character", "location", "organization"], help="Filtrar por tipo")

    entities_show = entities_sub.add_parser("show", help="Mostrar entidad")
    entities_show.add_argument("id", type=int, help="ID de la entidad")

    entities_suggest = entities_sub.add_parser("suggest-merges", help="Sugerir fusiones")
    entities_suggest.add_argument("--project", "-p", type=int, help="ID del proyecto")

    # Subcomando: export
    export_parser = subparsers.add_parser(
        "export",
        help="Exportar datos",
    )
    export_sub = export_parser.add_subparsers(dest="subcommand")

    export_sheet = export_sub.add_parser("character-sheet", help="Ficha de personaje")
    export_sheet.add_argument("entity_id", type=int, help="ID de la entidad")
    export_sheet.add_argument("--format", "-f", choices=["md", "json"], default="md", help="Formato")
    export_sheet.add_argument("--output", "-o", type=Path, help="Archivo de salida")

    export_style = export_sub.add_parser("style-guide", help="Guía de estilo")
    export_style.add_argument("--project", "-p", type=int, help="ID del proyecto")
    export_style.add_argument("--format", "-f", choices=["md", "json"], default="md", help="Formato")
    export_style.add_argument("--output", "-o", type=Path, help="Archivo de salida")

    export_report = export_sub.add_parser("full-report", help="Reporte completo")
    export_report.add_argument("--project", "-p", type=int, help="ID del proyecto")
    export_report.add_argument("--output", "-o", type=Path, help="Archivo de salida")

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.command == "verify":
        return cmd_verify()
    elif args.command == "info":
        return cmd_info()
    elif args.command == "analyze":
        return cmd_analyze(args.document, args.project)
    elif args.command == "project":
        return cmd_project(args)
    elif args.command == "alerts":
        return cmd_alerts(args)
    elif args.command == "entities":
        return cmd_entities(args)
    elif args.command == "export":
        return cmd_export(args)
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
    print(f"  Duración: {format_duration(report.duration_seconds)}")
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


def cmd_project(args) -> int:
    """Gestiona proyectos."""
    from .persistence.project import get_project_repository

    repo = get_project_repository()

    if args.subcommand == "list":
        result = repo.get_all()
        if result.is_failure:
            print(f"Error: {result.error.user_message}")
            return 1

        projects = result.value
        if not projects:
            print("No hay proyectos.")
            return 0

        print(f"{'ID':<6} {'Nombre':<30} {'Creado':<20}")
        print("-" * 60)
        for p in projects:
            created = p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "N/A"
            print(f"{p.id:<6} {p.name[:30]:<30} {created:<20}")

    elif args.subcommand == "info":
        result = repo.get(args.id)
        if result.is_failure:
            print(f"Proyecto {args.id} no encontrado")
            return 1

        p = result.value
        print(f"ID: {p.id}")
        print(f"Nombre: {p.name}")
        print(f"Creado: {p.created_at}")
        if p.source_file:
            print(f"Archivo fuente: {p.source_file}")

    elif args.subcommand == "delete":
        result = repo.delete(args.id)
        if result.is_failure:
            print(f"Error al eliminar proyecto: {result.error.user_message}")
            return 1
        print(f"Proyecto {args.id} eliminado.")

    else:
        print("Subcomando no reconocido. Usa: list, info <id>, delete <id>")
        return 1

    return 0


def cmd_alerts(args) -> int:
    """Gestiona alertas."""
    from .alerts.engine import get_alert_engine
    from .alerts.models import AlertSeverity, AlertStatus, AlertFilter

    engine = get_alert_engine()

    if args.subcommand == "list":
        project_id = args.project or 1

        # Construir filtro
        alert_filter = AlertFilter()
        if args.severity:
            alert_filter.severities = [AlertSeverity(args.severity)]
        if args.status:
            status_map = {
                "open": [AlertStatus.NEW, AlertStatus.OPEN, AlertStatus.IN_PROGRESS],
                "resolved": [AlertStatus.RESOLVED, AlertStatus.AUTO_RESOLVED],
                "dismissed": [AlertStatus.DISMISSED],
            }
            alert_filter.statuses = status_map.get(args.status, [])

        result = engine.get_alerts(project_id, alert_filter)
        if result.is_failure:
            print(f"Error: {result.error.user_message}")
            return 1

        alerts = result.value
        if not alerts:
            print("No hay alertas.")
            return 0

        print(f"{'ID':<6} {'Sev.':<10} {'Categoría':<15} {'Título':<40}")
        print("-" * 75)
        for a in alerts[:30]:  # Limitar a 30
            print(f"{a.id:<6} {a.severity.value:<10} {a.category.value:<15} {a.title[:40]:<40}")

        if len(alerts) > 30:
            print(f"... y {len(alerts) - 30} alertas más")

    elif args.subcommand == "show":
        result = engine.get_alert(args.id)
        if result.is_failure:
            print(f"Alerta {args.id} no encontrada")
            return 1

        a = result.value
        print(f"ID: {a.id}")
        print(f"Título: {a.title}")
        print(f"Descripción: {a.description}")
        print(f"Explicación: {a.explanation}")
        print(f"Categoría: {a.category.value}")
        print(f"Severidad: {a.severity.value}")
        print(f"Estado: {a.status.value}")
        print(f"Confianza: {a.confidence:.0%}")
        if a.chapter:
            print(f"Capítulo: {a.chapter}")
        if a.suggestion:
            print(f"Sugerencia: {a.suggestion}")
        if a.excerpt:
            print(f"Extracto: «{a.excerpt[:100]}...»")

    elif args.subcommand == "resolve":
        result = engine.resolve_alert(args.id, args.note)
        if result.is_failure:
            print(f"Error: {result.error.user_message}")
            return 1
        print(f"Alerta {args.id} marcada como resuelta.")

    elif args.subcommand == "dismiss":
        result = engine.dismiss_alert(args.id, args.note)
        if result.is_failure:
            print(f"Error: {result.error.user_message}")
            return 1
        print(f"Alerta {args.id} descartada.")

    else:
        print("Subcomando no reconocido. Usa: list, show <id>, resolve <id>, dismiss <id>")
        return 1

    return 0


def cmd_entities(args) -> int:
    """Gestiona entidades."""
    from .entities.repository import get_entity_repository
    from .entities.models import EntityType

    repo = get_entity_repository()

    if args.subcommand == "list":
        project_id = args.project or 1
        entities = repo.get_by_project(project_id)

        if args.type:
            type_map = {
                "character": EntityType.CHARACTER,
                "location": EntityType.LOCATION,
                "organization": EntityType.ORGANIZATION,
            }
            filter_type = type_map.get(args.type)
            if filter_type:
                entities = [e for e in entities if e.entity_type == filter_type]

        if not entities:
            print("No hay entidades.")
            return 0

        print(f"{'ID':<6} {'Nombre':<30} {'Tipo':<15} {'Import.':<10}")
        print("-" * 65)
        for e in entities[:50]:  # Limitar a 50
            print(f"{e.id:<6} {e.canonical_name[:30]:<30} {e.entity_type.value:<15} {e.importance.value:<10}")

        if len(entities) > 50:
            print(f"... y {len(entities) - 50} entidades más")

    elif args.subcommand == "show":
        entity = repo.get(args.id)
        if not entity:
            print(f"Entidad {args.id} no encontrada")
            return 1

        print(f"ID: {entity.id}")
        print(f"Nombre canónico: {entity.canonical_name}")
        print(f"Tipo: {entity.entity_type.value}")
        print(f"Importancia: {entity.importance.value}")
        if entity.aliases:
            print(f"Aliases: {', '.join(entity.aliases)}")
        if entity.attributes:
            print(f"Atributos: {len(entity.attributes)}")

    elif args.subcommand == "suggest-merges":
        from .entities.semantic_fusion import get_fusion_engine

        project_id = args.project or 1
        engine = get_fusion_engine()
        entities = repo.get_by_project(project_id)

        if len(entities) < 2:
            print("Se necesitan al menos 2 entidades para sugerir fusiones.")
            return 0

        suggestions = engine.find_fusion_candidates(entities, similarity_threshold=0.7)

        if not suggestions:
            print("No se encontraron candidatos para fusión.")
            return 0

        print("Candidatos para fusión:")
        print("-" * 60)
        for s in suggestions[:10]:
            print(f"  {s.entity1.canonical_name} <-> {s.entity2.canonical_name}")
            print(f"    Similitud: {s.similarity:.0%} - {s.reason}")
            print()

        if len(suggestions) > 10:
            print(f"... y {len(suggestions) - 10} sugerencias más")

    else:
        print("Subcomando no reconocido. Usa: list, show <id>, suggest-merges")
        return 1

    return 0


def cmd_export(args) -> int:
    """Exporta datos."""
    if args.subcommand == "character-sheet":
        from .entities.repository import get_entity_repository
        from .exporters.character_sheets import (
            CharacterSheet,
            AttributeInfo,
            MentionInfo,
        )

        repo = get_entity_repository()
        entity = repo.get(args.entity_id)

        if not entity:
            print(f"Entidad {args.entity_id} no encontrada")
            return 1

        # Crear ficha básica
        sheet = CharacterSheet(
            entity_id=entity.id or 0,
            canonical_name=entity.canonical_name,
            aliases=entity.aliases or [],
            entity_type=entity.entity_type.value,
            importance=entity.importance.value,
            physical_attributes=[],
            psychological_attributes=[],
            other_attributes=[],
            mentions=MentionInfo(
                total_mentions=0,
                chapters=[],
                mention_frequency={},
                first_appearance_chapter=None,
                last_appearance_chapter=None,
            ),
            project_id=entity.project_id or 0,
            confidence_score=0.0,
        )

        if args.format == "json":
            output = sheet.to_json()
        else:
            output = sheet.to_markdown()

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Ficha exportada a {args.output}")
        else:
            print(output)

    elif args.subcommand == "style-guide":
        from .exporters.style_guide import generate_style_guide

        project_id = args.project or 1
        result = generate_style_guide(project_id, f"Proyecto {project_id}")

        if result.is_failure:
            print(f"Error: {result.error.user_message}")
            return 1

        guide = result.value
        if args.format == "json":
            output = guide.to_json()
        else:
            output = guide.to_markdown()

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Guía de estilo exportada a {args.output}")
        else:
            print(output)

    elif args.subcommand == "full-report":
        print("Reporte completo no implementado aún.")
        print("Usa 'analyze' para generar un análisis completo.")
        return 0

    else:
        print("Subcomando no reconocido. Usa: character-sheet, style-guide, full-report")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
