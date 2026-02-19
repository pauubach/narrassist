"""
Revisor de alertas basado en LLM.

Usa un modelo de lenguaje local (Ollama) para revisar alertas
y filtrar falsos positivos antes de mostrarlas al usuario.
"""

import logging
from dataclasses import dataclass

from ..llm.client import get_llm_client

logger = logging.getLogger(__name__)


@dataclass
class AlertReviewResult:
    """Resultado de la revisión de una alerta."""

    is_valid: bool  # True si la alerta es válida
    confidence: float  # Confianza en la decisión (0.0-1.0)
    reason: str  # Explicación de la decisión
    suggested_severity: str | None = None  # Severidad sugerida si es válida


class LLMAlertReviewer:
    """
    Revisa alertas usando un LLM local para filtrar falsos positivos.

    Analiza el contexto de cada alerta y decide si es un problema real
    o un falso positivo del detector automático.
    """

    REVIEW_PROMPT_TEMPLATE = """Eres un corrector editorial experto en español. Tu tarea es revisar una alerta automática para determinar si es un problema real o un falso positivo.

**Alerta detectada:**
- Tipo: {alert_type}
- Categoría: {category}
- Texto marcado: "{text}"
- Explicación del detector: {explanation}
{suggestion_line}

**Contexto en el documento:**
«{context}»

**Tu tarea:**
1. Analiza si el problema señalado es real o es un falso positivo
2. Considera el contexto literario/editorial
3. Ten en cuenta que algunos "errores" pueden ser intencionales (diálogos, estilo del autor)

**Responde SOLO con un JSON válido:**
{{
  "is_valid": true/false,
  "confidence": 0.0-1.0,
  "reason": "explicación breve",
  "severity": "critical/warning/info/hint" (solo si is_valid es true)
}}

IMPORTANTE: Sé conservador. Si no estás seguro, marca como válido (is_valid: true) para que el corrector humano decida."""

    def __init__(
        self,
        model: str = "llama3.2",
        min_confidence_to_filter: float = 0.8,
    ):
        """
        Inicializa el revisor.

        Args:
            model: Modelo de Ollama a usar
            min_confidence_to_filter: Confianza mínima para filtrar una alerta
        """
        self.model = model
        self.min_confidence_to_filter = min_confidence_to_filter
        self._client = None

    def _get_client(self):
        """Obtiene el cliente LLM."""
        if self._client is None:
            self._client = get_llm_client()
        return self._client

    def review_alert(
        self,
        alert_type: str,
        category: str,
        text: str,
        explanation: str,
        context: str,
        suggestion: str | None = None,
    ) -> AlertReviewResult:
        """
        Revisa una alerta individual.

        Args:
            alert_type: Tipo de alerta (ej: "typography_wrong_dash")
            category: Categoría (typography, repetition, agreement)
            text: Texto marcado como problemático
            explanation: Explicación del detector
            context: Contexto alrededor del problema
            suggestion: Sugerencia de corrección (opcional)

        Returns:
            Resultado de la revisión
        """
        try:
            client = self._get_client()

            suggestion_line = f'- Sugerencia: "{suggestion}"' if suggestion else ""

            prompt = self.REVIEW_PROMPT_TEMPLATE.format(
                alert_type=alert_type,
                category=category,
                text=text,
                explanation=explanation,
                suggestion_line=suggestion_line,
                context=context[:500],  # Limitar contexto
            )

            response = client.generate(
                prompt=prompt,
                model=self.model,
                temperature=0.1,  # Baja temperatura para consistencia
                max_tokens=200,
            )

            return self._parse_response(response)

        except RuntimeError as e:
            logger.warning(f"LLM review failed: {e}")
            # Si falla el LLM, marcar como válida (conservador)
            return AlertReviewResult(
                is_valid=True,
                confidence=0.5,
                reason="No se pudo revisar con LLM, se mantiene la alerta",
            )
        except Exception as e:
            logger.error(f"Error in LLM alert review: {e}")
            return AlertReviewResult(
                is_valid=True,
                confidence=0.5,
                reason=f"Error durante revisión: {str(e)}",
            )

    def _parse_response(self, response: str) -> AlertReviewResult:
        """Parsea la respuesta del LLM."""
        import json
        import re

        # Intentar extraer JSON de la respuesta
        try:
            # Buscar JSON en la respuesta
            json_match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                return AlertReviewResult(
                    is_valid=bool(data.get("is_valid", True)),
                    confidence=float(data.get("confidence", 0.5)),
                    reason=str(data.get("reason", "Sin explicación")),
                    suggested_severity=data.get("severity"),
                )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response: {e}")

        # Fallback: buscar palabras clave
        response_lower = response.lower()
        if "falso positivo" in response_lower or "is_valid.*false" in response_lower:
            return AlertReviewResult(
                is_valid=False,
                confidence=0.6,
                reason="Detectado como posible falso positivo",
            )

        # Por defecto, mantener la alerta
        return AlertReviewResult(
            is_valid=True,
            confidence=0.5,
            reason="No se pudo determinar, se mantiene la alerta",
        )

    def review_batch(
        self,
        alerts: list[dict],
        max_reviews: int = 50,
    ) -> list[tuple[dict, AlertReviewResult]]:
        """
        Revisa un lote de alertas.

        Args:
            alerts: Lista de alertas (dicts con type, category, text, etc.)
            max_reviews: Máximo de alertas a revisar (para limitar tiempo)

        Returns:
            Lista de tuplas (alerta, resultado)
        """
        results = []

        for i, alert in enumerate(alerts[:max_reviews]):
            result = self.review_alert(
                alert_type=alert.get("type", "unknown"),
                category=alert.get("category", "other"),
                text=alert.get("text", ""),
                explanation=alert.get("explanation", ""),
                context=alert.get("context", ""),
                suggestion=alert.get("suggestion"),
            )

            results.append((alert, result))

            # Log progreso
            if (i + 1) % 10 == 0:
                logger.info(f"LLM reviewed {i + 1}/{min(len(alerts), max_reviews)} alerts")

        # Estadísticas
        valid_count = sum(1 for _, r in results if r.is_valid)
        filtered_count = len(results) - valid_count
        logger.info(
            f"LLM review complete: {valid_count} valid, "
            f"{filtered_count} filtered as false positives"
        )

        return results

    def should_filter_alert(self, review_result: AlertReviewResult) -> bool:
        """
        Determina si una alerta debe filtrarse basado en la revisión.

        Args:
            review_result: Resultado de la revisión LLM

        Returns:
            True si la alerta debe filtrarse (falso positivo con alta confianza)
        """
        return (
            not review_result.is_valid and review_result.confidence >= self.min_confidence_to_filter
        )


def get_llm_reviewer(model: str = "llama3.2") -> LLMAlertReviewer:
    """Obtiene una instancia del revisor LLM."""
    return LLMAlertReviewer(model=model)
