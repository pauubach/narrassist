"""
Ejecuta tests pesados (que cargan spaCy) uno a uno por archivo.

Evita cargar todos en memoria a la vez, previniendo crasheos en
equipos con poca RAM (Xeon E3 + Quadro M3000M).

Uso:
    python scripts/run_heavy_tests.py              # Todos los pesados
    python scripts/run_heavy_tests.py adversarial   # Solo adversarial
    python scripts/run_heavy_tests.py --list        # Listar sin ejecutar
"""

import subprocess
import sys
import os
from pathlib import Path

# Archivos heavy organizados por prioridad (menos RAM primero)
HEAVY_TEST_FILES = {
    "unit": [
        "tests/unit/test_attributes.py",
        "tests/unit/test_ner.py",
        "tests/unit/test_cesp_linguistic.py",
        "tests/unit/test_spanish_rules.py",
    ],
    "regression": [
        "tests/regression/test_ojos_verdes_bug.py",
    ],
    "integration": [
        "tests/integration/test_cesp_pipeline.py",
    ],
    "adversarial": [
        "tests/adversarial/test_attribute_adversarial.py",
        "tests/adversarial/test_ner_adversarial.py",
        "tests/adversarial/test_entity_fusion_adversarial.py",
        "tests/adversarial/test_generalization.py",
        "tests/adversarial/test_emotional_coherence_adversarial.py",
        "tests/adversarial/test_pipeline_breaking.py",
        "tests/adversarial/test_analysis_functional.py",
        "tests/adversarial/test_linguistic_edge_cases.py",
        "tests/adversarial/test_syntactic_attribution_cases.py",
        "tests/adversarial/test_semantic_pragmatic_attribution_cases.py",
        "tests/adversarial/test_cross_entity_attribute_adversarial.py",
        "tests/adversarial/test_pipeline_e2e_adversarial.py",
        "tests/adversarial/test_comprehensive_manuscripts.py",
        "tests/adversarial/test_full_pipeline_e2e.py",
        "tests/adversarial/test_multimethod_evaluation.py",
        "tests/adversarial/test_method_evaluation.py",
    ],
    "evaluation": [
        "tests/evaluation/test_nlp_capabilities.py",
        "tests/evaluation/test_ner_unseen_data.py",
    ],
}


def list_files(category=None):
    """Lista archivos de test pesados."""
    for cat, files in HEAVY_TEST_FILES.items():
        if category and cat != category:
            continue
        print(f"\n  [{cat}]")
        for f in files:
            exists = "OK" if Path(f).exists() else "MISSING"
            print(f"    {exists}  {f}")


def run_one(test_file: str, verbose: bool = True) -> tuple[int, int, int]:
    """
    Ejecuta un archivo de test en un subproceso aislado.

    Returns:
        (passed, failed, xfailed)
    """
    if not Path(test_file).exists():
        print(f"  SKIP  {test_file} (no existe)")
        return (0, 0, 0)

    cmd = [
        sys.executable, "-m", "pytest",
        test_file,
        "-m", "",  # Override el -m "not heavy" del pytest.ini
        "--tb=line",
        "-q",
        "--no-header",
    ]

    if verbose:
        print(f"\n  RUN   {test_file}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min max por archivo
            cwd=str(Path(__file__).parent.parent),
        )

        # Parsear resultado
        output = result.stdout + result.stderr
        last_line = ""
        for line in output.strip().split("\n"):
            if "passed" in line or "failed" in line or "error" in line:
                last_line = line.strip()

        passed = failed = xfailed = 0
        import re
        m = re.search(r"(\d+) passed", last_line)
        if m:
            passed = int(m.group(1))
        m = re.search(r"(\d+) failed", last_line)
        if m:
            failed = int(m.group(1))
        m = re.search(r"(\d+) xfailed", last_line)
        if m:
            xfailed = int(m.group(1))

        status = "PASS" if result.returncode == 0 else "FAIL"
        print(f"  {status}  {test_file}: {passed} passed, {failed} failed, {xfailed} xfailed")

        if failed > 0 and verbose:
            # Mostrar líneas de failure
            for line in output.split("\n"):
                if "FAILED" in line or "ERROR" in line:
                    print(f"        {line.strip()}")

        return (passed, failed, xfailed)

    except subprocess.TimeoutExpired:
        print(f"  TIME  {test_file}: timeout (>5 min)")
        return (0, 0, 0)
    except Exception as e:
        print(f"  ERR   {test_file}: {e}")
        return (0, 0, 0)


def main():
    args = sys.argv[1:]

    if "--list" in args:
        category = next((a for a in args if a != "--list"), None)
        list_files(category)
        return

    category = args[0] if args else None

    print("=" * 60)
    print("  Heavy Test Runner (un archivo a la vez)")
    print("=" * 60)

    total_passed = total_failed = total_xfailed = 0

    for cat, files in HEAVY_TEST_FILES.items():
        if category and cat != category:
            continue

        print(f"\n{'─' * 60}")
        print(f"  Categoría: {cat} ({len(files)} archivos)")
        print(f"{'─' * 60}")

        for test_file in files:
            p, f, x = run_one(test_file)
            total_passed += p
            total_failed += f
            total_xfailed += x

    print(f"\n{'=' * 60}")
    print(f"  TOTAL: {total_passed} passed, {total_failed} failed, {total_xfailed} xfailed")
    print(f"{'=' * 60}")

    sys.exit(1 if total_failed > 0 else 0)


if __name__ == "__main__":
    main()
