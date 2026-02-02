# -*- coding: utf-8 -*-
"""
Tests unitarios para GoldenCorpusHarness.

Estos tests verifican la logica del harness sin ejecutar evaluaciones NLP costosas.
"""

import json
import tempfile
from pathlib import Path

import pytest

import sys
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "tests" / "evaluation"))

from golden_corpus_harness import (
    GoldenCorpusHarness,
    GoldStandardResult,
    CapabilityScore,
    RegressionInfo,
    ImprovementInfo,
    HarnessReport,
)


# ============================================================================
# Helpers
# ============================================================================

def _make_score(cap: str, p: float, r: float, f1: float, tp=0, fp=0, fn=0):
    return CapabilityScore(
        capability=cap,
        precision=p, recall=r, f1=f1,
        true_positives=tp, false_positives=fp, false_negatives=fn,
    )


def _make_result(name: str, scores: dict[str, CapabilityScore]):
    res = GoldStandardResult(name=name, text_file=f"test_books/{name}.txt")
    res.scores = scores
    return res


def _make_baseline(data: dict) -> Path:
    """Crea un archivo baseline temporal y retorna su path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(data, tmp, indent=2)
    tmp.close()
    return Path(tmp.name)


# ============================================================================
# Tests
# ============================================================================

class TestCapabilityScore:
    """Tests para CapabilityScore."""

    def test_basic_creation(self):
        score = _make_score("ner", 80.0, 90.0, 84.7, tp=9, fp=2, fn=1)
        assert score.capability == "ner"
        assert score.precision == 80.0
        assert score.recall == 90.0
        assert score.f1 == 84.7

    def test_zero_score(self):
        score = _make_score("ner", 0.0, 0.0, 0.0)
        assert score.f1 == 0.0


class TestGoldStandardResult:
    """Tests para GoldStandardResult."""

    def test_avg_f1_single(self):
        result = _make_result("test", {
            "ner": _make_score("ner", 80.0, 90.0, 84.7),
        })
        assert abs(result.avg_f1 - 84.7) < 0.01

    def test_avg_f1_multiple(self):
        result = _make_result("test", {
            "ner": _make_score("ner", 80.0, 90.0, 84.7),
            "chapters": _make_score("chapters", 100.0, 100.0, 100.0),
        })
        expected = (84.7 + 100.0) / 2
        assert abs(result.avg_f1 - expected) < 0.01

    def test_avg_f1_with_zero(self):
        result = _make_result("test", {
            "ner": _make_score("ner", 80.0, 90.0, 84.7),
            "chapters": _make_score("chapters", 0.0, 0.0, 0.0),
        })
        # Solo cuenta scores con f1 > 0
        assert abs(result.avg_f1 - 84.7) < 0.01

    def test_avg_f1_empty(self):
        result = _make_result("test", {})
        assert result.avg_f1 == 0.0

    def test_errors_list(self):
        result = _make_result("test", {})
        result.errors.append("some error")
        assert len(result.errors) == 1


class TestRegressionInfo:
    """Tests para RegressionInfo."""

    def test_is_critical_zero_f1(self):
        reg = RegressionInfo("gs", "ner", 80.0, 0.0, -80.0)
        assert reg.is_critical

    def test_is_critical_large_drop(self):
        reg = RegressionInfo("gs", "ner", 80.0, 50.0, -30.0)
        assert reg.is_critical

    def test_not_critical_small_drop(self):
        reg = RegressionInfo("gs", "ner", 80.0, 70.0, -10.0)
        assert not reg.is_critical


class TestHarnessReport:
    """Tests para HarnessReport."""

    def test_has_regressions_false(self):
        report = HarnessReport(timestamp="2026-01-01")
        assert not report.has_regressions

    def test_has_regressions_true(self):
        report = HarnessReport(
            timestamp="2026-01-01",
            regressions=[RegressionInfo("gs", "ner", 80.0, 70.0, -10.0)],
        )
        assert report.has_regressions

    def test_overall_f1(self):
        report = HarnessReport(
            timestamp="2026-01-01",
            aggregate_scores={
                "ner": _make_score("ner", 0, 0, 0, tp=9, fp=1, fn=1),
                "chapters": _make_score("chapters", 0, 0, 0, tp=5, fp=0, fn=0),
            },
        )
        # tp=14, fp=1, fn=1
        # p = 14/15, r = 14/15, f1 = 2*p*r/(p+r) = p = 14/15
        expected = 14 / 15
        assert abs(report.overall_f1 - expected) < 0.01


class TestHarnessDetectRegressions:
    """Tests para deteccion de regresiones."""

    def _make_harness_with_baseline(self, baseline_data: dict):
        path = _make_baseline(baseline_data)
        return GoldenCorpusHarness(
            regression_threshold=5.0,
            baseline_path=path,
            history_path=Path(tempfile.mktemp(suffix=".json")),
        )

    def test_no_regression(self):
        """Sin regresion si F1 es igual o mejor."""
        baseline = {
            "test_gs": {
                "summary": {"ner": {"f1": 80.0}},
            }
        }
        harness = self._make_harness_with_baseline(baseline)

        current = {
            "test_gs": _make_result("test_gs", {
                "ner": _make_score("ner", 90.0, 90.0, 90.0),
            }),
        }
        regressions, improvements = harness.detect_regressions(current)
        assert len(regressions) == 0
        # delta=+10 > threshold(5) → mejora detectada
        assert len(improvements) == 1

    def test_regression_detected(self):
        """Regresion detectada si F1 cae mas de 5pp."""
        baseline = {
            "test_gs": {
                "summary": {"ner": {"f1": 80.0}},
            }
        }
        harness = self._make_harness_with_baseline(baseline)

        current = {
            "test_gs": _make_result("test_gs", {
                "ner": _make_score("ner", 70.0, 70.0, 70.0),
            }),
        }
        regressions, improvements = harness.detect_regressions(current)
        assert len(regressions) == 1
        assert regressions[0].delta == -10.0

    def test_within_threshold(self):
        """No regresion si la caida esta dentro del umbral."""
        baseline = {
            "test_gs": {
                "summary": {"ner": {"f1": 80.0}},
            }
        }
        harness = self._make_harness_with_baseline(baseline)

        current = {
            "test_gs": _make_result("test_gs", {
                "ner": _make_score("ner", 76.0, 76.0, 76.0),
            }),
        }
        regressions, improvements = harness.detect_regressions(current)
        assert len(regressions) == 0
        assert len(improvements) == 0

    def test_no_baseline_no_regression(self):
        """Sin baseline, no hay regresiones."""
        harness = self._make_harness_with_baseline({})

        current = {
            "test_gs": _make_result("test_gs", {
                "ner": _make_score("ner", 50.0, 50.0, 50.0),
            }),
        }
        regressions, improvements = harness.detect_regressions(current)
        assert len(regressions) == 0

    def test_multiple_capabilities(self):
        """Detecta regresion en una capacidad y mejora en otra."""
        baseline = {
            "test_gs": {
                "summary": {
                    "ner": {"f1": 80.0},
                    "chapters": {"f1": 60.0},
                },
            }
        }
        harness = self._make_harness_with_baseline(baseline)

        current = {
            "test_gs": _make_result("test_gs", {
                "ner": _make_score("ner", 70.0, 70.0, 70.0),
                "chapters": _make_score("chapters", 90.0, 90.0, 90.0),
            }),
        }
        regressions, improvements = harness.detect_regressions(current)
        assert len(regressions) == 1
        assert regressions[0].capability == "ner"
        assert len(improvements) == 1
        assert improvements[0].capability == "chapters"


class TestHarnessComputeAggregate:
    """Tests para compute_aggregate."""

    def test_single_result(self):
        results = {
            "gs1": _make_result("gs1", {
                "ner": _make_score("ner", 0, 0, 0, tp=8, fp=2, fn=1),
            }),
        }
        aggregate = GoldenCorpusHarness.compute_aggregate(results)
        assert "ner" in aggregate
        assert aggregate["ner"].true_positives == 8
        # P = 8/10 = 80%
        assert abs(aggregate["ner"].precision - 80.0) < 0.1

    def test_aggregation_across_multiple(self):
        results = {
            "gs1": _make_result("gs1", {
                "ner": _make_score("ner", 0, 0, 0, tp=8, fp=2, fn=1),
            }),
            "gs2": _make_result("gs2", {
                "ner": _make_score("ner", 0, 0, 0, tp=5, fp=1, fn=4),
            }),
        }
        aggregate = GoldenCorpusHarness.compute_aggregate(results)
        # tp=13, fp=3, fn=5
        # P = 13/16 = 81.25%
        # R = 13/18 = 72.2%
        assert aggregate["ner"].true_positives == 13
        assert aggregate["ner"].false_positives == 3
        assert aggregate["ner"].false_negatives == 5

    def test_empty_results(self):
        aggregate = GoldenCorpusHarness.compute_aggregate({})
        assert aggregate == {}


class TestHarnessBaselineIO:
    """Tests para carga y guardado de baseline."""

    def test_load_nonexistent(self):
        harness = GoldenCorpusHarness(
            baseline_path=Path("/nonexistent/path.json"),
        )
        baseline = harness.load_baseline()
        assert baseline == {}

    def test_save_and_load(self):
        tmp_baseline = Path(tempfile.mktemp(suffix=".json"))
        harness = GoldenCorpusHarness(baseline_path=tmp_baseline)

        report = HarnessReport(
            timestamp="2026-01-01T00:00:00",
            results={
                "test_gs": _make_result("test_gs", {
                    "ner": _make_score("ner", 80.0, 90.0, 84.7, tp=9, fp=2, fn=1),
                }),
            },
        )

        harness.save_baseline(report)
        assert tmp_baseline.exists()

        # Resetear cache y recargar
        harness._baseline = None
        loaded = harness.load_baseline()
        assert "test_gs" in loaded
        assert "summary" in loaded["test_gs"]
        assert loaded["test_gs"]["summary"]["ner"]["f1"] == 84.7

        # Cleanup
        tmp_baseline.unlink(missing_ok=True)

    def test_get_baseline_f1(self):
        baseline = {
            "test_gs": {
                "summary": {"ner": {"f1": 84.7}},
            }
        }
        path = _make_baseline(baseline)
        harness = GoldenCorpusHarness(baseline_path=path)

        assert harness.get_baseline_f1("test_gs", "ner") == 84.7
        assert harness.get_baseline_f1("test_gs", "chapters") is None
        assert harness.get_baseline_f1("nonexistent", "ner") is None


class TestHarnessHistory:
    """Tests para historial de evaluaciones."""

    def test_append_history(self):
        tmp_history = Path(tempfile.mktemp(suffix=".json"))
        harness = GoldenCorpusHarness(history_path=tmp_history)

        report = HarnessReport(
            timestamp="2026-01-01T00:00:00",
            aggregate_scores={
                "ner": _make_score("ner", 80.0, 90.0, 84.7, tp=9, fp=2, fn=1),
            },
            elapsed_seconds=10.5,
        )

        harness._append_history(report)
        assert tmp_history.exists()

        with open(tmp_history, "r") as f:
            history = json.load(f)

        assert len(history) == 1
        assert history[0]["timestamp"] == "2026-01-01T00:00:00"
        assert "per_capability" in history[0]
        assert "ner" in history[0]["per_capability"]

        # Agregar otra entrada
        report.timestamp = "2026-01-02T00:00:00"
        harness._append_history(report)

        with open(tmp_history, "r") as f:
            history = json.load(f)
        assert len(history) == 2

        # Cleanup
        tmp_history.unlink(missing_ok=True)


class TestHarnessFormatReport:
    """Tests para formateo de reportes."""

    def test_format_empty_report(self):
        harness = GoldenCorpusHarness()
        report = HarnessReport(timestamp="2026-01-01T00:00:00")
        text = harness.format_report(report)
        assert "GOLDEN CORPUS HARNESS" in text
        assert "Sin regresiones detectadas" in text

    def test_format_with_regressions(self):
        harness = GoldenCorpusHarness()
        report = HarnessReport(
            timestamp="2026-01-01T00:00:00",
            regressions=[
                RegressionInfo("gs1", "ner", 80.0, 70.0, -10.0),
            ],
        )
        text = harness.format_report(report)
        assert "REGRESIONES DETECTADAS" in text
        assert "gs1/ner" in text

    def test_format_with_improvements(self):
        harness = GoldenCorpusHarness()
        report = HarnessReport(
            timestamp="2026-01-01T00:00:00",
            improvements=[
                ImprovementInfo("gs1", "chapters", 60.0, 90.0, 30.0),
            ],
        )
        text = harness.format_report(report)
        assert "MEJORAS DETECTADAS" in text
        assert "gs1/chapters" in text

    def test_format_with_results(self):
        harness = GoldenCorpusHarness()
        report = HarnessReport(
            timestamp="2026-01-01T00:00:00",
            results={
                "gs1": _make_result("gs1", {
                    "ner": _make_score("ner", 80.0, 90.0, 84.7),
                }),
            },
            aggregate_scores={
                "ner": _make_score("ner", 80.0, 90.0, 84.7, tp=9, fp=2, fn=1),
            },
        )
        text = harness.format_report(report)
        assert "gs1" in text
        assert "84.7" in text
        assert "METRICAS AGREGADAS" in text
