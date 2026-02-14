"""Regression tests for temporal marker offsets in PipelineNERMixin."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from narrative_assistant.pipelines.ua_ner import PipelineNERMixin


class _DummyPipeline(PipelineNERMixin):
    """Minimal concrete class to test mixin methods in isolation."""


class _Marker:
    def __init__(self, start_char: int, end_char: int):
        self.start_char = start_char
        self.end_char = end_char


def test_temporal_markers_are_offset_to_global_positions(monkeypatch):
    from narrative_assistant.temporal import markers as markers_module

    class FakeTemporalMarkerExtractor:
        def extract(self, text: str, chapter: int | None = None):
            if chapter == 1:
                return [_Marker(2, 8)]
            if chapter == 2:
                return [_Marker(1, 3)]
            return []

    monkeypatch.setattr(
        markers_module,
        "TemporalMarkerExtractor",
        FakeTemporalMarkerExtractor,
    )

    pipeline = _DummyPipeline()
    context = SimpleNamespace(
        chapters=[
            {"number": 1, "content": "capitulo uno", "start_char": 100},
            {"number": 2, "content": "capitulo dos", "start_char": 250},
        ],
        full_text="x" * 1000,
        temporal_markers=[],
        stats={},
    )

    pipeline._extract_temporal_markers(context)

    assert len(context.temporal_markers) == 2

    first = context.temporal_markers[0]
    second = context.temporal_markers[1]

    assert (first.start_char, first.end_char) == (102, 108)
    assert (second.start_char, second.end_char) == (251, 253)
    assert context.stats["temporal_markers"] == 2


def test_temporal_markers_keep_local_positions_when_start_is_zero(monkeypatch):
    from narrative_assistant.temporal import markers as markers_module

    class FakeTemporalMarkerExtractor:
        def extract(self, text: str, chapter: int | None = None):
            return [_Marker(4, 9)]

    monkeypatch.setattr(
        markers_module,
        "TemporalMarkerExtractor",
        FakeTemporalMarkerExtractor,
    )

    pipeline = _DummyPipeline()
    context = SimpleNamespace(
        chapters=[
            {"number": 1, "content": "capitulo", "start_char": 0},
        ],
        full_text="x" * 100,
        temporal_markers=[],
        stats={},
    )

    pipeline._extract_temporal_markers(context)

    assert len(context.temporal_markers) == 1
    marker = context.temporal_markers[0]
    assert (marker.start_char, marker.end_char) == (4, 9)
    assert context.stats["temporal_markers"] == 1

