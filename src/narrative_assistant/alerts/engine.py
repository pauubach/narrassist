"""
Motor centralizado de alertas.

Recibe alertas de todos los detectores, las clasifica, prioriza
y gestiona su ciclo de vida.
"""

import logging
import threading
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from typing import Any, Optional

from ..analysis.attribute_consistency import get_attribute_display_name
from ..core.result import Result
from .formatter import AlertFormatter
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
    - Recalibra confianza según historial de descartes (BK-22)
    - Aplica pesos adaptativos per-project (nivel 3)
    """

    # Nivel 3: learning rate para pesos adaptativos por proyecto
    ADAPTIVE_LEARNING_RATE = 0.03
    ADAPTIVE_WEIGHT_FLOOR = 0.1
    ADAPTIVE_WEIGHT_CEIL = 1.0

    # BK-18: Tipos de alerta que aplican decay temporal
    DECAY_ALERT_TYPES = frozenset(
        {
            "attribute_inconsistency",
            "temporal_anachronism",
            "relationship_contradiction",
            "character_location_impossibility",
        }
    )
    DECAY_RATE = 0.97  # factor por capítulo de distancia
    DECAY_FLOOR = 0.15  # confianza mínima para evitar alertas vanishing

    def __init__(self, repository: AlertRepository | None = None):
        """
        Inicializa el motor de alertas.

        Args:
            repository: Repositorio de alertas (opcional, usa singleton por defecto)
        """
        self.repo = repository or get_alert_repository()
        self.alert_handlers: dict[str, Callable[[Any], Alert]] = {}
        # Cache de calibración en memoria: {(project_id, alert_type, source_module): factor}
        self._calibration_cache: dict[tuple[int, str, str], float] = {}
        # BK-18: Cache de total de capítulos por proyecto
        self._total_chapters_cache: dict[int, int] = {}
        # Nivel 3: Cache de pesos adaptativos: {(project_id, alert_type, entity_name): weight}
        self._adaptive_weights_cache: dict[tuple[int, str, str], float] = {}

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

        Aplica calibración automática: si el detector tiene un historial
        alto de descartes (falsos positivos), la confianza se reduce.

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
        original_confidence = kwargs.get("confidence", 0.8)
        source_module = kwargs.get("source_module", "")

        # Aplicar calibración de confianza (BK-22)
        factor = self._get_calibration_factor(project_id, alert_type, source_module)
        effective_confidence = original_confidence * factor

        # BK-18: Decay temporal — alertas de capítulos lejanos pierden confianza
        chapter = kwargs.get("chapter")
        if chapter is not None and alert_type in self.DECAY_ALERT_TYPES:
            total_chapters = kwargs.pop("_total_chapters", None)
            if total_chapters is None:
                total_chapters = self._get_total_chapters(project_id)
            if total_chapters > 0:
                chapter_distance = max(0, total_chapters - chapter)
                decay = self.DECAY_RATE**chapter_distance
                effective_confidence = max(
                    self.DECAY_FLOOR, effective_confidence * decay
                )

        # Nivel 3: Pesos adaptativos per-project/per-entity
        # Cascada: per-entity (si disponible) > project-level > 1.0
        extra_data = kwargs.get("extra_data", {})
        entity_names = []
        if isinstance(extra_data, dict):
            for key in ("entity_name", "entity1_name", "entity2_name"):
                name = extra_data.get(key, "")
                if name:
                    entity_names.append(name)
        if entity_names:
            # Promedio de pesos per-entity (para alertas multi-entidad)
            weights = [self._get_adaptive_weight(project_id, alert_type, n) for n in entity_names]
            adaptive_weight = sum(weights) / len(weights)
        else:
            adaptive_weight = self._get_adaptive_weight(project_id, alert_type, "")
        effective_confidence *= adaptive_weight

        effective_confidence = round(effective_confidence, 4)

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
            confidence=effective_confidence,
            source_module=source_module,
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
            logger.warning(
                f"Created {len(created_alerts)} alerts with {len(errors)} errors"
            )
            return Result.partial(created_alerts, errors)

        logger.info(f"Created {len(created_alerts)} alerts for project {project_id}")
        return Result.success(created_alerts)

    def get_alerts(
        self, project_id: int, alert_filter: AlertFilter | None = None
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
            alerts = [a for a in alerts if hasattr(alert_filter, 'matches') and alert_filter.matches(a)]
            logger.debug(f"Filtered to {len(alerts)} alerts for project {project_id}")

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
        old_status = getattr(alert, 'status', None)

        alert.status = status
        alert.resolution_note = note

        if status in [
            AlertStatus.RESOLVED,
            AlertStatus.DISMISSED,
            AlertStatus.AUTO_RESOLVED,
        ]:
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
            "open": sum(1 for a in alerts if hasattr(a, 'is_open') and a.is_open()),
            "closed": sum(1 for a in alerts if hasattr(a, 'is_closed') and a.is_closed()),
            "by_category": defaultdict(int),
            "by_severity": defaultdict(int),
            "by_status": defaultdict(int),
            "by_chapter": defaultdict(int),
            "by_source": defaultdict(int),
        }

        for alert in alerts:
            if hasattr(alert, 'category') and hasattr(alert.category, 'value'):
                summary["by_category"][alert.category.value] += 1
            if hasattr(alert, 'severity') and hasattr(alert.severity, 'value'):
                summary["by_severity"][alert.severity.value] += 1
            if hasattr(alert, 'status') and hasattr(alert.status, 'value'):
                summary["by_status"][alert.status.value] += 1
            if hasattr(alert, 'source_module'):
                summary["by_source"][alert.source_module] += 1
            if hasattr(alert, 'chapter') and alert.chapter:
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
        sources: list[dict[str, Any]] | None = None,
    ) -> Result[Alert]:
        """
        Crea alerta desde inconsistencia de atributo.

        Soporta tanto inconsistencias de 2 valores (legacy) como N valores (multi-valor).

        IMPORTANTE: Incluye referencias a ubicaciones para mostrar:
        "Capítulo X: 'valor1' vs Capítulo Y: 'valor2'" (2 valores)
        "Cap. X: 'valor1', Cap. Y: 'valor2', Cap. Z: 'valor3'" (N valores)

        Args:
            value1_source, value2_source: Deben incluir (legacy, solo 2 valores):
                - chapter: int
                - page: int (calculado con calculate_page_and_line)
                - line: int (calculado con calculate_page_and_line)
                - start_char: int
                - end_char: int
                - text/excerpt: str
            sources: Lista de fuentes para multi-valor (preferido), cada una con:
                - chapter: int
                - start_char: int
                - end_char: int
                - excerpt/text: str
                - value: str

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

        # Si se proporciona sources[], usarlo (multi-valor)
        # Si no, construir desde value1_source/value2_source (legacy)
        if sources is None or len(sources) == 0:
            # Construir descripción legacy (2 valores)
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

            description = f"{ref1}: '{value1}' vs {ref2}: '{value2}'"

            # Estructura sources[] para frontend
            sources = [
                {
                    "chapter": value1_source.get("chapter"),
                    "page": value1_source.get("page", 1),
                    "line": value1_source.get("line", 1),
                    "start_char": value1_source.get(
                        "start_char", value1_source.get("position", 0)
                    ),
                    "end_char": value1_source.get(
                        "end_char", value1_source.get("start_char", 0) + 100
                    ),
                    "excerpt": value1_source.get("text", value1_source.get("excerpt", "")),
                    "value": value1,
                },
                {
                    "chapter": value2_source.get("chapter"),
                    "page": value2_source.get("page", 1),
                    "line": value2_source.get("line", 1),
                    "start_char": value2_source.get(
                        "start_char", value2_source.get("position", 0)
                    ),
                    "end_char": value2_source.get(
                        "end_char", value2_source.get("start_char", 0) + 100
                    ),
                    "excerpt": value2_source.get("text", value2_source.get("excerpt", "")),
                    "value": value2,
                },
            ]
        else:
            # Multi-valor: construir descripción con N valores
            value_refs = []
            for src in sources:
                ref = f"Cap. {src.get('chapter', '?')}"
                if "page" in src:
                    ref += f", pág. {src['page']}"
                if "line" in src:
                    ref += f", lín. {src['line']}"
                value_refs.append(f"{ref}: '{src.get('value', '?')}'")

            if len(value_refs) == 2:
                description = f"{value_refs[0]} vs {value_refs[1]}"
            else:
                # N > 2: formato "valor1, valor2, ..., valorN"
                description = ", ".join(value_refs[:-1]) + f", {value_refs[-1]}"

        # Traducir nombre del atributo para mostrar en español
        from ..nlp.attributes import AttributeKey

        try:
            attr_key_enum = AttributeKey(attribute_key)
            display_name = get_attribute_display_name(attr_key_enum)
        except (ValueError, KeyError):
            display_name = attribute_key.replace("_", " ")

        # Generar sugerencia basada en los valores encontrados
        if len(sources) == 2:
            suggestion = f"Revisar si {display_name} es '{sources[0].get('value')}' o '{sources[1].get('value')}' y corregir el valor incorrecto."
        elif len(sources) > 2:
            # Multi-valor: sugerir revisar todos los valores
            suggestion = f"Se encontraron {len(sources)} valores diferentes para {display_name}. Revisar cada aparición y corregir los valores incorrectos."
        else:
            # Fallback genérico
            suggestion = f"Verificar cuál es el valor correcto para {display_name}."

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.CONSISTENCY,
            severity=severity,
            alert_type="attribute_inconsistency",
            title=f"Inconsistencia: {display_name} de {entity_name}",
            description=description,
            explanation=explanation,
            suggestion=suggestion,
            chapter=sources[0].get("chapter") if sources else value1_source.get("chapter"),
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
        chapter: int | None = None,
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
            explanation=AlertFormatter.format_context(sentence),
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
        suggestion: str | None,
        confidence: float,
        explanation: str,
        rule_id: str = "",
        chapter: int | None = None,
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
            explanation=AlertFormatter.format_context(sentence),
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

    def create_from_correction_issue(
        self,
        project_id: int,
        category: str,
        issue_type: str,
        text: str,
        start_char: int,
        end_char: int,
        explanation: str,
        suggestion: str | None = None,
        confidence: float = 0.8,
        context: str = "",
        chapter: int | None = None,
        rule_id: str = "",
        extra_data: dict | None = None,
    ) -> Result[Alert]:
        """
        Crea alerta desde un issue de corrección editorial.

        Soporta tipografía, repeticiones y concordancia.

        Args:
            project_id: ID del proyecto
            category: Categoría (typography, repetition, agreement)
            issue_type: Tipo específico de issue
            text: Fragmento problemático
            start_char: Posición inicio
            end_char: Posición fin
            explanation: Explicación para el corrector
            suggestion: Sugerencia de corrección (opcional)
            confidence: Confianza (0.0-1.0)
            context: Contexto alrededor del problema
            chapter: Número de capítulo (opcional)
            rule_id: ID de la regla
            extra_data: Datos adicionales

        Returns:
            Result con la alerta creada
        """
        # Mapear categoría de corrección a AlertCategory
        category_map = {
            "typography": AlertCategory.TYPOGRAPHY,
            "punctuation": AlertCategory.PUNCTUATION,
            "repetition": AlertCategory.REPETITION,
            "agreement": AlertCategory.AGREEMENT,
            "style_register": AlertCategory.STYLE,
            "references": AlertCategory.STYLE,
            "acronyms": AlertCategory.STYLE,
            "structure": AlertCategory.STYLE,
            "coherence": AlertCategory.STYLE,
        }
        alert_category = category_map.get(category, AlertCategory.STYLE)

        # Calcular severidad basada en confianza y tipo
        severity = self.calculate_severity_from_confidence(confidence)

        # Títulos legibles según categoría
        category_titles = {
            "typography": "Tipografía",
            "punctuation": "Puntuación",
            "repetition": "Repetición",
            "agreement": "Concordancia",
            "style_register": "Estilo",
            "references": "Referencias",
            "acronyms": "Siglas",
            "structure": "Estructura",
            "coherence": "Coherencia",
        }
        title_prefix = category_titles.get(category, "Corrección")

        # Generar título breve que identifique el problema
        # Para muletillas/palabras repetidas, mostrar la palabra
        # Para otros casos, usar un resumen del tipo de issue
        if issue_type in ("overused_word", "crutch_word"):
            title = f"{title_prefix}: «{text[:30]}»"
        else:
            # Para otros tipos, título descriptivo basado en el texto
            title = f"{title_prefix}: «{text[:30]}{'...' if len(text) > 30 else ''}»"

        # Descripción = la explicación técnica completa (ej: estadísticas)
        # Esto es lo que el detector generó como explanation
        description = explanation

        # Explanation = contexto del texto o consejo práctico
        # Si hay contexto, mostrarlo formateado
        # Si no, dar consejo práctico genérico
        if context:
            explanation_text = AlertFormatter.format_context(context, prefix="Contexto")
        elif not suggestion:
            # Sin contexto ni sugerencia, dar consejo genérico
            explanation_text = "Revise el fragmento marcado y considere si es necesaria una corrección."
        else:
            # Hay sugerencia, el contexto está implícito en excerpt
            explanation_text = None

        return self.create_alert(
            project_id=project_id,
            category=alert_category,
            severity=severity,
            alert_type=f"{category}_{issue_type}",
            title=title,
            description=description,
            explanation=explanation_text or "",
            suggestion=suggestion,
            chapter=chapter,
            start_char=start_char,
            end_char=end_char,
            excerpt=text,
            confidence=confidence,
            source_module="corrections_detector",
            extra_data=extra_data
            or {
                "text": text,
                "issue_type": issue_type,
                "rule_id": rule_id,
            },
        )

    def create_alerts_from_spelling_report(
        self,
        project_id: int,
        report: Any,  # SpellingReport
        chapter: int | None = None,
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

            alerts_data.append(
                {
                    "category": AlertCategory.ORTHOGRAPHY,
                    "severity": self.calculate_severity_from_confidence(
                        issue.confidence
                    ),
                    "alert_type": f"spelling_{issue.error_type.value}",
                    "title": f"Error ortográfico: '{issue.word}'",
                    "description": issue.explanation,
                    "explanation": AlertFormatter.format_context(issue.sentence),
                    "suggestion": (
                        f"Sugerencias: {', '.join(issue.suggestions[:3])}"
                        if issue.suggestions
                        else None
                    ),
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
                }
            )

        return self.create_alerts_batch(project_id, alerts_data)

    def create_alerts_from_grammar_report(
        self,
        project_id: int,
        report: Any,  # GrammarReport
        chapter: int | None = None,
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

            alerts_data.append(
                {
                    "category": AlertCategory.GRAMMAR,
                    "severity": self.calculate_severity_from_confidence(
                        issue.confidence
                    ),
                    "alert_type": f"grammar_{issue.error_type.value}",
                    "title": f"Error gramatical: {issue.explanation[:50]}",
                    "description": (
                        f"'{issue.text}' → '{issue.suggestion}'"
                        if issue.suggestion
                        else f"'{issue.text}'"
                    ),
                    "explanation": AlertFormatter.format_context(issue.sentence),
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
                }
            )

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
        entity_ids: list[int] | None = None,
        extra_data: dict[str, Any] | None = None,
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
        extra_data: dict[str, Any] | None = None,
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

        # Traducir nombres de registros al español
        register_translations = {
            "colloquial": "coloquial",
            "formal": "formal",
            "neutral": "neutral",
            "formal_literary": "formal literario",
            "technical": "técnico",
            "poetic": "poético",
            "vulgar": "vulgar",
        }
        from_register_es = register_translations.get(from_register, from_register)
        to_register_es = register_translations.get(to_register, to_register)

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.STYLE,
            severity=severity,
            alert_type="register_change",
            title=f"Cambio de registro: {from_register_es} → {to_register_es}",
            description=f"Transición de registro {from_register_es} a {to_register_es}",
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
        entity_ids: list[int] | None = None,
        extra_data: dict[str, Any] | None = None,
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
        extra_data: dict[str, Any] | None = None,
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
            return Result.success(None)

        severity = (
            AlertSeverity.WARNING
            if attribution_confidence == "unknown"
            else AlertSeverity.INFO
        )

        speakers_str = (
            ", ".join(possible_speakers) if possible_speakers else "desconocido"
        )

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
        suggestion: str | None = None,
        chapter: int | None = None,
        start_char: int | None = None,
        end_char: int | None = None,
        entity_ids: list[int] | None = None,
        extra_data: dict[str, Any] | None = None,
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
            incoherence_type, f"Incoherencia emocional: {entity_name}"
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

    def create_from_ambiguous_attribute(
        self,
        project_id: int,
        attribute_key: str,
        attribute_value: str,
        candidates: list[dict[str, Any]],  # [{"entity_name": str, "entity_id": int}, ...]
        source_text: str,
        chapter: int | None = None,
        start_char: int | None = None,
        end_char: int | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> Result[Alert]:
        """
        Crea alerta interactiva para atributo con propiedad ambigua.

        Cuando el sistema no puede determinar con certeza a qué entidad
        pertenece un atributo, genera una alerta pidiendo al usuario que
        seleccione el propietario correcto.

        Args:
            project_id: ID del proyecto
            attribute_key: Clave del atributo (eye_color, hair_color, etc.)
            attribute_value: Valor del atributo ("azules", "rizado", etc.)
            candidates: Lista de entidades candidatas con entity_name y entity_id
            source_text: Texto de la oración ambigua
            chapter: Número de capítulo
            start_char: Posición de inicio
            end_char: Posición de fin
            extra_data: Datos adicionales

        Returns:
            Result con la alerta creada
        """
        # Formatear nombres de atributos para UI
        attr_display_names = {
            "eye_color": "color de ojos",
            "hair_color": "color de cabello",
            "hair_type": "tipo de cabello",
            "height": "altura",
            "build": "complexión",
            "facial_hair": "vello facial",
            "skin_tone": "tono de piel",
            "age": "edad",
        }
        attr_display = attr_display_names.get(attribute_key, attribute_key)

        # Crear lista de nombres de candidatos para descripción
        candidate_names = [c["entity_name"] for c in candidates]
        candidates_str = ", ".join(candidate_names)

        # FEATURE: Sugerencia contextual basada en atributos ya asignados
        suggested_entity_id = None
        try:
            from ..entities.repository import get_entity_repository
            entity_repo = get_entity_repository()

            # Buscar si algún candidato YA tiene este atributo asignado
            for candidate in candidates:
                entity_id = candidate["entity_id"]
                attributes = entity_repo.get_attributes_by_entity(entity_id)

                # Verificar si tiene el mismo atributo con valor similar
                for attr in attributes:
                    if attr.get("attribute_key") == attribute_key:
                        # Comparación case-insensitive y normalizada
                        existing_value = str(attr.get("attribute_value", "")).lower().strip()
                        new_value = attribute_value.lower().strip()

                        if existing_value == new_value or existing_value in new_value or new_value in existing_value:
                            suggested_entity_id = entity_id
                            logger.info(
                                f"Sugerencia contextual: {candidate['entity_name']} ya tiene "
                                f"{attribute_key}={attr.get('attribute_value')} (confianza={attr.get('confidence', 0):.2f})"
                            )
                            break

                if suggested_entity_id:
                    break
        except Exception as e:
            logger.debug(f"Error buscando sugerencia contextual: {e}")

        # FEATURE: Filtrado por género gramatical
        # Si el atributo tiene género (ej: "rubia" → Fem), eliminar candidatos
        # con género incompatible
        gender_filtered_candidates = candidates
        try:
            attr_gender = self._detect_attribute_gender(attribute_value)
            if attr_gender:
                compatible = []
                for c in candidates:
                    entity_gender = self._get_entity_gender(c.get("entity_id"), c.get("entity_name", ""))
                    if entity_gender is None or entity_gender == attr_gender:
                        compatible.append(c)
                    else:
                        logger.info(
                            f"Género incompatible: '{c['entity_name']}' ({entity_gender}) vs "
                            f"atributo '{attribute_value}' ({attr_gender})"
                        )

                if len(compatible) == 1:
                    # Solo queda un candidato: asignar directamente sin alerta
                    logger.info(
                        f"Género resuelve ambigüedad: '{compatible[0]['entity_name']}' "
                        f"es el único candidato {attr_gender} para '{attribute_value}'"
                    )
                    return self._auto_assign_attribute(
                        project_id=project_id,
                        entity_id=compatible[0]["entity_id"],
                        entity_name=compatible[0]["entity_name"],
                        attribute_key=attribute_key,
                        attribute_value=attribute_value,
                        confidence=0.75,
                        source="gender_filter",
                    )
                elif len(compatible) > 1:
                    gender_filtered_candidates = compatible
        except Exception as e:
            logger.debug(f"Error en filtrado por género: {e}")

        # Marcar candidato sugerido en la lista
        candidates_with_suggestion = []
        for c in gender_filtered_candidates:
            candidate_copy = c.copy()
            if suggested_entity_id and c["entity_id"] == suggested_entity_id:
                candidate_copy["suggested"] = True
            candidates_with_suggestion.append(candidate_copy)

        # Recalcular nombres tras filtrado
        candidate_names = [c["entity_name"] for c in gender_filtered_candidates]
        candidates_str = ", ".join(candidate_names)

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.CONSISTENCY,
            severity=AlertSeverity.WARNING,
            alert_type="ambiguous_attribute",
            title=f"¿Quién tiene {attr_display} {attribute_value}?",
            description=f"No se puede determinar automáticamente a quién pertenece este atributo. Candidatos: {candidates_str}.",
            explanation=f"El contexto «{source_text[:150]}» no permite determinar con certeza el propietario del atributo. Por favor, seleccione la entidad correcta.",
            suggestion=f"Seleccione quién tiene {attr_display} {attribute_value}, o marque como 'No asignar' si ningún candidato es correcto",
            chapter=chapter,
            start_char=start_char,
            end_char=end_char,
            excerpt=source_text[:200] if source_text else "",
            entity_ids=[c["entity_id"] for c in candidates],
            confidence=0.7,  # Media-alta: sabemos que ES ambiguo
            source_module="attribute_extraction",
            extra_data={
                "attribute_key": attribute_key,
                "attribute_value": attribute_value,
                "candidates": candidates_with_suggestion,  # Con flag 'suggested' si aplica
                "suggested_entity_id": suggested_entity_id,  # Para UI
                "source_text": source_text,
                **(extra_data or {}),
            },
        )

    def _detect_attribute_gender(self, attribute_value: str) -> str | None:
        """
        Detecta el género gramatical de un valor de atributo usando spaCy.

        Args:
            attribute_value: Valor del atributo ("rubia", "alto", "morena")

        Returns:
            "Fem", "Masc", o None si no se puede determinar
        """
        try:
            from ..nlp.spacy_gpu import load_spacy_model
            nlp = load_spacy_model()
            doc = nlp(attribute_value)
            for token in doc:
                gender = token.morph.get("Gender")
                if gender:
                    g = gender[0] if isinstance(gender, list) else gender
                    if g in ("Fem", "Masc"):
                        return str(g)
        except Exception:
            pass
        return None

    def _get_entity_gender(self, entity_id: int | None, entity_name: str) -> str | None:
        """
        Obtiene el género de una entidad a partir de sus atributos o nombre.

        Args:
            entity_id: ID de la entidad
            entity_name: Nombre de la entidad

        Returns:
            "Fem", "Masc", o None si no se puede determinar
        """
        # Intentar obtener de atributos almacenados
        if entity_id:
            try:
                from ..entities.repository import get_entity_repository
                repo = get_entity_repository()
                attrs = repo.get_attributes_by_entity(entity_id)
                for attr in attrs:
                    if attr.get("attribute_key") == "gender":
                        val = str(attr.get("attribute_value", "")).lower().strip()
                        if val in ("masculino", "masc", "m", "male"):
                            return "Masc"
                        elif val in ("femenino", "fem", "f", "female"):
                            return "Fem"
            except Exception:
                pass

        # Intentar inferir del nombre con spaCy
        try:
            from ..nlp.spacy_gpu import load_spacy_model
            nlp = load_spacy_model()
            doc = nlp(entity_name)
            for token in doc:
                gender = token.morph.get("Gender")
                if gender:
                    g = gender[0] if isinstance(gender, list) else gender
                    if g in ("Fem", "Masc"):
                        return str(g)
        except Exception:
            pass

        return None

    def _auto_assign_attribute(
        self,
        project_id: int,
        entity_id: int,
        entity_name: str,
        attribute_key: str,
        attribute_value: str,
        confidence: float = 0.75,
        source: str = "gender_filter",
    ) -> Result[Alert]:
        """
        Asigna un atributo directamente sin generar alerta interactiva.

        Usado cuando el filtrado por género resuelve la ambigüedad.
        Crea una alerta informativa (auto-resuelta) en lugar de interactiva.

        Returns:
            Result con alerta informativa ya resuelta
        """
        try:
            from ..entities.repository import get_entity_repository
            entity_repo = get_entity_repository()
            entity_repo.create_attribute(
                entity_id=entity_id,
                attribute_type="inferred",
                attribute_key=attribute_key,
                attribute_value=attribute_value,
                confidence=confidence,
            )
            logger.info(
                f"Auto-asignado por género: {entity_name}.{attribute_key} = "
                f"'{attribute_value}' (confianza={confidence})"
            )
        except Exception as e:
            logger.warning(f"Error auto-asignando atributo: {e}")

        # Crear alerta informativa (ya resuelta) para que el usuario sepa qué se hizo
        attr_display = get_attribute_display_name(attribute_key)
        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.CONSISTENCY,
            severity=AlertSeverity.INFO,
            alert_type="ambiguous_attribute_auto_resolved",
            title=f"Atributo asignado automáticamente: {entity_name}",
            description=(
                f"{attr_display} «{attribute_value}» asignado a {entity_name} "
                f"por concordancia de género gramatical."
            ),
            explanation=(
                f"El atributo «{attribute_value}» tiene género que solo concuerda con "
                f"{entity_name}, lo cual resolvió la ambigüedad automáticamente."
            ),
            suggestion="Si la asignación es incorrecta, edite el atributo manualmente.",
            entity_ids=[entity_id],
            confidence=confidence,
            source_module="attribute_extraction",
            extra_data={
                "attribute_key": attribute_key,
                "attribute_value": attribute_value,
                "resolved_entity": entity_name,
                "resolution_method": source,
            },
        )

    def create_from_deceased_reappearance(
        self,
        project_id: int,
        entity_id: int,
        entity_name: str,
        death_chapter: int,
        appearance_chapter: int,
        appearance_start_char: int,
        appearance_end_char: int,
        appearance_excerpt: str,
        appearance_type: str,
        death_excerpt: str = "",
        confidence: float = 0.85,
        extra_data: dict[str, Any] | None = None,
    ) -> Result[Alert]:
        """
        Crea alerta cuando un personaje fallecido reaparece como vivo.

        Esta es una inconsistencia narrativa grave: el personaje muere en
        un capítulo y aparece actuando/hablando en un capítulo posterior.

        Args:
            project_id: ID del proyecto
            entity_id: ID del personaje
            entity_name: Nombre del personaje
            death_chapter: Capítulo donde muere
            appearance_chapter: Capítulo donde reaparece
            appearance_start_char: Posición inicio de la reaparición
            appearance_end_char: Posición fin de la reaparición
            appearance_excerpt: Texto de la reaparición
            appearance_type: Tipo de reaparición (dialogue, action)
            death_excerpt: Texto donde se menciona la muerte
            confidence: Confianza de la detección
            extra_data: Datos adicionales

        Returns:
            Result con la alerta creada
        """
        severity = (
            AlertSeverity.CRITICAL if confidence >= 0.8 else AlertSeverity.WARNING
        )

        # Descripción según tipo de aparición
        if appearance_type == "dialogue":
            action_desc = "habla"
        else:
            action_desc = "actúa"

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.CONSISTENCY,
            severity=severity,
            alert_type="deceased_reappearance",
            title=f"Personaje fallecido reaparece: {entity_name}",
            description=(
                f"{entity_name} muere en capítulo {death_chapter} "
                f"pero {action_desc} en capítulo {appearance_chapter}"
            ),
            explanation=(
                f"El personaje '{entity_name}' fue declarado muerto en el capítulo {death_chapter}. "
                f"Sin embargo, aparece realizando acciones en el capítulo {appearance_chapter}, "
                f"lo cual es una inconsistencia narrativa a menos que sea un flashback, "
                f"recuerdo o aparición sobrenatural."
            ),
            suggestion=(
                f"Verificar si '{entity_name}' realmente muere en el capítulo {death_chapter}. "
                f"Si la reaparición es intencional (flashback, fantasma, recuerdo), "
                f"considerar añadir contexto narrativo que lo aclare."
            ),
            chapter=appearance_chapter,
            start_char=appearance_start_char,
            end_char=appearance_end_char,
            excerpt=appearance_excerpt[:300] if appearance_excerpt else "",
            entity_ids=[entity_id],
            confidence=confidence,
            source_module="vital_status_analyzer",
            extra_data={
                "entity_name": entity_name,
                "death_chapter": death_chapter,
                "appearance_chapter": appearance_chapter,
                "appearance_type": appearance_type,
                "death_excerpt": death_excerpt[:200] if death_excerpt else "",
                **(extra_data or {}),
            },
        )

    # ==========================================================================
    # Alertas de estilo
    # ==========================================================================

    def create_from_pacing_issue(
        self,
        project_id: int,
        issue_type: str,
        severity_level: str,
        chapter: int | None,
        segment_type: str,
        description: str,
        explanation: str,
        suggestion: str = "",
        actual_value: float = 0.0,
        expected_range: tuple = (0.0, 0.0),
        comparison_value: float | None = None,
        confidence: float = 0.8,
    ) -> Result[Alert]:
        """
        Crea alerta desde problema de ritmo narrativo.

        Args:
            issue_type: Tipo de problema (chapter_too_short, dense_text_block, etc.)
            severity_level: info, suggestion, warning, issue
            chapter: Número de capítulo afectado
            segment_type: chapter, scene, paragraph
            description: Descripción del problema
            explanation: Explicación detallada
            suggestion: Sugerencia de corrección
            actual_value: Valor detectado
            expected_range: Rango esperado
            comparison_value: Valor medio del documento
        """
        severity_map = {
            "issue": AlertSeverity.WARNING,
            "warning": AlertSeverity.WARNING,
            "suggestion": AlertSeverity.INFO,
            "info": AlertSeverity.HINT,
        }
        severity = severity_map.get(severity_level, AlertSeverity.INFO)

        issue_titles = {
            "chapter_too_short": "Capítulo muy corto",
            "chapter_too_long": "Capítulo muy largo",
            "unbalanced_chapters": "Capítulos desbalanceados",
            "too_much_dialogue": "Exceso de diálogo",
            "too_little_dialogue": "Poco diálogo",
            "dense_text_block": "Bloque de texto denso",
            "sparse_text_block": "Texto disperso",
            "rhythm_shift": "Cambio de ritmo",
            "scene_too_short": "Escena muy corta",
            "scene_too_long": "Escena muy larga",
        }
        title = issue_titles.get(issue_type, f"Problema de ritmo: {issue_type}")
        if chapter:
            title = f"{title} (Cap. {chapter})"

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.STRUCTURE,
            severity=severity,
            alert_type=f"pacing_{issue_type}",
            title=title,
            description=description,
            explanation=explanation,
            suggestion=suggestion
            or "Revisar el equilibrio del ritmo narrativo en este segmento",
            chapter=chapter,
            confidence=confidence,
            source_module="pacing_analyzer",
            extra_data={
                "issue_type": issue_type,
                "segment_type": segment_type,
                "actual_value": actual_value,
                "expected_range": list(expected_range),
                "comparison_value": comparison_value,
            },
        )

    def create_from_sticky_sentence(
        self,
        project_id: int,
        sentence: str,
        glue_percentage: float,
        chapter: int | None = None,
        start_char: int | None = None,
        end_char: int | None = None,
        severity_level: str = "medium",
        confidence: float = 0.75,
    ) -> Result[Alert]:
        """
        Crea alerta desde frase pegajosa (alto porcentaje de palabras de relleno).

        Args:
            sentence: La frase detectada
            glue_percentage: Porcentaje de palabras de relleno (0-100)
            chapter: Capítulo donde aparece
            start_char: Posición de inicio
            end_char: Posición de fin
            severity_level: critical, high, medium, low
        """
        severity_map = {
            "critical": AlertSeverity.WARNING,
            "high": AlertSeverity.WARNING,
            "medium": AlertSeverity.INFO,
            "low": AlertSeverity.HINT,
        }
        severity = severity_map.get(severity_level, AlertSeverity.INFO)

        excerpt = sentence[:120] + "..." if len(sentence) > 120 else sentence

        # Convertir glue_percentage a escala 0-100 si está en escala 0-1
        glue_pct = glue_percentage * 100 if glue_percentage <= 1.0 else glue_percentage

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.STYLE,
            severity=severity,
            alert_type="sticky_sentence",
            title="Frase pegajosa (exceso de palabras funcionales)",
            description=f'Frase con {glue_pct:.0f}% de palabras funcionales: "{excerpt}"',
            explanation=(
                f"Esta frase tiene un {glue_pct:.0f}% de palabras funcionales "
                f"(artículos, preposiciones, conjunciones), lo que dificulta la fluidez. "
                f"Las frases con más del 40% de palabras funcionales suelen percibirse como pesadas."
            ),
            suggestion="Reformular para reducir las palabras de relleno y mejorar la claridad",
            chapter=chapter,
            start_char=start_char,
            end_char=end_char,
            excerpt=excerpt,
            confidence=confidence,
            source_module="sticky_sentences",
            extra_data={
                "glue_percentage": round(glue_pct, 1),
                "severity_level": severity_level,
            },
        )

    def create_from_style_variation(
        self,
        project_id: int,
        variation_type: str,
        description: str,
        explanation: str,
        chapter: int | None = None,
        start_char: int | None = None,
        end_char: int | None = None,
        excerpt: str = "",
        confidence: float = 0.7,
        extra_data: dict | None = None,
    ) -> Result[Alert]:
        """
        Crea alerta desde variación estilística inesperada.

        Args:
            variation_type: tone_shift, formality_change, vocabulary_anomaly, register_inconsistency
            description: Descripción de la variación
            explanation: Explicación detallada
        """
        severity = self.calculate_severity_from_confidence(confidence)

        type_titles = {
            "tone_shift": "Cambio de tono narrativo",
            "formality_change": "Cambio de formalidad",
            "vocabulary_anomaly": "Vocabulario atípico",
            "register_inconsistency": "Inconsistencia de registro",
        }
        title = type_titles.get(
            variation_type, f"Variación estilística: {variation_type}"
        )

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.STYLE,
            severity=severity,
            alert_type=f"style_variation_{variation_type}",
            title=title,
            description=description,
            explanation=explanation,
            suggestion="Verificar si la variación estilística es intencional",
            chapter=chapter,
            start_char=start_char,
            end_char=end_char,
            excerpt=excerpt[:200] if excerpt else "",
            confidence=confidence,
            source_module="style_analyzer",
            extra_data={
                "variation_type": variation_type,
                **(extra_data or {}),
            },
        )

    def create_from_word_echo(
        self,
        project_id: int,
        word: str,
        occurrences: list[dict],
        min_distance: int,
        chapter: int | None = None,
        confidence: float = 0.8,
    ) -> Result[Alert]:
        """
        Crea alerta desde eco de palabra (repetición a corta distancia).

        Args:
            word: Palabra repetida
            occurrences: Lista de ocurrencias [{position, context}, ...]
            min_distance: Distancia mínima entre repeticiones (en palabras)
            chapter: Capítulo donde se detecta
        """
        # Severidad basada en distancia: más cerca = más severo
        if min_distance < 10:
            severity = AlertSeverity.WARNING
        elif min_distance < 30:
            severity = AlertSeverity.INFO
        else:
            severity = AlertSeverity.HINT

        count = len(occurrences)

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.REPETITION,
            severity=severity,
            alert_type="word_echo",
            title=f'Eco: "{word}" ({count}x en {min_distance} palabras)',
            description=f'La palabra "{word}" aparece {count} veces con solo {min_distance} palabras de distancia',
            explanation=(
                f'Se detectó repetición cercana de "{word}". '
                f"Las repeticiones a menos de 30 palabras de distancia pueden "
                f"percibirse como descuido estilístico, salvo que sean intencionales."
            ),
            suggestion=f'Considerar sinónimos o reformulación para evitar la repetición de "{word}"',
            chapter=chapter,
            confidence=confidence,
            source_module="repetition_detector",
            extra_data={
                "word": word,
                "occurrences": occurrences[:10],  # Limitar a 10 para no sobrecargar
                "min_distance": min_distance,
                "count": count,
            },
        )

    # ==========================================================================
    # Alertas de diálogos
    # ==========================================================================

    def create_from_dialogue_issue(
        self,
        project_id: int,
        issue_type: str,
        severity_level: str,
        chapter: int,
        paragraph: int,
        start_char: int,
        end_char: int,
        text: str,
        description: str,
        suggestion: str,
        consecutive_count: int = 1,
        confidence: float = 0.85,
    ) -> Result[Alert]:
        """
        Crea alerta desde un problema de diálogo.

        Args:
            project_id: ID del proyecto
            issue_type: Tipo de problema (orphan_no_attribution, consecutive_no_change, etc.)
            severity_level: Nivel de severidad (high, medium, low)
            chapter: Número de capítulo
            paragraph: Número de párrafo
            start_char: Posición inicio del diálogo
            end_char: Posición fin del diálogo
            text: Texto del diálogo problemático
            description: Descripción del problema
            suggestion: Sugerencia de corrección
            consecutive_count: Cantidad de diálogos consecutivos (para secuencias)
            confidence: Confianza de la detección (0.0-1.0)

        Returns:
            Result con la alerta creada
        """
        # Mapear severidad
        severity_map = {
            "high": AlertSeverity.WARNING,
            "medium": AlertSeverity.INFO,
            "low": AlertSeverity.HINT,
        }
        severity = severity_map.get(severity_level, AlertSeverity.INFO)

        # Títulos según tipo de problema
        title_map = {
            "orphan_no_attribution": "Diálogo sin atribución de hablante",
            "orphan_no_context": "Diálogo sin contexto de escena",
            "consecutive_no_change": f"Secuencia de {consecutive_count} diálogos sin indicar cambio de hablante",
            "chapter_start_dialogue": "Capítulo inicia con diálogo sin contexto",
        }
        title = title_map.get(issue_type, f"Problema de diálogo: {issue_type}")

        # Limitar texto para excerpt
        excerpt = text[:200] + "..." if len(text) > 200 else text

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.DIALOGUE,
            severity=severity,
            alert_type=f"dialogue_{issue_type}",
            title=title,
            description=description,
            explanation=(
                f"Se detectó un problema de contexto en el diálogo del capítulo {chapter}, "
                f"párrafo {paragraph}. {description}"
            ),
            suggestion=suggestion,
            chapter=chapter,
            start_char=start_char,
            end_char=end_char,
            excerpt=excerpt,
            confidence=confidence,
            source_module="dialogue_validator",
            extra_data={
                "issue_type": issue_type,
                "paragraph": paragraph,
                "consecutive_count": consecutive_count,
                "dialogue_text": text[:500] if text else "",
            },
        )

    def create_from_name_variant(
        self,
        project_id: int,
        entity_id: int,
        entity_name: str,
        canonical_form: str,
        variant_form: str,
        canonical_count: int,
        variant_count: int,
        variant_mentions: list[dict],
        all_in_dialogue: bool = False,
        confidence: float = 0.85,
    ) -> Result[Alert]:
        """
        Crea alerta por variante ortográfica en nombre de entidad.

        Detecta cuando un personaje aparece con diferentes acentuaciones
        (ej: "María" 150 veces vs "Maria" 2 veces).
        """
        if all_in_dialogue:
            severity = AlertSeverity.HINT
        elif confidence >= 0.9:
            severity = AlertSeverity.WARNING
        else:
            severity = AlertSeverity.INFO

        title = f"Variante de nombre: '{variant_form}'"
        vez = "vez" if variant_count == 1 else "veces"
        description = (
            f"'{entity_name}' aparece como '{variant_form}' "
            f"{variant_count} {vez} "
            f"(forma habitual: '{canonical_form}', {canonical_count} menciones)"
        )

        chapters_affected = sorted(
            set(
                m["chapter_id"]
                for m in variant_mentions
                if m.get("chapter_id") is not None
            )
        )
        ch_list = ", ".join(str(c) for c in chapters_affected[:5])
        if len(chapters_affected) > 5:
            ch_list += f" (+{len(chapters_affected) - 5} más)"

        ch_word = "capítulo" if len(chapters_affected) == 1 else "capítulos"
        explanation = (
            f"La entidad '{entity_name}' se menciona habitualmente como "
            f"'{canonical_form}' ({canonical_count} veces). "
            f"Sin embargo, aparece como '{variant_form}' en {ch_word} {ch_list}. "
        )
        if all_in_dialogue:
            explanation += (
                "Todas las apariciones de la variante están dentro de diálogos, "
                "lo cual podría ser intencional (registro informal)."
            )
        else:
            explanation += "Esto podría ser un error tipográfico (tilde omitida)."

        first = variant_mentions[0] if variant_mentions else {}

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.ENTITY,
            severity=severity,
            alert_type="entity_name_variant",
            title=title,
            description=description,
            explanation=explanation,
            suggestion=f"Revisar si '{variant_form}' debería ser '{canonical_form}'",
            chapter=first.get("chapter_id"),
            start_char=first.get("start_char"),
            end_char=first.get("end_char"),
            excerpt=(
                first.get("context_before", "")
                + variant_form
                + first.get("context_after", "")
            ),
            entity_ids=[entity_id],
            confidence=confidence,
            source_module="name_variant_detector",
            extra_data={
                "canonical_form": canonical_form,
                "variant_form": variant_form,
                "canonical_count": canonical_count,
                "variant_count": variant_count,
                "chapters_affected": chapters_affected,
                "all_in_dialogue": all_in_dialogue,
            },
        )

    def create_alerts_from_dialogue_report(
        self,
        project_id: int,
        report: Any,  # DialogueValidationReport
        min_severity: str = "low",
    ) -> Result[list[Alert]]:
        """
        Crea alertas desde un DialogueValidationReport completo.

        Args:
            project_id: ID del proyecto
            report: DialogueValidationReport con los issues
            min_severity: Severidad mínima para crear alertas (high, medium, low)

        Returns:
            Result con lista de alertas creadas
        """
        severity_order = {"high": 3, "medium": 2, "low": 1}
        min_severity_value = severity_order.get(min_severity, 1)

        alerts_data = []

        for issue in report.issues:
            # Filtrar por severidad mínima
            issue_severity_value = severity_order.get(issue.severity.value, 1)
            if issue_severity_value < min_severity_value:
                continue

            alerts_data.append(
                {
                    "category": AlertCategory.DIALOGUE,
                    "severity": {
                        "high": AlertSeverity.WARNING,
                        "medium": AlertSeverity.INFO,
                        "low": AlertSeverity.HINT,
                    }.get(issue.severity.value, AlertSeverity.INFO),
                    "alert_type": f"dialogue_{issue.issue_type.value}",
                    "title": self._get_dialogue_issue_title(
                        issue.issue_type.value, issue.consecutive_count
                    ),
                    "description": issue.description,
                    "explanation": (
                        f"Se detectó un problema de contexto en el diálogo del capítulo "
                        f"{issue.location.chapter}, párrafo {issue.location.paragraph}. "
                        f"{issue.description}"
                    ),
                    "suggestion": issue.suggestion,
                    "chapter": issue.location.chapter,
                    "start_char": issue.location.start_char,
                    "end_char": issue.location.end_char,
                    "excerpt": issue.location.text[:200] if issue.location.text else "",
                    "confidence": 0.85 if issue.severity.value == "high" else 0.7,
                    "source_module": "dialogue_validator",
                    "extra_data": {
                        "issue_type": issue.issue_type.value,
                        "paragraph": issue.location.paragraph,
                        "consecutive_count": issue.consecutive_count,
                    },
                }
            )

        return self.create_alerts_batch(project_id, alerts_data)

    def _get_dialogue_issue_title(
        self, issue_type: str, consecutive_count: int = 1
    ) -> str:
        """Genera título para problema de diálogo."""
        title_map = {
            "orphan_no_attribution": "Diálogo sin atribución de hablante",
            "orphan_no_context": "Diálogo sin contexto de escena",
            "consecutive_no_change": f"Secuencia de {consecutive_count} diálogos sin indicar cambio",
            "chapter_start_dialogue": "Capítulo inicia con diálogo sin contexto",
        }
        return title_map.get(issue_type, f"Problema de diálogo: {issue_type}")

    # ==========================================================================
    # Calibración de confianza por detector (BK-22)
    # ==========================================================================

    def _get_calibration_factor(
        self, project_id: int, alert_type: str, source_module: str
    ) -> float:
        """
        Obtiene el factor de calibración para un detector.

        Busca en cache primero, luego en DB. Devuelve 1.0 si no hay datos.
        """
        cache = getattr(self, "_calibration_cache", None)
        if cache is None:
            self._calibration_cache = {}
            cache = self._calibration_cache

        cache_key = (project_id, alert_type, source_module)
        if cache_key in cache:
            return cache[cache_key]

        try:
            from ..persistence.database import get_database

            db = get_database()
            row = db.fetchone(
                """
                SELECT calibration_factor FROM detector_calibration
                WHERE project_id = ? AND alert_type = ? AND source_module = ?
                """,
                (project_id, alert_type, source_module),
            )
            factor = row["calibration_factor"] if row else 1.0
            self._calibration_cache[cache_key] = factor
            return factor
        except Exception:
            return 1.0

    def _get_total_chapters(self, project_id: int) -> int:
        """Obtiene total de capítulos de un proyecto (con cache)."""
        cache = getattr(self, "_total_chapters_cache", None)
        if cache is None:
            self._total_chapters_cache = {}
            cache = self._total_chapters_cache

        if project_id in cache:
            return cache[project_id]

        try:
            from ..persistence.database import get_database

            db = get_database()
            row = db.fetchone(
                "SELECT COUNT(*) as cnt FROM chapters WHERE project_id = ?",
                (project_id,),
            )
            total = row["cnt"] if row else 0
            self._total_chapters_cache[project_id] = total
            return total
        except Exception:
            return 0

    def recalibrate_detector(
        self, project_id: int, alert_type: str, source_module: str
    ) -> float:
        """
        Recalcula la calibración para un (project, alert_type, source_module).

        fp_rate = dismissed / total
        calibration_factor = 1 - fp_rate * 0.5
          → 0% dismissed  = factor 1.0 (sin cambio)
          → 50% dismissed = factor 0.75
          → 100% dismissed = factor 0.5 (mitad de confianza)

        Returns:
            Nuevo factor de calibración
        """
        try:
            from ..persistence.database import get_database

            db = get_database()

            row = db.fetchone(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'dismissed' THEN 1 ELSE 0 END) as dismissed
                FROM alerts
                WHERE project_id = ? AND alert_type = ? AND source_module = ?
                """,
                (project_id, alert_type, source_module),
            )

            total = row["total"] if row else 0
            dismissed = row["dismissed"] if row else 0

            if total == 0:
                fp_rate = 0.0
                factor = 1.0
            else:
                fp_rate = dismissed / total
                factor = round(1.0 - fp_rate * 0.5, 4)

            db.execute(
                """
                INSERT INTO detector_calibration
                    (project_id, alert_type, source_module, total_alerts,
                     total_dismissed, fp_rate, calibration_factor, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT (project_id, alert_type, source_module)
                DO UPDATE SET
                    total_alerts = excluded.total_alerts,
                    total_dismissed = excluded.total_dismissed,
                    fp_rate = excluded.fp_rate,
                    calibration_factor = excluded.calibration_factor,
                    updated_at = datetime('now')
                """,
                (
                    project_id,
                    alert_type,
                    source_module,
                    total,
                    dismissed,
                    fp_rate,
                    factor,
                ),
            )

            # Invalidar cache
            cache_key = (project_id, alert_type, source_module)
            self._calibration_cache.pop(cache_key, None)

            logger.debug(
                f"Recalibrated {alert_type}/{source_module}: "
                f"{dismissed}/{total} dismissed, factor={factor}"
            )
            return factor

        except Exception as e:
            logger.warning(
                f"Recalibration failed for {alert_type}/{source_module}: {e}"
            )
            return 1.0

    def recalibrate_project(self, project_id: int) -> dict[str, float]:
        """
        Recalibra todos los detectores de un proyecto.

        Returns:
            Dict de {alert_type/source_module: factor}
        """
        try:
            from ..persistence.database import get_database

            db = get_database()
            rows = db.fetchall(
                """
                SELECT DISTINCT alert_type, source_module
                FROM alerts
                WHERE project_id = ?
                """,
                (project_id,),
            )

            results = {}
            for row in rows:
                at = row["alert_type"]
                sm = row["source_module"] or ""
                factor = self.recalibrate_detector(project_id, at, sm)
                results[f"{at}/{sm}"] = factor

            self._calibration_cache = {
                k: v for k, v in self._calibration_cache.items() if k[0] != project_id
            }

            logger.info(
                f"Recalibrated {len(results)} detectors for project {project_id}"
            )
            return results
        except Exception as e:
            logger.warning(f"Project recalibration failed: {e}")
            return {}

    def clear_calibration_cache(self, project_id: int | None = None) -> None:
        """Limpia la cache de calibración (opcionalmente solo para un proyecto)."""
        if project_id is None:
            self._calibration_cache.clear()
        else:
            self._calibration_cache = {
                k: v for k, v in self._calibration_cache.items() if k[0] != project_id
            }

    # =====================================================================
    # Nivel 3: Pesos adaptativos per-project
    # =====================================================================

    def _get_adaptive_weight(
        self, project_id: int, alert_type: str, entity_name: str = ""
    ) -> float:
        """
        Obtiene el peso adaptativo con cascada: per-entity > project-level > 1.0.

        Args:
            project_id: ID del proyecto
            alert_type: Tipo de alerta
            entity_name: Nombre canónico de entidad (vacío = solo project-level)
        """
        cache = getattr(self, "_adaptive_weights_cache", None)
        if cache is None:
            self._adaptive_weights_cache = {}
            cache = self._adaptive_weights_cache

        norm_name = entity_name.strip().lower() if entity_name else ""

        # Cascada: per-entity > project-level > 1.0
        if norm_name:
            entity_key = (project_id, alert_type, norm_name)
            if entity_key in cache:
                return cache[entity_key]

            try:
                from ..persistence.database import get_database
                db = get_database()
                row = db.fetchone(
                    "SELECT weight FROM project_detector_weights "
                    "WHERE project_id = ? AND alert_type = ? AND entity_canonical_name = ?",
                    (project_id, alert_type, norm_name),
                )
                if row:
                    weight = row["weight"]
                    cache[entity_key] = weight
                    return weight
            except Exception:
                pass
            # Fall through to project-level

        project_key = (project_id, alert_type, "")
        if project_key in cache:
            return cache[project_key]

        try:
            from ..persistence.database import get_database
            db = get_database()
            row = db.fetchone(
                "SELECT weight FROM project_detector_weights "
                "WHERE project_id = ? AND alert_type = ? AND entity_canonical_name = ''",
                (project_id, alert_type),
            )
            weight = row["weight"] if row else 1.0
            cache[project_key] = weight
            return weight
        except Exception:
            return 1.0

    def update_adaptive_weight(
        self,
        project_id: int,
        alert_type: str,
        dismissed: bool,
        entity_names: list[str] | None = None,
    ) -> float:
        """
        Actualiza el peso adaptativo tras feedback del usuario.

        Siempre actualiza el peso project-level. Si se proporcionan entity_names,
        también actualiza pesos per-entity (con learning rate fraccionado si son
        múltiples entidades).

        Args:
            project_id: ID del proyecto
            alert_type: Tipo de alerta
            dismissed: True si el usuario descartó, False si confirmó/resolvió
            entity_names: Nombres canónicos de entidades afectadas (opcional)

        Returns:
            Nuevo peso project-level
        """
        # Siempre actualizar project-level
        project_weight = self._update_single_weight(
            project_id, alert_type, "", dismissed, self.ADAPTIVE_LEARNING_RATE,
        )

        # Per-entity: learning rate fraccionado entre entidades
        if entity_names:
            unique_names = list({n.strip().lower() for n in entity_names if n.strip()})
            if unique_names:
                entity_lr = self.ADAPTIVE_LEARNING_RATE / len(unique_names)
                for name in unique_names:
                    self._update_single_weight(
                        project_id, alert_type, name, dismissed, entity_lr,
                    )

        return project_weight

    def _update_single_weight(
        self,
        project_id: int,
        alert_type: str,
        entity_canonical_name: str,
        dismissed: bool,
        learning_rate: float,
    ) -> float:
        """Actualiza un único registro de peso en la BD."""
        try:
            from ..persistence.database import get_database

            db = get_database()

            row = db.fetchone(
                "SELECT weight, feedback_count, dismiss_count, confirm_count "
                "FROM project_detector_weights "
                "WHERE project_id = ? AND alert_type = ? AND entity_canonical_name = ?",
                (project_id, alert_type, entity_canonical_name),
            )

            if row:
                weight = row["weight"]
                feedback_count = row["feedback_count"]
                dismiss_count = row["dismiss_count"]
                confirm_count = row["confirm_count"]
            else:
                weight = 1.0
                feedback_count = 0
                dismiss_count = 0
                confirm_count = 0

            if dismissed:
                weight -= learning_rate
                dismiss_count += 1
            else:
                weight += learning_rate * 0.5
                confirm_count += 1

            weight = round(
                max(self.ADAPTIVE_WEIGHT_FLOOR, min(self.ADAPTIVE_WEIGHT_CEIL, weight)),
                4,
            )
            feedback_count += 1

            db.execute(
                """INSERT INTO project_detector_weights
                    (project_id, alert_type, entity_canonical_name, weight,
                     feedback_count, dismiss_count, confirm_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT (project_id, alert_type, entity_canonical_name)
                DO UPDATE SET
                    weight = excluded.weight,
                    feedback_count = excluded.feedback_count,
                    dismiss_count = excluded.dismiss_count,
                    confirm_count = excluded.confirm_count,
                    updated_at = datetime('now')
                """,
                (project_id, alert_type, entity_canonical_name, weight,
                 feedback_count, dismiss_count, confirm_count),
            )

            # Invalidar cache
            cache_key = (project_id, alert_type, entity_canonical_name)
            cache = getattr(self, "_adaptive_weights_cache", {})
            cache[cache_key] = weight

            entity_label = f" entity={entity_canonical_name}" if entity_canonical_name else ""
            logger.debug(
                f"Adaptive weight updated: project={project_id} type={alert_type}"
                f"{entity_label} weight={weight} (dismissed={dismissed})"
            )
            return weight
        except Exception as e:
            logger.warning(f"Failed to update adaptive weight: {e}")
            return 1.0

    def get_adaptive_weights(self, project_id: int) -> dict[str, dict]:
        """Obtiene todos los pesos adaptativos de un proyecto (project + per-entity)."""
        try:
            from ..persistence.database import get_database

            db = get_database()
            rows = db.fetchall(
                "SELECT alert_type, entity_canonical_name, weight, "
                "feedback_count, dismiss_count, confirm_count "
                "FROM project_detector_weights WHERE project_id = ? ORDER BY weight ASC",
                (project_id,),
            )
            result = {}
            for r in rows:
                entity = r["entity_canonical_name"] or ""
                key = f"{r['alert_type']}/{entity}" if entity else r["alert_type"]
                result[key] = {
                    "weight": r["weight"],
                    "alert_type": r["alert_type"],
                    "entity": entity,
                    "feedback_count": r["feedback_count"],
                    "dismiss_count": r["dismiss_count"],
                    "confirm_count": r["confirm_count"],
                }
            return result
        except Exception:
            return {}

    def clear_adaptive_weights_cache(self, project_id: int | None = None) -> None:
        """Limpia la cache de pesos adaptativos."""
        cache = getattr(self, "_adaptive_weights_cache", None)
        if cache is None:
            return
        if project_id is None:
            cache.clear()
        else:
            self._adaptive_weights_cache = {
                k: v for k, v in cache.items() if k[0] != project_id
            }


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
