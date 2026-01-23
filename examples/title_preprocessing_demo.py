#!/usr/bin/env python3
"""
Demo del preprocesador de títulos para spaCy.

Demuestra los 3 principales usos:
1. Detección simple de títulos
2. Preprocesamiento para análisis con spaCy
3. Extracción de entidades agrupadas por capítulo
"""

import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from narrative_assistant.nlp.title_preprocessor import (
    TitlePreprocessor,
    is_title,
)
from narrative_assistant.nlp.spacy_title_integration import (
    analyze_with_title_handling,
    extract_entities_by_title,
    debug_parsing,
)
from narrative_assistant.nlp.spacy_gpu import load_spacy_model


# Ejemplo de texto con títulos problemáticos
SAMPLE_TEXT = """1: El Despertar

María Sánchez se despertó temprano. La luz del amanecer se filtraba por las ventanas.

Juan estaba en la cocina preparando el desayuno.

2: La Búsqueda

María salió corriendo hacia el bosque. Buscaba a su hermano gemelo.

Pedro la encontró en el camino. "¿Dónde vas?", preguntó.

CAPÍTULO 3: El Encuentro

En la plaza del pueblo, María se encontró con un misterioso personaje. Los ojos del desconocido brillaban con inteligencia.

"Creo que te conozco", dijo María.

* * *

El hombre sonrió enigmáticamente. "Quizás en otra vida".

---

4 - El Retorno

María volvió a casa confundida. ¿Quién era ese hombre?

Su madre estaba esperándola. "¿Dónde estabas?", preguntó con preocupación.
"""


def demo_basic_detection():
    """Demuestra detección simple de títulos."""
    print("=" * 80)
    print("DEMO 1: Detección Simple de Títulos")
    print("=" * 80)
    print()

    test_lines = [
        "1: El Despertar",
        "María Sánchez se despertó temprano.",
        "CAPÍTULO 3: El Encuentro",
        "La luz del amanecer se filtraba por las ventanas.",
        "2.1 Subsección importante",
        "Pedro la encontró en el camino.",
        "* * *",
        "---",
    ]

    for line in test_lines:
        result = is_title(line)
        marker = "[TÍTULO]" if result else "[CONTENIDO]"
        print(f"{marker} {line}")
    print()


def demo_preprocessing():
    """Demuestra preprocesamiento de un texto completo."""
    print("=" * 80)
    print("DEMO 2: Preprocesamiento de Texto Completo")
    print("=" * 80)
    print()

    preprocessor = TitlePreprocessor()
    processed = preprocessor.process(SAMPLE_TEXT)

    print(f"Análisis del documento:")
    print(f"  - Total de párrafos: {len(processed.paragraphs)}")
    print(f"  - Títulos detectados: {processed.title_count}")
    print(f"  - Párrafos de contenido: {processed.content_count}")
    print()

    print("Párrafos detectados:")
    for i, para in enumerate(processed.paragraphs):
        marker = "[TÍTULO]" if para.is_title else "[CONTENIDO]"
        confidence_str = f"(confianza: {para.confidence:.1%})" if para.is_title else ""
        text_preview = para.text[:50].replace("\n", " ") + "..." if len(para.text) > 50 else para.text
        print(f"  {i+1:2d}. {marker} {text_preview} {confidence_str}")
    print()

    print("Contenido sin títulos (listo para spaCy):")
    print("-" * 80)
    print(processed.get_content_text())
    print("-" * 80)
    print()


def demo_spacy_analysis():
    """Demuestra análisis con spaCy de contenido preprocesado."""
    print("=" * 80)
    print("DEMO 3: Análisis con spaCy (consciente de títulos)")
    print("=" * 80)
    print()

    print("Cargando modelo spaCy...")
    try:
        nlp = load_spacy_model(enable_gpu=False)
    except Exception as e:
        print(f"Error cargando modelo: {e}")
        print("Saltando demo de spaCy")
        return

    print("Analizando texto...")
    result = analyze_with_title_handling(nlp, SAMPLE_TEXT)

    print(f"Análisis completado:")
    print(f"  - Documentos procesados: {len(result.docs)}")
    print(f"  - Títulos: {result.title_count}")
    print(f"  - Contenido: {result.content_count}")
    print()

    print("Resultados agrupados por título:")
    print("-" * 80)
    for title_doc, content_docs in result.grouped_by_title:
        if title_doc:
            print(f"\n[TÍTULO] {title_doc.text}")
        else:
            print(f"\n[SIN TÍTULO]")

        if content_docs:
            for i, doc in enumerate(content_docs, 1):
                print(f"  Párrafo {i}:")
                # Mostrar verbos principales
                for token in doc:
                    if token.pos_ == "VERB" and token.dep_ in ("ROOT", "acl"):
                        print(f"    - Verbo: {token.text} ({token.dep_})")
                # Mostrar entidades
                if doc.ents:
                    print(f"    Entidades:")
                    for ent in doc.ents:
                        print(f"      - {ent.text} ({ent.label_})")
        else:
            print("  (sin contenido)")

    print()


def demo_entity_extraction():
    """Demuestra extracción de entidades por capítulo."""
    print("=" * 80)
    print("DEMO 4: Extracción de Entidades por Capítulo")
    print("=" * 80)
    print()

    print("Cargando modelo spaCy...")
    try:
        nlp = load_spacy_model(enable_gpu=False)
    except Exception as e:
        print(f"Error cargando modelo: {e}")
        print("Saltando demo de entidades")
        return

    print("Extrayendo entidades...")
    entities = extract_entities_by_title(nlp, SAMPLE_TEXT)

    print("Entidades encontradas por capítulo:")
    print("-" * 80)
    for title, ents_by_label in entities.items():
        print(f"\n{title}:")
        for label, entity_list in ents_by_label.items():
            print(f"  {label}:")
            for ent in entity_list:
                print(f"    - {ent}")

    print()


def demo_parsing_quality():
    """Demuestra el impacto del preprocesamiento en la calidad."""
    print("=" * 80)
    print("DEMO 5: Impacto del Preprocesamiento (Métricas)")
    print("=" * 80)
    print()

    print("Cargando modelo spaCy...")
    try:
        nlp = load_spacy_model(enable_gpu=False)
    except Exception as e:
        print(f"Error cargando modelo: {e}")
        print("Saltando demo de métricas")
        return

    # Crear un texto con un título problemático
    problematic_text = """1: El Despertar

María se despertó temprano. Vio el amanecer. Escuchó el canto de los pájaros."""

    print("Texto analizado:")
    print("-" * 80)
    print(problematic_text)
    print("-" * 80)
    print()

    # Comparar análisis
    doc_with_title = nlp(problematic_text)
    print("Parsing CON título mezclado:")
    for token in doc_with_title:
        if token.pos_ == "VERB":
            print(f"  {token.text:10s} POS={token.pos_:6s} DEP={token.dep_:10s} HEAD={token.head.text}")
    print()

    # Sin título
    content_only = "María se despertó temprano. Vio el amanecer. Escuchó el canto de los pájaros."
    doc_without_title = nlp(content_only)
    print("Parsing SIN título:")
    for token in doc_without_title:
        if token.pos_ == "VERB":
            print(f"  {token.text:10s} POS={token.pos_:6s} DEP={token.dep_:10s} HEAD={token.head.text}")
    print()


def main():
    """Ejecuta todas las demos."""
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "DEMO: PREPROCESADOR DE TÍTULOS PARA SPACY" + " " * 17 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    # Ejecutar demos
    demo_basic_detection()
    demo_preprocessing()
    demo_spacy_analysis()
    demo_entity_extraction()
    demo_parsing_quality()

    print("=" * 80)
    print("DEMOS COMPLETADAS")
    print("=" * 80)
    print()
    print("Resumen de características:")
    print("  1. Detección de títulos con múltiples heurísticas")
    print("  2. Preprocesamiento automático para spaCy")
    print("  3. Análisis consciente de títulos (agrupación)")
    print("  4. Extracción de entidades y dependencias por capítulo")
    print("  5. Métricas de impacto del preprocesamiento")
    print()


if __name__ == "__main__":
    main()
