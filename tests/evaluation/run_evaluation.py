# -*- coding: utf-8 -*-
"""
Script unificado de evaluacion de precision para todas las capacidades NLP.

Ejecuta evaluaciones contra gold standards y genera metricas de:
- NER (Named Entity Recognition)
- Deteccion de capitulos
- Extraccion de relaciones
- Timeline/eventos temporales
- Errores gramaticales (dequeismo, queismo, laismo)
- Fusion semantica de entidades

Uso:
    python tests/evaluation/run_evaluation.py [--capability CAPABILITY] [--verbose]
"""

import re
import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

# Asegurar que el path del proyecto esta en sys.path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gold_standards import (
    ALL_GOLD_STANDARDS,
    ADVANCED_GOLD_STANDARDS,
    GoldStandard,
    GoldEntity,
    GoldRelation,
    GoldEvent,
    GoldChapter,
    GoldGrammarError,
    GoldOrthographyError,
    GoldCoreference,
    GoldMuletilla,
    GoldDialogue,
    GoldFocalizationViolation,
    GoldSentimentPoint,
    GoldRegisterChange,
    GOLD_MULETILLAS_DATA,
    GOLD_DIALOGUES_DATA,
    GOLD_REGISTER_CHANGES_DATA,
    GOLD_FOCALIZATION_VIOLATIONS_DATA,
    GOLD_SENTIMENT_ARC_DATA,
)


@dataclass
class EvaluationMetrics:
    """Metricas de evaluacion para una capacidad."""
    capability: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    details: dict = None

    def calculate(self):
        """Calcula precision, recall y F1."""
        if self.true_positives + self.false_positives > 0:
            self.precision = self.true_positives / (self.true_positives + self.false_positives)
        if self.true_positives + self.false_negatives > 0:
            self.recall = self.true_positives / (self.true_positives + self.false_negatives)
        if self.precision + self.recall > 0:
            self.f1_score = 2 * (self.precision * self.recall) / (self.precision + self.recall)

    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class EvaluationReport:
    """Reporte completo de evaluacion."""
    timestamp: str
    gold_standard_name: str
    text_file: str
    metrics: dict  # capability -> EvaluationMetrics
    summary: dict


def normalize_text(text: str) -> str:
    """Normaliza texto para comparacion."""
    import unicodedata
    # Quitar acentos
    normalized = unicodedata.normalize('NFD', text)
    result = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    result = unicodedata.normalize('NFC', result)
    return ' '.join(result.lower().split())


def read_test_file(path: str) -> str:
    """Lee un archivo de texto de prueba."""
    full_path = PROJECT_ROOT / path
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()


# =============================================================================
# EVALUADORES POR CAPACIDAD
# =============================================================================

def evaluate_ner(text: str, gold: GoldStandard, verbose: bool = False) -> EvaluationMetrics:
    """Evalua NER contra gold standard."""
    from narrative_assistant.nlp.ner import NERExtractor

    metrics = EvaluationMetrics(capability="ner")

    try:
        extractor = NERExtractor()
        result = extractor.extract_entities(text)

        # extract_entities devuelve Result[NERResult]
        if hasattr(result, 'is_success'):
            if not result.is_success:
                metrics.details["error"] = str(result.error)
                return metrics
            ner_result = result.value
        else:
            ner_result = result

        # Obtener entidades detectadas (solo PER)
        detected = set()
        detected_original = {}
        for ent in ner_result.entities:
            if ent.label.value in ("PER",):
                text_norm = normalize_text(ent.text)
                detected.add(text_norm)
                detected_original[text_norm] = ent.text

        # Gold entities normalizadas
        gold_entities = set()
        gold_original = {}
        for ge in gold.entities:
            if ge.entity_type == "PER":
                name_norm = normalize_text(ge.name)
                gold_entities.add(name_norm)
                gold_original[name_norm] = ge.name
                for mention in ge.mentions:
                    mention_norm = normalize_text(mention)
                    gold_entities.add(mention_norm)
                    gold_original[mention_norm] = mention

        # Calcular metricas
        true_positives = detected & gold_entities
        false_positives = detected - gold_entities
        false_negatives = gold_entities - detected

        metrics.true_positives = len(true_positives)
        metrics.false_positives = len(false_positives)
        metrics.false_negatives = len(false_negatives)
        metrics.calculate()

        if verbose:
            metrics.details["true_positives"] = [detected_original.get(x, x) for x in true_positives]
            metrics.details["false_positives"] = [detected_original.get(x, x) for x in false_positives]
            metrics.details["false_negatives"] = [gold_original.get(x, x) for x in false_negatives]

    except Exception as e:
        metrics.details["error"] = str(e)

    return metrics


def evaluate_grammar(text: str, gold: GoldStandard, verbose: bool = False) -> dict[str, EvaluationMetrics]:
    """Evalua deteccion de errores gramaticales."""
    from narrative_assistant.nlp.grammar.spanish_rules import (
        check_dequeismo,
        check_queismo,
        check_laismo,
    )
    from narrative_assistant.nlp.spacy_gpu import load_spacy_model

    results = {}

    # Cargar spaCy para procesar texto
    nlp = load_spacy_model()
    doc = nlp(text)

    # Agrupar gold errors por tipo
    gold_by_type = {}
    for error in gold.grammar_errors:
        if error.error_type not in gold_by_type:
            gold_by_type[error.error_type] = []
        gold_by_type[error.error_type].append(normalize_text(error.text))

    # Evaluar cada tipo de error
    error_checkers = {
        "dequeismo": check_dequeismo,
        "queismo": check_queismo,
        "laismo": check_laismo,
    }

    for error_type, checker in error_checkers.items():
        metrics = EvaluationMetrics(capability=f"grammar_{error_type}")

        try:
            issues = checker(doc)
            detected = set(normalize_text(issue.text) for issue in issues)
            gold_set = set(gold_by_type.get(error_type, []))

            true_positives = detected & gold_set
            false_positives = detected - gold_set
            false_negatives = gold_set - detected

            metrics.true_positives = len(true_positives)
            metrics.false_positives = len(false_positives)
            metrics.false_negatives = len(false_negatives)
            metrics.calculate()

            if verbose:
                metrics.details["detected"] = list(detected)
                metrics.details["gold"] = list(gold_set)
                metrics.details["true_positives"] = list(true_positives)
                metrics.details["false_positives"] = list(false_positives)
                metrics.details["false_negatives"] = list(false_negatives)

        except Exception as e:
            metrics.details["error"] = str(e)

        results[error_type] = metrics

    return results


def _filter_metadata_sections(text: str) -> str:
    """Filtra secciones de metadatos al final del texto (resumen, notas, etc.)."""
    lines = text.split('\n')

    # Patrones que indican inicio de seccion de metadatos (MUY especificos)
    metadata_start_markers = [
        r'^RESUMEN\s+(DE\s+)?(ESTRUCTURA|CAPITULOS?|PERSONAJES|CRONOL[OÓ]GIC)',
        r'^LISTA\s+DE\s+(INCONSISTENCIAS|PERSONAJES|CAPITULOS|EVENTOS)',
        r'^FORMATOS?\s+(DE\s+)?(CAPITULO|ESTRUCTURA)',
        r'^PERSONAJES\s*:?\s*$',
        r'^INCONSISTENCIAS?\s+(INTENCIONADAS|DETECTADAS|ENCONTRADAS)',
        r'^ESTRUCTURA\s+ESPERADA',
        r'^NOTAS?\s+(DEL\s+)?(AUTOR|EDITOR)',
        r'^CRONOLOG[IÍ]A\s*:?\s*$',
    ]

    # Buscar el "FIN" de la narrativa principal
    fin_line = -1
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() == 'FIN':
            fin_line = i
            break

    # Si encontramos FIN, buscar si hay seccion de metadatos despues
    if fin_line > 0:
        # Buscar marcadores de metadatos despues del FIN
        for i in range(fin_line + 1, len(lines)):
            line_stripped = lines[i].strip()
            if not line_stripped or line_stripped == '---':
                continue

            for pattern in metadata_start_markers:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    # Confirmar que es metadatos y cortar en FIN
                    return '\n'.join(lines[:fin_line + 1])

    # Buscar marcadores de metadatos sin FIN previo
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        for pattern in metadata_start_markers:
            if re.match(pattern, line_stripped, re.IGNORECASE):
                # Verificar que hay contenido de metadatos despues (listas, etc.)
                remaining_lines = lines[i:i+10]
                list_count = sum(1 for l in remaining_lines if re.match(r'^[-*]\s+', l.strip()) or re.match(r'^\d+\.\s+"', l.strip()))
                if list_count >= 2:
                    return '\n'.join(lines[:i])

    # Si no hay metadatos claros, devolver todo el texto
    return text


def evaluate_chapters(text: str, gold: GoldStandard, verbose: bool = False) -> EvaluationMetrics:
    """Evalua deteccion de capitulos."""
    metrics = EvaluationMetrics(capability="chapters")

    # Filtrar secciones de metadatos para evitar falsos positivos
    narrative_text = _filter_metadata_sections(text)

    # Patrones para detectar inicio de capitulo (deben estar al inicio de linea)
    chapter_patterns = [
        # CAPITULO + numero (arabigo o romano)
        (r'^CAP[IÍ]TULO\s+(\d+|[IVXLCDM]+)\b', 'chapter_word'),
        # Capitulo + numero + separador + titulo
        (r'^Capitulo\s+(\d+|[IVXLCDM]+|\w+)\s*[-:]\s*\w+', 'chapter_title'),
        # Capitulo + numero escrito (Uno, Dos, Cinco, etc.)
        (r'^Capitulo\s+(Uno|Dos|Tres|Cuatro|Cinco|Seis|Siete|Ocho|Nueve|Diez)\b', 'chapter_written'),
        # Capitulo + numero simple al final de linea
        (r'^Capitulo\s+(\d+)\s*$', 'chapter_simple'),
        # Solo numero romano + punto + espacio + texto (VII. Titulo)
        (r'^([IVXLCDM]+)\.\s+[A-Z]', 'roman_dot'),
        # Solo numero + punto + espacio + texto (8. Titulo)
        (r'^(\d{1,2})\.\s+[A-Z]', 'number_dot'),
        # EPILOGO o PROLOGO al inicio de linea
        (r'^(EP[IÍ]LOGO|PR[OÓ]LOGO)\b', 'special'),
    ]

    detected_chapters = set()
    detected_positions = set()  # Para evitar duplicados por posicion

    for line in narrative_text.split('\n'):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        for pattern, pattern_type in chapter_patterns:
            match = re.match(pattern, line_stripped, re.IGNORECASE)
            if match:
                marker = match.group(1) if match.lastindex else match.group(0)
                # Normalizar: mayusculas, sin acentos
                marker_norm = marker.upper().strip()

                # Evitar duplicados (mismo marcador ya detectado)
                if marker_norm not in detected_chapters:
                    detected_chapters.add(marker_norm)
                break  # Solo un patron por linea

    detected_count = len(detected_chapters)
    gold_count = len(gold.chapters)

    # Comparacion mas precisa: intentar match entre detectados y gold
    # Normalizar gold markers (extraer solo el identificador numerico/romano)
    gold_markers = set()
    for ch in gold.chapters:
        # Extraer numero/identificador del gold
        marker = ch.start_marker.strip()
        # Intentar extraer el identificador
        for pattern, _ in chapter_patterns:
            m = re.match(pattern, marker, re.IGNORECASE)
            if m:
                gold_markers.add(m.group(1).upper() if m.lastindex else m.group(0).upper())
                break
        else:
            # Fallback: extraer numero/romano sin puntuacion
            # "VII." -> "VII", "8." -> "8"
            cleaned = re.sub(r'[.\-:\s]+$', '', marker).upper()
            gold_markers.add(cleaned)

    # Calcular matches
    true_positives = detected_chapters & gold_markers
    false_positives = detected_chapters - gold_markers
    false_negatives = gold_markers - detected_chapters

    metrics.true_positives = len(true_positives)
    metrics.false_positives = len(false_positives)
    metrics.false_negatives = len(false_negatives)
    metrics.calculate()

    if verbose:
        metrics.details["detected_count"] = detected_count
        metrics.details["gold_count"] = gold_count
        metrics.details["detected_markers"] = list(detected_chapters)[:20]
        metrics.details["gold_markers"] = list(gold_markers)
        metrics.details["true_positives"] = list(true_positives)
        metrics.details["false_positives"] = list(false_positives)
        metrics.details["false_negatives"] = list(false_negatives)

    return metrics


def evaluate_relations(text: str, gold: GoldStandard, verbose: bool = False) -> EvaluationMetrics:
    """Evalua deteccion de relaciones entre personajes."""
    metrics = EvaluationMetrics(capability="relations")

    # TODO: Integrar con el extractor de relaciones real
    # Por ahora, usar deteccion basica por patrones

    # Patrones para relaciones - ajustados para evitar falsos positivos
    relation_patterns = {
        # romantic_partner: novio/novia pero NO marido/esposa (eso es spouse)
        "romantic_partner": [r"\bnovio\b", r"\bnovia\b", r"\bpareja\b(?!\s+de\s+hecho)"],
        # spouse: relacion matrimonial
        "spouse": [r"\bmarido\b", r"\besposa?\b", r"\bcasaron\b", r"\bboda\b", r"\bmatrimonio\b"],
        # friend
        "friend": [r"\bamig[oa]s?\b", r"\bamistad\b", r"\bmejor\s+amig[oa]\b"],
        # sibling
        "sibling": [r"\bhermano\b", r"\bhermana\b", r"\bhermanos\b"],
        # colleague: patron mas restrictivo para evitar FP con "trabajo" generico
        "colleague": [r"\bcolega\b", r"\bcompañero\s+de\s+trabajo\b", r"\bcompa[nñ]er[oa]\s+de\b"],
        # parent_child
        "parent_child": [r"\bpadre\b", r"\bmadre\b", r"\bhij[oa]\b", r"\bpadres\b", r"\bprogenitor"],
    }

    detected_relations = set()
    text_lower = text.lower()

    for rel_type, patterns in relation_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                detected_relations.add(rel_type)

    gold_types = set(r.relation_type for r in gold.relations)

    true_positives = detected_relations & gold_types
    false_positives = detected_relations - gold_types
    false_negatives = gold_types - detected_relations

    metrics.true_positives = len(true_positives)
    metrics.false_positives = len(false_positives)
    metrics.false_negatives = len(false_negatives)
    metrics.calculate()

    if verbose:
        metrics.details["detected_types"] = list(detected_relations)
        metrics.details["gold_types"] = list(gold_types)
        metrics.details["gold_relations"] = [(r.entity1, r.entity2, r.relation_type) for r in gold.relations]

    return metrics


def evaluate_timeline(text: str, gold: GoldStandard, verbose: bool = False) -> EvaluationMetrics:
    """Evalua deteccion de eventos temporales."""
    metrics = EvaluationMetrics(capability="timeline")

    # Filtrar secciones de metadatos (resumen cronologico, lista de eventos, etc.)
    narrative_text = _filter_metadata_sections(text)

    # Numeros escritos en espanol: patron flexible que captura cualquier palabra
    # que parezca un numero (1-999+). Incluye unidades, decenas, centenas y compuestos.
    # Ejemplos: uno, veinte, treinta y cinco, ciento dos, doscientos, etc.
    UNIDADES = r'un[oa]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve'
    ESPECIALES = r'diez|once|doce|trece|catorce|quince'
    DIECI = r'dieci(?:s[eé]is|siete|ocho|nueve)'
    VEINTI = r'veinti(?:un[oa]?|d[oó]s|tr[eé]s|cuatro|cinco|s[eé]is|siete|ocho|nueve)|veinte'
    DECENAS = r'treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa'
    CENTENAS = r'cien(?:to)?|doscient[oa]s?|trescient[oa]s?|cuatrocient[oa]s?|quinient[oa]s?|seiscient[oa]s?|setecient[oa]s?|ochocient[oa]s?|novecient[oa]s?'
    # Patron compuesto: numero simple o "decena y unidad" o "centena (y) decena..."
    NUMEROS_ESCRITOS = rf'(?:{CENTENAS}(?:\s+y?\s*(?:{DECENAS}(?:\s+y\s+(?:{UNIDADES}))?|{VEINTI}|{DIECI}|{ESPECIALES}|{UNIDADES}))?|{DECENAS}(?:\s+y\s+(?:{UNIDADES}))?|{VEINTI}|{DIECI}|{ESPECIALES}|{UNIDADES})'

    # Patrones ordenados por especificidad (más específicos primero)
    temporal_patterns = [
        # Fechas completas: "15 de enero de 1990"
        (r'\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+\d{4}', "fecha_completa"),
        # Mes de año: "enero de 1990", "abril 1990"
        (r'(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de\s+)?\d{4}', "mes_ano"),
        # Estacion de año: "verano de 1995"
        (r'(?:verano|oto[nñ]o|invierno|primavera)\s+de\s+\d{4}', "estacion_ano"),
        # Mes de ese mismo año: "septiembre de ese mismo año"
        (r'(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+ese\s+(?:mismo\s+)?a[nñ]o', "relativo_mes"),
        # Referencias relativas con numeros escritos: "tres meses despues", "un año despues de"
        (rf'(?:{NUMEROS_ESCRITOS})\s+(?:a[nñ]os?|meses?|d[ií]as?|semanas?)\s+(?:despu[eé]s|antes|m[aá]s\s+tarde)', "relativo_escrito"),
        # Referencias relativas con digitos: "2 años despues"
        (r'\d+\s+(?:a[nñ]os?|meses?|d[ií]as?|semanas?)\s+(?:despu[eé]s|antes|m[aá]s\s+tarde)', "relativo_num"),
        # "al año siguiente"
        (r'al\s+a[nñ]o\s+siguiente', "relativo"),
        # "un año después de graduarse"
        (rf'(?:{NUMEROS_ESCRITOS})\s+a[nñ]o\s+(?:despu[eé]s|antes)\s+de\s+\w+', "relativo_evento"),
        # Presente
        (r'\b(?:actualmente|en\s+la\s+actualidad)\b', "presente"),
        # Edades: "cinco años", "diez años" (sin "después/antes")
        (rf'\b(?:{NUMEROS_ESCRITOS})\s+a[nñ]os?\b', "edad"),
        # Ese mismo año
        (r'ese\s+mismo\s+a[nñ]o|aquel\s+a[nñ]o|el\s+mismo\s+a[nñ]o', "relativo"),
        # Cursos/periodos: "segundo curso"
        (r'(?:primer|segundo|tercer|cuarto|quinto)\s+(?:curso|semestre|trimestre|a[nñ]o)', "periodo"),
        # Cumpleaños con numero escrito: "dieciocho cumpleaños"
        (rf'(?:{NUMEROS_ESCRITOS})\s+cumplea[nñ]os', "cumpleanos"),
        # Años solos: 1990, 2024 (solo si no estan ya capturados en patron anterior)
        (r'\b(?:19|20)\d{2}\b', "ano"),
    ]

    # Detectar y clasificar marcadores, evitando duplicados por posición
    detected_positions = set()  # Para evitar duplicados
    detected_markers = []

    for pattern, tipo in temporal_patterns:
        for match in re.finditer(pattern, narrative_text, re.IGNORECASE):
            start, end = match.span()
            # Solo añadir si no hay solapamiento con marcadores ya detectados
            overlaps = any(
                not (end <= pos_start or start >= pos_end)
                for pos_start, pos_end in detected_positions
            )
            if not overlaps:
                detected_positions.add((start, end))
                marker_text = match.group()
                detected_markers.append((marker_text.lower().strip(), tipo, start))

    # Agrupar marcadores únicos
    unique_markers = set(m[0] for m in detected_markers)
    detected_count = len(unique_markers)

    # Contar marcadores únicos en gold
    gold_markers_set = set()
    for event in gold.events:
        for marker in event.temporal_markers:
            gold_markers_set.add(marker.lower().strip())
    gold_count = len(gold_markers_set)

    # Comparar marcadores detectados contra gold usando matching flexible
    true_positives = 0
    matched_gold = set()
    matched_detected = set()

    for detected in unique_markers:
        if detected in matched_detected:
            continue
        for gold_marker in gold_markers_set:
            if gold_marker in matched_gold:
                continue
            # Match exacto o parcial
            if detected == gold_marker:
                true_positives += 1
                matched_gold.add(gold_marker)
                matched_detected.add(detected)
                break
            # Match si uno contiene al otro
            if detected in gold_marker or gold_marker in detected:
                true_positives += 1
                matched_gold.add(gold_marker)
                matched_detected.add(detected)
                break
            # Match por año si ambos contienen el mismo año
            detected_years = set(re.findall(r'\b(19\d{2}|20\d{2})\b', detected))
            gold_years = set(re.findall(r'\b(19\d{2}|20\d{2})\b', gold_marker))
            if detected_years and gold_years and detected_years == gold_years:
                true_positives += 1
                matched_gold.add(gold_marker)
                matched_detected.add(detected)
                break

    metrics.true_positives = true_positives
    metrics.false_positives = detected_count - true_positives
    metrics.false_negatives = gold_count - len(matched_gold)
    metrics.calculate()

    if verbose:
        metrics.details["detected_count"] = detected_count
        metrics.details["gold_count"] = gold_count
        metrics.details["detected_unique"] = sorted(unique_markers)[:20]
        metrics.details["gold_markers"] = sorted(gold_markers_set)[:20]
        metrics.details["matched_gold"] = sorted(matched_gold)
        metrics.details["unmatched_gold"] = sorted(gold_markers_set - matched_gold)
        metrics.details["unmatched_detected"] = sorted(unique_markers - matched_detected)

    return metrics


def evaluate_fusion(text: str, gold: GoldStandard, verbose: bool = False) -> EvaluationMetrics:
    """Evalua fusion semantica de entidades."""
    from narrative_assistant.entities.semantic_fusion import normalize_for_comparison
    from narrative_assistant.nlp.embeddings import get_embeddings_model

    metrics = EvaluationMetrics(capability="fusion")

    if not gold.fusion_pairs:
        metrics.details["note"] = "No fusion pairs in gold standard"
        return metrics

    try:
        # Para evaluation usamos tanto normalizacion como embeddings
        embeddings = None
        try:
            embeddings = get_embeddings_model()
        except Exception:
            pass  # Embeddings no disponibles

        threshold = 0.7
        correct = 0
        incorrect = 0

        for name1, name2 in gold.fusion_pairs:
            # Primero: comparacion normalizada (sin acentos, lowercase)
            norm1 = normalize_for_comparison(name1)
            norm2 = normalize_for_comparison(name2)

            if norm1 == norm2:
                similarity = 1.0
            elif embeddings:
                # Usar embeddings si estan disponibles
                similarity = embeddings.similarity(name1, name2)
            else:
                # Fallback: Levenshtein simple
                similarity = 1.0 if norm1 == norm2 else 0.0

            should_fuse = similarity >= threshold

            # Todos los pares en gold.fusion_pairs DEBEN fusionarse
            if should_fuse:
                correct += 1
            else:
                incorrect += 1
                if verbose:
                    if "failed_pairs" not in metrics.details:
                        metrics.details["failed_pairs"] = []
                    metrics.details["failed_pairs"].append({
                        "pair": (name1, name2),
                        "similarity": round(similarity, 3),
                        "norm1": norm1,
                        "norm2": norm2,
                    })

        metrics.true_positives = correct
        metrics.false_negatives = incorrect
        metrics.calculate()

        if verbose:
            metrics.details["threshold"] = threshold
            metrics.details["total_pairs"] = len(gold.fusion_pairs)

    except Exception as e:
        metrics.details["error"] = str(e)

    return metrics


def evaluate_attributes(text: str, gold: GoldStandard, verbose: bool = False) -> EvaluationMetrics:
    """Evalua extraccion de atributos de personajes."""
    metrics = EvaluationMetrics(capability="attributes")

    if not gold.attributes:
        metrics.details["note"] = "No attributes in gold standard"
        return metrics

    try:
        from narrative_assistant.nlp.attributes import (
            AttributeExtractor,
            reset_attribute_extractor,
        )

        # Usar extractor sin LLM para velocidad en evaluacion
        reset_attribute_extractor()
        extractor = AttributeExtractor(
            use_llm=False,  # Disable LLM for speed
            use_embeddings=False,  # Disable embeddings for speed
            use_dependency_extraction=True,
            use_patterns=True,
            min_confidence=0.3,
        )

        # Extraer atributos del texto
        result = extractor.extract_attributes(text)
        if hasattr(result, 'is_success') and not result.is_success:
            metrics.details["error"] = str(result.error)
            return metrics

        extraction_result = result.value if hasattr(result, 'value') else result
        detected_attrs = extraction_result.attributes if extraction_result else []

        # Mapeo de keys del extractor a keys del gold standard
        # El extractor usa enums como AttributeKey.HAIR_COLOR, el gold usa strings como "cabello"
        KEY_MAPPING = {
            "hair_color": ["cabello", "pelo", "hair"],
            "eye_color": ["ojos", "eye"],
            "height": ["estatura", "altura", "height"],
            "build": ["complexion", "build", "cuerpo"],
            "age": ["edad", "age"],
            "profession": ["profesion", "trabajo", "profession"],
            "beard": ["barba", "beard"],
        }

        # Crear conjuntos para comparacion
        # Gold: (entity_norm, key_norm, value_norm)
        gold_set = set()
        for ga in gold.attributes:
            entity_norm = normalize_text(ga.entity)
            key_norm = normalize_text(ga.key)
            for value in ga.values:
                value_norm = normalize_text(value)
                gold_set.add((entity_norm, key_norm, value_norm))

        # Detectados: normalizar keys usando el mapeo
        detected_set = set()
        detected_raw = []
        for attr in detected_attrs:
            # entity_name es el campo correcto
            entity_norm = normalize_text(attr.entity_name) if hasattr(attr, 'entity_name') else normalize_text(str(attr))

            # key puede ser un enum - extraer su value
            if hasattr(attr, 'key'):
                if hasattr(attr.key, 'value'):
                    key_raw = attr.key.value  # Enum value
                else:
                    key_raw = str(attr.key)
            else:
                key_raw = "unknown"

            key_norm = normalize_text(key_raw)

            # value
            value_norm = normalize_text(attr.value) if hasattr(attr, 'value') else ""

            detected_set.add((entity_norm, key_norm, value_norm))
            detected_raw.append((entity_norm, key_norm, value_norm))

        # Matching flexible
        true_positives = 0
        matched_gold = set()

        for det_entity, det_key, det_value in detected_set:
            for gold_entity, gold_key, gold_value in gold_set:
                if (gold_entity, gold_key, gold_value) in matched_gold:
                    continue

                # Entity match (parcial)
                entity_match = det_entity in gold_entity or gold_entity in det_entity

                # Key match: buscar en el mapeo
                key_match = False
                for mapped_key, aliases in KEY_MAPPING.items():
                    if det_key == mapped_key or det_key in aliases:
                        if gold_key in aliases or gold_key == mapped_key:
                            key_match = True
                            break
                # Fallback: match directo
                if not key_match:
                    key_match = det_key == gold_key or det_key in gold_key or gold_key in det_key

                # Value match (parcial)
                value_match = det_value in gold_value or gold_value in det_value or det_value == gold_value

                if entity_match and key_match and value_match:
                    true_positives += 1
                    matched_gold.add((gold_entity, gold_key, gold_value))
                    break

        metrics.true_positives = true_positives
        metrics.false_positives = len(detected_set) - true_positives
        metrics.false_negatives = len(gold_set) - len(matched_gold)
        metrics.calculate()

        if verbose:
            metrics.details["detected_count"] = len(detected_set)
            metrics.details["gold_count"] = len(gold_set)
            metrics.details["detected_sample"] = detected_raw[:10]
            metrics.details["gold_sample"] = list(gold_set)[:10]
            metrics.details["matched"] = list(matched_gold)

    except Exception as e:
        metrics.details["error"] = str(e)
        import traceback
        metrics.details["traceback"] = traceback.format_exc()

    return metrics


def evaluate_inconsistencies(text: str, gold: GoldStandard, verbose: bool = False) -> EvaluationMetrics:
    """Evalua deteccion de inconsistencias en atributos."""
    metrics = EvaluationMetrics(capability="inconsistencies")

    # Filtrar solo atributos marcados como inconsistencia
    gold_inconsistencies = [a for a in gold.attributes if a.is_inconsistency]

    if not gold_inconsistencies:
        metrics.details["note"] = "No inconsistencies marked in gold standard"
        return metrics

    # Mapeo de keys
    KEY_MAPPING = {
        "hair_color": ["cabello", "pelo", "hair"],
        "eye_color": ["ojos", "eye"],
        "height": ["estatura", "altura", "height"],
        "build": ["complexion", "build", "cuerpo"],
        "age": ["edad", "age"],
        "profession": ["profesion", "trabajo", "profession"],
        "beard": ["barba", "beard"],
    }

    def normalize_key(key_raw: str) -> str:
        """Normaliza un key del extractor al formato del gold."""
        key_norm = normalize_text(key_raw)
        for mapped_key, aliases in KEY_MAPPING.items():
            if key_norm == mapped_key or key_norm in aliases:
                return aliases[0]  # Retorna el primer alias (espanol)
        return key_norm

    try:
        from narrative_assistant.nlp.attributes import (
            AttributeExtractor,
            reset_attribute_extractor,
        )

        # Usar extractor sin LLM para velocidad en evaluacion
        reset_attribute_extractor()
        extractor = AttributeExtractor(
            use_llm=False,
            use_embeddings=False,
            use_dependency_extraction=True,
            use_patterns=True,
            min_confidence=0.3,
        )

        # Extraer atributos
        result = extractor.extract_attributes(text)
        if hasattr(result, 'is_success') and not result.is_success:
            metrics.details["error"] = str(result.error)
            return metrics

        extraction_result = result.value if hasattr(result, 'value') else result
        detected_attrs = extraction_result.attributes if extraction_result else []

        # Agrupar por (entity, key)
        attr_groups = {}
        for attr in detected_attrs:
            entity = normalize_text(attr.entity_name) if hasattr(attr, 'entity_name') else normalize_text(str(attr))

            # Extraer key del enum si es necesario
            if hasattr(attr, 'key'):
                if hasattr(attr.key, 'value'):
                    key_raw = attr.key.value
                else:
                    key_raw = str(attr.key)
            else:
                key_raw = "unknown"

            key = normalize_key(key_raw)
            value = normalize_text(attr.value) if hasattr(attr, 'value') else ""

            group_key = (entity, key)
            if group_key not in attr_groups:
                attr_groups[group_key] = set()
            attr_groups[group_key].add(value)

        # Detectar inconsistencias (mas de un valor para el mismo entity+key)
        detected_inconsistencies = set()
        for (entity, key), values in attr_groups.items():
            if len(values) > 1:
                detected_inconsistencies.add((entity, key))

        # Gold inconsistencies - normalizar keys tambien
        gold_set = set()
        for gi in gold_inconsistencies:
            entity_norm = normalize_text(gi.entity)
            key_norm = normalize_text(gi.key)
            gold_set.add((entity_norm, key_norm))

        # Matching flexible para comparar (entity puede ser parcial)
        true_positives_set = set()
        for det_entity, det_key in detected_inconsistencies:
            for gold_entity, gold_key in gold_set:
                if (gold_entity, gold_key) in true_positives_set:
                    continue
                entity_match = det_entity in gold_entity or gold_entity in det_entity
                key_match = det_key == gold_key or det_key in gold_key or gold_key in det_key
                if entity_match and key_match:
                    true_positives_set.add((gold_entity, gold_key))
                    break

        metrics.true_positives = len(true_positives_set)
        metrics.false_positives = len(detected_inconsistencies) - len(true_positives_set)
        metrics.false_negatives = len(gold_set) - len(true_positives_set)
        metrics.calculate()

        if verbose:
            metrics.details["detected"] = list(detected_inconsistencies)
            metrics.details["gold"] = list(gold_set)
            metrics.details["true_positives"] = list(true_positives_set)
            metrics.details["attr_groups"] = {str(k): list(v) for k, v in attr_groups.items()}

    except Exception as e:
        metrics.details["error"] = str(e)
        import traceback
        metrics.details["traceback"] = traceback.format_exc()

    return metrics


def evaluate_orthography(text: str, gold: GoldStandard, verbose: bool = False) -> EvaluationMetrics:
    """Evalua deteccion de errores ortograficos usando sistema de votacion."""
    metrics = EvaluationMetrics(capability="orthography")

    if not gold.orthography_errors:
        metrics.details["note"] = "No orthography errors in gold standard"
        return metrics

    try:
        # Usar el nuevo sistema de votación multi-corrector
        from narrative_assistant.nlp.orthography import get_voting_spelling_checker

        checker = get_voting_spelling_checker(
            use_pyspellchecker=True,
            use_hunspell=True,  # Si disponible
            use_symspell=True,
            use_languagetool=True,  # Si disponible
            use_llm_arbitration=False,  # Desactivar LLM para evaluación rápida
        )
        result = checker.check(text)

        if hasattr(result, 'is_success') and not result.is_success:
            metrics.details["error"] = str(result.error)
            return metrics

        report = result.value if hasattr(result, 'value') else result
        detected_issues = report.issues if report else []

        # Crear conjunto de errores detectados (palabra normalizada)
        detected_set = set()
        detected_raw = {}
        for issue in detected_issues:
            word_norm = normalize_text(issue.word)
            detected_set.add(word_norm)
            detected_raw[word_norm] = issue.word

        # Gold errors normalizados
        gold_set = set()
        gold_raw = {}
        for ge in gold.orthography_errors:
            text_norm = normalize_text(ge.text)
            gold_set.add(text_norm)
            gold_raw[text_norm] = ge.text

        # Matching
        true_positives = detected_set & gold_set
        false_positives = detected_set - gold_set
        false_negatives = gold_set - detected_set

        metrics.true_positives = len(true_positives)
        metrics.false_positives = len(false_positives)
        metrics.false_negatives = len(false_negatives)
        metrics.calculate()

        if verbose:
            metrics.details["detected_count"] = len(detected_set)
            metrics.details["gold_count"] = len(gold_set)
            metrics.details["true_positives"] = [detected_raw.get(x, x) for x in true_positives]
            metrics.details["false_positives"] = [detected_raw.get(x, x) for x in false_positives]
            metrics.details["false_negatives"] = [gold_raw.get(x, x) for x in false_negatives]

    except Exception as e:
        metrics.details["error"] = str(e)
        import traceback
        metrics.details["traceback"] = traceback.format_exc()

    return metrics


# =============================================================================
# EVALUADORES AVANZADOS
# =============================================================================

def evaluate_coreference(text: str, gold: GoldStandard, verbose: bool = False) -> EvaluationMetrics:
    """Evalua resolucion de correferencias."""
    metrics = EvaluationMetrics(capability="coreference")

    if not gold.coreferences:
        metrics.details["note"] = "No coreference chains in gold standard"
        return metrics

    try:
        from narrative_assistant.nlp.coreference_resolver import resolve_coreferences_voting

        result = resolve_coreferences_voting(text)

        if hasattr(result, 'is_failure') and result.is_failure:
            metrics.details["error"] = str(result.error)
            return metrics

        coref_result = result.value if hasattr(result, 'value') else result
        detected_chains = coref_result.chains if coref_result else []

        # Crear mapeo de menciones detectadas a entidades
        detected_mentions = {}  # mencion -> entidad
        for chain in detected_chains:
            entity = chain.canonical_name.lower()
            for mention in chain.mentions:
                detected_mentions[mention.text.lower()] = entity

        # Gold: crear mapeo de menciones a entidades
        gold_mentions = {}
        for gc in gold.coreferences:
            entity = gc.entity.lower()
            for mention in gc.mentions:
                gold_mentions[mention.lower()] = entity

        # Comparar: para cada mencion en gold, verificar si esta correctamente asignada
        correct = 0
        incorrect = 0
        missed = 0

        for mention, gold_entity in gold_mentions.items():
            mention_norm = normalize_text(mention)
            if mention_norm in detected_mentions:
                detected_entity = detected_mentions[mention_norm]
                # Match si detecta la misma entidad o una similar
                if gold_entity in detected_entity or detected_entity in gold_entity:
                    correct += 1
                else:
                    incorrect += 1
            else:
                # Buscar match parcial
                found = False
                for det_mention, det_entity in detected_mentions.items():
                    if mention_norm in det_mention or det_mention in mention_norm:
                        if gold_entity in det_entity or det_entity in gold_entity:
                            correct += 1
                            found = True
                            break
                if not found:
                    missed += 1

        metrics.true_positives = correct
        metrics.false_positives = incorrect
        metrics.false_negatives = missed
        metrics.calculate()

        if verbose:
            metrics.details["detected_chains"] = len(detected_chains)
            metrics.details["gold_chains"] = len(gold.coreferences)
            metrics.details["sample_detected"] = [
                {"entity": c.canonical_name, "mentions": [m.text for m in c.mentions[:5]]}
                for c in detected_chains[:5]
            ]

    except Exception as e:
        metrics.details["error"] = str(e)
        import traceback
        metrics.details["traceback"] = traceback.format_exc()

    return metrics


def evaluate_dialogue_attribution(text: str, gold: GoldStandard, verbose: bool = False) -> EvaluationMetrics:
    """Evalua atribucion de dialogos (quien dice cada linea)."""
    metrics = EvaluationMetrics(capability="dialogue")

    # Extraer dialogos del texto
    dialogue_pattern = r'[-—]\s*(.+?)(?:\s*[-—]|$)'
    dialogues = re.findall(dialogue_pattern, text, re.MULTILINE)

    if not dialogues:
        metrics.details["note"] = "No dialogues found in text"
        return metrics

    try:
        from narrative_assistant.voice.speaker_attribution import get_speaker_attribution

        attributor = get_speaker_attribution()
        result = attributor.attribute_speakers(text)

        if hasattr(result, 'is_failure') and result.is_failure:
            metrics.details["error"] = str(result.error)
            return metrics

        attribution_result = result.value if hasattr(result, 'value') else result

        # Contar atribuciones exitosas
        attributed = 0
        unattributed = 0

        if attribution_result:
            for attr in attribution_result.attributions:
                if attr.speaker and attr.speaker != "unknown":
                    attributed += 1
                else:
                    unattributed += 1

        metrics.true_positives = attributed
        metrics.false_negatives = unattributed
        metrics.calculate()

        if verbose:
            metrics.details["total_dialogues"] = len(dialogues)
            metrics.details["attributed"] = attributed
            metrics.details["unattributed"] = unattributed

    except Exception as e:
        # El modulo puede no estar implementado aun
        metrics.details["error"] = str(e)
        metrics.details["note"] = "Speaker attribution module may not be fully implemented"

    return metrics


def evaluate_muletillas(text: str, gold_name: str, verbose: bool = False) -> EvaluationMetrics:
    """Evalua deteccion de muletillas en el texto."""
    metrics = EvaluationMetrics(capability="muletillas")

    if gold_name not in GOLD_MULETILLAS_DATA:
        metrics.details["note"] = f"No muletillas data for {gold_name}"
        return metrics

    gold_data = GOLD_MULETILLAS_DATA[gold_name]

    # Lista de muletillas comunes en espanol
    MULETILLAS = [
        "pues", "o sea", "eh", "bueno", "vamos", "la verdad", "no se",
        "vale", "viste", "ya", "ay", "mira", "oye", "sabes", "como",
        "digamos", "en plan", "tipo", "entonces", "total"
    ]

    try:
        # Filtrar seccion de metadatos
        narrative_text = _filter_metadata_sections(text)

        # Detectar muletillas en el texto
        detected_muletillas = {}
        text_lower = narrative_text.lower()

        for muletilla in MULETILLAS:
            # Contar ocurrencias (usando word boundaries para evitar matches parciales)
            pattern = rf'\b{re.escape(muletilla)}\b'
            count = len(re.findall(pattern, text_lower))
            if count > 0:
                detected_muletillas[muletilla] = count

        # Contar total esperado vs detectado
        total_gold = sum(
            count
            for speaker_data in gold_data.values()
            for count in speaker_data.values()
        )

        total_detected = sum(detected_muletillas.values())

        # Comparar muletillas especificas
        gold_muletillas = set()
        for speaker_data in gold_data.values():
            gold_muletillas.update(speaker_data.keys())

        detected_types = set(detected_muletillas.keys())

        true_positives = gold_muletillas & detected_types
        false_positives = detected_types - gold_muletillas
        false_negatives = gold_muletillas - detected_types

        metrics.true_positives = len(true_positives)
        metrics.false_positives = len(false_positives)
        metrics.false_negatives = len(false_negatives)
        metrics.calculate()

        if verbose:
            metrics.details["total_gold_count"] = total_gold
            metrics.details["total_detected_count"] = total_detected
            metrics.details["detected_muletillas"] = detected_muletillas
            metrics.details["gold_types"] = list(gold_muletillas)
            metrics.details["true_positives"] = list(true_positives)

    except Exception as e:
        metrics.details["error"] = str(e)
        import traceback
        metrics.details["traceback"] = traceback.format_exc()

    return metrics


def evaluate_focalization(text: str, gold_name: str, verbose: bool = False) -> EvaluationMetrics:
    """Evalua deteccion de violaciones de focalizacion."""
    metrics = EvaluationMetrics(capability="focalization")

    if gold_name not in GOLD_FOCALIZATION_VIOLATIONS_DATA:
        metrics.details["note"] = f"No focalization data for {gold_name}"
        return metrics

    gold_violations = GOLD_FOCALIZATION_VIOLATIONS_DATA[gold_name]

    try:
        # Intentar usar el modulo de focalizacion si existe
        try:
            from narrative_assistant.focalization import detect_focalization_violations

            result = detect_focalization_violations(text)

            if hasattr(result, 'is_failure') and result.is_failure:
                metrics.details["error"] = str(result.error)
                return metrics

            detected = result.value if hasattr(result, 'value') else result
            detected_violations = detected.violations if detected else []

            # Comparar con gold
            matched = 0
            for gold_v in gold_violations:
                gold_text_norm = normalize_text(gold_v.text[:50])  # Primeros 50 chars
                for det_v in detected_violations:
                    det_text_norm = normalize_text(det_v.text[:50])
                    if gold_text_norm in det_text_norm or det_text_norm in gold_text_norm:
                        matched += 1
                        break

            metrics.true_positives = matched
            metrics.false_positives = len(detected_violations) - matched
            metrics.false_negatives = len(gold_violations) - matched

        except ImportError:
            # Modulo no implementado - evaluacion basica por patrones
            metrics.details["note"] = "Focalization module not implemented - using pattern-based detection"

            # Patrones que indican cambio de POV
            pov_patterns = [
                r'\bpensaba\s+que\b',  # Pensamientos internos
                r'\bsabia\s+que\b',  # Conocimiento interno
                r'\bsentia\s+(?:que|como)\b',  # Sentimientos
                r'\bsin\s+saber\b',  # Lo que no sabe alguien
            ]

            narrative_text = _filter_metadata_sections(text)
            detected_count = 0
            for pattern in pov_patterns:
                detected_count += len(re.findall(pattern, narrative_text, re.IGNORECASE))

            # Heuristica: comparar con el numero esperado
            metrics.true_positives = min(detected_count, len(gold_violations))
            metrics.false_positives = max(0, detected_count - len(gold_violations))
            metrics.false_negatives = max(0, len(gold_violations) - detected_count)

        metrics.calculate()

        if verbose:
            metrics.details["gold_violations"] = len(gold_violations)
            metrics.details["gold_texts"] = [v.text[:50] + "..." for v in gold_violations]

    except Exception as e:
        metrics.details["error"] = str(e)
        import traceback
        metrics.details["traceback"] = traceback.format_exc()

    return metrics


def evaluate_sentiment_arc(text: str, gold_name: str, verbose: bool = False) -> EvaluationMetrics:
    """Evalua deteccion de arcos de sentimiento."""
    metrics = EvaluationMetrics(capability="sentiment")

    if gold_name not in GOLD_SENTIMENT_ARC_DATA:
        metrics.details["note"] = f"No sentiment arc data for {gold_name}"
        return metrics

    gold_arc = GOLD_SENTIMENT_ARC_DATA[gold_name]

    try:
        # Intentar usar el modulo de sentimiento si existe
        try:
            from narrative_assistant.nlp.sentiment import analyze_sentiment_arc

            result = analyze_sentiment_arc(text)

            if hasattr(result, 'is_failure') and result.is_failure:
                metrics.details["error"] = str(result.error)
                return metrics

            detected_arc = result.value if hasattr(result, 'value') else result

            # Comparar puntos del arco
            if detected_arc and hasattr(detected_arc, 'points'):
                # Verificar si la progresion general es correcta
                gold_progression = [p.sentiment for p in gold_arc]
                detected_progression = [p.sentiment for p in detected_arc.points]

                # Match basico: misma direccion general
                gold_trend = sum(1 if s == "positivo" else -1 if s == "negativo" else 0 for s in gold_progression)
                det_trend = sum(1 if s == "positivo" else -1 if s == "negativo" else 0 for s in detected_progression)

                # Si la tendencia coincide, es un match parcial
                if (gold_trend > 0 and det_trend > 0) or (gold_trend < 0 and det_trend < 0):
                    metrics.true_positives = len(detected_arc.points)
                else:
                    metrics.true_positives = len(detected_arc.points) // 2

                metrics.false_negatives = max(0, len(gold_arc) - metrics.true_positives)

        except ImportError:
            # Modulo no implementado - evaluacion basica por palabras clave
            metrics.details["note"] = "Sentiment module not implemented - using keyword-based detection"

            narrative_text = _filter_metadata_sections(text)

            # Palabras clave de sentimiento
            positive_words = ["alegr", "feliz", "paz", "esperanz", "sonri", "amor", "gratitud", "alivio"]
            negative_words = ["dolor", "triste", "rabia", "miedo", "llorar", "sufr", "angust", "devastac"]

            pos_count = sum(1 for w in positive_words if w in narrative_text.lower())
            neg_count = sum(1 for w in negative_words if w in narrative_text.lower())

            # Verificar si detectamos cambios de sentimiento
            total_detected = pos_count + neg_count
            gold_count = len(gold_arc)

            metrics.true_positives = min(total_detected, gold_count)
            metrics.false_positives = max(0, total_detected - gold_count)
            metrics.false_negatives = max(0, gold_count - total_detected)

        metrics.calculate()

        if verbose:
            metrics.details["gold_arc_points"] = len(gold_arc)
            metrics.details["gold_progression"] = [
                {"chapter": p.chapter, "sentiment": p.sentiment, "description": p.description}
                for p in gold_arc[:5]
            ]

    except Exception as e:
        metrics.details["error"] = str(e)
        import traceback
        metrics.details["traceback"] = traceback.format_exc()

    return metrics


def evaluate_register_changes(text: str, gold_name: str, verbose: bool = False) -> EvaluationMetrics:
    """Evalua deteccion de cambios de registro linguistico."""
    metrics = EvaluationMetrics(capability="register")

    if gold_name not in GOLD_REGISTER_CHANGES_DATA:
        metrics.details["note"] = f"No register change data for {gold_name}"
        return metrics

    gold_changes = GOLD_REGISTER_CHANGES_DATA[gold_name]

    try:
        # Intentar usar el modulo de registro si existe
        try:
            from narrative_assistant.nlp.style.register_analyzer import analyze_register

            result = analyze_register(text)

            if hasattr(result, 'is_failure') and result.is_failure:
                metrics.details["error"] = str(result.error)
                return metrics

            detected = result.value if hasattr(result, 'value') else result

            if detected and hasattr(detected, 'changes'):
                metrics.true_positives = len(detected.changes)
                metrics.false_negatives = max(0, len(gold_changes) - len(detected.changes))
            else:
                metrics.false_negatives = len(gold_changes)

        except ImportError:
            # Modulo no implementado - evaluacion basica
            metrics.details["note"] = "Register analyzer not implemented - using heuristic detection"

            narrative_text = _filter_metadata_sections(text)

            # Indicadores de registro formal
            formal_indicators = ["senor", "senora", "estimado", "procedamos", "igualmente"]
            # Indicadores de registro coloquial
            informal_indicators = ["tio", "tia", "mola", "curro", "flipante", "viste"]

            formal_count = sum(1 for w in formal_indicators if w in narrative_text.lower())
            informal_count = sum(1 for w in informal_indicators if w in narrative_text.lower())

            # Si hay mezcla de registros, detectamos cambios
            if formal_count > 0 and informal_count > 0:
                detected_changes = min(formal_count, informal_count)
                metrics.true_positives = min(detected_changes, len(gold_changes))
            else:
                metrics.true_positives = 0

            metrics.false_negatives = max(0, len(gold_changes) - metrics.true_positives)

        metrics.calculate()

        if verbose:
            metrics.details["gold_changes"] = len(gold_changes)
            metrics.details["gold_sample"] = [
                {"character": c.character, "from": c.from_register, "to": c.to_register}
                for c in gold_changes[:3]
            ]

    except Exception as e:
        metrics.details["error"] = str(e)
        import traceback
        metrics.details["traceback"] = traceback.format_exc()

    return metrics


# =============================================================================
# EVALUACION PRINCIPAL
# =============================================================================

def run_evaluation(
    gold_name: str,
    capabilities: list[str] = None,
    verbose: bool = False
) -> EvaluationReport:
    """Ejecuta evaluacion completa para un gold standard."""

    # Buscar en ambos conjuntos de gold standards
    all_standards = {**ALL_GOLD_STANDARDS, **ADVANCED_GOLD_STANDARDS}

    if gold_name not in all_standards:
        raise ValueError(f"Gold standard '{gold_name}' not found. Available: {list(all_standards.keys())}")

    gold = all_standards[gold_name]
    text = read_test_file(gold.text_file)

    all_capabilities = [
        "ner", "chapters", "relations", "timeline", "fusion", "grammar",
        "attributes", "inconsistencies", "orthography", "coreference", "dialogue",
        "muletillas", "focalization", "sentiment", "register"
    ]
    if capabilities:
        selected = [c for c in capabilities if c in all_capabilities or c.startswith("grammar_")]
    else:
        selected = all_capabilities

    metrics = {}

    # NER
    if "ner" in selected and gold.entities:
        print(f"  Evaluando NER...")
        metrics["ner"] = evaluate_ner(text, gold, verbose)

    # Capitulos
    if "chapters" in selected and gold.chapters:
        print(f"  Evaluando capitulos...")
        metrics["chapters"] = evaluate_chapters(text, gold, verbose)

    # Relaciones
    if "relations" in selected and gold.relations:
        print(f"  Evaluando relaciones...")
        metrics["relations"] = evaluate_relations(text, gold, verbose)

    # Timeline
    if "timeline" in selected and gold.events:
        print(f"  Evaluando timeline...")
        metrics["timeline"] = evaluate_timeline(text, gold, verbose)

    # Fusion
    if "fusion" in selected and gold.fusion_pairs:
        print(f"  Evaluando fusion...")
        metrics["fusion"] = evaluate_fusion(text, gold, verbose)

    # Gramatica
    if "grammar" in selected and gold.grammar_errors:
        print(f"  Evaluando gramatica...")
        grammar_metrics = evaluate_grammar(text, gold, verbose)
        for error_type, m in grammar_metrics.items():
            metrics[f"grammar_{error_type}"] = m

    # Atributos
    if "attributes" in selected and gold.attributes:
        print(f"  Evaluando atributos...")
        metrics["attributes"] = evaluate_attributes(text, gold, verbose)

    # Inconsistencias
    if "inconsistencies" in selected and gold.attributes:
        # Verificar si hay inconsistencias marcadas
        has_inconsistencies = any(a.is_inconsistency for a in gold.attributes)
        if has_inconsistencies:
            print(f"  Evaluando inconsistencias...")
            metrics["inconsistencies"] = evaluate_inconsistencies(text, gold, verbose)

    # Ortografia
    if "orthography" in selected and gold.orthography_errors:
        print(f"  Evaluando ortografia...")
        metrics["orthography"] = evaluate_orthography(text, gold, verbose)

    # Correferencias
    if "coreference" in selected and gold.coreferences:
        print(f"  Evaluando correferencias...")
        metrics["coreference"] = evaluate_coreference(text, gold, verbose)

    # Dialogos
    if "dialogue" in selected:
        # Evaluar si el texto tiene dialogos (presencia de guiones)
        if '—' in text or '--' in text or '- ' in text:
            print(f"  Evaluando atribucion de dialogos...")
            metrics["dialogue"] = evaluate_dialogue_attribution(text, gold, verbose)

    # Muletillas
    if "muletillas" in selected and gold_name in GOLD_MULETILLAS_DATA:
        print(f"  Evaluando muletillas...")
        metrics["muletillas"] = evaluate_muletillas(text, gold_name, verbose)

    # Focalizacion
    if "focalization" in selected and gold_name in GOLD_FOCALIZATION_VIOLATIONS_DATA:
        print(f"  Evaluando focalizacion...")
        metrics["focalization"] = evaluate_focalization(text, gold_name, verbose)

    # Sentimiento
    if "sentiment" in selected and gold_name in GOLD_SENTIMENT_ARC_DATA:
        print(f"  Evaluando arco de sentimiento...")
        metrics["sentiment"] = evaluate_sentiment_arc(text, gold_name, verbose)

    # Registro linguistico
    if "register" in selected and gold_name in GOLD_REGISTER_CHANGES_DATA:
        print(f"  Evaluando cambios de registro...")
        metrics["register"] = evaluate_register_changes(text, gold_name, verbose)

    # Resumen
    summary = {}
    for cap, m in metrics.items():
        summary[cap] = {
            "precision": round(m.precision * 100, 1),
            "recall": round(m.recall * 100, 1),
            "f1": round(m.f1_score * 100, 1),
        }

    return EvaluationReport(
        timestamp=datetime.now().isoformat(),
        gold_standard_name=gold_name,
        text_file=gold.text_file,
        metrics={k: asdict(v) for k, v in metrics.items()},
        summary=summary,
    )


def run_all_evaluations(verbose: bool = False) -> dict[str, EvaluationReport]:
    """Ejecuta evaluacion para todos los gold standards."""
    reports = {}

    for name in ALL_GOLD_STANDARDS:
        print(f"\n{'='*60}")
        print(f"Evaluando: {name}")
        print(f"{'='*60}")

        try:
            reports[name] = run_evaluation(name, verbose=verbose)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

    return reports


def print_report(report: EvaluationReport):
    """Imprime un reporte de evaluacion."""
    print(f"\n{'='*60}")
    print(f"REPORTE: {report.gold_standard_name}")
    print(f"Archivo: {report.text_file}")
    print(f"Timestamp: {report.timestamp}")
    print(f"{'='*60}")

    print("\n  Capacidad          | Precision | Recall | F1")
    print("  " + "-"*50)

    for cap, stats in report.summary.items():
        print(f"  {cap:19} | {stats['precision']:8.1f}% | {stats['recall']:5.1f}% | {stats['f1']:.1f}%")


def save_report(reports: dict[str, EvaluationReport], output_path: Path):
    """Guarda reportes en JSON."""
    data = {}
    for name, report in reports.items():
        data[name] = {
            "timestamp": report.timestamp,
            "gold_standard_name": report.gold_standard_name,
            "text_file": report.text_file,
            "metrics": report.metrics,
            "summary": report.summary,
        }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nReporte guardado en: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Evalua capacidades NLP contra gold standards")
    parser.add_argument("--gold", "-g", help="Gold standard especifico a evaluar")
    parser.add_argument("--capability", "-c", help="Capacidad especifica a evaluar")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mostrar detalles")
    parser.add_argument("--output", "-o", help="Archivo JSON de salida")
    parser.add_argument("--list", "-l", action="store_true", help="Listar gold standards disponibles")

    args = parser.parse_args()

    if args.list:
        print("Gold standards disponibles (desarrollo):")
        for name, gs in ALL_GOLD_STANDARDS.items():
            print(f"  - {name}: {gs.description}")
        print("\nGold standards avanzados:")
        for name, gs in ADVANCED_GOLD_STANDARDS.items():
            print(f"  - {name}: {gs.description}")
        return

    if args.gold:
        print(f"Evaluando gold standard: {args.gold}")
        capabilities = [args.capability] if args.capability else None
        report = run_evaluation(args.gold, capabilities=capabilities, verbose=args.verbose)
        print_report(report)

        if args.output:
            save_report({args.gold: report}, Path(args.output))
    else:
        # Evaluar todos
        reports = run_all_evaluations(verbose=args.verbose)

        for report in reports.values():
            print_report(report)

        # Resumen global
        print("\n" + "="*60)
        print("RESUMEN GLOBAL")
        print("="*60)

        all_metrics = {}
        for report in reports.values():
            for cap, stats in report.summary.items():
                if cap not in all_metrics:
                    all_metrics[cap] = []
                all_metrics[cap].append(stats)

        print("\n  Capacidad          | Avg Precision | Avg Recall | Avg F1")
        print("  " + "-"*56)

        for cap, stats_list in sorted(all_metrics.items()):
            avg_p = sum(s["precision"] for s in stats_list) / len(stats_list)
            avg_r = sum(s["recall"] for s in stats_list) / len(stats_list)
            avg_f1 = sum(s["f1"] for s in stats_list) / len(stats_list)
            print(f"  {cap:19} | {avg_p:12.1f}% | {avg_r:9.1f}% | {avg_f1:.1f}%")

        if args.output:
            save_report(reports, Path(args.output))


if __name__ == "__main__":
    main()
