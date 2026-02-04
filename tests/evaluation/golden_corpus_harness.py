"""
Golden Corpus Harness — marco unificado de evaluacion con deteccion de regresiones.

Orquesta la evaluacion de todas las capacidades NLP contra gold standards,
compara resultados con una baseline guardada y detecta regresiones automaticamente.

Uso desde pytest:
    pytest tests/evaluation/test_golden_corpus.py -v

Uso desde CLI:
    python tests/evaluation/golden_corpus_harness.py [--update-baseline] [--verbose]
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# Paths del proyecto
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from gold_standards import ADVANCED_GOLD_STANDARDS, ALL_GOLD_STANDARDS
from run_evaluation import (
    EvaluationMetrics,
    EvaluationReport,
    run_evaluation,
)

logger = logging.getLogger(__name__)

# ============================================================================
# Dataclasses
# ============================================================================

BASELINE_PATH = Path(__file__).parent / "baseline_results.json"
HISTORY_PATH = Path(__file__).parent / "evaluation_history.json"

# Umbral por defecto: una caida de F1 > 5pp se considera regresion
DEFAULT_REGRESSION_THRESHOLD = 5.0


@dataclass
class CapabilityScore:
    """Metricas de una capacidad en una evaluacion."""

    capability: str
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0


@dataclass
class GoldStandardResult:
    """Resultado completo de un gold standard."""

    name: str
    text_file: str
    scores: dict[str, CapabilityScore] = field(default_factory=dict)
    elapsed_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def avg_f1(self) -> float:
        """F1 promedio sobre todas las capacidades evaluadas."""
        valid = [s.f1 for s in self.scores.values() if s.f1 > 0]
        return sum(valid) / len(valid) if valid else 0.0


@dataclass
class RegressionInfo:
    """Informacion de una regresion detectada."""

    gold_standard: str
    capability: str
    baseline_f1: float
    current_f1: float
    delta: float  # negativo = regresion

    @property
    def is_critical(self) -> bool:
        """Regresion critica: F1 cayo a 0 o mas de 20pp."""
        return self.current_f1 == 0.0 or self.delta < -20.0


@dataclass
class ImprovementInfo:
    """Informacion de una mejora detectada."""

    gold_standard: str
    capability: str
    baseline_f1: float
    current_f1: float
    delta: float  # positivo = mejora


@dataclass
class HarnessReport:
    """Reporte completo del harness."""

    timestamp: str
    results: dict[str, GoldStandardResult] = field(default_factory=dict)
    regressions: list[RegressionInfo] = field(default_factory=list)
    improvements: list[ImprovementInfo] = field(default_factory=list)
    aggregate_scores: dict[str, CapabilityScore] = field(default_factory=dict)
    elapsed_seconds: float = 0.0

    @property
    def has_regressions(self) -> bool:
        return len(self.regressions) > 0

    @property
    def has_critical_regressions(self) -> bool:
        return any(r.is_critical for r in self.regressions)

    @property
    def overall_f1(self) -> float:
        """F1 global agregado micro-averaged."""
        total_tp = sum(s.true_positives for s in self.aggregate_scores.values())
        total_fp = sum(s.false_positives for s in self.aggregate_scores.values())
        total_fn = sum(s.false_negatives for s in self.aggregate_scores.values())
        p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


# ============================================================================
# GoldenCorpusHarness
# ============================================================================


class GoldenCorpusHarness:
    """
    Marco unificado de evaluacion contra golden corpus.

    Orquesta evaluaciones, detecta regresiones y gestiona la baseline.
    """

    def __init__(
        self,
        regression_threshold: float = DEFAULT_REGRESSION_THRESHOLD,
        baseline_path: Optional[Path] = None,
        history_path: Optional[Path] = None,
        verbose: bool = False,
    ):
        self.regression_threshold = regression_threshold
        self.baseline_path = baseline_path or BASELINE_PATH
        self.history_path = history_path or HISTORY_PATH
        self.verbose = verbose
        self._baseline: Optional[dict] = None

    # ------------------------------------------------------------------
    # Baseline
    # ------------------------------------------------------------------

    def load_baseline(self) -> dict:
        """Carga la baseline de resultados previos."""
        if self._baseline is not None:
            return self._baseline

        if self.baseline_path.exists():
            with open(self.baseline_path, encoding="utf-8") as f:
                self._baseline = json.load(f)
        else:
            self._baseline = {}
        return self._baseline

    def save_baseline(self, report: HarnessReport) -> None:
        """Guarda resultados actuales como nueva baseline."""
        data = {}
        for gs_name, gs_result in report.results.items():
            data[gs_name] = {
                "timestamp": report.timestamp,
                "gold_standard_name": gs_name,
                "text_file": gs_result.text_file,
                "metrics": {},
                "summary": {},
            }
            for cap_name, score in gs_result.scores.items():
                data[gs_name]["metrics"][cap_name] = {
                    "capability": cap_name,
                    "true_positives": score.true_positives,
                    "false_positives": score.false_positives,
                    "false_negatives": score.false_negatives,
                    "precision": score.precision / 100.0,
                    "recall": score.recall / 100.0,
                    "f1_score": score.f1 / 100.0,
                    "details": {},
                }
                data[gs_name]["summary"][cap_name] = {
                    "precision": round(score.precision, 1),
                    "recall": round(score.recall, 1),
                    "f1": round(score.f1, 1),
                }

        with open(self.baseline_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("Baseline guardada en %s", self.baseline_path)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def _append_history(self, report: HarnessReport) -> None:
        """Agrega el resultado al historial."""
        history = []
        if self.history_path.exists():
            try:
                with open(self.history_path, encoding="utf-8") as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []

        entry = {
            "timestamp": report.timestamp,
            "overall_f1": round(report.overall_f1 * 100, 1),
            "regressions": len(report.regressions),
            "improvements": len(report.improvements),
            "elapsed_seconds": round(report.elapsed_seconds, 1),
            "per_capability": {},
        }
        for cap_name, score in report.aggregate_scores.items():
            entry["per_capability"][cap_name] = {
                "f1": round(score.f1, 1),
                "precision": round(score.precision, 1),
                "recall": round(score.recall, 1),
            }

        history.append(entry)

        # Mantener solo las ultimas 50 entradas
        history = history[-50:]

        with open(self.history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Evaluacion individual
    # ------------------------------------------------------------------

    def evaluate_gold_standard(
        self,
        name: str,
        capabilities: Optional[list[str]] = None,
    ) -> GoldStandardResult:
        """Evalua un gold standard y devuelve el resultado."""
        all_standards = {**ALL_GOLD_STANDARDS, **ADVANCED_GOLD_STANDARDS}
        if name not in all_standards:
            raise ValueError(
                f"Gold standard '{name}' no encontrado. Disponibles: {list(all_standards.keys())}"
            )

        gs = all_standards[name]
        result = GoldStandardResult(name=name, text_file=gs.text_file)

        start = time.time()
        try:
            report = run_evaluation(name, capabilities=capabilities, verbose=self.verbose)

            for cap_name, summary in report.summary.items():
                raw = report.metrics.get(cap_name, {})
                result.scores[cap_name] = CapabilityScore(
                    capability=cap_name,
                    precision=summary["precision"],
                    recall=summary["recall"],
                    f1=summary["f1"],
                    true_positives=raw.get("true_positives", 0),
                    false_positives=raw.get("false_positives", 0),
                    false_negatives=raw.get("false_negatives", 0),
                )
        except Exception as e:
            result.errors.append(str(e))
            logger.error("Error evaluando %s: %s", name, e)

        result.elapsed_seconds = time.time() - start
        return result

    # ------------------------------------------------------------------
    # Deteccion de regresiones
    # ------------------------------------------------------------------

    def detect_regressions(
        self,
        current: dict[str, GoldStandardResult],
    ) -> tuple[list[RegressionInfo], list[ImprovementInfo]]:
        """Compara resultados actuales con baseline y detecta cambios."""
        baseline = self.load_baseline()
        regressions: list[RegressionInfo] = []
        improvements: list[ImprovementInfo] = []

        for gs_name, gs_result in current.items():
            if gs_name not in baseline:
                continue

            baseline_summary = baseline[gs_name].get("summary", {})

            for cap_name, score in gs_result.scores.items():
                if cap_name not in baseline_summary:
                    continue

                baseline_f1 = baseline_summary[cap_name].get("f1", 0.0)
                current_f1 = score.f1
                delta = current_f1 - baseline_f1

                if delta < -self.regression_threshold:
                    regressions.append(
                        RegressionInfo(
                            gold_standard=gs_name,
                            capability=cap_name,
                            baseline_f1=baseline_f1,
                            current_f1=current_f1,
                            delta=delta,
                        )
                    )
                elif delta > self.regression_threshold:
                    improvements.append(
                        ImprovementInfo(
                            gold_standard=gs_name,
                            capability=cap_name,
                            baseline_f1=baseline_f1,
                            current_f1=current_f1,
                            delta=delta,
                        )
                    )

        return regressions, improvements

    # ------------------------------------------------------------------
    # Metricas agregadas
    # ------------------------------------------------------------------

    @staticmethod
    def compute_aggregate(
        results: dict[str, GoldStandardResult],
    ) -> dict[str, CapabilityScore]:
        """Calcula metricas agregadas micro-averaged por capacidad."""
        accum: dict[str, dict] = {}

        for gs_result in results.values():
            for cap_name, score in gs_result.scores.items():
                if cap_name not in accum:
                    accum[cap_name] = {"tp": 0, "fp": 0, "fn": 0}
                accum[cap_name]["tp"] += score.true_positives
                accum[cap_name]["fp"] += score.false_positives
                accum[cap_name]["fn"] += score.false_negatives

        aggregate: dict[str, CapabilityScore] = {}
        for cap_name, counts in accum.items():
            tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
            p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
            aggregate[cap_name] = CapabilityScore(
                capability=cap_name,
                precision=round(p * 100, 1),
                recall=round(r * 100, 1),
                f1=round(f1 * 100, 1),
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
            )

        return aggregate

    # ------------------------------------------------------------------
    # Ejecucion completa
    # ------------------------------------------------------------------

    def run_all(
        self,
        gold_standards: Optional[list[str]] = None,
        capabilities: Optional[list[str]] = None,
        include_advanced: bool = False,
        save_history: bool = True,
    ) -> HarnessReport:
        """Ejecuta evaluacion completa y genera reporte."""
        start = time.time()

        # Seleccionar gold standards
        available = dict(ALL_GOLD_STANDARDS)
        if include_advanced:
            available.update(ADVANCED_GOLD_STANDARDS)

        if gold_standards:
            names = [n for n in gold_standards if n in available]
        else:
            names = list(available.keys())

        # Evaluar cada gold standard
        results: dict[str, GoldStandardResult] = {}
        for name in names:
            logger.info("Evaluando gold standard: %s", name)
            results[name] = self.evaluate_gold_standard(name, capabilities)

        # Detectar regresiones
        regressions, improvements = self.detect_regressions(results)

        # Agregar metricas
        aggregate = self.compute_aggregate(results)

        report = HarnessReport(
            timestamp=datetime.now().isoformat(),
            results=results,
            regressions=regressions,
            improvements=improvements,
            aggregate_scores=aggregate,
            elapsed_seconds=time.time() - start,
        )

        if save_history:
            self._append_history(report)

        return report

    # ------------------------------------------------------------------
    # API para pytest
    # ------------------------------------------------------------------

    def check_no_regressions(
        self,
        gold_standard: str,
        capability: str,
    ) -> tuple[bool, Optional[RegressionInfo]]:
        """
        Verifica que no hay regresion para un gold_standard + capability.

        Retorna (passed, regression_info).
        """
        result = self.evaluate_gold_standard(gold_standard, capabilities=[capability])
        regressions, _ = self.detect_regressions({gold_standard: result})

        for reg in regressions:
            if reg.capability == capability:
                return False, reg

        return True, None

    def get_baseline_f1(self, gold_standard: str, capability: str) -> Optional[float]:
        """Obtiene el F1 de baseline para un gold_standard + capability."""
        baseline = self.load_baseline()
        if gold_standard not in baseline:
            return None
        summary = baseline[gold_standard].get("summary", {})
        if capability not in summary:
            return None
        return summary[capability].get("f1")

    # ------------------------------------------------------------------
    # Formato de reporte
    # ------------------------------------------------------------------

    def format_report(self, report: HarnessReport) -> str:
        """Genera un reporte legible en texto."""
        lines: list[str] = []
        sep = "=" * 72

        lines.append(sep)
        lines.append("GOLDEN CORPUS HARNESS — REPORTE DE EVALUACION")
        lines.append(f"Timestamp: {report.timestamp}")
        lines.append(f"Tiempo total: {report.elapsed_seconds:.1f}s")
        lines.append(sep)

        # Resultados por gold standard
        for gs_name, gs_result in report.results.items():
            lines.append(f"\n--- {gs_name} ({gs_result.text_file}) ---")
            if gs_result.errors:
                for err in gs_result.errors:
                    lines.append(f"  ERROR: {err}")
                continue

            lines.append(f"  {'Capacidad':<22} | {'Precision':>9} | {'Recall':>7} | {'F1':>7}")
            lines.append("  " + "-" * 54)
            for cap_name, score in gs_result.scores.items():
                lines.append(
                    f"  {cap_name:<22} | {score.precision:>8.1f}% | "
                    f"{score.recall:>6.1f}% | {score.f1:>5.1f}%"
                )

        # Metricas agregadas
        lines.append(f"\n{sep}")
        lines.append("METRICAS AGREGADAS (micro-averaged)")
        lines.append(sep)
        lines.append(f"  {'Capacidad':<22} | {'Precision':>9} | {'Recall':>7} | {'F1':>7}")
        lines.append("  " + "-" * 54)
        for cap_name, score in sorted(
            report.aggregate_scores.items(), key=lambda x: x[1].f1, reverse=True
        ):
            lines.append(
                f"  {cap_name:<22} | {score.precision:>8.1f}% | "
                f"{score.recall:>6.1f}% | {score.f1:>5.1f}%"
            )

        lines.append(f"\n  F1 Global: {report.overall_f1 * 100:.1f}%")

        # Regresiones
        if report.regressions:
            lines.append(f"\n{sep}")
            lines.append(f"REGRESIONES DETECTADAS ({len(report.regressions)})")
            lines.append(sep)
            for reg in report.regressions:
                marker = "CRITICA" if reg.is_critical else "WARNING"
                lines.append(
                    f"  [{marker}] {reg.gold_standard}/{reg.capability}: "
                    f"F1 {reg.baseline_f1:.1f}% -> {reg.current_f1:.1f}% "
                    f"({reg.delta:+.1f}pp)"
                )
        else:
            lines.append("\n  Sin regresiones detectadas.")

        # Mejoras
        if report.improvements:
            lines.append(f"\n{sep}")
            lines.append(f"MEJORAS DETECTADAS ({len(report.improvements)})")
            lines.append(sep)
            for imp in report.improvements:
                lines.append(
                    f"  [MEJORA] {imp.gold_standard}/{imp.capability}: "
                    f"F1 {imp.baseline_f1:.1f}% -> {imp.current_f1:.1f}% "
                    f"({imp.delta:+.1f}pp)"
                )

        return "\n".join(lines)


# ============================================================================
# CLI
# ============================================================================


def main():
    """Punto de entrada CLI del harness."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Golden Corpus Harness: evaluacion y deteccion de regresiones"
    )
    parser.add_argument(
        "--gold",
        "-g",
        nargs="*",
        help="Gold standards especificos (default: todos los de desarrollo)",
    )
    parser.add_argument(
        "--capability",
        "-c",
        nargs="*",
        help="Capacidades especificas a evaluar",
    )
    parser.add_argument(
        "--include-advanced",
        action="store_true",
        help="Incluir gold standards avanzados",
    )
    parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=DEFAULT_REGRESSION_THRESHOLD,
        help=f"Umbral de regresion en pp de F1 (default: {DEFAULT_REGRESSION_THRESHOLD})",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Actualizar baseline con los resultados actuales",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Mostrar detalles",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    harness = GoldenCorpusHarness(
        regression_threshold=args.threshold,
        verbose=args.verbose,
    )

    report = harness.run_all(
        gold_standards=args.gold,
        capabilities=args.capability,
        include_advanced=args.include_advanced,
    )

    print(harness.format_report(report))

    if args.update_baseline:
        harness.save_baseline(report)
        print("\nBaseline actualizada.")

    # Exit code: 1 si hay regresiones criticas
    if report.has_critical_regressions:
        sys.exit(2)
    elif report.has_regressions:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
