"""
Mixin de separacion de entidades coordinadas para NERExtractor.

Contiene los metodos que separan entidades coordinadas como
"Pedro y Carmen" en entidades individuales.

Este modulo se separa de ner.py para reducir el tamano del archivo
principal y mejorar la mantenibilidad. La clase NERCoordSplitterMixin
se usa como mixin de NERExtractor.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ner import ExtractedEntity

logger = logging.getLogger(__name__)


class NERCoordSplitterMixin:
    """
    Mixin con metodos de separacion de entidades coordinadas.

    Separa entidades como "Pedro y Carmen" en entidades individuales
    usando analisis de dependencias de spaCy y fallbacks heuristicos.

    Se usa como mixin de NERExtractor.
    """

    def _simple_coord_split(self, text: str) -> list[tuple[str, int]]:
        """
        Divide texto coordinado simple como "Pedro y Carmen" en partes.

        Fallback cuando spaCy no detecta la estructura coordinada.

        Args:
            text: Texto a dividir

        Returns:
            Lista de tuplas (texto, offset) para cada parte
        """
        import re

        parts = []

        # Buscar patron "X y Y" o "X e Y"
        # Solo dividir si ambas partes empiezan con mayuscula (nombres propios)
        pattern = r"^([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)\s+[ye]\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)$"

        match = re.match(pattern, text.strip())
        if match:
            part1 = match.group(1)
            part2 = match.group(2)

            # Encontrar offsets
            offset1 = text.find(part1)
            offset2 = text.find(part2, offset1 + len(part1))

            if offset1 >= 0:
                parts.append((part1, offset1))
            if offset2 >= 0:
                parts.append((part2, offset2))

        return parts

    def _entities_overlap(
        self,
        start1: int,
        end1: int,
        start2: int,
        end2: int,
    ) -> bool:
        """Verifica si dos rangos de entidades se solapan."""
        return not (end1 <= start2 or end2 <= start1)

    def _split_coordinated_entities(
        self,
        doc,
        entities: list[ExtractedEntity],
    ) -> list[ExtractedEntity]:
        """
        Separa entidades coordinadas como "Pedro y Carmen" en entidades individuales.

        Usa analisis de dependencias de spaCy para detectar estructuras coordinadas
        y extraer cada componente como entidad separada.

        Args:
            doc: Documento spaCy procesado
            entities: Lista de entidades detectadas

        Returns:
            Lista de entidades con coordinaciones separadas
        """
        from .ner import ExtractedEntity

        result = []
        processed_spans = set()

        for entity in entities:
            # Verificar si ya procesamos este span
            span_key = (entity.start_char, entity.end_char)
            if span_key in processed_spans:
                continue

            # Verificar si contiene conjuncion coordinante
            if " y " not in entity.text.lower() and " e " not in entity.text.lower():
                result.append(entity)
                processed_spans.add(span_key)
                continue

            # Buscar tokens en el span de la entidad
            entity_tokens = [
                t for t in doc if t.idx >= entity.start_char and t.idx < entity.end_char
            ]

            # Buscar la conjuncion
            conj_token = None
            for token in entity_tokens:
                if token.lower_ in ("y", "e") and token.dep_ == "cc":
                    conj_token = token
                    break

            if not conj_token:
                # Fallback: separacion simple por patron "X y Y"
                # Esto funciona cuando spaCy no detecta la estructura coordinada
                parts = self._simple_coord_split(entity.text)
                if len(parts) >= 2:
                    for part_text, part_offset in parts:
                        if self._is_valid_spacy_entity(part_text):  # type: ignore[attr-defined]
                            new_ent = ExtractedEntity(
                                text=part_text,
                                label=entity.label,
                                start_char=entity.start_char + part_offset,
                                end_char=entity.start_char + part_offset + len(part_text),
                                confidence=entity.confidence * 0.85,
                                source="simple_coord_split",
                            )
                            result.append(new_ent)
                            processed_spans.add((new_ent.start_char, new_ent.end_char))
                    processed_spans.add(span_key)
                    continue
                else:
                    # No se pudo separar, mantener original
                    result.append(entity)
                    processed_spans.add(span_key)
                    continue

            # Encontrar los elementos coordinados
            # El patron puede ser:
            # 1. "Pedro y Carmen" donde y->Carmen y Carmen->Pedro(conj)
            # 2. "Pedro y Carmen" donde y->Pedro y Pedro->Carmen(conj)
            # Buscamos todos los tokens con dep=conj y su head

            coordinated = []
            for token in entity_tokens:
                if token.dep_ == "conj":
                    # Encontrar el head de la coordinacion
                    if token.head in entity_tokens:
                        coordinated.append(token.head)
                    coordinated.append(token)

            # Si no encontramos con dep=conj, buscar nombres propios directamente
            if len(coordinated) < 2:
                coordinated = [t for t in entity_tokens if t.pos_ == "PROPN"]

            if len(coordinated) < 2:
                # No se encontro estructura coordinada valida, usar fallback
                parts = self._simple_coord_split(entity.text)
                if len(parts) >= 2:
                    for part_text, part_offset in parts:
                        if self._is_valid_spacy_entity(part_text):  # type: ignore[attr-defined]
                            new_ent = ExtractedEntity(
                                text=part_text,
                                label=entity.label,
                                start_char=entity.start_char + part_offset,
                                end_char=entity.start_char + part_offset + len(part_text),
                                confidence=entity.confidence * 0.85,
                                source="simple_coord_split",
                            )
                            result.append(new_ent)
                            processed_spans.add((new_ent.start_char, new_ent.end_char))
                    processed_spans.add(span_key)
                    continue
                else:
                    result.append(entity)
                    processed_spans.add(span_key)
                    continue

            # Crear entidades separadas para cada elemento coordinado
            for coord_token in coordinated:
                # Encontrar el span completo del nombre (puede incluir apellido/modificadores)
                start = coord_token.idx
                end = coord_token.idx + len(coord_token.text)

                # Expandir para incluir tokens siguientes que sean parte del nombre
                # (apellidos, titulos, etc.)
                for next_token in doc:
                    if next_token.idx == end + 1:  # Token siguiente
                        # Incluir si es un nombre propio o parte del nombre
                        if next_token.pos_ in ("PROPN", "NOUN") and next_token.dep_ in (
                            "flat",
                            "appos",
                            "compound",
                        ):
                            end = next_token.idx + len(next_token.text)
                        else:
                            break

                # Verificar que el span es valido y dentro de la entidad original
                if start >= entity.start_char and end <= entity.end_char:
                    coord_text = doc.text[start:end]

                    # Solo anadir si el texto parece un nombre valido
                    if coord_text and coord_text[0].isupper() and len(coord_text) >= 2:
                        new_entity = ExtractedEntity(
                            text=coord_text,
                            label=entity.label,
                            start_char=start,
                            end_char=end,
                            confidence=entity.confidence * 0.9,  # Ligeramente menor confianza
                            source="coord_split",
                        )
                        result.append(new_entity)
                        processed_spans.add((start, end))

            # Marcar el span original como procesado
            processed_spans.add(span_key)

        # Deduplicar y ordenar
        seen = set()
        unique_result = []
        for entity in sorted(result, key=lambda e: e.start_char):
            key = (entity.text, entity.start_char, entity.end_char)
            if key not in seen:
                unique_result.append(entity)
                seen.add(key)

        logger.debug(
            f"Separación de coordinados: {len(entities)} -> {len(unique_result)} entidades"
        )
        return unique_result
