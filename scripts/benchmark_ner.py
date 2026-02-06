"""
Benchmark NER contra corpus test_books/.

Evalúa las capacidades del NER multi-método usando libros reales del corpus.
Compara: spaCy-only, Transformer-only, multi-método (votación).

Métricas:
- Entidades detectadas por tipo (PER/LOC/ORG/MISC)
- Acuerdo inter-método (Cohen's kappa proxy)
- Distribución de confianza
- Cobertura: qué porcentaje del texto tiene entidades

Uso:
    python scripts/benchmark_ner.py                    # Benchmark rápido (5 libros)
    python scripts/benchmark_ner.py --full             # Todos los libros
    python scripts/benchmark_ner.py --category ficcion # Solo ficción
    python scripts/benchmark_ner.py --output report.json
"""

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class MethodResult:
    """Resultado de un método NER para un documento."""

    method: str
    entity_count: int = 0
    per_count: int = 0
    loc_count: int = 0
    org_count: int = 0
    misc_count: int = 0
    avg_confidence: float = 0.0
    unique_entities: int = 0
    elapsed_ms: float = 0.0
    entities: list[dict] = field(default_factory=list)


@dataclass
class DocumentResult:
    """Resultado del benchmark para un documento."""

    filename: str
    category: str
    text_length: int = 0
    chunk_tested: int = 0  # Chars used for NER (max 5000)
    methods: dict[str, MethodResult] = field(default_factory=dict)
    inter_method_agreement: float = 0.0


@dataclass
class BenchmarkReport:
    """Reporte completo del benchmark NER."""

    timestamp: str = ""
    total_documents: int = 0
    documents: list[DocumentResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


# ============================================================================
# Parsing helpers
# ============================================================================


def parse_epub_text(epub_path: Path, max_chars: int = 5000) -> str:
    """Extrae texto de un EPUB (primeros max_chars chars narrativos)."""
    try:
        from narrative_assistant.parsers.epub_parser import EPUBParser

        parser = EPUBParser()
        result = parser.parse(epub_path)
        if result.is_failure:
            return ""
        doc = result.value
        text = doc.content[:max_chars] if doc.content else ""
        return text
    except Exception:
        pass

    # Fallback: leer directamente
    try:
        import zipfile

        with zipfile.ZipFile(epub_path) as z:
            text_parts = []
            for name in z.namelist():
                if name.endswith((".xhtml", ".html", ".htm")):
                    raw = z.read(name).decode("utf-8", errors="ignore")
                    # Strip HTML tags
                    clean = re.sub(r"<[^>]+>", " ", raw)
                    clean = re.sub(r"\s+", " ", clean).strip()
                    text_parts.append(clean)
            full_text = " ".join(text_parts)
            return full_text[:max_chars]
    except Exception:
        return ""


def parse_txt_text(txt_path: Path, max_chars: int = 5000) -> str:
    """Lee texto plano."""
    try:
        return txt_path.read_text(encoding="utf-8")[:max_chars]
    except Exception:
        return ""


def get_text(file_path: Path, max_chars: int = 5000) -> str:
    """Obtiene texto de cualquier formato soportado."""
    suffix = file_path.suffix.lower()
    if suffix == ".epub":
        return parse_epub_text(file_path, max_chars)
    elif suffix in (".txt", ".md"):
        return parse_txt_text(file_path, max_chars)
    return ""


# ============================================================================
# NER Methods
# ============================================================================


def run_spacy_ner(text: str) -> MethodResult:
    """Ejecuta NER solo con spaCy."""
    result = MethodResult(method="spacy")
    t0 = time.time()

    try:
        from narrative_assistant.nlp.ner import NERExtractor

        extractor = NERExtractor(
            use_llm_preprocessing=False,
            use_transformer_ner=False,
        )
        ner_result = extractor.extract_entities(text)
        if hasattr(ner_result, "is_success") and not ner_result.is_success:
            return result
        ner_data = ner_result.value if hasattr(ner_result, "value") else ner_result

        entities = ner_data.entities if ner_data else []
        result.entity_count = len(entities)
        result.unique_entities = len(ner_data.unique_entities) if ner_data else 0

        for ent in entities:
            label = ent.label.value if hasattr(ent.label, "value") else str(ent.label)
            if label == "PER":
                result.per_count += 1
            elif label == "LOC":
                result.loc_count += 1
            elif label == "ORG":
                result.org_count += 1
            else:
                result.misc_count += 1
            result.entities.append({
                "text": ent.text,
                "label": label,
                "confidence": getattr(ent, "confidence", 0.0),
            })

        confidences = [getattr(e, "confidence", 0.0) for e in entities]
        result.avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    except Exception as e:
        result.entities.append({"error": str(e)})

    result.elapsed_ms = (time.time() - t0) * 1000
    return result


def run_multimethod_ner(text: str) -> MethodResult:
    """Ejecuta NER multi-método (spaCy + transformer + voting)."""
    result = MethodResult(method="multimethod")
    t0 = time.time()

    try:
        from narrative_assistant.nlp.ner import NERExtractor

        extractor = NERExtractor(
            use_llm_preprocessing=False,  # Skip LLM for speed
            use_transformer_ner=True,
        )
        ner_result = extractor.extract_entities(text)
        if hasattr(ner_result, "is_success") and not ner_result.is_success:
            return result
        ner_data = ner_result.value if hasattr(ner_result, "value") else ner_result

        entities = ner_data.entities if ner_data else []
        result.entity_count = len(entities)
        result.unique_entities = len(ner_data.unique_entities) if ner_data else 0

        for ent in entities:
            label = ent.label.value if hasattr(ent.label, "value") else str(ent.label)
            if label == "PER":
                result.per_count += 1
            elif label == "LOC":
                result.loc_count += 1
            elif label == "ORG":
                result.org_count += 1
            else:
                result.misc_count += 1
            result.entities.append({
                "text": ent.text,
                "label": label,
                "confidence": getattr(ent, "confidence", 0.0),
            })

        confidences = [getattr(e, "confidence", 0.0) for e in entities]
        result.avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    except Exception as e:
        result.entities.append({"error": str(e)})

    result.elapsed_ms = (time.time() - t0) * 1000
    return result


# ============================================================================
# Inter-method agreement
# ============================================================================


def compute_agreement(method_a: MethodResult, method_b: MethodResult) -> float:
    """
    Calcula acuerdo entre dos métodos (overlap de entidades detectadas).

    Returns:
        Jaccard similarity (0-1) entre conjuntos de entidades.
    """
    set_a = {e["text"].lower() for e in method_a.entities if "text" in e}
    set_b = {e["text"].lower() for e in method_b.entities if "text" in e}

    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0

    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


# ============================================================================
# File Discovery
# ============================================================================

CATEGORY_MAP = {
    "01_ficcion": "ficcion",
    "02_memorias": "memorias",
    "03_biografia": "biografia",
    "04_famosos": "famosos",
    "05_divulgacion": "divulgacion",
    "06_ensayo": "ensayo",
    "07_autoayuda": "autoayuda",
    "08_tecnico": "tecnico",
    "09_practico": "practico",
    "10_grafico": "grafico",
    "11_infantil": "infantil",
    "12_teatro_guion": "teatro",
}


def discover_books(test_books_dir: Path, category: str | None = None) -> list[tuple[Path, str]]:
    """Descubre libros en test_books/ por categoría."""
    books = []
    for subdir in sorted(test_books_dir.iterdir()):
        if not subdir.is_dir():
            continue
        cat = CATEGORY_MAP.get(subdir.name, subdir.name)
        if category and cat != category:
            continue
        for f in sorted(subdir.iterdir()):
            if f.suffix.lower() in (".epub", ".txt", ".md"):
                books.append((f, cat))
    return books


# ============================================================================
# Main Benchmark
# ============================================================================


def run_benchmark(
    books: list[tuple[Path, str]],
    max_chars: int = 5000,
    methods: list[str] | None = None,
) -> BenchmarkReport:
    """Ejecuta el benchmark completo."""
    from datetime import datetime

    if methods is None:
        methods = ["spacy", "multimethod"]

    report = BenchmarkReport(
        timestamp=datetime.now().isoformat(),
        total_documents=len(books),
    )

    for i, (book_path, cat) in enumerate(books, 1):
        print(f"  [{i}/{len(books)}] {book_path.name} ({cat})...", end=" ", flush=True)

        text = get_text(book_path, max_chars)
        if not text or len(text) < 100:
            print("SKIP (texto insuficiente)")
            continue

        doc_result = DocumentResult(
            filename=book_path.name,
            category=cat,
            text_length=len(text),
            chunk_tested=min(len(text), max_chars),
        )

        for method_name in methods:
            if method_name == "spacy":
                m_result = run_spacy_ner(text)
            elif method_name == "multimethod":
                m_result = run_multimethod_ner(text)
            else:
                continue
            doc_result.methods[method_name] = m_result

        # Inter-method agreement
        if "spacy" in doc_result.methods and "multimethod" in doc_result.methods:
            doc_result.inter_method_agreement = compute_agreement(
                doc_result.methods["spacy"],
                doc_result.methods["multimethod"],
            )

        report.documents.append(doc_result)

        # Print summary for this doc
        parts = []
        for m_name, m_result in doc_result.methods.items():
            parts.append(f"{m_name}={m_result.entity_count}ents")
        agreement_str = f"agree={doc_result.inter_method_agreement:.0%}"
        print(f"{', '.join(parts)}, {agreement_str}")

    # Compute summary
    report.summary = compute_summary(report)

    return report


def compute_summary(report: BenchmarkReport) -> dict:
    """Computa estadísticas resumidas del benchmark."""
    if not report.documents:
        return {"error": "No documents processed"}

    summary = {
        "total_documents": len(report.documents),
        "by_category": {},
        "by_method": {},
        "agreement": {},
    }

    # Por método
    for method_name in ("spacy", "multimethod"):
        counts = []
        confidences = []
        per_counts = []
        loc_counts = []
        org_counts = []
        times = []

        for doc in report.documents:
            if method_name in doc.methods:
                m = doc.methods[method_name]
                counts.append(m.entity_count)
                confidences.append(m.avg_confidence)
                per_counts.append(m.per_count)
                loc_counts.append(m.loc_count)
                org_counts.append(m.org_count)
                times.append(m.elapsed_ms)

        if counts:
            summary["by_method"][method_name] = {
                "avg_entities": round(sum(counts) / len(counts), 1),
                "total_entities": sum(counts),
                "avg_per": round(sum(per_counts) / len(per_counts), 1),
                "avg_loc": round(sum(loc_counts) / len(loc_counts), 1),
                "avg_org": round(sum(org_counts) / len(org_counts), 1),
                "avg_confidence": round(sum(confidences) / len(confidences), 3),
                "avg_time_ms": round(sum(times) / len(times), 0),
            }

    # Agreement
    agreements = [d.inter_method_agreement for d in report.documents if d.inter_method_agreement > 0]
    if agreements:
        summary["agreement"] = {
            "avg_jaccard": round(sum(agreements) / len(agreements), 3),
            "min_jaccard": round(min(agreements), 3),
            "max_jaccard": round(max(agreements), 3),
        }

    # Por categoría
    cat_groups = defaultdict(list)
    for doc in report.documents:
        cat_groups[doc.category].append(doc)

    for cat, docs in cat_groups.items():
        cat_ents = []
        for doc in docs:
            for m in doc.methods.values():
                cat_ents.append(m.entity_count)
        summary["by_category"][cat] = {
            "documents": len(docs),
            "avg_entities": round(sum(cat_ents) / len(cat_ents), 1) if cat_ents else 0,
        }

    return summary


def print_summary(report: BenchmarkReport):
    """Imprime resumen del benchmark."""
    s = report.summary

    print(f"\n{'=' * 60}")
    print(f"  NER BENCHMARK REPORT")
    print(f"  Documentos: {s.get('total_documents', 0)}")
    print(f"{'=' * 60}")

    # Por método
    print(f"\n  {'Método':<15} | {'Ents/doc':>8} | {'PER':>5} | {'LOC':>5} | {'ORG':>5} | {'Conf':>6} | {'ms':>8}")
    print("  " + "-" * 70)
    for method, stats in s.get("by_method", {}).items():
        print(
            f"  {method:<15} | {stats['avg_entities']:>8.1f} | "
            f"{stats['avg_per']:>5.1f} | {stats['avg_loc']:>5.1f} | "
            f"{stats['avg_org']:>5.1f} | {stats['avg_confidence']:>6.3f} | "
            f"{stats['avg_time_ms']:>8.0f}"
        )

    # Agreement
    ag = s.get("agreement", {})
    if ag:
        print(f"\n  Inter-method agreement (Jaccard):")
        print(f"    Avg: {ag.get('avg_jaccard', 0):.3f}  "
              f"Min: {ag.get('min_jaccard', 0):.3f}  "
              f"Max: {ag.get('max_jaccard', 0):.3f}")

    # Por categoría
    print(f"\n  {'Categoría':<15} | {'Docs':>5} | {'Avg Ents':>8}")
    print("  " + "-" * 35)
    for cat, stats in sorted(s.get("by_category", {}).items()):
        print(f"  {cat:<15} | {stats['documents']:>5} | {stats['avg_entities']:>8.1f}")


def main():
    parser = argparse.ArgumentParser(description="Benchmark NER contra corpus test_books/")
    parser.add_argument("--full", action="store_true", help="Procesar todos los libros")
    parser.add_argument("--category", "-c", help="Solo una categoría (ficcion, memorias, etc.)")
    parser.add_argument("--max-docs", type=int, default=5, help="Máximo de documentos (default: 5)")
    parser.add_argument("--max-chars", type=int, default=5000, help="Chars por documento (default: 5000)")
    parser.add_argument("--output", "-o", help="Guardar reporte JSON")
    parser.add_argument("--spacy-only", action="store_true", help="Solo método spaCy")
    args = parser.parse_args()

    test_books = PROJECT_ROOT / "test_books"
    if not test_books.exists():
        print(f"ERROR: No se encontró {test_books}")
        sys.exit(1)

    books = discover_books(test_books, category=args.category)
    if not books:
        print("No se encontraron libros")
        sys.exit(1)

    if not args.full:
        # Seleccionar muestra diversa (1 por categoría, hasta max_docs)
        seen_cats = set()
        sample = []
        for book, cat in books:
            if cat not in seen_cats and len(sample) < args.max_docs:
                sample.append((book, cat))
                seen_cats.add(cat)
        if len(sample) < args.max_docs:
            for book, cat in books:
                if (book, cat) not in sample and len(sample) < args.max_docs:
                    sample.append((book, cat))
        books = sample

    print(f"Benchmark NER: {len(books)} documentos")
    print(f"Max chars/doc: {args.max_chars}")

    methods = ["spacy"] if args.spacy_only else ["spacy", "multimethod"]
    report = run_benchmark(books, max_chars=args.max_chars, methods=methods)
    print_summary(report)

    if args.output:
        output_path = Path(args.output)
        # Simplify entities for JSON output (drop full entity lists for size)
        for doc in report.documents:
            for m in doc.methods.values():
                m.entities = m.entities[:10]  # Keep only first 10

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)
        print(f"\nReporte guardado en: {output_path}")


if __name__ == "__main__":
    main()
