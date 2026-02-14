"""
Mixin de análisis de contexto lingüístico para extracción de atributos.

Detecta metáforas, negaciones, temporalidad, condiciones, contrastes
y cláusulas relativas para mejorar la precisión de la extracción.

Extraído de attributes.py para reducir complejidad del monolito.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AttributeContextMixin:
    """
    Mixin con métodos de análisis de contexto lingüístico.

    Proporciona detección de:
    - Diálogos (comillas, guiones)
    - Metáforas (comparaciones, símiles)
    - Negaciones
    - Temporalidad pasada
    - Condicionalidad
    - Contrastes ("no X, sino Y")
    - Cláusulas relativas

    Requiere que la clase que hereda tenga:
    - self._metaphor_patterns (compilados en __init__)
    - self._negation_patterns
    - self._temporal_past_patterns
    - self._conditional_patterns
    - self._contrastive_patterns
    """

    def _is_inside_dialogue(self, text: str, position: int) -> bool:
        """
        Detecta si una posición está dentro de un diálogo (entre comillas o guiones).

        Los atributos mencionados en diálogos no deben asignarse al hablante,
        ya que podrían referirse a otra persona.

        Ejemplos:
        - "Tenías los ojos verdes" -> dentro de diálogo
        - —Eras muy alta —dijo Juan. -> dentro de diálogo
        - - Pero tenías el pelo rubio... -> dentro de diálogo
        """
        # Buscar hacia atrás para encontrar inicio de diálogo
        before = text[:position]

        # Contar comillas y guiones de diálogo
        # Español usa: «», "", '', —, -

        # Comillas españolas «»
        open_spanish = before.count("«")
        close_spanish = before.count("»")
        if open_spanish > close_spanish:
            return True

        # Comillas dobles ""
        open_double = before.count('"')
        # Si número impar de comillas dobles, estamos dentro
        if open_double % 2 == 1:
            return True

        # Comillas inglesas ""
        open_curly = before.count("\u201c")
        close_curly = before.count("\u201d")
        if open_curly > close_curly:
            return True

        # Guiones de diálogo (— largo o - corto al inicio de línea)
        # Buscar el último inicio de línea con guión

        # Patrón: inicio de línea o después de punto/salto seguido de guión
        dialogue_start_pattern = re.compile(r"(?:^|\n)\s*[-—]")
        matches = list(dialogue_start_pattern.finditer(before))

        if matches:
            last_dialogue_start = matches[-1].end()
            between = before[last_dialogue_start:]

            # Verificar si hay un cierre de diálogo
            # El diálogo termina con: otro guión, salto de línea, o verbo de habla
            speech_verbs = [
                "dijo",
                "preguntó",
                "contestó",
                "respondió",
                "exclamó",
                "murmuró",
                "gritó",
                "susurró",
                "añadió",
                "comentó",
            ]
            has_speech_verb = any(verb in between.lower() for verb in speech_verbs)
            has_closing_dash = bool(re.search(r"\s[-—]\s", between))
            has_newline = "\n" in between

            # Si no hay indicador de fin de diálogo, estamos dentro
            if not has_speech_verb and not has_closing_dash and not has_newline:
                return True

            # Caso especial: "- texto - dijo X - más texto"
            # Si hay verbo de habla pero después sigue el diálogo
            if has_speech_verb:
                # Buscar si hay otro guión después del verbo de habla
                verb_match = None
                for verb in speech_verbs:
                    verb_pos = between.lower().find(verb)
                    if verb_pos != -1:
                        verb_match = verb_pos
                        break
                if verb_match is not None:
                    after_verb = between[verb_match:]
                    # Si hay otro guión después del verbo, el texto posterior está en diálogo
                    if re.search(r"\s[-—]\s", after_verb):
                        # La posición está después de ese segundo guión?
                        second_dash = re.search(r"\s[-—]\s", after_verb)
                        if second_dash:
                            return True

        return False

    def _is_metaphor(
        self, context: str, match_text: str = "", match_pos_in_context: int = 0
    ) -> bool:
        """
        Detecta si el contexto sugiere una metáfora.

        Args:
            context: Texto de contexto alrededor del match
            match_text: Texto que hizo match (para verificar si la metáfora lo afecta)
            match_pos_in_context: Posición del match dentro del contexto

        Returns:
            True si es probable que sea una metáfora
        """
        for pattern in self._metaphor_patterns:  # type: ignore[attr-defined]
            # Buscar TODAS las ocurrencias del patrón de metáfora en el contexto
            for metaphor_match in pattern.finditer(context):
                metaphor_pos = metaphor_match.start()
                metaphor_end = metaphor_match.end()

                # Si no tenemos info del match, cualquier metáfora cuenta
                if not match_text or match_pos_in_context < 0:
                    return True

                match_end_in_context = match_pos_in_context + len(match_text)

                # Caso 1: Metáfora está ANTES del match
                if metaphor_end <= match_pos_in_context:
                    between = context[metaphor_end:match_pos_in_context]
                    # Si hay puntuación entre la metáfora y el match, no afecta
                    if "," in between or "." in between or ";" in between or "\n" in between:
                        continue
                    # Si hay más de 20 caracteres, probablemente no afecta
                    if len(between.strip()) > 20:
                        continue
                    return True

                # Caso 2: Metáfora está DENTRO del match
                elif metaphor_pos >= match_pos_in_context and metaphor_end <= match_end_in_context:
                    return True

                # Caso 3: Metáfora está DESPUÉS del match
                elif metaphor_pos >= match_end_in_context:
                    between = context[match_end_in_context:metaphor_pos]
                    # Si hay puntuación entre el match y la metáfora, no afecta
                    if "," in between or "." in between or ";" in between or "\n" in between:
                        continue
                    # Si hay más de 20 caracteres, probablemente no afecta
                    if len(between.strip()) > 20:
                        continue
                    return True

        return False

    def _is_negated(self, context: str, match_pos: int) -> bool:
        """
        Detecta si el atributo está negado.

        Maneja:
        - Negación simple: "no era alto", "nunca tuvo pelo negro"
        - Negación parcial: "no es que X, sino Y" (X está negado)

        Args:
            context: Contexto alrededor del match
            match_pos: Posición del match en el contexto

        Returns:
            True si el atributo está negado
        """
        # Solo buscar en el contexto antes del match
        before_context = context[:match_pos]

        # Buscar negación simple cercana (últimos 30 caracteres)
        return any(pattern.search(before_context[-30:]) for pattern in self._negation_patterns)  # type: ignore[attr-defined]

    def _is_temporal_past(self, context: str, match_pos: int) -> bool:
        """
        Detecta si el atributo se refiere al pasado (no al estado actual).

        Ejemplo: "De joven, Eva tenía pelo negro" → atributo pasado
        """
        before_context = context[:match_pos]

        return any(pattern.search(before_context[-60:]) for pattern in self._temporal_past_patterns)  # type: ignore[attr-defined]

    def _is_conditional(self, context: str, match_pos: int) -> bool:
        """
        Detecta si el atributo es hipotético/condicional (no real).

        Ejemplo: "Si Oscar se tiñera, sería pelirrojo" → no es pelirrojo realmente
        """
        before_context = context[:match_pos]

        return any(pattern.search(before_context[-50:]) for pattern in self._conditional_patterns)  # type: ignore[attr-defined]

    def _check_contrastive_correction(
        self, context: str, match_start: int, match_end: int, value: str
    ) -> tuple[bool, str | None]:
        """
        Detecta patrón contrastivo "No es X, sino Y" y extrae el valor correcto.

        Ejemplo: "No es que Pedro tuviera ojos azules, sino grises"
        → El valor "azules" está negado, "grises" es el correcto.

        Args:
            context: Contexto alrededor del match
            match_start: Inicio del match en el contexto
            match_end: Fin del match en el contexto
            value: Valor extraído actual

        Returns:
            (is_contrastive, corrected_value) - Si es contrastivo y el valor corregido
        """
        from .attributes import COLORS

        # Buscar patrón "no es que... sino" o "no era/tenía... sino"
        for pattern in self._contrastive_patterns:  # type: ignore[attr-defined]
            match = pattern.search(context)
            if match:
                # Verificar si nuestro valor está ANTES del "sino"
                sino_pos = context.lower().find("sino", match.start())
                if sino_pos > 0 and match_start < sino_pos:
                    # El valor actual está en la parte negada
                    # Buscar el valor después del "sino"
                    after_sino = context[sino_pos + 4:].strip()
                    # Extraer la primera palabra después de "sino" como posible corrección
                    color_match = re.search(r"\b([a-záéíóú]+)\b", after_sino)
                    if color_match:
                        corrected = color_match.group(1).lower()
                        # Verificar que sea un color válido
                        if corrected in COLORS:
                            return True, corrected
                    return True, None  # Es contrastivo pero no pudimos extraer corrección

        return False, None

    def _is_inside_relative_clause(
        self, text: str, entity_start: int, entity_end: int, attribute_pos: int
    ) -> bool:
        """
        Detecta si una entidad está dentro de una cláusula relativa.

        Usa dos estrategias:
        1. Dep-tree (preferido): ScopeResolver con spans de RC del árbol de dependencias
        2. Regex fallback: patrones de pronombres relativos + cierre de cláusula

        Ejemplo: "El hombre que María había visto tenía ojos azules."
        → "María" está dentro de "que María había visto" (cláusula relativa)
        → El atributo "ojos azules" pertenece a "El hombre", NO a María

        Args:
            text: Texto completo
            entity_start: Posición inicial de la entidad
            entity_end: Posición final de la entidad
            attribute_pos: Posición del atributo

        Returns:
            True si la entidad está dentro de una cláusula relativa
        """
        # La entidad está ANTES del atributo (ya filtrado en el caller)
        if entity_end > attribute_pos:
            return False

        # Estrategia 1: Dep-tree (ScopeResolver cacheado)
        resolver = getattr(self, "_scope_resolver", None)
        if resolver is not None:
            try:
                ent_in_rc, _ = resolver.is_in_relative_clause(entity_start)
                attr_in_rc, _ = resolver.is_in_relative_clause(attribute_pos)
                if ent_in_rc and not attr_in_rc:
                    logger.debug(
                        f"Entidad en cláusula relativa (dep-tree): "
                        f"'{text[entity_start:entity_end]}'"
                    )
                    return True
                if not ent_in_rc:
                    return False  # Dep-tree es confiable: si dice que no está, confiar
            except Exception as e:
                logger.debug(f"RC detection via dep-tree failed: {e}")

        # Estrategia 2: Regex fallback (cuando no hay dep-tree disponible)
        search_start = max(0, entity_start - 30)
        before_entity = text[search_start:entity_start]

        relative_patterns = [
            r"\bque\s*$",  # "...que María"
            r"\bquien(?:es)?\s*$",  # "...quien María"
            r"\bel\s+cual\s*$",  # "el cual María"
            r"\bla\s+cual\s*$",
            r"\bcuy[oa]s?\s*$",  # "cuyo hermano"
            r"\bdonde\s*$",  # "donde María"
            r"\bcuando\s*$",  # "cuando María"
        ]

        for pattern in relative_patterns:
            if re.search(pattern, before_entity, re.IGNORECASE):
                between = text[entity_end:attribute_pos]
                clause_closure = re.search(
                    r"\b(?:había|hubo|hizo|fue|vio|conoció|dijo)\s+\w+\s+(?:tenía|era|estaba|llevaba|mostraba)\b",
                    between,
                    re.IGNORECASE,
                )
                if clause_closure:
                    logger.debug(
                        f"Entidad en cláusula relativa (regex): '{text[entity_start:entity_end]}'"
                    )
                    return True

        return False
