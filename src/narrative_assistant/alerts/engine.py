"""
Motor centralizado de alertas.

Recibe alertas de todos los detectores, las clasifica, prioriza
y gestiona su ciclo de vida.
"""

import logging
import threading
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Optional

from ..core.result import Result
from ..analysis.attribute_consistency import get_attribute_display_name
from .models import Alert, AlertCategory, AlertFilter, AlertSeverity, AlertStatus
from .repository import AlertRepository, get_alert_repository

logger = logging.getLogger(__name__)

# Lock para thread-safety en singleton
_engine_lock = threading.Lock()
_alert_engine: Optional["AlertEngine"] = None


class AlertEngine:
    """
    Motor centralizado para gestión de alertas.

    Características:
    - Crea alertas desde diferentes detectores
    - Clasifica y prioriza automáticamente
    - Gestiona estados y transiciones
    - Filtra y busca alertas
    - Genera resúmenes y estadísticas
    """

    def __init__(self, repository: Optional[AlertRepository] = None):
        """
        Inicializa el motor de alertas.

        Args:
            repository: Repositorio de alertas (opcional, usa singleton por defecto)
        """
        self.repo = repository or get_alert_repository()
        self.alert_handlers: dict[str, Callable[[Any], Alert]] = {}

    def register_handler(
        self, alert_type: str, handler: Callable[[Any], Alert]
    ) -> None:
        """
        Registra un handler para convertir resultados de detector a alertas.

        Args:
            alert_type: Tipo de alerta (ej: "attribute_inconsistency")
            handler: Función que convierte resultado a Alert
        """
        self.alert_handlers[alert_type] = handler
        logger.debug(f"Registered handler for alert type: {alert_type}")

    def create_alert(
        self,
        project_id: int,
        category: AlertCategory,
        severity: AlertSeverity,
        alert_type: str,
        title: str,
        description: str,
        explanation: str,
        **kwargs,
    ) -> Result[Alert]:
        """
        Crea una nueva alerta.

        Args:
            project_id: ID del proyecto
            category: Categoría de la alerta
            severity: Severidad
            alert_type: Tipo específico
            title: Título breve
            description: Descripción corta
            explanation: Explicación detallada
            **kwargs: Campos opcionales (suggestion, chapter, entity_ids, etc.)

        Returns:
            Result con la alerta creada
        """
        alert = Alert(
            id=0,  # Se asignará por la DB
            project_id=project_id,
            category=category,
            severity=severity,
            alert_type=alert_type,
            title=title,
            description=description,
            explanation=explanation,
            suggestion=kwargs.get("suggestion"),
            chapter=kwargs.get("chapter"),
            scene=kwargs.get("scene"),
            start_char=kwargs.get("start_char"),
            end_char=kwargs.get("end_char"),
            excerpt=kwargs.get("excerpt", ""),
            entity_ids=kwargs.get("entity_ids", []),
            confidence=kwargs.get("confidence", 0.8),
            source_module=kwargs.get("source_module", ""),
            extra_data=kwargs.get("extra_data", {}),
        )

        return self.repo.create(alert)

    def create_alerts_batch(
        self, project_id: int, alerts_data: list[dict[str, Any]]
    ) -> Result[list[Alert]]:
        """
        Crea múltiples alertas de una vez.

        Args:
            project_id: ID del proyecto
            alerts_data: Lista de diccionarios con datos de alertas

        Returns:
            Result con lista de alertas creadas
        """
        created_alerts = []
        errors = []

        for data in alerts_data:
            data["project_id"] = project_id
            result = self.create_alert(**data)

            if result.is_success:
                created_alerts.append(result.value)
            else:
                errors.append(result.error)

        if errors:
            logger.warning(f"Created {len(created_alerts)} alerts with {len(errors)} errors")
            return Result.partial(created_alerts, errors)

        logger.info(f"Created {len(created_alerts)} alerts for project {project_id}")
        return Result.success(created_alerts)

    def get_alerts(
        self, project_id: int, alert_filter: Optional[AlertFilter] = None
    ) -> Result[list[Alert]]:
        """
        Obtiene alertas con filtros opcionales.

        Args:
            project_id: ID del proyecto
            alert_filter: Filtro opcional

        Returns:
            Result con lista de alertas filtradas
        """
        result = self.repo.get_by_project(project_id)
        if result.is_failure:
            return result

        alerts = result.value

        if alert_filter:
            alerts = [a for a in alerts if alert_filter.matches(a)]
            logger.debug(
                f"Filtered to {len(alerts)} alerts for project {project_id}"
            )

        return Result.success(alerts)

    def get_alert(self, alert_id: int) -> Result[Alert]:
        """
        Obtiene una alerta específica por ID.

        Args:
            alert_id: ID de la alerta

        Returns:
            Result con la alerta
        """
        return self.repo.get(alert_id)

    def update_alert_status(
        self,
        alert_id: int,
        status: AlertStatus,
        note: str = "",
    ) -> Result[Alert]:
        """
        Actualiza el estado de una alerta.

        Args:
            alert_id: ID de la alerta
            status: Nuevo estado
            note: Nota sobre la resolución

        Returns:
            Result con la alerta actualizada
        """
        result = self.repo.get(alert_id)
        if result.is_failure:
            return result

        alert = result.value
        old_status = alert.status

        alert.status = status
        alert.resolution_note = note

        if status in [AlertStatus.RESOLVED, AlertStatus.DISMISSED, AlertStatus.AUTO_RESOLVED]:
            alert.resolved_at = datetime.now()

        result = self.repo.update(alert)

        if result.is_success:
            logger.info(
                f"Alert {alert_id} status changed: {old_status.value} → {status.value}"
            )

        return result

    def dismiss_alert(self, alert_id: int, reason: str = "") -> Result[Alert]:
        """Descarta una alerta (falso positivo)."""
        return self.update_alert_status(
            alert_id, AlertStatus.DISMISSED, f"Descartada: {reason}"
        )

    def resolve_alert(self, alert_id: int, resolution: str = "") -> Result[Alert]:
        """Marca una alerta como resuelta."""
        return self.update_alert_status(
            alert_id, AlertStatus.RESOLVED, f"Resuelto: {resolution}"
        )

    def acknowledge_alert(self, alert_id: int) -> Result[Alert]:
        """Marca una alerta como vista/reconocida."""
        return self.update_alert_status(
            alert_id, AlertStatus.ACKNOWLEDGED, "Usuario vio la alerta"
        )

    def get_summary(self, project_id: int) -> Result[dict[str, Any]]:
        """
        Genera resumen estadístico de alertas.

        Args:
            project_id: ID del proyecto

        Returns:
            Result con diccionario de estadísticas
        """
        result = self.repo.get_by_project(project_id)
        if result.is_failure:
            return result

        alerts = result.value

        summary = {
            "total": len(alerts),
            "open": sum(1 for a in alerts if a.is_open()),
            "closed": sum(1 for a in alerts if a.is_closed()),
            "by_category": defaultdict(int),
            "by_severity": defaultdict(int),
            "by_status": defaultdict(int),
            "by_chapter": defaultdict(int),
            "by_source": defaultdict(int),
        }

        for alert in alerts:
            summary["by_category"][alert.category.value] += 1
            summary["by_severity"][alert.severity.value] += 1
            summary["by_status"][alert.status.value] += 1
            summary["by_source"][alert.source_module] += 1
            if alert.chapter:
                summary["by_chapter"][alert.chapter] += 1

        # Convertir defaultdict a dict normal
        summary["by_category"] = dict(summary["by_category"])
        summary["by_severity"] = dict(summary["by_severity"])
        summary["by_status"] = dict(summary["by_status"])
        summary["by_chapter"] = dict(summary["by_chapter"])
        summary["by_source"] = dict(summary["by_source"])

        return Result.success(summary)

    def prioritize_alerts(self, alerts: list[Alert]) -> list[Alert]:
        """
        Ordena alertas por prioridad.

        Criterios:
        1. Severidad (CRITICAL > WARNING > INFO > HINT)
        2. Confianza (mayor primero)
        3. Capítulo (orden de aparición)

        Args:
            alerts: Lista de alertas sin ordenar

        Returns:
            Lista ordenada por prioridad
        """
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.WARNING: 1,
            AlertSeverity.INFO: 2,
            AlertSeverity.HINT: 3,
        }

        return sorted(
            alerts,
            key=lambda a: (
                severity_order.get(a.severity, 4),
                -a.confidence,
                a.chapter or 0,
            ),
        )

    def calculate_severity_from_confidence(self, confidence: float) -> AlertSeverity:
        """
        Calcula severidad automáticamente basada en confianza.

        Args:
            confidence: Nivel de confianza (0.0-1.0)

        Returns:
            Severidad calculada
        """
        if confidence >= 0.9:
            return AlertSeverity.CRITICAL
        elif confidence >= 0.7:
            return AlertSeverity.WARNING
        elif confidence >= 0.5:
            return AlertSeverity.INFO
        else:
            return AlertSeverity.HINT

    def delete_alert(self, alert_id: int) -> Result[None]:
        """
        Elimina una alerta permanentemente.

        Args:
            alert_id: ID de la alerta

        Returns:
            Result indicando éxito o fallo
        """
        return self.repo.delete(alert_id)

    # --- Métodos helper para crear alertas desde detectores específicos ---

    def create_from_attribute_inconsistency(
        self,
        project_id: int,
        entity_name: str,
        entity_id: int,
        attribute_key: str,
        value1: str,
        value2: str,
        value1_source: dict[str, Any],
        value2_source: dict[str, Any],
        explanation: str,
        confidence: float = 0.9,
    ) -> Result[Alert]:
        """
        Crea alerta desde inconsistencia de atributo.

        IMPORTANTE: Incluye referencias a ubicaciones para mostrar:
        "Capítulo X: 'valor1' vs Capítulo Y: 'valor2'"

        Args:
            value1_source, value2_source: Deben incluir:
                - chapter: int
                - page: int (calculado con calculate_page_and_line)
                - line: int (calculado con calculate_page_and_line)
                - start_char: int
                - end_char: int
                - text/excerpt: str

        Example:
            value1_source = {
                "chapter": 2,
                "page": 14,
                "line": 5,
                "start_char": 1234,
                "end_char": 1280,
                "excerpt": "ojos azules"
            }
        """
        severity = self.calculate_severity_from_confidence(confidence)

        # Construir descripción con referencias mejoradas
        ref1 = f"Cap. {value1_source.get('chapter', '?')}"
        if "page" in value1_source:
            ref1 += f", pág. {value1_source['page']}"
        if "line" in value1_source:
            ref1 += f", lín. {value1_source['line']}"

        ref2 = f"Cap. {value2_source.get('chapter', '?')}"
        if "page" in value2_source:
            ref2 += f", pág. {value2_source['page']}"
        if "line" in value2_source:
            ref2 += f", lín. {value2_source['line']}"

        # Estructura sources[] para frontend
        sources = [
            {
                "chapter": value1_source.get("chapter"),
                "page": value1_source.get("page", 1),
                "line": value1_source.get("line", 1),
                "start_char": value1_source.get("start_char", value1_source.get("position", 0)),
                "end_char": value1_source.get("end_char", value1_source.get("start_char", 0) + 100),
                "excerpt": value1_source.get("text", value1_source.get("excerpt", "")),
                "value": value1,
            },
            {
                "chapter": value2_source.get("chapter"),
                "page": value2_source.get("page", 1),
                "line": value2_source.get("line", 1),
                "start_char": value2_source.get("start_char", value2_source.get("position", 0)),
                "end_char": value2_source.get("end_char", value2_source.get("start_char", 0) + 100),
                "excerpt": value2_source.get("text", value2_source.get("excerpt", "")),
                "value": value2,
            },
        ]

        # Traducir nombre del atributo para mostrar en español
        from ..nlp.attributes import AttributeKey
        try:
            attr_key_enum = AttributeKey(attribute_key)
            display_name = get_attribute_display_name(attr_key_enum)
        except (ValueError, KeyError):
            display_name = attribute_key.replace("_", " ")

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.CONSISTENCY,
            severity=severity,
            alert_type="attribute_inconsistency",
            title=f"Inconsistencia: {display_name} de {entity_name}",
            description=f"{ref1}: '{value1}' vs {ref2}: '{value2}'",
            explanation=explanation,
            suggestion=f"Verificar cuál es el valor correcto para {display_name}",
            chapter=value1_source.get("chapter"),
            entity_ids=[entity_id],
            confidence=confidence,
            source_module="attribute_consistency",
            extra_data={
                "entity_name": entity_name,
                "attribute_key": attribute_key,
                "value1": value1,
                "value2": value2,
                # ✅ Nueva estructura sources[] (consistente, fácil de usar en UI)
                "sources": sources,
                # ⚠️ Deprecated: mantener por compatibilidad temporal
                "value1_source": value1_source,
                "value2_source": value2_source,
            },
        )

    def create_from_spelling_issue(
        self,
        project_id: int,
        word: str,
        start_char: int,
        end_char: int,
        sentence: str,
        error_type: str,
        suggestions: list[str],
        confidence: float,
        explanation: str,
        chapter: Optional[int] = None,
    ) -> Result[Alert]:
        """
        Crea alerta desde un error ortográfico.

        Args:
            project_id: ID del proyecto
            word: Palabra con error
            start_char: Posición inicio
            end_char: Posición fin
            sentence: Oración de contexto
            error_type: Tipo de error (typo, accent, etc.)
            suggestions: Sugerencias de corrección
            confidence: Confianza (0.0-1.0)
            explanation: Explicación del error
            chapter: Número de capítulo (opcional)

        Returns:
            Result con la alerta creada
        """
        severity = self.calculate_severity_from_confidence(confidence)

        suggestion_text = None
        if suggestions:
            suggestion_text = f"Sugerencias: {', '.join(suggestions[:3])}"

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.ORTHOGRAPHY,
            severity=severity,
            alert_type=f"spelling_{error_type}",
            title=f"Error ortográfico: '{word}'",
            description=explanation,
            explanation=f"En contexto: «{sentence[:100]}...»" if len(sentence) > 100 else f"En contexto: «{sentence}»",
            suggestion=suggestion_text,
            chapter=chapter,
            start_char=start_char,
            end_char=end_char,
            excerpt=sentence,
            confidence=confidence,
            source_module="spelling_checker",
            extra_data={
                "word": word,
                "error_type": error_type,
                "suggestions": suggestions,
            },
        )

    def create_from_grammar_issue(
        self,
        project_id: int,
        text: str,
        start_char: int,
        end_char: int,
        sentence: str,
        error_type: str,
        suggestion: Optional[str],
        confidence: float,
        explanation: str,
        rule_id: str = "",
        chapter: Optional[int] = None,
    ) -> Result[Alert]:
        """
        Crea alerta desde un error gramatical.

        Args:
            project_id: ID del proyecto
            text: Fragmento con error
            start_char: Posición inicio
            end_char: Posición fin
            sentence: Oración de contexto
            error_type: Tipo de error (gender_agreement, etc.)
            suggestion: Corrección sugerida
            confidence: Confianza (0.0-1.0)
            explanation: Explicación del error
            rule_id: ID de la regla gramatical
            chapter: Número de capítulo (opcional)

        Returns:
            Result con la alerta creada
        """
        severity = self.calculate_severity_from_confidence(confidence)

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.GRAMMAR,
            severity=severity,
            alert_type=f"grammar_{error_type}",
            title=f"Error gramatical: {explanation[:50]}",
            description=f"'{text}' → '{suggestion}'" if suggestion else f"'{text}'",
            explanation=f"En contexto: «{sentence[:100]}...»" if len(sentence) > 100 else f"En contexto: «{sentence}»",
            suggestion=suggestion,
            chapter=chapter,
            start_char=start_char,
            end_char=end_char,
            excerpt=sentence,
            confidence=confidence,
            source_module="grammar_checker",
            extra_data={
                "text": text,
                "error_type": error_type,
                "rule_id": rule_id,
            },
        )

    def create_alerts_from_spelling_report(
        self,
        project_id: int,
        report: Any,  # SpellingReport
        chapter: Optional[int] = None,
        min_confidence: float = 0.5,
    ) -> Result[list[Alert]]:
        """
        Crea alertas desde un SpellingReport completo.

        Args:
            project_id: ID del proyecto
            report: SpellingReport con los issues
            chapter: Número de capítulo (opcional)
            min_confidence: Confianza mínima para crear alertas

        Returns:
            Result con lista de alertas creadas
        """
        alerts_data = []

        for issue in report.issues:
            if issue.confidence < min_confidence:
                continue

            alerts_data.append({
                "category": AlertCategory.ORTHOGRAPHY,
                "severity": self.calculate_severity_from_confidence(issue.confidence),
                "alert_type": f"spelling_{issue.error_type.value}",
                "title": f"Error ortográfico: '{issue.word}'",
                "description": issue.explanation,
                "explanation": f"En contexto: «{issue.sentence[:100]}...»" if len(issue.sentence) > 100 else f"En contexto: «{issue.sentence}»",
                "suggestion": f"Sugerencias: {', '.join(issue.suggestions[:3])}" if issue.suggestions else None,
                "chapter": chapter,
                "start_char": issue.start_char,
                "end_char": issue.end_char,
                "excerpt": issue.sentence,
                "confidence": issue.confidence,
                "source_module": "spelling_checker",
                "extra_data": {
                    "word": issue.word,
                    "error_type": issue.error_type.value,
                    "suggestions": issue.suggestions,
                },
            })

        return self.create_alerts_batch(project_id, alerts_data)

    def create_alerts_from_grammar_report(
        self,
        project_id: int,
        report: Any,  # GrammarReport
        chapter: Optional[int] = None,
        min_confidence: float = 0.5,
    ) -> Result[list[Alert]]:
        """
        Crea alertas desde un GrammarReport completo.

        Args:
            project_id: ID del proyecto
            report: GrammarReport con los issues
            chapter: Número de capítulo (opcional)
            min_confidence: Confianza mínima para crear alertas

        Returns:
            Result con lista de alertas creadas
        """
        alerts_data = []

        for issue in report.issues:
            if issue.confidence < min_confidence:
                continue

            alerts_data.append({
                "category": AlertCategory.GRAMMAR,
                "severity": self.calculate_severity_from_confidence(issue.confidence),
                "alert_type": f"grammar_{issue.error_type.value}",
                "title": f"Error gramatical: {issue.explanation[:50]}",
                "description": f"'{issue.text}' → '{issue.suggestion}'" if issue.suggestion else f"'{issue.text}'",
                "explanation": f"En contexto: «{issue.sentence[:100]}...»" if len(issue.sentence) > 100 else f"En contexto: «{issue.sentence}»",
                "suggestion": issue.suggestion,
                "chapter": chapter,
                "start_char": issue.start_char,
                "end_char": issue.end_char,
                "excerpt": issue.sentence,
                "confidence": issue.confidence,
                "source_module": "grammar_checker",
                "extra_data": {
                    "text": issue.text,
                    "error_type": issue.error_type.value,
                    "rule_id": issue.rule_id,
                },
            })

        return self.create_alerts_batch(project_id, alerts_data)

    # --- Métodos para módulos de análisis narrativo ---

    def create_from_temporal_inconsistency(
        self,
        project_id: int,
        inconsistency_type: str,
        description: str,
        explanation: str,
        chapter: int,
        start_char: int,
        end_char: int,
        excerpt: str,
        confidence: float = 0.8,
        entity_ids: Optional[list[int]] = None,
        extra_data: Optional[dict[str, Any]] = None,
    ) -> Result[Alert]:
        """
        Crea alerta desde inconsistencia temporal.

        Args:
            project_id: ID del proyecto
            inconsistency_type: Tipo (timeline_gap, duration_conflict, etc.)
            description: Descripción corta
            explanation: Explicación detallada
            chapter: Número de capítulo
            start_char: Posición inicio
            end_char: Posición fin
            excerpt: Extracto del texto
            confidence: Confianza (0.0-1.0)
            entity_ids: IDs de entidades involucradas
            extra_data: Datos adicionales

        Returns:
            Result con la alerta creada
        """
        severity = self.calculate_severity_from_confidence(confidence)

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.TIMELINE_ISSUE,
            severity=severity,
            alert_type=f"temporal_{inconsistency_type}",
            title=f"Inconsistencia temporal: {inconsistency_type}",
            description=description,
            explanation=explanation,
            suggestion="Revisar la coherencia temporal de los eventos",
            chapter=chapter,
            start_char=start_char,
            end_char=end_char,
            excerpt=excerpt,
            entity_ids=entity_ids or [],
            confidence=confidence,
            source_module="temporal_analysis",
            extra_data=extra_data or {},
        )

    def create_from_voice_deviation(
        self,
        project_id: int,
        entity_id: int,
        entity_name: str,
        deviation_type: str,
        expected_value: str,
        actual_value: str,
        description: str,
        explanation: str,
        chapter: int,
        start_char: int,
        end_char: int,
        excerpt: str,
        confidence: float = 0.7,
        extra_data: Optional[dict[str, Any]] = None,
    ) -> Result[Alert]:
        """
        Crea alerta desde desviación del perfil de voz.

        Args:
            project_id: ID del proyecto
            entity_id: ID del personaje
            entity_name: Nombre del personaje
            deviation_type: Tipo (formality_shift, vocabulary_anomaly, etc.)
            expected_value: Valor esperado según perfil
            actual_value: Valor detectado
            description: Descripción corta
            explanation: Explicación detallada
            chapter: Número de capítulo
            start_char: Posición inicio
            end_char: Posición fin
            excerpt: Diálogo o texto con la desviación
            confidence: Confianza (0.0-1.0)
            extra_data: Datos adicionales

        Returns:
            Result con la alerta creada
        """
        severity = self.calculate_severity_from_confidence(confidence)

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.VOICE_DEVIATION,
            severity=severity,
            alert_type=f"voice_{deviation_type}",
            title=f"Desviación de voz: {entity_name}",
            description=description,
            explanation=explanation,
            suggestion=f"Verificar si {entity_name} hablaría así según su perfil",
            chapter=chapter,
            start_char=start_char,
            end_char=end_char,
            excerpt=excerpt,
            entity_ids=[entity_id],
            confidence=confidence,
            source_module="voice_deviation_detector",
            extra_data={
                "entity_name": entity_name,
                "deviation_type": deviation_type,
                "expected_value": expected_value,
                "actual_value": actual_value,
                **(extra_data or {}),
            },
        )

    def create_from_register_change(
        self,
        project_id: int,
        from_register: str,
        to_register: str,
        severity_level: str,
        chapter: int,
        position: int,
        context_before: str,
        context_after: str,
        explanation: str,
        confidence: float = 0.7,
    ) -> Result[Alert]:
        """
        Crea alerta desde cambio de registro narrativo.

        Args:
            project_id: ID del proyecto
            from_register: Registro anterior (formal_literary, colloquial, etc.)
            to_register: Registro nuevo
            severity_level: Severidad del cambio (high, medium, low)
            chapter: Número de capítulo
            position: Posición en el texto
            context_before: Texto antes del cambio
            context_after: Texto después del cambio
            explanation: Explicación del cambio
            confidence: Confianza (0.0-1.0)

        Returns:
            Result con la alerta creada
        """
        # Mapear severidad del detector a AlertSeverity
        severity_map = {
            "high": AlertSeverity.WARNING,
            "medium": AlertSeverity.INFO,
            "low": AlertSeverity.HINT,
        }
        severity = severity_map.get(severity_level, AlertSeverity.INFO)

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.STYLE,
            severity=severity,
            alert_type="register_change",
            title=f"Cambio de registro: {from_register} → {to_register}",
            description=f"Transición de registro {from_register} a {to_register}",
            explanation=explanation,
            suggestion="Verificar si el cambio de registro es intencional",
            chapter=chapter,
            start_char=position,
            end_char=position + len(context_after),
            excerpt=f"...{context_before[-50:]} | {context_after[:50]}...",
            confidence=confidence,
            source_module="register_change_detector",
            extra_data={
                "from_register": from_register,
                "to_register": to_register,
                "severity_level": severity_level,
                "context_before": context_before,
                "context_after": context_after,
            },
        )

    def create_from_focalization_violation(
        self,
        project_id: int,
        violation_type: str,
        declared_focalizer: str,
        violated_rule: str,
        description: str,
        explanation: str,
        chapter: int,
        start_char: int,
        end_char: int,
        excerpt: str,
        confidence: float = 0.8,
        entity_ids: Optional[list[int]] = None,
        extra_data: Optional[dict[str, Any]] = None,
    ) -> Result[Alert]:
        """
        Crea alerta desde violación de focalización.

        Args:
            project_id: ID del proyecto
            violation_type: Tipo (unauthorized_pov, omniscient_leak, etc.)
            declared_focalizer: Focalizador declarado
            violated_rule: Regla violada
            description: Descripción corta
            explanation: Explicación detallada
            chapter: Número de capítulo
            start_char: Posición inicio
            end_char: Posición fin
            excerpt: Texto con la violación
            confidence: Confianza (0.0-1.0)
            entity_ids: IDs de entidades involucradas
            extra_data: Datos adicionales

        Returns:
            Result con la alerta creada
        """
        severity = self.calculate_severity_from_confidence(confidence)

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.FOCALIZATION,
            severity=severity,
            alert_type=f"focalization_{violation_type}",
            title=f"Violación de focalización: {violation_type}",
            description=description,
            explanation=explanation,
            suggestion=f"El focalizador actual es {declared_focalizer}. {violated_rule}",
            chapter=chapter,
            start_char=start_char,
            end_char=end_char,
            excerpt=excerpt,
            entity_ids=entity_ids or [],
            confidence=confidence,
            source_module="focalization_validator",
            extra_data={
                "violation_type": violation_type,
                "declared_focalizer": declared_focalizer,
                "violated_rule": violated_rule,
                **(extra_data or {}),
            },
        )

    def create_from_speaker_attribution(
        self,
        project_id: int,
        dialogue_text: str,
        chapter: int,
        start_char: int,
        end_char: int,
        attribution_confidence: str,
        possible_speakers: list[str],
        context: str,
        extra_data: Optional[dict[str, Any]] = None,
    ) -> Result[Alert]:
        """
        Crea alerta para diálogo con atribución ambigua.

        Args:
            project_id: ID del proyecto
            dialogue_text: Texto del diálogo
            chapter: Número de capítulo
            start_char: Posición inicio
            end_char: Posición fin
            attribution_confidence: Nivel de confianza (unknown, low)
            possible_speakers: Lista de posibles hablantes
            context: Contexto narrativo
            extra_data: Datos adicionales

        Returns:
            Result con la alerta creada
        """
        # Solo crear alertas para atribución desconocida o baja
        if attribution_confidence not in ["unknown", "low"]:
            return Result.success(None)  # type: ignore

        severity = (
            AlertSeverity.WARNING
            if attribution_confidence == "unknown"
            else AlertSeverity.INFO
        )

        speakers_str = ", ".join(possible_speakers) if possible_speakers else "desconocido"

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.STYLE,
            severity=severity,
            alert_type="speaker_attribution_ambiguous",
            title="Hablante ambiguo en diálogo",
            description=f"No se pudo determinar quién dice: «{dialogue_text[:50]}...»",
            explanation=f"Posibles hablantes: {speakers_str}. Contexto: {context[:100]}",
            suggestion="Considerar añadir verbo de habla o clarificar el hablante",
            chapter=chapter,
            start_char=start_char,
            end_char=end_char,
            excerpt=dialogue_text,
            confidence=0.5 if attribution_confidence == "low" else 0.3,
            source_module="speaker_attribution",
            extra_data={
                "attribution_confidence": attribution_confidence,
                "possible_speakers": possible_speakers,
                "context": context,
                **(extra_data or {}),
            },
        )

    def create_from_emotional_incoherence(
        self,
        project_id: int,
        entity_name: str,
        incoherence_type: str,
        declared_emotion: str,
        actual_behavior: str,
        declared_text: str,
        behavior_text: str,
        explanation: str,
        confidence: float = 0.7,
        suggestion: Optional[str] = None,
        chapter: Optional[int] = None,
        start_char: Optional[int] = None,
        end_char: Optional[int] = None,
        entity_ids: Optional[list[int]] = None,
        extra_data: Optional[dict[str, Any]] = None,
    ) -> Result[Alert]:
        """
        Crea alerta desde incoherencia emocional.

        Args:
            project_id: ID del proyecto
            entity_name: Nombre del personaje
            incoherence_type: Tipo (emotion_dialogue, emotion_action, temporal_jump)
            declared_emotion: Emoción declarada
            actual_behavior: Comportamiento detectado
            declared_text: Texto donde se declara la emoción
            behavior_text: Texto del comportamiento
            explanation: Explicación de la incoherencia
            confidence: Confianza de la detección
            suggestion: Sugerencia de corrección
            chapter: Capítulo
            start_char: Posición inicial
            end_char: Posición final
            entity_ids: IDs de entidades involucradas
            extra_data: Datos adicionales

        Returns:
            Result con la alerta creada
        """
        severity = self.calculate_severity_from_confidence(confidence)

        # Mapear tipo de incoherencia a categoría
        category_map = {
            "emotion_dialogue": AlertCategory.VOICE_DEVIATION,
            "emotion_action": AlertCategory.CONSISTENCY,
            "temporal_jump": AlertCategory.TIMELINE_ISSUE,
            "narrator_bias": AlertCategory.STYLE,
        }
        category = category_map.get(incoherence_type, AlertCategory.CONSISTENCY)

        # Título según tipo
        title_map = {
            "emotion_dialogue": f"Incoherencia emocional en diálogo de {entity_name}",
            "emotion_action": f"Acción inconsistente con estado emocional de {entity_name}",
            "temporal_jump": f"Cambio emocional abrupto de {entity_name}",
            "narrator_bias": f"Inconsistencia del narrador sobre {entity_name}",
        }
        title = title_map.get(
            incoherence_type,
            f"Incoherencia emocional: {entity_name}"
        )

        return self.create_alert(
            project_id=project_id,
            category=category,
            severity=severity,
            alert_type=f"emotional_{incoherence_type}",
            title=title,
            description=f"'{entity_name}' está '{declared_emotion}' pero muestra comportamiento {actual_behavior}",
            explanation=explanation,
            suggestion=suggestion,
            chapter=chapter,
            start_char=start_char,
            end_char=end_char,
            excerpt=behavior_text[:200] if behavior_text else "",
            entity_ids=entity_ids or [],
            confidence=confidence,
            source_module="emotional_coherence",
            extra_data={
                "declared_emotion": declared_emotion,
                "actual_behavior": actual_behavior,
                "declared_text": declared_text[:200] if declared_text else "",
                "incoherence_type": incoherence_type,
                **(extra_data or {}),
            },
        )


def get_alert_engine() -> AlertEngine:
    """
    Obtiene la instancia singleton del motor de alertas.

    Thread-safe con double-checked locking.

    Returns:
        Instancia única de AlertEngine
    """
    global _alert_engine

    if _alert_engine is None:
        with _engine_lock:
            if _alert_engine is None:
                _alert_engine = AlertEngine()
                logger.debug("AlertEngine singleton initialized")

    return _alert_engine
