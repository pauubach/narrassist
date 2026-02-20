"""Tests para identidad de manuscrito y política uncertain."""

import sys
from pathlib import Path

from narrative_assistant.persistence.database import Database
from narrative_assistant.persistence.manuscript_identity import (
    IDENTITY_DIFFERENT_DOCUMENT,
    IDENTITY_SAME_DOCUMENT,
    IDENTITY_UNCERTAIN,
    ManuscriptIdentityRepository,
    ManuscriptIdentityService,
)

_api_server = str(Path(__file__).resolve().parents[2] / "api-server")
if _api_server not in sys.path:
    sys.path.insert(0, _api_server)


def test_identity_service_near_revision_not_classified_as_different():
    service = ManuscriptIdentityService()
    base_block = (
        "Capítulo 1. Ana camina por la ciudad, observa vitrinas y recuerda la promesa.\n"
        "Capítulo 2. Luis espera en la estación y revisa el reloj mientras llueve.\n"
    )
    original = "\n".join([base_block for _ in range(30)])
    revised = original.replace("revisa el reloj", "revisa su reloj", 3)
    revised = revised.replace("recuerda la promesa", "recuerda una promesa", 2)

    decision = service.classify(original, revised)

    assert decision.classification in {IDENTITY_SAME_DOCUMENT, IDENTITY_UNCERTAIN}
    assert decision.signals.weighted_score >= 0.55


def test_identity_service_detects_different_document():
    service = ManuscriptIdentityService()
    novel_a = (
        "Capítulo 1\nEl detective llega a Madrid.\n\n"
        "Capítulo 2\nEncuentra pistas en el puerto."
    )
    novel_b = (
        "Manual de jardinería\n\n"
        "Cómo podar rosales en invierno y preparar el suelo para primavera."
    )

    decision = service.classify(novel_a, novel_b)

    assert decision.classification == IDENTITY_DIFFERENT_DOCUMENT
    assert decision.signals.weighted_score <= 0.45


def test_identity_repo_uncertain_rolling_count(tmp_path):
    db = Database(db_path=tmp_path / "identity.db")
    repo = ManuscriptIdentityRepository(db)
    service = ManuscriptIdentityService()

    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO projects (
                id, name, document_path, document_format, document_fingerprint, word_count, chapter_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (1, "Proyecto test", "/tmp/manuscrito.docx", "DOCX", "seed", 1000, 10),
        )

    # Reutilizar un decision base y forzar clasificación uncertain para el test.
    base_decision = service.classify("texto A", "texto B")
    uncertain_decision = base_decision.__class__(
        classification=IDENTITY_UNCERTAIN,
        confidence=0.61,
        signals=base_decision.signals,
        recommended_full_run=True,
    )

    for _ in range(4):
        repo.record_check(
            project_id=1,
            license_subject="license:test-1",
            previous_fingerprint="old-fp",
            candidate_fingerprint="new-fp",
            decision=uncertain_decision,
        )

    count = repo.uncertain_count_rolling("license:test-1", days=30)
    assert count == 4

    repo.upsert_risk_state(
        license_subject="license:test-1",
        uncertain_count_30d=count,
        review_required=count > 3,
    )

    row = db.fetchone(
        """
        SELECT uncertain_count_30d, review_required
        FROM manuscript_identity_risk_state
        WHERE license_subject = ?
        """,
        ("license:test-1",),
    )
    assert row is not None
    assert int(row["uncertain_count_30d"]) == 4
    assert int(row["review_required"]) == 1


def test_projects_router_has_identity_endpoints():
    from routers.projects import router

    paths = [route.path for route in router.routes]
    assert "/api/projects/{project_id}/document/replace" in paths
    assert "/api/projects/{project_id}/identity/last-check" in paths
