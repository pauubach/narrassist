"""
Test de capacidades NLP: NER, Relaciones, Timeline.

Evalúa cada tecnología disponible para:
- NER (Reconocimiento de Entidades Nombradas)
- Extracción de Relaciones
- Detección de Eventos Temporales
- Detección de Atributos de Personajes
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

    method: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    time_seconds: float = 0.0
    detected: list[str] = field(default_factory=list)
    missed: list[str] = field(default_factory=list)

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


def load_ner_gold_standard():
    """Cargar gold standard para NER."""
    from gold_standards import GOLD_INCONSISTENCIAS_PERSONAJES

    gold = GOLD_INCONSISTENCIAS_PERSONAJES
    entities = {}
    for e in gold.entities:
        entities[e.name.lower()] = {
            "type": e.entity_type,
            "mentions": [m.lower() for m in e.mentions],
        }
    return entities


def evaluate_spacy_ner(text: str, gold_entities: dict) -> NERTestResult:
    """Evaluar spaCy NER."""
    result = NERTestResult(method="spacy")

    try:
        from narrative_assistant.nlp.spacy_gpu import load_spacy_model

        start = time.time()
        nlp = load_spacy_model()
        doc = nlp(text)
        result.time_seconds = time.time() - start

        # Extraer entidades
        detected = set()
        for ent in doc.ents:
            if ent.label_ in ["PER", "PERSON", "LOC", "GPE", "ORG"]:
                detected.add(ent.text.lower())

        # Calcular métricas
        gold_mentions = set()
        for e_data in gold_entities.values():
            gold_mentions.update(e_data["mentions"])

        result.detected = list(detected)
        tp = detected & gold_mentions
        fp = detected - gold_mentions
        fn = gold_mentions - detected

        result.true_positives = len(tp)
        result.false_positives = len(fp)
        result.false_negatives = len(fn)
        result.missed = list(fn)[:10]

    except Exception as e:
        logger.warning(f"Error en spaCy NER: {e}")

    return result


def evaluate_transformers_ner(text: str, gold_entities: dict) -> NERTestResult:
    """Evaluar NER con transformers (BETO NER)."""
    result = NERTestResult(method="transformers_ner")

    try:
        from transformers import pipeline

        start = time.time()

        # Usar modelo BETO NER
        ner_pipeline = pipeline(
            "ner",
            model="mrm8488/bert-spanish-cased-finetuned-ner",
            aggregation_strategy="simple",
            device=-1,
        )

        entities = ner_pipeline(text[:5000])  # Limitar por velocidad
        result.time_seconds = time.time() - start

        # Extraer entidades
        detected = set()
        for ent in entities:
            if ent["entity_group"] in ["PER", "LOC", "ORG"]:
                detected.add(ent["word"].lower().strip())

        # Calcular métricas
        gold_mentions = set()
        for e_data in gold_entities.values():
            gold_mentions.update(e_data["mentions"])

        result.detected = list(detected)
        tp = detected & gold_mentions
        fp = detected - gold_mentions
        fn = gold_mentions - detected

        result.true_positives = len(tp)
        result.false_positives = len(fp)
        result.false_negatives = len(fn)
        result.missed = list(fn)[:10]

    except Exception as e:
        logger.warning(f"Error en transformers NER: {e}")

    return result


def run_ner_evaluation():
    """Ejecutar evaluación NER."""
    print("=" * 70)
    print("EVALUACIÓN NER")
    print("=" * 70)

    # Cargar datos
    test_file = (
        Path(__file__).parent.parent.parent
        / "test_books"
        / "evaluation_tests"
        / "prueba_inconsistencias_personajes.txt"
    )

    if not test_file.exists():
        print(f"Archivo no encontrado: {test_file}")
        return

    text = test_file.read_text(encoding="utf-8")
    gold_entities = load_ner_gold_standard()

    print(f"\n{len(gold_entities)} entidades en gold standard")
    for name, data in gold_entities.items():
        print(f"  - {name} ({data['type']}): {data['mentions'][:3]}...")

    results = []

    # spaCy
    print("\n" + "-" * 70)
    print("1. spaCy NER (es_core_news_lg)")
    print("-" * 70)
    r = evaluate_spacy_ner(text, gold_entities)
    results.append(r)
    print(f"  Precision: {r.precision:.1%}")
    print(f"  Recall:    {r.recall:.1%}")
    print(f"  F1:        {r.f1:.1%}")
    print(f"  Time:      {r.time_seconds:.2f}s")
    print(f"  Detected:  {', '.join(str(x) for x in r.detected[:10])}")
    print(f"  Missed:    {', '.join(str(x) for x in r.missed)}")

    # Transformers
    print("\n" + "-" * 70)
    print("2. Transformers NER (BETO)")
    print("-" * 70)
    r = evaluate_transformers_ner(text, gold_entities)
    results.append(r)
    print(f"  Precision: {r.precision:.1%}")
    print(f"  Recall:    {r.recall:.1%}")
    print(f"  F1:        {r.f1:.1%}")
    print(f"  Time:      {r.time_seconds:.2f}s")
    print(f"  Detected:  {', '.join(str(x) for x in r.detected[:10])}")
    print(f"  Missed:    {', '.join(str(x) for x in r.missed)}")

    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN NER")
    print("=" * 70)
    print(f"{'Method':<25} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Time':>10}")
    print("-" * 65)
    for r in results:
        print(
            f"{r.method:<25} {r.precision:>10.1%} {r.recall:>10.1%} {r.f1:>10.1%} {r.time_seconds:>9.2f}s"
        )

    return results


if __name__ == "__main__":
    run_ner_evaluation()
