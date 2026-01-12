"""
Verificador de Consistencia de Atributos.

Detecta cuando una entidad tiene valores contradictorios para
el mismo atributo en diferentes partes del texto.

Ejemplo: "ojos verdes" en cap. 2 vs "ojos azules" en cap. 5

Estrategias de detección:
1. Antónimos conocidos (verde/azul, alto/bajo)
2. Similitud semántica con embeddings
3. Reglas específicas por tipo de atributo
"""

import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..core.result import Result
from ..core.errors import NarrativeError, ErrorSeverity
from ..nlp.attributes import (
    ExtractedAttribute,
    AttributeKey,
    AttributeCategory,
)

logger = logging.getLogger(__name__)


class InconsistencyType(Enum):
    """Tipos de inconsistencia detectada."""

    ANTONYM = "antonym"  # Valores opuestos conocidos
    SEMANTIC_DIFF = "semantic_diff"  # Diferencia semántica alta
    VALUE_CHANGE = "value_change"  # Cambio de valor numérico
    CONTRADICTORY = "contradictory"  # Contradicción explícita


@dataclass
class AttributeInconsistency:
    """
    Representa una inconsistencia detectada entre atributos.

    Attributes:
        entity_name: Nombre de la entidad
        entity_id: ID de la entidad en la base de datos
        attribute_key: Clave del atributo inconsistente
        value1: Primer valor encontrado
        value1_chapter: Capítulo del primer valor
        value1_excerpt: Extracto del texto
        value2: Segundo valor encontrado
        value2_chapter: Capítulo del segundo valor
        value2_excerpt: Extracto del texto
        inconsistency_type: Tipo de inconsistencia
        confidence: Confianza de que sea inconsistencia real (0.0-1.0)
        explanation: Explicación legible
    """

    entity_name: str
    entity_id: int
    attribute_key: AttributeKey
    value1: str
    value1_chapter: Optional[int]
    value1_excerpt: str
    value2: str
    value2_chapter: Optional[int]
    value2_excerpt: str
    inconsistency_type: InconsistencyType
    confidence: float
    explanation: str

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización."""
        return {
            "entity_name": self.entity_name,
            "entity_id": self.entity_id,
            "attribute_key": self.attribute_key.value,
            "value1": self.value1,
            "value1_chapter": self.value1_chapter,
            "value1_excerpt": self.value1_excerpt,
            "value2": self.value2,
            "value2_chapter": self.value2_chapter,
            "value2_excerpt": self.value2_excerpt,
            "inconsistency_type": self.inconsistency_type.value,
            "confidence": self.confidence,
            "explanation": self.explanation,
        }


@dataclass
class ConsistencyCheckError(NarrativeError):
    """Error durante la verificación de consistencia."""

    original_error: str = ""
    message: str = ""
    severity: ErrorSeverity = ErrorSeverity.RECOVERABLE
    user_message: Optional[str] = None

    def __post_init__(self):
        if not self.message:
            self.message = f"Consistency check error: {self.original_error}"
        if not self.user_message:
            self.user_message = (
                "Error al verificar consistencia. "
                "Se continuará con los resultados parciales."
            )
        super().__post_init__()


# =============================================================================
# Diccionarios de antónimos y relaciones
# =============================================================================

# =============================================================================
# Lematización (normalización morfológica)
# =============================================================================

# Fallback manual para cuando spaCy no está disponible
# Solo los casos más comunes - spaCy es preferible
_FALLBACK_LEMMAS: dict[str, str] = {
    # Build - femeninos y plurales comunes
    "alta": "alto", "altas": "alto", "altos": "alto",
    "baja": "bajo", "bajas": "bajo", "bajos": "bajo",
    "bajita": "bajito", "bajitas": "bajito", "bajitos": "bajito",
    # Colores - plurales
    "verdes": "verde", "azules": "azul", "marrones": "marrón",
    "negros": "negro", "negras": "negro",
    # Personalidad
    "valientes": "valiente", "cobardes": "cobarde",
}

# Cache de lemas para evitar recalcular
_lemma_cache: dict[str, str] = {}
_spacy_nlp = None
_spacy_checked = False


def _get_spacy_for_lemmas():
    """Obtiene modelo spaCy para lematización (lazy loading)."""
    global _spacy_nlp, _spacy_checked
    if not _spacy_checked:
        _spacy_checked = True
        try:
            from ..nlp.spacy_gpu import load_spacy_model
            _spacy_nlp = load_spacy_model()
            logger.debug("spaCy cargado para lematización")
        except Exception as e:
            logger.debug(f"spaCy no disponible para lematización: {e}")
    return _spacy_nlp


def _normalize_value(value: str) -> str:
    """
    Normaliza un valor a su lema (forma canónica).

    Usa spaCy para lematización morfológica si está disponible.
    Fallback a diccionario manual si no.

    Args:
        value: Valor a normalizar (ej: "verdes", "alta")

    Returns:
        Lema normalizado (ej: "verde", "alto")
    """
    v = value.lower().strip()

    # Check cache first
    if v in _lemma_cache:
        return _lemma_cache[v]

    # Try spaCy lemmatization
    nlp = _get_spacy_for_lemmas()
    if nlp:
        try:
            doc = nlp(v)
            if doc and len(doc) > 0:
                lemma = doc[0].lemma_.lower()
                _lemma_cache[v] = lemma
                return lemma
        except Exception as e:
            logger.debug(f"Error en lematización spaCy: {e}")

    # Fallback to manual dictionary
    lemma = _FALLBACK_LEMMAS.get(v, v)
    _lemma_cache[v] = lemma
    return lemma


def reset_lemma_cache() -> None:
    """Resetea el cache de lemas y estado de spaCy (útil para tests)."""
    global _lemma_cache, _spacy_nlp, _spacy_checked
    _lemma_cache = {}
    _spacy_nlp = None
    _spacy_checked = False


# =============================================================================
# Diccionarios de sinónimos (para evitar falsos positivos)
# =============================================================================

# Sinónimos de colores (pueden coexistir o referirse a lo mismo)
COLOR_SYNONYMS: dict[str, set[str]] = {
    "castaño": {"marrón", "pardo", "chocolate"},
    "marrón": {"castaño", "pardo", "chocolate"},
    "negro": {"azabache", "oscuro", "moreno"},
    "blanco": {"cano", "canoso", "plateado", "gris"},
    "canoso": {"cano", "blanco", "plateado", "gris"},
    "rubio": {"dorado", "pajizo", "claro"},
    "rojo": {"pelirrojo", "cobrizo", "bermejo"},
    "pelirrojo": {"rojo", "cobrizo", "bermejo"},
    "gris": {"plateado", "ceniza", "canoso"},
    "miel": {"ámbar", "dorado", "avellana"},
    "ámbar": {"miel", "dorado", "avellana"},
    "avellana": {"miel", "ámbar", "castaño"},
}

# Sinónimos de constitución física
BUILD_SYNONYMS: dict[str, set[str]] = {
    "alto": {"grande", "esbelto", "larguirucho"},
    "bajo": {"pequeño", "bajito", "menudo", "chico"},
    "bajito": {"bajo", "pequeño", "menudo"},
    "delgado": {"flaco", "esbelto", "fino", "delgadísimo"},
    "flaco": {"delgado", "esbelto", "escuálido", "enjuto"},
    "gordo": {"obeso", "rollizo", "corpulento", "rechoncho", "gordito"},
    "corpulento": {"fornido", "robusto", "grande", "fuerte"},
    "robusto": {"corpulento", "fornido", "fuerte", "atlético"},
    "fornido": {"corpulento", "robusto", "fuerte", "musculoso"},
    "musculoso": {"atlético", "fornido", "fuerte"},
    "esbelto": {"delgado", "alto", "estilizado"},
}

# Sinónimos de personalidad
PERSONALITY_SYNONYMS: dict[str, set[str]] = {
    "valiente": {"audaz", "intrépido", "osado", "bravo"},
    "cobarde": {"miedoso", "temeroso", "pusilánime"},
    "amable": {"bondadoso", "afable", "simpático", "cordial"},
    "cruel": {"despiadado", "malvado", "sádico"},
    "honesto": {"sincero", "veraz", "íntegro", "recto"},
    "mentiroso": {"embustero", "falso", "tramposo"},
    "generoso": {"dadivoso", "espléndido", "altruista"},
    "tacaño": {"avaro", "mezquino", "cicatero"},
    "paciente": {"calmado", "sereno", "tranquilo"},
    "impaciente": {"nervioso", "inquieto", "ansioso"},
    "tímido": {"introvertido", "reservado", "retraído"},
    "extrovertido": {"sociable", "abierto", "comunicativo"},
    "sabio": {"inteligente", "prudente", "sensato"},
    "ingenuo": {"inocente", "cándido", "crédulo"},
    "astuto": {"sagaz", "perspicaz", "listo", "avispado"},
    "orgulloso": {"altivo", "soberbio", "arrogante"},
    "humilde": {"modesto", "sencillo", "llano"},
}

# Combinación de sinónimos por tipo de atributo
SYNONYMS_BY_KEY: dict[AttributeKey, dict[str, set[str]]] = {
    AttributeKey.EYE_COLOR: COLOR_SYNONYMS,
    AttributeKey.HAIR_COLOR: COLOR_SYNONYMS,
    AttributeKey.BUILD: BUILD_SYNONYMS,
    AttributeKey.HEIGHT: BUILD_SYNONYMS,
    AttributeKey.PERSONALITY: PERSONALITY_SYNONYMS,
    AttributeKey.TEMPERAMENT: PERSONALITY_SYNONYMS,
}


def _are_synonyms(v1: str, v2: str, attr_key: AttributeKey) -> bool:
    """Verifica si dos valores son sinónimos."""
    if attr_key not in SYNONYMS_BY_KEY:
        return False
    synonyms = SYNONYMS_BY_KEY[attr_key]
    # Check both directions
    if v1 in synonyms and v2 in synonyms.get(v1, set()):
        return True
    if v2 in synonyms and v1 in synonyms.get(v2, set()):
        return True
    return False


# =============================================================================
# Diccionarios de antónimos (para detectar contradicciones)
# =============================================================================

# Antónimos para colores (no se pueden tener dos a la vez)
COLOR_ANTONYMS: dict[str, set[str]] = {
    "verde": {"azul", "marrón", "negro", "gris", "castaño", "miel", "ámbar"},
    "azul": {"verde", "marrón", "negro", "castaño", "miel", "ámbar"},
    "marrón": {"verde", "azul", "gris", "negro"},
    "castaño": {"verde", "azul", "rubio", "negro", "pelirrojo"},
    "negro": {"verde", "azul", "rubio", "castaño", "pelirrojo", "canoso", "blanco"},
    "rubio": {"negro", "castaño", "moreno", "pelirrojo"},
    "pelirrojo": {"negro", "rubio", "castaño", "moreno", "canoso"},
    "canoso": {"negro", "rubio", "castaño", "pelirrojo"},
    "blanco": {"negro", "castaño", "rubio"},
    "gris": {"verde", "azul", "marrón"},
    "miel": {"verde", "azul", "negro"},
    "ámbar": {"verde", "azul", "negro"},
}

# Antónimos para constitución física
BUILD_ANTONYMS: dict[str, set[str]] = {
    "alto": {"bajo", "bajito", "pequeño"},
    "bajo": {"alto", "altísimo"},
    "bajito": {"alto", "altísimo"},
    "delgado": {"gordo", "corpulento", "obeso", "robusto", "fornido"},
    "gordo": {"delgado", "flaco", "esbelto", "delgadísimo"},
    "flaco": {"gordo", "corpulento", "robusto", "fornido"},
    "corpulento": {"delgado", "flaco", "esbelto", "enclenque"},
    "esbelto": {"gordo", "corpulento", "rechoncho"},
    "musculoso": {"enclenque", "débil", "escuálido"},
    "enclenque": {"musculoso", "fornido", "robusto"},
    "robusto": {"enclenque", "débil", "flaco", "delgado"},
    "fornido": {"enclenque", "débil", "flaco", "delgado"},
}

# Antónimos para tipo de pelo (largo/corto, liso/rizado)
HAIR_TYPE_ANTONYMS: dict[str, set[str]] = {
    "largo": {"corto", "rapado"},
    "corto": {"largo"},
    "liso": {"rizado", "ondulado", "encrespado"},
    "rizado": {"liso", "lacio"},
    "ondulado": {"liso", "lacio"},
    "encrespado": {"liso", "lacio"},
    "lacio": {"rizado", "ondulado", "encrespado"},
    "rapado": {"largo"},
    "recogido": {"suelto"},
    "suelto": {"recogido", "trenzado"},
    "trenzado": {"suelto"},
}

# Antónimos para personalidad
PERSONALITY_ANTONYMS: dict[str, set[str]] = {
    "amable": {"cruel", "desagradable", "hostil", "grosero"},
    "cruel": {"amable", "bondadoso", "compasivo"},
    "valiente": {"cobarde", "miedoso", "temeroso"},
    "cobarde": {"valiente", "audaz", "intrépido"},
    "honesto": {"mentiroso", "deshonesto", "tramposo"},
    "mentiroso": {"honesto", "sincero", "veraz"},
    "generoso": {"tacaño", "avaro", "mezquino"},
    "tacaño": {"generoso", "espléndido", "dadivoso"},
    "paciente": {"impaciente", "nervioso", "inquieto"},
    "impaciente": {"paciente", "calmado", "sereno"},
    "tímido": {"extrovertido", "desinhibido", "sociable"},
    "extrovertido": {"tímido", "introvertido", "reservado"},
    "sabio": {"ignorante", "necio", "tonto"},
    "ingenuo": {"astuto", "sagaz", "perspicaz"},
    "astuto": {"ingenuo", "inocente", "cándido"},
    "orgulloso": {"humilde", "modesto"},
    "humilde": {"orgulloso", "arrogante", "soberbio"},
    "arrogante": {"humilde", "modesto", "sencillo"},
}

# Antónimos para ubicación/posición (un personaje no puede estar en dos lugares a la vez)
# Estos son lugares que son mutuamente excluyentes dentro de un mismo capítulo/escena
LOCATION_ANTONYMS: dict[str, set[str]] = {
    # Interior vs exterior
    "dentro": {"fuera", "afuera", "exterior"},
    "fuera": {"dentro", "interior", "adentro"},
    "interior": {"exterior", "afuera", "fuera"},
    "exterior": {"interior", "dentro", "adentro"},
    # Direcciones cardinales
    "norte": {"sur"},
    "sur": {"norte"},
    "este": {"oeste"},
    "oeste": {"este"},
    # Arriba vs abajo
    "arriba": {"abajo"},
    "abajo": {"arriba"},
    "sótano": {"ático", "azotea", "tejado"},
    "ático": {"sótano", "planta baja"},
    "azotea": {"sótano", "planta baja"},
    # Ciudades/países conocidos que son mutuamente excluyentes
    "madrid": {"barcelona", "sevilla", "valencia", "bilbao", "londres", "parís", "roma"},
    "barcelona": {"madrid", "sevilla", "valencia", "bilbao", "londres", "parís", "roma"},
    "londres": {"madrid", "barcelona", "parís", "roma", "nueva york", "berlín"},
    "parís": {"madrid", "barcelona", "londres", "roma", "nueva york", "berlín"},
    "roma": {"madrid", "barcelona", "londres", "parís", "nueva york", "berlín"},
}

# Combinación de todos los antónimos por tipo de atributo
ANTONYMS_BY_KEY: dict[AttributeKey, dict[str, set[str]]] = {
    AttributeKey.EYE_COLOR: COLOR_ANTONYMS,
    AttributeKey.HAIR_COLOR: COLOR_ANTONYMS,
    AttributeKey.HAIR_TYPE: HAIR_TYPE_ANTONYMS,
    AttributeKey.BUILD: BUILD_ANTONYMS,
    AttributeKey.HEIGHT: BUILD_ANTONYMS,
    AttributeKey.PERSONALITY: PERSONALITY_ANTONYMS,
    AttributeKey.TEMPERAMENT: PERSONALITY_ANTONYMS,
    AttributeKey.LOCATION: LOCATION_ANTONYMS,
}


class AttributeConsistencyChecker:
    """
    Verificador de consistencia de atributos.

    Detecta contradicciones en los atributos de entidades
    comparando valores extraídos de diferentes partes del texto.

    Attributes:
        use_embeddings: Usar embeddings para comparación semántica
        min_confidence: Confianza mínima para reportar inconsistencia
    """

    def __init__(
        self,
        use_embeddings: bool = True,
        min_confidence: float = 0.5,
    ):
        """
        Inicializa el verificador.

        Args:
            use_embeddings: Usar embeddings para similitud semántica
            min_confidence: Confianza mínima (0.0-1.0)
        """
        self.use_embeddings = use_embeddings
        self.min_confidence = min_confidence
        self._embeddings_model = None

    def _get_embeddings_model(self):
        """Obtiene el modelo de embeddings (lazy loading)."""
        if self._embeddings_model is None and self.use_embeddings:
            try:
                from ..nlp.embeddings import get_embeddings_model
                self._embeddings_model = get_embeddings_model()
            except Exception as e:
                logger.warning(f"No se pudo cargar modelo de embeddings: {e}")
                self._embeddings_model = False
        return self._embeddings_model if self._embeddings_model else None

    def check_consistency(
        self,
        attributes: list[ExtractedAttribute],
    ) -> Result[list[AttributeInconsistency]]:
        """
        Verifica consistencia en una lista de atributos.

        Agrupa atributos por (entidad, clave) y busca valores
        contradictorios.

        Args:
            attributes: Lista de atributos extraídos

        Returns:
            Result con lista de inconsistencias detectadas
        """
        if not attributes:
            return Result.success([])

        inconsistencies: list[AttributeInconsistency] = []

        try:
            # Agrupar por (entity_name, attribute_key)
            grouped: dict[tuple[str, AttributeKey], list[ExtractedAttribute]] = {}

            for attr in attributes:
                key = (attr.entity_name.lower(), attr.key)
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(attr)

            logger.debug(f"Grouped {len(attributes)} attributes into {len(grouped)} entity-attribute pairs")

            # Buscar inconsistencias en cada grupo
            for (entity_name, attr_key), attrs in grouped.items():
                if len(attrs) < 2:
                    continue

                logger.debug(f"Checking {entity_name}.{attr_key.value}: {len(attrs)} values - {[a.value for a in attrs]}")

                # Comparar cada par de atributos
                for i, attr1 in enumerate(attrs):
                    for attr2 in attrs[i + 1:]:
                        # Saltar si son el mismo valor
                        if attr1.value.lower() == attr2.value.lower():
                            logger.debug(f"  Skipping {attr1.value} == {attr2.value} (same value)")
                            continue

                        # Saltar si ambos están negados (no son afirmaciones)
                        if attr1.is_negated and attr2.is_negated:
                            logger.debug(f"  Skipping {attr1.value} vs {attr2.value} (both negated)")
                            continue

                        # Calcular confianza de inconsistencia
                        confidence, inc_type = self._calculate_inconsistency(
                            attr1, attr2, attr_key
                        )

                        logger.debug(f"  Comparing {attr1.value} vs {attr2.value}: confidence={confidence:.2f}, type={inc_type.value}")

                        if confidence >= self.min_confidence:
                            explanation = self._generate_explanation(
                                attr_key, attr1, attr2, inc_type, confidence
                            )

                            logger.info(f"INCONSISTENCY DETECTED: {entity_name}.{attr_key.value} '{attr1.value}' vs '{attr2.value}' (confidence: {confidence:.2f})")

                            inconsistencies.append(
                                AttributeInconsistency(
                                    entity_name=attr1.entity_name,
                                    entity_id=0,  # Debe resolverse al crear alerta via EntityRepository
                                    attribute_key=attr_key,
                                    value1=attr1.value,
                                    value1_chapter=attr1.chapter_id,
                                    value1_excerpt=attr1.source_text,
                                    value2=attr2.value,
                                    value2_chapter=attr2.chapter_id,
                                    value2_excerpt=attr2.source_text,
                                    inconsistency_type=inc_type,
                                    confidence=confidence,
                                    explanation=explanation,
                                )
                            )

            # Ordenar por confianza descendente
            inconsistencies.sort(key=lambda x: -x.confidence)

            logger.info(f"Inconsistencias detectadas: {len(inconsistencies)}")
            return Result.success(inconsistencies)

        except Exception as e:
            error = ConsistencyCheckError(original_error=str(e))
            logger.error(f"Error verificando consistencia: {e}")
            return Result.partial(inconsistencies, [error])

    def _calculate_inconsistency(
        self,
        attr1: ExtractedAttribute,
        attr2: ExtractedAttribute,
        attr_key: AttributeKey,
    ) -> tuple[float, InconsistencyType]:
        """
        Calcula la confianza de que haya una inconsistencia real.

        Returns:
            Tupla de (confianza, tipo_inconsistencia)
        """
        # Normalizar valores (lematización morfológica)
        v1 = _normalize_value(attr1.value)
        v2 = _normalize_value(attr2.value)

        # Valores idénticos después de normalización = no hay inconsistencia
        if v1 == v2:
            return 0.0, InconsistencyType.VALUE_CHANGE

        # 0. Verificar sinónimos conocidos (evitar falsos positivos)
        if _are_synonyms(v1, v2, attr_key):
            logger.debug(f"Sinónimos detectados: {v1} ~ {v2}")
            return 0.0, InconsistencyType.VALUE_CHANGE  # No es inconsistencia

        # 1. Verificar antónimos conocidos
        if attr_key in ANTONYMS_BY_KEY:
            antonyms = ANTONYMS_BY_KEY[attr_key]
            if v1 in antonyms and v2 in antonyms.get(v1, set()):
                return 0.95, InconsistencyType.ANTONYM
            if v2 in antonyms and v1 in antonyms.get(v2, set()):
                return 0.95, InconsistencyType.ANTONYM

        # 2. Caso especial: edad (valores numéricos)
        if attr_key == AttributeKey.AGE:
            return self._check_age_consistency(v1, v2)

        # 3. Similitud semántica con embeddings
        if self.use_embeddings:
            similarity = self._calculate_semantic_similarity(v1, v2)
            if similarity is not None:
                # Alta similitud = probablemente sinónimos (no inconsistencia)
                if similarity >= 0.7:
                    logger.debug(f"Alta similitud semántica: {v1} ~ {v2} ({similarity:.2f})")
                    return 0.1, InconsistencyType.VALUE_CHANGE
                # Media similitud = cambio menor
                elif similarity >= 0.5:
                    return 0.4, InconsistencyType.VALUE_CHANGE
                # Baja similitud = posible inconsistencia
                elif similarity >= 0.3:
                    return 0.6, InconsistencyType.SEMANTIC_DIFF
                # Muy baja similitud = probable inconsistencia
                else:
                    return 0.8, InconsistencyType.SEMANTIC_DIFF

        # 4. Fallback: valores diferentes = posible inconsistencia
        # Considerar longitud de valores y overlap de caracteres
        overlap = len(set(v1) & set(v2)) / max(len(set(v1)), len(set(v2)), 1)
        if overlap < 0.3:
            return 0.6, InconsistencyType.VALUE_CHANGE

        return 0.4, InconsistencyType.VALUE_CHANGE

    def _check_age_consistency(
        self,
        v1: str,
        v2: str,
    ) -> tuple[float, InconsistencyType]:
        """Verifica consistencia de edades numéricas."""
        try:
            age1 = int(v1)
            age2 = int(v2)
            diff = abs(age1 - age2)

            # Diferencia pequeña (1-2 años) puede ser redondeo
            if diff <= 2:
                return 0.3, InconsistencyType.VALUE_CHANGE

            # Diferencia media (3-5 años) es sospechosa
            if diff <= 5:
                return 0.6, InconsistencyType.VALUE_CHANGE

            # Diferencia grande = muy probable inconsistencia
            return 0.9, InconsistencyType.CONTRADICTORY

        except ValueError:
            # No son números, usar comparación por defecto
            return 0.5, InconsistencyType.VALUE_CHANGE

    def _calculate_semantic_similarity(
        self,
        text1: str,
        text2: str,
    ) -> Optional[float]:
        """
        Calcula similitud semántica usando embeddings.

        Returns:
            Similitud coseno (0.0-1.0) o None si no disponible
        """
        model = self._get_embeddings_model()
        if not model:
            return None

        try:
            embeddings = model.encode([text1, text2])

            # Similitud coseno
            import numpy as np
            dot_product = np.dot(embeddings[0], embeddings[1])
            norm1 = np.linalg.norm(embeddings[0])
            norm2 = np.linalg.norm(embeddings[1])

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return float(dot_product / (norm1 * norm2))

        except Exception as e:
            logger.warning(f"Error calculando similitud semántica: {e}")
            return None

    def _generate_explanation(
        self,
        attr_key: AttributeKey,
        attr1: ExtractedAttribute,
        attr2: ExtractedAttribute,
        inc_type: InconsistencyType,
        confidence: float,
    ) -> str:
        """Genera una explicación legible de la inconsistencia."""
        key_name = attr_key.value.replace("_", " ")
        entity = attr1.entity_name

        # Ubicación
        loc1 = f"cap. {attr1.chapter_id}" if attr1.chapter_id else "texto"
        loc2 = f"cap. {attr2.chapter_id}" if attr2.chapter_id else "texto"

        if inc_type == InconsistencyType.ANTONYM:
            return (
                f"'{entity}' tiene {key_name} contradictorios: "
                f"'{attr1.value}' ({loc1}) vs '{attr2.value}' ({loc2}). "
                f"Son valores opuestos."
            )

        if inc_type == InconsistencyType.CONTRADICTORY:
            return (
                f"'{entity}' tiene {key_name} muy diferentes: "
                f"'{attr1.value}' ({loc1}) vs '{attr2.value}' ({loc2}). "
                f"Probable error de continuidad."
            )

        return (
            f"'{entity}' tiene {key_name} diferentes: "
            f"'{attr1.value}' ({loc1}) vs '{attr2.value}' ({loc2}). "
            f"Verificar si es intencional."
        )

    def check_entity_attributes(
        self,
        entity_name: str,
        attributes: list[ExtractedAttribute],
    ) -> list[AttributeInconsistency]:
        """
        Verifica consistencia de atributos de una entidad específica.

        Args:
            entity_name: Nombre de la entidad
            attributes: Atributos de esa entidad

        Returns:
            Lista de inconsistencias encontradas
        """
        # Filtrar atributos de la entidad
        entity_attrs = [
            a for a in attributes
            if a.entity_name.lower() == entity_name.lower()
        ]

        result = self.check_consistency(entity_attrs)
        return result.value if result.is_success else []


# =============================================================================
# Funciones de conveniencia
# =============================================================================

def check_attribute_consistency(
    attributes: list[ExtractedAttribute],
) -> Result[list[AttributeInconsistency]]:
    """
    Función de conveniencia para verificar consistencia.

    Args:
        attributes: Lista de atributos extraídos

    Returns:
        Result con lista de inconsistencias
    """
    checker = get_consistency_checker()
    return checker.check_consistency(attributes)


# =============================================================================
# Singleton thread-safe
# =============================================================================

_checker_lock = threading.Lock()
_consistency_checker: Optional[AttributeConsistencyChecker] = None


def get_consistency_checker(
    use_embeddings: bool = True,
    min_confidence: float = 0.5,
) -> AttributeConsistencyChecker:
    """
    Obtiene el singleton del verificador de consistencia.

    Args:
        use_embeddings: Usar embeddings para comparación
        min_confidence: Confianza mínima

    Returns:
        Instancia única del AttributeConsistencyChecker
    """
    global _consistency_checker

    if _consistency_checker is None:
        with _checker_lock:
            if _consistency_checker is None:
                _consistency_checker = AttributeConsistencyChecker(
                    use_embeddings=use_embeddings,
                    min_confidence=min_confidence,
                )

    return _consistency_checker


def reset_consistency_checker() -> None:
    """Resetea el singleton (útil para tests)."""
    global _consistency_checker
    with _checker_lock:
        _consistency_checker = None
