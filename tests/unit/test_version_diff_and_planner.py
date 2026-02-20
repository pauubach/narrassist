"""Tests para diff de versiones + planner incremental."""

import sys
from pathlib import Path

from narrative_assistant.persistence.database import Database
from narrative_assistant.persistence.version_diff import VersionDiffRepository

_api_server = str(Path(__file__).resolve().parents[2] / "api-server")
if _api_server not in sys.path:
    sys.path.insert(0, _api_server)

from routers._incremental_planner import build_incremental_plan, build_phase_plan
from routers.projects import router as projects_router


def _insert_project(db: Database, project_id: int = 1) -> None:
    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO projects (
                id, name, document_path, document_format, document_fingerprint, word_count, chapter_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, "Proyecto", "/tmp/doc.docx", "DOCX", "fp_seed", 1200, 2),
        )


def test_chapter_diff_metrics_from_snapshot(tmp_path):
    db = Database(db_path=tmp_path / "diff.db")
    _insert_project(db)

    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO analysis_snapshots (id, project_id, document_fingerprint, alert_count, entity_count, status)
            VALUES (1, 1, 'old_fp', 0, 0, 'complete')
            """
        )
        conn.execute(
            """
            INSERT INTO snapshot_chapters (snapshot_id, project_id, chapter_number, content_hash, content_text)
            VALUES (1, 1, 1, 'a', 'Texto capítulo uno')
            """
        )
        conn.execute(
            """
            INSERT INTO snapshot_chapters (snapshot_id, project_id, chapter_number, content_hash, content_text)
            VALUES (1, 1, 2, 'b', 'Texto capítulo dos')
            """
        )

    repo = VersionDiffRepository(db)
    metrics = repo.compute_chapter_diff(
        snapshot_id=1,
        chapters_data=[
            {"chapter_number": 1, "content": "Texto capítulo uno editado"},
            {"chapter_number": 2, "content": "Texto capítulo dos"},
            {"chapter_number": 3, "content": "Capítulo nuevo"},
        ],
    )

    assert metrics.modified == 1
    assert metrics.added == 1
    assert metrics.removed == 0
    assert metrics.changed_ratio > 0.60


def test_entity_links_detect_rename_using_aliases(tmp_path):
    db = Database(db_path=tmp_path / "links.db")
    _insert_project(db)

    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO analysis_snapshots (id, project_id, document_fingerprint, alert_count, entity_count, status)
            VALUES (1, 1, 'old_fp', 0, 1, 'complete')
            """
        )
        conn.execute(
            """
            INSERT INTO snapshot_entities (
                snapshot_id, project_id, original_entity_id, entity_type, canonical_name, aliases, importance, mention_count
            ) VALUES (1, 1, 10, 'character', 'Pepe García', '[]', 'high', 12)
            """
        )
        conn.execute(
            """
            INSERT INTO entities (id, project_id, entity_type, canonical_name, importance, mention_count, is_active)
            VALUES (20, 1, 'character', 'José García', 'high', 14, 1)
            """
        )
        conn.execute(
            """
            INSERT INTO entity_mentions (entity_id, chapter_id, surface_form, start_char, end_char, source)
            VALUES (20, NULL, 'Pepe García', 0, 11, 'ner')
            """
        )

    repo = VersionDiffRepository(db)
    result = repo.compute_and_store_entity_links(project_id=1, snapshot_id=1)

    assert result.renamed == 1
    assert result.new_entities == 0
    assert result.removed_entities == 0


def test_incremental_planner_skips_entity_enrichment_for_small_changes(tmp_path):
    db = Database(db_path=tmp_path / "plan.db")
    _insert_project(db)

    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO analysis_snapshots (id, project_id, document_fingerprint, alert_count, entity_count, status)
            VALUES (1, 1, 'old_fp', 0, 0, 'complete')
            """
        )
        for chapter_num in range(1, 11):
            conn.execute(
                """
                INSERT INTO snapshot_chapters (snapshot_id, project_id, chapter_number, content_hash, content_text)
                VALUES (1, 1, ?, ?, ?)
                """,
                (chapter_num, f"h{chapter_num}", f"Capitulo base {chapter_num}"),
            )

    plan = build_incremental_plan(
        db=db,
        project_id=1,
        snapshot_id=1,
        chapters_data=[
            {
                "chapter_number": chapter_num,
                "content": (
                    f"Capitulo base {chapter_num}."
                    if chapter_num == 10
                    else f"Capitulo base {chapter_num}"
                ),
            }
            for chapter_num in range(1, 11)
        ],
    )

    assert plan["mode"] == "incremental"
    assert plan["run_relationships"] is False
    assert plan["run_voice"] is False


def test_incremental_planner_forces_full_on_structure_change(tmp_path):
    db = Database(db_path=tmp_path / "plan_full.db")
    _insert_project(db)

    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO analysis_snapshots (id, project_id, document_fingerprint, alert_count, entity_count, status)
            VALUES (1, 1, 'old_fp', 0, 0, 'complete')
            """
        )
        for chapter_num in range(1, 5):
            conn.execute(
                """
                INSERT INTO snapshot_chapters (snapshot_id, project_id, chapter_number, content_hash, content_text)
                VALUES (1, 1, ?, ?, ?)
                """,
                (chapter_num, f"h{chapter_num}", f"Texto capitulo {chapter_num}"),
            )

    plan = build_incremental_plan(
        db=db,
        project_id=1,
        snapshot_id=1,
        chapters_data=[
            {"chapter_number": 1, "content": "Texto capitulo 1"},
            {"chapter_number": 2, "content": "Texto capitulo 2"},
            {"chapter_number": 3, "content": "Texto capitulo 3"},
            {"chapter_number": 4, "content": "Texto capitulo 4"},
            {"chapter_number": 5, "content": "Capitulo nuevo"},  # añadido -> full
        ],
    )

    assert plan["mode"] == "full"
    assert plan["run_relationships"] is True
    assert plan["run_voice"] is True


def test_phase_plan_dependency_closure_adds_health():
    from narrative_assistant.persistence.version_diff import ChapterDiffMetrics

    chapter_diff = ChapterDiffMetrics(
        total_previous=10,
        total_current=10,
        modified=1,
        added=0,
        removed=0,
        changed_ratio=0.15,
    )

    plan = build_phase_plan(
        chapter_diff=chapter_diff,
        entity_changes={"has_ner_delta": True, "has_attribute_delta": False},
        invalidations={},
    )

    assert plan["mode"] == "incremental"
    assert plan["run_relationships"] is True
    assert plan["run_voice"] is True
    assert plan["run_health"] is True
    assert "health" in plan["impacted_nodes"]


def test_projects_router_exposes_version_diff_endpoints():
    paths = [r.path for r in projects_router.routes]
    assert "/api/projects/{project_id}/versions/summary" in paths
    assert "/api/projects/{project_id}/versions/{version_num}/entity-links" in paths
    assert "/api/projects/{project_id}/versions/compare" in paths
