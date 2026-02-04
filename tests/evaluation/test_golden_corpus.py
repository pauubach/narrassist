"""
Tests de regresion contra golden corpus.

Usa el GoldenCorpusHarness para evaluar cada capacidad NLP contra gold standards
y verificar que no hay regresiones respecto a la baseline guardada.

Uso:
    # Todos los tests
    pytest tests/evaluation/test_golden_corpus.py -v

    # Solo NER
    pytest tests/evaluation/test_golden_corpus.py -v -k ner

    # Solo un gold standard
    pytest tests/evaluation/test_golden_corpus.py -v -k inconsistencias

    # Actualizar baseline despues de mejoras confirmadas
    python tests/evaluation/golden_corpus_harness.py --update-baseline
"""

import logging
import os
import sys
from pathlib import Path

import pytest

# Setup Java 17 BEFORE imports (requerido por LanguageTool)
java17_paths = [
    r"C:\Program Files\Microsoft\jdk-17.0.17.10-hotspot",
    r"C:\Program Files\Eclipse Adoptium\jdk-17",
    r"C:\Program Files\Java\jdk-17",
]
for java_path in java17_paths:
    if Path(java_path).exists():
        os.environ["JAVA_HOME"] = java_path
        bin_path = f"{java_path}\\bin" if os.name == "nt" else f"{java_path}/bin"
        os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")
        break

# Paths del proyecto
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from golden_corpus_harness import DEFAULT_REGRESSION_THRESHOLD, GoldenCorpusHarness

logger = logging.getLogger(__name__)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def harness():
    """Harness compartido por todos los tests del modulo."""
    return GoldenCorpusHarness(
        regression_threshold=DEFAULT_REGRESSION_THRESHOLD,
        verbose=False,
    )


# ============================================================================
# Mapeo: gold_standard -> capacidades aplicables
# ============================================================================

# Cada gold standard solo se evalua con las capacidades para las que tiene datos
GOLD_CAPABILITIES = {
    "inconsistencias": ["ner", "fusion", "attributes", "inconsistencies"],
    "gramatica": ["ner", "fusion", "grammar"],
    "relaciones": ["ner", "relations"],
    "timeline": ["ner", "chapters", "relations", "timeline"],
    "capitulos": ["ner", "chapters", "relations"],
    "narrativa_pura": ["ner", "chapters", "relations"],
    "ortografia": ["ner", "chapters", "orthography"],
}


def _build_test_params():
    """Genera parametros (gold_standard, capability) para parametrize."""
    params = []
    for gs_name, caps in GOLD_CAPABILITIES.items():
        for cap in caps:
            params.append(pytest.param(gs_name, cap, id=f"{gs_name}/{cap}"))
    return params


# ============================================================================
# Tests parametrizados: no-regresion por capacidad
# ============================================================================


@pytest.mark.evaluation
class TestGoldenCorpusRegression:
    """Verifica que no hay regresiones vs baseline para cada (gold_standard, capacidad)."""

    @pytest.mark.parametrize("gold_standard,capability", _build_test_params())
    def test_no_regression(self, harness, gold_standard, capability):
        """Evalua {gold_standard}/{capability} y compara con baseline."""
        baseline_f1 = harness.get_baseline_f1(gold_standard, capability)

        # Si no hay baseline, el test pasa (primera ejecucion)
        if baseline_f1 is None:
            pytest.skip(f"Sin baseline para {gold_standard}/{capability}")

        result = harness.evaluate_gold_standard(gold_standard, capabilities=[capability])
        assert not result.errors, f"Errores en evaluacion: {result.errors}"

        if capability not in result.scores:
            pytest.skip(f"Capacidad {capability} no evaluada para {gold_standard}")

        current_f1 = result.scores[capability].f1
        delta = current_f1 - baseline_f1
        threshold = harness.regression_threshold

        assert delta >= -threshold, (
            f"REGRESION en {gold_standard}/{capability}: "
            f"F1 {baseline_f1:.1f}% -> {current_f1:.1f}% "
            f"(delta={delta:+.1f}pp, umbral={threshold}pp)"
        )


# ============================================================================
# Tests de sanidad: metricas minimas
# ============================================================================

# Umbrales minimos de F1 que cada capacidad debe superar (sanity check)
MINIMUM_F1 = {
    "ner": 30.0,
    "chapters": 50.0,
    "fusion": 80.0,
    "grammar": 50.0,
    "relations": 40.0,
    "timeline": 40.0,
}


@pytest.mark.evaluation
class TestMinimumQuality:
    """Verifica que las capacidades principales superan umbrales minimos."""

    @pytest.mark.parametrize(
        "capability,min_f1",
        [pytest.param(cap, f1, id=cap) for cap, f1 in MINIMUM_F1.items()],
    )
    def test_minimum_f1(self, harness, capability, min_f1):
        """Verifica que el F1 agregado de {capability} supera {min_f1}%."""
        # Evaluar todos los gold standards que tienen esta capacidad
        relevant = [gs for gs, caps in GOLD_CAPABILITIES.items() if capability in caps]
        if not relevant:
            pytest.skip(f"No hay gold standards para {capability}")

        results = {}
        for gs_name in relevant:
            try:
                results[gs_name] = harness.evaluate_gold_standard(
                    gs_name, capabilities=[capability]
                )
            except Exception as e:
                logger.warning("Error evaluando %s/%s: %s", gs_name, capability, e)

        aggregate = harness.compute_aggregate(results)

        if capability not in aggregate:
            # La capacidad puede no haberse evaluado (sub-tipos como grammar_dequeismo)
            # Buscar sub-capacidades (grammar -> grammar_dequeismo, grammar_queismo, etc.)
            sub_caps = [k for k in aggregate if k.startswith(capability)]
            if not sub_caps:
                pytest.skip(f"Capacidad {capability} no produjo resultados")
            # Promedio de sub-capacidades
            avg_f1 = sum(aggregate[sc].f1 for sc in sub_caps) / len(sub_caps)
        else:
            avg_f1 = aggregate[capability].f1

        assert avg_f1 >= min_f1, (
            f"F1 agregado de {capability} ({avg_f1:.1f}%) por debajo del minimo ({min_f1:.1f}%)"
        )


# ============================================================================
# Test completo: reporte
# ============================================================================


@pytest.mark.evaluation
@pytest.mark.slow
class TestFullHarnessReport:
    """Ejecuta el harness completo y verifica el reporte."""

    def test_full_report_no_critical_regressions(self, harness):
        """Ejecuta evaluacion completa y verifica que no hay regresiones criticas."""
        report = harness.run_all(save_history=False)

        # Imprimir reporte para visibilidad
        print(harness.format_report(report))

        # No debe haber regresiones criticas (F1=0 o caida >20pp)
        assert not report.has_critical_regressions, (
            "Regresiones criticas detectadas: "
            + "; ".join(
                f"{r.gold_standard}/{r.capability}: {r.baseline_f1:.1f}% -> {r.current_f1:.1f}%"
                for r in report.regressions
                if r.is_critical
            )
        )
