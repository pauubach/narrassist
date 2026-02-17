"""
RAG (Retrieval-Augmented Generation) exhaustivo para el chat del asistente.

Busca TODAS las ocurrencias relevantes en TODO el manuscrito,
construye contexto numerado para el LLM, y parsea referencias
[REF:N] de la respuesta para crear referencias navegables.
"""

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# 1. Extracción de términos de búsqueda
# ============================================================================

# Palabras vacías en español (no aportan como términos de búsqueda)
_STOPWORDS_ES = frozenset({
    "pero", "como", "para", "este", "esta", "esto", "esos", "esas",
    "tiene", "están", "hacer", "hace", "hizo",
    "puede", "pudo", "podría", "sobre", "también", "cuando", "donde",
    "porque", "aunque", "mientras", "después", "antes", "entre",
    "desde", "hasta", "según", "durante", "mediante", "hacia",
    "cada", "otro", "otra", "otros", "todas", "todos", "todo",
    "toda", "algo", "alguien", "algún", "alguno", "alguna",
    "mucho", "mucha", "muchos", "muchas", "poco", "poca",
    "cual", "cuál", "quien", "quién", "cuyo", "cuya",
    "mismo", "misma", "mismos", "mismas", "varios", "varias",
    "dónde", "cómo", "cuándo", "cuánto", "cuántos", "qué",
})


def extract_search_terms(
    message: str,
    entities: Optional[list] = None,
) -> list[str]:
    """
    Extrae términos de búsqueda del mensaje del usuario.

    - Palabras > 3 chars (excluyendo stopwords)
    - Frases entrecomilladas como términos exactos
    - Si algún término coincide con un nombre de entidad, añade aliases

    Args:
        message: Mensaje del usuario
        entities: Lista de entidades del proyecto (con canonical_name y aliases)

    Returns:
        Lista de términos de búsqueda únicos
    """
    terms: list[str] = []

    # 1. Extraer frases entrecomilladas
    quoted = re.findall(r'"([^"]+)"', message)
    terms.extend(quoted)

    # 2. Extraer palabras significativas (> 3 chars, no stopwords)
    # Limpiar el mensaje de las frases entrecomilladas para no duplicar
    clean_msg = re.sub(r'"[^"]*"', '', message)
    words = re.findall(r'\b\w+\b', clean_msg.lower())
    for word in words:
        if len(word) > 3 and word not in _STOPWORDS_ES:
            terms.append(word)

    # 3. Expansión con entidades y aliases
    if entities:
        terms_lower = {t.lower() for t in terms}
        for entity in entities:
            name = getattr(entity, 'canonical_name', '')
            aliases = getattr(entity, 'aliases', []) or []
            all_names = [name] + aliases

            # Si algún término del usuario coincide con un nombre de entidad
            for entity_name in all_names:
                if entity_name and entity_name.lower() in terms_lower:
                    # Añadir todos los nombres de esa entidad
                    for n in all_names:
                        if n and n.lower() not in terms_lower:
                            terms.append(n)
                            terms_lower.add(n.lower())
                    break

    # Deduplicate preservando orden
    seen: set[str] = set()
    unique: list[str] = []
    for t in terms:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            unique.append(t)

    # Fallback: si todo se filtró por stopwords, usar la palabra más larga
    if not unique:
        all_words = re.findall(r'\b\w+\b', message)
        if all_words:
            longest = max(all_words, key=len)
            if len(longest) > 2:
                unique = [longest]

    return unique


# ============================================================================
# 2. Búsqueda exhaustiva en todo el manuscrito
# ============================================================================

def exhaustive_search(
    terms: list[str],
    chapters: list[dict[str, Any]],
    context_window: int = 150,
) -> list[dict[str, Any]]:
    """
    Busca TODAS las ocurrencias de todos los términos en todos los capítulos.

    Para cada match, extrae una ventana de contexto con la posición exacta.

    Args:
        terms: Términos de búsqueda
        chapters: Lista de capítulos con keys: number, title, content, start_char
        context_window: Caracteres de contexto antes y después del match

    Returns:
        Lista de matches con chapter_number, position, excerpt, etc.
    """
    matches: list[dict[str, Any]] = []

    for chapter in chapters:
        content = chapter.get("content", "")
        content_lower = content.lower()
        chapter_start = chapter.get("start_char", 0)

        for term in terms:
            term_lower = term.lower()
            start = 0
            while True:
                pos = content_lower.find(term_lower, start)
                if pos == -1:
                    break

                # Ventana de contexto
                excerpt_start = max(0, pos - context_window)
                excerpt_end = min(len(content), pos + len(term) + context_window)
                excerpt = content[excerpt_start:excerpt_end]

                # Limpiar excerpt: no cortar palabras
                if excerpt_start > 0:
                    space = excerpt.find(' ')
                    if space != -1 and space < context_window // 2:
                        excerpt = '...' + excerpt[space + 1:]
                        excerpt_start += space + 1
                if excerpt_end < len(content):
                    space = excerpt.rfind(' ')
                    if space != -1 and space > len(excerpt) - context_window // 2:
                        excerpt = excerpt[:space] + '...'

                matches.append({
                    "chapter_number": chapter.get("number", 0),
                    "chapter_title": chapter.get("title", ""),
                    "position_in_chapter": pos,
                    "global_start": chapter_start + pos,
                    "global_end": chapter_start + pos + len(term),
                    "excerpt": excerpt.strip(),
                    "excerpt_global_start": chapter_start + excerpt_start,
                    "term": term,
                })

                start = pos + 1

    return matches


# ============================================================================
# 3. Ranking y selección de excerpts
# ============================================================================

def rank_and_select(
    matches: list[dict[str, Any]],
    max_chars: int = 2000,
    max_excerpts: int = 8,
) -> list[dict[str, Any]]:
    """
    Fusiona matches solapados, prioriza diversidad entre capítulos,
    y selecciona los mejores excerpts dentro del budget de caracteres.

    Args:
        matches: Todos los matches de exhaustive_search
        max_chars: Budget máximo de caracteres para el contexto
        max_excerpts: Número máximo de excerpts

    Returns:
        Lista de excerpts seleccionados, ordenados por posición
    """
    if not matches:
        return []

    # 1. Ordenar por posición global
    sorted_matches = sorted(matches, key=lambda m: m["global_start"])

    # 2. Fusionar matches solapados (que están dentro de 50 chars uno de otro)
    merged: list[dict[str, Any]] = []
    for match in sorted_matches:
        if merged and _overlaps(merged[-1], match, threshold=50):
            # Fusionar: ampliar el excerpt y las posiciones
            prev = merged[-1]
            if len(match["excerpt"]) > len(prev["excerpt"]):
                prev["excerpt"] = match["excerpt"]
            # Expandir rango de posiciones al span completo
            prev["global_start"] = min(prev["global_start"], match["global_start"])
            prev["global_end"] = max(prev["global_end"], match["global_end"])
            # Unir términos
            prev_terms = prev.get("terms", [prev.get("term", "")])
            if match["term"] not in prev_terms:
                prev_terms.append(match["term"])
            prev["terms"] = prev_terms
        else:
            match["terms"] = [match.get("term", "")]
            merged.append(match)

    # 3. Priorizar diversidad: round-robin por capítulo
    by_chapter: dict[int, list[dict]] = {}
    for m in merged:
        ch = m["chapter_number"]
        by_chapter.setdefault(ch, []).append(m)

    # Ordenar capítulos por número de matches (descendente) para empezar
    # por los más relevantes
    chapter_order = sorted(by_chapter.keys(),
                           key=lambda c: len(by_chapter[c]), reverse=True)

    selected: list[dict[str, Any]] = []
    total_chars = 0
    round_idx = 0

    while total_chars < max_chars and len(selected) < max_excerpts:
        added_any = False
        for ch_num in chapter_order:
            ch_matches = by_chapter[ch_num]
            if round_idx < len(ch_matches):
                candidate = ch_matches[round_idx]
                candidate_len = len(candidate["excerpt"])
                if total_chars + candidate_len <= max_chars:
                    selected.append(candidate)
                    total_chars += candidate_len
                    added_any = True
                    if len(selected) >= max_excerpts:
                        break
        round_idx += 1
        if not added_any:
            break

    # 4. Reordenar por posición global para coherencia narrativa
    selected.sort(key=lambda m: m["global_start"])

    return selected


def _overlaps(a: dict, b: dict, threshold: int = 50) -> bool:
    """Verifica si dos matches están solapados o muy próximos."""
    return (
        a["chapter_number"] == b["chapter_number"]
        and abs(a["global_start"] - b["global_start"]) < threshold
    )


# ============================================================================
# 4. Construcción de contexto numerado para el LLM
# ============================================================================

def build_numbered_context(
    excerpts: list[dict[str, Any]],
) -> tuple[str, dict[int, dict[str, Any]]]:
    """
    Construye texto de contexto numerado para el system prompt del LLM.

    Cada excerpt se numera [1], [2], etc. El mapa permite después
    cruzar las referencias [REF:N] con posiciones reales.

    Args:
        excerpts: Excerpts seleccionados por rank_and_select

    Returns:
        Tupla (texto_contexto, mapa_referencias)
        - texto_contexto: string para inyectar en el system prompt
        - mapa_referencias: {ref_id: {chapter_number, chapter_title, global_start,
                                       global_end, excerpt}}
    """
    if not excerpts:
        return "", {}

    lines: list[str] = ["### Fragmentos relevantes del manuscrito:"]
    ref_map: dict[int, dict[str, Any]] = {}

    for i, excerpt in enumerate(excerpts, start=1):
        ch_title = excerpt.get("chapter_title", f"Capítulo {excerpt['chapter_number']}")
        lines.append(f"\n[REF:{i}] {ch_title}:")
        # Usar excerpt_for_llm si existe (contexto expandido), sino el excerpt normal
        llm_text = excerpt.get("excerpt_for_llm", excerpt["excerpt"])
        lines.append(f'"{llm_text}"')

        ref_map[i] = {
            "chapter_number": excerpt["chapter_number"],
            "chapter_title": ch_title,
            "global_start": excerpt["global_start"],
            "global_end": excerpt["global_end"],
            "excerpt": excerpt["excerpt"],  # Texto exacto para navegación
        }

    return "\n".join(lines), ref_map


# ============================================================================
# 5. Parsing de referencias [REF:N] de la respuesta del LLM
# ============================================================================

def build_reference_index(
    llm_response: str,
    ref_map: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Parsea [REF:N] del response del LLM y construye la lista de referencias
    navegables cruzando con el mapa de excerpts.

    Args:
        llm_response: Respuesta raw del LLM
        ref_map: Mapa de {ref_id: datos} de build_numbered_context

    Returns:
        Lista de referencias con id, chapter, chapterTitle, startChar, endChar, excerpt
    """
    # Encontrar todos los [REF:N] en la respuesta
    ref_pattern = re.compile(r'\[REF:(\d+)\]')
    found_refs = set(int(m) for m in ref_pattern.findall(llm_response))

    references: list[dict[str, Any]] = []
    seen: set[int] = set()

    for ref_id in sorted(found_refs):
        if ref_id in ref_map and ref_id not in seen:
            seen.add(ref_id)
            data = ref_map[ref_id]
            references.append({
                "id": ref_id,
                "chapter": data["chapter_number"],
                "chapterTitle": data["chapter_title"],
                "startChar": data["global_start"],
                "endChar": data["global_end"],
                "excerpt": data["excerpt"],
            })

    return references


# ============================================================================
# 6. System prompt para el chat
# ============================================================================

def build_chat_system_prompt(
    project_name: str,
    context_text: str,
    selection_context: str = "",
    history_text: str = "",
) -> str:
    """
    Construye el system prompt completo para el chat del asistente.

    Args:
        project_name: Nombre del proyecto/manuscrito
        context_text: Fragmentos relevantes (de build_numbered_context)
        selection_context: Contexto de texto seleccionado (opcional)
        history_text: Historial de conversación formateado

    Returns:
        System prompt completo
    """
    prompt_parts = [
        'Eres un asistente experto en análisis literario y corrección de textos.',
        f'Estás ayudando a analizar el manuscrito "{project_name}".',
        '',
        'Tu rol es:',
        '- Responder preguntas sobre el contenido del documento',
        '- Ayudar a identificar personajes, lugares y eventos',
        '- Señalar posibles inconsistencias cuando las encuentres',
        '- Dar sugerencias de mejora cuando sea apropiado',
        '',
        'Responde de forma concisa y profesional.',
        'Si no tienes información suficiente en el contexto proporcionado, indícalo.',
    ]

    # Instrucciones de citación (solo si hay contexto)
    if context_text:
        prompt_parts.extend([
            '',
            '═══════════════════════════════════════════════════════',
            '⚠️  FORMATO DE CITACIÓN OBLIGATORIO',
            '═══════════════════════════════════════════════════════',
            '',
            'Cuando cites información del manuscrito, usa EXACTAMENTE: [REF:N]',
            'Donde N es el número del contexto (1, 2, 3, etc.)',
            '',
            '✅ EJEMPLOS CORRECTOS:',
            '  "Elena tenía los ojos verdes" [REF:1]',
            '  Según el manuscrito, "era pelirroja" [REF:2]',
            '  Isabel [REF:1] interactúa con Carlos [REF:3]',
            '',
            '❌ FORMATOS PROHIBIDOS (NO uses):',
            '  - "fragmento [1]"   ← MAL',
            '  - "en [1]"          ← MAL',
            '  - "(referencia 1)"  ← MAL',
            '',
            'Escribe [REF:1], [REF:2], etc. EXACTAMENTE con ese formato.',
            'NO escribas "fragmento", "contexto", "referencia" antes del número.',
            '═══════════════════════════════════════════════════════',
        ])

    # Texto seleccionado por el usuario (recomendación panel de expertos)
    # System message dinámico con alto peso posicional - justo antes de la pregunta
    if selection_context:
        prompt_parts.extend([
            '',
            '═══════════════════════════════════════════════════════',
            '[CONTEXTO DE SELECCIÓN ACTIVA]',
            '═══════════════════════════════════════════════════════',
            selection_context,
            '',
            'COMPORTAMIENTO REQUERIDO:',
            '• La pregunta del usuario se refiere a este fragmento seleccionado',
            '• Responde explicando el fragmento en su contexto documental',
            '• Usa el historial previo SOLO si la pregunta lo requiere explícitamente',
            '• Incluye [REF:1] al citar el fragmento seleccionado',
            '═══════════════════════════════════════════════════════',
        ])

    # Contexto adicional del manuscrito
    if context_text:
        prompt_parts.extend(['', '## Contexto adicional del manuscrito', context_text])

    # Historial de conversación
    if history_text:
        prompt_parts.extend(['', history_text])

    return '\n'.join(prompt_parts)


def build_selection_context(
    selected_text: str,
    chapter_title: Optional[str] = None,
    expanded_context: Optional[str] = None,
) -> str:
    """
    Construye el bloque de contexto para el texto seleccionado.

    Args:
        selected_text: Texto seleccionado por el usuario
        chapter_title: Título del capítulo (opcional)
        expanded_context: Contexto expandido alrededor de la selección (opcional)

    Returns:
        Bloque de texto para inyectar en el system prompt
    """
    parts = []

    if chapter_title:
        parts.append(f'📍 Ubicación: {chapter_title}')
        parts.append('')

    # Si hay contexto expandido, mostrarlo primero
    if expanded_context:
        parts.append('📖 Contexto completo (±200 caracteres):')
        parts.append(f'"{expanded_context}"')
        parts.append('')
        parts.append(f'🎯 El usuario seleccionó específicamente: "{selected_text}"')
    else:
        # Truncar si es muy largo
        text = selected_text[:500] if len(selected_text) > 500 else selected_text
        parts.append(f'🎯 Texto seleccionado: "{text}"')

    return '\n'.join(parts)
