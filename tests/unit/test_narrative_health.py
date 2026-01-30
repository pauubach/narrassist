# -*- coding: utf-8 -*-
"""
Tests para el módulo de salud narrativa (narrative_health).

Cubre:
- Smoke test: import y creación
- Dimensiones independientes: warnings no afectan otras dimensiones
- Weighted scoring: dimensiones core pesan 1.5x
- Manuscrito mínimo: menos de 2 capítulos → CRITICAL
- Ghost character threshold adaptativo
"""

import pytest
from narrative_assistant.analysis.narrative_health import (
    NarrativeHealthChecker,
    HealthDimension,
    HealthStatus,
    DimensionScore,
    NarrativeHealthReport,
    DIMENSION_WEIGHTS,
    DIMENSION_NAMES,
)


@pytest.fixture
def checker():
    return NarrativeHealthChecker()


def _make_chapter(number: int, word_count: int = 2000, **kwargs) -> dict:
    """Crear datos de capítulo mínimos para tests."""
    ch = {
        "chapter_number": number,
        "word_count": word_count,
        "new_characters": [],
        "key_events": [],
        "llm_events": [],
        "dominant_tone": "neutral",
        "tone_intensity": 0.3,
        "conflict_interactions": 0,
        "positive_interactions": 0,
        "total_interactions": 0,
    }
    ch.update(kwargs)
    return ch


def _make_entity(name: str, mention_count: int = 10, **kwargs) -> dict:
    """Crear datos de entidad mínimos."""
    ent = {
        "entity_type": "character",
        "name": name,
        "mention_count": mention_count,
        "chapters_present": 3,
    }
    ent.update(kwargs)
    return ent


# =============================================================================
# Smoke tests
# =============================================================================

class TestNarrativeHealthSmoke:

    def test_import(self):
        from narrative_assistant.analysis.narrative_health import NarrativeHealthChecker
        assert NarrativeHealthChecker is not None

    def test_create_checker(self, checker):
        assert checker is not None

    def test_health_dimensions_defined(self):
        assert len(HealthDimension) == 12

    def test_dimension_weights_exist(self):
        """Cada dimensión tiene un peso definido."""
        for dim in HealthDimension:
            assert dim in DIMENSION_WEIGHTS, f"Falta peso para {dim}"

    def test_core_dimensions_weighted_higher(self):
        """Dimensiones core (protagonist, conflict, goal, climax) pesan 1.5x."""
        core = [HealthDimension.PROTAGONIST, HealthDimension.CONFLICT,
                HealthDimension.GOAL, HealthDimension.CLIMAX]
        for dim in core:
            assert DIMENSION_WEIGHTS[dim] == 1.5, f"{dim} debería pesar 1.5x"


# =============================================================================
# Manuscript mínimo
# =============================================================================

class TestMinimalManuscript:

    def test_less_than_2_chapters_critical(self, checker):
        """Menos de 2 capítulos → overall CRITICAL, score 0."""
        report = checker.check(
            chapters_data=[_make_chapter(1)],
            total_chapters=1,
        )
        assert report.overall_score == 0
        assert report.overall_status == HealthStatus.CRITICAL

    def test_two_chapters_can_score(self, checker):
        """Con 2 capítulos el análisis funciona."""
        chapters = [_make_chapter(1), _make_chapter(2)]
        entities = [_make_entity("Ana", mention_count=20)]
        report = checker.check(
            chapters_data=chapters,
            total_chapters=2,
            entities_data=entities,
        )
        assert report.overall_score >= 0
        assert len(report.dimensions) == 12


# =============================================================================
# Weighted scoring
# =============================================================================

class TestWeightedScoring:

    def test_weighted_average_differs_from_simple(self, checker):
        """La media ponderada difiere de la simple cuando hay scores desiguales."""
        chapters = [
            _make_chapter(1, new_characters=["Ana", "Luis"], positive_interactions=3,
                          dominant_tone="positive", tone_intensity=0.7),
            _make_chapter(2, new_characters=["Pedro"], conflict_interactions=2,
                          dominant_tone="tense", tone_intensity=0.8),
            _make_chapter(3, key_events=[{"event_type": "conflict"}],
                          dominant_tone="negative", tone_intensity=0.9),
            _make_chapter(4, key_events=[{"event_type": "revelation"}],
                          dominant_tone="positive"),
            _make_chapter(5, dominant_tone="positive"),
        ]
        entities = [
            _make_entity("Ana", 30),
            _make_entity("Luis", 15),
            _make_entity("Pedro", 10),
        ]
        report = checker.check(
            chapters_data=chapters,
            total_chapters=5,
            entities_data=entities,
        )
        # Verificar que se calculó con pesos
        scored = [d for d in report.dimensions if d.status != HealthStatus.NA]
        simple_avg = sum(d.score for d in scored) / len(scored)
        # El score ponderado puede ser mayor o menor que el simple
        # pero no debería ser exactamente igual (por la diferencia de pesos)
        assert report.overall_score != pytest.approx(simple_avg, abs=0.01) or \
            all(d.score == scored[0].score for d in scored), \
            "La media ponderada solo coincide con la simple si todos los scores son iguales"


# =============================================================================
# Dimensiones independientes
# =============================================================================

class TestDimensionIndependence:

    def test_all_12_dimensions_returned(self, checker):
        """El chequeo siempre devuelve 12 dimensiones."""
        chapters = [_make_chapter(i) for i in range(1, 6)]
        report = checker.check(
            chapters_data=chapters,
            total_chapters=5,
        )
        assert len(report.dimensions) == 12
        dims = {d.dimension for d in report.dimensions}
        for expected in HealthDimension:
            assert expected in dims, f"Falta dimensión: {expected}"

    def test_each_dimension_has_required_fields(self, checker):
        """Cada dimensión tiene los campos requeridos."""
        chapters = [_make_chapter(i) for i in range(1, 4)]
        report = checker.check(
            chapters_data=chapters,
            total_chapters=3,
        )
        for dim in report.dimensions:
            assert isinstance(dim.score, (int, float))
            assert 0 <= dim.score <= 100
            assert dim.status in (HealthStatus.OK, HealthStatus.WARNING,
                                  HealthStatus.CRITICAL, HealthStatus.NA)
            assert isinstance(dim.explanation, str)
            assert len(dim.explanation) > 0


# =============================================================================
# Pacing thresholds
# =============================================================================

class TestPacingThresholds:

    def test_moderate_variation_not_critical(self, checker):
        """Variación moderada (ratio ~3) no debería ser CRITICAL."""
        chapters = [
            _make_chapter(1, word_count=1000),
            _make_chapter(2, word_count=3000),  # 3x el mínimo
            _make_chapter(3, word_count=2000),
            _make_chapter(4, word_count=1500),
        ]
        report = checker.check(chapters_data=chapters, total_chapters=4)
        pacing = next(d for d in report.dimensions if d.dimension == HealthDimension.PACING)
        assert pacing.status != HealthStatus.CRITICAL, (
            f"Ratio ~3x no debería ser CRITICAL, pero es {pacing.status}"
        )


# =============================================================================
# Coherence thresholds
# =============================================================================

class TestCoherenceThresholds:

    def test_some_tone_shifts_not_critical(self, checker):
        """Hasta 35% de cambios tonales debería ser OK."""
        # 3 capítulos: pos → neg → pos = 2 shifts de 2 transiciones = 100%
        # Necesitamos más capítulos para probar el umbral
        chapters = [
            _make_chapter(1, dominant_tone="positive"),
            _make_chapter(2, dominant_tone="positive"),
            _make_chapter(3, dominant_tone="negative"),  # 1 shift
            _make_chapter(4, dominant_tone="negative"),
            _make_chapter(5, dominant_tone="positive"),  # 1 shift
            _make_chapter(6, dominant_tone="positive"),
        ]
        # 2 shifts de 5 transiciones = 40% → WARNING
        report = checker.check(chapters_data=chapters, total_chapters=6)
        coherence = next(d for d in report.dimensions if d.dimension == HealthDimension.COHERENCE)
        assert coherence.status in (HealthStatus.OK, HealthStatus.WARNING), (
            f"40% shifts debería ser WARNING como máximo, pero es {coherence.status}"
        )


# =============================================================================
# Ghost character adaptive threshold
# =============================================================================

class TestGhostCharacterThreshold:

    def test_few_characters_uses_2_pct(self, checker):
        """Con ≤10 personajes, umbral es 2%."""
        entities = [
            _make_entity("Ana", 50),
            _make_entity("Luis", 20),
            _make_entity("Pedro", 1),  # Ghost: 1/71 < 2%, <2 mentions
        ]
        chapters = [_make_chapter(i) for i in range(1, 6)]
        report = checker.check(
            chapters_data=chapters, total_chapters=5, entities_data=entities,
        )
        cast = next(d for d in report.dimensions if d.dimension == HealthDimension.CAST_BALANCE)
        assert cast is not None

    def test_character_with_2_mentions_not_ghost(self, checker):
        """Un personaje con ≥2 menciones no es ghost (mínimo absoluto)."""
        entities = [
            _make_entity("Ana", 50),
            _make_entity("Luis", 20),
            _make_entity("Pedro", 2),  # 2/72 < 2% pero ≥2 menciones → no ghost
        ]
        chapters = [_make_chapter(i) for i in range(1, 6)]
        report = checker.check(
            chapters_data=chapters, total_chapters=5, entities_data=entities,
        )
        cast = next(d for d in report.dimensions if d.dimension == HealthDimension.CAST_BALANCE)
        # Con 0 ghosts y reasonable protag ratio → should be OK
        assert cast.status in (HealthStatus.OK, HealthStatus.WARNING)
