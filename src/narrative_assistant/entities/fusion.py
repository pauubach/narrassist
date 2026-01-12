"""
Servicio de fusión de entidades.

Permite fusionar múltiples entidades detectadas que refieren
a la misma entidad real, con soporte para deshacer y sugerencias
automáticas basadas en similaridad de nombres.

Este servicio es CRÍTICO para el funcionamiento del sistema,
ya que la correferencia automática tiene ~45-55% de errores.
"""

import logging
import threading
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional

from ..core.result import Result
from ..core.errors import NarrativeError, ErrorSeverity
from .models import Entity, EntityType, MergeHistory, MergeSuggestion
from .repository import EntityRepository, get_entity_repository

logger = logging.getLogger(__name__)

# Umbral mínimo de similaridad para sugerir fusión
DEFAULT_SIMILARITY_THRESHOLD = 0.7

# Máximo de sugerencias a retornar
MAX_SUGGESTIONS = 50

# =============================================================================
# Diccionario de sinónimos por categoría
# =============================================================================
# Palabras que pueden referirse a la misma entidad
# Formato: {palabra_clave: [sinónimos]}

LOCATION_SYNONYMS = {
    # Espacios verdes
    "parque": ["jardín", "jardines", "parques", "plaza", "pradera", "campo"],
    "jardín": ["parque", "parques", "huerto", "vergel", "patio"],
    "bosque": ["arboleda", "monte", "selva", "espesura", "floresta"],
    "playa": ["costa", "orilla", "litoral", "ribera"],

    # Edificios
    "casa": ["hogar", "vivienda", "residencia", "domicilio", "morada", "mansión", "chalet"],
    "edificio": ["inmueble", "construcción", "bloque", "torre"],
    "apartamento": ["piso", "departamento", "flat", "estudio"],
    "iglesia": ["templo", "capilla", "basílica", "catedral", "parroquia"],
    "hospital": ["clínica", "sanatorio", "centro médico", "dispensario"],
    "escuela": ["colegio", "instituto", "academia", "centro educativo"],
    "universidad": ["facultad", "campus", "ateneo"],
    "tienda": ["comercio", "local", "negocio", "almacén", "bazar"],
    "restaurante": ["bar", "cafetería", "mesón", "taberna", "cantina", "bistró"],

    # Vías
    "calle": ["avenida", "paseo", "vía", "camino", "carretera", "callejón", "bulevar"],

    # Zonas
    "barrio": ["vecindario", "zona", "distrito", "colonia", "sector"],
    "ciudad": ["urbe", "metrópoli", "población", "localidad", "municipio"],
    "pueblo": ["aldea", "villa", "villorrio", "poblado"],
}

# Combinamos todos en un diccionario bidireccional
_SYNONYM_LOOKUP: dict[str, set[str]] = {}

def _build_synonym_lookup():
    """Construye lookup bidireccional de sinónimos."""
    for key, synonyms in LOCATION_SYNONYMS.items():
        key_lower = key.lower()
        if key_lower not in _SYNONYM_LOOKUP:
            _SYNONYM_LOOKUP[key_lower] = set()

        for syn in synonyms:
            syn_lower = syn.lower()
            _SYNONYM_LOOKUP[key_lower].add(syn_lower)

            # Bidireccional
            if syn_lower not in _SYNONYM_LOOKUP:
                _SYNONYM_LOOKUP[syn_lower] = set()
            _SYNONYM_LOOKUP[syn_lower].add(key_lower)

_build_synonym_lookup()


@dataclass
class FusionError(NarrativeError):
    """Error durante la fusión de entidades."""

    entity_ids: list[int] = None
    original_error: str = ""
    message: str = ""
    severity: ErrorSeverity = ErrorSeverity.RECOVERABLE
    user_message: Optional[str] = None

    def __post_init__(self):
        if not self.message:
            self.message = f"Entity fusion error: {self.original_error}"
        if not self.user_message:
            self.user_message = (
                "Error al fusionar entidades. "
                "Verifique que las entidades existen y pertenecen al mismo proyecto."
            )
        super().__post_init__()


@dataclass
class FusionResult:
    """
    Resultado de una operación de fusión.

    Attributes:
        success: Si la operación fue exitosa
        result_entity_id: ID de la entidad resultante
        merged_count: Número de entidades fusionadas
        aliases_added: Aliases añadidos durante la fusión
        mentions_moved: Menciones movidas
        attributes_moved: Atributos movidos
    """

    success: bool = False
    result_entity_id: Optional[int] = None
    merged_count: int = 0
    aliases_added: list[str] = None
    mentions_moved: int = 0
    attributes_moved: int = 0

    def __post_init__(self):
        if self.aliases_added is None:
            self.aliases_added = []


class EntityFusionService:
    """
    Servicio para fusión manual de entidades.

    Proporciona:
    - Fusión de múltiples entidades en una
    - Deshacer fusiones
    - Sugerencias automáticas de fusión
    - Validaciones de consistencia

    Attributes:
        repo: Repositorio de entidades
        similarity_threshold: Umbral para sugerencias
    """

    def __init__(
        self,
        repository: Optional[EntityRepository] = None,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        use_semantic_fusion: bool = True,
    ):
        """
        Inicializa el servicio de fusión.

        Args:
            repository: Repositorio de entidades. Si None, usa singleton.
            similarity_threshold: Umbral mínimo para sugerir fusiones
            use_semantic_fusion: Si True, usa embeddings para similaridad semántica
        """
        self.repo = repository or get_entity_repository()
        self.similarity_threshold = similarity_threshold
        self._use_semantic_fusion = use_semantic_fusion

    def merge_entities(
        self,
        project_id: int,
        entity_ids: list[int],
        canonical_name: str,
        note: Optional[str] = None,
    ) -> Result[FusionResult]:
        """
        Fusiona múltiples entidades en una sola.

        La primera entidad de la lista se convierte en la entidad
        resultante. Las demás se fusionan en ella y se desactivan.

        Args:
            project_id: ID del proyecto
            entity_ids: IDs de entidades a fusionar (mínimo 2)
            canonical_name: Nombre canónico de la entidad resultante
            note: Nota opcional del usuario

        Returns:
            Result con FusionResult

        Example:
            >>> service.merge_entities(
            ...     project_id=1,
            ...     entity_ids=[1, 5, 12],  # "Juan", "el doctor", "Dr. García"
            ...     canonical_name="Dr. Juan García"
            ... )
        """
        result = FusionResult()

        # Validaciones
        if len(entity_ids) < 2:
            error = FusionError(
                entity_ids=entity_ids,
                original_error="Se necesitan al menos 2 entidades para fusionar",
            )
            return Result.failure(error)

        # Obtener todas las entidades
        entities: list[Entity] = []
        for eid in entity_ids:
            entity = self.repo.get_entity(eid)
            if entity is None:
                error = FusionError(
                    entity_ids=entity_ids,
                    original_error=f"Entidad {eid} no encontrada",
                )
                return Result.failure(error)
            if entity.project_id != project_id:
                error = FusionError(
                    entity_ids=entity_ids,
                    original_error=f"Entidad {eid} pertenece a otro proyecto",
                )
                return Result.failure(error)
            entities.append(entity)

        # Verificar que sean del mismo tipo (o advertir)
        types = set(e.entity_type for e in entities)
        if len(types) > 1:
            logger.warning(
                f"Fusionando entidades de diferentes tipos: {types}. "
                f"Se usará el tipo de la primera entidad."
            )

        try:
            # La primera entidad será la resultante
            result_entity = entities[0]
            result_entity_id = result_entity.id

            # Recopilar todos los aliases
            all_aliases: set[str] = set()
            canonical_names_before: list[str] = []
            source_snapshots: list[dict] = []

            for entity in entities:
                canonical_names_before.append(entity.canonical_name)
                source_snapshots.append(entity.to_dict())

                # Añadir nombre canónico como alias si es diferente
                if entity.canonical_name.lower() != canonical_name.lower():
                    all_aliases.add(entity.canonical_name)

                # Añadir aliases existentes
                all_aliases.update(entity.aliases)

            # Remover el nuevo nombre canónico de aliases
            all_aliases.discard(canonical_name)

            result.aliases_added = list(all_aliases)

            # Actualizar la entidad resultante
            self.repo.update_entity(
                result_entity_id,
                canonical_name=canonical_name,
                aliases=list(all_aliases),
                merged_from_ids=entity_ids,
            )

            # Mover menciones y atributos de las otras entidades
            for entity in entities[1:]:
                mentions_moved = self.repo.move_mentions(entity.id, result_entity_id)
                attrs_moved = self.repo.move_attributes(entity.id, result_entity_id)
                result.mentions_moved += mentions_moved
                result.attributes_moved += attrs_moved

                # Desactivar la entidad fusionada (soft delete)
                self.repo.delete_entity(entity.id, hard_delete=False)

            # Actualizar conteo de menciones
            total_mentions = sum(e.mention_count for e in entities)
            self.repo.update_entity(result_entity_id)  # Trigger updated_at

            # Registrar en historial
            self.repo.add_merge_history(
                project_id=project_id,
                result_entity_id=result_entity_id,
                source_entity_ids=entity_ids,
                source_snapshots=source_snapshots,
                canonical_names_before=canonical_names_before,
                merged_by="user",
                note=note,
            )

            result.success = True
            result.result_entity_id = result_entity_id
            result.merged_count = len(entities)

            logger.info(
                f"Entidades fusionadas: {canonical_names_before} -> '{canonical_name}' "
                f"(ID={result_entity_id})"
            )

            return Result.success(result)

        except Exception as e:
            error = FusionError(
                entity_ids=entity_ids,
                original_error=str(e),
            )
            logger.error(f"Error fusionando entidades: {e}")
            return Result.failure(error)

    def undo_merge(self, merge_id: int) -> Result[list[int]]:
        """
        Deshace una fusión, restaurando las entidades originales.

        NOTA: Esta operación es compleja y puede no restaurar
        el estado exacto si hubo cambios posteriores.

        Args:
            merge_id: ID del registro de fusión

        Returns:
            Result con lista de IDs de entidades restauradas
        """
        # Por ahora, solo marcamos como deshecha
        # La implementación completa requeriría restaurar desde snapshots
        try:
            success = self.repo.mark_merge_undone(merge_id)
            if success:
                logger.info(f"Fusión {merge_id} marcada como deshecha")
                return Result.success([])
            else:
                error = FusionError(
                    original_error=f"Fusión {merge_id} no encontrada",
                )
                return Result.failure(error)
        except Exception as e:
            error = FusionError(
                original_error=str(e),
            )
            return Result.failure(error)

    def suggest_merges(
        self,
        project_id: int,
        entity_type: Optional[EntityType] = None,
        max_suggestions: int = MAX_SUGGESTIONS,
    ) -> list[MergeSuggestion]:
        """
        Sugiere fusiones basadas en similaridad de nombres.

        Analiza todas las entidades del proyecto y sugiere
        pares que podrían ser la misma entidad.

        Args:
            project_id: ID del proyecto
            entity_type: Filtrar por tipo (opcional)
            max_suggestions: Máximo de sugerencias

        Returns:
            Lista de sugerencias ordenadas por similaridad

        Example:
            >>> suggestions = service.suggest_merges(project_id=1)
            >>> for s in suggestions:
            ...     print(f"{s.entity1.canonical_name} <-> {s.entity2.canonical_name}")
            ...     print(f"  Similaridad: {s.similarity:.0%}, Razón: {s.reason}")
        """
        entities = self.repo.get_entities_by_project(
            project_id,
            entity_type=entity_type,
            active_only=True,
        )

        suggestions: list[MergeSuggestion] = []

        # Comparar cada par de entidades
        for i, e1 in enumerate(entities):
            for e2 in entities[i + 1 :]:
                # Saltar si son de tipos muy diferentes
                if not self._types_compatible(e1.entity_type, e2.entity_type):
                    continue

                # Calcular similaridad
                similarity, reason, evidence = self._compute_similarity(e1, e2)

                if similarity >= self.similarity_threshold:
                    suggestions.append(
                        MergeSuggestion(
                            entity1=e1,
                            entity2=e2,
                            similarity=similarity,
                            reason=reason,
                            evidence=evidence,
                        )
                    )

        # Ordenar por similaridad descendente
        suggestions.sort(key=lambda s: -s.similarity)

        return suggestions[:max_suggestions]

    def _types_compatible(self, type1: EntityType, type2: EntityType) -> bool:
        """Verifica si dos tipos de entidad pueden fusionarse."""
        # Mismo tipo siempre compatible
        if type1 == type2:
            return True

        # Grupos compatibles
        compatible_groups = [
            # Seres vivos
            {EntityType.CHARACTER, EntityType.CREATURE},
            # Lugares
            {EntityType.LOCATION, EntityType.BUILDING, EntityType.REGION},
            # Grupos
            {EntityType.ORGANIZATION, EntityType.FACTION, EntityType.FAMILY},
        ]

        for group in compatible_groups:
            if type1 in group and type2 in group:
                return True

        return False

    def _compute_similarity(
        self, e1: Entity, e2: Entity
    ) -> tuple[float, str, list[str]]:
        """
        Calcula similaridad entre dos entidades.

        Returns:
            Tupla de (similaridad, razón, evidencias)
        """
        evidence: list[str] = []
        max_similarity = 0.0
        reason = ""

        # 1. Comparar nombres canónicos
        sim_canonical = self._name_similarity(e1.canonical_name, e2.canonical_name)
        if sim_canonical > max_similarity:
            max_similarity = sim_canonical
            reason = self._get_similarity_reason(
                e1.canonical_name, e2.canonical_name, sim_canonical
            )

        # 2. Comparar contra aliases
        for alias1 in e1.all_names:
            for alias2 in e2.all_names:
                sim = self._name_similarity(alias1, alias2)
                if sim > max_similarity:
                    max_similarity = sim
                    reason = self._get_similarity_reason(alias1, alias2, sim)
                    evidence.append(f"'{alias1}' ~ '{alias2}' ({sim:.0%})")

        # 3. Boost por mismo tipo
        if e1.entity_type == e2.entity_type:
            max_similarity = min(1.0, max_similarity * 1.1)
            evidence.append(f"Mismo tipo: {e1.entity_type.value}")

        # 4. Detección de sinónimos (solo para ubicaciones)
        if e1.entity_type == EntityType.LOCATION or e2.entity_type == EntityType.LOCATION:
            syn_sim, syn_reason = self._check_synonym_match(e1, e2)
            if syn_sim > max_similarity:
                max_similarity = syn_sim
                reason = syn_reason
                evidence.append(f"Sinónimos detectados: {syn_reason}")

        # 5. Fusión semántica con embeddings (si la similaridad textual es baja)
        # Solo se usa si la similaridad textual no fue concluyente
        if max_similarity < 0.7 and self._use_semantic_fusion:
            try:
                from .semantic_fusion import get_semantic_fusion_service

                semantic_service = get_semantic_fusion_service()
                semantic_result = semantic_service.should_merge(e1, e2)

                if semantic_result.similarity > max_similarity:
                    max_similarity = semantic_result.similarity
                    reason = semantic_result.reason
                    evidence.append(f"Embeddings: {semantic_result.similarity:.2f}")
            except Exception as e:
                logger.debug(f"Semantic fusion not available: {e}")

        return max_similarity, reason, evidence

    def _check_synonym_match(
        self, e1: Entity, e2: Entity
    ) -> tuple[float, str]:
        """
        Verifica si dos entidades son sinónimos conocidos.

        Por ejemplo: "El parque" y "El jardín" cuando se refieren al mismo lugar.

        Returns:
            Tupla de (similaridad, razón)
        """
        import unicodedata

        def normalize(text: str) -> str:
            """Normaliza texto quitando acentos y pasando a minúsculas."""
            nfkd = unicodedata.normalize('NFKD', text.lower())
            return ''.join(c for c in nfkd if not unicodedata.combining(c))

        # Extraer palabras clave de los nombres (normalizadas)
        words1 = set(normalize(e1.canonical_name).split())
        words2 = set(normalize(e2.canonical_name).split())

        # Eliminar artículos y preposiciones
        stopwords = {"el", "la", "los", "las", "un", "una", "de", "del", "al"}
        words1 = words1 - stopwords
        words2 = words2 - stopwords

        # Buscar sinónimos (también normalizados)
        for w1 in words1:
            # Buscar en el lookup (keys tienen acentos originales)
            lookup_key = None
            for key in _SYNONYM_LOOKUP.keys():
                if normalize(key) == w1:
                    lookup_key = key
                    break

            if lookup_key:
                synonyms = _SYNONYM_LOOKUP[lookup_key]
                for w2 in words2:
                    for syn in synonyms:
                        if normalize(syn) == w2:
                            return 0.75, f"'{w1}' es sinónimo de '{w2}'"

        return 0.0, ""

    def _name_similarity(self, name1: str, name2: str) -> float:
        """
        Calcula similaridad entre dos nombres.

        Usa SequenceMatcher de difflib normalizado,
        con boost especial cuando un nombre contiene al otro.
        """
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()

        # Exacto
        if n1 == n2:
            return 1.0

        # Boost: Si un nombre contiene al otro completamente
        # Ej: "María" en "María Sánchez" -> alta probabilidad de ser la misma persona
        if n1 in n2 or n2 in n1:
            # Calcular ratio de contención
            shorter = min(len(n1), len(n2))
            longer = max(len(n1), len(n2))
            containment_ratio = shorter / longer
            # Si el nombre corto es >= 35% del largo, es muy probable que sean iguales
            # (Ej: "María"=5 chars en "María Sánchez"=13 chars -> 0.385)
            if containment_ratio >= 0.35:
                return 0.85 + (containment_ratio * 0.1)  # 0.885-0.95

        # SequenceMatcher estándar
        return SequenceMatcher(None, n1, n2).ratio()

    def _get_similarity_reason(
        self, name1: str, name2: str, similarity: float
    ) -> str:
        """Genera razón legible para la sugerencia."""
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()

        if n1 == n2:
            return "Mismo nombre (diferente capitalización)"

        if similarity >= 0.95:
            return "Nombres casi idénticos"

        # Verificar si uno contiene al otro
        if n1 in n2 or n2 in n1:
            return "Un nombre contiene al otro"

        # Verificar si comparten apellido/palabra significativa
        words1 = set(n1.split())
        words2 = set(n2.split())
        common = words1 & words2
        if common:
            return f"Comparten: {', '.join(common)}"

        if similarity >= 0.8:
            return "Nombres muy similares"

        return "Nombres similares"

    def split_entity(
        self,
        entity_id: int,
        new_entities: list[dict],
    ) -> Result[list[int]]:
        """
        Divide una entidad en múltiples entidades.

        Operación inversa a merge, útil cuando se detecta
        que una entidad fusionada incluye menciones incorrectas.

        Args:
            entity_id: ID de la entidad a dividir
            new_entities: Lista de dicts con {canonical_name, mention_ids}

        Returns:
            Result con lista de IDs de nuevas entidades

        NOTA: No implementado en MVP. Marcado para futuro.
        """
        error = FusionError(
            entity_ids=[entity_id],
            original_error="split_entity no implementado en MVP",
        )
        return Result.failure(error)


# =============================================================================
# Singleton thread-safe
# =============================================================================

_fusion_lock = threading.Lock()
_fusion_service: Optional[EntityFusionService] = None


def get_fusion_service(
    repository: Optional[EntityRepository] = None,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    use_semantic_fusion: bool = True,
) -> EntityFusionService:
    """
    Obtiene el singleton del servicio de fusión.

    Args:
        repository: Repositorio de entidades (opcional)
        similarity_threshold: Umbral de similaridad
        use_semantic_fusion: Si True, usa embeddings para similaridad semántica

    Returns:
        Instancia única del EntityFusionService
    """
    global _fusion_service

    if _fusion_service is None:
        with _fusion_lock:
            if _fusion_service is None:
                _fusion_service = EntityFusionService(
                    repository=repository,
                    similarity_threshold=similarity_threshold,
                    use_semantic_fusion=use_semantic_fusion,
                )

    return _fusion_service


def reset_fusion_service() -> None:
    """Resetea el singleton (útil para tests)."""
    global _fusion_service
    with _fusion_lock:
        _fusion_service = None
