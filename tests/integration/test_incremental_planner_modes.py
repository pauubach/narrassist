import sys
from pathlib import Path

from narrative_assistant.persistence.database import Database

_api_server = str(Path(__file__).resolve().parents[2] / "api-server")
if _api_server not in sys.path:
    sys.path.insert(0, _api_server)

from routers._incremental_planner import build_incremental_plan


def _seed_snapshot(db: Database, project_id: int, snapshot_id: int, chapters: int) -> None:
    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO projects (
                id, name, document_path, document_format, document_fingerprint, word_count, chapter_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, "Proyecto Planner", "/tmp/doc.docx", "DOCX", "fp_seed", 5000, chapters),
        )
        conn.execute(
            """
            INSERT INTO analysis_snapshots (id, project_id, document_fingerprint, alert_count, entity_count, status)
            VALUES (?, ?, 'old_fp', 0, 0, 'complete')
            """,
            (snapshot_id, project_id),
        )
        for chapter_num in range(1, chapters + 1):
            conn.execute(
                """
                INSERT INTO snapshot_chapters (snapshot_id, project_id, chapter_number, content_hash, content_text)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    project_id,
                    chapter_num,
                    f"h{chapter_num}",
                    f"Texto base {chapter_num}",
                ),
            )


def test_incremental_planner_modes_across_scenarios(tmp_path) -> None:
    db = Database(db_path=tmp_path / "planner_modes.db")
    _seed_snapshot(db, project_id=1, snapshot_id=1, chapters=10)

    # Caso 1: cambio pequeño en 1 capítulo -> incremental con omisión de relaciones/voz.
    small_change = build_incremental_plan(
        db=db,
        project_id=1,
        snapshot_id=1,
        chapters_data=[
            {"chapter_number": i, "content": f"Texto base {i}." if i == 10 else f"Texto base {i}"}
            for i in range(1, 11)
        ],
    )
    assert small_change["mode"] == "incremental"
    assert small_change["run_relationships"] is False
    assert small_change["run_voice"] is False

    # Caso 2: cambio moderado en varios capítulos -> incremental con impacto en relaciones/voz.
    moderate_change = build_incremental_plan(
        db=db,
        project_id=1,
        snapshot_id=1,
        chapters_data=[
            {
                "chapter_number": i,
                "content": f"Texto base {i} editado con cambios narrativos"
                if i <= 3
                else f"Texto base {i}",
            }
            for i in range(1, 11)
        ],
    )
    assert moderate_change["mode"] == "incremental"
    assert moderate_change["run_relationships"] is True
    assert moderate_change["run_voice"] is True

    # Caso 3: cambio estructural (capítulo añadido) -> full.
    structural_change = build_incremental_plan(
        db=db,
        project_id=1,
        snapshot_id=1,
        chapters_data=[{"chapter_number": i, "content": f"Texto base {i}"} for i in range(1, 12)],
    )
    assert structural_change["mode"] == "full"
