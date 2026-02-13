"""
Extractor de marcadores temporales.

Detecta referencias temporales en texto narrativo usando múltiples métodos:

1. **Patrones regex**: Para expresiones comunes y bien definidas
2. **Análisis NLP (spaCy)**: Para detectar entidades temporales (DATE, TIME)
3. **Análisis de dependencias**: Para expresiones temporales complejas

Tipos detectados:
- Fechas absolutas ("15 de marzo de 1985")
- Referencias relativas ("tres días después", "al día siguiente")
- Estaciones/épocas ("aquel verano")
- Edades de personajes ("cuando tenía 20 años")
- Duraciones ("durante tres meses")
- Frecuencias ("cada martes")
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Intentar importar spaCy para análisis NLP
try:
    import spacy
    from spacy.tokens import Doc

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.debug("spaCy no disponible, usando solo patrones regex")


class MarkerType(Enum):
    """Tipos de marcadores temporales."""

    ABSOLUTE_DATE = "absolute_date"
    RELATIVE_TIME = "relative_time"
    SEASON_EPOCH = "season_epoch"
    CHARACTER_AGE = "character_age"
    DURATION = "duration"
    FREQUENCY = "frequency"


@dataclass
class TemporalMarker:
    """
    Marcador temporal extraído del texto.

    Attributes:
        text: Texto original del marcador
        marker_type: Tipo de marcador temporal
        start_char: Posición inicial en el texto
        end_char: Posición final en el texto
        chapter: Número de capítulo (opcional)
        paragraph: Número de párrafo (opcional)
        direction: Dirección temporal ('past', 'future') para marcadores relativos
        magnitude: Unidad temporal ('día', 'mes', 'año')
        quantity: Cantidad numérica
        entity_id: ID de entidad asociada (para edades)
        age: Edad detectada
        age_phase: Fase de vida detectada cuando no hay edad numérica ("joven", "viejo", etc.)
        relative_year_offset: Desfase relativo de años para instancias implícitas (+5, -3)
        confidence: Nivel de confianza (0-1)
    """

    text: str
    marker_type: MarkerType
    start_char: int
    end_char: int
    chapter: int | None = None
    paragraph: int | None = None
    # Para marcadores relativos
    direction: str | None = None  # 'past', 'future'
    magnitude: str | None = None  # 'día', 'mes', 'año'
    quantity: int | None = None
    # Para edades
    entity_id: int | None = None
    age: int | None = None
    age_phase: str | None = None
    relative_year_offset: int | None = None
    # Instancia temporal (ej. "12@age:40", "12@year:1985")
    # Se popula cuando hay suficiente evidencia (entidad + marcador temporal).
    temporal_instance_id: str | None = None
    # Metadata adicional
    year: int | None = None
    month: int | None = None
    day: int | None = None
    # Confianza
    confidence: float = 1.0


# Conversión de palabras a números
WORD_TO_NUM = {
    "un": 1,
    "una": 1,
    "uno": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "veinte": 20,
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
    "algunos": 3,  # Aproximación
    "varios": 3,
    "pocos": 2,
    "muchos": 10,
}

# Normalización de fases vitales para construir instancias temporales estables
# cuando el texto no da una edad numérica explícita.
AGE_PHASE_ALIASES = {
    "niño": "child",
    "niña": "child",
    "pequeño": "child",
    "pequeña": "child",
    "adolescente": "teen",
    "joven": "young",
    "adulto": "adult",
    "adulta": "adult",
    "mayor": "elder",
    "viejo": "elder",
    "vieja": "elder",
    "infancia": "child",
    "niñez": "child",
    "juventud": "young",
    "adolescencia": "teen",
    "madurez": "adult",
    "vejez": "elder",
}

# Fases para desdobles temporales explícitos ("yo del futuro/pasado").
TEMPORAL_SELF_PHASE_ALIASES = {
    "futuro": "future_self",
    "pasado": "past_self",
}

# Meses en español
MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

# Patrones de extracción con nivel de confianza
TEMPORAL_PATTERNS: dict[MarkerType, list[tuple[str, float]]] = {
    MarkerType.ABSOLUTE_DATE: [
        # "15 de marzo de 1985"
        (
            r"\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})\b",
            0.95,
        ),
        # "marzo de 1985"
        (
            r"\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})\b",
            0.9,
        ),
        # "el año 1985"
        (r"\bel\s+año\s+(\d{4})\b", 0.95),
        # "en 1985" (año suelto con contexto)
        (r"\ben\s+(19\d{2}|20[0-2]\d)\b", 0.85),
        # Año suelto (menos confianza)
        (r"\b(19\d{2}|20[0-2]\d)\b", 0.6),
    ],
    MarkerType.RELATIVE_TIME: [
        # "X días/semanas/meses/años después/antes"
        (
            r"\b(\d+|un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\s+(días?|semanas?|meses?|años?)\s+(después|antes|más\s+tarde|atrás)\b",
            0.9,
        ),
        # "Una semana después" (inicio de oración, con mayúscula)
        (
            r"\b(Una?)\s+(semana|día|mes|año)\s+(después|antes|más\s+tarde)\b",
            0.9,
        ),
        # "al día siguiente", "la noche anterior"
        (
            r"\b(al\s+día\s+siguiente|la\s+noche\s+anterior|la\s+mañana\s+siguiente|el\s+día\s+anterior|a\s+la\s+mañana\s+siguiente)\b",
            0.95,
        ),
        # "aquella noche", "esa mañana", "aquella mañana de martes"
        (
            r"\b(aquel|aquella|ese|esa)\s+(noche|mañana|tarde|día)(\s+de\s+(lunes|martes|miércoles|jueves|viernes|sábado|domingo))?\b",
            0.8,
        ),
        # "aquella mañana de martes" (captura día de la semana con contexto temporal)
        (
            r"\b(aquel|aquella|ese|esa)\s+(lunes|martes|miércoles|jueves|viernes|sábado|domingo)\b",
            0.8,
        ),
        # "más tarde", "poco después"
        (
            r"\b(más\s+tarde|poco\s+después|mucho\s+después|tiempo\s+después|horas\s+después|minutos\s+después)\b",
            0.85,
        ),
        # "al cabo de X días"
        (
            r"\bal\s+cabo\s+de\s+(\d+|un|una|dos|tres|algunos|varios)\s+(días?|semanas?|meses?|años?)\b",
            0.9,
        ),
        # "mañana de martes", "noche del viernes" (sin demostrativo)
        (
            r"\b(la\s+)?(mañana|noche|tarde)\s+del?\s+(lunes|martes|miércoles|jueves|viernes|sábado|domingo)\b",
            0.75,
        ),
        # "al rato", "al instante", "al momento"
        (r"\bal\s+(rato|instante|momento|poco\s+rato)\b", 0.8),
        # "pasados unos/algunos días"
        (
            r"\bpasad[oa]s?\s+(unos?|algunos?|varios?|pocos?)\s+(días?|semanas?|meses?|años?|horas?)\b",
            0.9,
        ),
        # "transcurrido un tiempo", "transcurridas unas horas"
        (
            r"\btranscurrid[oa]s?\s+(un|una|unos|unas|algunos?|varios?|pocos?)\s+(tiempo|días?|semanas?|meses?|años?|horas?)\b",
            0.9,
        ),
        # "con el paso de los días/años"
        (
            r"\bcon\s+el\s+paso\s+de\s+(los\s+)?(días|años|meses|semanas|tiempo)\b",
            0.85,
        ),
        # "a las pocas horas/semanas"
        (
            r"\ba\s+las?\s+(pocas?|dos|tres|cuatro|cinco)\s+(horas?|días?|semanas?|meses?)\b",
            0.85,
        ),
    ],
    MarkerType.SEASON_EPOCH: [
        # "aquel verano", "ese invierno"
        (
            r"\b(aquel|aquella|ese|esa|el|la)\s+(verano|invierno|otoño|primavera)\b",
            0.9,
        ),
        # "durante la guerra"
        (
            r"\bdurante\s+(la\s+guerra|la\s+posguerra|la\s+República|el\s+franquismo|la\s+dictadura|la\s+transición)\b",
            0.85,
        ),
        # "en los años 80"
        (r"\ben\s+los\s+años\s+(\d{2})\b", 0.9),
        # "a principios/mediados/finales de"
        (
            r"\ba\s+(principios|mediados|finales)\s+de\s+(siglo|año|mes|década)\b",
            0.85,
        ),
        # "en la época de"
        (r"\ben\s+la\s+época\s+de\b", 0.7),
    ],
    MarkerType.CHARACTER_AGE: [
        # "cuando tenía X años"
        (r"\bcuando\s+ten[íi]a\s+(\d{1,3})\s+años\b", 0.9),
        # "a los X años"
        (r"\ba\s+los\s+(\d{1,3})\s+años\b", 0.85),
        # "con X años"
        (r"\bcon\s+(\d{1,3})\s+años\b", 0.85),
        # "X años cumplidos"
        (r"\b(\d{1,3})\s+años\s+cumplidos\b", 0.9),
        # "tenía X años"
        (r"\bten[íi]a\s+(\d{1,3})\s+años\b", 0.85),
        # "cumplió X años"
        (r"\bcumpli[óo]\s+(\d{1,3})\s+años\b", 0.9),
    ],
    MarkerType.DURATION: [
        # "durante X días/meses/años"
        (
            r"\bdurante\s+(\d+|un|una|dos|tres|algunos?|varios?|muchos?)\s+(días?|semanas?|meses?|años?|horas?)\b",
            0.9,
        ),
        # "por X tiempo"
        (r"\bpor\s+(\d+|un|una|largo|corto|mucho|poco)\s+(tiempo|rato|momento)\b", 0.8),
        # "a lo largo de X"
        (
            r"\ba\s+lo\s+largo\s+de\s+(\d+|varios|muchos|algunos)\s+(días?|semanas?|meses?|años?)\b",
            0.85,
        ),
    ],
    MarkerType.FREQUENCY: [
        # "cada día", "todas las noches"
        (
            r"\b(cada|todos?\s+los?|todas?\s+las?)\s+(día|noche|mañana|tarde|semana|mes|año|lunes|martes|miércoles|jueves|viernes|sábado|domingo)s?\b",
            0.9,
        ),
        # "siempre", "nunca"
        (
            r"\b(siempre|nunca|jamás|a\s+veces|a\s+menudo|frecuentemente|raramente|ocasionalmente)\b",
            0.85,
        ),
        # "de vez en cuando"
        (r"\bde\s+vez\s+en\s+cuando\b", 0.9),
    ],
}

# ============================================================================
# S3-05: Patrones HeidelTime para español
# ============================================================================
# Patrones adicionales inspirados en HeidelTime (Strötgen & Gertz, 2010).
# HeidelTime es Java-based; aquí implementamos sus patrones clave en Python.

HEIDELTIME_PATTERNS: dict[MarkerType, list[tuple[str, float]]] = {
    MarkerType.ABSOLUTE_DATE: [
        # "lunes, 5 de enero" (día de la semana + fecha)
        (
            r"\b(lunes|martes|miércoles|jueves|viernes|sábado|domingo),?\s+(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b",
            0.95,
        ),
        # "5/1/1990", "05-01-1990" (formato numérico)
        (r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", 0.85),
        # "siglo XX", "siglo XIX", "siglo XV"
        (r"\bsiglo\s+([IVXLCDM]+)\b", 0.9),
        # "los años cincuenta", "los años sesenta"
        (
            r"\blos\s+años\s+(veinte|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa)\b",
            0.9,
        ),
    ],
    MarkerType.RELATIVE_TIME: [
        # "hace X días/meses/años"
        (
            r"\bhace\s+(\d+|un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|pocos|varios|algunos|muchos)\s+(días?|semanas?|meses?|años?|horas?|minutos?)\b",
            0.9,
        ),
        # "desde hace X"
        (
            r"\bdesde\s+hace\s+(\d+|un|una|dos|tres|cuatro|cinco|varios|algunos)\s+(días?|semanas?|meses?|años?|horas?)\b",
            0.9,
        ),
        # "dentro de X días"
        (
            r"\bdentro\s+de\s+(\d+|un|una|dos|tres|pocos|algunos)\s+(días?|semanas?|meses?|años?|horas?)\b",
            0.9,
        ),
        # "la víspera", "anteanoche", "anteayer", "pasado mañana"
        (
            r"\b(la\s+víspera|anteanoche|anteayer|pasado\s+mañana|antes\s+de\s+ayer)\b",
            0.95,
        ),
        # "al anochecer", "al amanecer", "al mediodía", "a medianoche"
        (
            r"\b(al\s+anochecer|al\s+amanecer|al\s+mediodía|a\s+medianoche|al\s+atardecer|al\s+alba)\b",
            0.85,
        ),
        # "en aquel entonces", "por aquel entonces", "en ese momento"
        (
            r"\b(en\s+aquel\s+entonces|por\s+aquel\s+entonces|en\s+ese\s+momento|en\s+aquel\s+momento|por\s+entonces)\b",
            0.8,
        ),
        # "acto seguido", "a continuación", "a renglón seguido"
        (
            r"\b(acto\s+seguido|a\s+continuación|a\s+renglón\s+seguido|inmediatamente\s+después)\b",
            0.85,
        ),
        # "la semana pasada", "el mes que viene", "el año anterior"
        (
            r"\b(la\s+semana|el\s+mes|el\s+año|el\s+día|la\s+noche)\s+(pasad[oa]|anterior|siguiente|que\s+viene|próxim[oa])\b",
            0.9,
        ),
    ],
    MarkerType.SEASON_EPOCH: [
        # Festividades y eventos culturales
        (
            r"\b(Navidad|Nochebuena|Nochevieja|Año\s+Nuevo|Reyes|Semana\s+Santa|Todos\s+los\s+Santos|San\s+Valentín|San\s+Juan|Carnaval|Corpus\s+Christi)\b",
            0.9,
        ),
        # "en tiempos de", "en la época de"
        (
            r"\ben\s+(tiempos|época|la\s+era|la\s+época)\s+de\s+[A-Z]",
            0.8,
        ),
        # "antes de la guerra", "después de la revolución"
        (
            r"\b(antes|después|durante|tras|al\s+final)\s+de\s+la\s+(guerra|revolución|reconquista|cruzada|reforma|independencia|restauración|república)\b",
            0.85,
        ),
        # "en plena", "en pleno" (intensificador temporal)
        (
            r"\ben\s+plen[oa]\s+(guerra|verano|invierno|noche|día|madrugada|tormenta|batalla)\b",
            0.8,
        ),
    ],
    MarkerType.CHARACTER_AGE: [
        # "de joven", "de niño", "de mayor", "de viejo"
        (r"\bde\s+(joven|niño|niña|mayor|viejo|vieja|pequeño|pequeña|adolescente|adulto|adulta)\b", 0.8),
        # "siendo joven/niño/mayor"
        (r"\bsiendo\s+(joven|niño|niña|mayor|viejo|vieja|adolescente|adulto|adulta)\b", 0.8),
        # "en su juventud/niñez/vejez"
        (r"\ben\s+su\s+(juventud|niñez|infancia|adolescencia|vejez|madurez)\b", 0.85),
        # "a la edad de X años"
        (r"\ba\s+la\s+edad\s+de\s+(\d{1,3})\s+años\b", 0.95),
        # "recién cumplidos los X"
        (r"\brecién\s+cumplid[oa]s?\s+(los\s+)?(\d{1,3})\b", 0.9),
    ],
    MarkerType.DURATION: [
        # "desde X hasta Y"
        (
            r"\bdesde\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|\d{4})\s+hasta\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|\d{4})\b",
            0.9,
        ),
        # "entre X y Y" (años)
        (r"\bentre\s+(\d{4})\s+y\s+(\d{4})\b", 0.9),
        # "a lo largo de su vida", "toda su vida", "de por vida"
        (r"\b(a\s+lo\s+largo\s+de\s+su\s+vida|toda\s+su\s+vida|de\s+por\s+vida)\b", 0.85),
        # "en cuestión de minutos/horas"
        (
            r"\ben\s+cuestión\s+de\s+(minutos|horas|días|semanas|meses|segundos)\b",
            0.85,
        ),
    ],
}

# Merge HeidelTime patterns into main TEMPORAL_PATTERNS
for marker_type, patterns in HEIDELTIME_PATTERNS.items():
    if marker_type in TEMPORAL_PATTERNS:
        TEMPORAL_PATTERNS[marker_type].extend(patterns)
    else:
        TEMPORAL_PATTERNS[marker_type] = patterns


class TemporalMarkerExtractor:
    """
    Extractor de marcadores temporales de texto narrativo.

    Usa múltiples métodos:
    1. Patrones regex (siempre activo)
    2. NLP con spaCy (si está disponible) para entidades DATE/TIME
    3. Análisis de dependencias para expresiones complejas

    Ejemplo de uso:
        extractor = TemporalMarkerExtractor()
        markers = extractor.extract(text, chapter=1)
    """

    # Palabras clave temporales para detección NLP
    TEMPORAL_KEYWORDS = {
        "después",
        "antes",
        "siguiente",
        "anterior",
        "pasado",
        "futuro",
        "ayer",
        "hoy",
        "mañana",
        "anoche",
        "ahora",
        "entonces",
        "luego",
        "pronto",
        "tarde",
        "temprano",
        "siempre",
        "nunca",
        "jamás",
        "mientras",
        "cuando",
        "hasta",
        "desde",
        "durante",
    }

    # Palabras que indican tiempo relativo
    RELATIVE_INDICATORS = {
        "después",
        "antes",
        "siguiente",
        "anterior",
        "más tarde",
        "atrás",
        "pasado",
        "último",
        "próximo",
        "al cabo",
    }

    def __init__(self, use_nlp: bool = True):
        """
        Inicializa el extractor.

        Args:
            use_nlp: Si True, usa spaCy para detección adicional (si está disponible)
        """
        self.patterns: dict[MarkerType, list[tuple[re.Pattern, float]]] = {}
        for marker_type, pattern_list in TEMPORAL_PATTERNS.items():
            self.patterns[marker_type] = [
                (re.compile(pattern, re.IGNORECASE), confidence)
                for pattern, confidence in pattern_list
            ]

        # Cargar modelo spaCy si está disponible y se solicita
        self.nlp = None
        self.use_nlp = use_nlp and SPACY_AVAILABLE
        if self.use_nlp:
            try:
                from narrative_assistant.nlp.spacy_gpu import load_spacy_model

                self.nlp = load_spacy_model()
                logger.debug("spaCy cargado para extracción temporal")
            except Exception as e:
                logger.debug(f"No se pudo cargar spaCy: {e}")
                self.nlp = None
                self.use_nlp = False

    def extract(
        self,
        text: str,
        chapter: int | None = None,
    ) -> list[TemporalMarker]:
        """
        Extrae todos los marcadores temporales del texto.

        Combina múltiples métodos:
        1. Patrones regex para expresiones conocidas
        2. Entidades NER de spaCy (DATE, TIME) si disponible
        3. Análisis de dependencias para expresiones complejas

        Args:
            text: Texto a analizar
            chapter: Número de capítulo (opcional)

        Returns:
            Lista de marcadores temporales ordenados por posición
        """
        markers: list[TemporalMarker] = []
        seen_spans: set[tuple[int, int]] = set()  # Evitar duplicados

        # 1. Extracción con patrones regex (método principal)
        for marker_type, pattern_list in self.patterns.items():
            for pattern, confidence in pattern_list:
                for match in pattern.finditer(text):
                    span = (match.start(), match.end())

                    # Evitar extraer el mismo span múltiples veces
                    if span in seen_spans:
                        continue

                    # Verificar que no se solape con un span ya extraído
                    overlaps = any(self._spans_overlap(span, existing) for existing in seen_spans)
                    if overlaps:
                        continue

                    seen_spans.add(span)

                    marker = self._create_marker(match, marker_type, confidence, chapter)
                    markers.append(marker)

        # 2. Extracción con NLP (spaCy) si está disponible
        if self.nlp and self.use_nlp:
            nlp_markers = self._extract_with_nlp(text, chapter, seen_spans)
            markers.extend(nlp_markers)
            for m in nlp_markers:
                seen_spans.add((m.start_char, m.end_char))

        # Ordenar por posición
        markers.sort(key=lambda m: m.start_char)
        logger.debug(f"Extracted {len(markers)} temporal markers from text")

        return markers

    def _spans_overlap(self, span1: tuple[int, int], span2: tuple[int, int]) -> bool:
        """Verifica si dos spans se solapan."""
        return not (span1[1] <= span2[0] or span2[1] <= span1[0])

    def _extract_with_nlp(
        self,
        text: str,
        chapter: int | None,
        seen_spans: set[tuple[int, int]],
    ) -> list[TemporalMarker]:
        """
        Extrae marcadores temporales usando análisis NLP con spaCy.

        Detecta:
        - Entidades DATE y TIME del NER
        - Expresiones temporales basadas en dependencias sintácticas
        - Adverbios temporales en contexto

        Args:
            text: Texto a analizar
            chapter: Número de capítulo
            seen_spans: Spans ya detectados (para evitar duplicados)

        Returns:
            Lista de marcadores adicionales detectados
        """
        if not self.nlp:
            return []

        markers: list[TemporalMarker] = []

        try:
            doc = self.nlp(text)

            # 1. Extraer entidades temporales del NER (DATE, TIME)
            for ent in doc.ents:
                if ent.label_ in ("DATE", "TIME"):
                    span = (ent.start_char, ent.end_char)

                    # Verificar que no se solape con spans existentes
                    if span in seen_spans:
                        continue
                    overlaps = any(self._spans_overlap(span, existing) for existing in seen_spans)
                    if overlaps:
                        continue

                    # Determinar tipo de marcador
                    marker_type = self._classify_temporal_entity(ent.text)

                    marker = TemporalMarker(
                        text=ent.text,
                        marker_type=marker_type,
                        start_char=ent.start_char,
                        end_char=ent.end_char,
                        chapter=chapter,
                        confidence=0.75,  # NER tiene buena confianza
                    )

                    # Parsear información adicional
                    if marker_type == MarkerType.RELATIVE_TIME:
                        marker = self._infer_relative_info(marker, doc, ent)

                    markers.append(marker)

            # 2. Buscar expresiones temporales por dependencias sintácticas
            for token in doc:
                # Buscar adverbios temporales modificando verbos
                if token.pos_ == "ADV" and token.head.pos_ == "VERB":
                    if token.text.lower() in self.TEMPORAL_KEYWORDS:
                        span = (token.idx, token.idx + len(token.text))

                        if span in seen_spans:
                            continue
                        overlaps = any(
                            self._spans_overlap(span, existing) for existing in seen_spans
                        )
                        if overlaps:
                            continue

                        # Expandir para incluir contexto (ej: "poco después")
                        expanded_text, expanded_start, expanded_end = self._expand_temporal_phrase(
                            doc, token
                        )
                        span = (expanded_start, expanded_end)

                        if span in seen_spans:
                            continue

                        markers.append(
                            TemporalMarker(
                                text=expanded_text,
                                marker_type=MarkerType.RELATIVE_TIME,
                                start_char=expanded_start,
                                end_char=expanded_end,
                                chapter=chapter,
                                confidence=0.65,
                            )
                        )

        except Exception as e:
            logger.debug(f"Error en extracción NLP temporal: {e}")

        return markers

    def _classify_temporal_entity(self, text: str) -> MarkerType:
        """Clasifica el tipo de marcador basado en el texto de la entidad."""
        text_lower = text.lower()

        # Detectar fechas absolutas
        if re.search(r"\d{4}", text_lower):  # Contiene año
            return MarkerType.ABSOLUTE_DATE
        if any(month in text_lower for month in MONTHS):
            return MarkerType.ABSOLUTE_DATE

        # Detectar expresiones relativas
        if any(ind in text_lower for ind in self.RELATIVE_INDICATORS):
            return MarkerType.RELATIVE_TIME

        # Detectar estaciones
        if any(s in text_lower for s in ["verano", "invierno", "otoño", "primavera"]):
            return MarkerType.SEASON_EPOCH

        # Por defecto, tratarlo como tiempo relativo
        return MarkerType.RELATIVE_TIME

    def _infer_relative_info(
        self,
        marker: TemporalMarker,
        doc: "Doc",
        ent,
    ) -> TemporalMarker:
        """Infiere información adicional para marcadores relativos."""
        text_lower = marker.text.lower()

        # Dirección
        if any(w in text_lower for w in ["después", "siguiente", "más tarde", "luego"]):
            marker.direction = "future"
        elif any(w in text_lower for w in ["antes", "anterior", "atrás", "pasado"]):
            marker.direction = "past"

        # Intentar detectar cantidad y magnitud
        for token in doc[ent.start : ent.end]:
            if token.like_num or token.text.lower() in WORD_TO_NUM:
                if token.text.isdigit():
                    marker.quantity = int(token.text)
                else:
                    marker.quantity = WORD_TO_NUM.get(token.text.lower())

            if token.text.lower() in [
                "día",
                "días",
                "semana",
                "semanas",
                "mes",
                "meses",
                "año",
                "años",
            ]:
                marker.magnitude = token.text.lower().rstrip("s")

        return marker

    def _expand_temporal_phrase(
        self,
        doc: "Doc",
        token,
    ) -> tuple[str, int, int]:
        """Expande un token temporal para incluir el contexto relevante."""
        start_idx = token.idx
        end_idx = token.idx + len(token.text)
        text = token.text

        # Buscar modificadores a la izquierda (ej: "poco" en "poco después")
        for child in token.children:
            if child.i < token.i and child.dep_ in ("advmod", "det"):
                start_idx = min(start_idx, child.idx)
                text = doc.text[start_idx:end_idx]

        # Buscar complementos a la derecha (ej: "de eso" en "después de eso")
        for child in token.children:
            if child.i > token.i and child.dep_ in ("prep", "pobj"):
                end_idx = max(end_idx, child.idx + len(child.text))
                text = doc.text[start_idx:end_idx]

        return text, start_idx, end_idx

    def _create_marker(
        self,
        match: re.Match,
        marker_type: MarkerType,
        confidence: float,
        chapter: int | None,
    ) -> TemporalMarker:
        """Crea un marcador con información extraída."""
        marker = TemporalMarker(
            text=match.group(0),
            marker_type=marker_type,
            start_char=match.start(),
            end_char=match.end(),
            chapter=chapter,
            confidence=confidence,
        )

        # Extraer información adicional según tipo
        if marker_type == MarkerType.RELATIVE_TIME:
            marker = self._parse_relative(marker, match)
        elif marker_type == MarkerType.CHARACTER_AGE:
            marker = self._parse_age(marker, match)
        elif marker_type == MarkerType.ABSOLUTE_DATE:
            marker = self._parse_absolute_date(marker, match)
        elif marker_type == MarkerType.DURATION:
            marker = self._parse_duration(marker, match)

        return marker

    def _parse_relative(
        self,
        marker: TemporalMarker,
        match: re.Match,
    ) -> TemporalMarker:
        """Parsea información de marcador relativo."""
        text_lower = marker.text.lower()

        # Dirección
        if any(w in text_lower for w in ["después", "siguiente", "más tarde", "al cabo", "dentro de"]):
            marker.direction = "future"
        elif any(w in text_lower for w in ["antes", "anterior", "atrás", "hace"]):
            marker.direction = "past"

        # Magnitud y cantidad
        groups = match.groups()
        if len(groups) >= 2:
            qty_str = groups[0].lower()
            marker.quantity = WORD_TO_NUM.get(qty_str) or (
                int(qty_str) if qty_str.isdigit() else None
            )
            # Normalizar magnitud a singular
            magnitude = groups[1].lower()
            marker.magnitude = magnitude.rstrip("s")
            if marker.magnitude == "semana":
                marker.magnitude = "semana"
            elif marker.magnitude == "me":
                marker.magnitude = "mes"

        # Inferir cantidad si no se detectó (para expresiones como "Una semana después")
        if marker.magnitude and not marker.quantity:
            # Si tiene magnitud pero no cantidad, probablemente es 1
            if "una" in text_lower or "un " in text_lower:
                marker.quantity = 1

        return marker

    def _parse_age(
        self,
        marker: TemporalMarker,
        match: re.Match,
    ) -> TemporalMarker:
        """Parsea información de edad."""
        groups = match.groups()
        if groups:
            # Hay patrones con múltiples grupos (p. ej. "(los )?(\\d{1,3})").
            # Buscamos el primer grupo numérico real en lugar de asumir groups[0].
            for group in groups:
                if group and group.isdigit():
                    marker.age = int(group)
                    break

            # Si no hay edad numérica explícita, intentamos inferir fase de vida.
            if marker.age is None:
                marker.age_phase = self._infer_age_phase(marker.text)

        return marker

    @staticmethod
    def _infer_age_phase(text: str) -> str | None:
        """Infiere fase vital canónica a partir del texto del marcador."""
        text_lower = text.lower()
        for alias, canonical_phase in AGE_PHASE_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", text_lower):
                return canonical_phase
        return None

    @staticmethod
    def _build_temporal_instance_id(marker: TemporalMarker) -> str | None:
        """
        Construye un identificador de instancia temporal estable.

        Formato:
        - edad: "<entity_id>@age:<n>"
        - fase: "<entity_id>@phase:<name>"
        - offset relativo: "<entity_id>@offset_years:+/-n"
        - año:  "<entity_id>@year:<yyyy>"
        """
        if marker.entity_id is None:
            return None
        if marker.age is not None:
            return f"{marker.entity_id}@age:{marker.age}"
        if marker.age_phase:
            # Justificación: para narrativas de viaje temporal con "yo joven/viejo",
            # necesitamos distinguir instancias aunque no exista edad numérica.
            return f"{marker.entity_id}@phase:{marker.age_phase}"
        if marker.relative_year_offset is not None:
            sign = "+" if marker.relative_year_offset >= 0 else ""
            return f"{marker.entity_id}@offset_years:{sign}{marker.relative_year_offset}"
        if marker.year is not None:
            return f"{marker.entity_id}@year:{marker.year}"
        return None

    @staticmethod
    def _distance_to_mention(
        marker_start: int,
        marker_end: int,
        mention_start: int,
        mention_end: int,
    ) -> int:
        """Distancia mínima entre un span de marcador y uno de mención."""
        if mention_end < marker_start:
            return marker_start - mention_end
        if mention_start > marker_end:
            return mention_start - marker_end
        return 0  # Solapan

    def _find_closest_entity_id(
        self,
        marker_start: int,
        marker_end: int,
        entity_mentions: list[tuple[int, int, int]],
        max_distance: int = 200,
    ) -> int | None:
        """
        Busca la entidad más cercana al marcador (antes o después).

        Justificación: cubre tanto "Juan, a los 40 años" como "a los 40 años, Juan".
        """
        closest_entity = None
        min_distance = float("inf")
        for entity_id, mention_start, mention_end in entity_mentions:
            distance = self._distance_to_mention(
                marker_start,
                marker_end,
                mention_start,
                mention_end,
            )
            if distance < min_distance and distance <= max_distance:
                min_distance = distance
                closest_entity = entity_id
        return closest_entity

    def _infer_implicit_markers_near_mentions(
        self,
        text: str,
        entity_mentions: list[tuple[int, int, int]],
        chapter: int | None,
        existing_markers: list[TemporalMarker],
    ) -> list[TemporalMarker]:
        """
        Genera marcadores de instancia temporal implícita alrededor de menciones.

        Heurísticas cubiertas:
        - Adjetivo de fase junto al nombre ("joven Juan", "viejo Juan")
        - Desdoble temporal explícito ("yo del futuro/pasado", "versión futura")
        - Desfase relativo ("dentro de 5 años", "5 años después/antes")
        """
        inferred: list[TemporalMarker] = []
        occupied_spans = [(m.start_char, m.end_char) for m in existing_markers]
        seen_signatures: set[tuple[int | None, str | None, int, int]] = set()

        def _add_marker(candidate: TemporalMarker) -> None:
            span = (candidate.start_char, candidate.end_char)
            if any(self._spans_overlap(span, used) for used in occupied_spans):
                return
            signature = (
                candidate.entity_id,
                candidate.temporal_instance_id,
                candidate.start_char,
                candidate.end_char,
            )
            if signature in seen_signatures:
                return
            seen_signatures.add(signature)
            inferred.append(candidate)
            occupied_spans.append(span)

        for entity_id, mention_start, mention_end in entity_mentions:
            if mention_end <= mention_start:
                continue

            # 1) Fase vital adyacente al nombre ("joven Juan", "viejo Juan").
            before_start = max(0, mention_start - 24)
            before_text = text[before_start:mention_start]
            phase_match = re.search(
                r"(niño|niña|pequeño|pequeña|adolescente|joven|adulto|adulta|mayor|viejo|vieja)\s*$",
                before_text,
                re.IGNORECASE,
            )
            if phase_match:
                phase_word = phase_match.group(1).lower()
                phase = AGE_PHASE_ALIASES.get(phase_word)
                if phase:
                    abs_start = before_start + phase_match.start(1)
                    abs_end = mention_end
                    marker = TemporalMarker(
                        text=text[abs_start:abs_end],
                        marker_type=MarkerType.CHARACTER_AGE,
                        start_char=abs_start,
                        end_char=abs_end,
                        chapter=chapter,
                        entity_id=entity_id,
                        age_phase=phase,
                        confidence=0.66,
                    )
                    marker.temporal_instance_id = self._build_temporal_instance_id(marker)
                    _add_marker(marker)

            # Ventana contextual alrededor de la mención para cues implícitos.
            window_start = max(0, mention_start - 64)
            window_end = min(len(text), mention_end + 140)
            window = text[window_start:window_end]

            # 2) Desdobles tipo "yo del futuro/pasado" o "versión futura/pasada".
            for pattern in (
                r"\b(?:yo|versi[oó]n|doble|copia)\s+del\s+(futuro|pasado)\b",
                r"\b(?:yo|versi[oó]n|doble|copia)\s+(futuro|pasado)\b",
            ):
                for match in re.finditer(pattern, window, re.IGNORECASE):
                    plane_word = match.group(1).lower()
                    phase = TEMPORAL_SELF_PHASE_ALIASES.get(plane_word)
                    if not phase:
                        continue
                    abs_start = window_start + match.start()
                    abs_end = window_start + match.end()
                    marker = TemporalMarker(
                        text=text[abs_start:abs_end],
                        marker_type=MarkerType.CHARACTER_AGE,
                        start_char=abs_start,
                        end_char=abs_end,
                        chapter=chapter,
                        entity_id=entity_id,
                        age_phase=phase,
                        confidence=0.62,
                    )
                    marker.temporal_instance_id = self._build_temporal_instance_id(marker)
                    _add_marker(marker)

            # 3) Instancias por desplazamiento relativo en años sin edad explícita.
            offset_patterns = (
                (r"\bdentro\s+de\s+(\d{1,3})\s+años\b", +1),
                (r"\b(\d{1,3})\s+años\s+(después|más\s+tarde)\b", +1),
                (r"\b(\d{1,3})\s+años\s+(antes|atrás)\b", -1),
                (r"\bhace\s+(\d{1,3})\s+años\b", -1),
            )
            for pattern, sign in offset_patterns:
                for match in re.finditer(pattern, window, re.IGNORECASE):
                    qty_str = match.group(1)
                    if not qty_str or not qty_str.isdigit():
                        continue
                    years = int(qty_str)
                    abs_start = window_start + match.start()
                    abs_end = window_start + match.end()
                    marker = TemporalMarker(
                        text=text[abs_start:abs_end],
                        marker_type=MarkerType.CHARACTER_AGE,
                        start_char=abs_start,
                        end_char=abs_end,
                        chapter=chapter,
                        entity_id=entity_id,
                        relative_year_offset=sign * years,
                        direction="future" if sign > 0 else "past",
                        quantity=years,
                        magnitude="año",
                        confidence=0.60,
                    )
                    marker.temporal_instance_id = self._build_temporal_instance_id(marker)
                    _add_marker(marker)

        return inferred

    def _parse_absolute_date(
        self,
        marker: TemporalMarker,
        match: re.Match,
    ) -> TemporalMarker:
        """Parsea información de fecha absoluta."""
        text_lower = marker.text.lower()

        # Intentar extraer componentes de fecha
        # Patrón completo: "15 de marzo de 1985"
        full_match = re.search(
            r"(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})",
            text_lower,
        )
        if full_match:
            marker.day = int(full_match.group(1))
            marker.month = MONTHS.get(full_match.group(2))
            marker.year = int(full_match.group(3))
            return marker

        # Patrón mes-año: "marzo de 1985"
        month_year_match = re.search(
            r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})",
            text_lower,
        )
        if month_year_match:
            marker.month = MONTHS.get(month_year_match.group(1))
            marker.year = int(month_year_match.group(2))
            return marker

        # Solo año
        year_match = re.search(r"\b(19\d{2}|20[0-2]\d)\b", text_lower)
        if year_match:
            marker.year = int(year_match.group(1))

        return marker

    def _parse_duration(
        self,
        marker: TemporalMarker,
        match: re.Match,
    ) -> TemporalMarker:
        """Parsea información de duración."""
        groups = match.groups()
        if len(groups) >= 2:
            qty_str = groups[0].lower()
            marker.quantity = WORD_TO_NUM.get(qty_str) or (
                int(qty_str) if qty_str.isdigit() else None
            )
            marker.magnitude = groups[1].lower().rstrip("s")

        return marker

    def extract_with_entities(
        self,
        text: str,
        entity_mentions: list[tuple[int, int, int]],  # (entity_id, start, end)
        chapter: int | None = None,
    ) -> list[TemporalMarker]:
        """
        Extrae marcadores y los asocia con entidades cercanas.

        Args:
            text: Texto a analizar
            entity_mentions: Lista de menciones de entidades (entity_id, start, end)
            chapter: Número de capítulo

        Returns:
            Lista de marcadores con entidades asociadas
        """
        markers = self.extract(text, chapter)

        # Asociar edades con entidades (soporta mención antes o después del marcador).
        for marker in markers:
            if marker.marker_type == MarkerType.CHARACTER_AGE:
                marker.entity_id = self._find_closest_entity_id(
                    marker.start_char,
                    marker.end_char,
                    entity_mentions,
                )
                # Justificación: sin entity_id no podemos distinguir "A@40" de "B@40".
                # La instancia temporal debe anclarse al ID canónico de la entidad.
                marker.temporal_instance_id = self._build_temporal_instance_id(marker)
            elif marker.marker_type == MarkerType.RELATIVE_TIME:
                # Heurística: ciertos relativos en años también identifican instancia
                # ("dentro de 5 años", "hace 3 años", "5 años después").
                # Los tratamos como offset relativo cuando hay entidad cercana.
                marker.entity_id = self._find_closest_entity_id(
                    marker.start_char,
                    marker.end_char,
                    entity_mentions,
                )
                if marker.entity_id and marker.magnitude == "año" and marker.quantity:
                    sign = -1 if marker.direction == "past" else 1
                    marker.relative_year_offset = sign * marker.quantity
                    marker.temporal_instance_id = self._build_temporal_instance_id(marker)

        # Heurística adicional para instancias implícitas sin edad explícita.
        implicit_markers = self._infer_implicit_markers_near_mentions(
            text=text,
            entity_mentions=entity_mentions,
            chapter=chapter,
            existing_markers=markers,
        )
        if implicit_markers:
            markers.extend(implicit_markers)
            markers = sorted(markers, key=lambda m: (m.start_char, m.end_char))

        return markers

    def get_markers_by_type(
        self,
        markers: list[TemporalMarker],
        marker_type: MarkerType,
    ) -> list[TemporalMarker]:
        """Filtra marcadores por tipo."""
        return [m for m in markers if m.marker_type == marker_type]

    def get_markers_by_chapter(
        self,
        markers: list[TemporalMarker],
        chapter: int,
    ) -> list[TemporalMarker]:
        """Filtra marcadores por capítulo."""
        return [m for m in markers if m.chapter == chapter]
