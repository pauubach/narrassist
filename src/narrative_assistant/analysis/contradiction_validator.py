"""
Validador LLM de contradicciones cross-book.

Toma candidatos de contradicción (de cross_book_events.py) y los valida
con LLM multi-modelo para reducir falsos positivos.

Sigue el patrón de temporal/inconsistencies.py:
- LLM opcional (degrada si no hay Ollama)
- Multi-model voting vía client.voting_query()
- Veredictos: CONFIRMED, PROBABLE, DOUBTFUL, DISMISSED
"""

import logging
import threading
from dataclasses import dataclass

from .cross_book_events import EventContradiction

logger = logging.getLogger(__name__)


# ============================================================================
# Configuración
# ============================================================================

# Multiplicadores de confianza según veredicto LLM
VERDICT_MULTIPLIERS = {
    "CONFIRMED": 1.2,
    "PROBABLE": 1.0,
    "DOUBTFUL": 0.6,
    "DISMISSED": 0.2,
}

# Solo validamos contradicciones con confianza >= este umbral
MIN_CONFIDENCE_FOR_LLM = 0.4


# ============================================================================
# Resultado de validación
# ============================================================================

@dataclass
class ValidationResult:
    """Resultado de validar una contradicción con LLM."""

    contradiction: EventContradiction
    verdict: str  # CONFIRMED, PROBABLE, DOUBTFUL, DISMISSED
    original_confidence: float
    adjusted_confidence: float
    reasoning: str
    narrative_explanation: str | None = None
    models_used: list[str] | None = None

    @property
    def is_valid(self) -> bool:
        """True si la contradicción sobrevivió la validación."""
        return self.verdict in ("CONFIRMED", "PROBABLE")


# ============================================================================
# Validador
# ============================================================================

_lock = threading.Lock()
_instance: "ContradictionValidator | None" = None


def get_contradiction_validator() -> "ContradictionValidator":
    """Singleton thread-safe."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = ContradictionValidator()
    return _instance


def reset_contradiction_validator() -> None:
    """Reset singleton (para tests)."""
    global _instance
    with _lock:
        _instance = None


class ContradictionValidator:
    """
    Valida contradicciones cross-book usando LLM.

    Uso:
        validator = get_contradiction_validator()
        results = validator.validate_batch(contradictions, context_provider)
    """

    def __init__(self):
        self._client = None
        self._client_checked = False

    def _get_client(self):
        """Lazy-load del cliente LLM."""
        if not self._client_checked:
            try:
                from narrative_assistant.llm.client import get_llm_client
                self._client = get_llm_client()
            except Exception as e:
                logger.warning(f"LLM client not available: {e}")
                self._client = None
            self._client_checked = True
        return self._client

    @property
    def is_available(self) -> bool:
        """True si hay un cliente LLM disponible."""
        client = self._get_client()
        return client is not None and client.is_available

    def validate_single(
        self,
        contradiction: EventContradiction,
        context_a: str = "",
        context_b: str = "",
    ) -> ValidationResult:
        """
        Valida una contradicción individual con LLM.

        Args:
            contradiction: La contradicción candidata
            context_a: Fragmento de texto del libro A (alrededor del evento)
            context_b: Fragmento de texto del libro B (alrededor del evento)

        Returns:
            ValidationResult con veredicto y confianza ajustada
        """
        if not self.is_available:
            return self._fallback_result(contradiction)

        if contradiction.confidence < MIN_CONFIDENCE_FOR_LLM:
            return ValidationResult(
                contradiction=contradiction,
                verdict="DOUBTFUL",
                original_confidence=contradiction.confidence,
                adjusted_confidence=contradiction.confidence * 0.8,
                reasoning="Confianza demasiado baja para validación LLM",
            )

        try:
            return self._validate_with_llm(contradiction, context_a, context_b)
        except Exception as e:
            logger.warning(f"LLM validation failed for {contradiction.rule}: {e}")
            return self._fallback_result(contradiction)

    def validate_batch(
        self,
        contradictions: list[EventContradiction],
        context_provider: "callable | None" = None,
    ) -> list[ValidationResult]:
        """
        Valida un lote de contradicciones.

        Args:
            contradictions: Lista de contradicciones candidatas
            context_provider: Función(contradiction) -> (context_a, context_b)
                Si es None, se valida sin contexto textual.
        """
        results = []

        for contradiction in contradictions:
            context_a, context_b = "", ""
            if context_provider:
                try:
                    context_a, context_b = context_provider(contradiction)
                except Exception as e:
                    logger.debug(f"Context provider failed: {e}")

            result = self.validate_single(contradiction, context_a, context_b)
            results.append(result)

            # Ceder al chat entre iteraciones
            self._yield_to_chat()

        return results

    def _validate_with_llm(
        self,
        contradiction: EventContradiction,
        context_a: str,
        context_b: str,
    ) -> ValidationResult:
        """Ejecuta validación LLM real."""
        from narrative_assistant.llm.prompts import (
            EVENT_CONTRADICTION_EXAMPLES,
            EVENT_CONTRADICTION_SYSTEM,
            EVENT_CONTRADICTION_TEMPLATE,
            build_prompt,
        )
        from narrative_assistant.llm.sanitization import (
            sanitize_entity_name,
            validate_llm_response,
        )

        # Construir prompt
        prompt = build_prompt(
            EVENT_CONTRADICTION_TEMPLATE,
            examples=EVENT_CONTRADICTION_EXAMPLES,
            rule=contradiction.rule,
            entity_name=sanitize_entity_name(contradiction.entity_name),
            description=contradiction.description,
            book_a=contradiction.book_a_name,
            book_b=contradiction.book_b_name,
            context_a=context_a or "(sin contexto disponible)",
            context_b=context_b or "(sin contexto disponible)",
        )

        client = self._get_client()

        # Intentar voting_query para multi-modelo
        try:
            voting_result = client.voting_query(
                task_name="contradiction",
                prompt=prompt,
                system=EVENT_CONTRADICTION_SYSTEM,
                parse_fn=self._parse_response,
                max_tokens=500,
                temperature=0.1,
            )

            if voting_result and voting_result.is_valid and voting_result.consensus:
                parsed = voting_result.consensus
                verdict = parsed.get("verdict", "DOUBTFUL")
                adjusted = parsed.get("adjusted_confidence", contradiction.confidence)

                # Aplicar multiplicador del veredicto
                multiplier = VERDICT_MULTIPLIERS.get(verdict, 1.0)
                final_confidence = min(1.0, contradiction.confidence * multiplier)

                # Si el LLM dio su propia confianza, hacer media ponderada
                if adjusted > 0:
                    final_confidence = 0.6 * final_confidence + 0.4 * adjusted

                return ValidationResult(
                    contradiction=contradiction,
                    verdict=verdict,
                    original_confidence=contradiction.confidence,
                    adjusted_confidence=round(final_confidence, 3),
                    reasoning=parsed.get("reasoning", ""),
                    narrative_explanation=parsed.get("narrative_explanation"),
                    models_used=voting_result.models_used,
                )
        except Exception as e:
            logger.debug(f"Voting query failed, trying simple completion: {e}")

        # Fallback: completar con un solo modelo
        return self._validate_simple(client, prompt, contradiction)

    def _validate_simple(
        self,
        client,
        prompt: str,
        contradiction: EventContradiction,
    ) -> ValidationResult:
        """Validación con un solo modelo (fallback)."""
        from narrative_assistant.llm.prompts import EVENT_CONTRADICTION_SYSTEM

        response = client.complete(
            prompt=prompt,
            system=EVENT_CONTRADICTION_SYSTEM,
            max_tokens=500,
            temperature=0.1,
        )

        if not response:
            return self._fallback_result(contradiction)

        parsed = self._parse_response(response)
        if not parsed:
            return self._fallback_result(contradiction)

        verdict = parsed.get("verdict", "DOUBTFUL")
        multiplier = VERDICT_MULTIPLIERS.get(verdict, 1.0)
        adjusted = min(1.0, contradiction.confidence * multiplier)

        return ValidationResult(
            contradiction=contradiction,
            verdict=verdict,
            original_confidence=contradiction.confidence,
            adjusted_confidence=round(adjusted, 3),
            reasoning=parsed.get("reasoning", ""),
            narrative_explanation=parsed.get("narrative_explanation"),
            models_used=["single"],
        )

    def _parse_response(self, response_text: str) -> dict | None:
        """Parsea la respuesta JSON del LLM."""
        from narrative_assistant.llm.sanitization import validate_llm_response

        expected_keys = ["verdict", "reasoning"]
        result = validate_llm_response(response_text, expected_keys)

        if not result:
            return None

        # Normalizar veredicto
        verdict = result.get("verdict", "").upper().strip()
        valid_verdicts = {"CONFIRMED", "PROBABLE", "DOUBTFUL", "DISMISSED"}
        if verdict not in valid_verdicts:
            # Intentar mapeo flexible
            if "CONFIRM" in verdict:
                verdict = "CONFIRMED"
            elif "PROBAB" in verdict:
                verdict = "PROBABLE"
            elif "DISMISS" in verdict or "DESCART" in verdict:
                verdict = "DISMISSED"
            else:
                verdict = "DOUBTFUL"

        result["verdict"] = verdict

        # Normalizar confianza
        try:
            conf = float(result.get("adjusted_confidence", 0))
            result["adjusted_confidence"] = max(0.0, min(1.0, conf))
        except (ValueError, TypeError):
            result["adjusted_confidence"] = 0.0

        return result

    def _fallback_result(self, contradiction: EventContradiction) -> ValidationResult:
        """Resultado cuando LLM no está disponible."""
        return ValidationResult(
            contradiction=contradiction,
            verdict="PROBABLE",
            original_confidence=contradiction.confidence,
            adjusted_confidence=contradiction.confidence,
            reasoning="Validación sin LLM — confianza original mantenida",
        )

    def _yield_to_chat(self):
        """Cede al chat interactivo entre validaciones."""
        try:
            from narrative_assistant.llm.client import get_llm_scheduler
            scheduler = get_llm_scheduler()
            if scheduler:
                scheduler.yield_to_chat()
        except Exception:
            pass
