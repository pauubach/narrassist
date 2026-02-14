"""
Sistema de clustering para relaciones entre personajes.

Combina múltiples técnicas con votación:
1. Co-ocurrencia (quién aparece con quién)
2. Clustering jerárquico (dendrogramas)
3. Community detection (Louvain)
4. Embeddings + clustering

El sistema usa votación ponderada para combinar resultados.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


class RelationStrength(Enum):
    """Fuerza de la relación inferida."""

    NONE = 0
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    VERY_STRONG = 4


class RelationValence(Enum):
    """Valencia emocional de la relación."""

    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1
    UNKNOWN = 2


@dataclass
class CoOccurrence:
    """Registro de co-ocurrencia entre dos entidades."""

    entity1_id: int
    entity2_id: int
    chapter: int
    scene: int | None = None
    distance_chars: int = 0  # Distancia en caracteres
    context: str = ""  # Contexto textual


@dataclass
class InferredRelation:
    """Relación inferida entre dos entidades."""

    entity1_id: int
    entity2_id: int
    entity1_name: str
    entity2_name: str
    strength: RelationStrength
    valence: RelationValence
    confidence: float  # 0.0 - 1.0

    # Evidencias de cada técnica
    cooccurrence_score: float = 0.0
    hierarchical_cluster: int | None = None
    community_id: int | None = None
    embedding_similarity: float = 0.0

    # Votos de cada técnica (True si sugieren relación)
    votes: dict = field(default_factory=dict)

    # Evidencias textuales
    evidence_contexts: list[str] = field(default_factory=list)
    chapters_together: list[int] = field(default_factory=list)

    def __post_init__(self):
        if not self.votes:
            self.votes = {}


@dataclass
class CharacterCluster:
    """Grupo de personajes relacionados."""

    id: int
    name: str  # Nombre descriptivo del grupo (autogenerado)
    entity_ids: list[int]
    entity_names: list[str]
    centroid_entity_id: int | None = None  # Personaje central (más conectado)
    centroid_entity_name: str | None = None  # Nombre del personaje central
    cohesion_score: float = 0.0  # Qué tan cohesivo es el grupo
    custom_name: str | None = None  # Nombre personalizado por el usuario

    # Metadatos
    detection_method: str = ""  # "hierarchical", "louvain", "voting"
    chapters_active: list[int] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        """Retorna el nombre a mostrar: custom_name si existe, sino name."""
        return self.custom_name if self.custom_name else self.name


@dataclass
class KnowledgeAsymmetry:
    """Asimetría de conocimiento: qué sabe A de B vs B de A."""

    entity_a_id: int
    entity_b_id: int
    entity_a_name: str
    entity_b_name: str

    # Lo que A sabe de B
    a_knows_about_b: list[str] = field(default_factory=list)
    a_knowledge_chapters: list[int] = field(default_factory=list)

    # Lo que B sabe de A
    b_knows_about_a: list[str] = field(default_factory=list)
    b_knowledge_chapters: list[int] = field(default_factory=list)

    # Asimetría: >0 si A sabe más de B, <0 si B sabe más de A
    asymmetry_score: float = 0.0


class RelationshipClusteringEngine:
    """
    Motor de clustering para detectar relaciones entre personajes.

    Combina múltiples técnicas con votación ponderada:
    - Co-ocurrencia: frecuencia de aparición conjunta
    - Dendrograma: clustering jerárquico por similitud
    - Community detection: algoritmo de Louvain
    - Embeddings: similitud semántica de contextos
    """

    # Pesos para votación (suman 1.0)
    WEIGHTS = {
        "cooccurrence": 0.30,
        "hierarchical": 0.25,
        "community": 0.25,
        "embedding": 0.20,
    }

    # Umbrales
    COOCCURRENCE_THRESHOLD = 3  # Mínimo co-ocurrencias para considerar relación
    DISTANCE_THRESHOLD = 500  # Caracteres máximos para considerar "cerca"
    RELATION_CONFIDENCE_THRESHOLD = 0.5  # Confianza mínima para reportar

    def __init__(
        self,
        use_embeddings: bool = True,
        embedding_model=None,
    ):
        """
        Inicializa el motor de clustering.

        Args:
            use_embeddings: Si usar embeddings para similitud semántica
            embedding_model: Modelo de embeddings (opcional)
        """
        self.use_embeddings = use_embeddings
        self.embedding_model = embedding_model

        # Datos de análisis
        self._cooccurrences: list[CoOccurrence] = []
        self._entity_names: dict[int, str] = {}
        self._entity_contexts: dict[int, list[str]] = defaultdict(list)

        # Resultados
        self._relations: list[InferredRelation] = []
        self._clusters: list[CharacterCluster] = []
        self._knowledge_asymmetries: list[KnowledgeAsymmetry] = []

    def add_cooccurrence(
        self,
        entity1_id: int,
        entity2_id: int,
        entity1_name: str,
        entity2_name: str,
        chapter: int,
        scene: int | None = None,
        distance_chars: int = 0,
        context: str = "",
    ) -> None:
        """Registra una co-ocurrencia entre dos entidades."""
        # Normalizar orden (menor ID primero)
        if entity1_id > entity2_id:
            entity1_id, entity2_id = entity2_id, entity1_id
            entity1_name, entity2_name = entity2_name, entity1_name

        self._cooccurrences.append(
            CoOccurrence(
                entity1_id=entity1_id,
                entity2_id=entity2_id,
                chapter=chapter,
                scene=scene,
                distance_chars=distance_chars,
                context=context,
            )
        )

        # Guardar nombres y contextos
        self._entity_names[entity1_id] = entity1_name
        self._entity_names[entity2_id] = entity2_name

        if context:
            self._entity_contexts[entity1_id].append(context)
            self._entity_contexts[entity2_id].append(context)

    def analyze(self) -> dict:
        """
        Ejecuta análisis completo con todas las técnicas.

        Returns:
            Diccionario con resultados:
            - relations: Lista de relaciones inferidas
            - clusters: Grupos de personajes
            - knowledge_asymmetries: Asimetrías de conocimiento
            - dendrogram_data: Datos para visualizar dendrograma
        """
        if not self._cooccurrences:
            logger.warning("No hay co-ocurrencias para analizar")
            return {
                "relations": [],
                "clusters": [],
                "knowledge_asymmetries": [],
                "dendrogram_data": None,
            }

        # 1. Análisis de co-ocurrencia
        cooc_matrix, entity_ids = self._build_cooccurrence_matrix()
        cooc_scores = self._analyze_cooccurrence(cooc_matrix, entity_ids)

        # 2. Clustering jerárquico (dendrograma)
        hierarchical_clusters, dendrogram_data = self._hierarchical_clustering(
            cooc_matrix, entity_ids
        )

        # 3. Community detection (Louvain)
        communities = self._detect_communities(cooc_matrix, entity_ids)

        # 4. Similitud por embeddings (si disponible)
        embedding_scores = {}
        if self.use_embeddings and self.embedding_model:
            embedding_scores = self._compute_embedding_similarity(entity_ids)

        # 5. Votación y combinación
        self._relations = self._combine_with_voting(
            entity_ids,
            cooc_scores,
            hierarchical_clusters,
            communities,
            embedding_scores,
        )

        # 6. Crear clusters finales
        self._clusters = self._create_final_clusters(
            hierarchical_clusters,
            communities,
            entity_ids,
        )

        # 7. Analizar asimetrías de conocimiento
        self._knowledge_asymmetries = self._analyze_knowledge_asymmetry(entity_ids)

        return {
            "relations": [self._relation_to_dict(r) for r in self._relations],
            "clusters": [self._cluster_to_dict(c) for c in self._clusters],
            "knowledge_asymmetries": [
                self._asymmetry_to_dict(a) for a in self._knowledge_asymmetries
            ],
            "dendrogram_data": dendrogram_data,
        }

    def _build_cooccurrence_matrix(self) -> tuple[np.ndarray, list[int]]:
        """Construye matriz de co-ocurrencia."""
        # Obtener lista única de entidades
        entity_set = set()
        for cooc in self._cooccurrences:
            entity_set.add(cooc.entity1_id)
            entity_set.add(cooc.entity2_id)

        entity_ids = sorted(entity_set)
        n = len(entity_ids)
        id_to_idx = {eid: i for i, eid in enumerate(entity_ids)}

        # Construir matriz
        matrix = np.zeros((n, n), dtype=float)

        for cooc in self._cooccurrences:
            i = id_to_idx[cooc.entity1_id]
            j = id_to_idx[cooc.entity2_id]

            # Ponderar por distancia (más cerca = más peso)
            weight = 1.0
            if cooc.distance_chars > 0:
                weight = max(0.1, 1.0 - (cooc.distance_chars / self.DISTANCE_THRESHOLD))

            matrix[i, j] += weight
            matrix[j, i] += weight

        return matrix, entity_ids

    def _analyze_cooccurrence(
        self,
        matrix: np.ndarray,
        entity_ids: list[int],
    ) -> dict[tuple[int, int], float]:
        """
        Analiza co-ocurrencias y retorna scores normalizados.

        Returns:
            Dict de (entity1_id, entity2_id) -> score normalizado
        """
        scores = {}
        max_cooc = matrix.max() if matrix.max() > 0 else 1.0

        n = len(entity_ids)
        for i in range(n):
            for j in range(i + 1, n):
                if matrix[i, j] >= self.COOCCURRENCE_THRESHOLD:
                    pair = (entity_ids[i], entity_ids[j])
                    scores[pair] = matrix[i, j] / max_cooc

        return scores

    def _hierarchical_clustering(
        self,
        matrix: np.ndarray,
        entity_ids: list[int],
    ) -> tuple[dict[int, int], dict]:
        """
        Realiza clustering jerárquico y genera datos de dendrograma.

        Returns:
            - Dict de entity_id -> cluster_id
            - Datos para visualizar dendrograma
        """
        try:
            from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
            from scipy.spatial.distance import squareform
        except ImportError:
            logger.warning("scipy no disponible, omitiendo clustering jerárquico")
            return {}, {}

        n = len(entity_ids)
        if n < 2:
            return {}, {}

        # Convertir matriz de similitud a distancia
        # Normalizar primero
        max_val = matrix.max() if matrix.max() > 0 else 1.0
        similarity = matrix / max_val

        # Distancia = 1 - similitud
        distance = 1.0 - similarity
        np.fill_diagonal(distance, 0)

        # Asegurar que la matriz sea simétrica
        distance = (distance + distance.T) / 2

        try:
            # Convertir a formato condensado
            condensed = squareform(distance)

            # Linkage (ward, complete, average, single)
            Z = linkage(condensed, method="ward")

            # Cortar en clusters (criterio: distancia máxima)
            # Usar criterio adaptativo basado en la estructura
            max_d = 0.7 * Z[:, 2].max()  # 70% de la distancia máxima
            clusters_arr = fcluster(Z, max_d, criterion="distance")

            # Mapear a dict
            cluster_map = {entity_ids[i]: int(clusters_arr[i]) for i in range(n)}

            # Datos para dendrograma
            dendrogram_data = {
                "linkage_matrix": Z.tolist(),
                "labels": [self._entity_names.get(eid, str(eid)) for eid in entity_ids],
                "entity_ids": entity_ids,
            }

            return cluster_map, dendrogram_data

        except Exception as e:
            logger.warning(f"Error en clustering jerárquico: {e}")
            return {}, {}

    def _detect_communities(
        self,
        matrix: np.ndarray,
        entity_ids: list[int],
    ) -> dict[int, int]:
        """
        Detecta comunidades usando algoritmo de Louvain.

        Returns:
            Dict de entity_id -> community_id
        """
        try:
            import networkx as nx
            from networkx.algorithms.community import louvain_communities
        except ImportError:
            logger.warning("networkx no disponible, omitiendo community detection")
            return {}

        n = len(entity_ids)
        if n < 2:
            return {}

        # Crear grafo
        G = nx.Graph()

        for i, eid in enumerate(entity_ids):
            G.add_node(eid, name=self._entity_names.get(eid, str(eid)))

        # Añadir aristas con peso
        for i in range(n):
            for j in range(i + 1, n):
                if matrix[i, j] > 0:
                    G.add_edge(entity_ids[i], entity_ids[j], weight=matrix[i, j])

        try:
            # Detectar comunidades
            communities = louvain_communities(G, weight="weight", seed=42)

            # Mapear a dict
            community_map = {}
            for comm_id, community in enumerate(communities):
                for entity_id in community:
                    community_map[entity_id] = comm_id

            return community_map

        except Exception as e:
            logger.warning(f"Error en community detection: {e}")
            return {}

    def _compute_embedding_similarity(
        self,
        entity_ids: list[int],
    ) -> dict[tuple[int, int], float]:
        """
        Calcula similitud entre entidades usando embeddings de sus contextos.

        Returns:
            Dict de (entity1_id, entity2_id) -> similarity score
        """
        if not self.embedding_model:
            return {}

        # Generar embedding promedio por entidad
        entity_embeddings = {}

        for eid in entity_ids:
            contexts = self._entity_contexts.get(eid, [])
            if not contexts:
                continue

            try:
                # Concatenar contextos y generar embedding
                text = " ".join(contexts[:10])  # Máximo 10 contextos
                embedding = self.embedding_model.encode(text)
                entity_embeddings[eid] = embedding
            except Exception as e:
                logger.warning(f"Error generando embedding para entidad {eid}: {e}")

        # Calcular similitudes por pares
        scores = {}
        from numpy.linalg import norm

        eids_with_emb = list(entity_embeddings.keys())
        for i, eid1 in enumerate(eids_with_emb):
            for eid2 in eids_with_emb[i + 1 :]:
                emb1 = entity_embeddings[eid1]
                emb2 = entity_embeddings[eid2]

                # Cosine similarity
                sim = np.dot(emb1, emb2) / (norm(emb1) * norm(emb2) + 1e-8)

                # Normalizar a 0-1
                sim = (sim + 1) / 2

                pair = (min(eid1, eid2), max(eid1, eid2))
                scores[pair] = float(sim)

        return scores

    def _combine_with_voting(
        self,
        entity_ids: list[int],
        cooc_scores: dict[tuple[int, int], float],
        hierarchical_clusters: dict[int, int],
        communities: dict[int, int],
        embedding_scores: dict[tuple[int, int], float],
    ) -> list[InferredRelation]:
        """
        Combina resultados de todas las técnicas usando votación ponderada.

        Returns:
            Lista de relaciones inferidas con confianza combinada
        """
        relations = []

        # Obtener todos los pares posibles
        all_pairs = set(cooc_scores.keys())
        all_pairs.update(embedding_scores.keys())

        for eid1, eid2 in all_pairs:
            votes = {}

            # Voto de co-ocurrencia
            cooc_score = cooc_scores.get((eid1, eid2), 0.0)
            votes["cooccurrence"] = cooc_score > 0.3

            # Voto de clustering jerárquico (mismo cluster = relación)
            h_vote = False
            if hierarchical_clusters:
                c1 = hierarchical_clusters.get(eid1)
                c2 = hierarchical_clusters.get(eid2)
                h_vote = c1 is not None and c1 == c2
            votes["hierarchical"] = h_vote

            # Voto de community detection (misma comunidad = relación)
            c_vote = False
            if communities:
                comm1 = communities.get(eid1)
                comm2 = communities.get(eid2)
                c_vote = comm1 is not None and comm1 == comm2
            votes["community"] = c_vote

            # Voto de embeddings
            emb_score = embedding_scores.get((eid1, eid2), 0.0)
            votes["embedding"] = emb_score > 0.6

            # Calcular confianza ponderada
            confidence = sum(
                self.WEIGHTS[method] * (1.0 if vote else 0.0) for method, vote in votes.items()
            )

            # Solo reportar si supera umbral
            if confidence < self.RELATION_CONFIDENCE_THRESHOLD:
                continue

            # Determinar fuerza de la relación
            strength = self._determine_strength(cooc_score, confidence)

            # Determinar valencia (por ahora neutral, se puede mejorar con sentiment)
            valence = RelationValence.UNKNOWN

            # Recopilar evidencias
            evidence = [
                c.context
                for c in self._cooccurrences
                if (c.entity1_id == eid1 and c.entity2_id == eid2)
                or (c.entity1_id == eid2 and c.entity2_id == eid1)
            ][:5]  # Máximo 5 evidencias

            chapters = list(
                {
                    c.chapter
                    for c in self._cooccurrences
                    if (c.entity1_id == eid1 and c.entity2_id == eid2)
                    or (c.entity1_id == eid2 and c.entity2_id == eid1)
                }
            )

            relations.append(
                InferredRelation(
                    entity1_id=eid1,
                    entity2_id=eid2,
                    entity1_name=self._entity_names.get(eid1, str(eid1)),
                    entity2_name=self._entity_names.get(eid2, str(eid2)),
                    strength=strength,
                    valence=valence,
                    confidence=confidence,
                    cooccurrence_score=cooc_score,
                    hierarchical_cluster=hierarchical_clusters.get(eid1),
                    community_id=communities.get(eid1),
                    embedding_similarity=emb_score,
                    votes=votes,
                    evidence_contexts=evidence,
                    chapters_together=sorted(chapters),
                )
            )

        # Ordenar por confianza
        relations.sort(key=lambda r: r.confidence, reverse=True)

        return relations

    def _determine_strength(
        self,
        cooc_score: float,
        confidence: float,
    ) -> RelationStrength:
        """Determina la fuerza de la relación basándose en scores."""
        combined = (cooc_score + confidence) / 2

        if combined >= 0.8:
            return RelationStrength.VERY_STRONG
        elif combined >= 0.6:
            return RelationStrength.STRONG
        elif combined >= 0.4:
            return RelationStrength.MODERATE
        elif combined >= 0.2:
            return RelationStrength.WEAK
        else:
            return RelationStrength.NONE

    def _create_final_clusters(
        self,
        hierarchical_clusters: dict[int, int],
        communities: dict[int, int],
        entity_ids: list[int],
    ) -> list[CharacterCluster]:
        """
        Crea clusters finales combinando resultados de diferentes técnicas.

        Usa votación: si hierarchical y community coinciden, mayor confianza.
        """
        clusters = []  # type: ignore[var-annotated]

        # Preferir communities si disponible, sino hierarchical
        cluster_source = communities if communities else hierarchical_clusters

        if not cluster_source:
            return clusters

        # Agrupar por cluster
        cluster_members: dict[int, list[int]] = defaultdict(list)
        for eid, cid in cluster_source.items():
            cluster_members[cid].append(eid)

        for cid, members in cluster_members.items():
            if len(members) < 2:
                continue  # Ignorar clusters de un solo elemento

            names = [self._entity_names.get(eid, str(eid)) for eid in members]

            # Encontrar centroide (entidad más conectada)
            centroid = self._find_centroid(members)
            centroid_name = self._entity_names.get(centroid) if centroid else None

            # Calcular cohesión
            cohesion = self._calculate_cohesion(members)

            # Encontrar capítulos donde el grupo está activo
            chapters = set()
            for cooc in self._cooccurrences:
                if cooc.entity1_id in members or cooc.entity2_id in members:
                    chapters.add(cooc.chapter)

            # Generar nombre descriptivo usando el centroide
            cluster_name = self._generate_cluster_name(names, centroid_name)

            clusters.append(
                CharacterCluster(
                    id=cid,
                    name=cluster_name,
                    entity_ids=members,
                    entity_names=names,
                    centroid_entity_id=centroid,
                    centroid_entity_name=centroid_name,
                    cohesion_score=cohesion,
                    detection_method="louvain" if communities else "hierarchical",
                    chapters_active=sorted(chapters),
                )
            )

        return clusters

    def _find_centroid(self, members: list[int]) -> int | None:
        """Encuentra la entidad más conectada del grupo."""
        if not members:
            return None

        connection_counts = defaultdict(int)  # type: ignore[var-annotated]
        for cooc in self._cooccurrences:
            if cooc.entity1_id in members and cooc.entity2_id in members:
                connection_counts[cooc.entity1_id] += 1
                connection_counts[cooc.entity2_id] += 1

        if not connection_counts:
            return members[0]

        return max(connection_counts.keys(), key=lambda k: connection_counts[k])

    def _calculate_cohesion(self, members: list[int]) -> float:
        """Calcula qué tan cohesivo es el grupo (0-1)."""
        if len(members) < 2:
            return 1.0

        # Contar conexiones existentes vs posibles
        member_set = set(members)
        existing = 0

        for cooc in self._cooccurrences:
            if cooc.entity1_id in member_set and cooc.entity2_id in member_set:
                existing += 1

        # Conexiones posibles: n*(n-1)/2
        n = len(members)
        possible = n * (n - 1) / 2

        return min(1.0, existing / possible) if possible > 0 else 0.0

    def _generate_cluster_name(self, names: list[str], centroid_name: str | None = None) -> str:
        """
        Genera un nombre descriptivo para el cluster.

        Usa el personaje centroide (más conectado) como referencia principal:
        - "Círculo de María" para clusters con un personaje central claro
        - "María y Juan" para parejas
        - "María, Juan y Pedro" para tríos
        - "Grupo de María" para clusters grandes

        Args:
            names: Lista de nombres de entidades en el cluster
            centroid_name: Nombre del personaje central (si se conoce)

        Returns:
            Nombre descriptivo del cluster
        """
        if not names:
            return "Cluster vacío"

        if len(names) == 1:
            return names[0]

        if len(names) == 2:
            return f"{names[0]} y {names[1]}"

        if len(names) == 3:
            return f"{names[0]}, {names[1]} y {names[2]}"

        # Para clusters más grandes, usar el centroide como referencia
        if centroid_name:
            return f"Círculo de {centroid_name}"

        # Fallback si no hay centroide
        return f"{names[0]}, {names[1]} y {len(names) - 2} más"

    def _analyze_knowledge_asymmetry(
        self,
        entity_ids: list[int],
    ) -> list[KnowledgeAsymmetry]:
        """
        Analiza asimetrías de conocimiento entre personajes.

        Detecta cuándo A sabe más de B que B de A.
        Esto se infiere de:
        - Menciones de A sobre B en diálogos
        - A describe a B pero no viceversa
        - A reacciona a información sobre B
        """
        # Por ahora, placeholder - esto requeriría análisis de diálogos
        # y atribución de speaker más sofisticada
        return []

    def _relation_to_dict(self, rel: InferredRelation) -> dict:
        """Convierte relación a diccionario serializable."""
        return {
            "entity1_id": rel.entity1_id,
            "entity2_id": rel.entity2_id,
            "entity1_name": rel.entity1_name,
            "entity2_name": rel.entity2_name,
            "strength": rel.strength.name,
            "valence": rel.valence.name,
            "confidence": round(rel.confidence, 3),
            "cooccurrence_score": round(rel.cooccurrence_score, 3),
            "hierarchical_cluster": rel.hierarchical_cluster,
            "community_id": rel.community_id,
            "embedding_similarity": round(rel.embedding_similarity, 3),
            "votes": rel.votes,
            "evidence_contexts": rel.evidence_contexts,
            "chapters_together": rel.chapters_together,
        }

    def _cluster_to_dict(self, cluster: CharacterCluster) -> dict:
        """Convierte cluster a diccionario serializable."""
        return {
            "id": cluster.id,
            "name": cluster.name,
            "display_name": cluster.display_name,
            "custom_name": cluster.custom_name,
            "entity_ids": cluster.entity_ids,
            "entity_names": cluster.entity_names,
            "centroid_entity_id": cluster.centroid_entity_id,
            "centroid_entity_name": cluster.centroid_entity_name,
            "cohesion_score": round(cluster.cohesion_score, 3),
            "detection_method": cluster.detection_method,
            "chapters_active": cluster.chapters_active,
            "member_count": len(cluster.entity_ids),
        }

    def _asymmetry_to_dict(self, asym: KnowledgeAsymmetry) -> dict:
        """Convierte asimetría a diccionario serializable."""
        return {
            "entity_a_id": asym.entity_a_id,
            "entity_b_id": asym.entity_b_id,
            "entity_a_name": asym.entity_a_name,
            "entity_b_name": asym.entity_b_name,
            "a_knows_about_b": asym.a_knows_about_b,
            "b_knows_about_a": asym.b_knows_about_a,
            "asymmetry_score": round(asym.asymmetry_score, 3),
        }


def extract_cooccurrences_from_chapters(
    chapters: list[dict],
    entity_mentions: list[dict],
    window_chars: int = 500,
) -> list[CoOccurrence]:
    """
    Extrae co-ocurrencias de menciones de entidades en capítulos.

    Args:
        chapters: Lista de capítulos con content, chapter_number
        entity_mentions: Lista de menciones con entity_id, start_char, end_char, entity_name
        window_chars: Ventana en caracteres para considerar co-ocurrencia

    Returns:
        Lista de CoOccurrence
    """
    cooccurrences = []

    # Organizar menciones por capítulo
    mentions_by_chapter = defaultdict(list)
    for mention in entity_mentions:
        # Determinar capítulo basado en posición
        for chapter in chapters:
            if (
                chapter.get("start_char", 0)
                <= mention["start_char"]
                <= chapter.get("end_char", float("inf"))
            ):
                mentions_by_chapter[chapter["chapter_number"]].append(mention)
                break

    # Buscar co-ocurrencias dentro de cada capítulo
    for chapter_num, mentions in mentions_by_chapter.items():
        # Ordenar por posición
        mentions.sort(key=lambda m: m["start_char"])

        for i, m1 in enumerate(mentions):
            for m2 in mentions[i + 1 :]:
                # Calcular distancia
                distance = m2["start_char"] - m1["end_char"]

                if distance > window_chars:
                    break  # Ya están muy lejos, no seguir

                if m1["entity_id"] == m2["entity_id"]:
                    continue  # Misma entidad

                # Extraer contexto
                chapter_content = next(
                    (c.get("content", "") for c in chapters if c["chapter_number"] == chapter_num),
                    "",
                )
                context_start = max(0, m1["start_char"] - 50)
                context_end = min(len(chapter_content), m2["end_char"] + 50)
                context = chapter_content[context_start:context_end] if chapter_content else ""

                cooccurrences.append(
                    CoOccurrence(
                        entity1_id=min(m1["entity_id"], m2["entity_id"]),
                        entity2_id=max(m1["entity_id"], m2["entity_id"]),
                        chapter=chapter_num,
                        distance_chars=distance,
                        context=context,
                    )
                )

    return cooccurrences
