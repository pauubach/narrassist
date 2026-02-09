"""
Detector de variantes ortográficas en nombres de entidades.

Detecta cuando el mismo personaje/entidad tiene menciones con diferentes
acentuaciones (ej: "María" vs "Maria"), alertando al editor sobre
posibles errores tipográficos.

La detección distingue entre texto narrativo y diálogos:
- Narrativa: severidad WARNING (probable error)
- Diálogo: severidad HINT (posiblemente intencional)
"""

import logging
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class NameVariantIssue:
    """Variante ortográfica detectada en el nombre de una entidad."""

    entity_id: int
    entity_name: str
    canonical_form: str  # Forma mayoritaria (con acentos correctos)
    variant_form: str  # Forma variante (posible error)
    canonical_count: int
    variant_count: int
    variant_mentions: list[dict] = field(default_factory=list)
    all_in_dialogue: bool = False
    confidence: float = 0.85


def _strip_accents(text: str) -> str:
    """Elimina acentos preservando ñ/Ñ."""
    text = text.replace("ñ", "\x00").replace("Ñ", "\x01")
    nfkd = unicodedata.normalize("NFKD", text)
    result = "".join(c for c in nfkd if not unicodedata.combining(c))
    return result.replace("\x00", "ñ").replace("\x01", "Ñ")


def _normalize(text: str) -> str:
    """Normaliza: sin acentos, minúsculas, sin espacios extra."""
    return _strip_accents(text).lower().strip()


def _is_position_in_dialogue(
    start_char: int,
    dialogue_spans: list[tuple[int, int]],
) -> bool:
    """Verifica si una posición está dentro de un span de diálogo."""
    for d_start, d_end in dialogue_spans:
        if d_start <= start_char < d_end:
            return True
    return False


def detect_name_variants(
    entities: list,
    mentions_by_entity: dict[int, list],
    dialogue_spans: list[tuple[int, int]] | None = None,
) -> list[NameVariantIssue]:
    """
    Detecta variantes ortográficas en nombres de entidades.

    Para cada entidad, analiza sus menciones y detecta formas
    superficiales que difieren solo en acentuación.

    Args:
        entities: Lista de entidades del proyecto
        mentions_by_entity: Dict {entity_id: [EntityMention, ...]}
        dialogue_spans: Spans de diálogo [(start, end), ...]

    Returns:
        Lista de NameVariantIssue detectados
    """
    from ..entities.semantic_fusion import are_hypocoristic_match

    issues: list[NameVariantIssue] = []
    dialogue_spans = dialogue_spans or []

    for entity in entities:
        entity_id = getattr(entity, "id", None)
        if entity_id is None:
            continue

        mentions = mentions_by_entity.get(entity_id, [])
        if len(mentions) < 2:
            continue

        # Agrupar menciones por forma de superficie
        form_mentions: dict[str, list] = defaultdict(list)
        for mention in mentions:
            sf = getattr(mention, "surface_form", "").strip()
            if sf:
                form_mentions[sf].append(mention)

        if len(form_mentions) < 2:
            continue

        # Agrupar formas por normalización (sin acentos)
        norm_groups: dict[str, list[str]] = defaultdict(list)
        for surface_form in form_mentions:
            norm = _normalize(surface_form)
            norm_groups[norm].append(surface_form)

        # Detectar variantes con diferencia de acentos
        for _norm_key, forms in norm_groups.items():
            if len(forms) < 2:
                continue

            # Si no hay al menos 2 formas distintas, nada que hacer
            unique_forms = list(set(forms))
            if len(unique_forms) < 2:
                continue

            # Determinar forma mayoritaria
            form_counts = {f: len(form_mentions[f]) for f in unique_forms}
            canonical = max(form_counts, key=lambda f: form_counts[f])

            for variant_form in unique_forms:
                if variant_form == canonical:
                    continue

                # No alertar sobre hipocorísticos reales (Paco/Francisco).
                # Pero SÍ alertar sobre variantes de acentos (María/Maria)
                # que comparten la misma forma sin acentos.
                same_stripped = _strip_accents(variant_form) == _strip_accents(canonical)
                if not same_stripped:
                    try:
                        if are_hypocoristic_match(variant_form, canonical):
                            continue
                    except Exception:
                        pass

                # Construir detalles de menciones variantes
                variant_details = []
                all_in_dlg = bool(dialogue_spans)

                for m in form_mentions[variant_form]:
                    in_dialogue = False
                    m_start = getattr(m, "start_char", 0)
                    if dialogue_spans:
                        in_dialogue = _is_position_in_dialogue(
                            m_start, dialogue_spans
                        )

                    if not in_dialogue:
                        all_in_dlg = False

                    variant_details.append({
                        "chapter_id": getattr(m, "chapter_id", None),
                        "start_char": m_start,
                        "end_char": getattr(m, "end_char", 0),
                        "context_before": getattr(m, "context_before", "") or "",
                        "context_after": getattr(m, "context_after", "") or "",
                        "in_dialogue": in_dialogue,
                        "surface_form": getattr(m, "surface_form", ""),
                    })

                # Confianza basada en proporción
                total = form_counts[canonical] + form_counts[variant_form]
                ratio = form_counts[canonical] / total
                confidence = min(0.95, 0.5 + ratio * 0.45)

                issues.append(NameVariantIssue(
                    entity_id=entity_id,
                    entity_name=getattr(entity, "canonical_name", str(entity)),
                    canonical_form=canonical,
                    variant_form=variant_form,
                    canonical_count=form_counts[canonical],
                    variant_count=form_counts[variant_form],
                    variant_mentions=variant_details,
                    all_in_dialogue=all_in_dlg,
                    confidence=confidence,
                ))

    issues.sort(key=lambda i: i.confidence, reverse=True)
    logger.info(f"Name variant detector found {len(issues)} issues")
    return issues
