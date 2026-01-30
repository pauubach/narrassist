# -*- coding: utf-8 -*-
"""
Extractor basado en patrones regex de alta precisión.

Este extractor usa patrones regex cuidadosamente diseñados
para extraer atributos con ALTA PRECISIÓN (pero cobertura limitada).

Solo incluye patrones muy confiables (>85% precisión esperada).
"""

import re
import logging
from typing import Optional

from ..base import (
    BaseExtractor,
    ExtractionMethod,
    ExtractionContext,
    ExtractionResult,
    ExtractedAttribute,
    AttributeType,
)

logger = logging.getLogger(__name__)


class RegexExtractor(BaseExtractor):
    """
    Extractor de atributos usando patrones regex.

    Características:
    - Alta precisión (~90%) para patrones conocidos
    - Muy rápido (<10ms por texto típico)
    - Cobertura limitada (solo patrones explícitos)
    - Detecta metáforas y negaciones

    Example:
        >>> extractor = RegexExtractor()
        >>> context = ExtractionContext(
        ...     text="María tenía los ojos azules.",
        ...     entity_names=["María"]
        ... )
        >>> result = extractor.extract(context)
        >>> print(result.attributes[0].value)  # "azules"
    """

    # Patrones de alta confianza para color de ojos
    EYE_COLOR_PATTERNS = [
        # "tenía los ojos azules"
        (r'\b(?P<entity>\w+)\s+ten[ií]a\s+(?:los\s+)?ojos\s+(?P<value>\w+)', 0.9),
        # "sus ojos azules" (necesita contexto de entidad)
        (r'[Ss]us\s+ojos\s+(?P<value>azules?|verdes?|marr[oó]n(?:es)?|negros?|grises?)', 0.75),
        # "ojos de color azul"
        (r'ojos\s+de\s+color\s+(?P<value>\w+)', 0.85),
        # "los ojos azules de María"
        (r'los\s+ojos\s+(?P<value>\w+)\s+de\s+(?P<entity>\w+)', 0.9),
        # "María, de ojos azules"
        (r'(?P<entity>\w+),?\s+de\s+ojos\s+(?P<value>\w+)', 0.85),
    ]

    # Patrones para color de pelo
    HAIR_COLOR_PATTERNS = [
        # "tenía el cabello negro"
        (r'\b(?P<entity>\w+)\s+ten[ií]a\s+(?:el\s+)?(?:cabello|pelo)\s+(?P<value>negro|rubio|casta[ñn]o|pelirrojo|canoso|blanco|gris)', 0.9),
        # "su cabello negro"
        (r'[Ss]u\s+(?:cabello|pelo)\s+(?P<value>negro|rubio|casta[ñn]o|pelirrojo|canoso|blanco|gris)', 0.75),
        # "pelo de color castaño"
        (r'(?:cabello|pelo)\s+de\s+color\s+(?P<value>\w+)', 0.85),
        # "el cabello rubio de Juan"
        (r'(?:el\s+)?(?:cabello|pelo)\s+(?P<value>negro|rubio|casta[ñn]o|pelirrojo|canoso)\s+de\s+(?P<entity>\w+)', 0.9),
        # "cabello largo y negro" -> extrae "negro" (el color después de "y")
        (r'(?:cabello|pelo)\s+\w+\s+y\s+(?P<value>negro|rubio|casta[ñn]o|pelirrojo|canoso|blanco|gris)', 0.85),
        # "cabello negro y largo" -> extrae "negro" (el color antes de "y")
        (r'(?:cabello|pelo)\s+(?P<value>negro|rubio|casta[ñn]o|pelirrojo|canoso|blanco|gris)\s+y\s+\w+', 0.85),
        # "Llevaba el cabello corto y rubio"
        (r'[Ll]levaba\s+(?:el\s+)?(?:cabello|pelo)\s+\w+\s+y\s+(?P<value>negro|rubio|casta[ñn]o|pelirrojo|canoso)', 0.85),
        # "pelo rubio" simple (sin "y")
        (r'(?:cabello|pelo)\s+(?P<value>negro|rubio|casta[ñn]o|pelirrojo|canoso|blanco|gris)(?:\s|,|\.)', 0.80),
    ]

    # Patrones para tipo de pelo (largo, corto, etc.)
    HAIR_TYPE_PATTERNS = [
        # "cabello largo y negro" -> extrae "largo"
        (r'(?:cabello|pelo)\s+(?P<value>largo|corto|rizado|liso|ondulado)(?:\s+y\s+\w+)?', 0.85),
        # "llevaba el pelo recogido"
        (r'llevaba\s+(?:el\s+)?(?:cabello|pelo)\s+(?P<value>recogido|suelto|trenzado|rapado)', 0.85),
        # "tenía el pelo largo"
        (r'ten[ií]a\s+(?:el\s+)?(?:cabello|pelo)\s+(?P<value>largo|corto|rizado|liso)', 0.9),
        # "Llevaba el cabello corto y rubio" -> extrae "corto"
        (r'[Ll]levaba\s+(?:el\s+)?(?:cabello|pelo)\s+(?P<value>largo|corto|rizado|liso|ondulado)', 0.85),
        # "cabello negro y largo" -> extrae "largo" después de "y"
        (r'(?:cabello|pelo)\s+\w+\s+y\s+(?P<value>largo|corto|rizado|liso|ondulado)', 0.80),
        # "recogido en una trenza"
        (r'(?P<value>recogido|suelto|trenzado)\s+en\s+una?\s+\w+', 0.80),
    ]

    # Patrones para altura
    HEIGHT_PATTERNS = [
        # "era alto/alta"
        (r'(?P<entity>\w+)\s+era\s+(?:un\s+hombre\s+|una\s+mujer\s+)?(?P<value>muy\s+)?(?P<height>alt[oa]|baj[oa])', 0.9),
        # "un hombre alto"
        (r'(?:un|una)\s+(?:hombre|mujer)\s+(?P<value>alt[oa]|baj[oa])', 0.8),
        # "María, alta y delgada"
        (r'(?P<entity>\w+),?\s+(?P<value>alt[oa]|baj[oa])(?:\s+y\s+\w+)?', 0.75),
    ]

    # Patrones para complexión
    BUILD_PATTERNS = [
        # "era fornido/delgado"
        (r'(?P<entity>\w+)\s+era\s+(?:un\s+hombre\s+|una\s+mujer\s+)?(?P<value>fornid[oa]|delgad[oa]|robust[oa]|esbelt[oa])', 0.9),
        # "un hombre bajo y fornido"
        (r'(?:un|una)\s+(?:hombre|mujer)\s+\w+\s+y\s+(?P<value>fornid[oa]|delgad[oa]|robust[oa])', 0.85),
        # "de complexión robusta"
        (r'de\s+complexi[oó]n\s+(?P<value>\w+)', 0.9),
    ]

    # Patrones para edad
    AGE_PATTERNS = [
        # "tenía treinta años"
        (r'(?P<entity>\w+)\s+ten[ií]a\s+(?:aproximadamente\s+)?(?P<value>\w+)\s+a[ñn]os', 0.9),
        # "de unos treinta años"
        (r'de\s+(?:unos?\s+)?(?P<value>\w+)\s+a[ñn]os', 0.85),
        # "era joven/viejo"
        (r'(?P<entity>\w+)\s+era\s+(?P<value>joven|viej[oa]|ancian[oa]|mayor)', 0.85),
    ]

    # Patrones para profesión (genéricos por sufijo + estructura sintáctica)
    PROFESSION_PATTERNS = [
        # "el detective Ruiz", "la doctora Ana", "el profesor Martinez"
        (r'(?:[Ee]l|[Ll]a)\s+(?P<value>(?:\w+(?:ero|era|ista|or|ora|nte|dor|dora|tor|tora|ogo|oga|ario|aria|ivo|iva|ico|ica|ino|ina|ador|adora)))\s+(?P<entity>[A-ZÁÉÍÓÚÜÑ]\w+)', 0.90),
        # "Pedro, un joven carpintero" / "Ana, una gran detective"
        (r'(?P<entity>[A-ZÁÉÍÓÚÜÑ]\w+),\s+(?:un[oa]?\s+)?(?:\w+\s+)?(?P<value>\w+(?:ero|era|ista|or|ora|nte|dor|dora|tor|tora|ogo|oga|ario|aria|ivo|iva|ico|ica|ino|ina|ador|adora))\b', 0.80),
        # "trabajaba como carpintero" / "trabaja de detective"
        (r'trabaj(?:a|aba|ó)\s+(?:como|de)\s+(?P<value>\w+)', 0.85),
        # "era carpintero" / "es médico" (sin artículo)
        (r'(?P<entity>[A-ZÁÉÍÓÚÜÑ]\w+)\s+(?:era|es|fue|será)\s+(?:un[oa]?\s+)?(?P<value>(?:\w+(?:ero|era|ista|or|ora|nte|dor|dora|tor|tora|ogo|oga|ario|aria|ico|ica|ino|ina)))\b', 0.80),
        # "la bibliotecaria del pueblo" -> apposition with article
        (r'(?:[Ee]l|[Ll]a)\s+(?P<value>(?:\w+(?:ero|era|ista|or|ora|nte|dor|dora|tor|tora|ogo|oga|ario|aria|ivo|iva|ico|ica|ino|ina|ador|adora)))\s+(?:del?\s+\w+)', 0.75),
    ]

    # Palabras que coinciden con sufijos profesionales pero NO son profesiones
    PROFESSION_EXCLUSIONS = {
        "primero", "primera", "tercero", "tercera", "sincero", "sincera",
        "entero", "entera", "ligero", "ligera", "severo", "severa",
        "verdadero", "verdadera", "pasajero", "pasajera", "soltero", "soltera",
        "certero", "certera", "guerrero", "guerrera",
        "manera", "cantera", "madera", "ladera", "pradera", "carretera",
        "anterior", "exterior", "interior", "superior", "inferior", "posterior",
        "mejor", "peor", "mayor", "menor",
        "oscuro", "oscura", "claro", "clara",
    }

    # Indicadores de metáfora (para filtrar)
    METAPHOR_INDICATORS = [
        r'\bcomo\s+(?:el|la|un|una)\b',
        r'\bparec[ií]a\b',
        r'\bsemejante\s+a\b',
        r'\bbrillar\b',
        r'\breflejar\b',
    ]

    # Indicadores de negación
    NEGATION_INDICATORS = [
        r'\bno\s+ten[ií]a\b',
        r'\bsin\s+\b',
        r'\bnunca\b',
        r'\bjam[aá]s\b',
    ]

    def __init__(self):
        """Inicializa el extractor compilando patrones."""
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compila todos los patrones regex."""
        self._eye_patterns = [
            (re.compile(p, re.IGNORECASE), conf)
            for p, conf in self.EYE_COLOR_PATTERNS
        ]
        self._hair_color_patterns = [
            (re.compile(p, re.IGNORECASE), conf)
            for p, conf in self.HAIR_COLOR_PATTERNS
        ]
        self._hair_type_patterns = [
            (re.compile(p, re.IGNORECASE), conf)
            for p, conf in self.HAIR_TYPE_PATTERNS
        ]
        self._height_patterns = [
            (re.compile(p, re.IGNORECASE), conf)
            for p, conf in self.HEIGHT_PATTERNS
        ]
        self._build_patterns = [
            (re.compile(p, re.IGNORECASE), conf)
            for p, conf in self.BUILD_PATTERNS
        ]
        self._age_patterns = [
            (re.compile(p, re.IGNORECASE), conf)
            for p, conf in self.AGE_PATTERNS
        ]
        self._profession_patterns = [
            (re.compile(p, re.UNICODE), conf)
            for p, conf in self.PROFESSION_PATTERNS
        ]

        self._metaphor_re = [
            re.compile(p, re.IGNORECASE) for p in self.METAPHOR_INDICATORS
        ]
        self._negation_re = [
            re.compile(p, re.IGNORECASE) for p in self.NEGATION_INDICATORS
        ]

    @property
    def method(self) -> ExtractionMethod:
        return ExtractionMethod.REGEX

    @property
    def supported_attributes(self) -> set[AttributeType]:
        return {
            AttributeType.EYE_COLOR,
            AttributeType.HAIR_COLOR,
            AttributeType.HAIR_TYPE,
            AttributeType.HEIGHT,
            AttributeType.BUILD,
            AttributeType.AGE,
            AttributeType.PROFESSION,
        }

    def can_handle(self, context: ExtractionContext) -> float:
        """
        Regex es mejor para textos cortos y simples.
        """
        word_count = len(context.text.split())

        # Muy confiable para textos cortos
        if word_count < 50:
            return 0.9

        # Menos confiable para textos largos/complejos
        if word_count > 200:
            return 0.6

        return 0.75

    def extract(self, context: ExtractionContext) -> ExtractionResult:
        """
        Extrae atributos usando patrones regex.

        Args:
            context: Contexto con texto y entidades

        Returns:
            ExtractionResult con atributos encontrados
        """
        attributes = []
        errors = []

        # Normalizar nombres de entidades para búsqueda
        entity_names_lower = {name.lower() for name in context.entity_names}
        entity_names_list = context.entity_names  # Lista original para búsqueda posicional

        try:
            # Extraer cada tipo de atributo
            attributes.extend(
                self._extract_with_patterns(
                    context.text,
                    self._eye_patterns,
                    AttributeType.EYE_COLOR,
                    entity_names_lower,
                    entity_names_list,
                    context.chapter,
                )
            )

            attributes.extend(
                self._extract_with_patterns(
                    context.text,
                    self._hair_color_patterns,
                    AttributeType.HAIR_COLOR,
                    entity_names_lower,
                    entity_names_list,
                    context.chapter,
                )
            )

            attributes.extend(
                self._extract_with_patterns(
                    context.text,
                    self._hair_type_patterns,
                    AttributeType.HAIR_TYPE,
                    entity_names_lower,
                    entity_names_list,
                    context.chapter,
                )
            )

            attributes.extend(
                self._extract_with_patterns(
                    context.text,
                    self._height_patterns,
                    AttributeType.HEIGHT,
                    entity_names_lower,
                    entity_names_list,
                    context.chapter,
                )
            )

            attributes.extend(
                self._extract_with_patterns(
                    context.text,
                    self._build_patterns,
                    AttributeType.BUILD,
                    entity_names_lower,
                    entity_names_list,
                    context.chapter,
                )
            )

            attributes.extend(
                self._extract_with_patterns(
                    context.text,
                    self._age_patterns,
                    AttributeType.AGE,
                    entity_names_lower,
                    entity_names_list,
                    context.chapter,
                )
            )

            attributes.extend(
                self._extract_professions(
                    context.text,
                    entity_names_lower,
                    entity_names_list,
                    context.chapter,
                )
            )

            # Separar atributos compuestos
            attributes = self._separate_compound_attributes(attributes)

            # Deduplicar
            attributes = self._deduplicate(attributes)

            logger.debug(f"RegexExtractor found {len(attributes)} attributes")

        except Exception as e:
            errors.append(f"Error in regex extraction: {str(e)}")
            logger.exception("Error in regex extraction")

        return self._create_result(attributes, errors)

    def _extract_with_patterns(
        self,
        text: str,
        patterns: list[tuple[re.Pattern, float]],
        attr_type: AttributeType,
        entity_names: set[str],
        entity_names_list: list[str],
        chapter: Optional[int],
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos usando una lista de patrones.

        Args:
            text: Texto a analizar
            patterns: Lista de (patrón regex compilado, confianza base)
            attr_type: Tipo de atributo a extraer
            entity_names: Set de nombres de entidades (lowercase) para búsqueda rápida
            entity_names_list: Lista de nombres originales para _find_nearest_entity
            chapter: Número de capítulo

        Returns:
            Lista de atributos extraídos
        """
        attributes = []

        for pattern, base_confidence in patterns:
            for match in pattern.finditer(text):
                # Obtener valor
                try:
                    value = match.group("value")
                except IndexError:
                    continue

                if not value:
                    continue

                # Obtener entidad (del patrón o buscar la más cercana)
                try:
                    entity = match.group("entity")
                except IndexError:
                    entity = None

                # Si no hay entidad en el patrón, buscar la más cercana al match
                if not entity or entity.lower() not in entity_names:
                    entity = self._find_nearest_entity(
                        text, match.start(), entity_names_list
                    )

                if not entity:
                    continue

                # Verificar que la entidad existe en nuestro contexto
                if entity.lower() not in entity_names:
                    # Buscar coincidencia parcial
                    matched_entity = None
                    for name in entity_names:
                        if entity.lower() in name or name in entity.lower():
                            matched_entity = name
                            break
                    if matched_entity:
                        entity = matched_entity
                    else:
                        continue

                # Obtener contexto para verificar metáforas/negaciones
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 20)
                context_text = text[start:end]

                # Detectar metáforas
                is_metaphor = any(p.search(context_text) for p in self._metaphor_re)

                # Detectar negaciones
                is_negated = any(p.search(context_text) for p in self._negation_re)

                # Filtrar atributos negados - no representan el estado real
                if is_negated:
                    continue

                # Ajustar confianza
                confidence = base_confidence
                if is_metaphor:
                    confidence *= 0.5  # Reducir confianza para metáforas

                # Combinar "muy" con el valor si existe
                try:
                    muy = match.group("height")
                    if muy and match.group("value"):
                        value = f"{match.group('value')} {muy}".strip()
                except IndexError:
                    pass

                attributes.append(self._create_attribute(
                    entity_name=entity,
                    attr_type=attr_type,
                    value=value.strip(),
                    confidence=confidence,
                    source_text=match.group(0),
                    chapter=chapter,
                    is_negated=is_negated,
                    is_metaphor=is_metaphor,
                ))

        return attributes

    def _extract_professions(
        self,
        text: str,
        entity_names: set[str],
        entity_names_list: list[str],
        chapter: Optional[int],
    ) -> list[ExtractedAttribute]:
        """
        Extrae profesiones usando patrones de sufijo + estructura sintáctica.

        Detecta profesiones genéricamente por sufijos productivos del español:
        -ero/a, -ista, -or/a, -nte, -dor/a, -ico/a, -ario/a, -ogo/a, etc.
        """
        attributes = []

        for pattern, base_confidence in self._profession_patterns:
            for match in pattern.finditer(text):
                try:
                    value = match.group("value")
                except IndexError:
                    continue

                if not value or len(value) < 4:
                    continue

                # Filtrar exclusiones (palabras que coinciden con sufijos pero no son profesiones)
                if value.lower() in self.PROFESSION_EXCLUSIONS:
                    continue

                # Obtener entidad del patrón o buscar la más cercana
                try:
                    entity = match.group("entity")
                except IndexError:
                    entity = None

                if not entity or entity.lower() not in entity_names:
                    entity = self._find_nearest_entity(
                        text, match.start(), entity_names_list
                    )

                if not entity:
                    continue

                # Verificar que la entidad existe en nuestro contexto
                if entity.lower() not in entity_names:
                    matched_entity = None
                    for name in entity_names:
                        if entity.lower() in name or name in entity.lower():
                            matched_entity = name
                            break
                    if matched_entity:
                        entity = matched_entity
                    else:
                        continue

                attributes.append(self._create_attribute(
                    entity_name=entity,
                    attr_type=AttributeType.PROFESSION,
                    value=value.strip(),
                    confidence=base_confidence,
                    source_text=match.group(0),
                    chapter=chapter,
                ))

        return attributes

    def _find_last_entity(
        self,
        text: str,
        entity_names: list[str],
    ) -> Optional[str]:
        """
        Encuentra la primera entidad mencionada en el texto.

        Para patrones globales sin contexto de posición,
        retorna la primera entidad del texto (generalmente el protagonista).
        """
        first_entity = None
        first_pos = len(text)

        text_lower = text.lower()
        for name in entity_names:
            pos = text_lower.find(name.lower())
            if pos != -1 and pos < first_pos:
                first_pos = pos
                first_entity = name

        return first_entity

    def _find_nearest_entity(
        self,
        text: str,
        match_pos: int,
        entity_names: list[str],
        window_size: int = 200,
    ) -> Optional[str]:
        """
        Encuentra la entidad más cercana a una posición en el texto.

        Busca hacia atrás desde la posición del match para encontrar
        la entidad más cercana que probablemente sea el sujeto.

        Soporta coincidencias parciales: si el texto dice "María" y
        la lista tiene "María Sánchez", encontrará la coincidencia.

        Args:
            text: Texto completo
            match_pos: Posición del match del atributo
            entity_names: Nombres de entidades conocidas
            window_size: Tamaño de la ventana de búsqueda hacia atrás

        Returns:
            Nombre de la entidad más cercana o None
        """
        # Buscar en una ventana antes del match
        start_pos = max(0, match_pos - window_size)
        search_text = text[start_pos:match_pos].lower()

        nearest_entity = None
        nearest_pos = -1

        # Primero buscar nombres completos
        for name in entity_names:
            pos = search_text.rfind(name.lower())
            if pos > nearest_pos:
                nearest_pos = pos
                nearest_entity = name

        # Si no encontramos nombre completo, buscar coincidencias parciales
        # (primer nombre, apellido, o cualquier parte del nombre)
        if nearest_entity is None:
            for name in entity_names:
                # Dividir el nombre en partes (ej: "María Sánchez" -> ["María", "Sánchez"])
                name_parts = name.split()
                for part in name_parts:
                    if len(part) < 2:  # Ignorar iniciales muy cortas
                        continue
                    # Buscar cada parte como palabra completa
                    part_lower = part.lower()
                    # Usar regex para buscar palabra completa
                    pattern = r'\b' + re.escape(part_lower) + r'\b'
                    matches = list(re.finditer(pattern, search_text))
                    if matches:
                        # Tomar la última ocurrencia
                        last_match = matches[-1]
                        if last_match.start() > nearest_pos:
                            nearest_pos = last_match.start()
                            nearest_entity = name

        return nearest_entity

    def _separate_compound_attributes(
        self,
        attributes: list[ExtractedAttribute],
    ) -> list[ExtractedAttribute]:
        """
        Separa atributos compuestos como "largo y negro" en dos atributos.
        """
        result = []

        # Clasificadores para separación
        hair_colors = {"negro", "rubio", "castaño", "pelirrojo", "canoso", "gris", "blanco", "oscuro", "claro"}
        hair_types = {"largo", "corto", "rizado", "liso", "ondulado", "recogido", "suelto"}
        heights = {"alto", "alta", "bajo", "baja"}
        builds = {"fornido", "fornida", "delgado", "delgada", "robusto", "robusta", "esbelto", "esbelta"}

        for attr in attributes:
            # Buscar patrón "X y Y"
            match = re.search(r'(\w+)\s+y\s+(\w+)', attr.value, re.IGNORECASE)

            if match:
                val1 = match.group(1).lower()
                val2 = match.group(2).lower()

                # Determinar tipos
                type1 = self._classify_adjective(val1, hair_colors, hair_types, heights, builds)
                type2 = self._classify_adjective(val2, hair_colors, hair_types, heights, builds)

                if type1 != type2 and type1 and type2:
                    # Separar en dos atributos
                    result.append(self._create_attribute(
                        entity_name=attr.entity_name,
                        attr_type=type1,
                        value=val1,
                        confidence=attr.confidence * 0.95,
                        source_text=attr.source_text,
                        chapter=attr.chapter,
                        is_negated=attr.is_negated,
                    ))
                    result.append(self._create_attribute(
                        entity_name=attr.entity_name,
                        attr_type=type2,
                        value=val2,
                        confidence=attr.confidence * 0.95,
                        source_text=attr.source_text,
                        chapter=attr.chapter,
                        is_negated=attr.is_negated,
                    ))
                else:
                    # Mantener original si son del mismo tipo
                    result.append(attr)
            else:
                result.append(attr)

        return result

    def _classify_adjective(
        self,
        adj: str,
        hair_colors: set[str],
        hair_types: set[str],
        heights: set[str],
        builds: set[str],
    ) -> Optional[AttributeType]:
        """Clasifica un adjetivo en su tipo de atributo."""
        adj = adj.lower()

        if adj in hair_colors:
            return AttributeType.HAIR_COLOR
        if adj in hair_types:
            return AttributeType.HAIR_TYPE
        if adj in heights:
            return AttributeType.HEIGHT
        if adj in builds:
            return AttributeType.BUILD

        return None

    def _deduplicate(
        self,
        attributes: list[ExtractedAttribute],
    ) -> list[ExtractedAttribute]:
        """
        Elimina atributos duplicados, manteniendo el de mayor confianza.
        """
        seen: dict[tuple, ExtractedAttribute] = {}

        for attr in attributes:
            key = (
                attr.entity_name.lower(),
                attr.attribute_type,
                attr.value.lower(),
            )

            if key not in seen or attr.confidence > seen[key].confidence:
                seen[key] = attr

        return list(seen.values())
