"""
Integración del preprocesador de títulos con pipelines de spaCy.

Proporciona dos enfoques:
1. Preprocesamiento antes de spaCy (recomendado)
2. Post-procesamiento de resultados de spaCy
3. Análisis paralelo de títulos y contenido

Uso:
    from narrative_assistant.nlp.spacy_title_integration import analyze_with_title_handling

    nlp = load_spacy_model()
    result = analyze_with_title_handling(nlp, text)

    for title_doc, content_docs in result.grouped_by_title:
        print(f"Título: {title_doc.text if title_doc else 'N/A'}")
        for doc in content_docs:
            for ent in doc.ents:
                print(f"  - {ent.text} ({ent.label_})")
"""

import logging
from dataclasses import dataclass
from typing import Optional, Iterator

from .title_preprocessor import TitlePreprocessor, ProcessedDocument, ProcessedParagraph
from .spacy_gpu import load_spacy_model

logger = logging.getLogger(__name__)


@dataclass
class TitleAwareDoc:
    """
    Documento spaCy con información de título asociado.

    Attributes:
        doc: Documento spaCy procesado
        is_title: Si es un título
        preceding_title: Título que precede a este contenido (si aplica)
        paragraph_index: Índice del párrafo en el documento
    """
    doc: object  # Doc de spaCy
    is_title: bool
    preceding_title: Optional['TitleAwareDoc'] = None
    paragraph_index: int = 0
    text: Optional[str] = None

    def __post_init__(self):
        if self.text is None and hasattr(self.doc, 'text'):
            self.text = self.doc.text


@dataclass
class TitleAwareAnalysisResult:
    """
    Resultado del análisis consciente de títulos.

    Attributes:
        docs: Lista de documentos spaCy analizados
        preprocessed: Documento preprocesado
        grouped_by_title: Lista de tuplas (título_doc, [contenido_docs])
        title_count: Número de títulos procesados
        content_count: Número de párrafos de contenido procesados
    """
    docs: list[object]  # list[Doc]
    preprocessed: ProcessedDocument
    grouped_by_title: list[tuple[Optional[object], list[object]]]
    title_count: int
    content_count: int


def analyze_with_title_handling(nlp, text: str) -> TitleAwareAnalysisResult:
    """
    Analiza un texto con manejo especial de títulos.

    Estrategia:
    1. Preprocesar para detectar y separar títulos
    2. Procesar títulos por separado (análisis básico)
    3. Procesar contenido narrativo (análisis completo)
    4. Agrupar resultados

    Args:
        nlp: Modelo spaCy cargado
        text: Texto a analizar

    Returns:
        TitleAwareAnalysisResult con documentos analizados

    Ejemplo:
        nlp = load_spacy_model()
        result = analyze_with_title_handling(nlp, text)

        for title_doc, content_docs in result.grouped_by_title:
            if title_doc:
                print(f"Título: {title_doc.text}")
            for doc in content_docs:
                for token in doc:
                    if token.pos_ == "VERB":
                        print(f"  Verbo: {token.text}")
    """
    preprocessor = TitlePreprocessor()
    processed = preprocessor.process(text)

    docs = []
    title_aware_docs = []
    title_index_map = {}  # Mapeo de índice de párrafo a índice de título

    # Procesar todos los párrafos con spaCy
    last_title_doc = None
    last_title_index = -1

    for i, para in enumerate(processed.paragraphs):
        doc = nlp(para.text)

        aware_doc = TitleAwareDoc(
            doc=doc,
            is_title=para.is_title,
            paragraph_index=i,
            text=para.text,
        )

        docs.append(doc)
        title_aware_docs.append(aware_doc)

        if para.is_title:
            last_title_doc = aware_doc
            last_title_index = i
            title_index_map[i] = (aware_doc, [])
        else:
            # Asociar con el último título
            if last_title_index >= 0:
                title_index_map[last_title_index][1].append(doc)
            else:
                # Sin título previo
                if None not in title_index_map:
                    title_index_map[None] = (None, [])
                title_index_map[None][1].append(doc)

    # Agrupar por título
    grouped = []
    seen_titles = set()
    for para in processed.paragraphs:
        if para.is_title:
            # Buscar título en el mapa
            for idx, (title_doc, content_docs) in title_index_map.items():
                if idx not in seen_titles and title_doc and title_doc.text == para.text:
                    grouped.append((title_doc, content_docs))
                    seen_titles.add(idx)
                    break

    # Añadir contenido sin título
    if None in title_index_map:
        grouped.append((None, title_index_map[None][1]))

    logger.info(
        f"Análisis completado: {len(processed.get_titles())} títulos, "
        f"{len(processed.get_content())} párrafos de contenido"
    )

    return TitleAwareAnalysisResult(
        docs=docs,
        preprocessed=processed,
        grouped_by_title=grouped,
        title_count=processed.title_count,
        content_count=processed.content_count,
    )


def analyze_paragraphs_separately(
    nlp,
    text: str,
    keep_titles: bool = False
) -> Iterator[tuple[ProcessedParagraph, object]]:
    """
    Analiza un texto párrafo por párrafo, detectando títulos.

    Estrategia lazy: procesa cada párrafo bajo demanda.

    Args:
        nlp: Modelo spaCy cargado
        text: Texto a analizar
        keep_titles: Si True, también procesa títulos

    Yields:
        Tupla (párrafo_procesado, doc_spacy)

    Ejemplo:
        nlp = load_spacy_model()
        for para, doc in analyze_paragraphs_separately(nlp, text):
            if not para.is_title:
                for token in doc:
                    print(f"{token.text} -> {token.dep_}")
    """
    preprocessor = TitlePreprocessor()
    processed = preprocessor.process(text)

    for para in processed.paragraphs:
        if para.is_title and not keep_titles:
            continue

        doc = nlp(para.text)
        yield para, doc


def extract_entities_by_title(
    nlp,
    text: str,
    entity_labels: Optional[list[str]] = None
) -> dict:
    """
    Extrae entidades agrupadas por título de capítulo.

    Args:
        nlp: Modelo spaCy cargado
        text: Texto a analizar
        entity_labels: Etiquetas a extraer (None = todas)

    Returns:
        Dict con estructura:
        {
            "Capítulo 1: El Comienzo": {
                "PERSON": ["María", "Juan"],
                "LOC": ["Madrid", "París"],
                ...
            },
            ...
        }

    Ejemplo:
        nlp = load_spacy_model()
        entities = extract_entities_by_title(nlp, text)

        for title, ents_by_label in entities.items():
            print(f"Capítulo: {title}")
            for label, entities_list in ents_by_label.items():
                print(f"  {label}: {', '.join(entities_list)}")
    """
    result = analyze_with_title_handling(nlp, text)
    entities_by_title = {}

    for title_doc, content_docs in result.grouped_by_title:
        title_text = title_doc.text if title_doc else "Sin título"
        entities_by_label = {}

        for doc in content_docs:
            for ent in doc.ents:
                # Filtrar por etiqueta si se especificó
                if entity_labels and ent.label_ not in entity_labels:
                    continue

                label = ent.label_
                if label not in entities_by_label:
                    entities_by_label[label] = []

                # Evitar duplicados
                if ent.text not in entities_by_label[label]:
                    entities_by_label[label].append(ent.text)

        if entities_by_label:
            entities_by_title[title_text] = entities_by_label

    return entities_by_title


def extract_dependencies_by_title(
    nlp,
    text: str,
    dep_labels: Optional[list[str]] = None
) -> dict:
    """
    Extrae relaciones de dependencia agrupadas por título.

    Args:
        nlp: Modelo spaCy cargado
        text: Texto a analizar
        dep_labels: Etiquetas de dependencia a extraer (None = todas)

    Returns:
        Dict con estructura:
        {
            "Capítulo 1": [
                ("María", "VERB", "despertó", ["nsubj"]),
                ...
            ]
        }

    Ejemplo:
        nlp = load_spacy_model()
        deps = extract_dependencies_by_title(nlp, text)

        for title, relations in deps.items():
            print(f"Capítulo: {title}")
            for head_text, head_pos, dep_text, dep_labels in relations:
                print(f"  {head_text} ({head_pos}) -> {dep_text}")
    """
    result = analyze_with_title_handling(nlp, text)
    deps_by_title = {}

    for title_doc, content_docs in result.grouped_by_title:
        title_text = title_doc.text if title_doc else "Sin título"
        deps_list = []

        for doc in content_docs:
            for token in doc:
                if token.dep_ == "ROOT":
                    continue

                # Filtrar por etiqueta si se especificó
                if dep_labels and token.dep_ not in dep_labels:
                    continue

                head = token.head
                deps_list.append({
                    'dependent': token.text,
                    'dependent_pos': token.pos_,
                    'head': head.text,
                    'head_pos': head.pos_,
                    'dependency': token.dep_,
                })

        if deps_list:
            deps_by_title[title_text] = deps_list

    return deps_by_title


def get_parsing_quality_metrics(
    nlp,
    text: str
) -> dict:
    """
    Calcula métricas de calidad del parsing de spaCy.

    Compara parsing de contenido (sin título) vs contenido completo,
    para demostrar el impacto del preprocesamiento de títulos.

    Args:
        nlp: Modelo spaCy cargado
        text: Texto a analizar

    Returns:
        Dict con métricas de calidad
    """
    preprocessor = TitlePreprocessor()
    processed = preprocessor.process(text)

    # Análisis CON títulos (como se haría normalmente)
    doc_with_titles = nlp(text)

    # Análisis SIN títulos (después de preprocesar)
    content_text = processed.get_content_text()
    doc_without_titles = nlp(content_text)

    metrics = {
        'text_length': len(text),
        'content_length': len(content_text),
        'title_count': processed.title_count,
        'with_titles': {
            'sentence_count': len(list(doc_with_titles.sents)),
            'entity_count': len(doc_with_titles.ents),
            'verb_count': sum(1 for token in doc_with_titles if token.pos_ == 'VERB'),
            'root_verbs': sum(1 for token in doc_with_titles if token.pos_ == 'VERB' and token.dep_ == 'ROOT'),
        },
        'without_titles': {
            'sentence_count': len(list(doc_without_titles.sents)),
            'entity_count': len(doc_without_titles.ents),
            'verb_count': sum(1 for token in doc_without_titles if token.pos_ == 'VERB'),
            'root_verbs': sum(1 for token in doc_without_titles if token.pos_ == 'VERB' and token.dep_ == 'ROOT'),
        },
    }

    return metrics


# =============================================================================
# Funciones auxiliares para debugging
# =============================================================================


def debug_parsing(nlp, text: str, max_tokens: int = 50) -> str:
    """
    Muestra un análisis detallado del parsing para debugging.

    Args:
        nlp: Modelo spaCy cargado
        text: Texto a analizar
        max_tokens: Máximo de tokens a mostrar

    Returns:
        String formateado con análisis
    """
    preprocessor = TitlePreprocessor()
    processed = preprocessor.process(text)

    output = []
    output.append("=" * 80)
    output.append("ANÁLISIS DE PARSING CON MANEJO DE TÍTULOS")
    output.append("=" * 80)
    output.append("")

    # Mostrar párrafos detectados
    output.append("PÁRRAFOS DETECTADOS:")
    output.append("-" * 80)
    for i, para in enumerate(processed.paragraphs):
        marker = "[TÍTULO]" if para.is_title else "[CONTENIDO]"
        output.append(f"{marker} [{i}] {para.text[:60]}...")
    output.append("")

    # Análisis de cada párrafo
    output.append("ANÁLISIS DETALLADO:")
    output.append("-" * 80)

    for para in processed.paragraphs[:3]:  # Primeros 3 para no sobrecargar
        marker = "[TÍTULO]" if para.is_title else "[CONTENIDO]"
        output.append(f"{marker}: {para.text}")

        doc = nlp(para.text)

        # Tokens y dependencias
        output.append("  Tokens (pos, dep, head):")
        for token in doc[:max_tokens]:
            output.append(
                f"    {token.i:2d}. {token.text:15s} "
                f"{token.pos_:6s} {token.dep_:10s} -> {token.head.text}"
            )

        # Entidades
        if doc.ents:
            output.append("  Entidades:")
            for ent in doc.ents:
                output.append(f"    - {ent.text} ({ent.label_})")
        output.append("")

    output.append("=" * 80)
    return "\n".join(output)
