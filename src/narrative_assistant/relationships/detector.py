"""
Detección automática de relaciones entre entidades desde texto.

Sistema Multi-Método con Votación Ponderada:

1. **Patrones regex** (30%): Patrones explícitos como "X, madre de Y"
2. **Análisis de dependencias** (25%): Verbos relacionales y sintaxis
3. **LLM local** (30%): Comprensión semántica profunda con Ollama
4. **Embeddings semánticos** (15%): Similitud contextual

Arquitectura:
- Cada método genera candidatos con scores de confianza
- Sistema de votación ponderada para consenso
- Bonificación por acuerdo entre métodos (1.15x)
- Fallbacks graceful si algún método no está disponible
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from enum import Enum

from .models import (
    EntityRelationship,
    RelationshipEvidence,
    RelationType,
    TextReference,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Enums y Configuración del Sistema de Votación
# =============================================================================


class RelationDetectionMethod(Enum):
    """Métodos de detección de relaciones."""

    PATTERNS = "patterns"  # Patrones regex explícitos
    DEPENDENCY = "dependency"  # Análisis de dependencias sintácticas
    LLM = "llm"  # LLM local (Ollama)
    EMBEDDINGS = "embeddings"  # Similitud semántica


# Pesos por defecto para votación
DEFAULT_RELATION_WEIGHTS = {
    RelationDetectionMethod.PATTERNS: 0.30,
    RelationDetectionMethod.DEPENDENCY: 0.25,
    RelationDetectionMethod.LLM: 0.30,
    RelationDetectionMethod.EMBEDDINGS: 0.15,
}

# Bonus por acuerdo entre métodos
AGREEMENT_BONUS = 1.15


def _get_default_relation_methods() -> list[RelationDetectionMethod]:
    """
    Retorna los métodos habilitados por defecto según el hardware.

    - Con GPU: Todos los métodos (incluyendo LLM)
    - Sin GPU: Solo métodos rápidos (sin LLM)
    """
    try:
        from ..core.device import get_device_config

        device_config = get_device_config()
        has_gpu = device_config.device_type in ("cuda", "mps")
    except Exception:
        has_gpu = False

    if has_gpu:
        return list(RelationDetectionMethod)
    else:
        return [
            RelationDetectionMethod.PATTERNS,
            RelationDetectionMethod.DEPENDENCY,
            RelationDetectionMethod.EMBEDDINGS,
        ]


@dataclass
class RelationDetectionConfig:
    """Configuración del sistema de detección de relaciones."""

    enabled_methods: list[RelationDetectionMethod] = field(
        default_factory=_get_default_relation_methods
    )
    method_weights: dict[RelationDetectionMethod, float] = field(
        default_factory=lambda: DEFAULT_RELATION_WEIGHTS.copy()
    )
    min_confidence: float = 0.4
    consensus_threshold: float = 0.5  # Mínimo % de métodos que deben acordar
    ollama_model: str = "llama3.2"
    ollama_timeout: int = 300
    use_llm: bool = field(default=None)  # None = auto

    def __post_init__(self):
        """Ajusta configuración según hardware si use_llm es None."""
        if self.use_llm is None:
            self.use_llm = RelationDetectionMethod.LLM in self.enabled_methods
        elif self.use_llm and RelationDetectionMethod.LLM not in self.enabled_methods:
            self.enabled_methods.append(RelationDetectionMethod.LLM)
        elif not self.use_llm and RelationDetectionMethod.LLM in self.enabled_methods:
            self.enabled_methods.remove(RelationDetectionMethod.LLM)


# =============================================================================
# Estructuras de Datos
# =============================================================================


@dataclass
class DetectedRelation:
    """Relación detectada antes de ser confirmada."""

    source_name: str
    target_name: str
    relation_type: RelationType
    evidence_text: str
    chapter: int = 0
    start_char: int = 0
    end_char: int = 0
    confidence: float = 0.5
    detection_method: str = "pattern"
    methods_agreed: list[str] = field(default_factory=list)
    reasoning: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Implementaciones de Métodos de Detección
# =============================================================================


class DependencyRelationMethod:
    """
    Detección de relaciones basada en análisis de dependencias sintácticas.

    Usa spaCy para analizar verbos relacionales y su estructura argumental.
    """

    # Verbos que indican relaciones entre personas
    RELATIONAL_VERBS = {
        # Verbos familiares/sociales
        "ser": {
            "hermano": RelationType.SIBLING,
            "hermana": RelationType.SIBLING,
            "padre": RelationType.PARENT,
            "madre": RelationType.PARENT,
            "hijo": RelationType.CHILD,
            "hija": RelationType.CHILD,
            "esposo": RelationType.SPOUSE,
            "esposa": RelationType.SPOUSE,
            "amigo": RelationType.FRIEND,
            "amiga": RelationType.FRIEND,
            "enemigo": RelationType.ENEMY,
            "rival": RelationType.RIVAL,
            "mentor": RelationType.MENTOR,
            "primo": RelationType.COUSIN,
            "prima": RelationType.COUSIN,
            "tío": RelationType.UNCLE_AUNT,
            "tía": RelationType.UNCLE_AUNT,
        },
        # Verbos emocionales
        "odiar": RelationType.HATES,
        "amar": RelationType.LOVER,
        "querer": RelationType.LOVER,
        "temer": RelationType.FEARS,
        "admirar": RelationType.ADMIRES,
        "confiar": RelationType.TRUSTS,
        "desconfiar": RelationType.DISTRUSTS,
        "detestar": RelationType.HATES,
    }

    def __init__(self):
        self._nlp = None
        self._lock = threading.Lock()

    @property
    def nlp(self):
        """Lazy loading del modelo spaCy."""
        if self._nlp is None:
            with self._lock:
                if self._nlp is None:
                    try:
                        from ..nlp.spacy_gpu import load_spacy_model

                        self._nlp = load_spacy_model()
                    except Exception as e:
                        logger.warning(f"No se pudo cargar spaCy para dependencias: {e}")
        return self._nlp

    def detect(
        self,
        text: str,
        chapter: int = 0,
        entities: list[str] | None = None,
    ) -> list[tuple[DetectedRelation, float, str]]:
        """
        Detecta relaciones usando análisis de dependencias.

        Returns:
            Lista de (DetectedRelation, score, razonamiento)
        """
        if not self.nlp:
            return []

        results = []
        entity_set = {e.lower() for e in (entities or [])}

        try:
            doc = self.nlp(text)

            for sent in doc.sents:
                sent_results = self._analyze_sentence(sent, chapter, entity_set, text)
                results.extend(sent_results)

        except Exception as e:
            logger.debug(f"Error en análisis de dependencias: {e}")

        return results

    def _analyze_sentence(
        self,
        sent,
        chapter: int,
        entity_set: set[str],
        full_text: str,
    ) -> list[tuple[DetectedRelation, float, str]]:
        """Analiza una oración en busca de relaciones."""
        results = []

        for token in sent:
            # Buscar verbos relacionales
            if token.pos_ == "VERB":
                lemma = token.lemma_.lower()

                # Verbo directo (odiar, amar, etc.)
                if lemma in self.RELATIONAL_VERBS and not isinstance(
                    self.RELATIONAL_VERBS[lemma], dict
                ):
                    rel_type = self.RELATIONAL_VERBS[lemma]
                    result = self._extract_relation_from_verb(
                        token, rel_type, chapter, entity_set, full_text
                    )
                    if result:
                        results.append(result)

                # Verbo copulativo "ser" con atributo
                elif lemma == "ser":
                    result = self._extract_copulative_relation(
                        token, chapter, entity_set, full_text
                    )
                    if result:
                        results.append(result)

        return results

    def _extract_relation_from_verb(
        self,
        verb_token,
        rel_type: RelationType,
        chapter: int,
        entity_set: set[str],
        full_text: str,
    ) -> tuple[DetectedRelation, float, str] | None:
        """Extrae relación de un verbo emocional/relacional."""
        source = None
        target = None

        # Buscar sujeto (nsubj)
        for child in verb_token.children:
            if child.dep_ in ("nsubj", "nsubj:pass"):
                if child.ent_type_ in ("PER", "PERSON") or child.text[0].isupper():
                    source = child.text
            elif child.dep_ in ("obj", "dobj", "obl"):
                # Objeto directo o preposicional
                if child.ent_type_ in ("PER", "PERSON") or child.text[0].isupper():
                    target = child.text
                # Buscar en hijos del complemento preposicional
                for subchild in child.children:
                    if subchild.ent_type_ in ("PER", "PERSON") or subchild.text[0].isupper():
                        target = subchild.text

        if source and target:
            evidence = verb_token.sent.text
            confidence = 0.75

            # Boost si conocemos las entidades
            if entity_set:
                if source.lower() in entity_set:
                    confidence += 0.1
                if target.lower() in entity_set:
                    confidence += 0.1

            rel = DetectedRelation(
                source_name=source,
                target_name=target,
                relation_type=rel_type,
                evidence_text=evidence,
                chapter=chapter,
                start_char=verb_token.sent.start_char,
                end_char=verb_token.sent.end_char,
                confidence=min(1.0, confidence),
                detection_method="dependency",
            )
            reasoning = f"Verbo relacional '{verb_token.lemma_}' con sujeto y objeto"
            return (rel, confidence, reasoning)

        return None

    def _extract_copulative_relation(
        self,
        verb_token,
        chapter: int,
        entity_set: set[str],
        full_text: str,
    ) -> tuple[DetectedRelation, float, str] | None:
        """Extrae relación de construcción 'X es Y de Z'."""
        source = None
        attribute = None
        target = None

        for child in verb_token.children:
            if child.dep_ in ("nsubj", "nsubj:pass"):
                if child.ent_type_ in ("PER", "PERSON") or child.text[0].isupper():
                    source = child.text
            elif child.dep_ in ("attr", "acomp", "xcomp"):
                attribute = child.lemma_.lower()
                # Buscar complemento "de X"
                for subchild in child.children:
                    if subchild.dep_ == "nmod" or (
                        subchild.dep_ == "case" and subchild.text.lower() == "de"
                    ):
                        for subsubchild in child.children:
                            if subsubchild.dep_ == "nmod":
                                for nmod_child in subsubchild.children:
                                    if (
                                        nmod_child.ent_type_ in ("PER", "PERSON")
                                        or nmod_child.text[0].isupper()
                                    ):
                                        target = nmod_child.text
                                if not target and (
                                    subsubchild.ent_type_ in ("PER", "PERSON")
                                    or subsubchild.text[0].isupper()
                                ):
                                    target = subsubchild.text

        # Mapear atributo a tipo de relación
        if source and attribute and attribute in self.RELATIONAL_VERBS.get("ser", {}):
            rel_type = self.RELATIONAL_VERBS["ser"][attribute]

            # Para relaciones sin target explícito (ej: "Juan es hermano")
            # usamos el contexto para inferir
            if not target:
                return None

            evidence = verb_token.sent.text
            confidence = 0.8

            if entity_set:
                if source.lower() in entity_set:
                    confidence += 0.1
                if target.lower() in entity_set:
                    confidence += 0.1

            rel = DetectedRelation(
                source_name=source,
                target_name=target,
                relation_type=rel_type,
                evidence_text=evidence,
                chapter=chapter,
                start_char=verb_token.sent.start_char,
                end_char=verb_token.sent.end_char,
                confidence=min(1.0, confidence),
                detection_method="dependency",
            )
            reasoning = f"Construcción copulativa 'X es {attribute} de Y'"
            return (rel, confidence, reasoning)

        return None


class LLMRelationMethod:
    """
    Detección de relaciones usando LLM local (Ollama).

    Aprovecha la comprensión semántica profunda para detectar
    relaciones implícitas y complejas.
    """

    def __init__(self, model: str = "llama3.2", timeout: int = 300):
        self.model = model
        self.timeout = timeout
        self._client = None
        self._lock = threading.Lock()

    @property
    def client(self):
        """Lazy loading del cliente LLM."""
        if self._client is None:
            with self._lock:
                if self._client is None:
                    try:
                        from ..llm.client import get_llm_client

                        self._client = get_llm_client()
                    except Exception as e:
                        logger.warning(f"No se pudo conectar LLM para relaciones: {e}")
        return self._client

    def detect(
        self,
        text: str,
        chapter: int = 0,
        entities: list[str] | None = None,
    ) -> list[tuple[DetectedRelation, float, str]]:
        """
        Detecta relaciones usando LLM.

        Args:
            text: Texto a analizar (se limita para eficiencia)
            chapter: Número de capítulo
            entities: Lista de entidades conocidas

        Returns:
            Lista de (DetectedRelation, score, razonamiento)
        """
        if not self.client or not self.client.is_available:
            return []

        from narrative_assistant.llm.sanitization import sanitize_for_prompt

        # Sanitizar texto del manuscrito antes de enviarlo al LLM (A-10)
        text_sample = sanitize_for_prompt(
            text[:3000] if len(text) > 3000 else text, max_length=3000
        )

        entities_str = ", ".join(
            sanitize_for_prompt(e, max_length=100) for e in entities[:20]
        ) if entities else "no especificadas"

        prompt = f"""Analiza el siguiente texto narrativo en español y extrae las relaciones entre personajes.

TEXTO:
{text_sample}

ENTIDADES CONOCIDAS: {entities_str}

Busca relaciones de tipo:
- Familiares: padre/madre, hijo/hija, hermanos, esposos, primos, tíos, abuelos
- Sociales: amigos, enemigos, rivales, mentores, colegas
- Emocionales: amor, odio, admiración, miedo, confianza, desconfianza
- Otras: jefe/empleado, propietario, creador

Para cada relación encontrada, responde en formato:
RELACION: [nombre1] -> [tipo_relacion] -> [nombre2]
EVIDENCIA: [frase del texto que lo demuestra]
CONFIANZA: [alta/media/baja]

Ejemplo:
RELACION: María -> PARENT -> Juan
EVIDENCIA: "María, la madre de Juan, lo abrazó"
CONFIANZA: alta

Lista todas las relaciones encontradas:"""

        try:
            response = self.client.complete(
                prompt=prompt,
                system="Eres un experto en análisis narrativo. Extrae relaciones entre personajes con precisión. Solo reporta relaciones que estén claramente indicadas en el texto.",
                max_tokens=1000,
                temperature=0.1,
            )

            if not response:
                return []

            return self._parse_llm_response(response, chapter, text)

        except Exception as e:
            logger.debug(f"Error en LLM relaciones: {e}")
            return []

    def _parse_llm_response(
        self,
        response: str,
        chapter: int,
        original_text: str,
    ) -> list[tuple[DetectedRelation, float, str]]:
        """Parsea la respuesta del LLM."""
        results = []

        # Patrones para parsear respuesta
        relation_pattern = re.compile(
            r"RELACION:\s*(?P<source>[^->]+?)\s*->\s*(?P<type>\w+)\s*->\s*(?P<target>[^->]+)",
            re.IGNORECASE,
        )
        evidence_pattern = re.compile(r'EVIDENCIA:\s*["\']?([^"\']+)["\']?', re.IGNORECASE)
        confidence_pattern = re.compile(r"CONFIANZA:\s*(alta|media|baja)", re.IGNORECASE)

        # Dividir por bloques de relación
        blocks = re.split(r"\n(?=RELACION:)", response, flags=re.IGNORECASE)

        for block in blocks:
            rel_match = relation_pattern.search(block)
            if not rel_match:
                continue

            source = rel_match.group("source").strip()
            rel_type_str = rel_match.group("type").strip().upper()
            target = rel_match.group("target").strip()

            # Mapear tipo de relación
            rel_type = self._map_relation_type(rel_type_str)
            if not rel_type:
                continue

            # Obtener evidencia
            evidence_match = evidence_pattern.search(block)
            evidence = evidence_match.group(1).strip() if evidence_match else block

            # Obtener confianza
            conf_match = confidence_pattern.search(block)
            conf_map = {"alta": 0.9, "media": 0.7, "baja": 0.5}
            confidence = conf_map.get(conf_match.group(1).lower() if conf_match else "media", 0.7)

            # Buscar posición en texto original
            start_char = original_text.find(source)
            end_char = start_char + len(evidence) if start_char >= 0 else 0

            rel = DetectedRelation(
                source_name=source,
                target_name=target,
                relation_type=rel_type,
                evidence_text=evidence[:200],  # Limitar longitud
                chapter=chapter,
                start_char=max(0, start_char),
                end_char=end_char,
                confidence=confidence,
                detection_method="llm",
            )
            reasoning = f"LLM detectó relación {rel_type_str}"
            results.append((rel, confidence, reasoning))

        return results

    def _map_relation_type(self, type_str: str) -> RelationType | None:
        """Mapea string a RelationType."""
        mapping = {
            "PARENT": RelationType.PARENT,
            "CHILD": RelationType.CHILD,
            "SIBLING": RelationType.SIBLING,
            "SPOUSE": RelationType.SPOUSE,
            "FRIEND": RelationType.FRIEND,
            "ENEMY": RelationType.ENEMY,
            "RIVAL": RelationType.RIVAL,
            "MENTOR": RelationType.MENTOR,
            "HATES": RelationType.HATES,
            "LOVES": RelationType.LOVER,
            "LOVER": RelationType.LOVER,
            "FEARS": RelationType.FEARS,
            "ADMIRES": RelationType.ADMIRES,
            "TRUSTS": RelationType.TRUSTS,
            "DISTRUSTS": RelationType.DISTRUSTS,
            "GRANDPARENT": RelationType.GRANDPARENT,
            "COUSIN": RelationType.COUSIN,
            "UNCLE_AUNT": RelationType.UNCLE_AUNT,
            "OWNS": RelationType.OWNS,
            "MEMBER_OF": RelationType.MEMBER_OF,
            "LEADER_OF": RelationType.LEADER_OF,
            "WORKS_IN": RelationType.WORKS_IN,
            "LIVES_IN": RelationType.LIVES_IN,
        }
        return mapping.get(type_str.upper())


class EmbeddingsRelationMethod:
    """
    Detección de relaciones usando embeddings semánticos.

    Usa similitud de contexto para validar relaciones
    detectadas por otros métodos.
    """

    # Frases prototipo para cada tipo de relación
    RELATION_PROTOTYPES = {
        RelationType.PARENT: ["es el padre de", "es la madre de", "su padre", "su madre"],
        RelationType.CHILD: ["es el hijo de", "es la hija de", "su hijo", "su hija"],
        RelationType.SIBLING: ["es hermano de", "es hermana de", "son hermanos"],
        RelationType.SPOUSE: ["es esposo de", "es esposa de", "están casados"],
        RelationType.FRIEND: ["son amigos", "es amigo de", "amistad", "mejor amigo"],
        RelationType.ENEMY: ["son enemigos", "es enemigo de", "lo odia", "lo detesta"],
        RelationType.HATES: ["odia a", "detesta a", "no soporta a", "aborrece"],
        RelationType.LOVER: ["ama a", "está enamorado de", "quiere a", "amor"],
        RelationType.FEARS: ["teme a", "tiene miedo de", "le asusta"],
        RelationType.TRUSTS: ["confía en", "se fía de", "tiene confianza"],
    }

    def __init__(self):
        self._embeddings = None
        self._prototype_embeddings = None
        self._lock = threading.Lock()

    @property
    def embeddings(self):
        """Lazy loading del modelo de embeddings."""
        if self._embeddings is None:
            with self._lock:
                if self._embeddings is None:
                    try:
                        from ..nlp.embeddings import get_embeddings_model

                        self._embeddings = get_embeddings_model()
                    except Exception as e:
                        logger.warning(f"No se pudo cargar embeddings para relaciones: {e}")
        return self._embeddings

    def _get_prototype_embeddings(self) -> dict:
        """Calcula embeddings de frases prototipo (lazy, una sola vez)."""
        if self._prototype_embeddings is None and self.embeddings:
            self._prototype_embeddings = {}
            for rel_type, phrases in self.RELATION_PROTOTYPES.items():
                # Usar el promedio de las frases prototipo
                embeddings_list = []
                for phrase in phrases:
                    try:
                        emb = self.embeddings.encode(phrase)
                        embeddings_list.append(emb)
                    except Exception as e:
                        logger.debug(f"Error codificando frase prototipo para embeddings: {e}")
                if embeddings_list:
                    import numpy as np

                    self._prototype_embeddings[rel_type] = np.mean(embeddings_list, axis=0)
        return self._prototype_embeddings or {}

    def validate_relation(
        self,
        detected: DetectedRelation,
        context: str,
    ) -> tuple[float, str]:
        """
        Valida una relación detectada usando similitud semántica.

        Args:
            detected: Relación detectada por otro método
            context: Contexto textual de la relación

        Returns:
            (score_ajustado, razonamiento)
        """
        if not self.embeddings:
            return detected.confidence, "sin embeddings"

        prototypes = self._get_prototype_embeddings()
        if not prototypes or detected.relation_type not in prototypes:
            return detected.confidence, "sin prototipo"

        try:
            # Calcular embedding del contexto
            context_emb = self.embeddings.encode(context)

            # Calcular similitud con prototipo
            prototype_emb = prototypes[detected.relation_type]
            similarity = self.embeddings.compute_similarity_from_embeddings(
                context_emb, prototype_emb
            )

            # Ajustar confianza basado en similitud
            if similarity > 0.7:
                adjustment = 1.15  # Boost
                reasoning = f"Alta similitud semántica ({similarity:.2f})"
            elif similarity > 0.5:
                adjustment = 1.0  # Sin cambio
                reasoning = f"Similitud moderada ({similarity:.2f})"
            elif similarity > 0.3:
                adjustment = 0.9  # Pequeña penalización
                reasoning = f"Baja similitud ({similarity:.2f})"
            else:
                adjustment = 0.7  # Penalización
                reasoning = f"Muy baja similitud ({similarity:.2f})"

            new_confidence = min(1.0, detected.confidence * adjustment)
            return new_confidence, reasoning

        except Exception as e:
            logger.debug(f"Error validando con embeddings: {e}")
            return detected.confidence, "error de embeddings"


class RelationshipDetector:
    """
    Detecta relaciones a partir del texto usando múltiples técnicas.

    Técnicas implementadas:
    - Patrones regex para relaciones explícitas
    - Análisis de verbos relacionales
    - Detección de posesivos
    - Co-ocurrencia con contexto emocional
    """

    # Patrones para relaciones familiares
    FAMILY_PATTERNS = [
        # "María, madre de Juan" o "María, la madre de Juan"
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:la\s+)?madre\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.PARENT,
            0.9,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:el\s+)?padre\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.PARENT,
            0.9,
        ),
        # "el hijo de María" - captura inversa
        (
            r"(?:el\s+)?hijo\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(?:,\s*(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+))?",
            RelationType.CHILD,
            0.85,
        ),
        (
            r"(?:la\s+)?hija\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(?:,\s*(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+))?",
            RelationType.CHILD,
            0.85,
        ),
        # Hermanos
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:el\s+)?hermano\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.SIBLING,
            0.9,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:la\s+)?hermana\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.SIBLING,
            0.9,
        ),
        # "X y su madre/padre"
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+y\s+su\s+(?P<rel>madre|padre|hermano|hermana|hijo|hija)",
            None,
            0.7,
        ),  # None = se determina por grupo rel
        # Abuelos
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:el\s+)?abuelo\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.GRANDPARENT,
            0.9,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:la\s+)?abuela\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.GRANDPARENT,
            0.9,
        ),
        # Esposos
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:el\s+)?esposo\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.SPOUSE,
            0.9,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:la\s+)?esposa\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.SPOUSE,
            0.9,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:el\s+)?marido\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.SPOUSE,
            0.9,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:la\s+)?mujer\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.SPOUSE,
            0.85,
        ),
        # Tíos/primos
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:el\s+)?tío\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.UNCLE_AUNT,
            0.9,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:la\s+)?tía\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.UNCLE_AUNT,
            0.9,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:el\s+)?primo\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.COUSIN,
            0.9,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:la\s+)?prima\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.COUSIN,
            0.9,
        ),
    ]

    # Patrones para relaciones sociales
    SOCIAL_PATTERNS = [
        # Amigos
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:el\s+)?amigo\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.FRIEND,
            0.85,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:la\s+)?amiga\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.FRIEND,
            0.85,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+y\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+eran\s+(?:los\s+)?mejores\s+amigos",
            RelationType.FRIEND,
            0.9,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+y\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+eran\s+amigos",
            RelationType.FRIEND,
            0.85,
        ),
        # Enemigos
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:el\s+)?enemigo\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.ENEMY,
            0.85,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+y\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+eran\s+enemigos",
            RelationType.ENEMY,
            0.85,
        ),
        # Rivales
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:el\s+)?rival\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.RIVAL,
            0.85,
        ),
        # Mentor
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:el\s+)?mentor\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.MENTOR,
            0.85,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+(?:el\s+)?maestro\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.MENTOR,
            0.8,
        ),
    ]

    # Patrones para relaciones emocionales (verbos)
    EMOTIONAL_PATTERNS = [
        # Odio
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+odiaba\s+(?:a\s+)?(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.HATES,
            0.85,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+detestaba\s+(?:a\s+)?(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.HATES,
            0.8,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+aborrecía\s+(?:a\s+)?(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.HATES,
            0.85,
        ),
        # Miedo
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+temía\s+(?:a\s+)?(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+|el\s+\w+|la\s+\w+)",
            RelationType.FEARS,
            0.8,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+tenía\s+miedo\s+(?:de\s+)?(?:a\s+)?(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+|el\s+\w+|la\s+\w+)",
            RelationType.FEARS,
            0.85,
        ),
        # Amor
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+amaba\s+(?:a\s+)?(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.LOVER,
            0.85,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+(?:estaba\s+)?enamorad[oa]\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.LOVER,
            0.9,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+quería\s+(?:a\s+)?(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.LOVER,
            0.6,
        ),  # Menor confianza, "querer" es ambiguo
        # Admiración
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+admiraba\s+(?:a\s+)?(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.ADMIRES,
            0.85,
        ),
        # Confianza/Desconfianza
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+confiaba\s+(?:en\s+)?(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.TRUSTS,
            0.8,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+desconfiaba\s+de\s+(?P<target>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.DISTRUSTS,
            0.8,
        ),
    ]

    # Patrones para posesión
    POSSESSION_PATTERNS = [
        # "la espada de Juan", "el anillo de María"
        (
            r"(?:el|la)\s+(?P<object>\w+)\s+de\s+(?P<owner>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.OWNED_BY,
            0.6,
        ),
        # "Juan tenía una espada"
        (
            r"(?P<owner>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+tenía\s+(?:un|una)\s+(?P<object>\w+)",
            RelationType.OWNS,
            0.7,
        ),
        # "Juan poseía"
        (
            r"(?P<owner>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+poseía\s+(?:el|la|un|una)\s+(?P<object>\w+)",
            RelationType.OWNS,
            0.8,
        ),
    ]

    # Patrones espaciales
    SPATIAL_PATTERNS = [
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+vivía\s+en\s+(?P<place>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+|\w+)",
            RelationType.LIVES_IN,
            0.85,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+trabajaba\s+en\s+(?P<place>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+|\w+)",
            RelationType.WORKS_IN,
            0.8,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+nació\s+en\s+(?P<place>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+|\w+)",
            RelationType.BORN_IN,
            0.9,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+murió\s+en\s+(?P<place>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+|\w+)",
            RelationType.DIED_IN,
            0.9,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+evitaba\s+(?P<place>el\s+\w+|la\s+\w+)",
            RelationType.AVOIDS,
            0.75,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+nunca\s+(?:se\s+)?acercaba\s+(?:a\s+)?(?P<place>el\s+\w+|la\s+\w+)",
            RelationType.AVOIDS,
            0.8,
        ),
    ]

    # Patrones para membresía
    MEMBERSHIP_PATTERNS = [
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+miembro\s+de\s+(?:la\s+)?(?P<org>\w+)",
            RelationType.MEMBER_OF,
            0.85,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+fundador\s+de\s+(?:la\s+)?(?P<org>\w+)",
            RelationType.FOUNDER_OF,
            0.9,
        ),
        (
            r"(?P<source>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+),?\s+líder\s+de\s+(?:la\s+)?(?P<org>\w+)",
            RelationType.LEADER_OF,
            0.85,
        ),
    ]

    # Patrones sobrenaturales
    SUPERNATURAL_PATTERNS = [
        (
            r"(?:la\s+)?(?P<object>\w+)\s+maldita?\s+(?:de\s+)?(?P<entity>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.CURSED_BY,
            0.75,
        ),
        (
            r"(?P<entity>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+(?:estaba\s+)?maldito\s+por\s+(?P<source>\w+)",
            RelationType.CURSED_BY,
            0.8,
        ),
        (
            r"(?P<object>\w+)\s+bendecid[oa]\s+por\s+(?P<entity>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            RelationType.BLESSED_BY,
            0.8,
        ),
    ]

    def __init__(self, known_entities: list[str] | None = None):
        """
        Inicializa el detector.

        Args:
            known_entities: Lista de nombres de entidades conocidas
                           para mejorar la precisión de detección
        """
        self.known_entities = set(known_entities or [])
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compila todos los patrones regex."""
        self._compiled_patterns = []

        all_patterns = (
            self.FAMILY_PATTERNS
            + self.SOCIAL_PATTERNS
            + self.EMOTIONAL_PATTERNS
            + self.POSSESSION_PATTERNS
            + self.SPATIAL_PATTERNS
            + self.MEMBERSHIP_PATTERNS
            + self.SUPERNATURAL_PATTERNS
        )

        for pattern_tuple in all_patterns:
            pattern, rel_type, confidence = pattern_tuple
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                self._compiled_patterns.append((compiled, rel_type, confidence))
            except re.error as e:
                logger.warning(f"Error compilando patrón: {pattern} - {e}")

    def detect_from_text(
        self,
        text: str,
        chapter: int = 0,
        entities: list[str] | None = None,
    ) -> list[DetectedRelation]:
        """
        Detecta relaciones en un texto.

        Args:
            text: Texto a analizar
            chapter: Número de capítulo
            entities: Lista opcional de entidades conocidas en este texto

        Returns:
            Lista de relaciones detectadas
        """
        detected = []
        working_entities = entities or self.known_entities

        for compiled, rel_type, confidence in self._compiled_patterns:
            for match in compiled.finditer(text):
                groups = match.groupdict()

                # Obtener source y target
                source = groups.get("source", "")
                target = groups.get("target", "")

                # Algunos patrones usan nombres diferentes
                if not source:
                    source = groups.get("owner", groups.get("entity", ""))
                if not target:
                    target = groups.get("object", groups.get("place", groups.get("org", "")))

                # Determinar tipo de relación si es None (patrón genérico)
                actual_rel_type = rel_type
                if rel_type is None:
                    rel_group = groups.get("rel", "")
                    actual_rel_type = self._get_relation_from_word(rel_group)

                if not source or not target or not actual_rel_type:
                    continue

                # Ajustar confianza si conocemos las entidades
                adjusted_confidence = confidence
                if working_entities:
                    if source in working_entities:
                        adjusted_confidence += 0.1
                    if target in working_entities:
                        adjusted_confidence += 0.1
                    adjusted_confidence = min(1.0, adjusted_confidence)

                detected.append(
                    DetectedRelation(
                        source_name=source.strip(),
                        target_name=target.strip(),
                        relation_type=actual_rel_type,
                        evidence_text=match.group(0),
                        chapter=chapter,
                        start_char=match.start(),
                        end_char=match.end(),
                        confidence=adjusted_confidence,
                        detection_method="pattern",
                    )
                )

        # Eliminar duplicados (misma relación detectada por múltiples patrones)
        return self._deduplicate_relations(detected)

    def _get_relation_from_word(self, word: str) -> RelationType | None:
        """Determina tipo de relación desde palabra clave."""
        word = word.lower()
        mapping = {
            "madre": RelationType.PARENT,
            "padre": RelationType.PARENT,
            "hermano": RelationType.SIBLING,
            "hermana": RelationType.SIBLING,
            "hijo": RelationType.CHILD,
            "hija": RelationType.CHILD,
            "abuelo": RelationType.GRANDPARENT,
            "abuela": RelationType.GRANDPARENT,
            "tío": RelationType.UNCLE_AUNT,
            "tía": RelationType.UNCLE_AUNT,
            "primo": RelationType.COUSIN,
            "prima": RelationType.COUSIN,
            "esposo": RelationType.SPOUSE,
            "esposa": RelationType.SPOUSE,
            "amigo": RelationType.FRIEND,
            "amiga": RelationType.FRIEND,
            "enemigo": RelationType.ENEMY,
        }
        return mapping.get(word)

    def _deduplicate_relations(
        self,
        relations: list[DetectedRelation],
    ) -> list[DetectedRelation]:
        """Elimina relaciones duplicadas, manteniendo la de mayor confianza."""
        seen = {}

        for rel in relations:
            key = (rel.source_name.lower(), rel.target_name.lower(), rel.relation_type)
            if key not in seen or rel.confidence > seen[key].confidence:
                seen[key] = rel

        return list(seen.values())

    def detect_from_dialogue(
        self,
        dialogue: str,
        speaker: str,
        context_entities: list[str],
        chapter: int = 0,
    ) -> list[DetectedRelation]:
        """
        Detecta relaciones a partir de diálogos.

        Analiza qué dice un personaje sobre otros para inferir relaciones.

        Args:
            dialogue: Texto del diálogo
            speaker: Nombre del hablante
            context_entities: Entidades mencionadas en contexto
            chapter: Número de capítulo

        Returns:
            Lista de relaciones detectadas
        """
        detected = []

        # Patrones específicos para diálogos
        dialogue_patterns = [
            # "Te quiero" dirigido a alguien
            (r"te\s+(?:quiero|amo)", RelationType.LOVER, 0.75),
            # "Te odio"
            (r"te\s+odio", RelationType.HATES, 0.85),
            # "Eres mi amigo"
            (r"eres\s+mi\s+amigo", RelationType.FRIEND, 0.8),
            # "No confío en ti"
            (r"no\s+conf[ií]o\s+en\s+ti", RelationType.DISTRUSTS, 0.8),
            # "Confío en ti"
            (r"conf[ií]o\s+en\s+ti", RelationType.TRUSTS, 0.8),
        ]

        # Si hay un solo receptor probable en el contexto
        if len(context_entities) == 1:
            receiver = context_entities[0]

            for pattern, rel_type, confidence in dialogue_patterns:
                if re.search(pattern, dialogue, re.IGNORECASE):
                    detected.append(
                        DetectedRelation(
                            source_name=speaker,
                            target_name=receiver,
                            relation_type=rel_type,
                            evidence_text=dialogue,
                            chapter=chapter,
                            confidence=confidence,
                            detection_method="dialogue",
                        )
                    )

        # Detectar menciones a terceros
        # "Mi hermano Juan..."
        third_person_patterns = [
            (
                r"mi\s+(?P<rel>hermano|hermana|padre|madre|hijo|hija)\s+(?P<name>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
                None,
                0.85,
            ),
            (
                r"(?P<name>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+es\s+mi\s+(?P<rel>hermano|hermana|padre|madre|amigo|amiga|enemigo)",
                None,
                0.85,
            ),
        ]

        for pattern, _, confidence in third_person_patterns:
            compiled = re.compile(pattern, re.IGNORECASE)
            for match in compiled.finditer(dialogue):
                groups = match.groupdict()
                name = groups.get("name", "")
                rel_word = groups.get("rel", "")

                rel_type = self._get_relation_from_word(rel_word)
                if rel_type and name:
                    detected.append(
                        DetectedRelation(
                            source_name=speaker,
                            target_name=name,
                            relation_type=rel_type,
                            evidence_text=match.group(0),
                            chapter=chapter,
                            confidence=confidence,
                            detection_method="dialogue",
                        )
                    )

        return detected

    def convert_to_relationships(
        self,
        detected: list[DetectedRelation],
        project_id: int = 0,
        entity_id_map: dict[str, str] | None = None,
    ) -> list[EntityRelationship]:
        """
        Convierte relaciones detectadas a EntityRelationship.

        Args:
            detected: Lista de DetectedRelation
            project_id: ID del proyecto
            entity_id_map: Mapeo de nombre -> entity_id

        Returns:
            Lista de EntityRelationship
        """
        relationships = []
        entity_id_map = entity_id_map or {}

        for det in detected:
            source_id = entity_id_map.get(det.source_name.lower(), "")
            target_id = entity_id_map.get(det.target_name.lower(), "")

            evidence = RelationshipEvidence(
                text=det.evidence_text,
                reference=TextReference(
                    chapter=det.chapter,
                    char_start=det.start_char,
                    char_end=det.end_char,
                ),
                behavior_type="other",
                confidence=det.confidence,
            )

            rel = EntityRelationship(
                project_id=project_id,
                source_entity_id=source_id,
                target_entity_id=target_id,
                source_entity_name=det.source_name,
                target_entity_name=det.target_name,
                relation_type=det.relation_type,
                first_mention_chapter=det.chapter,
                last_mention_chapter=det.chapter,
                evidence=[evidence],
                evidence_texts=[det.evidence_text],
                confidence=det.confidence,
            )

            relationships.append(rel)

        return relationships


def detect_relationships_from_text(
    text: str,
    chapter: int = 0,
    known_entities: list[str] | None = None,
) -> list[DetectedRelation]:
    """
    Función de conveniencia para detectar relaciones (solo patrones).

    Args:
        text: Texto a analizar
        chapter: Número de capítulo
        known_entities: Lista de entidades conocidas

    Returns:
        Lista de relaciones detectadas
    """
    detector = RelationshipDetector(known_entities)
    return detector.detect_from_text(text, chapter, known_entities)


# =============================================================================
# Sistema de Votación Multi-Método
# =============================================================================


@dataclass
class RelationDetectionResult:
    """
    Resultado de la detección de relaciones con votación.

    Attributes:
        relations: Relaciones detectadas y validadas
        method_contributions: Cuántas relaciones aportó cada método
        processing_time_ms: Tiempo de procesamiento
        consensus_stats: Estadísticas de consenso entre métodos
    """

    relations: list[DetectedRelation] = field(default_factory=list)
    method_contributions: dict[str, int] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    consensus_stats: dict[str, float] = field(default_factory=dict)

    @property
    def total_relations(self) -> int:
        return len(self.relations)

    @property
    def high_confidence_count(self) -> int:
        return sum(1 for r in self.relations if r.confidence >= 0.7)


class VotingRelationshipDetector:
    """
    Detector de relaciones con votación multi-método.

    Combina múltiples técnicas de detección y usa votación ponderada
    para determinar las relaciones finales con mayor precisión.

    Métodos disponibles:
    - PATTERNS: Patrones regex explícitos (rápido, alta precisión en explícitos)
    - DEPENDENCY: Análisis de dependencias sintácticas (captura verbos relacionales)
    - LLM: LLM local para comprensión semántica profunda (relaciones implícitas)
    - EMBEDDINGS: Validación semántica con embeddings (ajusta confianza)

    Example:
        >>> detector = VotingRelationshipDetector()
        >>> result = detector.detect(text, entities=["Juan", "María"])
        >>> for rel in result.relations:
        ...     print(f"{rel.source_name} -> {rel.relation_type.value} -> {rel.target_name}")
    """

    def __init__(
        self,
        config: RelationDetectionConfig | None = None,
        known_entities: list[str] | None = None,
    ):
        """
        Inicializa el detector con votación.

        Args:
            config: Configuración del sistema de votación
            known_entities: Lista de entidades conocidas
        """
        self.config = config or RelationDetectionConfig()
        self.known_entities = set(known_entities or [])

        # Inicializar métodos
        self._pattern_detector = RelationshipDetector(known_entities)
        self._dependency_method: DependencyRelationMethod | None = None
        self._llm_method: LLMRelationMethod | None = None
        self._embeddings_method: EmbeddingsRelationMethod | None = None

        self._init_methods()

        logger.info(
            f"VotingRelationshipDetector inicializado con métodos: "
            f"{[m.value for m in self.config.enabled_methods]}"
        )

    def _init_methods(self) -> None:
        """Inicializa los métodos de detección habilitados."""
        for method in self.config.enabled_methods:
            try:
                if method == RelationDetectionMethod.DEPENDENCY:
                    self._dependency_method = DependencyRelationMethod()
                elif method == RelationDetectionMethod.LLM:
                    self._llm_method = LLMRelationMethod(
                        model=self.config.ollama_model, timeout=self.config.ollama_timeout
                    )
                elif method == RelationDetectionMethod.EMBEDDINGS:
                    self._embeddings_method = EmbeddingsRelationMethod()
                # PATTERNS siempre está disponible via _pattern_detector
            except Exception as e:
                logger.warning(f"No se pudo inicializar método {method.value}: {e}")

    def detect(
        self,
        text: str,
        chapter: int = 0,
        entities: list[str] | None = None,
    ) -> RelationDetectionResult:
        """
        Detecta relaciones usando votación multi-método.

        Args:
            text: Texto a analizar
            chapter: Número de capítulo
            entities: Lista de entidades conocidas

        Returns:
            RelationDetectionResult con relaciones y estadísticas
        """
        import time

        start_time = time.time()

        result = RelationDetectionResult()
        working_entities = list(entities or self.known_entities)

        # Recolectar candidatos de cada método
        all_candidates: dict[
            tuple[str, str, RelationType],
            list[tuple[DetectedRelation, float, str, RelationDetectionMethod]],
        ] = {}

        # 1. Detección por patrones (siempre activo)
        if RelationDetectionMethod.PATTERNS in self.config.enabled_methods:
            pattern_results = self._pattern_detector.detect_from_text(
                text, chapter, working_entities
            )
            for rel in pattern_results:
                key = (rel.source_name.lower(), rel.target_name.lower(), rel.relation_type)
                if key not in all_candidates:
                    all_candidates[key] = []
                all_candidates[key].append(
                    (rel, rel.confidence, "patrón explícito", RelationDetectionMethod.PATTERNS)
                )
            result.method_contributions["patterns"] = len(pattern_results)

        # 2. Detección por dependencias
        if (
            RelationDetectionMethod.DEPENDENCY in self.config.enabled_methods
            and self._dependency_method
        ):
            try:
                dep_results = self._dependency_method.detect(text, chapter, working_entities)
                for rel, score, reasoning in dep_results:
                    key = (rel.source_name.lower(), rel.target_name.lower(), rel.relation_type)
                    if key not in all_candidates:
                        all_candidates[key] = []
                    all_candidates[key].append(
                        (rel, score, reasoning, RelationDetectionMethod.DEPENDENCY)
                    )
                result.method_contributions["dependency"] = len(dep_results)
            except Exception as e:
                logger.debug(f"Error en detección por dependencias: {e}")

        # 3. Detección por LLM
        if RelationDetectionMethod.LLM in self.config.enabled_methods and self._llm_method:
            try:
                llm_results = self._llm_method.detect(text, chapter, working_entities)
                for rel, score, reasoning in llm_results:
                    key = (rel.source_name.lower(), rel.target_name.lower(), rel.relation_type)
                    if key not in all_candidates:
                        all_candidates[key] = []
                    all_candidates[key].append((rel, score, reasoning, RelationDetectionMethod.LLM))
                result.method_contributions["llm"] = len(llm_results)
            except Exception as e:
                logger.debug(f"Error en detección LLM: {e}")

        # 4. Votación y consolidación
        result.relations = self._vote_and_consolidate(all_candidates, text)

        # 5. Validación con embeddings (ajusta confianza)
        if (
            RelationDetectionMethod.EMBEDDINGS in self.config.enabled_methods
            and self._embeddings_method
        ):
            result.relations = self._validate_with_embeddings(result.relations, text)

        # Calcular estadísticas
        result.processing_time_ms = (time.time() - start_time) * 1000
        result.consensus_stats = self._calculate_consensus_stats(result.relations)

        logger.info(
            f"Detección completada: {result.total_relations} relaciones, "
            f"{result.high_confidence_count} alta confianza, "
            f"{result.processing_time_ms:.1f}ms"
        )

        return result

    def _vote_and_consolidate(
        self,
        candidates: dict[tuple, list[tuple]],
        text: str,
    ) -> list[DetectedRelation]:
        """
        Aplica votación ponderada y consolida candidatos.

        Args:
            candidates: Candidatos agrupados por (source, target, type)
            text: Texto original

        Returns:
            Lista de relaciones consolidadas
        """
        consolidated = []

        for _key, votes in candidates.items():
            if not votes:
                continue

            # Calcular score ponderado
            total_weight = 0.0
            weighted_sum = 0.0
            methods_agreed = []
            reasoning_parts = {}

            for _rel, score, reasoning, method in votes:
                weight = self.config.method_weights.get(method, 0.1)
                weighted_sum += score * weight
                total_weight += weight
                methods_agreed.append(method.value)
                reasoning_parts[method.value] = reasoning

            if total_weight == 0:
                continue

            base_score = weighted_sum / total_weight

            # Bonus por consenso entre métodos
            num_methods = len(set(methods_agreed))
            if num_methods >= 2:
                consensus_bonus = AGREEMENT_BONUS
                base_score = min(1.0, base_score * consensus_bonus)

            # Verificar umbral de confianza
            if base_score < self.config.min_confidence:
                continue

            # Usar la mejor evidencia disponible
            best_vote = max(votes, key=lambda v: v[1])
            best_rel = best_vote[0]

            # Crear relación consolidada
            consolidated_rel = DetectedRelation(
                source_name=best_rel.source_name,
                target_name=best_rel.target_name,
                relation_type=best_rel.relation_type,
                evidence_text=best_rel.evidence_text,
                chapter=best_rel.chapter,
                start_char=best_rel.start_char,
                end_char=best_rel.end_char,
                confidence=base_score,
                detection_method="voting",
                methods_agreed=list(set(methods_agreed)),
                reasoning=reasoning_parts,
            )

            consolidated.append(consolidated_rel)

        # Ordenar por confianza
        consolidated.sort(key=lambda r: r.confidence, reverse=True)

        return consolidated

    def _validate_with_embeddings(
        self,
        relations: list[DetectedRelation],
        text: str,
    ) -> list[DetectedRelation]:
        """Valida y ajusta confianza usando embeddings semánticos."""
        if not self._embeddings_method:
            return relations

        validated = []
        for rel in relations:
            # Obtener contexto de la relación
            context_start = max(0, rel.start_char - 100)
            context_end = min(len(text), rel.end_char + 100)
            context = text[context_start:context_end]

            # Validar con embeddings
            new_confidence, reasoning = self._embeddings_method.validate_relation(rel, context)

            # Actualizar relación
            rel.confidence = new_confidence
            rel.reasoning["embeddings"] = reasoning
            if "embeddings" not in rel.methods_agreed:
                rel.methods_agreed.append("embeddings")

            validated.append(rel)

        return validated

    def _calculate_consensus_stats(
        self,
        relations: list[DetectedRelation],
    ) -> dict[str, float]:
        """Calcula estadísticas de consenso."""
        if not relations:
            return {}

        total = len(relations)
        single_method = sum(1 for r in relations if len(r.methods_agreed) == 1)
        multi_method = sum(1 for r in relations if len(r.methods_agreed) >= 2)
        high_consensus = sum(1 for r in relations if len(r.methods_agreed) >= 3)

        return {
            "single_method_pct": single_method / total * 100,
            "multi_method_pct": multi_method / total * 100,
            "high_consensus_pct": high_consensus / total * 100 if total > 0 else 0,
            "avg_confidence": sum(r.confidence for r in relations) / total,
        }


# =============================================================================
# Singleton y Funciones de Conveniencia
# =============================================================================

_voting_detector_lock = threading.Lock()
_voting_detector: VotingRelationshipDetector | None = None


def get_voting_relationship_detector(
    config: RelationDetectionConfig | None = None,
    known_entities: list[str] | None = None,
) -> VotingRelationshipDetector:
    """
    Obtiene el singleton del detector de relaciones con votación.

    Args:
        config: Configuración opcional
        known_entities: Entidades conocidas

    Returns:
        Instancia del VotingRelationshipDetector
    """
    global _voting_detector

    if _voting_detector is None:
        with _voting_detector_lock:
            if _voting_detector is None:
                _voting_detector = VotingRelationshipDetector(config, known_entities)

    return _voting_detector


def reset_voting_detector() -> None:
    """Resetea el singleton (útil para tests)."""
    global _voting_detector
    with _voting_detector_lock:
        _voting_detector = None


def detect_relationships_voting(
    text: str,
    chapter: int = 0,
    entities: list[str] | None = None,
    config: RelationDetectionConfig | None = None,
) -> RelationDetectionResult:
    """
    Función de conveniencia para detectar relaciones con votación multi-método.

    Esta es la función recomendada para obtener relaciones de alta calidad.

    Args:
        text: Texto a analizar
        chapter: Número de capítulo
        entities: Lista de entidades conocidas
        config: Configuración opcional

    Returns:
        RelationDetectionResult con relaciones y estadísticas

    Example:
        >>> result = detect_relationships_voting(text, entities=["Juan", "María"])
        >>> for rel in result.relations:
        ...     print(f"{rel.source_name} -> {rel.relation_type.value} -> {rel.target_name}")
        ...     print(f"  Confianza: {rel.confidence:.2f}")
        ...     print(f"  Métodos: {', '.join(rel.methods_agreed)}")
    """
    detector = VotingRelationshipDetector(config, entities)
    return detector.detect(text, chapter, entities)
