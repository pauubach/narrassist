"""
Funciones de exportación de informes de análisis.

Soporta exportación a JSON y Markdown para compartir
resultados de análisis con editores.

Compatible con:
- AnalysisReport (legacy)
- UnifiedReport (recomendado)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from ..alerts.models import Alert
from ..core.result import Result
from ..core.utils import format_duration
from ..entities.models import Entity

if TYPE_CHECKING:
    from ..core.errors import NarrativeError

logger = logging.getLogger(__name__)


@runtime_checkable
class ReportProtocol(Protocol):
    """Protocolo para informes de análisis (soporta legacy y unified)."""

    project_id: int
    session_id: int
    document_path: str
    entities: list
    alerts: list
    stats: dict
    errors: list
    warnings: list
    duration_seconds: float


def _get_fingerprint(report: ReportProtocol) -> str:
    """Obtiene el fingerprint del informe (compatible con ambos tipos)."""
    # UnifiedReport usa 'fingerprint', AnalysisReport usa 'document_fingerprint'
    return getattr(report, "document_fingerprint", None) or getattr(report, "fingerprint", "")


def export_report_json(report: ReportProtocol, output_path: str | Path) -> Result[None]:
    """
    Exporta informe de análisis a JSON.

    Args:
        report: Informe de análisis (AnalysisReport o UnifiedReport)
        output_path: Ruta del archivo de salida

    Returns:
        Result indicando éxito o fallo
    """
    try:
        path = Path(output_path)

        # Serializar informe
        data = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "project_id": report.project_id,
                "session_id": report.session_id,
                "document_path": report.document_path,
                "document_fingerprint": _get_fingerprint(report),
                "analysis_duration_seconds": report.duration_seconds,
            },
            "stats": report.stats,
            "entities": [_entity_to_dict(e) for e in report.entities],
            "alerts": [_alert_to_dict(a) for a in report.alerts],
            "errors": [
                {
                    "message": e.user_message,
                    "severity": e.severity.value,
                    "technical_details": e.technical_details,
                }
                for e in report.errors
            ],
            "warnings": report.warnings,
        }

        # Escribir archivo
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Exported JSON report to {path}")
        return Result.success(None)

    except Exception as e:
        from ..core.errors import ErrorSeverity, NarrativeError

        error = NarrativeError(
            message=f"Failed to export JSON: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        return Result.failure(error)


def export_report_markdown(report: ReportProtocol, output_path: str | Path) -> Result[None]:
    """
    Exporta informe de análisis a Markdown.

    Args:
        report: Informe de análisis (AnalysisReport o UnifiedReport)
        output_path: Ruta del archivo de salida

    Returns:
        Result indicando éxito o fallo
    """
    try:
        path = Path(output_path)

        # Generar Markdown
        lines = []

        # Encabezado
        lines.append("# Informe de Análisis - Narrative Assistant")
        lines.append("")
        lines.append(f"**Documento:** {Path(report.document_path).name}")
        lines.append(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Duración:** {format_duration(report.duration_seconds)}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Estadísticas
        lines.append("## Estadísticas del Documento")
        lines.append("")
        lines.append(f"- **Caracteres:** {report.stats.get('total_characters', 0):,}")
        lines.append(f"- **Capítulos:** {report.stats.get('chapters', 0)}")
        lines.append(f"- **Entidades detectadas:** {len(report.entities)}")
        lines.append(f"- **Atributos extraídos:** {report.stats.get('attributes_extracted', 0)}")
        lines.append(f"- **Inconsistencias:** {report.stats.get('inconsistencies_found', 0)}")
        lines.append("")

        # Entidades por tipo
        if report.entities:
            lines.append("### Entidades por Tipo")
            lines.append("")
            entity_types: dict[str, int] = {}
            for e in report.entities:
                entity_types[e.entity_type] = entity_types.get(e.entity_type, 0) + 1

            for etype, count in sorted(entity_types.items(), key=lambda x: -x[1]):
                lines.append(f"- **{etype.upper()}:** {count}")
            lines.append("")

        # Alertas
        lines.append("## Alertas")
        lines.append("")
        lines.append(f"**Total:** {len(report.alerts)}")
        lines.append("")

        # Alertas críticas
        critical = [a for a in report.alerts if a.severity.value == "critical"]
        if critical:
            lines.append(f"### Alertas Críticas ({len(critical)})")
            lines.append("")
            for i, alert in enumerate(critical, 1):
                lines.extend(_alert_to_markdown(alert, i))
            lines.append("")

        # Advertencias
        warnings = [a for a in report.alerts if a.severity.value == "warning"]
        if warnings:
            lines.append(f"### Advertencias ({len(warnings)})")
            lines.append("")
            for i, alert in enumerate(warnings, 1):
                lines.extend(_alert_to_markdown(alert, i))
            lines.append("")

        # Informativas
        info = [a for a in report.alerts if a.severity.value == "info"]
        if info:
            lines.append(f"### Informativas ({len(info)})")
            lines.append("")
            for i, alert in enumerate(info, 1):
                lines.extend(_alert_to_markdown(alert, i))
            lines.append("")

        # Entidades detectadas
        if report.entities:
            lines.append("## Entidades Detectadas")
            lines.append("")

            # Agrupar por tipo
            by_type: dict[str, list[Entity]] = {}
            for e in report.entities:
                if e.entity_type not in by_type:
                    by_type[e.entity_type] = []
                by_type[e.entity_type].append(e)

            for etype in sorted(by_type.keys()):
                entities = by_type[etype]
                lines.append(f"### {etype.upper()} ({len(entities)})")
                lines.append("")
                for entity in sorted(entities, key=lambda x: x.canonical_name):
                    lines.append(f"- **{entity.canonical_name}**")
                    if entity.aliases:
                        lines.append(f"  - Alias: {', '.join(entity.aliases)}")
                    lines.append(f"  - Confianza: {entity.confidence:.0%}")
                lines.append("")

        # Errores del sistema
        if report.errors:
            lines.append("## Advertencias del Sistema")
            lines.append("")
            for i, error in enumerate(report.errors, 1):
                lines.append(f"{i}. {error.user_message}")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append(
            f"*Informe generado por Narrative Assistant el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        )
        lines.append("")

        # Escribir archivo
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Exported Markdown report to {path}")
        return Result.success(None)

    except Exception as e:
        from ..core.errors import ErrorSeverity, NarrativeError

        error = NarrativeError(
            message=f"Failed to export Markdown: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        return Result.failure(error)


def export_alerts_json(alerts: list[Alert], output_path: str | Path) -> Result[None]:
    """
    Exporta solo las alertas a JSON.

    Args:
        alerts: Lista de alertas
        output_path: Ruta del archivo de salida

    Returns:
        Result indicando éxito o fallo
    """
    try:
        path = Path(output_path)

        data = {
            "export_date": datetime.now().isoformat(),
            "total_alerts": len(alerts),
            "alerts": [_alert_to_dict(a) for a in alerts],
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Exported {len(alerts)} alerts to {path}")
        return Result.success(None)

    except Exception as e:
        from ..core.errors import ErrorSeverity, NarrativeError

        error = NarrativeError(
            message=f"Failed to export alerts JSON: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        return Result.failure(error)


def _entity_to_dict(entity: Entity) -> dict[str, Any]:
    """Convierte Entity a diccionario JSON-serializable."""
    return {
        "id": entity.id,
        "type": entity.entity_type,
        "name": entity.canonical_name,
        "aliases": entity.aliases,
        "confidence": entity.confidence,
    }


def _alert_to_dict(alert: Alert) -> dict[str, Any]:
    """Convierte Alert a diccionario JSON-serializable."""
    return {
        "id": alert.id,
        "category": alert.category.value,
        "severity": alert.severity.value,
        "type": alert.alert_type,
        "title": alert.title,
        "description": alert.description,
        "explanation": alert.explanation,
        "suggestion": alert.suggestion,
        "chapter": alert.chapter,
        "scene": alert.scene,
        "excerpt": alert.excerpt,
        "entity_ids": alert.entity_ids,
        "confidence": alert.confidence,
        "status": alert.status.value,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
    }


def _alert_to_markdown(alert: Alert, index: int) -> list[str]:
    """Convierte Alert a líneas de Markdown."""
    lines = []
    lines.append(f"#### {index}. {alert.title}")
    lines.append("")
    lines.append(f"**Descripción:** {alert.description}")
    lines.append("")
    lines.append(f"**Explicación:** {alert.explanation}")
    lines.append("")
    if alert.suggestion:
        lines.append(f"**Sugerencia:** {alert.suggestion}")
        lines.append("")
    if alert.chapter:
        lines.append(f"**Ubicación:** Capítulo {alert.chapter}")
        if alert.scene:
            lines.append(f", Escena {alert.scene}")
        lines.append("")
    if alert.excerpt:
        lines.append("**Extracto:**")
        lines.append("```")
        lines.append(alert.excerpt[:200])  # Máximo 200 caracteres
        if len(alert.excerpt) > 200:
            lines.append("...")
        lines.append("```")
        lines.append("")
    lines.append(f"**Confianza:** {alert.confidence:.0%}")
    lines.append("")
    return lines
