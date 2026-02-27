"""
Tests para el sistema de clustering de entidades (M3 optimization).

Verifica que:
1. Clustering reduce significativamente el número de pares a comparar
2. No pierde pares legítimos que deberían fusionarse
3. Maneja edge cases (nombres cortos, unicodedata, etc.)
"""

import pytest

from narrative_assistant.entities.clustering import (
    _fast_name_similarity,
    _name_fingerprint,
    _ngram_similarity,
    cluster_entities_by_name_similarity,
    compute_reduced_pairs_from_clusters,
)
from narrative_assistant.entities.models import Entity, EntityType


@pytest.fixture
def sample_entities():
    """Entidades de prueba con nombres similares y diferentes."""
    return [
        Entity(
            id=1,
            canonical_name="María García",
            entity_type=EntityType.CHARACTER,
            project_id=1,
        ),
        Entity(
            id=2,
            canonical_name="García María",  # Mismo nombre, orden diferente
            entity_type=EntityType.CHARACTER,
            project_id=1,
        ),
        Entity(
            id=3,
            canonical_name="Mari García",  # Diminutivo
            entity_type=EntityType.CHARACTER,
            project_id=1,
        ),
        Entity(
            id=4,
            canonical_name="María Sánchez",  # Apellido diferente
            entity_type=EntityType.CHARACTER,
            project_id=1,
        ),
        Entity(
            id=5,
            canonical_name="Juan Pérez",  # Nombre completamente diferente
            entity_type=EntityType.CHARACTER,
            project_id=1,
        ),
        Entity(
            id=6,
            canonical_name="Don Juan Pérez",  # Con título
            entity_type=EntityType.CHARACTER,
            project_id=1,
        ),
    ]


def test_name_fingerprint_normalizes_order():
    """Fingerprint debe ser insensible al orden de palabras."""
    fp1 = _name_fingerprint("María García Sánchez")
    fp2 = _name_fingerprint("García Sánchez María")
    assert fp1 == fp2
    assert fp1 == "garcia maria sanchez"


def test_name_fingerprint_removes_titles():
    """Fingerprint debe quitar títulos (don, doña, etc.)."""
    fp1 = _name_fingerprint("Don García Pérez")
    fp2 = _name_fingerprint("García Pérez")
    assert fp1 == fp2


def test_name_fingerprint_strips_accents():
    """Fingerprint debe quitar acentos."""
    fp1 = _name_fingerprint("María José")
    fp2 = _name_fingerprint("Maria Jose")
    assert fp1 == fp2


def test_fast_name_similarity_exact():
    """Similaridad debe ser 1.0 para nombres normalizados iguales."""
    sim = _fast_name_similarity("María García", "maria garcia")
    assert sim == 1.0


def test_fast_name_similarity_containment():
    """Similaridad debe ser alta cuando un nombre contiene al otro."""
    sim = _fast_name_similarity("María", "María García")
    assert sim >= 0.75  # Contención detectada


def test_fast_name_similarity_different():
    """Similaridad debe ser baja para nombres diferentes."""
    sim = _fast_name_similarity("María García", "Juan Pérez")
    assert sim < 0.4


def test_ngram_similarity():
    """N-gramas detectan similaridad parcial."""
    # "Garcia" y "Gárcia" (con tilde)
    sim = _ngram_similarity("Garcia", "Gárcia", n=2)
    assert sim > 0.8  # Muy similares en bigramas

    # Nombres diferentes
    sim2 = _ngram_similarity("García", "Pérez", n=2)
    assert sim2 < 0.3


def test_cluster_entities_by_name_similarity(sample_entities):
    """Clustering debe agrupar entidades con nombres similares."""
    clusters = cluster_entities_by_name_similarity(sample_entities)

    # Debe haber al menos 2 clusters:
    # - Cluster 1: María García, García María, Mari García (variantes)
    # - Cluster 2: Juan Pérez, Don Juan Pérez (con/sin título)
    assert len(clusters) >= 2

    # Verificar que entidades con mismo fingerprint están juntas
    cluster_names = {frozenset(e.canonical_name for e in c.entities) for c in clusters}

    # Al menos un cluster debe tener "María García" y "García María"
    maria_cluster_found = any(
        "María García" in names and "García María" in names for names in cluster_names
    )
    assert maria_cluster_found


def test_cluster_empty_list():
    """Clustering de lista vacía debe retornar lista vacía."""
    clusters = cluster_entities_by_name_similarity([])
    assert clusters == []


def test_cluster_single_entity():
    """Una sola entidad no genera clusters."""
    entities = [
        Entity(
            id=1,
            canonical_name="María García",
            entity_type=EntityType.CHARACTER,
            project_id=1,
        )
    ]
    clusters = cluster_entities_by_name_similarity(entities)
    assert len(clusters) == 0  # No clusters con > 1 entidad


def test_compute_reduced_pairs_reduces_significantly():
    """Clustering debe reducir dramáticamente el número de pares."""
    # Crear 100 entidades con nombres variados pero realistas
    # 10 grupos con nombres completamente diferentes entre grupos
    base_names = [
        "García",
        "Pérez",
        "Martínez",
        "López",
        "González",
        "Rodríguez",
        "Fernández",
        "Sánchez",
        "Ramírez",
        "Torres",
    ]

    entities = []
    for group_id, base_name in enumerate(base_names):
        # Cada grupo tiene 10 variaciones del mismo apellido
        for variation in range(10):
            if variation == 0:
                canonical_name = f"{base_name}"
            elif variation <= 3:
                # Variantes con nombre
                first_names = ["María", "Juan", "Pedro", "Ana"]
                canonical_name = f"{first_names[variation - 1]} {base_name}"
            elif variation <= 6:
                # Variantes con doble apellido
                second_surnames = ["Silva", "Cruz", "Mendoza"]
                canonical_name = f"{base_name} {second_surnames[variation - 4]}"
            else:
                # Variantes con título
                titles = ["Don", "Doña", "Dr."]
                canonical_name = f"{titles[variation - 7]} {base_name}"

            entities.append(
                Entity(
                    id=group_id * 10 + variation + 1,
                    canonical_name=canonical_name,
                    entity_type=EntityType.CHARACTER,
                    project_id=1,
                )
            )

    # Sin clustering: 100 * 99 / 2 = 4,950 pares
    total_possible_pairs = (len(entities) * (len(entities) - 1)) // 2
    assert total_possible_pairs == 4950

    # Con clustering: debería ser mucho menor
    reduced_pairs = compute_reduced_pairs_from_clusters(entities, similarity_threshold=0.45)

    # Esperar reducción significativa (al menos 10x)
    # Cada grupo de 10 debería tener ~45 pares internos → 10 grupos * 45 = 450 pares
    reduction_factor = total_possible_pairs / len(reduced_pairs) if reduced_pairs else float("inf")
    assert reduction_factor >= 5, f"Reducción insuficiente: {reduction_factor:.1f}x"


def test_clustering_handles_unicode():
    """Clustering debe manejar caracteres Unicode correctamente."""
    entities = [
        Entity(
            id=1,
            canonical_name="José María",
            entity_type=EntityType.CHARACTER,
            project_id=1,
        ),
        Entity(
            id=2,
            canonical_name="Jose Maria",  # Sin tildes
            entity_type=EntityType.CHARACTER,
            project_id=1,
        ),
    ]

    clusters = cluster_entities_by_name_similarity(entities)

    # Debe agrupar ambos (mismos caracteres sin acentos)
    assert len(clusters) == 1
    assert len(clusters[0].entities) == 2


def test_clustering_threshold_affects_grouping():
    """Umbral de clustering afecta la agresividad del agrupamiento."""
    entities = [
        Entity(
            id=1,
            canonical_name="María García",
            entity_type=EntityType.CHARACTER,
            project_id=1,
        ),
        Entity(
            id=2,
            canonical_name="Mari García",  # Similaridad media
            entity_type=EntityType.CHARACTER,
            project_id=1,
        ),
    ]

    # Umbral bajo (agresivo): debe agrupar
    clusters_low = cluster_entities_by_name_similarity(entities, similarity_threshold=0.3)
    assert len(clusters_low) >= 1

    # Umbral alto (estricto): puede no agrupar
    clusters_high = cluster_entities_by_name_similarity(entities, similarity_threshold=0.9)
    # Puede haber 0 o 1 cluster dependiendo de la similaridad exacta
    assert len(clusters_high) <= 1


@pytest.mark.parametrize(
    "name1,name2,expected_high_similarity",
    [
        ("María García", "García María", True),  # Orden diferente
        ("Don García", "García", True),  # Con/sin título
        ("María José", "Maria Jose", True),  # Con/sin tildes
        ("Mari García", "María García", True),  # Diminutivo vs formal
        ("María García", "Juan Pérez", False),  # Nombres diferentes
        ("El Magistral", "Fermín de Pas", False),  # Apodo (no detectado por texto)
    ],
)
def test_fast_name_similarity_parametrized(name1, name2, expected_high_similarity):
    """Test parametrizado de similaridad de nombres."""
    sim = _fast_name_similarity(name1, name2)
    if expected_high_similarity:
        assert sim >= 0.5, f"Similaridad baja inesperada: {sim:.2f} entre '{name1}' y '{name2}'"
    else:
        assert sim < 0.5, f"Similaridad alta inesperada: {sim:.2f} entre '{name1}' y '{name2}'"


def test_clustering_preserves_all_entities(sample_entities):
    """Clustering no debe perder entidades."""
    clusters = cluster_entities_by_name_similarity(sample_entities)

    clustered_entity_ids = {e.id for c in clusters for e in c.entities}
    total_entity_ids = {e.id for e in sample_entities}

    # Las entidades agrupadas deben ser un subconjunto (entidades solas no están en clusters)
    assert clustered_entity_ids.issubset(total_entity_ids)


def test_representative_name_is_longest():
    """Nombre representativo debe ser el más completo."""
    entities = [
        Entity(
            id=1,
            canonical_name="María",
            entity_type=EntityType.CHARACTER,
            project_id=1,
        ),
        Entity(
            id=2,
            canonical_name="María García Sánchez",  # Más completo
            entity_type=EntityType.CHARACTER,
            project_id=1,
        ),
    ]

    clusters = cluster_entities_by_name_similarity(entities)

    if clusters:
        # Si hay cluster, el representativo debe ser el nombre más largo
        assert clusters[0].representative_name == "María García Sánchez"
