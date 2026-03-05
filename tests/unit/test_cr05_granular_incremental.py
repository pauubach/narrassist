"""Tests para CR-05: incrementalidad granular por capítulo y entidad."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

_api_server = str(Path(__file__).resolve().parents[2] / "api-server")
if _api_server not in sys.path:
    sys.path.insert(0, _api_server)

from routers._incremental_planner import build_phase_plan  # noqa: E402

from narrative_assistant.persistence.database import Database  # noqa: E402
from narrative_assistant.persistence.version_diff import ChapterDiffMetrics  # noqa: E402

# ============================================================================
# Capa 1: ChapterDiffMetrics con IDs específicos + planner passthrough
# ============================================================================


class TestChapterDiffMetricsIds:
    """Verifica que ChapterDiffMetrics incluye capítulos específicos."""

    def test_modified_chapters_field(self):
        """modified_chapters contiene los números de capítulo modificados."""
        m = ChapterDiffMetrics(
            total_previous=3,
            total_current=3,
            modified=1,
            added=0,
            removed=0,
            changed_ratio=0.33,
            modified_chapters=frozenset({2}),
        )
        assert m.modified_chapters == frozenset({2})
        assert m.added_chapters == frozenset()

    def test_added_removed_chapters(self):
        """added/removed chapters rastreados correctamente."""
        m = ChapterDiffMetrics(
            total_previous=2,
            total_current=3,
            modified=0,
            added=1,
            removed=0,
            changed_ratio=0.33,
            added_chapters=frozenset({3}),
        )
        assert 3 in m.added_chapters

    def test_to_dict_serializes_frozensets(self):
        """to_dict serializa frozensets como listas ordenadas."""
        m = ChapterDiffMetrics(
            total_previous=5,
            total_current=5,
            modified=2,
            added=0,
            removed=0,
            changed_ratio=0.4,
            modified_chapters=frozenset({3, 1}),
            added_chapters=frozenset(),
            removed_chapters=frozenset(),
        )
        d = m.to_dict()
        assert d["modified_chapters"] == [1, 3]
        assert d["added_chapters"] == []
        assert d["removed_chapters"] == []


class TestPlanPassesChangedChapters:
    """Verifica que el plan incluye changed_chapter_numbers."""

    def test_full_plan_includes_changed_chapters(self):
        """Plan full incluye capítulos cambiados."""
        diff = ChapterDiffMetrics(
            total_previous=3,
            total_current=4,
            modified=1,
            added=1,
            removed=0,
            changed_ratio=0.5,
            modified_chapters=frozenset({2}),
            added_chapters=frozenset({4}),
        )
        plan = build_phase_plan(diff)
        assert plan["mode"] == "full"
        assert sorted(plan["changed_chapter_numbers"]) == [2, 4]

    def test_incremental_plan_includes_changed_chapters(self):
        """Plan incremental incluye capítulos cambiados."""
        diff = ChapterDiffMetrics(
            total_previous=30,
            total_current=30,
            modified=1,
            added=0,
            removed=0,
            changed_ratio=0.03,
            modified_chapters=frozenset({5}),
        )
        plan = build_phase_plan(diff)
        assert plan["mode"] == "incremental"
        assert plan["changed_chapter_numbers"] == [5]


# ============================================================================
# Capa 2: Prose per-chapter caching
# ============================================================================


class TestMergeFunctions:
    """Verifica las funciones merge para agregación per-chapter."""

    def test_merge_sticky(self):
        """Merge de sticky sentences agrega correctamente."""
        from routers._enrichment_phases import _merge_sticky

        per_ch = {
            1: {"sticky_sentences": [{"text": "a", "chapter": 1}], "total_sentences": 10, "total_sticky": 1},
            2: {"sticky_sentences": [{"text": "b", "chapter": 2}], "total_sentences": 20, "total_sticky": 1},
        }
        result = _merge_sticky(per_ch)
        assert len(result["sticky_sentences"]) == 2
        assert result["stats"]["total_sentences"] == 30
        assert result["stats"]["total_sticky"] == 2

    def test_merge_energy(self):
        """Merge de sentence energy calcula avg correctamente."""
        from routers._enrichment_phases import _merge_energy

        per_ch = {
            1: {"low_energy_sentences": [{"text": "x"}], "avg_energy": 0.4},
            2: {"low_energy_sentences": [], "avg_energy": 0.8},
        }
        result = _merge_energy(per_ch)
        assert len(result["low_energy_sentences"]) == 1
        assert abs(result["stats"]["avg_energy"] - 0.6) < 0.01

    def test_merge_echo(self):
        """Merge de echo report combina repeticiones."""
        from routers._enrichment_phases import _merge_echo

        per_ch = {
            1: {"repetitions": [{"word": "casa"}]},
            3: {"repetitions": [{"word": "puerta"}, {"word": "ventana"}]},
        }
        result = _merge_echo(per_ch)
        assert result["total"] == 3

    def test_merge_variation_global_stats(self):
        """Merge de sentence variation recalcula estadísticas globales."""
        from routers._enrichment_phases import _merge_variation

        per_ch = {
            1: {
                "chapter_result": {"chapter": 1, "avg_length": 10.0, "std_dev": 2.0,
                                   "variation_coefficient": 0.2, "min_length": 5,
                                   "max_length": 15, "sentence_count": 5},
                "lengths": [5, 8, 10, 12, 15],
            },
            2: {
                "chapter_result": {"chapter": 2, "avg_length": 20.0, "std_dev": 3.0,
                                   "variation_coefficient": 0.15, "min_length": 15,
                                   "max_length": 25, "sentence_count": 5},
                "lengths": [15, 18, 20, 22, 25],
            },
        }
        result = _merge_variation(per_ch)
        assert len(result["chapters"]) == 2
        assert result["global_stats"]["total_sentences"] == 10
        assert result["global_stats"]["min_length"] == 5
        assert result["global_stats"]["max_length"] == 25

    def test_merge_pacing(self):
        """Merge de pacing combina metrics."""
        from routers._enrichment_phases import _merge_pacing

        per_ch = {
            1: {"chapter": 1, "pace_score": 0.7},
            2: {"chapter": 2, "pace_score": 0.5},
        }
        result = _merge_pacing(per_ch)
        assert len(result["chapter_metrics"]) == 2

    def test_merge_dialogue(self):
        """Merge de dialogue combina issues y warnings."""
        from routers._enrichment_phases import _merge_dialogue

        per_ch = {
            1: {"issues": [{"type": "missing_attribution"}], "warnings": []},
            2: {"issues": [], "warnings": [{"type": "ambiguous"}]},
        }
        result = _merge_dialogue(per_ch)
        assert result["total"] == 2


class TestChapterScopedFallback:
    """Verifica fallback de caching per-chapter."""

    def test_fallback_when_no_chapter_info(self):
        """changed_chapter_numbers=None → fallback a cómputo global."""
        from routers._enrichment_phases import _GRANULAR_THRESHOLD

        ch_numbers = [1, 2, 3, 4, 5]
        changed_set = None
        # Lógica de decisión del helper
        use_granular = (
            changed_set is not None
            and len(ch_numbers) > 0
            and len(changed_set) <= len(ch_numbers) * _GRANULAR_THRESHOLD
        )
        assert use_granular is False

    def test_fallback_when_many_changed(self):
        """>50% capítulos cambiados → fallback a global."""
        from routers._enrichment_phases import _GRANULAR_THRESHOLD

        ch_numbers = [1, 2, 3, 4]
        changed_set = {1, 2, 3}  # 75%
        use_granular = (
            changed_set is not None
            and len(ch_numbers) > 0
            and len(changed_set) <= len(ch_numbers) * _GRANULAR_THRESHOLD
        )
        assert use_granular is False

    def test_granular_when_few_changed(self):
        """<50% capítulos cambiados → usa granular."""
        from routers._enrichment_phases import _GRANULAR_THRESHOLD

        ch_numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        changed_set = {5}  # 10%
        use_granular = (
            changed_set is not None
            and len(ch_numbers) > 0
            and len(changed_set) <= len(ch_numbers) * _GRANULAR_THRESHOLD
        )
        assert use_granular is True


# ============================================================================
# Capa 3: Entity-scoped timeline
# ============================================================================


class TestMergeTimeline:
    """Verifica merge de timeline per-entity."""

    def test_merge_timeline_sorts_by_mentions(self):
        """Merge ordena personajes por total_mentions desc."""
        from routers._enrichment_phases import _merge_timeline

        per_ent = {
            1: {"entity_id": 1, "name": "Ana", "total_mentions": 5},
            2: {"entity_id": 2, "name": "Bob", "total_mentions": 20},
            3: {"entity_id": 3, "name": "Clara", "total_mentions": 10},
        }
        chapters = [
            SimpleNamespace(chapter_number=1, title="Cap 1"),
            SimpleNamespace(chapter_number=2, title="Cap 2"),
        ]
        result = _merge_timeline(per_ent, chapters=chapters)
        assert result["characters"][0]["name"] == "Bob"
        assert result["characters"][1]["name"] == "Clara"
        assert result["total_chapters"] == 2

    def test_merge_timeline_skips_empty(self):
        """Merge ignora entidades no-character (resultado vacío)."""
        from routers._enrichment_phases import _merge_timeline

        per_ent = {
            1: {"entity_id": 1, "name": "Ana", "total_mentions": 5},
            2: {},  # entidad no-character
        }
        result = _merge_timeline(per_ent)
        assert len(result["characters"]) == 1


class TestEntityScopedFallback:
    """Verifica fallback de entity-scoped enrichment."""

    def test_fallback_when_no_chapter_info(self):
        """Sin changed_chapter_numbers → affected_ids = None → fallback."""
        from routers._enrichment_phases import _GRANULAR_THRESHOLD

        affected_ids = None
        entity_ids = [1, 2, 3]
        use_granular = (
            affected_ids is not None
            and len(entity_ids) > 0
            and len(affected_ids) <= len(entity_ids) * _GRANULAR_THRESHOLD
        )
        assert use_granular is False

    def test_granular_when_few_entities_affected(self):
        """Pocas entidades afectadas → usa granular."""
        from routers._enrichment_phases import _GRANULAR_THRESHOLD

        affected_ids = {1}
        entity_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        use_granular = (
            affected_ids is not None
            and len(entity_ids) > 0
            and len(affected_ids) <= len(entity_ids) * _GRANULAR_THRESHOLD
        )
        assert use_granular is True

    def test_planner_affected_entities_override_skips_derivation(self):
        """Si planner pasa impacted_entity_ids, no debe recalcular desde capítulos."""
        from routers._enrichment_phases import _run_entity_scoped_enrichment

        entities = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        computed: list[int] = []

        def _compute(entity):
            computed.append(entity.id)
            return {"entity_id": entity.id, "computed": True}

        def _cached(_db, _pid, _etype, entity_id):
            if entity_id == 2:
                return {"entity_id": 2, "computed": False}
            return None

        with patch(
            "routers._enrichment_phases._get_affected_entity_ids",
            side_effect=AssertionError("must not be called when planner override exists"),
        ), patch(
            "routers._enrichment_phases._get_cached_entity_result",
            side_effect=_cached,
        ), patch(
            "routers._enrichment_phases._cache_entity_result",
            return_value=None,
        ), patch(
            "routers._enrichment_phases._cache_result",
            return_value=True,
        ):
            ok = _run_entity_scoped_enrichment(
                db_session=object(),
                project_id=1,
                enrichment_type="character_timeline",
                phase=10,
                entities=entities,
                changed_chapter_numbers=[1],
                affected_entity_ids=[1],
                compute_one_entity=_compute,
                merge_fn=lambda per_ent: {"characters": list(per_ent.values())},
                label="character_timeline",
                ctx={},
            )

        assert ok is True
        assert computed == [1]


class TestAffectedEntityClosure:
    """Verifica expansión por vecinos (relaciones/interacciones)."""

    def test_changed_character_expands_to_related_entities(self, tmp_path):
        from routers._enrichment_phases import _get_affected_entity_ids

        db = Database(db_path=tmp_path / "cr05_entity_closure.db")
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    id, name, document_path, document_format, document_fingerprint, word_count, chapter_count
                ) VALUES (1, 'Proyecto Cierre', '/tmp/closure.docx', 'DOCX', 'fp_closure', 500, 1)
                """
            )
            conn.execute(
                """
                INSERT INTO chapters (id, project_id, chapter_number, title, content, start_char, end_char)
                VALUES (10, 1, 1, 'Cap 1', 'Texto', 0, 5)
                """
            )
            conn.execute(
                """
                INSERT INTO entities (id, project_id, entity_type, canonical_name, mention_count, is_active)
                VALUES (1, 1, 'character', 'Ana', 2, 1)
                """
            )
            conn.execute(
                """
                INSERT INTO entities (id, project_id, entity_type, canonical_name, mention_count, is_active)
                VALUES (2, 1, 'character', 'Beto', 1, 1)
                """
            )
            conn.execute(
                """
                INSERT INTO entity_mentions (entity_id, chapter_id, surface_form, start_char, end_char, source)
                VALUES (1, 10, 'Ana', 0, 3, 'ner')
                """
            )
            conn.execute(
                """
                INSERT INTO relationships (project_id, entity1_id, entity2_id, relation_type)
                VALUES (1, 1, 2, 'allies')
                """
            )

        affected = _get_affected_entity_ids(
            db_session=db,
            project_id=1,
            changed_chapter_numbers=[1],
        )
        assert affected == {1, 2}


class TestScopedCacheValidation:
    """Verifica que caches granulares validan schema/hash antes de reutilizar."""

    @staticmethod
    def _insert_project(db: Database) -> None:
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    id, name, document_path, document_format, document_fingerprint, word_count, chapter_count
                ) VALUES (1, 'Proyecto CR05', '/tmp/cr05.docx', 'DOCX', 'fp_cr05', 1000, 3)
                """
            )

    def test_chapter_cache_ignores_schema_mismatch(self, tmp_path):
        from routers._enrichment_cache import get_schema_version
        from routers._enrichment_phases import _get_cached_chapter_result

        db = Database(db_path=tmp_path / "cr05_scope_schema.db")
        self._insert_project(db)
        schema_v = int(get_schema_version("sticky_sentences"))
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO enrichment_cache (
                    project_id, enrichment_type, entity_scope, status, phase,
                    input_hash, result_json, schema_version, computed_at, updated_at
                ) VALUES (
                    1, 'sticky_sentences', 'chapter:2', 'completed', 12,
                    'hash-ok', '{"ok": true}', ?, datetime('now'), datetime('now')
                )
                """,
                (max(0, schema_v - 1),),
            )

        result = _get_cached_chapter_result(
            db_session=db,
            project_id=1,
            enrichment_type="sticky_sentences",
            chapter_number=2,
            expected_input_hash="hash-ok",
        )
        assert result is None

    def test_chapter_cache_ignores_hash_mismatch(self, tmp_path):
        from routers._enrichment_cache import get_schema_version
        from routers._enrichment_phases import _get_cached_chapter_result

        db = Database(db_path=tmp_path / "cr05_scope_hash.db")
        self._insert_project(db)
        schema_v = int(get_schema_version("sticky_sentences"))
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO enrichment_cache (
                    project_id, enrichment_type, entity_scope, status, phase,
                    input_hash, result_json, schema_version, computed_at, updated_at
                ) VALUES (
                    1, 'sticky_sentences', 'chapter:4', 'completed', 12,
                    'cached-hash', '{"ok": true}', ?, datetime('now'), datetime('now')
                )
                """,
                (schema_v,),
            )

        result = _get_cached_chapter_result(
            db_session=db,
            project_id=1,
            enrichment_type="sticky_sentences",
            chapter_number=4,
            expected_input_hash="current-hash",
        )
        assert result is None

    def test_entity_cache_ignores_schema_mismatch(self, tmp_path):
        from routers._enrichment_cache import get_schema_version
        from routers._enrichment_phases import _get_cached_entity_result

        db = Database(db_path=tmp_path / "cr05_scope_entity_schema.db")
        self._insert_project(db)
        schema_v = int(get_schema_version("character_timeline"))
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO enrichment_cache (
                    project_id, enrichment_type, entity_scope, status, phase,
                    result_json, schema_version, computed_at, updated_at
                ) VALUES (
                    1, 'character_timeline', 'entity:99', 'completed', 10,
                    '{"entity_id": 99}', ?, datetime('now'), datetime('now')
                )
                """,
                (max(0, schema_v - 1),),
            )

        result = _get_cached_entity_result(
            db_session=db,
            project_id=1,
            enrichment_type="character_timeline",
            entity_id=99,
        )
        assert result is None
