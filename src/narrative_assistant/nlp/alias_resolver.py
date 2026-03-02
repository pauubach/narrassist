"""
Sistema Genérico de Resolución de Alias.

Este módulo resuelve referencias indirectas a entidades en textos narrativos:
- Motes/apodos: "el Magistral" → "Fermín de Pas"
- Títulos: "don Fermín", "el canónigo" → "Fermín de Pas"
- Oficios/roles: "el doctor", "el cura" → nombre propio
- Relaciones familiares: "su madre", "el padre" → nombre si hay contexto
- Seudónimos literarios: "Clarín" → "Leopoldo Alas"

El sistema es genérico y no depende de listas cerradas:
1. Detecta patrones lingüísticos de alias (artículo + título/oficio)
2. Usa contexto narrativo para resolución
3. Aplica LLM para casos complejos
4. Mantiene coherencia con el sistema de correferencias

Referencias lingüísticas:
- Títulos honoríficos españoles: don/doña, señor/señora, fray, sor
- Títulos profesionales: doctor, licenciado, maestro, profesor
- Títulos eclesiásticos: padre, monseñor, obispo, canónigo, magistral
- Títulos nobiliarios: conde, duque, marqués, barón
- Títulos militares: general, coronel, capitán, teniente
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Enums y Constantes
# =============================================================================


class AliasType(Enum):
    """Tipo de alias detectado."""

    NICKNAME = "nickname"  # Mote/apodo: "el Gordo", "la Regenta"
    HONORIFIC_TITLE = "honorific"  # Don/doña, señor/señora
    PROFESSIONAL = "professional"  # Doctor, maestro, licenciado
    ECCLESIASTIC = "ecclesiastic"  # Padre, fray, canónigo, obispo
    NOBLE = "noble"  # Conde, duque, marqués
    MILITARY = "military"  # General, coronel, capitán
    FAMILY = "family"  # Padre, madre, hermano (en contexto)
    ROLE = "role"  # El protagonista, el narrador
    PSEUDONYM = "pseudonym"  # Seudónimo literario/artístico
    DESCRIPTIVE = "descriptive"  # "el hombre alto", "la mujer del vestido rojo"


# =============================================================================
# Patrones de Alias (Genéricos, no listas cerradas)
# =============================================================================

# Artículos que preceden títulos/apodos
ALIAS_ARTICLES = {"el", "la", "los", "las"}

# Títulos honoríficos (sin artículo)
HONORIFIC_PATTERNS = {
    # Tratamientos de respeto
    r"^don\s+\w+",
    r"^doña\s+\w+",
    r"^señor\s+\w+",
    r"^señora\s+\w+",
    r"^señorita\s+\w+",
    # Abreviaturas
    r"^sr\.?\s+\w+",
    r"^sra\.?\s+\w+",
    r"^srta\.?\s+\w+",
    r"^d\.?\s+\w+",
    r"^dña\.?\s+\w+",
}

# Patrones de títulos profesionales
PROFESSIONAL_TITLES = {
    "doctor",
    "doctora",
    "dr",
    "dra",
    "licenciado",
    "licenciada",
    "lic",
    "ingeniero",
    "ingeniera",
    "ing",
    "arquitecto",
    "arquitecta",
    "arq",
    "maestro",
    "maestra",
    "profesor",
    "profesora",
    "prof",
    "abogado",
    "abogada",
}

# Patrones de títulos eclesiásticos
ECCLESIASTIC_TITLES = {
    "padre",
    "fray",
    "sor",
    "monseñor",
    "obispo",
    "arzobispo",
    "cardenal",
    "canónigo",
    "magistral",
    "prior",
    "priora",
    "abad",
    "abadesa",
    "párroco",
    "vicario",
    "deán",
    "hermano",
    "hermana",  # religioso/a
}

# Patrones de títulos nobiliarios
NOBLE_TITLES = {
    "rey",
    "reina",
    "príncipe",
    "princesa",
    "infante",
    "infanta",
    "duque",
    "duquesa",
    "marqués",
    "marquesa",
    "conde",
    "condesa",
    "vizconde",
    "vizcondesa",
    "barón",
    "baronesa",
    "lord",
    "lady",
    "sir",
}

# Patrones de títulos militares
MILITARY_TITLES = {
    "general",
    "coronel",
    "comandante",
    "capitán",
    "capitana",
    "teniente",
    "alférez",
    "sargento",
    "cabo",
    "soldado",
    "almirante",
    "vicealmirante",
}

# Relaciones familiares (requieren contexto para resolución)
FAMILY_RELATIONS = {
    "padre",
    "madre",
    "papá",
    "mamá",
    "hijo",
    "hija",
    "niño",
    "niña",
    "hermano",
    "hermana",
    "abuelo",
    "abuela",
    "tío",
    "tía",
    "tio",
    "tia",
    "primo",
    "prima",
    "sobrino",
    "sobrina",
    "nieto",
    "nieta",
    "esposo",
    "esposa",
    "marido",
    "mujer",
    "novio",
    "novia",
    "suegro",
    "suegra",
    "cuñado",
    "cuñada",
    "yerno",
    "nuera",
}

# Todos los títulos combinados para detección rápida
ALL_TITLES = PROFESSIONAL_TITLES | ECCLESIASTIC_TITLES | NOBLE_TITLES | MILITARY_TITLES

# Determinantes y conectores para descriptores nominales
ALIAS_DETERMINERS = {
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    "su",
    "sus",
    "mi",
    "mis",
    "tu",
    "tus",
    "nuestro",
    "nuestra",
    "nuestros",
    "nuestras",
    "vuestro",
    "vuestra",
    "vuestros",
    "vuestras",
}
ALIAS_CONNECTORS = {"de", "del", "la", "las", "el", "los", "y", "e"}


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class DetectedAlias:
    """Alias detectado en el texto."""

    text: str  # Texto del alias: "el Magistral"
    alias_type: AliasType  # Tipo de alias
    base_form: str  # Forma base: "Magistral"
    start_char: int  # Posición inicio
    end_char: int  # Posición fin
    confidence: float = 0.7  # Confianza de detección
    resolved_to: str | None = None  # Entidad resuelta si se conoce
    context: str = ""  # Contexto circundante

    def __hash__(self):
        return hash((self.text, self.start_char, self.end_char))


@dataclass
class AliasCluster:
    """Cluster de alias que refieren a la misma entidad."""

    canonical_name: str  # Nombre canónico: "Fermín de Pas"
    aliases: list[DetectedAlias] = field(default_factory=list)
    confidence: float = 0.0  # Confianza agregada
    source: str = "unknown"  # Fuente de resolución

    def add_alias(self, alias: DetectedAlias):
        """Añade un alias al cluster."""
        if alias not in self.aliases:
            self.aliases.append(alias)
            alias.resolved_to = self.canonical_name


@dataclass
class AliasResolutionResult:
    """Resultado de la resolución de alias."""

    clusters: list[AliasCluster] = field(default_factory=list)
    unresolved: list[DetectedAlias] = field(default_factory=list)
    method_used: str = "unknown"
    processing_time: float = 0.0


# =============================================================================
# Detector de Alias
# =============================================================================


class AliasDetector:
    """
    Detecta alias y referencias indirectas en texto narrativo.

    Patrones detectados:
    1. artículo + título: "el doctor", "la condesa"
    2. artículo + apodo: "el Magistral", "la Regenta"
    3. título + nombre: "don Fermín", "fray Luis"
    4. relación + posesivo: "su madre", "el padre de Juan"
    """

    def __init__(self, nlp=None):
        """
        Inicializa el detector.

        Args:
            nlp: Modelo spaCy (opcional, para análisis morfológico)
        """
        self._nlp = nlp
        self._nlp_loaded = False

    def _get_nlp(self):
        """Obtiene modelo spaCy (lazy loading)."""
        if not self._nlp_loaded:
            try:
                from .spacy_gpu import load_spacy_model

                self._nlp = load_spacy_model()
            except Exception as e:
                logger.warning(f"spaCy no disponible para alias detector: {e}")
                self._nlp = None
            self._nlp_loaded = True
        return self._nlp

    def detect_aliases(self, text: str) -> list[DetectedAlias]:
        """
        Detecta todos los alias en el texto.

        Args:
            text: Texto a analizar

        Returns:
            Lista de alias detectados
        """
        aliases = []

        # 1. Detectar aposiciones descriptivas explícitas:
        #    "Pedro, el carpintero, ..." -> alias ya resuelto a "Pedro"
        appositive_aliases = self._detect_appositive_descriptor_patterns(text)
        aliases.extend(appositive_aliases)

        # 2. Propagar alias definidos en aposición:
        #    "Pedro, el carpintero, ... El carpintero ..."
        aliases.extend(self._detect_defined_alias_repetitions(text, appositive_aliases))

        # 3. Detectar patrones con artículo + título/apodo
        aliases.extend(self._detect_article_title_patterns(text))

        # 4. Detectar patrones título + nombre (don Fermín)
        aliases.extend(self._detect_title_name_patterns(text))

        # 5. Detectar apodos con artículo ("el Gordo", "la Regenta")
        aliases.extend(self._detect_nickname_patterns(text))

        # 6. Detectar relaciones familiares con posesivo
        aliases.extend(self._detect_family_patterns(text))

        # 7. Detectar descriptores nominales genéricos en contexto de persona:
        #    "la joven", "la rubia", "el abuelo", "el manco de Lepanto"
        aliases.extend(self._detect_generic_descriptor_patterns(text))

        # Deduplicar por posición
        seen_positions = set()
        unique_aliases = []
        for alias in aliases:
            pos = (alias.start_char, alias.end_char)
            if pos not in seen_positions:
                unique_aliases.append(alias)
                seen_positions.add(pos)

        return unique_aliases

    def _detect_appositive_descriptor_patterns(self, text: str) -> list[DetectedAlias]:
        """
        Detecta aposiciones tipo "Nombre, el/la descriptor, ...".

        Ejemplos:
        - "Pedro, el carpintero, ..."
        - "Cervantes, el manco de Lepanto, ..."
        - "María, la rubia, ..."
        """
        aliases = []

        name_pattern = (
            r"[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+"
            r"(?:\s+(?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+|de|del|la|las|los|y)){0,5}"
        )
        desc_pattern = (
            r"(?:"
            + "|".join(ALIAS_DETERMINERS)
            + r")\s+[a-záéíóúñ]+(?:\s+(?:[a-záéíóúñ]+|de|del|la|las|los|y|e)){0,5}"
        )

        # Nombre primero: "Pedro, el carpintero, ..."
        pattern_name_first = rf"\b({name_pattern})\s*,\s*({desc_pattern})\s*,"
        for match in re.finditer(pattern_name_first, text, re.IGNORECASE):
            name = match.group(1).strip()
            alias_text = match.group(2).strip()
            if not self._is_valid_alias_phrase(alias_text):
                continue

            ctx_start = max(0, match.start(2) - 80)
            ctx_end = min(len(text), match.end(2) + 80)

            aliases.append(
                DetectedAlias(
                    text=alias_text,
                    alias_type=self._infer_alias_type_from_phrase(alias_text),
                    base_form=self._extract_base_form(alias_text),
                    start_char=match.start(2),
                    end_char=match.end(2),
                    confidence=0.95,
                    resolved_to=name,
                    context=text[ctx_start:ctx_end],
                )
            )

        # Descriptor primero: "El carpintero, Pedro, ..."
        pattern_desc_first = rf"\b({desc_pattern})\s*,\s*({name_pattern})\s*,"
        for match in re.finditer(pattern_desc_first, text, re.IGNORECASE):
            alias_text = match.group(1).strip()
            name = match.group(2).strip()
            if not self._is_valid_alias_phrase(alias_text):
                continue

            ctx_start = max(0, match.start(1) - 80)
            ctx_end = min(len(text), match.end(1) + 80)

            aliases.append(
                DetectedAlias(
                    text=alias_text,
                    alias_type=self._infer_alias_type_from_phrase(alias_text),
                    base_form=self._extract_base_form(alias_text),
                    start_char=match.start(1),
                    end_char=match.end(1),
                    confidence=0.93,
                    resolved_to=name,
                    context=text[ctx_start:ctx_end],
                )
            )

        return aliases

    def _detect_defined_alias_repetitions(
        self,
        text: str,
        definitions: list[DetectedAlias],
    ) -> list[DetectedAlias]:
        """
        Reutiliza definiciones de alias ya ancladas por aposición.

        Si se detectó "Pedro, el carpintero, ...", cualquier reaparición de
        "el carpintero" (o formas contractas razonables) se resuelve a Pedro.
        """
        aliases: list[DetectedAlias] = []
        definitions_by_variant: dict[str, list[DetectedAlias]] = {}

        for definition in definitions:
            if not definition.resolved_to:
                continue
            for variant in self._build_alias_variants(definition.text):
                definitions_by_variant.setdefault(variant, []).append(definition)

        seen_positions: set[tuple[int, int]] = set()
        for variant, variant_definitions in definitions_by_variant.items():
            pattern = rf"\b{re.escape(variant)}\b"
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start = match.start()
                end = match.end()

                # Saltar spans ya cubiertos y la ocurrencia definitoria exacta
                if (start, end) in seen_positions:
                    continue
                if any(d.start_char == start and d.end_char == end for d in variant_definitions):
                    continue
                if any(start < d.end_char and end > d.start_char for d in variant_definitions):
                    continue

                # Elegir definición más cercana hacia atrás (o en general si no hay previa).
                nearest = min(
                    variant_definitions,
                    key=lambda d: (
                        (0 if d.start_char <= start else 1),
                        abs(start - d.start_char),
                    ),
                )
                if not nearest.resolved_to:
                    continue

                ctx_start = max(0, start - 80)
                ctx_end = min(len(text), end + 80)

                aliases.append(
                    DetectedAlias(
                        text=match.group(0),
                        alias_type=nearest.alias_type,
                        base_form=nearest.base_form,
                        start_char=start,
                        end_char=end,
                        confidence=max(0.72, nearest.confidence - 0.12),
                        resolved_to=nearest.resolved_to,
                        context=text[ctx_start:ctx_end],
                    )
                )
                seen_positions.add((start, end))

        return aliases

    def _detect_article_title_patterns(self, text: str) -> list[DetectedAlias]:
        """Detecta patrones tipo 'el doctor', 'la condesa'."""
        aliases = []

        # Patrón: artículo + título (profesional, eclesiástico, noble, militar)
        pattern = r"\b(el|la|los|las)\s+(" + "|".join(ALL_TITLES) + r")\b"
        for match in re.finditer(pattern, text, re.IGNORECASE):
            match.group(1).lower()
            title = match.group(2).lower()

            # Determinar tipo de alias
            if title in PROFESSIONAL_TITLES:
                alias_type = AliasType.PROFESSIONAL
            elif title in ECCLESIASTIC_TITLES:
                alias_type = AliasType.ECCLESIASTIC
            elif title in NOBLE_TITLES:
                alias_type = AliasType.NOBLE
            elif title in MILITARY_TITLES:
                alias_type = AliasType.MILITARY
            else:
                alias_type = AliasType.ROLE

            # Extraer contexto
            ctx_start = max(0, match.start() - 50)
            ctx_end = min(len(text), match.end() + 50)

            alias = DetectedAlias(
                text=match.group(0),
                alias_type=alias_type,
                base_form=title.capitalize(),
                start_char=match.start(),
                end_char=match.end(),
                confidence=0.75,
                context=text[ctx_start:ctx_end],
            )
            aliases.append(alias)

        return aliases

    def _detect_title_name_patterns(self, text: str) -> list[DetectedAlias]:
        """Detecta patrones tipo 'don Fermín', 'fray Luis'."""
        aliases = []

        # Títulos que van directamente antes del nombre (sin artículo)
        direct_titles = {"don", "doña", "fray", "sor", "san", "santa"}

        # Patrón: título + nombre propio (capitalizado)
        pattern = (
            r"\b("
            + "|".join(direct_titles)
            + r")\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)\b"
        )
        for match in re.finditer(pattern, text, re.IGNORECASE):
            match.group(1).lower()
            name = match.group(2)

            alias_type = AliasType.HONORIFIC_TITLE

            ctx_start = max(0, match.start() - 50)
            ctx_end = min(len(text), match.end() + 50)

            alias = DetectedAlias(
                text=match.group(0),
                alias_type=alias_type,
                base_form=name,  # El nombre es la forma base
                start_char=match.start(),
                end_char=match.end(),
                confidence=0.85,  # Alta confianza, patrón claro
                context=text[ctx_start:ctx_end],
            )
            aliases.append(alias)

        return aliases

    def _detect_nickname_patterns(self, text: str) -> list[DetectedAlias]:
        """
        Detecta apodos tipo 'el Magistral', 'la Regenta'.

        Un apodo se caracteriza por:
        - Artículo definido + sustantivo/adjetivo capitalizado
        - El sustantivo NO es un título conocido
        - Suele referirse a una persona específica
        """
        aliases = []

        # Patrón: artículo + palabra capitalizada (no título conocido)
        pattern = r"\b(el|la)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\b"

        for match in re.finditer(pattern, text):
            word = match.group(2).lower()

            # Ignorar si es un título conocido (ya detectado en otra función)
            if word in ALL_TITLES or word in FAMILY_RELATIONS:
                continue

            # Verificar que no sea sustantivo común al analizar contexto
            # Los apodos suelen tener el artículo + palabra como referencia a persona
            full_text = match.group(0)
            position = match.start()

            # Heurística: si aparece en contexto de diálogo o acción, es probable apodo
            ctx_start = max(0, position - 100)
            ctx_end = min(len(text), match.end() + 100)
            context = text[ctx_start:ctx_end]

            # Indicadores de que es referencia a persona
            person_indicators = [
                r"dijo\s+" + re.escape(full_text),
                r"preguntó\s+" + re.escape(full_text),
                re.escape(full_text) + r"\s+dijo",
                re.escape(full_text) + r"\s+respondió",
                re.escape(full_text) + r"\s+se\s+",
                re.escape(full_text) + r"\s+había",
                re.escape(full_text) + r"\s+era",
            ]

            is_person_ref = any(re.search(pat, context, re.IGNORECASE) for pat in person_indicators)

            if is_person_ref:
                alias = DetectedAlias(
                    text=full_text,
                    alias_type=AliasType.NICKNAME,
                    base_form=match.group(2),  # Palabra sin artículo
                    start_char=match.start(),
                    end_char=match.end(),
                    confidence=0.65,  # Confianza media, requiere verificación
                    context=context,
                )
                aliases.append(alias)

        return aliases

    def _detect_family_patterns(self, text: str) -> list[DetectedAlias]:
        """Detecta referencias familiares tipo 'su madre', 'el padre'."""
        aliases = []

        # Patrón 1: posesivo + relación familiar
        poss_pattern = (
            r"\b(mi|tu|su|mis|tus|sus|nuestro|nuestra|vuestro|vuestra)\s+("
            + "|".join(FAMILY_RELATIONS)
            + r")\b"
        )
        for match in re.finditer(poss_pattern, text, re.IGNORECASE):
            match.group(1).lower()
            relation = match.group(2).lower()

            ctx_start = max(0, match.start() - 50)
            ctx_end = min(len(text), match.end() + 50)

            alias = DetectedAlias(
                text=match.group(0),
                alias_type=AliasType.FAMILY,
                base_form=relation.capitalize(),
                start_char=match.start(),
                end_char=match.end(),
                confidence=0.60,  # Requiere contexto para resolver
                context=text[ctx_start:ctx_end],
            )
            aliases.append(alias)

        # Patrón 2: artículo + relación familiar + de + nombre
        art_pattern = (
            r"\b(el|la)\s+(" + "|".join(FAMILY_RELATIONS) + r")\s+de\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\b"
        )
        for match in re.finditer(art_pattern, text, re.IGNORECASE):
            relation = match.group(2).lower()
            name = match.group(3)

            ctx_start = max(0, match.start() - 50)
            ctx_end = min(len(text), match.end() + 50)

            alias = DetectedAlias(
                text=match.group(0),
                alias_type=AliasType.FAMILY,
                base_form=f"{relation.capitalize()} de {name}",
                start_char=match.start(),
                end_char=match.end(),
                confidence=0.80,  # Más confianza porque incluye nombre
                context=text[ctx_start:ctx_end],
            )
            aliases.append(alias)

        return aliases

    def _detect_generic_descriptor_patterns(self, text: str) -> list[DetectedAlias]:
        """
        Detecta descriptores nominales no capitalizados:
        "la joven", "la rubia", "el manco de Lepanto", "el abuelo".

        Se aplica una heurística conservadora de contexto para evitar ruido.
        """
        aliases: list[DetectedAlias] = []

        pattern = (
            r"\b(el|la|los|las)\s+"
            r"([a-záéíóúñ]+(?:\s+(?:de|del)\s+[A-Za-zÁÉÍÓÚÑáéíóúñ]+(?:\s+[A-Za-zÁÉÍÓÚÑáéíóúñ]+){0,2})?)\b"
        )
        for match in re.finditer(pattern, text, re.IGNORECASE):
            alias_text = match.group(0).strip()
            if not self._is_valid_alias_phrase(alias_text):
                continue

            # Evitar duplicar patrones más específicos ya cubiertos.
            first_content = self._extract_base_form(alias_text).lower()
            if first_content in ALL_TITLES:
                continue

            ctx_start = max(0, match.start() - 100)
            ctx_end = min(len(text), match.end() + 100)
            context = text[ctx_start:ctx_end]
            if not self._looks_like_person_reference(alias_text, context):
                continue

            aliases.append(
                DetectedAlias(
                    text=alias_text,
                    alias_type=self._infer_alias_type_from_phrase(alias_text),
                    base_form=self._extract_base_form(alias_text),
                    start_char=match.start(),
                    end_char=match.end(),
                    confidence=0.58,
                    context=context,
                )
            )

        return aliases

    def _infer_alias_type_from_phrase(self, phrase: str) -> AliasType:
        """Clasifica un alias textual sin depender de listas cerradas de nombres."""
        tokens = [
            t.lower()
            for t in re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]+", phrase)
        ]
        content = [t for t in tokens if t not in ALIAS_DETERMINERS and t not in ALIAS_CONNECTORS]
        if not content:
            return AliasType.ROLE

        head = content[0]
        if any(tok in FAMILY_RELATIONS for tok in content):
            return AliasType.FAMILY
        if head in PROFESSIONAL_TITLES:
            return AliasType.PROFESSIONAL
        if head in ECCLESIASTIC_TITLES:
            return AliasType.ECCLESIASTIC
        if head in NOBLE_TITLES:
            return AliasType.NOBLE
        if head in MILITARY_TITLES:
            return AliasType.MILITARY
        return AliasType.DESCRIPTIVE

    def _extract_base_form(self, phrase: str) -> str:
        """Obtiene la cabeza léxica principal de un alias textual."""
        tokens = re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]+", phrase)
        for token in tokens:
            token_l = token.lower()
            if token_l not in ALIAS_DETERMINERS and token_l not in ALIAS_CONNECTORS:
                return token.capitalize()
        return phrase.strip().capitalize()

    def _is_valid_alias_phrase(self, phrase: str) -> bool:
        """Valida estructura mínima de una frase alias nominal."""
        cleaned = phrase.strip().strip(",.;:!?")
        if len(cleaned) < 4 or len(cleaned) > 70:
            return False

        if re.search(r"[\"“”()\[\]]", cleaned):
            return False

        if re.search(r"\b(que|cuando|porque|aunque|mientras|si)\b", cleaned, re.IGNORECASE):
            return False

        tokens = re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]+", cleaned)
        if len(tokens) < 2 or len(tokens) > 8:
            return False

        if tokens[0].lower() not in ALIAS_DETERMINERS:
            return False

        content = [t for t in tokens[1:] if t.lower() not in ALIAS_CONNECTORS]
        if not content:
            return False

        return True

    def _build_alias_variants(self, alias_text: str) -> list[str]:
        """Genera variantes razonables para recuperar repeticiones del alias."""
        normalized = " ".join(alias_text.lower().split())
        tokens = normalized.split()
        if len(tokens) < 2:
            return [normalized]

        variants = {normalized}
        first = tokens[0]
        tail = " ".join(tokens[1:])

        # Variante corta: "el manco de Lepanto" -> "el manco"
        if len(tokens) >= 2:
            variants.add(" ".join(tokens[:2]))

        # Contracciones/preposiciones frecuentes.
        if first == "el":
            variants.add(f"del {tail}")
            variants.add(f"al {tail}")
        elif first == "la":
            variants.add(f"de la {tail}")
            variants.add(f"a la {tail}")
        elif first == "los":
            variants.add(f"de los {tail}")
            variants.add(f"a los {tail}")
        elif first == "las":
            variants.add(f"de las {tail}")
            variants.add(f"a las {tail}")

        return sorted(v for v in variants if len(v) >= 4)

    def _looks_like_person_reference(self, alias_text: str, context: str) -> bool:
        """Heurística simple para filtrar descriptores no personales."""
        alias_escaped = re.escape(alias_text)
        person_verb_stems = (
            "dij|pregunt|respond|habl|grit|susurr|mir|entr|sal|lleg|"
            "sonri|llor|pens|record|corr|camin|abraz|bes|teni|era|estab|fue"
        )
        patterns = [
            rf"{alias_escaped}\s+\w*({person_verb_stems})\w*",
            rf"\w*({person_verb_stems})\w*\s+(?:a|con)?\s*{alias_escaped}",
            rf"{alias_escaped}\s+se\s+\w+",
        ]
        return any(re.search(p, context, re.IGNORECASE) for p in patterns)


# =============================================================================
# Resolutor de Alias
# =============================================================================


class AliasResolver:
    """
    Resuelve alias a sus entidades canónicas.

    Métodos de resolución:
    1. Contexto local: Busca nombres propios cercanos
    2. Frecuencia global: El nombre más frecuente con ese alias
    3. LLM: Análisis semántico profundo
    4. Correferencias: Usa cadenas de correferencia existentes
    """

    def __init__(self, nlp=None, llm_client=None):
        """
        Inicializa el resolutor.

        Args:
            nlp: Modelo spaCy
            llm_client: Cliente LLM para resolución avanzada
        """
        self._nlp = nlp
        self._llm_client = llm_client
        self._lock = threading.Lock()

    def resolve_aliases(
        self,
        aliases: list[DetectedAlias],
        text: str,
        known_entities: list | None = None,
        coref_chains: list | None = None,
    ) -> AliasResolutionResult:
        """
        Resuelve alias a sus entidades canónicas.

        Args:
            aliases: Lista de alias detectados
            text: Texto completo
            known_entities: Entidades ya conocidas (nombres propios)
            coref_chains: Cadenas de correferencia existentes

        Returns:
            Resultado con clusters de alias resueltos
        """
        import time

        start_time = time.time()

        result = AliasResolutionResult()

        # 1. Resolver por contexto local (títulos + nombre cercano)
        for alias in aliases:
            resolved_source = "context"

            # Si el detector ya obtuvo una ancla fiable (p. ej. aposición),
            # preferir esa resolución.
            resolved = alias.resolved_to
            if resolved:
                resolved_source = "pattern"
            else:
                resolved = self._resolve_by_context(alias, text, known_entities)

            if not resolved and coref_chains:
                resolved = self._resolve_with_coref(alias, coref_chains)
                if resolved:
                    resolved_source = "coreference"

            if resolved:
                # Crear o añadir a cluster
                cluster = self._find_or_create_cluster(result.clusters, resolved)
                cluster.add_alias(alias)
                cluster.confidence = max(cluster.confidence, alias.confidence)
                cluster.source = resolved_source
            else:
                result.unresolved.append(alias)

        # 2. Intentar resolver los no resueltos con LLM
        if result.unresolved and self._llm_client:
            self._resolve_with_llm(result.unresolved, text, known_entities)
            newly_resolved = []
            for alias in result.unresolved:
                if alias.resolved_to:
                    cluster = self._find_or_create_cluster(result.clusters, alias.resolved_to)
                    cluster.add_alias(alias)
                    cluster.source = "llm"
                    newly_resolved.append(alias)

            # Quitar los resueltos de la lista de no resueltos
            result.unresolved = [a for a in result.unresolved if a not in newly_resolved]

        result.method_used = "context+llm" if self._llm_client else "context"
        result.processing_time = time.time() - start_time

        return result

    def _resolve_by_context(
        self,
        alias: DetectedAlias,
        text: str,
        known_entities: list | None,
    ) -> str | None:
        """
        Intenta resolver un alias por contexto local.

        Busca nombres propios cercanos que podrían ser la referencia.
        """
        if not known_entities:
            return None

        # Para títulos tipo "don X", el nombre ya está en el alias
        if alias.alias_type == AliasType.HONORIFIC_TITLE:
            # El base_form ya es el nombre
            return alias.base_form

        # Buscar entidades cercanas en el texto
        context_window = 500  # caracteres
        ctx_start = max(0, alias.start_char - context_window)
        ctx_end = min(len(text), alias.end_char + context_window)
        context_text = text[ctx_start:ctx_end].lower()

        candidates = []
        for entity in known_entities:
            for entity_text in self._extract_entity_names(entity):
                if not entity_text:
                    continue
                pos_local = context_text.find(entity_text.lower())
                if pos_local < 0:
                    continue
                pos = ctx_start + pos_local
                distance = abs(pos - alias.start_char)
                candidates.append((entity_text, distance))

        if not candidates:
            return None

        # Ordenar por distancia y devolver el más cercano
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]

    def _resolve_with_coref(
        self,
        alias: DetectedAlias,
        coref_chains: list,
    ) -> str | None:
        """Usa cadenas de correferencia ya calculadas como respaldo."""
        alias_norm = alias.text.strip().lower()
        if not alias_norm:
            return None

        for chain in coref_chains:
            main = getattr(chain, "main_mention", None)
            if not main:
                continue
            for mention in getattr(chain, "mentions", []) or []:
                if getattr(mention, "text", "").strip().lower() == alias_norm:
                    return str(main)
        return None

    def _extract_entity_names(self, entity: object) -> list[str]:
        """Extrae nombres y alias de una entidad heterogénea (str/objeto/dataclass)."""
        if isinstance(entity, str):
            stripped = entity.strip()
            return [stripped] if stripped else []

        candidates: list[str] = []
        for attr in ("canonical_name", "name", "text"):
            value = getattr(entity, attr, None)
            if isinstance(value, str):
                value = value.strip()
                if value:
                    candidates.append(value)

        aliases = getattr(entity, "aliases", None)
        if isinstance(aliases, (list, tuple, set)):
            for alias in aliases:
                if isinstance(alias, str):
                    alias = alias.strip()
                    if alias:
                        candidates.append(alias)

        # Deduplicar preservando orden
        seen = set()
        unique = []
        for name in candidates:
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(name)
        return unique

    def _resolve_with_llm(
        self,
        aliases: list[DetectedAlias],
        text: str,
        known_entities: list | None,
    ) -> list[DetectedAlias]:
        """
        Usa LLM para resolver alias complejos.
        """
        if not self._llm_client:
            return aliases

        from narrative_assistant.llm.sanitization import sanitize_for_prompt

        # Sanitizar datos del manuscrito antes de enviarlo al LLM (A-10)
        entities_str = ", ".join(
            sanitize_for_prompt(getattr(e, "text", str(e)), max_length=100)
            for e in (known_entities or [])[:20]
        )
        aliases_str = "\n".join(
            f"- {sanitize_for_prompt(a.text, max_length=100)} ({a.alias_type.value}): contexto '{sanitize_for_prompt(a.context[:100], max_length=100)}...'"
            for a in aliases[:10]
        )

        prompt = f"""Analiza estos alias/referencias en un texto narrativo español y determina a qué personaje se refieren.

PERSONAJES CONOCIDOS: {entities_str}

ALIAS A RESOLVER:
{aliases_str}

Para cada alias, indica a qué personaje de la lista se refiere, o "DESCONOCIDO" si no se puede determinar.

Responde SOLO con JSON:
{{"resolutions": [
  {{"alias": "el Magistral", "refers_to": "Fermín de Pas", "confidence": 0.9}},
  {{"alias": "su madre", "refers_to": "DESCONOCIDO", "confidence": 0.3}}
]}}

JSON:"""

        try:
            response = self._llm_client.complete(
                prompt,
                system="Eres un experto en análisis literario español. Resuelves referencias y alias de personajes.",
                temperature=0.1,
            )

            if response:
                import json

                # Limpiar respuesta
                cleaned = response.strip()
                if cleaned.startswith("```"):
                    lines = cleaned.split("\n")
                    lines = [l for l in lines if not l.startswith("```")]
                    cleaned = "\n".join(lines)

                start = cleaned.find("{")
                end = cleaned.rfind("}") + 1
                if start >= 0 and end > start:
                    data = json.loads(cleaned[start:end])

                    for resolution in data.get("resolutions", []):
                        alias_text = resolution.get("alias", "")
                        refers_to = resolution.get("refers_to", "")

                        if refers_to and refers_to != "DESCONOCIDO":
                            # Encontrar el alias correspondiente
                            for alias in aliases:
                                if alias.text.lower() == alias_text.lower():
                                    alias.resolved_to = refers_to
                                    alias.confidence = resolution.get("confidence", 0.7)
                                    break

        except Exception as e:
            logger.warning(f"Error en resolución LLM de alias: {e}")

        return aliases

    def _find_or_create_cluster(
        self,
        clusters: list[AliasCluster],
        canonical_name: str,
    ) -> AliasCluster:
        """Encuentra o crea un cluster para un nombre canónico."""
        for cluster in clusters:
            if cluster.canonical_name.lower() == canonical_name.lower():
                return cluster

        new_cluster = AliasCluster(canonical_name=canonical_name)
        clusters.append(new_cluster)
        return new_cluster


# =============================================================================
# Funciones de Conveniencia
# =============================================================================

_detector: AliasDetector | None = None
_resolver: AliasResolver | None = None
_lock = threading.Lock()


def get_alias_detector() -> AliasDetector:
    """Obtiene el detector de alias singleton."""
    global _detector
    if _detector is None:
        with _lock:
            if _detector is None:
                _detector = AliasDetector()
    return _detector


def get_alias_resolver() -> AliasResolver:
    """Obtiene el resolutor de alias singleton."""
    global _resolver
    if _resolver is None:
        with _lock:
            if _resolver is None:
                _resolver = AliasResolver()
    return _resolver


def detect_and_resolve_aliases(
    text: str,
    known_entities: list | None = None,
) -> AliasResolutionResult:
    """
    Función de conveniencia para detectar y resolver alias.

    Args:
        text: Texto a analizar
        known_entities: Lista de entidades conocidas

    Returns:
        Resultado de resolución de alias
    """
    detector = get_alias_detector()
    resolver = get_alias_resolver()

    aliases = detector.detect_aliases(text)
    return resolver.resolve_aliases(aliases, text, known_entities)
