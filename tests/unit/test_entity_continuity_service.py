import json
from pathlib import Path

from narrative_assistant.analysis.entity_continuity_service import EntityContinuityService


def _load_fixture_cases() -> list[dict]:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "entity_continuity_cases.json"
    with fixture_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_entity_continuity_fixture_metrics() -> None:
    service = EntityContinuityService()
    cases = _load_fixture_cases()

    expected_renamed_total = 0
    predicted_renamed_total = 0
    true_positive_renamed = 0

    for case in cases:
        links, metrics = service.match_entities_between_versions(
            old_entities=case["old_entities"],
            new_entities=case["new_entities"],
        )
        expected = case["expected"]

        assert metrics.matched == int(expected["matched"]), case["name"]
        assert metrics.renamed == int(expected["renamed"]), case["name"]
        assert metrics.new_entities == int(expected["new_entities"]), case["name"]
        assert metrics.removed_entities == int(expected["removed_entities"]), case["name"]

        expected_renamed_total += int(expected["renamed"])
        predicted_case_renamed = [link for link in links if link["link_type"] == "renamed"]
        predicted_renamed_total += len(predicted_case_renamed)

        # TP: si se esperaba al menos un renombre y se detectó al menos uno.
        if int(expected["renamed"]) > 0 and predicted_case_renamed:
            true_positive_renamed += 1

    precision = (
        true_positive_renamed / predicted_renamed_total if predicted_renamed_total > 0 else 1.0
    )
    recall = true_positive_renamed / expected_renamed_total if expected_renamed_total > 0 else 1.0

    assert precision >= 0.9
    assert recall >= 0.9
