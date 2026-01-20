#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Evaluación rápida de NER en archivos DOCX (sin validación LLM).

Para obtener resultados más rápido, deshabilitamos la validación LLM.
"""

import sys
import io
import logging
from collections import defaultdict
from pathlib import Path

# Forzar salida UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configurar logging
logging.basicConfig(
    level=logging.WARNING,  # Solo warnings y errors para reducir ruido
    format='%(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from narrative_assistant.parsers.docx_parser import DocxParser
from narrative_assistant.nlp.ner import NERExtractor, EntityLabel


def format_number(num: int) -> str:
    return f"{num:,}".replace(",", ".")


def print_header(text: str, char: str = "="):
    line = char * 80
    print(f"\n{line}")
    print(f"{text.center(80)}")
    print(f"{line}\n")


def print_section(text: str):
    print(f"\n{'─' * 80}")
    print(f"▶ {text}")
    print(f"{'─' * 80}")


def main():
    print_header("EVALUACIÓN RÁPIDA DE NER (Sin validación LLM)", "═")

    # Inicializar extractor
    print("🔧 Inicializando NER Extractor (sin validación LLM)...")
    extractor = NERExtractor()
    print("  ✓ Listo\n")

    # Buscar archivo principal
    test_books_dir = Path(__file__).parent.parent / "test_books"
    doc_path = test_books_dir / "la_regenta_sample.docx"

    if not doc_path.exists():
        print(f"❌ ERROR: No se encontró {doc_path}")
        return 1

    print(f"📄 Analizando: {doc_path.name}\n")

    # Parse documento
    print("  Parseando documento...")
    parser = DocxParser()
    parse_result = parser.parse(doc_path)

    if parse_result.is_failure:
        print(f"  ❌ Error: {parse_result.error}")
        return 1

    raw_doc = parse_result.value
    full_text = raw_doc.full_text

    print(f"  ✓ {format_number(len(full_text))} caracteres")
    print(f"  ✓ {format_number(len(raw_doc.paragraphs))} párrafos")

    # Extraer entidades SIN validación
    print(f"\n  Extrayendo entidades (sin validación LLM)...")
    ner_result = extractor.extract_entities(full_text, enable_validation=False)

    if ner_result.is_failure:
        print(f"  ❌ Error: {ner_result.error}")
        return 1

    result_value = ner_result.value
    entities = result_value.entities

    print(f"  ✓ {len(entities)} entidades extraídas\n")

    # Análisis por tipo
    print_header("DISTRIBUCIÓN POR TIPO")

    by_type = defaultdict(list)
    for entity in entities:
        by_type[entity.label].append(entity)

    for label in EntityLabel:
        count = len(by_type.get(label, []))
        pct = (count / len(entities) * 100) if entities else 0.0
        bar = "█" * int(pct / 2)
        print(f"  {label.value:<6} {count:>5} ({pct:>5.1f}%)  {bar}")

    # Análisis por fuente
    print_header("DISTRIBUCIÓN POR FUENTE")

    by_source = defaultdict(int)
    for entity in entities:
        by_source[entity.source] += 1

    for source, count in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(entities) * 100) if entities else 0.0
        bar = "█" * int(pct / 2)
        print(f"  {source:<20} {count:>5} ({pct:>5.1f}%)  {bar}")

    # Muestras por tipo
    print_header("MUESTRAS DE ENTIDADES")

    for label in EntityLabel:
        label_name = {
            EntityLabel.PER: "PERSONAS",
            EntityLabel.LOC: "LUGARES",
            EntityLabel.ORG: "ORGANIZACIONES",
            EntityLabel.MISC: "MISCELÁNEA"
        }.get(label, label.value)

        filtered = [e for e in entities if e.label == label]
        if not filtered:
            continue

        print(f"\n{label.value} - {label_name} (Total: {len(filtered)})")

        # Mostrar top 15 por confianza
        filtered.sort(key=lambda x: x.confidence, reverse=True)
        unique_texts = []
        seen = set()
        for e in filtered:
            text_lower = e.text.lower()
            if text_lower not in seen:
                seen.add(text_lower)
                unique_texts.append((e.text, e.confidence, e.source))
                if len(unique_texts) >= 15:
                    break

        for text, conf, source in unique_texts:
            conf_bar = "█" * int(conf * 10)
            print(f"  • {text:<35} [{conf_bar:<10}] {conf:.2f} ({source})")

    # Confidence scores
    print_header("ANÁLISIS DE CONFIANZA")

    confidences = [e.confidence for e in entities]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0
    min_conf = min(confidences) if confidences else 0
    max_conf = max(confidences) if confidences else 0

    print(f"  Promedio:  {avg_conf:.3f}")
    print(f"  Mínima:    {min_conf:.3f}")
    print(f"  Máxima:    {max_conf:.3f}")

    # Entidades de baja confianza
    low_conf = [e for e in entities if e.confidence < 0.7]
    if low_conf:
        print(f"\n  Entidades de baja confianza (<0.7): {len(low_conf)}")
        print(f"  Muestras:")
        for e in low_conf[:10]:
            print(f"    • {e.text:<30} {e.confidence:.2f} ({e.label.value}, {e.source})")

    # Estadísticas finales
    print_header("RESUMEN")

    density = (len(entities) / len(full_text) * 1000) if len(full_text) > 0 else 0
    unique_count = len(result_value.unique_entities)

    print(f"  Total entidades:     {len(entities)}")
    print(f"  Entidades únicas:    {unique_count}")
    print(f"  Densidad:            {density:.2f} entidades/1000 chars")
    print(f"  Caracteres:          {format_number(len(full_text))}")

    print_header("EVALUACIÓN COMPLETADA", "═")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
