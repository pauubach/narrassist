#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Evaluación exhaustiva de NER en archivos DOCX de prueba.

Analiza:
- Extracción de entidades por tipo (PER, LOC, ORG, MISC)
- Distribución por fuente (spacy, llm, gazetteer, etc.)
- Confidence scores promedio
- Detección de posibles falsos positivos/negativos
- Análisis por capítulo
"""

import sys
import io
import logging
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Any, Optional

# Forzar salida UTF-8 en Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configurar logging detallado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from narrative_assistant.parsers.docx_parser import DocxParser
from narrative_assistant.nlp.ner import NERExtractor, EntityLabel
from narrative_assistant.core.config import get_config


def format_number(num: int) -> str:
    """Formatea número con separadores de miles."""
    return f"{num:,}".replace(",", ".")


def print_header(text: str, char: str = "="):
    """Imprime un encabezado formateado."""
    line = char * 80
    print(f"\n{line}")
    print(f"{text.center(80)}")
    print(f"{line}\n")


def print_section(text: str):
    """Imprime una sección."""
    print(f"\n{'─' * 80}")
    print(f"▶ {text}")
    print(f"{'─' * 80}")


def analyze_document(doc_path: Path, extractor: NERExtractor) -> Optional[Dict[str, Any]]:
    """
    Analiza un documento y extrae métricas NER.

    Returns:
        Diccionario con todas las métricas de análisis
    """
    print_section(f"Analizando: {doc_path.name}")

    try:
        # Parse documento
        parser = DocxParser()
        parse_result = parser.parse(doc_path)

        if parse_result.is_failure:
            logger.error(f"Error parsing {doc_path}: {parse_result.error}")
            return None

        raw_doc = parse_result.value
        full_text = raw_doc.full_text
        print(f"  ✓ Documento parseado: {format_number(len(full_text))} caracteres")
        print(f"  ✓ Párrafos: {format_number(len(raw_doc.paragraphs))}")

        # Extract chapters from coordinate system
        chapters = []
        if hasattr(raw_doc.coordinate_system, 'chapters'):
            chapters = raw_doc.coordinate_system.chapters
        print(f"  ✓ Capítulos detectados: {len(chapters)}")

        # Extraer entidades
        print(f"\n  Extrayendo entidades...")
        ner_result = extractor.extract_entities(full_text, enable_validation=True)

        if ner_result.is_failure:
            logger.error(f"Error NER: {ner_result.error}")
            return None

        result_value = ner_result.value
        entities = result_value.entities
        rejected = result_value.rejected_entities

        print(f"  ✓ Entidades extraídas: {len(entities)}")
        print(f"  ✓ Entidades rechazadas: {len(rejected)}")

        # Análisis por tipo
        by_type = defaultdict(list)
        for entity in entities:
            by_type[entity.label].append(entity)

        # Análisis por fuente
        by_source = defaultdict(int)
        for entity in entities:
            by_source[entity.source] += 1

        # Confidence scores
        confidences = [e.confidence for e in entities]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Entidades únicas
        unique_entities = result_value.unique_entities

        # Análisis de rechazados
        rejected_by_type = defaultdict(int)
        rejected_by_source = defaultdict(int)
        for entity in rejected:
            rejected_by_type[entity.label] += 1
            rejected_by_source[entity.source] += 1

        # Análisis por capítulo (si hay)
        entities_by_chapter = defaultdict(list)
        if chapters:
            for entity in entities:
                # Encontrar en qué capítulo está la entidad
                for i, chapter in enumerate(chapters):
                    if chapter.start_char <= entity.start_char < chapter.end_char:
                        entities_by_chapter[i].append(entity)
                        break

        return {
            'path': doc_path,
            'total_chars': len(full_text),
            'total_paragraphs': len(raw_doc.paragraphs),
            'total_chapters': len(chapters),
            'total_entities': len(entities),
            'total_rejected': len(rejected),
            'by_type': dict(by_type),
            'by_source': dict(by_source),
            'avg_confidence': avg_confidence,
            'unique_count': len(unique_entities),
            'rejected_by_type': dict(rejected_by_type),
            'rejected_by_source': dict(rejected_by_source),
            'validation_method': result_value.validation_method,
            'entities': entities,
            'rejected': rejected,
            'chapters': chapters,
            'entities_by_chapter': dict(entities_by_chapter)
        }

    except Exception as e:
        logger.error(f"Error procesando {doc_path}: {e}", exc_info=True)
        return None


def print_entity_samples(entities: List, label: EntityLabel, max_samples: int = 20):
    """Imprime muestras de entidades de un tipo específico."""
    filtered = [e for e in entities if e.label == label]
    if not filtered:
        print(f"    (ninguna entidad {label.value})")
        return

    # Ordenar por confidence descendente
    filtered.sort(key=lambda x: x.confidence, reverse=True)

    # Mostrar muestras únicas
    unique_texts = []
    seen = set()
    for e in filtered:
        text_lower = e.text.lower()
        if text_lower not in seen:
            seen.add(text_lower)
            unique_texts.append((e.text, e.confidence, e.source))
            if len(unique_texts) >= max_samples:
                break

    for text, conf, source in unique_texts:
        conf_bar = "█" * int(conf * 10)
        print(f"    • {text:<35} [{conf_bar:<10}] {conf:.2f} ({source})")


def print_detailed_report(results: Dict[str, Any]):
    """Imprime reporte detallado de un documento."""

    print_header("REPORTE DETALLADO DE NER")

    # Resumen general
    print("📊 RESUMEN GENERAL")
    print(f"  Documento:           {results['path'].name}")
    print(f"  Tamaño:              {format_number(results['total_chars'])} caracteres")
    print(f"  Párrafos:            {format_number(results['total_paragraphs'])}")
    print(f"  Capítulos:           {results['total_chapters']}")
    print(f"  Método validación:   {results['validation_method']}")

    print(f"\n🔍 EXTRACCIÓN NER")
    print(f"  Total extraídas:     {results['total_entities']}")
    print(f"  Únicas:              {results['unique_count']}")
    print(f"  Rechazadas:          {results['total_rejected']}")
    print(f"  Confidence promedio: {results['avg_confidence']:.3f}")

    # Densidad de entidades
    density = (results['total_entities'] / results['total_chars'] * 1000) if results['total_chars'] > 0 else 0
    print(f"  Densidad:            {density:.2f} entidades/1000 chars")

    # Por tipo
    print(f"\n📈 DISTRIBUCIÓN POR TIPO")
    by_type = results['by_type']
    total = results['total_entities']

    for label in EntityLabel:
        count = len(by_type.get(label, []))
        pct = (count / total * 100) if total > 0 else 0.0
        bar = "█" * int(pct / 2)
        print(f"  {label.value:<6} {count:>5} ({pct:>5.1f}%)  {bar}")

    # Por fuente
    print(f"\n🔗 DISTRIBUCIÓN POR FUENTE")
    by_source = results['by_source']
    for source, count in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total * 100) if total > 0 else 0.0
        bar = "█" * int(pct / 2)
        print(f"  {source:<20} {count:>5} ({pct:>5.1f}%)  {bar}")

    # Entidades rechazadas
    if results['total_rejected'] > 0:
        print(f"\n❌ ENTIDADES RECHAZADAS")
        print(f"  Total rechazadas: {results['total_rejected']}")

        print(f"\n  Por tipo:")
        for label, count in results['rejected_by_type'].items():
            print(f"    {label.value:<6} {count:>5}")

        print(f"\n  Por fuente:")
        for source, count in results['rejected_by_source'].items():
            print(f"    {source:<20} {count:>5}")

    # Análisis por capítulo
    if results['entities_by_chapter']:
        print(f"\n📖 DISTRIBUCIÓN POR CAPÍTULO")
        for chapter_idx, chapter_entities in sorted(results['entities_by_chapter'].items()):
            chapter = results['chapters'][chapter_idx]
            print(f"\n  Capítulo {chapter_idx + 1}: {chapter.title or '(sin título)'}")
            print(f"    Entidades: {len(chapter_entities)}")

            # Contar por tipo en este capítulo
            types_in_chapter = defaultdict(int)
            for e in chapter_entities:
                types_in_chapter[e.label] += 1

            for label, count in types_in_chapter.items():
                print(f"      {label.value}: {count}")

    # Muestras por tipo
    print(f"\n📝 MUESTRAS DE ENTIDADES (Top 20 por confianza)")

    for label in EntityLabel:
        label_name = {
            EntityLabel.PER: "PERSONAS",
            EntityLabel.LOC: "LUGARES",
            EntityLabel.ORG: "ORGANIZACIONES",
            EntityLabel.MISC: "MISCELÁNEA"
        }.get(label, label.value)

        print(f"\n  {label.value} - {label_name}")
        print_entity_samples(results['entities'], label)

    # Análisis de falsos positivos (muestras de rechazados)
    if results['rejected']:
        print(f"\n⚠️  MUESTRAS DE ENTIDADES RECHAZADAS (posibles falsos positivos)")
        print(f"    Mostrando primeras 30 rechazadas:")
        rejected_samples = results['rejected'][:30]
        for e in rejected_samples:
            print(f"    • {e.text:<35} ({e.label.value}) - {e.source} [{e.confidence:.2f}]")


def print_comparison_summary(all_results: List[Dict[str, Any]]):
    """Imprime resumen comparativo de todos los documentos."""

    print_header("RESUMEN COMPARATIVO - TODOS LOS DOCUMENTOS", "=")

    total_docs = len(all_results)
    total_chars = sum(r['total_chars'] for r in all_results)
    total_entities = sum(r['total_entities'] for r in all_results)
    total_rejected = sum(r['total_rejected'] for r in all_results)

    print(f"📚 CORPUS ANALIZADO")
    print(f"  Documentos:          {total_docs}")
    print(f"  Caracteres totales:  {format_number(total_chars)}")
    print(f"  Entidades extraídas: {format_number(total_entities)}")
    print(f"  Entidades rechazadas:{format_number(total_rejected)}")

    acceptance_ratio = (total_entities/(total_entities+total_rejected)*100) if (total_entities + total_rejected) > 0 else 0
    print(f"  Ratio aceptación:    {acceptance_ratio:.1f}%")

    # Promedio por documento
    print(f"\n📊 PROMEDIOS POR DOCUMENTO")
    avg_entities = total_entities / total_docs if total_docs > 0 else 0
    avg_chars = total_chars / total_docs if total_docs > 0 else 0
    avg_density = (total_entities / total_chars * 1000) if total_chars > 0 else 0

    print(f"  Entidades/doc:       {avg_entities:.1f}")
    print(f"  Caracteres/doc:      {format_number(int(avg_chars))}")
    print(f"  Densidad:            {avg_density:.2f} entidades/1000 chars")

    # Agregado por tipo
    print(f"\n📈 AGREGADO POR TIPO (TODOS LOS DOCS)")

    agg_by_type = defaultdict(int)
    for result in all_results:
        for label, entities in result['by_type'].items():
            agg_by_type[label] += len(entities)

    for label in EntityLabel:
        count = agg_by_type.get(label, 0)
        pct = (count / total_entities * 100) if total_entities > 0 else 0.0
        bar = "█" * int(pct / 2)
        print(f"  {label.value:<6} {count:>6} ({pct:>5.1f}%)  {bar}")

    # Agregado por fuente
    print(f"\n🔗 AGREGADO POR FUENTE (TODOS LOS DOCS)")

    agg_by_source = defaultdict(int)
    for result in all_results:
        for source, count in result['by_source'].items():
            agg_by_source[source] += count

    for source, count in sorted(agg_by_source.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_entities * 100) if total_entities > 0 else 0.0
        bar = "█" * int(pct / 2)
        print(f"  {source:<20} {count:>6} ({pct:>5.1f}%)  {bar}")

    # Tabla comparativa
    print(f"\n📋 TABLA COMPARATIVA")
    print(f"  {'Documento':<40} {'Entidades':>10} {'PER':>6} {'LOC':>6} {'ORG':>6} {'MISC':>6}")
    print(f"  {'-'*78}")

    for result in all_results:
        name = result['path'].name[:38]
        total = result['total_entities']
        per = len(result['by_type'].get(EntityLabel.PER, []))
        loc = len(result['by_type'].get(EntityLabel.LOC, []))
        org = len(result['by_type'].get(EntityLabel.ORG, []))
        misc = len(result['by_type'].get(EntityLabel.MISC, []))

        print(f"  {name:<40} {total:>10} {per:>6} {loc:>6} {org:>6} {misc:>6}")


def print_recommendations(all_results: List[Dict[str, Any]]):
    """Imprime recomendaciones basadas en el análisis."""

    print_header("RECOMENDACIONES Y OBSERVACIONES", "=")

    if not all_results:
        print("No hay resultados para analizar.")
        return

    # Calcular estadísticas agregadas
    total_entities = sum(r['total_entities'] for r in all_results)
    total_chars = sum(r['total_chars'] for r in all_results)
    total_rejected = sum(r['total_rejected'] for r in all_results)

    avg_density = (total_entities / total_chars * 1000) if total_chars > 0 else 0
    rejection_rate = (total_rejected / (total_entities + total_rejected) * 100) if (total_entities + total_rejected) > 0 else 0

    # Analizar distribución por tipo
    agg_by_type = defaultdict(int)
    for result in all_results:
        for label, entities in result['by_type'].items():
            agg_by_type[label] += len(entities)

    per_pct = (agg_by_type.get(EntityLabel.PER, 0) / total_entities * 100) if total_entities > 0 else 0
    loc_pct = (agg_by_type.get(EntityLabel.LOC, 0) / total_entities * 100) if total_entities > 0 else 0

    # Analizar fuentes
    agg_by_source = defaultdict(int)
    for result in all_results:
        for source, count in result['by_source'].items():
            agg_by_source[source] += count

    spacy_pct = (agg_by_source.get('spacy', 0) / total_entities * 100) if total_entities > 0 else 0

    print("🔍 ANÁLISIS DE RESULTADOS\n")

    # 1. Densidad
    print("1. DENSIDAD DE ENTIDADES")
    print(f"   Densidad actual: {avg_density:.2f} entidades/1000 chars")
    if avg_density < 2:
        print("   ⚠️  DENSIDAD MUY BAJA - Posible problema de recall")
        print("      • Verificar que el modelo spaCy se cargó correctamente")
        print("      • Considerar habilitar más métodos de detección (gazetteer, LLM)")
    elif avg_density > 12:
        print("   ⚠️  DENSIDAD MUY ALTA - Posible problema de precision")
        print("      • Muchos falsos positivos detectados")
        print("      • Revisar umbrales de confianza")
    else:
        print("   ✓ Densidad dentro del rango normal (3-8 para ficción)")
    print()

    # 2. Precision
    print("2. PRECISION (Falsos Positivos)")
    print(f"   Tasa de rechazo: {rejection_rate:.1f}%")
    if rejection_rate > 30:
        print("   ⚠️  ALTA TASA DE RECHAZO")
        print("      • El validador está rechazando muchas entidades")
        print("      • Revisar entidades rechazadas para identificar patrones")
        print("      • Posible ajuste de umbrales del validador")
    else:
        print("   ✓ Tasa de rechazo razonable")
    print()

    # 3. Distribución por tipo
    print("3. DISTRIBUCIÓN POR TIPO")
    print(f"   PER: {per_pct:.1f}%, LOC: {loc_pct:.1f}%")
    if per_pct < 50:
        print("   ⚠️  PER MUY BAJO para ficción (esperado 60-70%)")
        print("      • Posible problema detectando personajes")
    elif per_pct > 80:
        print("   ⚠️  PER MUY ALTO - Posibles falsos positivos en PER")
    else:
        print("   ✓ Distribución razonable para ficción literaria")
    print()

    # 4. Fuentes
    print("4. FUENTES DE EXTRACCIÓN")
    print(f"   spaCy dominancia: {spacy_pct:.1f}%")
    if spacy_pct > 90:
        print("   ⚠️  SPACY DOMINANTE - Otros métodos no contribuyen")
        print("      • Verificar que LLM está habilitado si se desea")
        print("      • Verificar que el gazetteer dinámico funciona")
    else:
        print("   ✓ Buena diversidad de fuentes")
    print()

    # 5. Recomendaciones generales
    print("5. ACCIONES RECOMENDADAS\n")

    print("   A. VALIDACIÓN MANUAL")
    print("      • Buscar manualmente 3-5 personajes principales en el texto")
    print("      • Verificar si fueron detectados correctamente")
    print("      • Identificar patrones de nombres que no se están detectando")
    print()

    print("   B. ANÁLISIS DE RECHAZADOS")
    print("      • Revisar muestras de entidades rechazadas arriba")
    print("      • Identificar si hay verdaderos positivos siendo rechazados")
    print("      • Ajustar umbrales del validador si es necesario")
    print()

    print("   C. ANÁLISIS DE CONFIDENCE")
    print("      • Validar manualmente entidades con baja confianza (<0.7)")
    print("      • Determinar si son verdaderos positivos o falsos positivos")
    print()

    print("   D. PRÓXIMOS PASOS")
    print("      • Crear gold standard manual para el documento principal")
    print("      • Calcular métricas exactas de precision/recall/F1")
    print("      • Iterar en mejoras del sistema")
    print()


def main():
    """Función principal."""

    print_header("EVALUACIÓN EXHAUSTIVA DE NER", "═")
    print("Analizando archivos DOCX de prueba...")
    print("Este proceso puede tardar varios minutos.\n")

    # Inicializar extractor
    print("🔧 Inicializando NER Extractor...")
    config = get_config()
    print(f"  • Device preference: {config.gpu.device_preference}")
    print(f"  • GPU habilitado para spaCy: {config.gpu.spacy_gpu_enabled}")

    try:
        extractor = NERExtractor()
        print("  ✓ Extractor listo\n")
    except Exception as e:
        logger.error(f"Error inicializando extractor: {e}", exc_info=True)
        return 1

    # Buscar archivos de prueba
    test_books_dir = Path(__file__).parent.parent / "test_books"

    # Priorizar la_regenta_sample.docx
    primary_file = test_books_dir / "la_regenta_sample.docx"

    if not primary_file.exists():
        print(f"❌ ERROR: No se encontró el archivo principal: {primary_file}")
        print("   Buscando otros archivos DOCX...")
        primary_file = None

    # Buscar otros archivos DOCX (excluyendo temporales)
    all_docx = [
        f for f in test_books_dir.glob("*.docx")
        if not f.name.startswith("~$")
    ]

    if not all_docx:
        print(f"❌ ERROR: No se encontraron archivos .docx en {test_books_dir}")
        return 1

    # Ordenar para poner la_regenta primero si existe
    if primary_file and primary_file.exists():
        docx_files = [primary_file] + [f for f in all_docx if f != primary_file]
    else:
        docx_files = all_docx
        primary_file = docx_files[0]  # Usar el primero como principal

    print(f"📁 Archivos encontrados: {len(docx_files)}")
    for f in docx_files:
        marker = "★" if f == primary_file else " "
        print(f"  {marker} {f.name}")
    print()

    # Analizar cada documento
    all_results = []

    for doc_path in docx_files:
        result = analyze_document(doc_path, extractor)
        if result:
            all_results.append(result)

            # Imprimir reporte detallado solo para el archivo principal
            if doc_path == primary_file:
                print_detailed_report(result)

    # Resumen comparativo
    if len(all_results) > 1:
        print_comparison_summary(all_results)

    # Recomendaciones
    print_recommendations(all_results)

    print_header("EVALUACIÓN COMPLETADA", "═")
    print(f"✅ Se analizaron {len(all_results)} documentos exitosamente.")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
