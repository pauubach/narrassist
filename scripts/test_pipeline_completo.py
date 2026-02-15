#!/usr/bin/env python
"""
Ejecuta la pipeline completa sobre documento_prueba_completo.txt
y compara las alertas detectadas contra ERRORES_INTENCIONADOS.md.
"""

import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from narrative_assistant.pipelines.unified_analysis import UnifiedAnalysisPipeline, UnifiedConfig

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
)
# Habilitar INFO para nuestros detectores
for mod in [
    "narrative_assistant.pipelines.ua_quality",
    "narrative_assistant.pipelines.ua_consistency",
    "narrative_assistant.pipelines.ua_alerts",
]:
    logging.getLogger(mod).setLevel(logging.INFO)

DOCUMENT = Path(__file__).parent.parent / "samples" / "documento_prueba_completo.txt"


def main():
    print(f"=== Pipeline completa: {DOCUMENT.name} ===\n")

    # Config con TODOS los detectores activados
    config = UnifiedConfig(
        run_structure=True,
        run_document_classification=True,
        run_dialogue_detection=True,
        run_ner=True,
        run_coreference=True,
        run_entity_fusion=True,
        run_attributes=True,
        run_relationships=True,
        run_interactions=True,
        run_knowledge=True,
        run_voice_profiles=True,
        run_spelling=True,
        run_grammar=True,
        run_lexical_repetitions=True,
        run_semantic_repetitions=True,
        run_coherence=True,
        run_register_analysis=True,
        run_sticky_sentences=True,
        run_sentence_energy=True,
        run_sensory_report=True,
        run_typography=True,
        run_pov_check=True,
        run_references_check=True,
        run_acronyms_check=True,
        run_temporal=True,
        run_focalization=True,
        run_voice_deviations=True,
        run_emotional=True,
        run_sentiment=True,
        run_pacing=True,
        run_consistency=True,
        run_temporal_consistency=True,
        run_vital_status=True,
        run_character_location=True,
        run_chekhov=True,
        create_alerts=True,
        run_character_profiling=True,
        run_network_analysis=True,
        run_anachronism_detection=True,
        run_ooc_detection=True,
        run_classical_spanish=True,
        run_name_variants=True,
        run_multi_model_voting=True,
        run_full_reports=True,
        min_confidence=0.3,
        use_llm=False,
        parallel_extraction=False,  # Secuencial para estabilidad
        max_workers=2,
        enable_memory_monitoring=False,  # Evitar saltarse fases por RAM
    )

    pipeline = UnifiedAnalysisPipeline(config)

    t0 = time.time()
    result = pipeline.analyze(
        document_path=DOCUMENT,
        project_name="Test Pipeline Completo",
    )
    elapsed = time.time() - t0

    if result.is_failure:
        print(f"ERROR: {result.error}")
        return 1

    report = result.value
    print(f"Tiempo: {elapsed:.1f}s\n")

    # --- Entidades ---
    entities = getattr(report, "entities", [])
    print(f"ENTIDADES: {len(entities)}")
    by_type = Counter()
    for e in entities:
        etype = getattr(e, "entity_type", None)
        if etype:
            etype = etype.value if hasattr(etype, "value") else str(etype)
        by_type[etype] += 1
    for t, c in by_type.most_common():
        print(f"  {t}: {c}")
    print()

    # Listar personajes
    persons = [e for e in entities if str(getattr(e, "entity_type", "")).replace("EntityType.", "") in ("PERSON", "person", "PER")]
    print(f"PERSONAJES ({len(persons)}):")
    for p in persons:
        name = getattr(p, "canonical_name", None) or getattr(p, "name", None) or getattr(p, "text", "?")
        print(f"  - {name}")
    print()

    # --- Alertas ---
    alerts = getattr(report, "alerts", [])
    print(f"ALERTAS TOTAL: {len(alerts)}\n")

    # Por categoría
    by_cat = Counter()
    for a in alerts:
        cat = getattr(a, "category", None)
        if cat:
            cat = cat.value if hasattr(cat, "value") else str(cat)
        by_cat[cat] += 1

    print("POR CATEGORÍA:")
    for cat, count in by_cat.most_common():
        print(f"  {cat}: {count}")
    print()

    # Por severidad
    by_sev = Counter()
    for a in alerts:
        sev = getattr(a, "severity", None)
        if sev:
            sev = sev.value if hasattr(sev, "value") else str(sev)
        by_sev[sev] += 1

    print("POR SEVERIDAD:")
    for sev, count in by_sev.most_common():
        print(f"  {sev}: {count}")
    print()

    # Por subcategoría / tipo
    by_subcat = Counter()
    for a in alerts:
        subcat = getattr(a, "subcategory", None) or getattr(a, "alert_type", None) or getattr(a, "type", None)
        if subcat:
            subcat = subcat.value if hasattr(subcat, "value") else str(subcat)
        by_subcat[subcat] += 1

    print("POR SUBCATEGORÍA / TIPO:")
    for sc, count in by_subcat.most_common():
        print(f"  {sc}: {count}")
    print()

    # Detalle de las primeras 50 alertas
    print("=" * 70)
    print("DETALLE DE ALERTAS (primeras 100):")
    print("=" * 70)
    for i, a in enumerate(alerts[:100]):
        cat = getattr(a, "category", "?")
        if hasattr(cat, "value"):
            cat = cat.value
        sev = getattr(a, "severity", "?")
        if hasattr(sev, "value"):
            sev = sev.value
        subcat = getattr(a, "subcategory", None) or getattr(a, "alert_type", None) or getattr(a, "type", None)
        if subcat and hasattr(subcat, "value"):
            subcat = subcat.value
        title = getattr(a, "title", "")
        desc = getattr(a, "description", "")
        chapter = getattr(a, "chapter_index", None) or getattr(a, "chapter", None)
        print(f"\n[{i+1}] [{sev}] {cat} / {subcat}")
        if chapter is not None:
            print(f"    Cap: {chapter}")
        print(f"    Título: {title}")
        if desc:
            print(f"    Desc: {desc[:200]}")

    # --- Comprobación contra ERRORES_INTENCIONADOS.md ---
    print("\n" + "=" * 70)
    print("CHECKLIST vs ERRORES_INTENCIONADOS.md")
    print("=" * 70)

    # Construir set de subcategorías detectadas
    detected_subcats = set()
    for a in alerts:
        sc = getattr(a, "subcategory", None) or getattr(a, "alert_type", None) or getattr(a, "type", None)
        if sc:
            detected_subcats.add(sc.value if hasattr(sc, "value") else str(sc))

    detected_cats = set()
    for a in alerts:
        cat = getattr(a, "category", None)
        if cat:
            detected_cats.add(cat.value if hasattr(cat, "value") else str(cat))

    # Categorías esperadas del ERRORES_INTENCIONADOS.md
    expected_checks = [
        ("Vital status (padre resucitado)", ["deceased_reappearance", "vital_status", "CONSISTENCY"]),
        ("Ubicación imposible (Lucía Madrid+BCN)", ["character_location", "location_impossibility", "WORLD"]),
        ("Conocimiento prematuro (Weber)", ["knowledge_anachronism", "KNOWLEDGE"]),
        ("Emoción-diálogo mismatch", ["emotional", "emotion_dialogue", "EMOTIONAL"]),
        ("OOC Carlos grita", ["out_of_character", "behavioral", "ooc", "BEHAVIORAL"]),
        ("Diálogos huérfanos", ["dialogue_orphan", "DIALOGUE"]),
        ("Contradicción edad Carlos", ["attribute_inconsistency", "CONSISTENCY"]),
        ("Name variant María Josefa", ["name_variant", "ENTITY", "ORTHOGRAPHY"]),
        ("Sticky sentences", ["sticky_sentence", "STYLE"]),
        ("Voz pasiva / baja energía", ["low_energy", "sentence_energy", "STYLE"]),
        ("Redundancia semántica", ["semantic_duplicate", "semantic_redundancy", "STYLE"]),
        ("Señales no lineales (flashback/forward)", ["non_linear", "prolepsis", "analepsis", "STRUCTURE"]),
        ("Chekhov (María Josefa)", ["chekhov", "STRUCTURE", "NARRATIVE"]),
        ("Cambio de registro", ["register_change", "register", "STYLE"]),
        ("Déficit sensorial", ["sensory", "low_sensory", "STYLE"]),
        ("Tipografía (guiones, espacios)", ["typography", "TYPOGRAPHY"]),
        ("Repeticiones léxicas", ["repetition", "STYLE", "REPETITION"]),
        ("Concordancia (segundo/segunda)", ["agreement", "GRAMMAR", "grammar"]),
        ("Dequeísmo / laísmo", ["grammar", "GRAMMAR"]),
        ("Anglicismos", ["anglicism", "STYLE"]),
        ("Muletillas (básicamente, realmente)", ["crutch", "filler", "STYLE"]),
        ("Variantes ortográficas (sicología/psicología)", ["orthographic_variant", "ORTHOGRAPHY"]),
        ("Anacoluto (frase sin verbo)", ["anacoluto", "GRAMMAR"]),
        ("POV cambio 1a/3a persona", ["pov", "POV", "FOCALIZATION"]),
        ("Variantes regionales (cogió/agarró)", ["regional", "STYLE"]),
        ("Referencias bibliográficas", ["reference", "REFERENCES"]),
        ("Siglas sin definir (PLN, IA/I.A.)", ["acronym", "ACRONYMS"]),
        ("Pacing (cap. 4 corto)", ["pacing", "PACING"]),
        ("Fillers (en realidad, o sea)", ["filler", "STYLE"]),
        ("Monotonía de longitud de frase", ["sentence_length_monotony", "monotony", "STYLE"]),
        ("Verbos débiles", ["weak_verb", "STYLE"]),
        ("Personajes planos", ["shallow", "unbalanced_cast", "archetype", "NARRATIVE"]),
        ("Atribución débil (dijo x15)", ["dialogue_weak", "attribution", "DIALOGUE"]),
        ("Interacción Elena-Lucía contradictoria", ["interaction", "BEHAVIORAL"]),
        ("Focalización (acceso mental Roberto)", ["focalization", "forbidden_mind", "FOCALIZATION"]),
        ("Omniscient leak (Carlos desde Múnich)", ["omniscient", "focalization", "FOCALIZATION"]),
        ("Inconsistencia temporal (3 fechas)", ["temporal_inconsistency", "temporal", "CONSISTENCY"]),
        ("Prolepsis/spoiler severo", ["prolepsis", "spoiler", "STRUCTURE"]),
        ("Duplicado exacto entre caps", ["duplicate", "STYLE"]),
        ("Rutina repetida (cap. 6)", ["duplicate", "near_paragraph", "STYLE"]),
        ("Cabello castaño vs rubio", ["attribute_inconsistency", "CONSISTENCY"]),
    ]

    found = 0
    missing = 0
    for desc, keywords in expected_checks:
        # Buscar si alguna keyword coincide con alguna subcategoría o categoría detectada
        all_detected = detected_subcats | detected_cats
        match = any(
            any(kw.lower() in det.lower() for det in all_detected)
            for kw in keywords
        )
        status = "OK" if match else "MISSING"
        if match:
            found += 1
        else:
            missing += 1
        print(f"  [{status}] {desc}")

    print(f"\n  RESULTADO: {found}/{found+missing} categorías detectadas")
    print(f"  Faltan: {missing} categorías")

    # --- Datos adicionales ---
    # Capítulos
    chapters = getattr(report, "chapters", [])
    print(f"\nCAPÍTULOS detectados: {len(chapters)}")
    for ch in chapters:
        title = getattr(ch, "title", None) or getattr(ch, "heading", None) or "?"
        print(f"  - {title}")

    # Errores no fatales
    errors = getattr(report, "errors", []) or getattr(report, "non_fatal_errors", [])
    if errors:
        print(f"\nERRORES NO FATALES: {len(errors)}")
        for e in errors[:10]:
            print(f"  - {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
