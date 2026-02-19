"""
Validador de entidades multi-capa.

Sistema de validación que combina múltiples estrategias para filtrar
falsos positivos en la detección de entidades:

1. Validación LLM (si disponible): Revisa entidades en contexto narrativo
2. Scoring heurístico (siempre activo): Múltiples señales combinadas
3. Feedback del usuario: Entidades rechazadas persistentes por proyecto

El sistema es degradable: si el LLM no está disponible, usa solo
heurísticas + feedback, manteniendo una precisión razonable.
"""

import logging
import re
import threading
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ..entities.filters import get_filter_repository

logger = logging.getLogger(__name__)


# =============================================================================
# Configuración
# =============================================================================


@dataclass
class EntityValidatorConfig:
    """Configuración del validador de entidades."""

    # Umbrales
    min_confidence_threshold: float = 0.4  # Score mínimo para aceptar entidad
    llm_validation_enabled: bool = True  # Usar LLM si está disponible
    morphology_check_enabled: bool = True  # Usar análisis morfológico con spaCy

    # Pesos para scoring heurístico
    weight_frequency: float = 0.15  # Aparece más de una vez
    weight_capitalization: float = 0.15  # Capitalización consistente
    weight_position: float = 0.10  # No es inicio de oración
    weight_length: float = 0.10  # Longitud >= 3 caracteres
    weight_no_article: float = 0.15  # No empieza con artículo
    weight_not_common: float = 0.15  # No es palabra común
    weight_morphology: float = 0.20  # Penalización si parece verbo (POS-tag)

    # Configuración LLM
    llm_batch_size: int = 20  # Entidades a validar por llamada LLM
    llm_timeout: float = 30.0  # Timeout para validación LLM


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class EntityScore:
    """Score de validación de una entidad."""

    text: str
    total_score: float
    is_valid: bool

    # Scores individuales
    frequency_score: float = 0.0
    capitalization_score: float = 0.0
    position_score: float = 0.0
    length_score: float = 0.0
    article_score: float = 0.0
    common_word_score: float = 0.0
    morphology_score: float = 1.0  # Penalización si parece verbo
    llm_score: float | None = None

    # Metadata
    validation_method: str = "heuristic"  # "heuristic", "llm", "combined"
    rejection_reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "total_score": round(self.total_score, 3),
            "is_valid": self.is_valid,
            "scores": {
                "frequency": round(self.frequency_score, 3),
                "capitalization": round(self.capitalization_score, 3),
                "position": round(self.position_score, 3),
                "length": round(self.length_score, 3),
                "article": round(self.article_score, 3),
                "common_word": round(self.common_word_score, 3),
                "morphology": round(self.morphology_score, 3),
                "llm": round(self.llm_score, 3) if self.llm_score else None,
            },
            "method": self.validation_method,
            "rejection_reason": self.rejection_reason,
        }


@dataclass
class ValidationResult:
    """Resultado de validación de un conjunto de entidades."""

    valid_entities: list  # ExtractedEntity que pasaron validación
    rejected_entities: list  # ExtractedEntity rechazadas
    scores: dict[str, EntityScore] = field(default_factory=dict)  # text -> score

    validation_method: str = "heuristic"
    llm_available: bool = False

    @property
    def acceptance_rate(self) -> float:
        total = len(self.valid_entities) + len(self.rejected_entities)
        return len(self.valid_entities) / total if total > 0 else 1.0


# =============================================================================
# Detección de Zonas No-Narrativas
# =============================================================================

# Patrones para detectar líneas que son encabezados/títulos (no narrativa)
# Las entidades en estas zonas deben filtrarse o penalizarse
HEADING_LINE_PATTERNS = [
    # Capítulos en varios formatos
    r"^#{1,6}\s+",  # Markdown headings
    r"^(CAPÍTULO|CAPITULO|CAP\.?)\s*[\dIVXLCDM]+\.?\s*",
    r"^(CHAPTER|Cap[íi]tulo)\s+[\dIVXLCDM]+\.?\s*",
    # Partes/secciones
    r"^(PARTE|SECCIÓN|SECCION|BOOK|LIBRO)\s+[\dIVXLCDM]+\.?\s*",
    r"^(PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA)\s+(PARTE|SECCION)",
    # Prólogo/Epílogo
    r"^(PRÓLOGO|PROLOGO|EPÍLOGO|EPILOGO|PROLOGUE|EPILOGUE)\s*$",
    # Títulos de capítulo (solo mayúsculas, mín 10 chars)
    r"^[A-ZÁÉÍÓÚÑÜ\s\-:]{10,60}$",
    # Números romanos solos (títulos de capítulo)
    r"^[IVXLCDM]+\s*\.?\s*$",
    # Números arábigos solos o con punto
    r"^\d{1,3}\s*\.?\s*$",
]

# Patrones para detectar líneas de metadatos/estructura
METADATA_LINE_PATTERNS = [
    # Etiquetas de atributos
    r"^(Nombre|Edad|Profesión|Descripción|Personaje|Atributo|Tipo|Género)\s*:",
    r"^(Ojos|Cabello|Pelo|Estatura|Altura|Peso|Complexión)\s*:",
    # Listas de personajes/lugares
    r"^(PERSONAJES?|LUGARES?|ORGANIZACIONES?|EVENTOS?|TIMELINE)\s*:?\s*$",
    r"^(Lista de|Resumen de|Índice de)\s+",
    # Marcadores de formato
    r"^[-•*]\s+[A-ZÁÉÍÓÚ]",  # Listas con bullets
    r"^\d+\.\s+[A-ZÁÉÍÓÚ]",  # Listas numeradas al inicio
    # Etiquetas de errores gramaticales (en textos de prueba)
    r"^(ERRORES?\s+GRAMATICALES?|Errores?\s+de\s+concordancia)",
    r"^(DEQUEÍSMO|QUEÍSMO|LAÍSMO|LEÍSMO)\s*:?\s*$",
    # Instrucciones/notas
    r"^(NOTA|NOTE|AVISO|IMPORTANTE|TODO|FIXME)\s*:",
    # Variantes ortográficas con barra
    r".*/.+",  # Contiene barra (como "Capitulo/Chapter")
]

# Compilar patrones una sola vez
_HEADING_PATTERNS = [re.compile(p, re.IGNORECASE) for p in HEADING_LINE_PATTERNS]
_METADATA_PATTERNS = [re.compile(p, re.IGNORECASE) for p in METADATA_LINE_PATTERNS]


def is_non_narrative_line(line: str) -> bool:
    """
    Determina si una línea es no-narrativa (encabezado, metadato, título).

    Las entidades detectadas en líneas no-narrativas son probablemente
    falsos positivos (títulos de capítulo, etiquetas, etc.).

    Args:
        line: Línea de texto a evaluar

    Returns:
        True si es una línea no-narrativa
    """
    line = line.strip()

    if not line:
        return True  # Líneas vacías no son narrativa

    # Líneas muy cortas con todo mayúsculas (probablemente título)
    if len(line) < 50 and line.isupper():
        return True

    # Verificar patrones de encabezado
    for pattern in _HEADING_PATTERNS:
        if pattern.match(line):
            return True

    # Verificar patrones de metadatos
    return any(pattern.match(line) for pattern in _METADATA_PATTERNS)


def get_line_for_position(text: str, position: int) -> tuple[str, bool]:
    """
    Obtiene la línea completa que contiene una posición dada.

    Args:
        text: Texto completo
        position: Posición del caracter

    Returns:
        Tupla (línea, es_inicio_de_línea):
        - línea: texto de la línea completa
        - es_inicio_de_línea: True si position está al inicio de la línea
    """
    if position < 0 or position >= len(text):
        return "", False

    # Encontrar inicio de línea
    line_start = text.rfind("\n", 0, position)
    line_start = line_start + 1 if line_start != -1 else 0

    # Encontrar fin de línea
    line_end = text.find("\n", position)
    line_end = line_end if line_end != -1 else len(text)

    line = text[line_start:line_end]
    is_line_start = (position == line_start) or (position - line_start < 3)

    return line, is_line_start


# =============================================================================
# Palabras y patrones comunes (para heurísticas)
# =============================================================================

# Marcadores discursivos temporales y conectores que NO son entidades
# (integrado desde entity_validation.py)
DISCOURSE_MARKERS = {
    # Temporales
    "acto seguido",
    "poco después",
    "al día siguiente",
    "mientras tanto",
    "de repente",
    "al cabo de",
    "en ese momento",
    "al instante",
    "seguidamente",
    "a continuación",
    "más tarde",
    "más adelante",
    "poco antes",
    "justo después",
    "inmediatamente después",
    # Conectores discursivos
    "por lo tanto",
    "sin embargo",
    "no obstante",
    "en consecuencia",
    "por consiguiente",
    "así pues",
    "de hecho",
    "en efecto",
    "por cierto",
    # Expresiones fijas
    "de todos modos",
    "en cualquier caso",
    "de todas formas",
    "sea como sea",
    "en todo caso",
    # Cuantificadores temporales
    "una vez más",
    "otra vez",
    "de nuevo",
    "nuevamente",
}

# Palabras muy comunes en español que rara vez son entidades
COMMON_SPANISH_WORDS = {
    # Artículos y determinantes
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    "este",
    "esta",
    "estos",
    "estas",
    "ese",
    "esa",
    "esos",
    "esas",
    "aquel",
    "aquella",
    "aquellos",
    "aquellas",
    # Pronombres
    "yo",
    "tú",
    "él",
    "ella",
    "nosotros",
    "vosotros",
    "ellos",
    "ellas",
    "me",
    "te",
    "se",
    "nos",
    "os",
    "le",
    "les",
    "lo",
    "mí",
    "ti",
    "sí",
    "conmigo",
    "contigo",
    "consigo",
    # Posesivos
    "mi",
    "mis",
    "tu",
    "tus",
    "su",
    "sus",
    "nuestro",
    "nuestra",
    "vuestro",
    "vuestra",
    "nuestros",
    "nuestras",
    "vuestros",
    "vuestras",
    # Preposiciones
    "a",
    "ante",
    "bajo",
    "con",
    "contra",
    "de",
    "desde",
    "en",
    "entre",
    "hacia",
    "hasta",
    "para",
    "por",
    "según",
    "sin",
    "sobre",
    "tras",
    # Conjunciones
    "y",
    "e",
    "o",
    "u",
    "ni",
    "que",
    "pero",
    "sino",
    "aunque",
    "porque",
    "pues",
    "como",
    "cuando",
    "donde",
    "si",
    "mientras",
    "apenas",
    # Adverbios comunes
    "no",
    "muy",
    "más",
    "menos",
    "tan",
    "tanto",
    "mucho",
    "poco",
    "bien",
    "mal",
    "mejor",
    "peor",
    "siempre",
    "nunca",
    "también",
    "tampoco",
    "aquí",
    "allí",
    "ahí",
    "acá",
    "allá",
    "cerca",
    "lejos",
    "dentro",
    "fuera",
    "arriba",
    "abajo",
    "delante",
    "detrás",
    "encima",
    "debajo",
    "antes",
    "después",
    "ahora",
    "luego",
    "entonces",
    "todavía",
    "ya",
    "quizá",
    "quizás",
    "acaso",
    "tal vez",
    # Interrogativos/exclamativos
    "qué",
    "quién",
    "quiénes",
    "cuál",
    "cuáles",
    "cuánto",
    "cuánta",
    "cuántos",
    "cuántas",
    "cómo",
    "dónde",
    "cuándo",
    "por qué",
    # Verbos auxiliares comunes
    "ser",
    "estar",
    "haber",
    "tener",
    "hacer",
    "poder",
    "deber",
    "ir",
    "es",
    "está",
    "hay",
    "tiene",
    "hace",
    "puede",
    "debe",
    "va",
    "era",
    "estaba",
    "había",
    "tenía",
    "hacía",
    "podía",
    "debía",
    "iba",
    "fue",
    "estuvo",
    "hubo",
    "tuvo",
    "hizo",
    "pudo",
    "debió",  # Sustantivos muy genéricos
    "cosa",
    "cosas",
    "algo",
    "nada",
    "todo",
    "parte",
    "vez",
    "veces",
    "manera",
    "forma",
    "modo",
    "tipo",
    "clase",
    "especie",
    "hombre",
    "mujer",
    "persona",
    "gente",
    "mundo",
    "vida",
    "tiempo",
    "día",
    "días",
    "noche",
    "noches",
    "año",
    "años",
    "momento",
    "lugar",
    # Adjetivos muy comunes
    "bueno",
    "malo",
    "grande",
    "pequeño",
    "nuevo",
    "viejo",
    "joven",
    "alto",
    "largo",
    "corto",
    "ancho",
    "estrecho",
    "primero",
    "último",
    "siguiente",
    "anterior",
    "mismo",
    "otro",
    "demás",
    # NUEVOS: Palabras que aparecen capitalizadas como ejemplos de errores
    "correcto",
    "incorrecto",
    "habemos",
    "hubieron",
    "haiga",
    "mayor",
    "menor",
}

# Patrones que indican que NO es una entidad
NOT_ENTITY_PATTERNS = [
    # Preguntas
    r"^¿",
    r"\?$",
    # Frases interrogativas
    r"^(quién|qué|cómo|dónde|cuándo|cuánto|por qué|para qué)\s",
    # Descripciones con posesivos
    r"^(mi|tu|su|mis|tus|sus)\s+(cara|rostro|ojos|pelo|cabello|mano|manos|cuerpo|voz)",
    # Artículo + adjetivo + sustantivo común
    r"^(el|la|los|las|un|una)\s+(pequeño|grande|viejo|joven|alto|bajo)\s+",
    # Frases de diálogo comunes
    r"^(hola|adiós|gracias|por favor|perdón|disculpa)\b",
    # Números y fechas
    r"^\d+\s*(de\s+)?(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)",
    # Expresiones temporales
    r"^(ayer|hoy|mañana|anoche|esta noche|esta mañana)\b",
    # Títulos de secciones/capítulos en mayúsculas (permitir palabras adicionales)
    r"^(CAPÍTULO|CAPITULO|PARTE|SECCIÓN|SECCION|PRÓLOGO|PROLOGO|EPÍLOGO|EPILOGO|FIN|MANUSCRITO|DOCUMENTO|TEXTO|NOTAS?)\s*(DE\s+|DEL\s+)?",
    # Patrones de metadatos/formato (Personaje X:, Atributo:, etc.)
    r"^(Personaje|Atributo|Ojos|Cabello|Pelo|Estatura|Edad|Profesión|Descripción|Nombre|Tipo)\s*[:,]",
    # NOTA: El siguiente patrón de mayúsculas se ha movido a CASE_SENSITIVE_NOT_ENTITY_PATTERNS
    # porque no debe usar IGNORECASE
    # Patrones de listas o etiquetas
    r"^[-•*]\s*",
    # ===== NUEVOS PATRONES PARA METADATOS (Iteración 1) =====
    # Encabezados de secciones de metadatos
    r"^LISTA\s+DE\s+",
    r"^Inconsistencias?\s+(intencionadas?|temporales?)?\s*:?",
    r"^RESUMEN\s+(DE|CRONOLÓGICO)",
    # Palabras sueltas en mayúsculas seguidas de dos puntos (metadata)
    r"^[A-ZÁÉÍÓÚÑÜ]{3,}\s*:",
    # Días de la semana (no son entidades)
    r"^(lunes|martes|miércoles|jueves|viernes|sábado|domingo)$",
    # Palabras comunes que aparecen capitalizadas al inicio de línea en listas
    r"^(Barba|Postre|Perfume|Bebida|Estatura)\b",
    # ===== NUEVOS PATRONES ITERACIÓN 2 =====
    # Términos metalingüísticos (gramática, lingüística)
    r"^(Dequeísmo|Queísmo|Laísmo|Leísmo|Loísmo|Concordancia|Redundancia|Pleonasmo|Solecismo|Anacoluto)\b",
    # Términos que terminan en -ísmo/-ístico (generalmente abstractos)
    r"^[A-ZÁÉÍÓÚ][a-záéíóúñ]+(ísmo|ístico|ísticos|ísticas)s?$",
    # Entidades con barra (variantes ortográficas)
    r"^[A-Za-záéíóúñÁÉÍÓÚÑ]+/[A-Za-záéíóúñÁÉÍÓÚÑ]+$",
    # Texto de errores gramaticales como ejemplo
    r"^(ERRORES\s+GRAMATICALES|Errores\s+gramaticales)\b",
    # ===== NUEVOS PATRONES ITERACIÓN 3 =====
    # Títulos de partes: "PRIMERA PARTE", "Segunda Parte", etc.
    r"^(PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA|SEXTA|SEPTIMA|OCTAVA|NOVENA|DECIMA)\s+(PARTE|SECCION|LIBRO|VOLUMEN)\b",
    r"^(Primera|Segunda|Tercera|Cuarta|Quinta|Sexta|Septima|Octava|Novena|Decima)\s+(Parte|Seccion|Libro|Volumen)\b",
    # Frases que empiezan con "El/La" + sustantivo común
    r"^(El|La)\s+(reloj|tiempo|dia|día|noche|mundo|sol|luna|viento|aire|cielo|mar|agua|luz)\s",
    # Frases con "Un/Una" + sustantivo genérico de persona
    r"^(Un|Una)\s+(hombre|mujer|nino|niña|niño|persona|anciano|anciana|joven|senor|señor|senora|señora)\s",
    # Palabras sueltas en MAYÚSCULAS que son metadatos
    r"^(DETECCION|DETECCIÓN|CAPITULOS|CAPÍTULOS|ESTRUCTURA|ORIGENES|ORÍGENES|URGENTE|REVELACIONES)\b",
    r"^(PERSONAJES?|FORMATOS?|PARTES?|TIMELINE|EVENTOS?)\s*[:,]?\s*\(?",
    # Capítulo + número escrito
    r"^Cap[ií]tulo\s+(Uno|Dos|Tres|Cuatro|Cinco|Seis|Siete|Ocho|Nueve|Diez)\b",
    r"^CAPITULO\s+(UNO|DOS|TRES|CUATRO|CINCO|SEIS|SIETE|OCHO|NUEVE|DIEZ)\b",
    # Números romanos solos como título (VII., VIII., etc.)
    r"^[IVXLC]+\.\s*",
    # ===== NUEVOS PATRONES ITERACIÓN 4: Frases genéricas =====
    # Lista común de adjetivos genéricos para reutilizar
    # Patrón: palabra_indefinida + adjetivo_generico
    #
    # Frases indefinidas con "algo" + adjetivo (no son entidades específicas)
    r"^algo\s+(extraño|raro|diferente|especial|terrible|horrible|malo|bueno|nuevo|viejo|grande|pequeño|oscuro|claro|misterioso|sospechoso|inquietante|inesperado|sorprendente)\b",
    # Frases con "lo" + adjetivo sustantivado (no son entidades)
    r"^lo\s+(extraño|raro|peor|mejor|malo|bueno|importante|difícil|fácil|curioso|interesante|terrible|horrible|posible|imposible|increíble|absurdo|lógico|normal|extraño)\b",
    # Frases con "eso/esto/aquello" + adjetivo (pronombres demostrativos genéricos)
    r"^(eso|esto|aquello)\s+(extraño|raro|terrible|horrible|malo|bueno|nuevo|viejo|diferente|especial)\b",
    # Frases con "nada/todo" + adjetivo
    r"^(nada|todo)\s+(extraño|especial|nuevo|malo|bueno|diferente|importante)\b",
    # Frases genéricas con adjetivo + sustantivo común
    r"^(el|la|un|una)\s+(mismo|misma|propio|propia|otro|otra|cierto|cierta|algún|alguna|ningún|ninguna)\s+(hombre|mujer|persona|cosa|lugar|momento|día|noche)\b",
    # Frases con "cualquier" (indefinido genérico)
    r"^cualquier\s+(cosa|persona|lugar|momento|día|forma|manera|caso)\b",
    # Sustantivos abstractos solos muy comunes (con o sin artículo)
    r"^((el|la)\s+)?(esperanza|verdad|mentira|realidad|vida|muerte|amor|odio|miedo|alegría|tristeza|soledad|felicidad|desgracia)\s*$",
]


# Patrones que deben ser CASE-SENSITIVE (no usan IGNORECASE)
# Estos patrones dependen de mayúsculas/minúsculas para funcionar
CASE_SENSITIVE_NOT_ENTITY_PATTERNS = [
    # Texto largo completamente en MAYÚSCULAS (probablemente título, mínimo 15 chars)
    # Este patrón DEBE ser case-sensitive porque solo debe coincidir con texto en mayúsculas
    # Excluye nombres cortos como "MARÍA" o "JUAN"
    r"^[A-ZÁÉÍÓÚÑÜ\s\-:]{15,}$",
]


# =============================================================================
# Validador principal
# =============================================================================


class EntityValidator:
    """
    Validador de entidades multi-capa.

    Combina validación LLM (si disponible) con heurísticas robustas
    y feedback del usuario para filtrar falsos positivos.

    Uso:
        validator = EntityValidator()
        result = validator.validate(entities, full_text, project_id)
        for entity in result.valid_entities:
            print(f"✓ {entity.text}")
        for entity in result.rejected_entities:
            print(f"✗ {entity.text} - {result.scores[entity.text].rejection_reason}")
    """

    def __init__(
        self,
        config: EntityValidatorConfig | None = None,
        db=None,
    ):
        """
        Inicializa el validador.

        Args:
            config: Configuración del validador
            db: Base de datos para feedback persistente (opcional)
        """
        self.config = config or EntityValidatorConfig()
        self.db = db

        # LLM client (lazy loading)
        self._llm_client = None
        self._llm_checked = False

        # spaCy model (lazy loading para análisis morfológico)
        self._nlp = None
        self._nlp_checked = False

        # Cache de entidades rechazadas por proyecto
        self._rejected_cache: dict[int, set[str]] = {}
        self._cache_lock = threading.Lock()

        # Compilar patrones (case-insensitive)
        self._not_entity_patterns = [re.compile(p, re.IGNORECASE) for p in NOT_ENTITY_PATTERNS]

        # Compilar patrones case-sensitive (para mayúsculas literales)
        self._case_sensitive_patterns = [re.compile(p) for p in CASE_SENSITIVE_NOT_ENTITY_PATTERNS]

        logger.debug("EntityValidator inicializado")

    def validate(
        self,
        entities: list,  # list[ExtractedEntity]
        full_text: str,
        project_id: int | None = None,
    ) -> ValidationResult:
        """
        Valida un conjunto de entidades.

        Args:
            entities: Lista de entidades a validar
            full_text: Texto completo del documento (para contexto)
            project_id: ID del proyecto (para feedback persistente)

        Returns:
            ValidationResult con entidades válidas y rechazadas
        """
        if not entities:
            return ValidationResult(valid_entities=[], rejected_entities=[])

        # Preparar análisis de frecuencia
        entity_texts = [e.text for e in entities]
        frequency = Counter(entity_texts)

        # Cargar entidades rechazadas del proyecto
        rejected_by_user = self._get_rejected_entities(project_id) if project_id else set()

        # Calcular scores heurísticos para cada instancia de entidad
        # Usamos (text, start_char) como key para distinguir instancias en diferentes posiciones
        scores: dict[str, EntityScore] = {}
        instance_scores: dict[tuple, EntityScore] = {}  # (text, start_char) -> score

        for entity in entities:
            instance_key = (entity.text, entity.start_char)
            score = self._calculate_heuristic_score(
                entity, full_text, frequency, rejected_by_user, project_id
            )
            instance_scores[instance_key] = score
            # También guardar por texto para compatibilidad (usar la mejor puntuación)
            if entity.text not in scores or score.total_score > scores[entity.text].total_score:
                scores[entity.text] = score

        # Intentar validación LLM si está habilitada
        llm_available = False
        if self.config.llm_validation_enabled:
            llm_available = self._validate_with_llm(entities, full_text, scores)

        # Clasificar entidades usando scores por instancia
        valid = []
        rejected = []

        for entity in entities:
            instance_key = (entity.text, entity.start_char)
            entity_score = instance_scores.get(instance_key)
            if entity_score and entity_score.is_valid:
                valid.append(entity)
            else:
                rejected.append(entity)

        # Deduplicar válidas (por texto)
        seen_texts = set()
        unique_valid = []
        for entity in valid:
            if entity.text not in seen_texts:
                unique_valid.append(entity)
                seen_texts.add(entity.text)

        result = ValidationResult(
            valid_entities=unique_valid,
            rejected_entities=rejected,
            scores=scores,
            validation_method="combined" if llm_available else "heuristic",
            llm_available=llm_available,
        )

        logger.info(
            f"Validación completada: {len(unique_valid)} válidas, "
            f"{len(rejected)} rechazadas (método: {result.validation_method})"
        )

        return result

    def _calculate_heuristic_score(
        self,
        entity,  # ExtractedEntity
        full_text: str,
        frequency: Counter,
        rejected_by_user: set[str],
        project_id: int | None = None,
    ) -> EntityScore:
        """
        Calcula el score heurístico de una entidad.

        Combina múltiples señales para determinar la probabilidad
        de que sea una entidad válida.
        """
        text = entity.text
        text_lower = text.lower().strip()
        words = text.split()

        # ===== FILTRO 0: Marcadores discursivos temporales =====
        if text_lower in DISCOURSE_MARKERS:
            return EntityScore(
                text=text,
                total_score=0.0,
                is_valid=False,
                validation_method="discourse_marker",
                rejection_reason=f"Marcador discursivo/temporal: '{text}'",
            )

        # ===== NUEVO: Usar sistema híbrido de filtros de 3 niveles =====
        entity_type = entity.label.value if hasattr(entity, "label") else None
        try:
            filter_repo = get_filter_repository()
            filter_decision = filter_repo.should_filter_entity(
                entity_name=text, entity_type=entity_type, project_id=project_id
            )

            # Si hay force_include a nivel proyecto, aceptar directamente
            if filter_decision.level == "project" and not filter_decision.should_filter:
                return EntityScore(
                    text=text,
                    total_score=1.0,
                    is_valid=True,
                    validation_method="project_force_include",
                    rejection_reason=None,
                )

            # Si debe filtrarse por cualquier nivel, rechazar
            if filter_decision.should_filter:
                return EntityScore(
                    text=text,
                    total_score=0.0,
                    is_valid=False,
                    validation_method=f"{filter_decision.level}_filtered",
                    rejection_reason=filter_decision.reason,
                )
        except Exception as e:
            # Si falla el nuevo sistema, usar el antiguo
            logger.debug(f"Error en sistema de filtros híbrido: {e}")

        # Fallback: Verificar si fue rechazada por el usuario (sistema antiguo)
        if text_lower in rejected_by_user or text in rejected_by_user:
            return EntityScore(
                text=text,
                total_score=0.0,
                is_valid=False,
                validation_method="user_rejected",
                rejection_reason="Rechazada por el usuario anteriormente",
            )

        # ===== NUEVO: Verificar si está en zona no-narrativa =====
        # Obtener la línea donde aparece la entidad
        line, is_line_start = get_line_for_position(full_text, entity.start_char)
        if is_non_narrative_line(line):
            return EntityScore(
                text=text,
                total_score=0.0,
                is_valid=False,
                validation_method="zone_rejected",
                rejection_reason=f"En zona no-narrativa (título/metadato): '{line[:50]}...' "
                if len(line) > 50
                else f"En zona no-narrativa: '{line}'",
            )

        # Verificar patrones que indican que NO es entidad (case-insensitive)
        for pattern in self._not_entity_patterns:
            if pattern.search(text):
                return EntityScore(
                    text=text,
                    total_score=0.0,
                    is_valid=False,
                    validation_method="pattern_rejected",
                    rejection_reason="Coincide con patrón de no-entidad",
                )

        # Verificar patrones case-sensitive (para texto en mayúsculas)
        for pattern in self._case_sensitive_patterns:
            if pattern.search(text):
                return EntityScore(
                    text=text,
                    total_score=0.0,
                    is_valid=False,
                    validation_method="pattern_rejected",
                    rejection_reason="Coincide con patrón de no-entidad (mayúsculas)",
                )

        # Calcular scores individuales
        scores = EntityScore(text=text, total_score=0.0, is_valid=False)

        # 1. Frecuencia (aparece más de una vez)
        freq = frequency.get(text, 1)
        if freq >= 3:
            scores.frequency_score = 1.0
        elif freq >= 2:
            scores.frequency_score = 0.7
        else:
            scores.frequency_score = 0.3

        # 2. Capitalización consistente
        # Buscar todas las ocurrencias en el texto y verificar capitalización
        capitalization_consistent = self._check_capitalization_consistency(text, full_text)
        scores.capitalization_score = 1.0 if capitalization_consistent else 0.3

        # 3. Posición (no es inicio de oración la mayoría de veces)
        not_sentence_start = self._check_not_sentence_start(text, full_text)
        scores.position_score = 1.0 if not_sentence_start else 0.4

        # 4. Longitud
        if len(text) >= 5:
            scores.length_score = 1.0
        elif len(text) >= 3:
            scores.length_score = 0.7
        else:
            scores.length_score = 0.3

        # 5. No empieza con artículo
        first_word = words[0].lower() if words else ""
        if first_word in {"el", "la", "los", "las", "un", "una", "unos", "unas"}:
            scores.article_score = 0.2  # Penalización fuerte
        else:
            scores.article_score = 1.0

        # 6. No es palabra común
        if text_lower in COMMON_SPANISH_WORDS:
            scores.common_word_score = 0.0
        elif any(w.lower() in COMMON_SPANISH_WORDS for w in words if len(w) > 2):
            # Contiene alguna palabra común pero tiene otras
            scores.common_word_score = 0.5
        else:
            scores.common_word_score = 1.0

        # 7. Análisis morfológico (detectar verbos)
        morphology_score, morphology_reason = self._calculate_morphology_score(entity, full_text)
        scores.morphology_score = morphology_score

        # 8. Verificar si aparece mayoritariamente en zonas no-narrativas
        zone_penalty = self._check_zone_distribution(text, full_text)
        if zone_penalty < 0.5:
            # Penalizar si aparece mayoritariamente en encabezados/metadatos
            scores.total_score *= zone_penalty
            if zone_penalty < 0.3:
                scores.rejection_reason = "Aparece principalmente en títulos/metadatos"

        # Calcular score total ponderado
        cfg = self.config
        scores.total_score = (
            scores.frequency_score * cfg.weight_frequency
            + scores.capitalization_score * cfg.weight_capitalization
            + scores.position_score * cfg.weight_position
            + scores.length_score * cfg.weight_length
            + scores.article_score * cfg.weight_no_article
            + scores.common_word_score * cfg.weight_not_common
            + scores.morphology_score * cfg.weight_morphology
        )

        # Determinar validez
        scores.is_valid = scores.total_score >= cfg.min_confidence_threshold
        scores.validation_method = "heuristic"

        if not scores.is_valid:
            # Determinar razón de rechazo (priorizar morphology)
            if scores.morphology_score < 0.5 and morphology_reason:
                scores.rejection_reason = morphology_reason
            elif scores.common_word_score == 0.0:
                scores.rejection_reason = "Es una palabra común del español"
            elif scores.article_score < 0.5:
                scores.rejection_reason = "Empieza con artículo (probablemente descripción)"
            elif scores.capitalization_score < 0.5:
                scores.rejection_reason = "Capitalización inconsistente"
            elif scores.frequency_score < 0.5:
                scores.rejection_reason = "Aparece solo una vez (baja confianza)"
            else:
                scores.rejection_reason = f"Score bajo ({scores.total_score:.2f})"

        return scores

    def _check_zone_distribution(self, entity_text: str, full_text: str) -> float:
        """
        Verifica en qué proporción de apariciones la entidad está en zona narrativa.

        Args:
            entity_text: Texto de la entidad
            full_text: Texto completo

        Returns:
            Proporción de apariciones en zona narrativa (0.0-1.0)
            1.0 = todas en narrativa, 0.0 = todas en no-narrativa
        """
        import re

        pattern = r"\b" + re.escape(entity_text) + r"\b"
        matches = list(re.finditer(pattern, full_text, re.IGNORECASE))

        if len(matches) == 0:
            return 1.0  # No encontrada, asumir válida

        narrative_count = 0
        for match in matches:
            line, _ = get_line_for_position(full_text, match.start())
            if not is_non_narrative_line(line):
                narrative_count += 1

        return narrative_count / len(matches)

    def _check_capitalization_consistency(self, entity_text: str, full_text: str) -> bool:
        """
        Verifica si la entidad aparece consistentemente capitalizada.

        Una entidad real (nombre propio) debería aparecer casi siempre
        con la primera letra en mayúscula.
        """
        import re

        # Buscar todas las ocurrencias (case insensitive)
        pattern = r"\b" + re.escape(entity_text) + r"\b"
        matches = list(re.finditer(pattern, full_text, re.IGNORECASE))

        if len(matches) < 2:
            # Si solo aparece una vez, asumir válido
            return True

        # Contar cuántas veces aparece capitalizada
        capitalized_count = 0
        for match in matches:
            matched_text = match.group()
            if matched_text and matched_text[0].isupper():
                capitalized_count += 1

        # Si más del 70% están capitalizadas, es consistente
        return (capitalized_count / len(matches)) >= 0.7

    def _check_not_sentence_start(self, entity_text: str, full_text: str) -> bool:
        """
        Verifica si la entidad aparece mayormente NO al inicio de oración.

        Las palabras al inicio de oración siempre se capitalizan en español,
        así que si una "entidad" solo aparece al inicio de oraciones,
        probablemente no es un nombre propio.
        """
        import re

        # Buscar ocurrencias
        pattern = r"\b" + re.escape(entity_text) + r"\b"
        matches = list(re.finditer(pattern, full_text, re.IGNORECASE))

        if len(matches) < 2:
            return True

        # Verificar cuántas están al inicio de oración
        sentence_start_count = 0
        for match in matches:
            pos = match.start()
            # Verificar si está al inicio o después de . ! ? \n
            if pos == 0:
                sentence_start_count += 1
            elif pos > 0:
                # Buscar hacia atrás el caracter no-espacio más cercano
                before = full_text[:pos].rstrip()
                if before and before[-1] in ".!?¿¡\n":
                    sentence_start_count += 1

        # Si menos del 50% están al inicio de oración, es válido
        return (sentence_start_count / len(matches)) < 0.5

    def _validate_with_llm(
        self,
        entities: list,
        full_text: str,
        scores: dict[str, EntityScore],
    ) -> bool:
        """
        Valida entidades usando LLM.

        El LLM revisa las entidades en contexto y determina cuáles
        son realmente nombres propios vs falsos positivos.

        Returns:
            True si se usó LLM, False si no está disponible
        """
        llm = self._get_llm_client()
        if not llm:
            return False

        # Agrupar entidades únicas con score borderline para validar
        # (las muy buenas y muy malas ya están decididas por heurísticas)
        entities_to_validate: list[Any] = []
        for entity in entities:
            score = scores.get(entity.text)
            if score and 0.3 <= score.total_score <= 0.7:
                if entity.text not in [e.text for e in entities_to_validate]:
                    entities_to_validate.append(entity)

        if not entities_to_validate:
            logger.debug("No hay entidades borderline para validar con LLM")
            return True  # LLM disponible, pero no necesario

        # Limitar batch
        entities_to_validate = entities_to_validate[: self.config.llm_batch_size]

        # Extraer contexto para cada entidad
        entity_contexts = []
        for entity in entities_to_validate:
            context = self._extract_context(entity, full_text)
            entity_contexts.append(
                {
                    "text": entity.text,
                    "type": entity.label.value if hasattr(entity, "label") else "UNKNOWN",
                    "context": context,
                }
            )

        from ..llm.sanitization import sanitize_for_prompt

        # Sanitizar contextos del manuscrito antes de enviarlo al LLM (A-10)
        entities_json = "\n".join(
            [
                f'  - "{sanitize_for_prompt(ec["text"], max_length=100)}" (detectado como {ec["type"]}): "{sanitize_for_prompt(ec["context"], max_length=200)}"'
                for ec in entity_contexts
            ]
        )

        prompt = f"""Analiza estas posibles entidades extraídas de un texto narrativo en español.
Para cada una, determina si es realmente una ENTIDAD NOMBRADA válida o un falso positivo.

ENTIDADES A VALIDAR:
{entities_json}

CRITERIOS:
- VÁLIDO: Nombres propios de personas, lugares, organizaciones (Juan, Madrid, Acme Corp)
- INVÁLIDO:
  * Frases de diálogo ("¿Quién eres?", "Hola María")
  * Descripciones genéricas ("el hombre alto", "la mujer rubia")
  * Sustantivos comunes ("las endorfinas", "el coche")
  * Expresiones temporales ("ayer", "esta mañana")
  * Pronombres y artículos

Responde SOLO con JSON:
{{"validations": [
  {{"text": "...", "is_valid": true/false, "reason": "breve explicación"}}
]}}

JSON:"""

        try:
            response = llm.complete(
                prompt,
                system="Eres un experto en análisis lingüístico de textos narrativos en español. Validas entidades nombradas con precisión.",
                temperature=0.1,
                max_tokens=1000,
            )

            if not response:
                return False

            # Parsear respuesta
            validations = self._parse_llm_validation_response(response)

            # Actualizar scores con validación LLM
            for validation in validations:
                text = validation.get("text", "")
                is_valid = validation.get("is_valid", True)
                reason = validation.get("reason", "")

                if text in scores:
                    score = scores[text]
                    score.llm_score = 1.0 if is_valid else 0.0
                    score.validation_method = "combined"

                    # LLM tiene voto de calidad
                    if is_valid:
                        score.total_score = min(1.0, score.total_score + 0.3)
                        score.is_valid = True
                    else:
                        score.total_score = max(0.0, score.total_score - 0.3)
                        score.is_valid = False
                        score.rejection_reason = f"LLM: {reason}"

            logger.debug(f"LLM validó {len(validations)} entidades")
            return True

        except Exception as e:
            logger.warning(f"Error en validación LLM: {e}")
            return False

    def _extract_context(self, entity, full_text: str, context_chars: int = 100) -> str:
        """Extrae contexto alrededor de una entidad."""
        start = max(0, entity.start_char - context_chars)
        end = min(len(full_text), entity.end_char + context_chars)

        context = full_text[start:end]

        # Limpiar y truncar
        context = context.replace("\n", " ").strip()
        if len(context) > 200:
            context = context[:200] + "..."

        return context

    def _parse_llm_validation_response(self, response: str) -> list[dict[str, Any]]:
        """Parsea la respuesta JSON del LLM."""
        import json

        try:
            cleaned = response.strip()

            # Remover bloques markdown
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                cleaned = "\n".join(lines)

            # Encontrar JSON
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1

            if start != -1 and end > start:
                cleaned = cleaned[start:end]

            data = json.loads(cleaned)
            if not isinstance(data, dict):
                return []

            validations = data.get("validations", [])
            if not isinstance(validations, list):
                return []

            parsed_validations: list[dict[str, Any]] = []
            for item in validations:
                if isinstance(item, dict):
                    parsed_validations.append({str(k): v for k, v in item.items()})
            return parsed_validations

        except json.JSONDecodeError as e:
            logger.debug(f"Error parseando JSON de validación LLM: {e}")
            return []

    def _get_llm_client(self):
        """Obtiene el cliente LLM (lazy loading)."""
        if self._llm_checked:
            return self._llm_client

        self._llm_checked = True

        try:
            from ..llm.client import get_llm_client

            client = get_llm_client()
            if client and client.is_available:
                self._llm_client = client
                logger.debug(f"LLM disponible para validación: {client.model_name}")
            else:
                self._llm_client = None
        except Exception as e:
            logger.debug(f"LLM no disponible para validación: {e}")
            self._llm_client = None

        return self._llm_client

    def _get_nlp(self):
        """Obtiene el modelo spaCy para análisis morfológico (lazy loading)."""
        if self._nlp_checked:
            return self._nlp

        self._nlp_checked = True

        try:
            from .spacy_gpu import load_spacy_model

            self._nlp = load_spacy_model()
            logger.debug("spaCy disponible para análisis morfológico")
        except Exception as e:
            logger.debug(f"spaCy no disponible para análisis morfológico: {e}")
            self._nlp = None

        return self._nlp

    def _check_is_verb_in_context(self, entity_text: str, context: str) -> tuple[bool, float]:
        """
        Verifica si el texto de la entidad es un verbo usando POS-tagging de spaCy.

        Analiza el contexto completo para determinar si la palabra es un verbo
        conjugado, lo cual indicaría un falso positivo.

        Args:
            entity_text: Texto de la entidad a verificar
            context: Contexto donde aparece la entidad (oración o fragmento)

        Returns:
            Tupla (is_verb, confidence):
            - is_verb: True si parece ser un verbo
            - confidence: 0.0-1.0, qué tan seguro estamos de que es verbo
        """
        nlp = self._get_nlp()
        if not nlp:
            return False, 0.0

        try:
            # Analizar el contexto con spaCy
            doc = nlp(context)

            # Buscar la entidad en el documento analizado
            entity_lower = entity_text.lower().strip()
            entity_words = entity_lower.split()

            for token in doc:
                # Comparar con el texto de la entidad
                token_text = token.text.lower().strip()

                # Verificación simple: token individual
                if token_text == entity_lower:
                    if token.pos_ == "VERB":
                        # Es un verbo conjugado
                        return True, 0.9
                    elif token.pos_ == "AUX":
                        # Es un verbo auxiliar
                        return True, 0.8

                # Verificación para entidades de múltiples palabras
                if len(entity_words) > 1 and token_text == entity_words[0]:
                    # Verificar si la primera palabra es verbo
                    if token.pos_ in ("VERB", "AUX"):
                        return True, 0.7

            # No encontrado como verbo
            return False, 0.0

        except Exception as e:
            logger.debug(f"Error en análisis morfológico: {e}")
            return False, 0.0

    def _calculate_morphology_score(
        self,
        entity,
        full_text: str,
    ) -> tuple[float, str | None]:
        """
        Calcula el score morfológico de una entidad.

        Penaliza entidades que parecen verbos conjugados según spaCy.

        Args:
            entity: ExtractedEntity a evaluar
            full_text: Texto completo del documento

        Returns:
            Tupla (score, reason):
            - score: 1.0 si NO es verbo, 0.0-0.3 si ES verbo
            - reason: Razón de penalización si aplica
        """
        if not self.config.morphology_check_enabled:
            return 1.0, None

        # Extraer contexto alrededor de la entidad
        context = self._extract_context(entity, full_text, context_chars=150)

        # Verificar si es verbo
        is_verb, confidence = self._check_is_verb_in_context(entity.text, context)

        if is_verb:
            # Penalizar fuertemente
            score = 0.1 if confidence > 0.8 else 0.3
            return score, f"Detectado como verbo (confianza: {confidence:.0%})"

        # Verificación adicional: terminaciones verbales típicas del español
        text_lower = entity.text.lower().strip()

        # Terminaciones de verbos conjugados en español
        verb_endings = {
            # Presente indicativo
            "o",
            "as",
            "a",
            "amos",
            "áis",
            "an",
            "es",
            "e",
            "emos",
            "éis",
            "en",
            "ís",
            "imos",
            # Pretérito
            "é",
            "aste",
            "ó",
            "asteis",
            "aron",
            "í",
            "iste",
            "ió",
            "isteis",
            "ieron",
            # Imperfecto
            "aba",
            "abas",
            "ábamos",
            "abais",
            "aban",
            "ía",
            "ías",
            "íamos",
            "íais",
            "ían",
            # Futuro
            "aré",
            "arás",
            "ará",
            "aremos",
            "aréis",
            "arán",
            "eré",
            "erás",
            "erá",
            "eremos",
            "eréis",
            "erán",
            "iré",
            "irás",
            "irá",
            "iremos",
            "iréis",
            "irán",
            # Condicional
            "aría",
            "arías",
            "aríamos",
            "aríais",
            "arían",
            "ería",
            "erías",
            "eríamos",
            "eríais",
            "erían",
            "iría",
            "irías",
            "iríamos",
            "iríais",
            "irían",
            # Subjuntivo
            "ara",
            "aras",
            "áramos",
            "arais",
            "aran",
            "iera",
            "ieras",
            "iéramos",
            "ierais",
            "ieran",
            "ase",
            "ases",
            "ásemos",
            "aseis",
            "asen",
            "iese",
            "ieses",
            "iésemos",
            "ieseis",
            "iesen",
        }

        # Verificar si termina como verbo conjugado (pero no es nombre conocido)
        for ending in verb_endings:
            if (
                len(ending) >= 3
                and text_lower.endswith(ending)
                and len(text_lower) > len(ending) + 2
            ):
                # Podría ser verbo, penalizar ligeramente
                return 0.6, f"Termina en '{ending}' (posible verbo)"

        return 1.0, None

    def _get_rejected_entities(self, project_id: int) -> set[str]:
        """
        Obtiene las entidades rechazadas por el usuario para un proyecto.

        Args:
            project_id: ID del proyecto

        Returns:
            Set de textos de entidades rechazadas (lowercase)
        """
        with self._cache_lock:
            if project_id in self._rejected_cache:
                return self._rejected_cache[project_id]

        # Cargar de la base de datos
        rejected = set()

        if self.db:
            try:
                rows = self.db.fetchall(
                    """
                    SELECT entity_text FROM rejected_entities
                    WHERE project_id = ?
                    """,
                    (project_id,),
                )
                rejected = {row["entity_text"].lower() for row in rows}
            except Exception as e:
                logger.debug(f"Error cargando entidades rechazadas: {e}")

        with self._cache_lock:
            self._rejected_cache[project_id] = rejected

        return rejected

    def reject_entity(self, project_id: int, entity_text: str) -> bool:
        """
        Marca una entidad como rechazada por el usuario.

        Args:
            project_id: ID del proyecto
            entity_text: Texto de la entidad a rechazar

        Returns:
            True si se guardó correctamente
        """
        entity_lower = entity_text.lower().strip()

        # Actualizar cache
        with self._cache_lock:
            if project_id not in self._rejected_cache:
                self._rejected_cache[project_id] = set()
            self._rejected_cache[project_id].add(entity_lower)

        # Guardar en DB
        if self.db:
            try:
                with self.db.connection() as conn:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO rejected_entities (project_id, entity_text)
                        VALUES (?, ?)
                        """,
                        (project_id, entity_lower),
                    )
                logger.debug(f"Entidad rechazada guardada: '{entity_text}' (proyecto {project_id})")
                return True
            except Exception as e:
                logger.warning(f"Error guardando entidad rechazada: {e}")
                return False

        return True

    def unreject_entity(self, project_id: int, entity_text: str) -> bool:
        """
        Quita una entidad de la lista de rechazadas.

        Args:
            project_id: ID del proyecto
            entity_text: Texto de la entidad

        Returns:
            True si se quitó correctamente
        """
        entity_lower = entity_text.lower().strip()

        # Actualizar cache
        with self._cache_lock:
            if project_id in self._rejected_cache:
                self._rejected_cache[project_id].discard(entity_lower)

        # Eliminar de DB
        if self.db:
            try:
                with self.db.connection() as conn:
                    conn.execute(
                        """
                        DELETE FROM rejected_entities
                        WHERE project_id = ? AND entity_text = ?
                        """,
                        (project_id, entity_lower),
                    )
                return True
            except Exception as e:
                logger.warning(f"Error eliminando entidad rechazada: {e}")
                return False

        return True

    def clear_cache(self, project_id: int | None = None) -> None:
        """
        Limpia el cache de entidades rechazadas.

        Args:
            project_id: Si se especifica, solo limpia ese proyecto
        """
        with self._cache_lock:
            if project_id:
                self._rejected_cache.pop(project_id, None)
            else:
                self._rejected_cache.clear()


# =============================================================================
# Singleton y funciones de conveniencia
# =============================================================================

_validator_lock = threading.Lock()
_validator: EntityValidator | None = None


def get_entity_validator(db=None) -> EntityValidator:
    """
    Obtiene el validador de entidades singleton.

    Args:
        db: Base de datos para feedback persistente

    Returns:
        Instancia de EntityValidator
    """
    global _validator

    if _validator is None:
        with _validator_lock:
            if _validator is None:
                _validator = EntityValidator(db=db)

    return _validator


def validate_entities(
    entities: list,
    full_text: str,
    project_id: int | None = None,
) -> ValidationResult:
    """
    Valida un conjunto de entidades (atajo).

    Args:
        entities: Lista de ExtractedEntity
        full_text: Texto completo del documento
        project_id: ID del proyecto (opcional, para feedback)

    Returns:
        ValidationResult
    """
    return get_entity_validator().validate(entities, full_text, project_id)
