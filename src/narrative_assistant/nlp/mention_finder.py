"""
Buscador de menciones adicionales de entidades.

Después del NER, busca ocurrencias adicionales de nombres ya conocidos
en el texto para completar el conteo de menciones.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class FoundMention:
    """Una mención encontrada de una entidad."""
    entity_name: str  # Nombre canónico de la entidad
    surface_form: str  # Forma en que aparece en el texto
    start_char: int
    end_char: int
    confidence: float = 0.9


class MentionFinder:
    """
    Busca menciones adicionales de entidades conocidas.

    Complementa el NER buscando todas las ocurrencias de nombres
    que ya fueron identificados como entidades.
    """

    # Palabras que no deben buscarse como menciones (muy comunes)
    SKIP_PATTERNS = {
        "el", "la", "los", "las", "un", "una", "de", "del", "al",
        "y", "o", "a", "en", "que", "se", "no", "es", "su", "si",
    }

    def __init__(
        self,
        min_name_length: int = 2,
        case_sensitive: bool = False,
        whole_word_only: bool = True,
    ):
        """
        Inicializa el buscador.

        Args:
            min_name_length: Longitud mínima de nombre a buscar
            case_sensitive: Si la búsqueda distingue mayúsculas
            whole_word_only: Si buscar solo palabras completas
        """
        self.min_name_length = min_name_length
        self.case_sensitive = case_sensitive
        self.whole_word_only = whole_word_only

    def find_all_mentions(
        self,
        text: str,
        entity_names: list[str],
        aliases: Optional[dict[str, list[str]]] = None,
        existing_positions: Optional[set[tuple[int, int]]] = None,
    ) -> list[FoundMention]:
        """
        Busca todas las menciones de los nombres de entidades en el texto.

        Args:
            text: Texto donde buscar
            entity_names: Lista de nombres canónicos de entidades
            aliases: Diccionario de aliases por entidad {nombre: [alias1, alias2]}
            existing_positions: Posiciones ya detectadas por NER (para evitar duplicados)

        Returns:
            Lista de menciones encontradas
        """
        mentions = []
        existing = existing_positions or set()

        # Construir lista de todos los nombres a buscar
        names_to_search = []
        for name in entity_names:
            if len(name) >= self.min_name_length:
                names_to_search.append((name, name))  # (nombre_buscar, nombre_canónico)

            # Añadir aliases
            if aliases and name in aliases:
                for alias in aliases[name]:
                    if len(alias) >= self.min_name_length:
                        names_to_search.append((alias, name))

        # Ordenar por longitud (más largos primero) para evitar solapamientos
        names_to_search.sort(key=lambda x: len(x[0]), reverse=True)

        # Buscar cada nombre
        found_positions = set()  # Evitar solapamientos

        for search_name, canonical_name in names_to_search:
            # Saltar palabras muy comunes
            if search_name.lower() in self.SKIP_PATTERNS:
                continue

            new_mentions = self._find_name_occurrences(
                text, search_name, canonical_name, existing, found_positions
            )

            for mention in new_mentions:
                found_positions.add((mention.start_char, mention.end_char))
                mentions.append(mention)

        logger.info(
            f"MentionFinder: Found {len(mentions)} additional mentions "
            f"for {len(entity_names)} entities"
        )

        return mentions

    def _find_name_occurrences(
        self,
        text: str,
        search_name: str,
        canonical_name: str,
        existing: set[tuple[int, int]],
        found: set[tuple[int, int]],
    ) -> list[FoundMention]:
        """Busca todas las ocurrencias de un nombre."""
        mentions = []

        # Construir patrón regex
        if self.whole_word_only:
            # Límites de palabra, con soporte para español
            pattern = rf'\b{re.escape(search_name)}\b'
        else:
            pattern = re.escape(search_name)

        flags = 0 if self.case_sensitive else re.IGNORECASE

        try:
            for match in re.finditer(pattern, text, flags):
                start = match.start()
                end = match.end()

                # ¿Ya existe esta posición exacta?
                if (start, end) in existing:
                    continue

                # ¿Solapa con menciones ya detectadas por NER?
                # Ej: NER detectó "María Sánchez" (0-14), evitar "María" (0-5)
                overlaps_existing = False
                for (e_start, e_end) in existing:
                    if not (end <= e_start or start >= e_end):
                        overlaps_existing = True
                        break

                if overlaps_existing:
                    continue

                # ¿Solapa con algo ya encontrado en esta búsqueda?
                overlaps_found = False
                for (f_start, f_end) in found:
                    if not (end <= f_start or start >= f_end):
                        overlaps_found = True
                        break

                if overlaps_found:
                    continue

                # Verificar contexto (no en medio de otra palabra)
                if start > 0 and text[start-1].isalpha():
                    continue
                if end < len(text) and text[end].isalpha():
                    continue

                mentions.append(FoundMention(
                    entity_name=canonical_name,
                    surface_form=match.group(),
                    start_char=start,
                    end_char=end,
                    confidence=0.85,  # Menor que NER (0.9-1.0)
                ))

        except re.error as e:
            logger.warning(f"Regex error searching for '{search_name}': {e}")

        return mentions

    def count_mentions_for_entity(
        self,
        text: str,
        entity_name: str,
        aliases: Optional[list[str]] = None,
    ) -> int:
        """
        Cuenta cuántas veces aparece una entidad (nombre + aliases).

        Args:
            text: Texto donde buscar
            entity_name: Nombre canónico
            aliases: Lista de aliases opcionales

        Returns:
            Número total de menciones
        """
        all_names = [entity_name]
        if aliases:
            all_names.extend(aliases)

        total = 0

        for name in all_names:
            if len(name) < self.min_name_length:
                continue
            if name.lower() in self.SKIP_PATTERNS:
                continue

            pattern = rf'\b{re.escape(name)}\b'
            flags = 0 if self.case_sensitive else re.IGNORECASE

            try:
                matches = list(re.finditer(pattern, text, flags))
                total += len(matches)
            except re.error:
                pass

        return total


def get_mention_finder() -> MentionFinder:
    """Obtiene instancia del buscador de menciones."""
    return MentionFinder()
