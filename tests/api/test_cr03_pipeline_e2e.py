"""E2E CR-03: PATCH settings -> analyze -> runtime gating efectivo."""

from __future__ import annotations

import time
from types import SimpleNamespace

from narrative_assistant.persistence.version_diff import ChapterDiffMetrics


def _patch_analysis_runtime(monkeypatch, grammar_calls: list[int]) -> None:
    """Parchea el runtime para ejecutar /analyze de forma síncrona y rápida."""

    class _DummyModelManager:
        @staticmethod
        def get_model_path(_model_type):  # noqa: ANN001
            return "/tmp/model.bin"

    def _fake_run_parsing(ctx, tracker):  # noqa: ANN001
        ctx["document_fingerprint"] = "fp-test-cr03"
        ctx["word_count"] = 120
        ctx["chapters_count"] = 1
        ctx["chapters_data"] = [{"chapter_number": 1, "content": "Texto de prueba."}]

    def _fake_run_ner(ctx, tracker):  # noqa: ANN001
        ctx.setdefault("entities", [])

    def _fake_run_attributes(ctx, tracker):  # noqa: ANN001
        ctx.setdefault("attributes", [])

    def _fake_run_grammar(ctx, tracker):  # noqa: ANN001
        grammar_calls.append(int(ctx["project_id"]))

    def _fake_build_incremental_plan(*args, **kwargs):  # noqa: ANN002, ANN003
        return {
            "mode": "incremental",
            "impacted_nodes": ["health"],
            "run_relationships": False,
            "run_voice": False,
            "run_prose": False,
            "run_health": False,
            "chapter_diff": {"modified": 1, "added": 0, "removed": 0, "changed_ratio": 0.05},
            "changed_chapter_numbers": [1],
            "impacted_chapter_numbers": [1],
            "impacted_entity_ids": [],
            "seed_entity_ids": [],
            "reason": "test_e2e",
        }

    def _fake_chapter_diff(self, snapshot_id, chapters_data):  # noqa: ANN001
        return ChapterDiffMetrics(
            total_previous=1,
            total_current=1,
            modified=1,
            added=0,
            removed=0,
            changed_ratio=0.05,
            modified_chapters=frozenset({1}),
        )

    def _fake_entity_diff(self, project_id, snapshot_id):  # noqa: ANN001
        return SimpleNamespace(
            new_entities=0,
            removed_entities=0,
            renamed=0,
            to_dict=lambda: {"new_entities": 0, "removed_entities": 0, "renamed": 0},
        )

    monkeypatch.setattr(
        "narrative_assistant.core.model_manager.get_model_manager",
        lambda: _DummyModelManager(),
    )
    monkeypatch.setattr("routers._analysis_phases.run_parsing", _fake_run_parsing)
    monkeypatch.setattr("routers._analysis_phases.run_snapshot", lambda *a, **k: None)
    monkeypatch.setattr("routers._analysis_phases.run_cleanup", lambda *a, **k: None)
    monkeypatch.setattr("routers._analysis_phases.run_classification", lambda *a, **k: None)
    monkeypatch.setattr("routers._analysis_phases.run_structure", lambda *a, **k: None)
    monkeypatch.setattr("routers._analysis_phases.claim_heavy_slot_or_queue", lambda *a, **k: True)
    monkeypatch.setattr("routers._analysis_phases.run_ollama_healthcheck", lambda *a, **k: None)
    monkeypatch.setattr("routers._analysis_phases.run_ner", _fake_run_ner)
    monkeypatch.setattr("routers._analysis_phases.run_llm_entity_validation", lambda *a, **k: None)
    monkeypatch.setattr("routers._analysis_phases.run_fusion", lambda *a, **k: None)
    monkeypatch.setattr("routers._analysis_phases.run_timeline", lambda *a, **k: None)
    monkeypatch.setattr("routers._analysis_phases.run_attributes", _fake_run_attributes)
    monkeypatch.setattr("routers._analysis_phases.run_consistency", lambda *a, **k: None)
    monkeypatch.setattr("routers._analysis_phases.run_grammar", _fake_run_grammar)
    monkeypatch.setattr("routers._analysis_phases._emit_grammar_alerts", lambda *a, **k: None)
    monkeypatch.setattr("routers._analysis_phases._emit_consistency_alerts", lambda *a, **k: None)
    monkeypatch.setattr("routers._analysis_phases.run_events", lambda *a, **k: None)
    monkeypatch.setattr("routers._analysis_phases.run_alerts", lambda *a, **k: None)
    monkeypatch.setattr("routers._analysis_phases.run_reconciliation", lambda *a, **k: None)
    monkeypatch.setattr("routers._analysis_phases.release_heavy_slot", lambda *a, **k: None)
    monkeypatch.setattr("routers._analysis_phases.handle_analysis_error", lambda *a, **k: None)
    monkeypatch.setattr("routers._analysis_phases.run_finally_cleanup", lambda *a, **k: None)
    monkeypatch.setattr(
        "narrative_assistant.persistence.version_diff.VersionDiffRepository.compute_chapter_diff",
        _fake_chapter_diff,
    )
    monkeypatch.setattr(
        "narrative_assistant.persistence.version_diff.VersionDiffRepository.compute_and_store_entity_links",
        _fake_entity_diff,
    )
    monkeypatch.setattr("routers._incremental_planner.build_incremental_plan", _fake_build_incremental_plan)
    monkeypatch.setattr("routers._enrichment_phases.capture_entity_fingerprint", lambda *a, **k: "")
    monkeypatch.setattr("routers._enrichment_phases.invalidate_enrichment_if_mutated", lambda *a, **k: None)
    monkeypatch.setattr("routers._enrichment_phases.write_version_metrics", lambda *a, **k: None)
    monkeypatch.setattr(
        "routers.projects._get_lightweight_capabilities",
        lambda: {"ollama_available": False, "languagetool_available": False, "has_gpu": False},
    )


def _wait_for_grammar_calls(grammar_calls: list[int], expected_count: int, timeout_sec: float = 12.0):
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if len(grammar_calls) >= expected_count:
            return True
        time.sleep(0.05)
    return len(grammar_calls) >= expected_count


def test_analyze_skips_grammar_when_grammar_and_spelling_disabled(
    test_client, sample_project, monkeypatch
):
    project_id = sample_project.id
    grammar_calls: list[int] = []
    _patch_analysis_runtime(monkeypatch, grammar_calls)

    patch_resp = test_client.patch(
        f"/api/projects/{project_id}/settings",
        json={"analysis_features": {"pipeline_flags": {"grammar": False, "spelling": False}}},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["success"] is True

    analyze_resp = test_client.post(
        f"/api/projects/{project_id}/analyze",
        files={"file": ("doc.txt", b"Texto de prueba", "text/plain")},
    )
    assert analyze_resp.status_code == 200
    analyze_payload = analyze_resp.json()
    assert analyze_payload["success"] is True, analyze_payload
    _wait_for_grammar_calls(grammar_calls, expected_count=1)
    assert grammar_calls == []


def test_analyze_runs_grammar_when_any_of_grammar_or_spelling_enabled(
    test_client, sample_project, monkeypatch
):
    project_id = sample_project.id
    grammar_calls: list[int] = []
    _patch_analysis_runtime(monkeypatch, grammar_calls)

    patch_resp = test_client.patch(
        f"/api/projects/{project_id}/settings",
        json={"analysis_features": {"pipeline_flags": {"grammar": True, "spelling": False}}},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["success"] is True

    analyze_resp = test_client.post(
        f"/api/projects/{project_id}/analyze",
        files={"file": ("doc.txt", b"Texto de prueba", "text/plain")},
    )
    assert analyze_resp.status_code == 200
    analyze_payload = analyze_resp.json()
    assert analyze_payload["success"] is True, analyze_payload
    assert _wait_for_grammar_calls(grammar_calls, expected_count=1)
    assert grammar_calls == [project_id]
