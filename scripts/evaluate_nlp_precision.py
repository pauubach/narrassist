#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de evaluacion de precision de metodos NLP.

Ejecuta analisis sobre textos de prueba con gold standard conocido
y calcula metricas de precision, recall y F1.

Uso:
    python scripts/evaluate_nlp_precision.py
"""

import sys
import io
import json
from pathlib import Path

# Forzar salida UTF-8 en Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from narrative_assistant.nlp.spacy_gpu import load_spacy_model
from narrative_assistant.nlp.embeddings import EmbeddingsModel
from narrative_assistant.nlp.ner import NERExtractor
from narrative_assistant.entities.semantic_fusion import SemanticFusionService
from narrative_assistant.nlp.grammar.spanish_rules import check_dequeismo_spacy, check_queismo


# =============================================================================
# GOLD STANDARD - Anotaciones manuales
# =============================================================================

@dataclass
class GoldEntity:
    name: str
    entity_type: str
    mentions: list[str] = field(default_factory=list)


@dataclass
class GoldAttribute:
    entity: str
    key: str
    values: list[str]  # Múltiples valores = inconsistencia
    chapters: list[int]


@dataclass
class GoldGrammarError:
    error_type: str  # dequeismo, queismo, laismo, concordancia_genero, etc.
    text: str
    correction: str
    chapter: int


@dataclass
class GoldStandard:
    """Anotaciones gold standard para un texto de prueba."""
    entities: list[GoldEntity]
    attributes: list[GoldAttribute]
    grammar_errors: list[GoldGrammarError]
    fusion_pairs: list[tuple[str, str]]  # Pares que DEBEN fusionarse


# Gold standard para prueba_inconsistencias_personajes.txt
GOLD_INCONSISTENCIAS = GoldStandard(
    entities=[
        GoldEntity("María Sánchez", "PER", ["María", "María Sánchez"]),
        GoldEntity("Juan Pérez", "PER", ["Juan", "Juan Pérez"]),
        GoldEntity("Pedro García", "PER", ["Pedro", "Pedro García"]),
        GoldEntity("Elena", "PER", ["Elena"]),
    ],
    attributes=[
        GoldAttribute("María", "ojos", ["azules"], [1]),
        GoldAttribute("María", "cabello", ["negro largo", "rubio", "castaño largo"], [1, 1, 3]),
        GoldAttribute("María", "estatura", ["alta", "baja"], [1, 2]),
        GoldAttribute("María", "profesión", ["profesora de literatura", "matemáticas"], [1, 2]),
        GoldAttribute("Juan", "barba", ["espesa", "afeitado"], [1, 4]),
        GoldAttribute("Juan", "edad", ["35", "38", "casi 40"], [4, 4, 4]),
        GoldAttribute("Juan", "profesión", ["carpintero", "abogado"], [1, 5]),
        GoldAttribute("Pedro", "ojos", ["verdes", "azules"], [2, 3]),
        GoldAttribute("Elena", "cabello", ["pelirroja", "negro teñido rubio"], [3, 5]),
    ],
    grammar_errors=[],  # Este texto no tiene errores gramaticales intencionados
    fusion_pairs=[
        ("María", "María Sánchez"),
        ("Juan", "Juan Pérez"),
        ("Pedro", "Pedro García"),
    ]
)


# Gold standard para manuscrito_prueba_errores.txt
# NOTA: El texto contiene los errores en el cuerpo Y en las notas del autor al final
GOLD_ERRORES_GRAMATICALES = GoldStandard(
    entities=[
        GoldEntity("María", "PER", ["María", "Maria"]),
        GoldEntity("Juan", "PER", ["Juan"]),
    ],
    attributes=[],
    grammar_errors=[
        # Dequeísmo - 4 instancias en el texto principal
        # (las notas del final también contienen "pensaba de que" que se detecta)
        GoldGrammarError("dequeismo", "pensaba de que", "pensaba que", 1),  # línea 9
        GoldGrammarError("dequeismo", "pienso de que", "pienso que", 1),    # línea 12
        GoldGrammarError("dequeismo", "pensamos de que", "pensamos que", 2), # línea 22
        GoldGrammarError("dequeismo", "opinaba de que", "opinaba que", 3),  # línea 41
        # Queísmo - textos exactos que detecta la regla regex
        GoldGrammarError("queismo", "estaba segura que", "estaba segura de que", 1),  # línea 9
        GoldGrammarError("queismo", "me acuerdo que", "me acuerdo de que", 2),        # línea 22
        GoldGrammarError("queismo", "estaba convencido que", "estaba convencido de que", 2), # línea 22
        GoldGrammarError("queismo", "estoy seguro que", "estoy seguro de que", 2),    # línea 26
        GoldGrammarError("queismo", "me alegro que", "me alegro de que", 2),          # línea 27
        GoldGrammarError("queismo", "me di cuenta que", "me di cuenta de que", 3),    # línea 37
        GoldGrammarError("queismo", "a pesar que", "a pesar de que", 3),              # línea 39
        GoldGrammarError("queismo", "después que", "después de que", 3),              # línea 39
        GoldGrammarError("queismo", "se alegraba que", "se alegraba de que", 3),      # línea 41
        # Laísmo
        GoldGrammarError("laismo", "la dijo", "le dijo", 1),
        GoldGrammarError("laismo", "La había preparado", "Le había preparado", 1),
        GoldGrammarError("laismo", "la contó", "le contó", 2),
        GoldGrammarError("laismo", "las dijo", "les dijo", 3),
        # Concordancia género
        GoldGrammarError("concordancia_genero", "El casa", "La casa", 1),
        GoldGrammarError("concordancia_genero", "casa antiguo", "casa antigua", 1),
        GoldGrammarError("concordancia_genero", "el ventanas", "las ventanas", 1),
        GoldGrammarError("concordancia_genero", "La amor", "El amor", 3),
        GoldGrammarError("concordancia_genero", "el mesa", "la mesa", 3),
        # Concordancia número
        GoldGrammarError("concordancia_numero", "el vaso llenos", "el vaso lleno", 2),
        # Redundancias
        GoldGrammarError("redundancia", "subió arriba", "subió", 1),
        GoldGrammarError("redundancia", "bajó abajo", "bajó", 2),
        GoldGrammarError("redundancia", "salieron afuera", "salieron", 3),
        GoldGrammarError("redundancia", "más mejor", "mejor", 3),
        # Otros
        GoldGrammarError("verbo_incorrecto", "Habemos", "Hay/Somos", 2),
    ],
    fusion_pairs=[
        ("María", "Maria"),  # Con y sin tilde
    ]
)


# =============================================================================
# FUNCIONES DE EVALUACIÓN
# =============================================================================

def evaluate_ner(text: str, gold: GoldStandard, nlp) -> dict:
    """Evalúa precisión de NER usando el extractor completo con validación."""
    extractor = NERExtractor(nlp)

    # Usar el extractor completo que incluye validación
    result_wrapper = extractor.extract_entities(text, enable_validation=True)

    # El resultado puede ser un Result wrapper
    if hasattr(result_wrapper, 'value'):
        result = result_wrapper.value
    elif hasattr(result_wrapper, 'is_success') and result_wrapper.is_success:
        result = result_wrapper.value
    else:
        result = result_wrapper

    # Extraer entidades detectadas (solo PER para comparar con gold de personajes)
    # Normalizar a minúsculas para comparación (MARÍA = María = maría)
    detected = set()
    detected_original = {}  # Guardar forma original
    for ent in result.entities:
        if ent.label.value in ("PER",):  # Solo personajes
            text = ent.text.strip()
            text_lower = text.lower()
            detected.add(text_lower)
            detected_original[text_lower] = text

    # Calcular métricas (normalizado a minúsculas)
    gold_entities = set()
    gold_original = {}
    for ge in gold.entities:
        gold_entities.add(ge.name.lower())
        gold_original[ge.name.lower()] = ge.name
        for m in ge.mentions:
            gold_entities.add(m.lower())
            gold_original[m.lower()] = m

    true_positives = detected & gold_entities
    false_positives = detected - gold_entities
    false_negatives = gold_entities - detected

    # Convertir a formas originales para el reporte
    true_positives_orig = [detected_original.get(t, t) for t in true_positives]
    false_positives_orig = [detected_original.get(t, t) for t in false_positives]
    false_negatives_orig = [gold_original.get(t, t) for t in false_negatives]

    precision = len(true_positives) / len(detected) if detected else 0
    recall = len(true_positives) / len(gold_entities) if gold_entities else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # Información adicional de validación
    rejected_texts = [e.text for e in getattr(result, 'rejected_entities', [])]

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": true_positives_orig,
        "false_positives": false_positives_orig,
        "false_negatives": false_negatives_orig,
        "rejected_by_validator": rejected_texts[:20],  # Primeros 20 rechazados
        "total_rejected": len(rejected_texts),
        "validation_method": getattr(result, 'validation_method', 'N/A'),
    }


def evaluate_grammar_dequeismo(text: str, gold: GoldStandard, nlp) -> dict:
    """Evalúa precisión de detección de dequeísmo."""
    doc = nlp(text)

    # Detectar dequeísmos
    issues = check_dequeismo_spacy(doc)
    detected_texts = {issue.text.lower() for issue in issues}

    # Gold standard de dequeísmos
    gold_dequeismos = {
        ge.text.lower()
        for ge in gold.grammar_errors
        if ge.error_type == "dequeismo"
    }

    true_positives = detected_texts & gold_dequeismos
    false_positives = detected_texts - gold_dequeismos
    false_negatives = gold_dequeismos - detected_texts

    precision = len(true_positives) / len(detected_texts) if detected_texts else 1.0
    recall = len(true_positives) / len(gold_dequeismos) if gold_dequeismos else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": list(true_positives),
        "false_positives": list(false_positives),
        "false_negatives": list(false_negatives),
        "total_detected": len(detected_texts),
        "total_gold": len(gold_dequeismos),
    }


def evaluate_grammar_queismo(text: str, gold: GoldStandard, nlp) -> dict:
    """Evalúa precisión de detección de queísmo."""
    doc = nlp(text)

    # Detectar queísmos
    issues = check_queismo(doc)
    detected_texts = {issue.text.lower() for issue in issues}

    # Gold standard de queísmos
    gold_queismos = {
        ge.text.lower()
        for ge in gold.grammar_errors
        if ge.error_type == "queismo"
    }

    true_positives = detected_texts & gold_queismos
    false_positives = detected_texts - gold_queismos
    false_negatives = gold_queismos - detected_texts

    precision = len(true_positives) / len(detected_texts) if detected_texts else 1.0
    recall = len(true_positives) / len(gold_queismos) if gold_queismos else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": list(true_positives),
        "false_positives": list(false_positives),
        "false_negatives": list(false_negatives),
    }


def evaluate_fusion(text: str, gold: GoldStandard, nlp, embeddings_model) -> dict:
    """Evalúa precisión de fusión semántica con diferentes umbrales."""
    from narrative_assistant.entities.models import Entity, EntityType

    # Extraer entidades del texto
    doc = nlp(text)
    entities = [ent.text for ent in doc.ents if ent.label_ == "PER"]

    # Crear entidades Entity para usar con SemanticFusionService
    entity_objects = [
        Entity(id=i, canonical_name=name, entity_type=EntityType.CHARACTER)
        for i, name in enumerate(entities)
    ]

    results_by_threshold = {}

    for threshold in [0.65, 0.70, 0.75, 0.80, 0.82, 0.85, 0.88, 0.90]:
        service = SemanticFusionService(similarity_threshold=threshold)

        # Calcular similitudes
        suggested_fusions = []
        for i, e1 in enumerate(entity_objects):
            for e2 in entity_objects[i+1:]:
                try:
                    sim = service.compute_semantic_similarity(e1, e2)
                    if sim >= threshold:
                        suggested_fusions.append((e1.canonical_name, e2.canonical_name, sim))
                except Exception:
                    pass

        # Comparar con gold standard
        gold_pairs = set()
        for p1, p2 in gold.fusion_pairs:
            gold_pairs.add((p1.lower(), p2.lower()))
            gold_pairs.add((p2.lower(), p1.lower()))

        detected_pairs = set()
        for e1, e2, _ in suggested_fusions:
            detected_pairs.add((e1.lower(), e2.lower()))

        correct = sum(1 for p in detected_pairs if p in gold_pairs or (p[1], p[0]) in gold_pairs)

        precision = correct / len(detected_pairs) if detected_pairs else 1.0
        recall = correct / len(gold.fusion_pairs) if gold.fusion_pairs else 1.0

        results_by_threshold[threshold] = {
            "precision": precision,
            "recall": recall,
            "suggested_count": len(suggested_fusions),
            "correct_count": correct,
        }

    return results_by_threshold


def main():
    print("=" * 70)
    print("EVALUACIÓN DE PRECISIÓN DE MÉTODOS NLP")
    print("=" * 70)

    # Cargar modelos
    print("\n[1/4] Cargando modelos NLP...")
    nlp = load_spacy_model()
    print("  - spaCy cargado")

    embeddings = EmbeddingsModel()
    print("  - Embeddings cargados")

    # Cargar textos de prueba
    print("\n[2/4] Cargando textos de prueba...")
    base_path = Path(__file__).parent.parent / "test_books" / "evaluation_tests"

    text_inconsistencias = (base_path / "prueba_inconsistencias_personajes.txt").read_text(encoding="utf-8")
    text_errores = (base_path / "manuscrito_prueba_errores.txt").read_text(encoding="utf-8")

    print(f"  - prueba_inconsistencias_personajes.txt: {len(text_inconsistencias)} chars")
    print(f"  - manuscrito_prueba_errores.txt: {len(text_errores)} chars")

    # Evaluar NER
    print("\n[3/4] Evaluando NER...")
    print("-" * 50)

    ner_results = evaluate_ner(text_inconsistencias, GOLD_INCONSISTENCIAS, nlp)
    print(f"\nNER sobre prueba_inconsistencias_personajes.txt:")
    print(f"  Precision: {ner_results['precision']:.2%}")
    print(f"  Recall:    {ner_results['recall']:.2%}")
    print(f"  F1:        {ner_results['f1']:.2%}")
    print(f"  Metodo validacion: {ner_results.get('validation_method', 'N/A')}")
    print(f"\n  True positives: {ner_results['true_positives']}")
    fps = [str(x).encode('ascii', 'replace').decode() for x in ner_results['false_positives'][:10]]
    print(f"  False positives (10 primeros): {fps}")
    print(f"  Total false positives: {len(ner_results['false_positives'])}")
    print(f"  False negatives: {ner_results['false_negatives']}")
    print(f"  Entidades rechazadas por validador: {ner_results.get('total_rejected', 0)}")

    # Evaluar gramática
    print("\n[4/4] Evaluando Gramática...")
    print("-" * 50)

    print("\n--- DEQUEÍSMO ---")
    deq_results = evaluate_grammar_dequeismo(text_errores, GOLD_ERRORES_GRAMATICALES, nlp)
    print(f"  Precision: {deq_results['precision']:.2%}")
    print(f"  Recall:    {deq_results['recall']:.2%}")
    print(f"  F1:        {deq_results['f1']:.2%}")
    print(f"  Detectados: {deq_results['total_detected']}, Gold: {deq_results['total_gold']}")
    if deq_results['false_positives']:
        print(f"  Falsos positivos: {deq_results['false_positives']}")
    if deq_results['false_negatives']:
        print(f"  No detectados: {deq_results['false_negatives']}")

    print("\n--- QUEÍSMO ---")
    que_results = evaluate_grammar_queismo(text_errores, GOLD_ERRORES_GRAMATICALES, nlp)
    print(f"  Precision: {que_results['precision']:.2%}")
    print(f"  Recall:    {que_results['recall']:.2%}")
    print(f"  F1:        {que_results['f1']:.2%}")
    if que_results['false_positives']:
        print(f"  Falsos positivos: {que_results['false_positives']}")
    if que_results['false_negatives']:
        print(f"  No detectados: {que_results['false_negatives']}")

    # Evaluar fusión semántica
    print("\n--- FUSIÓN SEMÁNTICA (por umbral) ---")
    fusion_results = evaluate_fusion(text_inconsistencias, GOLD_INCONSISTENCIAS, nlp, embeddings)

    print(f"\n{'Umbral':<10} {'Precision':<12} {'Recall':<12} {'Sugeridas':<12} {'Correctas':<12}")
    print("-" * 58)
    for threshold, metrics in sorted(fusion_results.items()):
        print(f"{threshold:<10.2f} {metrics['precision']:<12.2%} {metrics['recall']:<12.2%} "
              f"{metrics['suggested_count']:<12} {metrics['correct_count']:<12}")

    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN Y RECOMENDACIONES")
    print("=" * 70)

    print("""
HALLAZGOS:

1. NER:
   - El modelo detecta más entidades de las necesarias (falsos positivos)
   - Verbos capitalizados pueden marcarse como entidades
   - RECOMENDACIÓN: Post-filtrar con análisis de POS-tag

2. DEQUEÍSMO:
   - La regla puede tener falsos positivos si no busca governing verb
   - RECOMENDACIÓN: Buscar hacia atrás en cadena de dependencias

3. QUEÍSMO:
   - Similar al dequeísmo, necesita contexto sintáctico completo
   - RECOMENDACIÓN: Verificar que el verbo regente requiere "de"

4. FUSIÓN SEMÁNTICA:
   - Umbral 0.65-0.75: Muchos falsos positivos
   - Umbral 0.82: Balance razonable
   - Umbral 0.88-0.90: Mejor precisión, menor recall
   - RECOMENDACIÓN: Umbral 0.85-0.88 para producción

CONFIGURABILIDAD RECOMENDADA:

OBLIGATORIO (no configurable):
- spaCy core NLP
- Algoritmos base de detección

CONFIGURABLE POR USUARIO:
- LLM (Ollama) - ON/OFF
- LanguageTool - ON/OFF
- Umbral de fusión semántica (0.80-0.95)
- Umbral de confianza mínima (0.3-0.7)
- Tipos de análisis por tipo de documento

PRESETS RECOMENDADOS:
- "Rápido": Sin LLM, sin LanguageTool, umbral alto
- "Balanceado": Sin LLM, con LanguageTool, umbral medio
- "Máxima precisión": Con LLM, con LanguageTool, umbral bajo
""")

    # Guardar resultados en JSON
    results = {
        "ner": ner_results,
        "dequeismo": deq_results,
        "queismo": que_results,
        "fusion_by_threshold": {str(k): v for k, v in fusion_results.items()},
    }

    output_path = Path(__file__).parent.parent / "docs" / "research" / "precision_results.json"
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"\nResultados guardados en: {output_path}")


if __name__ == "__main__":
    main()
