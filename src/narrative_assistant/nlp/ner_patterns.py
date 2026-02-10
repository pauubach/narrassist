"""
Mixin de deteccion de patrones para NERExtractor.

Contiene los metodos que detectan patrones de titulo+nombre,
lugares compuestos y personas compuestas con particulas.

Este modulo se separa de ner.py para reducir el tamano del archivo
principal y mejorar la mantenibilidad. La clase NERPatternDetectorMixin
se usa como mixin de NERExtractor.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ner import EntityLabel, ExtractedEntity

logger = logging.getLogger(__name__)


class NERPatternDetectorMixin:
    """
    Mixin con metodos de deteccion de patrones de entidades NER.

    Detecta patrones como titulo+nombre ("doctor Ramirez"),
    lugares compuestos ("Monte Olimpo") y personas compuestas
    con particulas ("Garcia de la Vega").

    Se usa como mixin de NERExtractor.
    """

    # ==========================================================================
    # Patrones de titulo + nombre (generalizable)
    # ==========================================================================

    # Titulos profesionales/militares que preceden a un apellido
    # Formato: "titulo Apellido" -> entidad PER
    PROFESSIONAL_TITLES = {
        # Medicos/Sanitarios
        "doctor",
        "doctora",
        "dr",
        "dra",
        # Militares
        "coronel",
        "general",
        "capitan",
        "capitán",
        "teniente",
        "sargento",
        "almirante",
        "comandante",
        "mayor",
        # Policiales/Judiciales
        "inspector",
        "inspectora",
        "comisario",
        "comisaria",
        "juez",
        "jueza",
        "fiscal",
        "subinspector",
        "subinspectora",
        # Religiosos
        "fray",
        "sor",
        "padre",
        "madre",
        "hermano",
        "hermana",
        "rabino",
        "rabina",
        "iman",
        "imán",
        # Academicos
        "profesor",
        "profesora",
        "catedratico",
        "catedrático",
        "catedratica",
        # Nobiliarios/Formales
        "conde",
        "condesa",
        "duque",
        "duquesa",
        "marques",
        "marqués",
        "marquesa",
        "baron",
        "barón",
        "baronesa",
        "sultan",
        "sultán",
        "sultana",
        "rey",
        "reina",
        "principe",
        "príncipe",
        "princesa",
    }

    # Prefijos de lugares compuestos
    # Formato: "prefijo Nombre" -> entidad LOC
    LOCATION_PREFIXES = {
        # Geograficos
        "monte",
        "sierra",
        "cordillera",
        "volcan",
        "volcán",
        "valle",
        "canon",
        "cañón",
        "desfiladero",
        "rio",
        "río",
        "lago",
        "laguna",
        "mar",
        "oceano",
        "océano",
        "isla",
        "peninsula",
        "península",
        "cabo",
        "bahia",
        "bahía",
        "desierto",
        "bosque",
        "selva",
        "pradera",
        "llanura",
        # Urbanos
        "plaza",
        "calle",
        "avenida",
        "paseo",
        "parque",
        "barrio",
        "colonia",
        "urbanizacion",
        "urbanización",
        "puerto",
        "aeropuerto",
        "estacion",
        "estación",
        # Construcciones
        "palacio",
        "castillo",
        "torre",
        "fortaleza",
        "muralla",
        "catedral",
        "iglesia",
        "monasterio",
        "convento",
        "hospital",
        "universidad",
        "instituto",
        "colegio",
        "base",
        "campo",
        "campamento",
        # Politicos
        "imperio",
        "reino",
        "republica",
        "república",
        "provincia",
        "region",
        "región",
        "departamento",
    }

    # Apellidos comunes en espanol para deteccion de particulas
    _COMMON_SURNAMES = {
        "garcia",
        "martinez",
        "lopez",
        "fernandez",
        "rodriguez",
        "perez",
        "sanchez",
        "romero",
        "navarro",
        "gonzalez",
        "diaz",
        "hernandez",
        "moreno",
        "muñoz",
        "alvarez",
        "jimenez",
        "ruiz",
        "torres",
        "dominguez",
        "ramos",
        "vazquez",
        "castillo",
        "serrano",
        "ortiz",
        "marin",
        "vega",
        "fuente",
        "cruz",
        "molina",
        "blanco",
        "delgado",
        "ortega",
        "castro",
        "guerrero",
        "medina",
        "flores",
        "campos",
        "herrera",
        "leon",
        "reyes",
        # Variantes con tilde
        "garcía",
        "martínez",
        "lópez",
        "fernández",
        "rodríguez",
        "pérez",
        "sánchez",
        "gonzález",
        "díaz",
        "hernández",
        "álvarez",
        "jiménez",
        "vázquez",
        "domínguez",
        "marín",
    }

    def _detect_title_name_patterns(
        self,
        doc,
        full_text: str,
        already_found: set[tuple[int, int]],
        existing_entities: list[ExtractedEntity],
    ) -> list[ExtractedEntity]:
        """
        Detecta patrones de titulo + nombre/apellido y EXTIENDE entidades existentes.

        Busca secuencias como "doctor Ramirez", "coronel Salgado", "fiscal Montero".
        Si encuentra un patron que CONTIENE una entidad ya detectada, extiende
        esa entidad para incluir el titulo.

        Este patron es GENERALIZABLE - no depende de nombres especificos,
        sino de la estructura titulo + palabra con mayuscula.

        Args:
            doc: Documento spaCy procesado
            full_text: Texto completo
            already_found: Posiciones ya detectadas (se modificara in-place)
            existing_entities: Entidades ya detectadas (se modificara in-place)

        Returns:
            Lista de NUEVAS entidades detectadas (que no extienden existentes)
        """
        import re

        from .ner import EntityLabel, ExtractedEntity

        new_entities = []

        # Buscar patron: titulo (case-insensitive) + Nombre (MUST start with uppercase)
        # Usamos (?-i:...) para hacer los nombres case-sensitive mientras el titulo es case-insensitive
        # Esto evita capturar palabras como "nos", "ha" que siguen al nombre
        title_pattern = (
            r"\b("
            + "|".join(re.escape(t) for t in self.PROFESSIONAL_TITLES)
            + r")\s+(?-i:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(?:\s+(?-i:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+))?\b"
        )

        for match in re.finditer(title_pattern, full_text, re.IGNORECASE):
            full_match = match.group(0)
            title = match.group(1)
            # name_part is extracted from full_match by removing the title
            # (no capture group needed - was causing "no such group" error)

            pattern_start = match.start()
            pattern_end = match.end()

            # Verificar que no esta ya detectada exactamente
            pos = (pattern_start, pattern_end)
            if pos in already_found:
                continue

            # Buscar si hay una entidad existente que este patron EXTIENDE
            # (es decir, el patron contiene la entidad existente)
            extended = False
            for i, ent in enumerate(existing_entities):
                # El patron debe contener la entidad existente
                # y el patron debe ser mas largo (incluye titulo)
                if (
                    ent.start_char >= pattern_start
                    and ent.end_char <= pattern_end
                    and pattern_end - pattern_start > ent.end_char - ent.start_char
                    and ent.label == EntityLabel.PER
                ):
                    # Extender la entidad existente
                    logger.debug(
                        f"Extendiendo entidad '{ent.text}' a '{full_match}' "
                        f"(añadiendo título '{title}')"
                    )

                    # Actualizar posiciones en already_found
                    old_pos = (ent.start_char, ent.end_char)
                    if old_pos in already_found:
                        already_found.discard(old_pos)
                    already_found.add(pos)

                    # Actualizar la entidad
                    existing_entities[i] = ExtractedEntity(
                        text=full_match,
                        label=EntityLabel.PER,
                        start_char=pattern_start,
                        end_char=pattern_end,
                        confidence=ent.confidence,  # Mantener confianza original
                        source=ent.source + "+title",
                    )
                    extended = True
                    break

            # Si no extendio ninguna entidad existente, verificar si es nueva
            if not extended:
                # Solo agregar si no hay solapamiento
                overlaps = False
                for s, e in already_found:
                    if not (pattern_end <= s or pattern_start >= e):
                        overlaps = True
                        break

                if not overlaps:
                    entity = ExtractedEntity(
                        text=full_match,
                        label=EntityLabel.PER,
                        start_char=pattern_start,
                        end_char=pattern_end,
                        confidence=0.75,
                        source="title_pattern",
                    )
                    new_entities.append(entity)
                    already_found.add(pos)
                    logger.debug(f"Nuevo patrón título+nombre detectado: '{full_match}'")

        return new_entities

    def _detect_compound_locations(
        self,
        doc,
        full_text: str,
        already_found: set[tuple[int, int]],
        existing_entities: list[ExtractedEntity],
    ) -> list[ExtractedEntity]:
        """
        Detecta lugares compuestos con prefijo geografico y EXTIENDE entidades existentes.

        Busca secuencias como "Monte Olimpo", "Valle Marineris", "Palacio de Cristal".
        Si encuentra un patron que CONTIENE una entidad LOC ya detectada, la extiende.

        Este patron es GENERALIZABLE - detecta cualquier prefijo geografico
        seguido de un nombre propio.

        Args:
            doc: Documento spaCy procesado
            full_text: Texto completo
            already_found: Posiciones ya detectadas (se modificara in-place)
            existing_entities: Entidades ya detectadas (se modificara in-place)

        Returns:
            Lista de NUEVAS entidades detectadas (que no extienden existentes)
        """
        import re

        from .ner import EntityLabel, ExtractedEntity

        new_entities = []

        # Patron 1: prefijo (case-insensitive) + Nombre (MUST start with uppercase)
        # Usamos (?-i:...) para hacer los nombres case-sensitive
        prefix_pattern = (
            r"\b("
            + "|".join(re.escape(p) for p in self.LOCATION_PREFIXES)
            + r")\s+(?-i:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(?:\s+(?-i:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+))?\b"
        )

        for match in re.finditer(prefix_pattern, full_text, re.IGNORECASE):
            full_match = match.group(0)
            prefix = match.group(1)

            pattern_start = match.start()
            pattern_end = match.end()

            pos = (pattern_start, pattern_end)
            if pos in already_found:
                continue

            # Buscar si extiende una entidad LOC existente
            extended = False
            for i, ent in enumerate(existing_entities):
                if (
                    ent.start_char >= pattern_start
                    and ent.end_char <= pattern_end
                    and pattern_end - pattern_start > ent.end_char - ent.start_char
                    and ent.label == EntityLabel.LOC
                ):
                    logger.debug(
                        f"Extendiendo ubicación '{ent.text}' a '{full_match}' "
                        f"(añadiendo prefijo '{prefix}')"
                    )

                    old_pos = (ent.start_char, ent.end_char)
                    if old_pos in already_found:
                        already_found.discard(old_pos)
                    already_found.add(pos)

                    existing_entities[i] = ExtractedEntity(
                        text=full_match,
                        label=EntityLabel.LOC,
                        start_char=pattern_start,
                        end_char=pattern_end,
                        confidence=ent.confidence,
                        source=ent.source + "+prefix",
                    )
                    extended = True
                    break

            if not extended:
                overlaps = False
                for s, e in already_found:
                    if not (pattern_end <= s or pattern_start >= e):
                        overlaps = True
                        break

                if not overlaps:
                    entity = ExtractedEntity(
                        text=full_match,
                        label=EntityLabel.LOC,
                        start_char=pattern_start,
                        end_char=pattern_end,
                        confidence=0.75,
                        source="location_pattern",
                    )
                    new_entities.append(entity)
                    already_found.add(pos)
                    logger.debug(f"Nuevo patrón lugar compuesto: '{full_match}'")

        # Patron 2: prefijo + de + Nombre (ej: "Palacio de Cristal")
        # NO usar IGNORECASE aqui - los nombres DEBEN empezar con mayuscula
        compound_pattern = r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+(de|del|de la|de los|de las)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)\b"

        for match in re.finditer(compound_pattern, full_text):
            first_word = match.group(1).lower()
            full_match = match.group(0)

            if first_word not in self.LOCATION_PREFIXES:
                continue

            pattern_start = match.start()
            pattern_end = match.end()

            pos = (pattern_start, pattern_end)
            if pos in already_found:
                continue

            # Buscar si extiende una entidad existente
            extended = False
            for i, ent in enumerate(existing_entities):
                if (
                    ent.start_char >= pattern_start
                    and ent.end_char <= pattern_end
                    and pattern_end - pattern_start > ent.end_char - ent.start_char
                    and ent.label == EntityLabel.LOC
                ):
                    old_pos = (ent.start_char, ent.end_char)
                    if old_pos in already_found:
                        already_found.discard(old_pos)
                    already_found.add(pos)

                    existing_entities[i] = ExtractedEntity(
                        text=full_match,
                        label=EntityLabel.LOC,
                        start_char=pattern_start,
                        end_char=pattern_end,
                        confidence=ent.confidence,
                        source=ent.source + "+compound",
                    )
                    extended = True
                    break

            if not extended:
                overlaps = False
                for s, e in already_found:
                    if not (pattern_end <= s or pattern_start >= e):
                        overlaps = True
                        break

                if not overlaps:
                    entity = ExtractedEntity(
                        text=full_match,
                        label=EntityLabel.LOC,
                        start_char=pattern_start,
                        end_char=pattern_end,
                        confidence=0.7,
                        source="location_pattern",
                    )
                    new_entities.append(entity)
                    already_found.add(pos)
                    logger.debug(f"Nuevo patrón lugar compuesto (de): '{full_match}'")

        return new_entities

    def _detect_compound_persons(
        self,
        doc,
        full_text: str,
        already_found: set[tuple[int, int]],
        existing_entities: list[ExtractedEntity],
    ) -> list[ExtractedEntity]:
        """
        Detecta nombres de personas compuestos con particulas (de, del, de la, etc.).

        Busca patrones como "Garcia de la Vega", "Lopez de Cordoba", "De la Fuente".
        Solo activa cuando al menos uno de los nombres es un PROPN reconocido por spaCy
        o un apellido conocido.

        Args:
            doc: Documento spaCy procesado
            full_text: Texto completo
            already_found: Posiciones ya detectadas
            existing_entities: Entidades ya detectadas

        Returns:
            Lista de NUEVAS entidades detectadas
        """
        import re

        from .ner import EntityLabel, ExtractedEntity

        new_entities = []

        # Patron: NombrePropio + particula + NombrePropio
        # Particulas: de, del, de la, de los, de las
        compound_pattern = (
            r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+"
            r"(de|del|de la|de los|de las)\s+"
            r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)\b"
        )

        for match in re.finditer(compound_pattern, full_text):
            first_word = match.group(1)
            match.group(2)
            last_part = match.group(3)
            full_match = match.group(0)

            first_lower = first_word.lower()
            last_part.split()[0].lower() if last_part else ""

            # Verificar que el PRIMER nombre sea un apellido o nombre propio.
            # El primer token DEBE ser un nombre/apellido, no un sustantivo
            # comun (evita FP con "Nacimiento de Ana", "Batalla de Madrid").
            first_is_surname = first_lower in self._COMMON_SURNAMES
            first_is_propn = False
            for token in doc:
                if token.text == first_word:
                    if token.pos_ == "PROPN" or token.ent_type_ == "PER":
                        first_is_propn = True
                    break  # Solo verificar el primer token

            if not (first_is_surname or first_is_propn):
                continue

            # Excluir si el primer nombre es un prefijo de lugar
            if first_lower in getattr(self, "LOCATION_PREFIXES", set()):
                continue

            pattern_start = match.start()
            pattern_end = match.end()
            pos = (pattern_start, pattern_end)

            if pos in already_found:
                continue

            # Verificar si extiende una entidad PER existente
            extended = False
            for i, ent in enumerate(existing_entities):
                if (
                    ent.start_char >= pattern_start
                    and ent.end_char <= pattern_end
                    and pattern_end - pattern_start > ent.end_char - ent.start_char
                    and ent.label == EntityLabel.PER
                ):
                    old_pos = (ent.start_char, ent.end_char)
                    if old_pos in already_found:
                        already_found.discard(old_pos)
                    already_found.add(pos)

                    existing_entities[i] = ExtractedEntity(
                        text=full_match,
                        label=EntityLabel.PER,
                        start_char=pattern_start,
                        end_char=pattern_end,
                        confidence=ent.confidence,
                        source=ent.source + "+compound_person",
                    )
                    extended = True
                    logger.debug(f"PER extendido con partícula: '{ent.text}' → '{full_match}'")
                    break

            if not extended:
                # Verificar que no solape con entidades existentes
                overlaps = False
                for s, e in already_found:
                    if not (pattern_end <= s or pattern_start >= e):
                        overlaps = True
                        break

                if not overlaps:
                    entity = ExtractedEntity(
                        text=full_match,
                        label=EntityLabel.PER,
                        start_char=pattern_start,
                        end_char=pattern_end,
                        confidence=0.7,
                        source="compound_person_pattern",
                    )
                    new_entities.append(entity)
                    already_found.add(pos)
                    logger.debug(f"Nuevo PER compuesto: '{full_match}'")

        return new_entities
