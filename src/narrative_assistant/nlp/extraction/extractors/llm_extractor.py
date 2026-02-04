"""
Extractor basado en LLM local (Ollama) con soporte multi-modelo.

Este extractor puede usar uno o varios modelos de lenguaje locales para:
1. Extraer atributos de textos complejos
2. Comparar respuestas de múltiples modelos (ensemble)
3. Usar votación ponderada para máxima precisión

IMPORTANTE: Solo usa modelos LOCALES para mantener privacidad.
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from ..base import (
    AttributeType,
    BaseExtractor,
    ExtractedAttribute,
    ExtractionContext,
    ExtractionMethod,
    ExtractionResult,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuración de modelos
# =============================================================================


@dataclass
class LLMModelConfig:
    """Configuración de un modelo LLM."""

    name: str  # Nombre en Ollama (ej: "mistral:7b-instruct")
    display_name: str  # Nombre para mostrar
    weight: float = 1.0  # Peso en votación (1.0 = normal)
    temperature: float = 0.1  # Temperatura (baja = más determinista)
    context_length: int = 4096  # Longitud de contexto
    ram_required_gb: int = 8  # RAM requerida aproximada
    quality_spanish: int = 5  # Calidad en español (1-5)


# Modelos recomendados para español, ordenados por calidad
RECOMMENDED_MODELS = [
    LLMModelConfig(
        name="mistral:7b-instruct",
        display_name="Mistral 7B Instruct",
        weight=1.2,  # Boost por excelente español
        quality_spanish=5,
        ram_required_gb=8,
    ),
    LLMModelConfig(
        name="llama3.1:8b",
        display_name="Llama 3.1 8B",
        weight=1.1,
        quality_spanish=5,
        ram_required_gb=8,
    ),
    LLMModelConfig(
        name="qwen2:7b",
        display_name="Qwen2 7B",
        weight=1.1,
        quality_spanish=5,
        ram_required_gb=8,
    ),
    LLMModelConfig(
        name="phi3:mini",
        display_name="Phi-3 Mini",
        weight=0.9,  # Ligeramente menor por ser más pequeño
        quality_spanish=4,
        ram_required_gb=4,
    ),
    LLMModelConfig(
        name="gemma2:9b",
        display_name="Gemma 2 9B",
        weight=1.0,
        quality_spanish=4,
        ram_required_gb=10,
    ),
]

# Mapa rápido por nombre
MODELS_BY_NAME = {m.name: m for m in RECOMMENDED_MODELS}


# =============================================================================
# Prompts
# =============================================================================

EXTRACTION_PROMPT_ES = """Eres un asistente experto en análisis de texto narrativo en español.

TEXTO A ANALIZAR:
{text}

PERSONAJES CONOCIDOS:
{entities}

TAREA:
Extrae TODOS los atributos físicos de los personajes mencionados en el texto.

TIPOS DE ATRIBUTOS:
- eye_color: color de ojos (azul, verde, marrón, negro, gris, avellana, violeta)
- hair_color: color de pelo (negro, rubio, castaño, pelirrojo, canoso, gris, blanco)
- hair_type: tipo de pelo (largo, corto, rizado, liso, ondulado, recogido, trenzado)
- height: altura (alto, bajo, mediano, muy alto)
- build: complexión (delgado, fornido, robusto, atlético, corpulento, esbelto)
- age: edad (joven, mayor, anciano, niño, adolescente, "treinta años")
- skin: piel (pálido, moreno, bronceado, pecoso, escamoso)

REGLAS IMPORTANTES:
1. Si dice "sus ojos", "su cabello", etc. y hay UN SOLO personaje mencionado antes, asigna el atributo a ese personaje
2. Si dice "ella/él tenía" después de mencionar un personaje, asigna a ese personaje
3. SOLO extrae información EXPLÍCITA en el texto, NO inventes
4. Incluye el fragmento exacto del texto como evidencia

FORMATO DE RESPUESTA (JSON puro):
[
  {{"entity": "Nombre del personaje", "attribute": "tipo_atributo", "value": "valor", "evidence": "fragmento textual"}}
]

Si no hay atributos físicos, responde: []

RESPUESTA:"""


# =============================================================================
# Resultado de un modelo individual
# =============================================================================


@dataclass
class SingleModelResult:
    """Resultado de extracción de un solo modelo."""

    model_name: str
    attributes: list[dict]  # Atributos crudos del JSON
    raw_response: str
    success: bool
    error: str | None = None
    latency_ms: float = 0.0


@dataclass
class EnsembleVote:
    """Voto de ensemble para un atributo."""

    entity: str
    attribute_type: str
    value: str
    evidence: str
    votes: list[tuple[str, float]]  # [(model_name, weight), ...]
    total_weight: float = 0.0
    consensus: str = "single"  # "unanimous", "majority", "contested", "single"


# =============================================================================
# Extractor Multi-LLM
# =============================================================================


class LLMExtractor(BaseExtractor):
    """
    Extractor de atributos usando uno o varios LLMs locales (Ollama).

    Soporta dos modos:
    1. **Modelo único**: Usa un solo modelo (rápido)
    2. **Ensemble**: Usa varios modelos y vota (más preciso)

    REQUISITOS:
    - Ollama instalado: https://ollama.com/download
    - Al menos un modelo descargado:
      ```
      ollama pull mistral:7b-instruct
      ollama pull llama3.1:8b
      ollama pull phi3:mini
      ```

    Example (modelo único):
        >>> extractor = LLMExtractor(model_name="mistral:7b-instruct")
        >>> result = extractor.extract(context)

    Example (ensemble):
        >>> extractor = LLMExtractor(
        ...     use_ensemble=True,
        ...     ensemble_models=["mistral:7b-instruct", "llama3.1:8b", "phi3:mini"]
        ... )
        >>> result = extractor.extract(context)
    """

    def __init__(
        self,
        # Modo simple
        model_name: str = "mistral:7b-instruct",
        # Modo ensemble
        use_ensemble: bool = False,
        ensemble_models: list[str] | None = None,
        min_votes_for_consensus: int = 2,
        # Configuración general
        base_url: str = "http://localhost:11434",
        timeout: int = 600,  # 10 min - CPU sin GPU es lento
        max_parallel_models: int = 3,
    ):
        """
        Inicializa el extractor.

        Args:
            model_name: Modelo a usar en modo simple
            use_ensemble: Si True, usa múltiples modelos
            ensemble_models: Lista de modelos para ensemble (None = todos disponibles)
            min_votes_for_consensus: Mínimo de votos para considerar consenso
            base_url: URL del servidor Ollama
            timeout: Timeout por modelo en segundos
            max_parallel_models: Máximo de modelos en paralelo
        """
        self._model_name = model_name
        self._use_ensemble = use_ensemble
        self._ensemble_models = ensemble_models
        self._min_votes = min_votes_for_consensus
        self._base_url = base_url
        self._timeout = timeout
        self._max_parallel = max_parallel_models

        self._client = None
        self._available_models: list[str] | None = None

    @property
    def method(self) -> ExtractionMethod:
        return ExtractionMethod.SEMANTIC_LLM

    @property
    def supported_attributes(self) -> set[AttributeType]:
        return {
            AttributeType.EYE_COLOR,
            AttributeType.HAIR_COLOR,
            AttributeType.HAIR_TYPE,
            AttributeType.HEIGHT,
            AttributeType.BUILD,
            AttributeType.AGE,
            AttributeType.SKIN,
            AttributeType.DISTINCTIVE_FEATURE,
        }

    def _get_client(self):
        """Lazy loading del cliente Ollama."""
        if self._client is None:
            try:
                import ollama

                self._client = ollama.Client(host=self._base_url)
            except ImportError:
                raise RuntimeError(
                    "Ollama no instalado. Ejecuta: pip install ollama\n"
                    "Y luego instala Ollama desde: https://ollama.com/download"
                )
        return self._client

    def get_available_models(self) -> list[str]:
        """
        Obtiene lista de modelos disponibles en Ollama.

        Returns:
            Lista de nombres de modelos instalados
        """
        if self._available_models is not None:
            return self._available_models

        try:
            client = self._get_client()
            response = client.list()
            models = response.get("models", [])
            self._available_models = [m.get("name", "") for m in models]
            logger.info(f"Modelos Ollama disponibles: {self._available_models}")
        except Exception as e:
            logger.warning(f"No se pudo obtener lista de modelos: {e}")
            self._available_models = []

        return self._available_models

    def get_recommended_models(self, max_ram_gb: int = 16) -> list[LLMModelConfig]:
        """
        Obtiene modelos recomendados según RAM disponible.

        Args:
            max_ram_gb: RAM máxima disponible

        Returns:
            Lista de configuraciones de modelos recomendados
        """
        available = set(self.get_available_models())
        recommended = []

        for config in RECOMMENDED_MODELS:
            # Verificar si está instalado (comparar sin tag de versión)
            model_base = config.name.split(":")[0]
            is_available = any(model_base in avail for avail in available)

            if is_available and config.ram_required_gb <= max_ram_gb:
                recommended.append(config)

        return recommended

    def can_handle(self, context: ExtractionContext) -> float:
        """
        Evalúa capacidad de manejar el contexto.

        Retorna 0 si Ollama no está disponible.
        """
        available = self.get_available_models()
        if not available:
            return 0.0

        # Verificar que al menos un modelo esté disponible
        if self._use_ensemble:
            models_to_use = self._get_ensemble_models()
            if not models_to_use:
                return 0.0
        else:
            model_base = self._model_name.split(":")[0]
            if not any(model_base in m for m in available):
                return 0.0

        # LLM es mejor para textos medianos/complejos
        word_count = len(context.text.split())
        if 30 <= word_count <= 1000:
            return 0.8
        return 0.6

    def _get_ensemble_models(self) -> list[str]:
        """Obtiene lista de modelos para ensemble."""
        if self._ensemble_models:
            # Filtrar solo los que están disponibles
            available = set(self.get_available_models())
            return [
                m for m in self._ensemble_models if any(m.split(":")[0] in a for a in available)
            ]

        # Si no se especificaron, usar todos los disponibles que conocemos
        available = self.get_available_models()
        ensemble = []
        for config in RECOMMENDED_MODELS:
            model_base = config.name.split(":")[0]
            for avail in available:
                if model_base in avail:
                    ensemble.append(avail)
                    break

        return ensemble[: self._max_parallel]  # Limitar

    def extract(self, context: ExtractionContext) -> ExtractionResult:
        """
        Extrae atributos usando LLM(s).

        En modo ensemble, ejecuta varios modelos y combina resultados.
        """
        if self._use_ensemble:
            return self._extract_ensemble(context)
        else:
            return self._extract_single(context)

    def _extract_single(self, context: ExtractionContext) -> ExtractionResult:
        """Extracción con un solo modelo."""
        attributes = []
        errors = []

        result = self._call_model(self._model_name, context)

        if result.success:
            for item in result.attributes:
                attr = self._convert_to_attribute(item, context)
                if attr:
                    attributes.append(attr)
        else:
            errors.append(result.error or "Error desconocido")

        return self._create_result(attributes, errors)

    def _extract_ensemble(self, context: ExtractionContext) -> ExtractionResult:
        """
        Extracción con múltiples modelos (ensemble).

        1. Ejecuta todos los modelos en paralelo
        2. Recopila atributos de cada uno
        3. Vota para determinar atributos finales
        """
        attributes = []
        errors = []
        model_results: list[SingleModelResult] = []

        models = self._get_ensemble_models()
        if not models:
            errors.append("No hay modelos disponibles para ensemble")
            return self._create_result(attributes, errors)

        logger.info(f"Ejecutando ensemble con {len(models)} modelos: {models}")

        # Ejecutar modelos en paralelo
        with ThreadPoolExecutor(max_workers=self._max_parallel) as executor:
            futures = {executor.submit(self._call_model, model, context): model for model in models}

            for future in as_completed(futures):
                model_name = futures[future]
                try:
                    result = future.result()
                    model_results.append(result)
                    if result.success:
                        logger.debug(
                            f"{model_name}: {len(result.attributes)} atributos "
                            f"({result.latency_ms:.0f}ms)"
                        )
                    else:
                        logger.warning(f"{model_name}: {result.error}")
                except Exception as e:
                    logger.error(f"{model_name} falló: {e}")

        # Votar y combinar resultados
        if model_results:
            voted_attrs = self._vote_attributes(model_results, context)
            attributes.extend(voted_attrs)

        successful = sum(1 for r in model_results if r.success)
        logger.info(
            f"Ensemble completado: {successful}/{len(models)} modelos exitosos, "
            f"{len(attributes)} atributos finales"
        )

        return self._create_result(attributes, errors)

    def _call_model(
        self,
        model_name: str,
        context: ExtractionContext,
    ) -> SingleModelResult:
        """
        Llama a un modelo específico.

        Returns:
            SingleModelResult con atributos extraídos
        """
        import time

        start_time = time.time()

        try:
            client = self._get_client()

            # Obtener configuración del modelo
            config = MODELS_BY_NAME.get(
                model_name, LLMModelConfig(name=model_name, display_name=model_name)
            )

            # Preparar prompt
            prompt = EXTRACTION_PROMPT_ES.format(
                text=context.text[:3000],  # Limitar texto
                entities=", ".join(context.entity_names),
            )

            # Llamar a Ollama
            response = client.generate(
                model=model_name,
                prompt=prompt,
                options={
                    "temperature": config.temperature,
                    "num_ctx": config.context_length,
                },
            )

            raw_response = response.get("response", "").strip()
            latency_ms = (time.time() - start_time) * 1000

            # Parsear JSON
            attributes = self._parse_json_response(raw_response)

            return SingleModelResult(
                model_name=model_name,
                attributes=attributes,
                raw_response=raw_response,
                success=True,
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return SingleModelResult(
                model_name=model_name,
                attributes=[],
                raw_response="",
                success=False,
                error=str(e),
                latency_ms=latency_ms,
            )

    def _parse_json_response(self, response_text: str) -> list[dict]:
        """Parsea respuesta JSON del LLM."""
        try:
            # Buscar array JSON
            start = response_text.find("[")
            end = response_text.rfind("]") + 1

            if start >= 0 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)

            return []

        except json.JSONDecodeError:
            logger.debug(f"Error parseando JSON: {response_text[:200]}")
            return []

    def _vote_attributes(
        self,
        model_results: list[SingleModelResult],
        context: ExtractionContext,
    ) -> list[ExtractedAttribute]:
        """
        Vota para determinar atributos finales.

        Agrupa atributos por (entidad, tipo, valor) y cuenta votos.
        """
        # Agrupar votos por (entity, attribute_type, value_normalized)
        votes: dict[tuple, EnsembleVote] = {}

        for result in model_results:
            if not result.success:
                continue

            # Obtener peso del modelo
            config = MODELS_BY_NAME.get(
                result.model_name,
                LLMModelConfig(name=result.model_name, display_name=result.model_name),
            )
            weight = config.weight

            for item in result.attributes:
                entity = item.get("entity", "").strip()
                attr_type = item.get("attribute", "").strip().lower()
                value = item.get("value", "").strip().lower()
                evidence = item.get("evidence", "")

                if not entity or not attr_type or not value:
                    continue

                # Normalizar entidad
                matched_entity = self._match_entity(entity, context.entity_names)
                if not matched_entity:
                    continue

                # Clave única
                key = (matched_entity.lower(), attr_type, value)

                if key not in votes:
                    votes[key] = EnsembleVote(
                        entity=matched_entity,
                        attribute_type=attr_type,
                        value=value,
                        evidence=evidence,
                        votes=[],
                    )

                votes[key].votes.append((result.model_name, weight))
                votes[key].total_weight += weight

        # Determinar consenso y crear atributos
        attributes = []
        total_models = sum(1 for r in model_results if r.success)

        for key, vote in votes.items():
            num_votes = len(vote.votes)

            # Determinar nivel de consenso
            if num_votes == total_models and total_models > 1:
                vote.consensus = "unanimous"
                confidence_boost = 1.15
            elif num_votes >= self._min_votes:
                vote.consensus = "majority"
                confidence_boost = 1.0
            elif num_votes == 1 and total_models > 1:
                vote.consensus = "single"
                confidence_boost = 0.8
            else:
                vote.consensus = "contested"
                confidence_boost = 0.9

            # Calcular confianza final
            avg_weight = vote.total_weight / num_votes
            base_confidence = 0.75 + (0.05 * num_votes)  # Más votos = más confianza
            final_confidence = min(0.98, base_confidence * avg_weight * confidence_boost)

            # Mapear tipo de atributo
            try:
                attr_type = AttributeType(vote.attribute_type)
            except ValueError:
                attr_type = AttributeType.OTHER

            attributes.append(
                self._create_attribute(
                    entity_name=vote.entity,
                    attr_type=attr_type,
                    value=vote.value,
                    confidence=final_confidence,
                    source_text=vote.evidence or f"Ensemble ({vote.consensus})",
                    chapter=context.chapter,
                )
            )

            logger.debug(
                f"Voto: {vote.entity}.{vote.attribute_type}={vote.value} "
                f"({num_votes}/{total_models} votos, {vote.consensus}, "
                f"conf={final_confidence:.2f})"
            )

        return attributes

    def _match_entity(
        self,
        entity_name: str,
        known_entities: list[str],
    ) -> str | None:
        """Encuentra la entidad conocida que coincide."""
        entity_lower = entity_name.lower()

        for known in known_entities:
            known_lower = known.lower()
            # Coincidencia exacta
            if entity_lower == known_lower:
                return known
            # Contención
            if entity_lower in known_lower or known_lower in entity_lower:
                return known

        return None

    def _convert_to_attribute(
        self,
        item: dict,
        context: ExtractionContext,
    ) -> ExtractedAttribute | None:
        """Convierte item del LLM a ExtractedAttribute."""
        entity = item.get("entity", "")
        attr_type_str = item.get("attribute", "other")
        value = item.get("value", "")
        evidence = item.get("evidence", "")

        if not entity or not value:
            return None

        matched_entity = self._match_entity(entity, context.entity_names)
        if not matched_entity:
            return None

        try:
            attr_type = AttributeType(attr_type_str)
        except ValueError:
            attr_type = AttributeType.OTHER

        return self._create_attribute(
            entity_name=matched_entity,
            attr_type=attr_type,
            value=value.lower().strip(),
            confidence=0.80,
            source_text=evidence or context.text[:100],
            chapter=context.chapter,
        )


# =============================================================================
# Funciones de utilidad
# =============================================================================


def list_available_models(base_url: str = "http://localhost:11434") -> list[str]:
    """
    Lista modelos disponibles en Ollama.

    Returns:
        Lista de nombres de modelos
    """
    try:
        import ollama

        client = ollama.Client(host=base_url)
        response = client.list()
        return [m.get("name", "") for m in response.get("models", [])]
    except Exception as e:
        logger.warning(f"Error listando modelos: {e}")
        return []


def get_recommended_ensemble(max_ram_gb: int = 16) -> list[str]:
    """
    Obtiene configuración de ensemble recomendada según RAM.

    Args:
        max_ram_gb: RAM disponible en GB

    Returns:
        Lista de nombres de modelos para ensemble
    """
    available = set(list_available_models())
    ensemble = []

    for config in RECOMMENDED_MODELS:
        if config.ram_required_gb > max_ram_gb:
            continue

        model_base = config.name.split(":")[0]
        for avail in available:
            if model_base in avail:
                ensemble.append(avail)
                break

    # Máximo 3 modelos para un buen balance tiempo/precisión
    return ensemble[:3]
