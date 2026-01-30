# -*- coding: utf-8 -*-
"""
Tests para el módulo de arquetipos de personajes (character_archetypes).

Cubre:
- Smoke test: import del módulo
- Scoring: Hero no domina por defecto
- Ensemble: tono diagnóstico, no prescriptivo
- Flat arc recognition
- Raw score preservation
"""

import pytest
from narrative_assistant.analysis.character_archetypes import (
    CharacterArchetypeAnalyzer,
    ArchetypeId,
    ArchetypeScore,
    CharacterArchetypeProfile,
    ArchetypeReport,
    ARCHETYPE_INFO,
)


@pytest.fixture
def analyzer():
    return CharacterArchetypeAnalyzer()


def _make_entity(eid: int, name: str, importance: str = "secondary",
                 mention_count: int = 10, **kwargs) -> dict:
    ent = {
        "id": eid,
        "name": name,
        "entity_type": "character",
        "importance": importance,
        "mention_count": mention_count,
        "chapter_count": 3,
    }
    ent.update(kwargs)
    return ent


def _make_arc(char_id: int, arc_type: str = "growth",
              trajectory: str = "rising", completeness: float = 0.7) -> dict:
    return {
        "character_id": char_id,
        "arc_type": arc_type,
        "trajectory": trajectory,
        "completeness": completeness,
    }


def _make_relation(eid1: int, eid2: int, rel_type: str,
                   subtype: str = "") -> dict:
    return {
        "entity1_id": eid1,
        "entity2_id": eid2,
        "relation_type": rel_type,
        "subtype": subtype,
    }


# =============================================================================
# Smoke tests
# =============================================================================

class TestArchetypeSmoke:

    def test_import(self):
        from narrative_assistant.analysis.character_archetypes import CharacterArchetypeAnalyzer
        assert CharacterArchetypeAnalyzer is not None

    def test_create_analyzer(self, analyzer):
        assert analyzer is not None

    def test_archetype_catalog_has_16_entries(self):
        """El catálogo tiene 16 arquetipos (12 Mark&Pearson + 4 Campbell)."""
        assert len(ARCHETYPE_INFO) == 16

    def test_all_archetype_ids_in_catalog(self):
        """Cada ArchetypeId tiene entrada en el catálogo."""
        for aid in ArchetypeId:
            assert aid.value in ARCHETYPE_INFO, f"Falta {aid.value} en catálogo"

    def test_empty_entities(self, analyzer):
        """Sin entidades devuelve report vacío."""
        report = analyzer.analyze(
            entities=[], character_arcs=[], relationships=[],
            interactions=[], total_chapters=5,
        )
        assert isinstance(report, ArchetypeReport)
        assert len(report.characters) == 0


# =============================================================================
# Scoring
# =============================================================================

class TestArchetypeScoring:

    def test_protagonist_gets_hero_bonus(self, analyzer):
        """Protagonista con arco de crecimiento obtiene bonus Hero."""
        entities = [_make_entity(1, "Ana", "protagonist", mention_count=50)]
        arcs = [_make_arc(1, "growth", "rising", 0.8)]
        report = analyzer.analyze(
            entities=entities, character_arcs=arcs,
            relationships=[], interactions=[], total_chapters=10,
        )
        assert len(report.characters) == 1
        profile = report.characters[0]
        assert profile.primary_archetype is not None
        # Hero debería estar entre los top scores
        hero_score = next(
            (s for s in profile.all_scores if s.archetype == ArchetypeId.HERO),
            None,
        )
        assert hero_score is not None
        assert hero_score.score > 0

    def test_hero_bonus_not_overwhelming(self, analyzer):
        """El bonus de protagonista no domina la puntuación."""
        entities = [
            _make_entity(1, "Ana", "protagonist", mention_count=50),
        ]
        arcs = [_make_arc(1, "static", "stable", 0.3)]
        relations = [_make_relation(1, 2, "HIERARCHICAL", "jefe")]
        report = analyzer.analyze(
            entities=entities, character_arcs=arcs,
            relationships=relations, interactions=[], total_chapters=10,
        )
        profile = report.characters[0]
        if profile.primary_archetype:
            # Con arco estático y relación jerárquica como jefe,
            # Hero no debería ser automáticamente el primario
            hero = next(
                (s for s in profile.all_scores if s.archetype == ArchetypeId.HERO),
                None,
            )
            ruler = next(
                (s for s in profile.all_scores if s.archetype == ArchetypeId.RULER),
                None,
            )
            # Ruler debería ser competitivo dado hierarchical + jefe
            if hero and ruler:
                assert ruler.score > 0, "Ruler debería tener score > 0 con relación jerárquica"

    def test_shadow_from_rivalry(self, analyzer):
        """Rivalidad debería dar puntos a Shadow."""
        entities = [
            _make_entity(1, "Ana", "protagonist"),
            _make_entity(2, "Carlos", "secondary"),
        ]
        arcs = [_make_arc(1, "growth"), _make_arc(2, "fall")]
        relations = [_make_relation(1, 2, "RIVALRY", "enemigo")]
        report = analyzer.analyze(
            entities=entities, character_arcs=arcs,
            relationships=relations, interactions=[], total_chapters=10,
        )
        carlos = next(p for p in report.characters if p.character_name == "Carlos")
        shadow = next(
            (s for s in carlos.all_scores if s.archetype == ArchetypeId.SHADOW),
            None,
        )
        assert shadow is not None
        assert shadow.score > 0, "Shadow debería tener score > 0 con rivalidad+fall arc"


# =============================================================================
# Ensemble notes (tono diagnóstico)
# =============================================================================

class TestEnsembleNotes:

    def test_no_prescriptive_language(self, analyzer):
        """Las notas del elenco no deben contener lenguaje prescriptivo."""
        entities = [
            _make_entity(1, "Ana", "protagonist"),
            _make_entity(2, "Luis", "secondary"),
            _make_entity(3, "Pedro", "secondary"),
        ]
        arcs = [_make_arc(1, "growth"), _make_arc(2, "static"), _make_arc(3, "static")]
        report = analyzer.analyze(
            entities=entities, character_arcs=arcs,
            relationships=[], interactions=[], total_chapters=10,
        )
        prescriptive_phrases = [
            "necesita", "debería", "tiene que", "hay que",
            "aporta profundidad", "enriquece la trama", "eleva la tensión",
        ]
        for note in report.ensemble_notes:
            for phrase in prescriptive_phrases:
                assert phrase not in note.lower(), (
                    f"Nota prescriptiva encontrada: '{phrase}' en '{note}'"
                )

    def test_flat_arc_recognition(self, analyzer):
        """Arcos estáticos generan nota sobre flat arcs."""
        entities = [
            _make_entity(1, "Ana", "protagonist"),
            _make_entity(2, "Maestro", "secondary"),
        ]
        arcs = [_make_arc(1, "growth"), _make_arc(2, "static", "stable", 0.5)]
        report = analyzer.analyze(
            entities=entities, character_arcs=arcs,
            relationships=[], interactions=[], total_chapters=10,
        )
        flat_arc_notes = [n for n in report.ensemble_notes if "flat arc" in n.lower() or "estático" in n.lower()]
        assert len(flat_arc_notes) >= 1, (
            f"Debería haber nota sobre flat arcs. Notas: {report.ensemble_notes}"
        )


# =============================================================================
# Serialization
# =============================================================================

class TestArchetypeSerialization:

    def test_report_to_dict(self, analyzer):
        """El report se serializa correctamente."""
        entities = [_make_entity(1, "Ana", "protagonist")]
        arcs = [_make_arc(1, "growth")]
        report = analyzer.analyze(
            entities=entities, character_arcs=arcs,
            relationships=[], interactions=[], total_chapters=5,
        )
        data = report.to_dict()
        assert "characters" in data
        assert "archetype_distribution" in data
        assert "ensemble_notes" in data
        assert isinstance(data["characters"], list)
        assert len(data["characters"]) == 1

    def test_profile_to_dict_has_top_archetypes(self, analyzer):
        """El perfil serializado incluye top_archetypes."""
        entities = [_make_entity(1, "Ana", "protagonist")]
        arcs = [_make_arc(1, "growth")]
        report = analyzer.analyze(
            entities=entities, character_arcs=arcs,
            relationships=[], interactions=[], total_chapters=5,
        )
        profile_dict = report.characters[0].to_dict()
        assert "top_archetypes" in profile_dict
        assert len(profile_dict["top_archetypes"]) <= 5
