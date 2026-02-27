"""
Sistema de clustering para reducir complejidad O(N²) en fusion de entidades.

Estrategia:
1. Pre-filter por similaridad textual rápida (difflib, n-gramas)
2. Clustering jerárquico por distancia de Levenshtein
3. Solo comparar pares DENTRO de cada cluster (embeddings costosos)

Reducción esperada:
- 1000 entidades = ~500K pares → clustering → ~5K pares (100x menos)
- Threshold: solo clústeres con > 1 elemento
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher

from ..entities.models import Entity, EntityType
from ..entities.semantic_fusion import normalize_for_comparison, strip_accents

logger = logging.getLogger(__name__)

# Umbral de similaridad para incluir en mismo cluster
# Valores más bajos = clusters más inclusivos (más pares a comparar)
# Valores más altos = clusters más estrictos (menos pares pero posibles pérdidas)
CLUSTERING_SIMILARITY_THRESHOLD = 0.45

# Tamaño mínimo de nombre para aplicar clustering agresivo
MIN_NAME_LENGTH_FOR_CLUSTERING = 3


@dataclass
class EntityCluster:
    """
    Cluster de entidades con nombres similares.

    Attributes:
        cluster_id: ID único del cluster
        entities: Entidades en el cluster
        representative_name: Nombre representativo (el más completo)
        entity_type: Tipo de entidades en el cluster
    """

    cluster_id: int
    entities: list[Entity]
    representative_name: str
    entity_type: EntityType

    def __len__(self) -> int:
        return len(self.entities)


def _name_fingerprint(name: str) -> str:
    """
    Genera fingerprint de nombre para agrupamiento rápido.

    Normaliza y ordena alfabéticamente las palabras para
    detectar variantes del mismo nombre.

    Examples:
        >>> _name_fingerprint("María Sánchez García")
        'garcia maria sanchez'
        >>> _name_fingerprint("García Sánchez María")
        'garcia maria sanchez'
        >>> _name_fingerprint("Don García Sánchez")
        'garcia sanchez'  # Don se quita en normalización
    """
    normalized = normalize_for_comparison(name)
    if not normalized:
        return ""

    # Ordenar alfabéticamente las palabras
    words = sorted(normalized.split())
    return " ".join(words)


def _fast_name_similarity(name1: str, name2: str) -> float:
    """
    Calcula similaridad rápida entre nombres (sin embeddings).

    Usa difflib.SequenceMatcher que es O(N*M) pero muy rápido
    comparado con embeddings.

    Args:
        name1: Primer nombre
        name2: Segundo nombre

    Returns:
        Similaridad entre 0.0 y 1.0
    """
    n1 = normalize_for_comparison(name1)
    n2 = normalize_for_comparison(name2)

    if not n1 or not n2:
        return 0.0

    # Exacto
    if n1 == n2:
        return 1.0

    # Contención a nivel de PALABRAS (no subcadena arbitraria)
    # "garcia" in "maria garcia" → OK (palabra completa)
    # "a" in "maria garcia" → RECHAZADO (subcadena, no palabra)
    words1 = set(n1.split())
    words2 = set(n2.split())
    if words1 and words2 and (words1 <= words2 or words2 <= words1):
        shorter = min(len(n1), len(n2))
        longer = max(len(n1), len(n2))
        # Requiere que la parte más corta tenga al menos 3 caracteres
        if shorter >= 3:
            return 0.75 + (shorter / longer) * 0.2  # 0.75-0.95

    # SequenceMatcher rápido
    return SequenceMatcher(None, n1, n2).ratio()


def _create_ngrams(text: str, n: int = 2) -> set[str]:
    """
    Genera n-gramas de caracteres de un texto.

    Útil para detectar similaridad parcial entre nombres.

    Args:
        text: Texto a procesar
        n: Tamaño del n-grama (default: 2 = bigramas)

    Returns:
        Set de n-gramas

    Examples:
        >>> _create_ngrams("garcia", 2)
        {'ga', 'ar', 'rc', 'ci', 'ia'}
    """
    text = strip_accents(text.lower())
    if len(text) < n:
        return {text}

    return {text[i : i + n] for i in range(len(text) - n + 1)}


def _ngram_similarity(name1: str, name2: str, n: int = 2) -> float:
    """
    Calcula similaridad por n-gramas (Jaccard similarity).

    Más robusto que SequenceMatcher para nombres con errores
    ortográficos o variantes.

    Args:
        name1: Primer nombre
        name2: Segundo nombre
        n: Tamaño del n-grama

    Returns:
        Similaridad Jaccard entre 0.0 y 1.0
    """
    ngrams1 = _create_ngrams(name1, n)
    ngrams2 = _create_ngrams(name2, n)

    if not ngrams1 or not ngrams2:
        return 0.0

    intersection = len(ngrams1 & ngrams2)
    union = len(ngrams1 | ngrams2)

    return intersection / union if union > 0 else 0.0


def cluster_entities_by_name_similarity(
    entities: list[Entity],
    similarity_threshold: float = CLUSTERING_SIMILARITY_THRESHOLD,
) -> list[EntityCluster]:
    """
    Agrupa entidades en clusters por similaridad de nombre.

    Estrategia:
    1. Fingerprint inicial (agrupar nombres idénticos después de normalizar)
    2. Similaridad textual rápida para agrupar variantes
    3. N-gramas para detectar nombres con errores/variaciones

    Args:
        entities: Lista de entidades a agrupar
        similarity_threshold: Umbral mínimo de similaridad

    Returns:
        Lista de clusters (solo clusters con > 1 entidad)

    Examples:
        >>> entities = [Entity(canonical_name="María García"), ...]
        >>> clusters = cluster_entities_by_name_similarity(entities)
        >>> for cluster in clusters:
        ...     print(f"Cluster {cluster.cluster_id}: {len(cluster)} entidades")
    """
    if not entities:
        return []

    # Fase 1: Agrupamiento por fingerprint (O(N))
    fingerprint_groups: dict[str, list[Entity]] = defaultdict(list)
    for entity in entities:
        fp = _name_fingerprint(entity.canonical_name)
        if fp:  # Ignorar nombres vacíos
            fingerprint_groups[fp].append(entity)

    # Fase 2: Refinar con similaridad textual (O(N²) pero solo dentro de grupos pequeños)
    clusters: list[EntityCluster] = []
    cluster_id_counter = 0

    for fingerprint, fp_entities in fingerprint_groups.items():
        if len(fp_entities) == 1:
            # Entidad única, no hay cluster
            continue

        # Si fingerprint es idéntico, todas las entidades del grupo van al mismo cluster
        # (ej: "María García" y "García María" normalizan a "garcia maria")
        if len(fp_entities) >= 2:
            # Elegir nombre representativo (el más largo)
            representative = max(
                (e.canonical_name for e in fp_entities),
                key=lambda n: (len(n), n),  # Primero por longitud, luego alfabético
            )
            clusters.append(
                EntityCluster(
                    cluster_id=cluster_id_counter,
                    entities=fp_entities,
                    representative_name=representative,
                    entity_type=fp_entities[0].entity_type,
                )
            )
            cluster_id_counter += 1
            continue

    # Fase 3: Agrupar entidades que NO matchean por fingerprint pero sí por similaridad
    # Esto cubre casos como "María Sánchez" vs "Mari Sanchez" (sin tilde, diminutivo)
    unclustered = [e for e in entities if e not in sum([c.entities for c in clusters], [])]

    if len(unclustered) > 1:
        # Crear grupos por similaridad textual rápida
        visited: set[int] = set()

        for i, entity1 in enumerate(unclustered):
            if i in visited:
                continue

            cluster_members: list[Entity] = [entity1]
            visited.add(i)

            for j, entity2 in enumerate(unclustered):
                if j <= i or j in visited:
                    continue

                # Calcular similaridad (rápido: difflib + n-gramas)
                sim_difflib = _fast_name_similarity(
                    entity1.canonical_name, entity2.canonical_name
                )
                sim_ngram = _ngram_similarity(entity1.canonical_name, entity2.canonical_name, n=3)

                # Combinar ambas métricas (promedio ponderado)
                similarity = 0.6 * sim_difflib + 0.4 * sim_ngram

                if similarity >= similarity_threshold:
                    cluster_members.append(entity2)
                    visited.add(j)

            # Solo crear cluster si hay > 1 miembro
            if len(cluster_members) >= 2:
                representative = max(
                    (e.canonical_name for e in cluster_members),
                    key=lambda n: (len(n), n),
                )
                clusters.append(
                    EntityCluster(
                        cluster_id=cluster_id_counter,
                        entities=cluster_members,
                        representative_name=representative,
                        entity_type=cluster_members[0].entity_type,
                    )
                )
                cluster_id_counter += 1

    # Log estadísticas
    total_entities = len(entities)
    clustered_entities = sum(len(c) for c in clusters)
    unclustered_count = total_entities - clustered_entities

    logger.info(
        f"Clustering completado: {len(clusters)} clusters, "
        f"{clustered_entities} entidades agrupadas, "
        f"{unclustered_count} sin agrupar"
    )

    return clusters


def compute_reduced_pairs_from_clusters(
    entities: list[Entity],
    similarity_threshold: float = CLUSTERING_SIMILARITY_THRESHOLD,
) -> list[tuple[Entity, Entity]]:
    """
    Genera pares de entidades a comparar usando clustering.

    Solo retorna pares DENTRO de cada cluster, reduciendo drásticamente
    el número de comparaciones de embeddings costosos.

    Args:
        entities: Lista de entidades
        similarity_threshold: Umbral de clustering

    Returns:
        Lista de pares (entity1, entity2) a comparar con embeddings

    Examples:
        >>> pairs = compute_reduced_pairs_from_clusters(entities)
        >>> # 1000 entidades → ~500K pares (sin clustering)
        >>> # 1000 entidades → ~5K pares (con clustering, reducción 100x)
    """
    clusters = cluster_entities_by_name_similarity(entities, similarity_threshold)

    pairs: list[tuple[Entity, Entity]] = []

    for cluster in clusters:
        # Comparar solo pares dentro del cluster
        cluster_entities = cluster.entities
        for i, ent1 in enumerate(cluster_entities):
            for j in range(i + 1, len(cluster_entities)):
                ent2 = cluster_entities[j]
                pairs.append((ent1, ent2))

    # Estadísticas
    total_possible_pairs = (len(entities) * (len(entities) - 1)) // 2
    reduction_factor = total_possible_pairs / len(pairs) if pairs else 0

    logger.info(
        f"Pares reducidos: {len(pairs)} (de {total_possible_pairs} posibles) "
        f"→ reducción {reduction_factor:.1f}x"
    )

    return pairs


def cluster_by_entity_type(
    entities: list[Entity],
) -> dict[EntityType, list[EntityCluster]]:
    """
    Agrupa entidades por tipo y luego aplica clustering de nombres.

    Args:
        entities: Lista de entidades

    Returns:
        Dict de {entity_type: [clusters]}
    """
    entities_by_type: dict[EntityType, list[Entity]] = defaultdict(list)
    for entity in entities:
        entities_by_type[entity.entity_type].append(entity)

    result: dict[EntityType, list[EntityCluster]] = {}
    for entity_type, type_entities in entities_by_type.items():
        if len(type_entities) >= 2:
            clusters = cluster_entities_by_name_similarity(type_entities)
            if clusters:
                result[entity_type] = clusters
                logger.info(
                    f"Tipo {entity_type.value}: {len(type_entities)} entidades "
                    f"→ {len(clusters)} clusters"
                )

    return result
