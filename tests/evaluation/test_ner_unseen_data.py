"""
Evaluación NER en datos NO VISTOS durante desarrollo.

Este test evalúa si los resultados del NER son generalizables
o si hay overfitting a los datos de entrenamiento.
"""

import os
from pathlib import Path

# Setup Java 17 BEFORE imports
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

import logging
import sys
import time
from dataclasses import dataclass, field

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Añadir paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))


@dataclass
class NERTestResult:
    """Resultado de evaluación NER."""

    test_name: str
    method: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    time_seconds: float = 0.0
    detected: list[str] = field(default_factory=list)
    missed: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)

    @property
    def precision(self) -> float:
        if self.true_positives + self.false_positives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_positives)

    @property
    def recall(self) -> float:
        if self.true_positives + self.false_negatives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_negatives)

    @property
    def f1(self) -> float:
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)


def load_unseen_gold_standards():
    """Cargar gold standards de datos no vistos."""
    from gold_standards import UNSEEN_GOLD_STANDARDS

    return UNSEEN_GOLD_STANDARDS


def evaluate_spacy_ner_on_file(text: str, gold_entities: list, test_name: str) -> NERTestResult:
    """Evaluar spaCy NER en un archivo específico."""
    result = NERTestResult(test_name=test_name, method="spacy")

    try:
        from narrative_assistant.nlp.ner import NERExtractor
        from narrative_assistant.nlp.spacy_gpu import load_spacy_model

        start = time.time()
        nlp = load_spacy_model()
        extractor = NERExtractor(nlp)

        # Extraer entidades
        ner_result = extractor.extract_entities(text)
        result.time_seconds = time.time() - start

        # Verificar si fue exitoso
        if ner_result.is_failure:
            logger.warning(f"Error extrayendo entidades: {ner_result.error}")
            return result

        # Normalizar entidades detectadas
        detected = set()
        for ent in ner_result.value.entities:
            detected.add(ent.text.lower().strip())

        # Normalizar gold standard mentions
        gold_mentions = set()
        for e in gold_entities:
            for mention in e.mentions:
                gold_mentions.add(mention.lower().strip())

        result.detected = list(detected)

        # Calcular métricas
        tp = detected & gold_mentions
        fp = detected - gold_mentions
        fn = gold_mentions - detected

        result.true_positives = len(tp)
        result.false_positives = len(fp)
        result.false_negatives = len(fn)
        result.missed = list(fn)
        result.extra = list(fp)

    except Exception as e:
        logger.warning(f"Error en spaCy NER para {test_name}: {e}")
        import traceback

        traceback.print_exc()

    return result


def run_unseen_data_evaluation():
    """Ejecutar evaluación NER en datos no vistos."""
    print("=" * 80)
    print("EVALUACIÓN NER EN DATOS NO VISTOS (VALIDACIÓN CONTRA OVERFITTING)")
    print("=" * 80)
    print()
    print("Estos archivos NUNCA fueron usados durante el desarrollo del NER.")
    print("Si los resultados son significativamente peores que en los datos de")
    print("desarrollo, indica overfitting.")
    print()

    # Cargar gold standards
    unseen_standards = load_unseen_gold_standards()

    results = []

    for name, gold in unseen_standards.items():
        print("-" * 80)
        print(f"TEST: {name.upper()}")
        print(f"Archivo: {gold.text_file}")
        print("-" * 80)

        # Cargar texto
        test_file = Path(__file__).parent.parent.parent / gold.text_file
        if not test_file.exists():
            print(f"  ERROR: Archivo no encontrado: {test_file}")
            continue

        text = test_file.read_text(encoding="utf-8")

        # Filtrar solo la parte narrativa (antes de GOLD STANDARD)
        if "GOLD STANDARD" in text:
            text = text.split("GOLD STANDARD")[0]

        print(f"  Entidades esperadas: {len(gold.entities)}")
        total_mentions = sum(len(e.mentions) for e in gold.entities)
        print(f"  Menciones totales: {total_mentions}")

        # Evaluar
        r = evaluate_spacy_ner_on_file(text, gold.entities, name)
        results.append(r)

        print("\n  Resultados:")
        print(f"    Precision: {r.precision:.1%}")
        print(f"    Recall:    {r.recall:.1%}")
        print(f"    F1:        {r.f1:.1%}")
        print(f"    Time:      {r.time_seconds:.2f}s")
        print(f"    TP={r.true_positives}, FP={r.false_positives}, FN={r.false_negatives}")

        if r.missed:
            print(f"\n  Missed ({len(r.missed)}):")
            for m in sorted(r.missed)[:15]:
                print(f"    - {m}")

        if r.extra:
            print(f"\n  Extra (false positives) ({len(r.extra)}):")
            for e in sorted(r.extra)[:15]:
                print(f"    - {e}")
        print()

    # Resumen
    print("=" * 80)
    print("RESUMEN - DATOS NO VISTOS")
    print("=" * 80)
    print(f"{'Test':<25} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Time':>10}")
    print("-" * 65)

    total_tp, total_fp, total_fn = 0, 0, 0
    for r in results:
        print(
            f"{r.test_name:<25} {r.precision:>10.1%} {r.recall:>10.1%} {r.f1:>10.1%} {r.time_seconds:>9.2f}s"
        )
        total_tp += r.true_positives
        total_fp += r.false_positives
        total_fn += r.false_negatives

    print("-" * 65)

    # Métricas agregadas
    if total_tp + total_fp > 0:
        total_p = total_tp / (total_tp + total_fp)
    else:
        total_p = 0

    if total_tp + total_fn > 0:
        total_r = total_tp / (total_tp + total_fn)
    else:
        total_r = 0

    if total_p + total_r > 0:
        total_f1 = 2 * total_p * total_r / (total_p + total_r)
    else:
        total_f1 = 0

    print(f"{'TOTAL (agregado)':<25} {total_p:>10.1%} {total_r:>10.1%} {total_f1:>10.1%}")

    print()
    print("=" * 80)
    print("INTERPRETACIÓN")
    print("=" * 80)
    print()
    print("Comparar estos resultados con los obtenidos en datos de desarrollo:")
    print("  - Si F1 en datos NO VISTOS es similar (±5%): NO hay overfitting")
    print("  - Si F1 en datos NO VISTOS es mucho menor (>10%): HAY overfitting")
    print()
    print("Resultados previos en datos de desarrollo: P=100%, R=100%, F1=100%")
    print(
        f"Resultados en datos NO VISTOS:            P={total_p:.1%}, R={total_r:.1%}, F1={total_f1:.1%}"
    )
    print()

    diff = 100.0 - (total_f1 * 100)
    if diff <= 5:
        print("[OK] CONCLUSION: Los resultados son GENERALIZABLES (diferencia <=5%)")
    elif diff <= 10:
        print("[WARN] CONCLUSION: Posible LEVE overfitting (diferencia 5-10%)")
    else:
        print("[FAIL] CONCLUSION: HAY OVERFITTING significativo (diferencia >10%)")

    return results


if __name__ == "__main__":
    run_unseen_data_evaluation()
