"""
Detector basado en el glosario del proyecto.

Detecta usos inconsistentes de términos definidos en el glosario:
- Uso de variantes en lugar del término canónico
- Posibles términos inventados sin definición
- Términos técnicos sin explicación
"""

import logging
import re
from typing import Optional

from ..base import BaseDetector, CorrectionIssue
from ..config import GlossaryConfig
from ..types import CorrectionCategory, GlossaryIssueType
from ...persistence.glossary import GlossaryEntry, GlossaryRepository

logger = logging.getLogger(__name__)


class GlossaryDetector(BaseDetector):
    """
    Detector de inconsistencias según el glosario del proyecto.

    Usa el glosario definido por el usuario para:
    1. Detectar cuando se usa una variante en lugar del término canónico
    2. Sugerir el término preferido para mantener consistencia
    3. Opcionalmente, detectar términos que podrían necesitar definición
    """

    def __init__(
        self,
        config: Optional[GlossaryConfig] = None,
        glossary_repository: Optional[GlossaryRepository] = None,
    ):
        self.config = config or GlossaryConfig()
        self._repository = glossary_repository or GlossaryRepository()
        self._entries_cache: dict[int, list[GlossaryEntry]] = {}
        self._patterns_cache: dict[int, dict[str, tuple[re.Pattern, GlossaryEntry]]] = {}

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.GLOSSARY

    @property
    def requires_spacy(self) -> bool:
        return False  # Funciona con regex

    def _get_entries(self, project_id: int) -> list[GlossaryEntry]:
        """Obtiene y cachea las entradas del glosario."""
        if project_id not in self._entries_cache:
            self._entries_cache[project_id] = self._repository.list_by_project(project_id)
        return self._entries_cache[project_id]

    def _get_patterns(
        self, project_id: int
    ) -> dict[str, tuple[re.Pattern, GlossaryEntry]]:
        """
        Compila patrones regex para las variantes del glosario.

        Returns:
            Dict[variante_lower -> (pattern, entry)]
        """
        if project_id not in self._patterns_cache:
            patterns = {}
            entries = self._get_entries(project_id)

            for entry in entries:
                # Crear patrón para cada variante
                for variant in entry.variants:
                    variant_lower = variant.lower()
                    # Evitar duplicados (si misma variante en múltiples entradas)
                    if variant_lower not in patterns:
                        patterns[variant_lower] = (
                            re.compile(
                                r"\b" + re.escape(variant) + r"\b",
                                re.IGNORECASE
                            ),
                            entry
                        )

            self._patterns_cache[project_id] = patterns

        return self._patterns_cache[project_id]

    def clear_cache(self, project_id: Optional[int] = None) -> None:
        """Limpia el caché de entradas (llamar cuando se modifica el glosario)."""
        if project_id is None:
            self._entries_cache.clear()
            self._patterns_cache.clear()
        else:
            self._entries_cache.pop(project_id, None)
            self._patterns_cache.pop(project_id, None)

    def detect(
        self,
        text: str,
        chapter_index: Optional[int] = None,
        project_id: Optional[int] = None,
        spacy_doc=None,
        **kwargs,
    ) -> list[CorrectionIssue]:
        """
        Detecta usos inconsistentes de términos del glosario.

        Args:
            text: Texto a analizar
            chapter_index: Índice del capítulo
            project_id: ID del proyecto (requerido para acceder al glosario)
            spacy_doc: Documento spaCy (opcional)

        Returns:
            Lista de CorrectionIssue encontrados
        """
        if not self.config.enabled:
            return []

        if project_id is None:
            logger.debug("GlossaryDetector requires project_id, skipping")
            return []

        issues: list[CorrectionIssue] = []

        # Detectar uso de variantes
        if self.config.alert_on_variants:
            issues.extend(
                self._detect_variant_usage(text, project_id, chapter_index)
            )

        # Actualizar estadísticas de uso si está habilitado
        if self.config.update_usage_stats:
            self._update_usage_stats(text, project_id, chapter_index)

        return issues

    def _detect_variant_usage(
        self,
        text: str,
        project_id: int,
        chapter_index: Optional[int],
    ) -> list[CorrectionIssue]:
        """Detecta cuando se usa una variante en lugar del término canónico."""
        issues = []
        patterns = self._get_patterns(project_id)

        for variant_lower, (pattern, entry) in patterns.items():
            for match in pattern.finditer(text):
                found_text = match.group()
                start = match.start()
                end = match.end()

                # Verificar si no es el término canónico (podría coincidir si es case different)
                if found_text.lower() == entry.term.lower():
                    continue

                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=GlossaryIssueType.VARIANT_USED.value,
                        start_char=start,
                        end_char=end,
                        text=found_text,
                        explanation=(
                            f'Se encontró "{found_text}" que es una variante de '
                            f'"{entry.term}". Para mantener consistencia, '
                            f"considere usar el término canónico del glosario."
                        ),
                        suggestion=entry.term,
                        confidence=self.config.base_confidence,
                        context=self._extract_context(text, start, end),
                        chapter_index=chapter_index,
                        rule_id=f"glossary_variant_{entry.id}",
                        extra_data={
                            "glossary_entry_id": entry.id,
                            "canonical_term": entry.term,
                            "variant_used": found_text,
                            "category": entry.category,
                            "definition": entry.definition[:100] if entry.definition else None,
                        },
                    )
                )

        return issues

    def _update_usage_stats(
        self,
        text: str,
        project_id: int,
        chapter_index: Optional[int],
    ) -> None:
        """Actualiza las estadísticas de uso de los términos del glosario."""
        entries = self._get_entries(project_id)
        text_lower = text.lower()

        for entry in entries:
            count = 0

            # Contar término principal
            term_pattern = re.compile(
                r"\b" + re.escape(entry.term) + r"\b",
                re.IGNORECASE
            )
            count += len(term_pattern.findall(text))

            # Contar variantes
            for variant in entry.variants:
                variant_pattern = re.compile(
                    r"\b" + re.escape(variant) + r"\b",
                    re.IGNORECASE
                )
                count += len(variant_pattern.findall(text))

            if count > 0:
                # Actualizar solo si hay ocurrencias
                entry.usage_count = (entry.usage_count or 0) + count

                # Actualizar primer capítulo si no está establecido
                if entry.first_chapter is None and chapter_index is not None:
                    entry.first_chapter = chapter_index

                # Guardar cambios
                self._repository.update(entry)

    def get_summary(self, text: str, project_id: int) -> dict:
        """
        Genera un resumen del uso de términos del glosario.

        Args:
            text: Texto a analizar
            project_id: ID del proyecto

        Returns:
            Diccionario con estadísticas
        """
        entries = self._get_entries(project_id)
        summary = {
            "total_entries": len(entries),
            "by_category": {},
            "most_used": [],
            "unused": [],
            "variants_found": [],
        }

        # Contar por categoría
        for entry in entries:
            cat = entry.category or "general"
            if cat not in summary["by_category"]:
                summary["by_category"][cat] = 0
            summary["by_category"][cat] += 1

        # Analizar uso en el texto
        text_lower = text.lower()
        usage_data = []

        for entry in entries:
            count = 0

            # Buscar término principal
            term_pattern = re.compile(
                r"\b" + re.escape(entry.term) + r"\b",
                re.IGNORECASE
            )
            term_count = len(term_pattern.findall(text))
            count += term_count

            # Buscar variantes
            variant_counts = {}
            for variant in entry.variants:
                variant_pattern = re.compile(
                    r"\b" + re.escape(variant) + r"\b",
                    re.IGNORECASE
                )
                v_count = len(variant_pattern.findall(text))
                if v_count > 0:
                    variant_counts[variant] = v_count
                    count += v_count

            usage_data.append({
                "term": entry.term,
                "count": count,
                "term_count": term_count,
                "variant_counts": variant_counts,
            })

        # Ordenar por uso
        usage_data.sort(key=lambda x: x["count"], reverse=True)

        # Top 10 más usados
        summary["most_used"] = [
            {"term": d["term"], "count": d["count"]}
            for d in usage_data[:10]
            if d["count"] > 0
        ]

        # Términos sin usar
        summary["unused"] = [
            d["term"] for d in usage_data if d["count"] == 0
        ]

        # Variantes encontradas
        for d in usage_data:
            if d["variant_counts"]:
                summary["variants_found"].append({
                    "canonical": d["term"],
                    "variants": d["variant_counts"],
                })

        return summary
