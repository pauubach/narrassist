"""
Análisis de red de personajes.

Extiende el sistema de clustering con métricas de análisis de redes:
- Centralidad (degree, betweenness, closeness)
- Densidad de interacciones
- Métricas temporales (evolución de la red por capítulo)
- Detección de puentes narrativos (personajes que conectan subgrupos)

Se integra con RelationshipClusteringEngine para enriquecer
los datos de relaciones con métricas de red.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class NetworkNode:
    """Nodo de la red de personajes."""

    entity_id: int
    entity_name: str
    degree: int = 0  # Número de conexiones
    weighted_degree: float = 0.0  # Suma de pesos de conexiones
    betweenness: float = 0.0  # Centralidad de intermediación
    closeness: float = 0.0  # Centralidad de cercanía
    is_bridge: bool = False  # Conecta subgrupos
    community_id: int | None = None

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "degree": self.degree,
            "weighted_degree": round(self.weighted_degree, 3),
            "betweenness": round(self.betweenness, 3),
            "closeness": round(self.closeness, 3),
            "is_bridge": self.is_bridge,
            "community_id": self.community_id,
        }


@dataclass
class NetworkEdge:
    """Arista de la red de personajes."""

    source_id: int
    target_id: int
    source_name: str
    target_name: str
    weight: float = 0.0  # Intensidad de la interacción
    chapters: list[int] = field(default_factory=list)
    interaction_count: int = 0

    def to_dict(self) -> dict:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "source_name": self.source_name,
            "target_name": self.target_name,
            "weight": round(self.weight, 3),
            "chapters": self.chapters,
            "interactions": self.interaction_count,
        }


@dataclass
class NetworkMetrics:
    """Métricas globales de la red de personajes."""

    node_count: int = 0
    edge_count: int = 0
    density: float = 0.0  # Aristas existentes / aristas posibles
    avg_degree: float = 0.0
    avg_clustering_coefficient: float = 0.0
    connected_components: int = 0
    diameter: int | None = None  # Distancia máxima entre nodos

    def to_dict(self) -> dict:
        return {
            "nodes": self.node_count,
            "edges": self.edge_count,
            "density": round(self.density, 3),
            "avg_degree": round(self.avg_degree, 3),
            "avg_clustering": round(self.avg_clustering_coefficient, 3),
            "components": self.connected_components,
            "diameter": self.diameter,
        }


@dataclass
class ChapterNetwork:
    """Red de personajes en un capítulo específico."""

    chapter: int
    active_characters: list[int] = field(default_factory=list)
    interactions: int = 0
    density: float = 0.0


@dataclass
class CharacterNetworkReport:
    """Reporte completo de la red de personajes."""

    nodes: list[NetworkNode] = field(default_factory=list)
    edges: list[NetworkEdge] = field(default_factory=list)
    metrics: NetworkMetrics = field(default_factory=NetworkMetrics)
    chapter_evolution: list[ChapterNetwork] = field(default_factory=list)

    # Personajes puente (conectan subgrupos)
    bridge_characters: list[str] = field(default_factory=list)
    # Personajes aislados (sin conexiones fuertes)
    isolated_characters: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "metrics": self.metrics.to_dict(),
            "chapter_evolution": [
                {
                    "chapter": cn.chapter,
                    "active": len(cn.active_characters),
                    "interactions": cn.interactions,
                    "density": round(cn.density, 3),
                }
                for cn in self.chapter_evolution
            ],
            "bridges": self.bridge_characters,
            "isolated": self.isolated_characters,
        }


class CharacterNetworkAnalyzer:
    """
    Analiza la red de personajes usando métricas de grafos.

    Construye un grafo ponderado de interacciones y calcula:
    - Centralidad por personaje
    - Puentes narrativos
    - Evolución temporal de la red
    """

    MIN_WEIGHT_THRESHOLD = 0.1  # Peso mínimo para incluir arista

    def analyze(
        self,
        cooccurrences: list[dict],
        entity_names: dict[int, str],
        total_chapters: int = 1,
    ) -> CharacterNetworkReport:
        """
        Analiza la red de personajes desde co-ocurrencias.

        Args:
            cooccurrences: Lista de co-ocurrencias con entity1_id, entity2_id,
                          chapter, distance_chars
            entity_names: Mapeo de entity_id -> nombre
            total_chapters: Número total de capítulos

        Returns:
            CharacterNetworkReport con métricas completas.
        """
        report = CharacterNetworkReport()

        if not cooccurrences:
            return report

        # Construir datos de aristas
        edge_data = self._aggregate_cooccurrences(cooccurrences, entity_names)

        # Intentar usar networkx para métricas avanzadas
        try:
            report = self._analyze_with_networkx(edge_data, entity_names, total_chapters)
        except ImportError:
            logger.info("networkx no disponible, usando análisis básico")
            report = self._analyze_basic(edge_data, entity_names, total_chapters)

        return report

    def _aggregate_cooccurrences(
        self,
        cooccurrences: list[dict],
        entity_names: dict[int, str],
    ) -> dict[tuple[int, int], dict]:
        """Agrega co-ocurrencias en aristas ponderadas."""
        edges: dict[tuple[int, int], dict] = {}

        for cooc in cooccurrences:
            eid1 = cooc.get("entity1_id", 0)
            eid2 = cooc.get("entity2_id", 0)
            chapter = cooc.get("chapter", 0)
            distance = cooc.get("distance_chars", 500)

            pair = (min(eid1, eid2), max(eid1, eid2))

            if pair not in edges:
                edges[pair] = {
                    "weight": 0.0,
                    "count": 0,
                    "chapters": set(),
                }

            # Ponderar por distancia (más cerca = más peso)
            weight = max(0.1, 1.0 - (distance / 500))
            edges[pair]["weight"] += weight
            edges[pair]["count"] += 1
            edges[pair]["chapters"].add(chapter)

        return edges

    def _analyze_with_networkx(
        self,
        edge_data: dict[tuple[int, int], dict],
        entity_names: dict[int, str],
        total_chapters: int,
    ) -> CharacterNetworkReport:
        """Análisis completo usando networkx."""
        import networkx as nx

        report = CharacterNetworkReport()

        # Construir grafo
        G = nx.Graph()
        for eid, name in entity_names.items():
            G.add_node(eid, name=name)

        for (eid1, eid2), data in edge_data.items():
            if data["weight"] >= self.MIN_WEIGHT_THRESHOLD:
                G.add_edge(eid1, eid2, weight=data["weight"])

        if G.number_of_nodes() == 0:
            return report

        # Métricas de centralidad
        try:
            betweenness = nx.betweenness_centrality(G, weight="weight")
        except Exception:
            betweenness = {n: 0.0 for n in G.nodes()}

        try:
            closeness = nx.closeness_centrality(G)
        except Exception:
            closeness = {n: 0.0 for n in G.nodes()}

        # Detectar puentes
        bridges = set()
        try:
            bridge_edges = list(nx.bridges(G))
            for u, v in bridge_edges:
                bridges.add(u)
                bridges.add(v)
        except Exception as e:
            logger.debug(f"Error calculando puentes en el grafo: {e}")

        # Nodos
        for eid in G.nodes():
            name = entity_names.get(eid, str(eid))
            node = NetworkNode(
                entity_id=eid,
                entity_name=name,
                degree=G.degree(eid),
                weighted_degree=G.degree(eid, weight="weight"),
                betweenness=betweenness.get(eid, 0.0),
                closeness=closeness.get(eid, 0.0),
                is_bridge=eid in bridges,
            )
            report.nodes.append(node)

        # Aristas
        for (eid1, eid2), data in edge_data.items():
            if data["weight"] >= self.MIN_WEIGHT_THRESHOLD:
                edge = NetworkEdge(
                    source_id=eid1,
                    target_id=eid2,
                    source_name=entity_names.get(eid1, str(eid1)),
                    target_name=entity_names.get(eid2, str(eid2)),
                    weight=data["weight"],
                    chapters=sorted(data["chapters"]),
                    interaction_count=data["count"],
                )
                report.edges.append(edge)

        # Métricas globales
        report.metrics.node_count = G.number_of_nodes()
        report.metrics.edge_count = G.number_of_edges()
        report.metrics.density = nx.density(G)
        report.metrics.avg_degree = (
            sum(dict(G.degree()).values()) / G.number_of_nodes()
            if G.number_of_nodes() > 0
            else 0
        )

        try:
            report.metrics.avg_clustering_coefficient = nx.average_clustering(G)
        except Exception as e:
            logger.debug(f"Error calculando coeficiente de clustering promedio: {e}")

        report.metrics.connected_components = nx.number_connected_components(G)

        try:
            if nx.is_connected(G):
                report.metrics.diameter = nx.diameter(G)
        except Exception as e:
            logger.debug(f"Error calculando diámetro del grafo: {e}")

        # Puentes y aislados
        report.bridge_characters = [
            entity_names.get(eid, str(eid))
            for eid in bridges
        ]
        report.isolated_characters = [
            entity_names.get(eid, str(eid))
            for eid in G.nodes()
            if G.degree(eid) == 0
        ]

        # Evolución por capítulo
        report.chapter_evolution = self._analyze_chapter_evolution(
            edge_data, entity_names, total_chapters
        )

        # Ordenar nodos por grado (más conectados primero)
        report.nodes.sort(key=lambda n: n.weighted_degree, reverse=True)

        logger.info(
            f"Red de personajes: {report.metrics.node_count} nodos, "
            f"{report.metrics.edge_count} aristas, "
            f"densidad={report.metrics.density:.3f}"
        )

        return report

    def _analyze_basic(
        self,
        edge_data: dict[tuple[int, int], dict],
        entity_names: dict[int, str],
        total_chapters: int,
    ) -> CharacterNetworkReport:
        """Análisis básico sin networkx."""
        report = CharacterNetworkReport()

        # Calcular grados manualmente
        degrees: dict[int, int] = defaultdict(int)
        weighted_degrees: dict[int, float] = defaultdict(float)

        for (eid1, eid2), data in edge_data.items():
            if data["weight"] >= self.MIN_WEIGHT_THRESHOLD:
                degrees[eid1] += 1
                degrees[eid2] += 1
                weighted_degrees[eid1] += data["weight"]
                weighted_degrees[eid2] += data["weight"]

                edge = NetworkEdge(
                    source_id=eid1,
                    target_id=eid2,
                    source_name=entity_names.get(eid1, str(eid1)),
                    target_name=entity_names.get(eid2, str(eid2)),
                    weight=data["weight"],
                    chapters=sorted(data["chapters"]),
                    interaction_count=data["count"],
                )
                report.edges.append(edge)

        # Nodos
        all_eids = set(entity_names.keys())
        for eid in all_eids:
            node = NetworkNode(
                entity_id=eid,
                entity_name=entity_names.get(eid, str(eid)),
                degree=degrees.get(eid, 0),
                weighted_degree=weighted_degrees.get(eid, 0.0),
            )
            report.nodes.append(node)

        # Métricas
        n = len(all_eids)
        report.metrics.node_count = n
        report.metrics.edge_count = len(report.edges)
        if n > 1:
            max_edges = n * (n - 1) / 2
            report.metrics.density = report.metrics.edge_count / max_edges
        report.metrics.avg_degree = sum(degrees.values()) / n if n > 0 else 0

        report.isolated_characters = [
            entity_names.get(eid, str(eid))
            for eid in all_eids
            if degrees.get(eid, 0) == 0
        ]

        report.chapter_evolution = self._analyze_chapter_evolution(
            edge_data, entity_names, total_chapters
        )

        report.nodes.sort(key=lambda n: n.weighted_degree, reverse=True)

        return report

    def _analyze_chapter_evolution(
        self,
        edge_data: dict[tuple[int, int], dict],
        entity_names: dict[int, str],
        total_chapters: int,
    ) -> list[ChapterNetwork]:
        """Analiza cómo evoluciona la red capítulo a capítulo."""
        evolution = []

        # Recopilar datos por capítulo
        chapter_chars: dict[int, set[int]] = defaultdict(set)
        chapter_interactions: dict[int, int] = defaultdict(int)

        for (eid1, eid2), data in edge_data.items():
            for ch in data["chapters"]:
                chapter_chars[ch].add(eid1)
                chapter_chars[ch].add(eid2)
                chapter_interactions[ch] += 1

        for ch in sorted(chapter_chars.keys()):
            chars = chapter_chars[ch]
            n = len(chars)
            interactions = chapter_interactions[ch]
            max_edges = n * (n - 1) / 2 if n > 1 else 1

            evolution.append(
                ChapterNetwork(
                    chapter=ch,
                    active_characters=sorted(chars),
                    interactions=interactions,
                    density=min(1.0, interactions / max_edges) if max_edges > 0 else 0,
                )
            )

        return evolution
