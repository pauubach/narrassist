"""
Utilidad de matching de entidades (exacto + fuzzy).

Compartida por:
- BK-05: Comparación entre runs de análisis (antes/después)
- BK-07: Sugerencias de links entre libros de una colección
"""

import logging
import unicodedata
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EntityMatchResult:
    """Resultado de un match entre dos entidades."""

    source_name: str
    target_name: str
    source_type: str
    target_type: str
    similarity: float
    match_type: str  # 'exact', 'fuzzy'


def _normalize_name(name: str) -> str:
    """Normaliza un nombre para comparación: lowercase, sin acentos, sin espacios extra."""
    # NFD decomposition + strip accents
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(ascii_name.lower().split())


def _char_ngrams(text: str, n: int = 3) -> set[str]:
    """Genera n-gramas de caracteres para similitud Jaccard."""
    normalized = _normalize_name(text)
    if len(normalized) < n:
        return {normalized}
    return {normalized[i : i + n] for i in range(len(normalized) - n + 1)}


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """Calcula similitud Jaccard entre dos conjuntos."""
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def exact_match(name1: str, name2: str) -> bool:
    """Match exacto (case-insensitive, accent-normalized)."""
    return _normalize_name(name1) == _normalize_name(name2)


def fuzzy_match(
    name1: str,
    name2: str,
    aliases1: list[str] | None = None,
    aliases2: list[str] | None = None,
    threshold: float = 0.7,
) -> float:
    """
    Match fuzzy usando Jaccard sobre n-gramas de caracteres.

    Compara nombre principal y aliases, retorna la mejor similitud.
    """
    all_names_1 = [name1] + (aliases1 or [])
    all_names_2 = [name2] + (aliases2 or [])

    best_similarity = 0.0
    for n1 in all_names_1:
        norm1 = _normalize_name(n1)
        ngrams1 = _char_ngrams(n1)
        for n2 in all_names_2:
            norm2 = _normalize_name(n2)
            ngrams2 = _char_ngrams(n2)

            # Containment: "María" in "María García" → high similarity
            if norm1 and norm2:
                if norm1 in norm2 or norm2 in norm1:
                    shorter = min(len(norm1), len(norm2))
                    longer = max(len(norm1), len(norm2))
                    sim = 0.7 + 0.3 * (shorter / longer)
                else:
                    sim = jaccard_similarity(ngrams1, ngrams2)
            else:
                sim = jaccard_similarity(ngrams1, ngrams2)

            if sim > best_similarity:
                best_similarity = sim

    return best_similarity


def find_matches(
    source_entities: list[dict],
    target_entities: list[dict],
    threshold: float = 0.7,
) -> list[EntityMatchResult]:
    """
    Encuentra matches entre dos listas de entidades.

    Cada entidad es un dict con al menos: canonical_name, entity_type.
    Opcionalmente: aliases (list[str]).

    Retorna lista de matches ordenada por similitud descendente.
    """
    matches = []

    for src in source_entities:
        src_name = src["canonical_name"]
        src_type = src.get("entity_type", "")

        for tgt in target_entities:
            tgt_name = tgt["canonical_name"]
            tgt_type = tgt.get("entity_type", "")

            # Solo comparar entidades del mismo tipo
            if src_type and tgt_type and src_type != tgt_type:
                continue

            # 1. Try exact match
            if exact_match(src_name, tgt_name):
                matches.append(EntityMatchResult(
                    source_name=src_name,
                    target_name=tgt_name,
                    source_type=src_type,
                    target_type=tgt_type,
                    similarity=1.0,
                    match_type="exact",
                ))
                continue

            # 2. Try fuzzy match
            sim = fuzzy_match(
                src_name,
                tgt_name,
                aliases1=src.get("aliases", []),
                aliases2=tgt.get("aliases", []),
                threshold=threshold,
            )
            if sim >= threshold:
                matches.append(EntityMatchResult(
                    source_name=src_name,
                    target_name=tgt_name,
                    source_type=src_type,
                    target_type=tgt_type,
                    similarity=sim,
                    match_type="fuzzy",
                ))

    # Sort by similarity descending
    matches.sort(key=lambda m: m.similarity, reverse=True)
    return matches
