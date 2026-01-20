#!/usr/bin/env python
"""
Benchmark del pipeline de análisis para medir tiempos por fase.
Útil para ajustar estimaciones de progreso.
"""

import time
import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from narrative_assistant.parsers.base import detect_format, get_parser
from narrative_assistant.parsers.structure_detector import StructureDetector
from narrative_assistant.nlp.ner import NERExtractor
from narrative_assistant.nlp.attributes import AttributeExtractor


def benchmark_file(file_path: Path) -> dict:
    """Ejecuta benchmark de un archivo y retorna tiempos por fase."""

    print(f"\n{'='*60}")
    print(f"Archivo: {file_path.name}")
    print(f"{'='*60}")

    results = {
        "file": file_path.name,
        "word_count": 0,
        "phases": {}
    }

    # FASE 1: Parsing
    print("\n[1/4] Parsing...")
    start = time.time()
    doc_format = detect_format(file_path)
    parser = get_parser(doc_format)
    parse_result = parser.parse(file_path)

    if parse_result.is_failure:
        print(f"  ERROR: {parse_result.error}")
        return results

    raw_document = parse_result.value
    full_text = raw_document.full_text
    word_count = len(full_text.split())
    results["word_count"] = word_count
    results["phases"]["parsing"] = round(time.time() - start, 2)
    print(f"  Tiempo: {results['phases']['parsing']}s | {word_count} palabras")

    # FASE 2: Estructura
    print("\n[2/4] Detección de estructura...")
    start = time.time()
    detector = StructureDetector()
    structure_result = detector.detect(raw_document)
    chapters_count = 0
    if structure_result.is_success and hasattr(structure_result.value, 'chapters'):
        chapters_count = len(structure_result.value.chapters) if structure_result.value.chapters else 1
    results["phases"]["structure"] = round(time.time() - start, 2)
    results["chapters"] = chapters_count
    print(f"  Tiempo: {results['phases']['structure']}s | {chapters_count} capítulos")

    # FASE 3: NER (con LLM)
    print("\n[3/4] NER (con LLM preprocesador)...")
    start = time.time()
    ner_extractor = NERExtractor(use_llm_preprocessing=True)
    ner_result = ner_extractor.extract_entities(full_text)
    entities_count = 0
    if ner_result.is_success and ner_result.value:
        entities_count = len(ner_result.value.entities)
    results["phases"]["ner"] = round(time.time() - start, 2)
    results["entities"] = entities_count
    print(f"  Tiempo: {results['phases']['ner']}s | {entities_count} entidades")

    # FASE 4: Atributos
    print("\n[4/4] Extracción de atributos...")
    start = time.time()
    if ner_result.is_success and ner_result.value:
        attr_extractor = AttributeExtractor()
        # Preparar menciones
        entity_mentions = []
        for ent in ner_result.value.entities[:20]:  # Limitar para benchmark
            entity_mentions.append((ent.text, ent.start_char, ent.end_char))

        if entity_mentions:
            attr_result = attr_extractor.extract_attributes(
                text=full_text[:10000],  # Limitar texto para benchmark
                entity_mentions=entity_mentions,
                chapter_id=None,
            )
            if attr_result.is_success and attr_result.value:
                results["attributes"] = len(attr_result.value.attributes)

    results["phases"]["attributes"] = round(time.time() - start, 2)
    print(f"  Tiempo: {results['phases']['attributes']}s | {results.get('attributes', 0)} atributos")

    # Resumen
    total = sum(results["phases"].values())
    results["total"] = round(total, 2)

    print(f"\n--- RESUMEN ---")
    print(f"Total: {total:.1f}s para {word_count} palabras")
    print(f"Velocidad: {word_count/total:.0f} palabras/segundo")

    for phase, duration in results["phases"].items():
        pct = (duration / total * 100) if total > 0 else 0
        print(f"  {phase}: {duration}s ({pct:.0f}%)")

    return results


def main():
    test_files = [
        Path("test_books/test_simple.txt"),          # ~30 palabras
        Path("test_books/test_document.txt"),        # ~100 palabras
        Path("test_books/test_document_fresh.txt"),  # ~300 palabras
        Path("test_books/la_regenta_sample.docx"),   # ~10k palabras
    ]

    base_path = Path(__file__).parent.parent

    all_results = []

    for file_path in test_files:
        full_path = base_path / file_path
        if full_path.exists():
            result = benchmark_file(full_path)
            all_results.append(result)
        else:
            print(f"\nArchivo no encontrado: {file_path}")

    # Tabla resumen final
    print(f"\n\n{'='*80}")
    print("RESUMEN FINAL - Tiempos por fase (segundos)")
    print(f"{'='*80}")
    print(f"{'Archivo':<30} {'Palabras':>10} {'Parsing':>8} {'Struct':>8} {'NER':>8} {'Attrs':>8} {'TOTAL':>8}")
    print("-" * 80)

    for r in all_results:
        if r["word_count"] > 0:
            print(f"{r['file']:<30} {r['word_count']:>10} "
                  f"{r['phases'].get('parsing', 0):>8.1f} "
                  f"{r['phases'].get('structure', 0):>8.1f} "
                  f"{r['phases'].get('ner', 0):>8.1f} "
                  f"{r['phases'].get('attributes', 0):>8.1f} "
                  f"{r.get('total', 0):>8.1f}")

    print(f"\n{'='*80}")
    print("PORCENTAJES PROMEDIO POR FASE")
    print(f"{'='*80}")

    # Calcular promedios
    if all_results:
        avg_pcts = {}
        count = 0
        for r in all_results:
            if r.get("total", 0) > 0:
                count += 1
                for phase, duration in r["phases"].items():
                    pct = duration / r["total"] * 100
                    avg_pcts[phase] = avg_pcts.get(phase, 0) + pct

        if count > 0:
            for phase in ["parsing", "structure", "ner", "attributes"]:
                avg = avg_pcts.get(phase, 0) / count
                print(f"  {phase}: {avg:.1f}%")


if __name__ == "__main__":
    main()
