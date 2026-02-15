"""
Clase base para detectores de correcciones.

Los detectores analizan el texto y generan CorrectionIssue que se
presentan al corrector como sugerencias. El corrector decide si
aplicar o ignorar cada sugerencia.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .types import CorrectionCategory


@dataclass
class CorrectionIssue:
    """
    Issue de corrección detectado.

    Representa un problema potencial encontrado en el texto que se
    presenta al corrector como sugerencia. NO se aplica automáticamente.

    Attributes:
        category: Categoría principal (typography, repetition, etc.)
        issue_type: Tipo específico del problema
        start_char: Posición inicial en el texto
        end_char: Posición final en el texto
        text: Texto problemático encontrado
        explanation: Explicación del problema para el corrector
        suggestion: Texto sugerido como corrección (opcional)
        confidence: Confianza de la detección (0.0-1.0)
        context: Contexto alrededor del problema
        chapter_index: Índice del capítulo (si aplica)
        rule_id: ID de la regla que detectó el problema
        extra_data: Datos adicionales específicos del tipo
    """

    category: str
    issue_type: str
    start_char: int
    end_char: int
    text: str
    explanation: str
    suggestion: str | None = None
    confidence: float = 0.8
    context: str = ""
    chapter_index: int | None = None
    rule_id: str | None = None
    extra_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "category": self.category,
            "issue_type": self.issue_type,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "text": self.text,
            "explanation": self.explanation,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "context": self.context,
            "chapter_index": self.chapter_index,
            "rule_id": self.rule_id,
            "extra_data": self.extra_data,
        }


class BaseDetector(ABC):
    """
    Clase base abstracta para detectores de correcciones.

    Los detectores analizan texto y generan una lista de CorrectionIssue
    que se presentan al corrector como sugerencias.

    Cada detector implementa:
    - detect(): Método principal que analiza el texto
    - category: Categoría de alertas que genera
    """

    @abstractmethod
    def detect(
        self,
        text: str,
        chapter_index: int | None = None,
    ) -> list[CorrectionIssue]:
        """
        Detecta problemas en el texto.

        Args:
            text: Texto a analizar
            chapter_index: Índice del capítulo (opcional)

        Returns:
            Lista de CorrectionIssue encontrados
        """
        pass

    @property
    @abstractmethod
    def category(self) -> CorrectionCategory:
        """Categoría de correcciones que genera este detector."""
        pass

    @property
    def requires_spacy(self) -> bool:
        """Si el detector necesita análisis de spaCy."""
        return False

    @property
    def requires_llm(self) -> bool:
        """Si el detector necesita un LLM (Ollama)."""
        return False

    def _extract_context(self, text: str, start: int, end: int, window: int = 40) -> str:
        """
        Extrae contexto alrededor de una posición.

        Args:
            text: Texto completo
            start: Posición inicial del problema
            end: Posición final del problema
            window: Caracteres de contexto a cada lado

        Returns:
            Texto de contexto con el problema marcado
        """
        ctx_start = max(0, start - window)
        ctx_end = min(len(text), end + window)

        # Ajustar a límites de palabra
        while ctx_start > 0 and text[ctx_start] not in " \n\t":
            ctx_start -= 1
        while ctx_end < len(text) and text[ctx_end] not in " \n\t":
            ctx_end += 1

        context = text[ctx_start:ctx_end].strip()

        # Añadir elipsis si hay más texto
        if ctx_start > 0:
            context = "..." + context
        if ctx_end < len(text):
            context = context + "..."

        return context
