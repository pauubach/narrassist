#!/usr/bin/env python
"""
Script de evaluación de NER para medir métricas en diferentes configuraciones.

Ejecutar:
    python scripts/evaluate_ner_metrics.py

Genera un resumen con precisión, recall estimado y tiempos por documento.
"""

import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.narrative_assistant.parsers.docx_parser import DocxParser
from src.narrative_assistant.nlp.ner import NERExtractor


@dataclass
class EvalResult:
    """Resultado de evaluación."""
    doc_name: str
    words: int
    total_entities: int
    per: int
    loc: int
    org: int
    misc: int
    time_seconds: float
    sources: dict
    sample_per: list
    sample_loc: list
    config: str
    errors: list


def evaluate_document(
    path: Path,
    use_llm: bool = False,
    max_words: int = 10000,
    config_name: str = "default"
) -> EvalResult:
    """Evalúa NER en un documento."""
    errors = []

    # Parse document
    parser = DocxParser()
    parse_result = parser.parse(path)

    if parse_result.is_failure:
        return EvalResult(
            doc_name=path.name,
            words=0, total_entities=0, per=0, loc=0, org=0, misc=0,
            time_seconds=0, sources={}, sample_per=[], sample_loc=[],
            config=config_name, errors=[f"Parse error: {parse_result.error}"]
        )

    doc = parse_result.value
    text = doc.full_text
    words = len(text.split())

    # Truncar si es muy largo (para velocidad)
    if words > max_words:
        # Tomar primeros N caracteres aproximados
        chars_estimate = int(max_words * 6)  # ~6 chars per word
        text = text[:chars_estimate]
        words = len(text.split())
        errors.append(f"Truncado a {words} palabras")

    # NER extraction
    extractor = NERExtractor(use_llm_preprocessing=use_llm)

    start = time.time()
    result = extractor.extract_entities(text)
    elapsed = time.time() - start

    if result.is_failure:
        return EvalResult(
            doc_name=path.name,
            words=words, total_entities=0, per=0, loc=0, org=0, misc=0,
            time_seconds=elapsed, sources={}, sample_per=[], sample_loc=[],
            config=config_name, errors=[f"NER error: {result.error}"]
        )

    entities = result.value.entities

    # Contar por tipo
    per = sum(1 for e in entities if e.label.value == 'PER')
    loc = sum(1 for e in entities if e.label.value == 'LOC')
    org = sum(1 for e in entities if e.label.value == 'ORG')
    misc = len(entities) - per - loc - org

    # Fuentes
    sources = {}
    for e in entities:
        sources[e.source] = sources.get(e.source, 0) + 1

    # Muestras
    sample_per = [e.text for e in entities if e.label.value == 'PER'][:8]
    sample_loc = [e.text for e in entities if e.label.value == 'LOC'][:8]

    return EvalResult(
        doc_name=path.name,
        words=words,
        total_entities=len(entities),
        per=per, loc=loc, org=org, misc=misc,
        time_seconds=elapsed,
        sources=sources,
        sample_per=sample_per,
        sample_loc=sample_loc,
        config=config_name,
        errors=errors
    )


def print_result(r: EvalResult, iteration: int):
    """Imprime resultado de forma legible."""
    print(f"\n{'='*70}")
    print(f"ITERACIÓN {iteration} | {r.doc_name} | Config: {r.config}")
    print(f"{'='*70}")
    print(f"Palabras: {r.words:,} | Tiempo: {r.time_seconds:.1f}s")

    if r.errors:
        print(f"WARN: Errores: {', '.join(r.errors)}")

    if r.total_entities == 0:
        print("ERROR: No se extrajeron entidades")
        return

    print(f"\nTotal entidades: {r.total_entities}")
    print(f"  PER:  {r.per:3d} ({100*r.per/r.total_entities:5.1f}%)")
    print(f"  LOC:  {r.loc:3d} ({100*r.loc/r.total_entities:5.1f}%)")
    print(f"  ORG:  {r.org:3d} ({100*r.org/r.total_entities:5.1f}%)")
    print(f"  MISC: {r.misc:3d} ({100*r.misc/r.total_entities:5.1f}%)")

    print(f"\nFuentes: {r.sources}")
    print(f"\nEjemplos PER: {r.sample_per}")
    print(f"Ejemplos LOC: {r.sample_loc}")


def print_summary_table(all_results: list[list[EvalResult]]):
    """Imprime tabla resumen de todas las iteraciones."""
    print("\n" + "="*90)
    print("RESUMEN DE TODAS LAS ITERACIONES")
    print("="*90)

    # Header
    print(f"\n{'Iter':<5} {'Documento':<30} {'Config':<15} {'Ent':>5} {'PER%':>6} {'LOC%':>6} {'Time':>8}")
    print("-"*90)

    for iteration, results in enumerate(all_results, 1):
        for r in results:
            per_pct = f"{100*r.per/r.total_entities:.1f}" if r.total_entities > 0 else "N/A"
            loc_pct = f"{100*r.loc/r.total_entities:.1f}" if r.total_entities > 0 else "N/A"
            time_str = f"{r.time_seconds:.1f}s"
            print(f"{iteration:<5} {r.doc_name[:30]:<30} {r.config:<15} {r.total_entities:>5} {per_pct:>6} {loc_pct:>6} {time_str:>8}")
        print("-"*90)


def main():
    """Ejecuta evaluación completa."""
    docs = [
        Path("d:/repos/tfm/test_books/la_regenta_sample.docx"),
        Path("d:/repos/tfm/test_books/diario POLIDORI.docx"),
        Path("d:/repos/tfm/test_books/Un mundo apasionado_para Anna Ubach.docx"),
    ]

    # Filtrar solo los que existen
    docs = [d for d in docs if d.exists()]
    print(f"Documentos a evaluar: {[d.name for d in docs]}")

    all_results = []

    # ========================================
    # ITERACIÓN 1: Solo spaCy (sin LLM)
    # ========================================
    print("\n" + "#"*70)
    print("# ITERACIÓN 1: spaCy only (sin LLM)")
    print("#"*70)

    iteration_results = []
    for doc_path in docs:
        result = evaluate_document(
            doc_path,
            use_llm=False,
            max_words=10000,
            config_name="spacy_only"
        )
        print_result(result, 1)
        iteration_results.append(result)

    all_results.append(iteration_results)

    # ========================================
    # ITERACIÓN 2: spaCy + LLM
    # ========================================
    print("\n" + "#"*70)
    print("# ITERACIÓN 2: spaCy + LLM (llama3.2)")
    print("#"*70)

    iteration_results = []
    for doc_path in docs:
        result = evaluate_document(
            doc_path,
            use_llm=True,
            max_words=5000,  # Menos palabras con LLM por velocidad
            config_name="spacy+llm"
        )
        print_result(result, 2)
        iteration_results.append(result)

    all_results.append(iteration_results)

    # Resumen final
    print_summary_table(all_results)


if __name__ == "__main__":
    main()
