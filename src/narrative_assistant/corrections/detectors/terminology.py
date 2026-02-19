"""
Detector de terminología inconsistente.

Detecta cuando el mismo concepto se refiere con diferentes términos
a lo largo del documento, lo cual puede confundir al lector.

Ejemplos:
- "coche" vs "automóvil" vs "vehículo" para el mismo objeto
- "ordenador" vs "computadora" vs "PC"
- Nombres propios con variaciones inconsistentes
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..base import BaseDetector, CorrectionIssue
from ..config import TerminologyConfig
from ..types import CorrectionCategory, TerminologyIssueType

if TYPE_CHECKING:
    from narrative_assistant.nlp.embeddings import EmbeddingsModel

logger = logging.getLogger(__name__)


@dataclass
class TermCluster:
    """Grupo de términos que refieren al mismo concepto."""

    canonical: str  # Término más frecuente/preferido
    variants: list[str] = field(default_factory=list)
    positions: dict[str, list[tuple[int, int]]] = field(default_factory=dict)
    similarity_score: float = 0.0


class TerminologyDetector(BaseDetector):
    """
    Detecta terminología inconsistente usando embeddings semánticos.

    Agrupa términos similares y señala cuando hay variaciones
    que podrían ser inconsistencias terminológicas.
    """

    # Términos que NO deben agruparse (son distintos a propósito)
    DO_NOT_CLUSTER = {
        # Pronombres y artículos
        "él",
        "ella",
        "ellos",
        "ellas",
        "este",
        "esta",
        "ese",
        "esa",
        # Verbos auxiliares
        "ser",
        "estar",
        "haber",
        "tener",
        "ir",
        "hacer",
        # Conectores
        "pero",
        "sin embargo",
        "aunque",
        "porque",
        "por tanto",
    }

    # Grupos de sinónimos conocidos (para mejorar detección)
    KNOWN_SYNONYM_GROUPS = [
        {"coche", "automóvil", "auto", "vehículo", "carro"},
        {"ordenador", "computadora", "computador", "pc", "portátil", "laptop"},
        {"teléfono", "móvil", "celular", "smartphone"},
        {"casa", "hogar", "vivienda", "domicilio", "residencia"},
        {"dinero", "plata", "pasta", "efectivo", "billetes"},
        {"niño", "chico", "chaval", "muchacho", "crío", "pequeño"},
        {"niña", "chica", "chavala", "muchacha", "cría", "pequeña"},
        {"padre", "papá", "progenitor", "viejo"},
        {"madre", "mamá", "progenitora", "vieja"},
        {"hermano", "hermana", "hermanos"},
        {"amigo", "amiga", "amigos", "colega", "compa"},
        {"trabajo", "empleo", "curro", "chamba"},
        {"rápido", "veloz", "rápidamente", "deprisa", "aprisa"},
        {"grande", "enorme", "gigante", "inmenso", "vasto"},
        {"pequeño", "chico", "diminuto", "minúsculo", "tiny"},
        {"bueno", "bien", "excelente", "genial", "estupendo"},
        {"malo", "mal", "terrible", "horrible", "pésimo"},
        {"bonito", "bello", "hermoso", "precioso", "lindo"},
        {"feo", "horrible", "espantoso", "horrendo"},
    ]

    def __init__(self, config: TerminologyConfig | None = None):
        self.config = config or TerminologyConfig()
        self._embeddings_model: "EmbeddingsModel | None" = None
        self._synonym_lookup = self._build_synonym_lookup()

    def _build_synonym_lookup(self) -> dict[str, set[str]]:
        """Construye lookup rápido de sinónimos conocidos."""
        lookup = {}
        for group in self.KNOWN_SYNONYM_GROUPS:
            for term in group:
                lookup[term.lower()] = group
        return lookup

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.STYLE

    @property
    def requires_spacy(self) -> bool:
        return True  # Necesita lematización

    @property
    def requires_embeddings(self) -> bool:
        return True  # Usa embeddings para similitud semántica

    def detect(
        self,
        text: str,
        chapter_index: int | None = None,
        spacy_doc=None,
        embeddings_model=None,
    ) -> list[CorrectionIssue]:
        """
        Detecta terminología inconsistente.

        Args:
            text: Texto a analizar
            chapter_index: Índice del capítulo
            spacy_doc: Documento spaCy preprocesado
            embeddings_model: Modelo de embeddings (opcional)

        Returns:
            Lista de CorrectionIssue encontrados
        """
        if not self.config.enabled:
            return []

        if spacy_doc is None:
            logger.warning("TerminologyDetector requires spaCy doc, skipping")
            return []

        self._embeddings_model = embeddings_model
        issues = []

        # Extraer términos relevantes (sustantivos, principalmente)
        term_positions = self._extract_terms(spacy_doc)

        # Agrupar términos similares
        clusters = self._cluster_terms(term_positions, text)

        # Generar issues para clusters con variaciones
        for cluster in clusters:
            if len(cluster.variants) >= 1:  # Al menos una variante
                issues.extend(self._create_issues_for_cluster(cluster, text, chapter_index))

        return issues

    def _extract_terms(self, doc) -> dict[str, list[tuple[int, int]]]:
        """Extrae términos relevantes con sus posiciones."""
        term_positions = defaultdict(list)

        for token in doc:
            # Solo sustantivos y nombres propios
            if token.pos_ not in ("NOUN", "PROPN"):
                continue

            # Ignorar palabras muy cortas
            if len(token.text) < self.config.min_term_length:
                continue

            # Ignorar términos en la lista de exclusión
            if token.lemma_.lower() in self.DO_NOT_CLUSTER:
                continue

            # Usar lema como clave de agrupación inicial
            key = token.lemma_.lower()
            term_positions[key].append((token.idx, token.idx + len(token.text)))

        return dict(term_positions)

    def _cluster_terms(
        self, term_positions: dict[str, list[tuple[int, int]]], text: str
    ) -> list[TermCluster]:
        """Agrupa términos similares usando sinónimos conocidos y embeddings."""
        clusters = []
        processed = set()

        # Primero: agrupar por sinónimos conocidos
        for term, positions in term_positions.items():
            if term in processed:
                continue

            # Buscar si tiene sinónimos conocidos
            synonyms = self._synonym_lookup.get(term, set())

            if synonyms:
                # Encontrar otros términos del documento que sean sinónimos
                cluster_terms = {term}
                cluster_positions = {term: positions}

                for syn in synonyms:
                    if syn in term_positions and syn != term:
                        cluster_terms.add(syn)
                        cluster_positions[syn] = term_positions[syn]
                        processed.add(syn)

                if len(cluster_terms) > 1:
                    # Determinar término canónico (el más frecuente)
                    canonical = max(cluster_terms, key=lambda t: len(cluster_positions.get(t, [])))
                    variants = [t for t in cluster_terms if t != canonical]

                    clusters.append(
                        TermCluster(
                            canonical=canonical,
                            variants=variants,
                            positions=cluster_positions,
                            similarity_score=1.0,  # Sinónimos conocidos = 100%
                        )
                    )

            processed.add(term)

        # Segundo: si hay modelo de embeddings, buscar similitudes adicionales
        if self._embeddings_model is not None and self.config.use_embeddings:
            # Términos no procesados aún
            remaining = [t for t in term_positions if t not in processed]

            if len(remaining) >= 2:
                embedding_clusters = self._cluster_by_embeddings(remaining, term_positions)
                clusters.extend(embedding_clusters)

        return clusters

    def _cluster_by_embeddings(
        self,
        terms: list[str],
        term_positions: dict[str, list[tuple[int, int]]],
    ) -> list[TermCluster]:
        """Agrupa términos por similitud de embeddings."""
        clusters: list[TermCluster] = []

        if len(terms) < 2:
            return clusters

        try:
            # Obtener embeddings
            embeddings = self._embeddings_model.encode(terms)

            # Calcular similitudes
            from numpy import dot
            from numpy.linalg import norm

            processed = set()
            threshold = self.config.similarity_threshold

            for i, term_i in enumerate(terms):
                if term_i in processed:
                    continue

                similar_terms = [term_i]
                similar_scores = []

                for j, term_j in enumerate(terms):
                    if i == j or term_j in processed:
                        continue

                    # Calcular similitud coseno
                    similarity = dot(embeddings[i], embeddings[j]) / (
                        norm(embeddings[i]) * norm(embeddings[j])
                    )

                    if similarity >= threshold:
                        similar_terms.append(term_j)
                        similar_scores.append(similarity)
                        processed.add(term_j)

                if len(similar_terms) > 1:
                    # Determinar canónico
                    canonical = max(similar_terms, key=lambda t: len(term_positions.get(t, [])))
                    variants = [t for t in similar_terms if t != canonical]

                    clusters.append(
                        TermCluster(
                            canonical=canonical,
                            variants=variants,
                            positions={t: term_positions[t] for t in similar_terms},
                            similarity_score=sum(similar_scores) / len(similar_scores)
                            if similar_scores
                            else 0.9,
                        )
                    )

                processed.add(term_i)

        except Exception as e:
            logger.warning(f"Error in embeddings clustering: {e}")

        return clusters

    def _create_issues_for_cluster(
        self,
        cluster: TermCluster,
        text: str,
        chapter_index: int | None,
    ) -> list[CorrectionIssue]:
        """Crea issues para un cluster de términos variantes."""
        issues: list[CorrectionIssue] = []

        # Solo reportar si hay suficiente variación
        total_occurrences = sum(len(positions) for positions in cluster.positions.values())

        if total_occurrences < self.config.min_occurrences:
            return issues

        # Reportar cada variante (no el canónico)
        for variant in cluster.variants:
            positions = cluster.positions.get(variant, [])

            # Limitar a las primeras N ocurrencias para no saturar
            for i, (start, end) in enumerate(positions[:5]):
                variant_text = text[start:end]

                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=TerminologyIssueType.VARIANT_TERM.value,
                        start_char=start,
                        end_char=end,
                        text=variant_text,
                        explanation=(
                            f"Terminología variable: '{variant_text}' podría "
                            f"unificarse con '{cluster.canonical}' "
                            f"(usado {len(cluster.positions.get(cluster.canonical, []))} veces)"
                        ),
                        suggestion=cluster.canonical,
                        confidence=min(0.9, cluster.similarity_score),
                        context=self._extract_context(text, start, end),
                        chapter_index=chapter_index,
                        rule_id="TERM_VARIANT",
                        extra_data={
                            "canonical": cluster.canonical,
                            "variant": variant,
                            "similarity": cluster.similarity_score,
                            "total_variants": len(cluster.variants),
                        },
                    )
                )

                # Si ya reportamos suficientes para esta variante
                if i >= 2:
                    break

        return issues
