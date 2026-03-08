"""Helpers de serializacion/deserializacion de cache de analisis."""

from __future__ import annotations

import contextlib
import hashlib
import json
from typing import Any


def _serialize_entities_for_cache(entities: list, entity_repo) -> str:
    """
    Serializa entidades + menciones a JSON para cache.

    Args:
        entities: Lista de Entity objects
        entity_repo: Repositorio de entidades para obtener menciones

    Returns:
        JSON string con [{entity_data, mentions: [...]}]
    """
    cache_data = []

    for entity in entities:
        mentions = entity_repo.get_mentions_by_entity(entity.id)

        entity_dict = {
            "id": entity.id,
            "canonical_name": entity.canonical_name,
            "entity_type": entity.entity_type.value
            if hasattr(entity.entity_type, "value")
            else str(entity.entity_type),
            "aliases": entity.aliases if entity.aliases else [],
            "importance": entity.importance.value
            if hasattr(entity.importance, "value")
            else str(entity.importance),
            "first_appearance_char": entity.first_appearance_char,
            "mention_count": entity.mention_count,
            "mentions": [
                {
                    "surface_form": m.surface_form,
                    "start_char": m.start_char,
                    "end_char": m.end_char,
                    "chapter_id": m.chapter_id,
                    "confidence": m.confidence,
                    "source": m.source,
                }
                for m in mentions
            ],
        }

        cache_data.append(entity_dict)

    return json.dumps(cache_data, ensure_ascii=False)


def _restore_entities_from_cache(
    entities_json: str,
    project_id: int,
    find_chapter_id_for_position,
) -> list:
    """
    Restaura entidades + menciones desde JSON de cache.

    Args:
        entities_json: JSON string de entidades serializadas
        project_id: ID del proyecto
        find_chapter_id_for_position: Funcion para mapear char -> chapter_id

    Returns:
        Lista de Entity objects con menciones creadas en DB
    """
    from narrative_assistant.entities.models import (
        Entity,
        EntityImportance,
        EntityMention,
        EntityType,
    )
    from narrative_assistant.entities.repository import get_entity_repository

    cache_data = json.loads(entities_json)
    entity_repo = get_entity_repository()
    entities = []

    for entity_dict in cache_data:
        entity_type_str = entity_dict["entity_type"]
        try:
            entity_type = EntityType(entity_type_str)
        except ValueError:
            entity_type = EntityType.CONCEPT

        importance_str = entity_dict["importance"]
        try:
            importance = EntityImportance(importance_str)
        except ValueError:
            importance = EntityImportance.MINIMAL

        entity = Entity(
            id=None,
            project_id=project_id,
            canonical_name=entity_dict["canonical_name"],
            entity_type=entity_type,
            aliases=entity_dict.get("aliases", []),
            importance=importance,
            first_appearance_char=entity_dict.get("first_appearance_char", 0),
            mention_count=entity_dict.get("mention_count", 0),
            description=None,
            merged_from_ids=[],
            is_active=True,
        )

        entity_id = entity_repo.create_entity(entity)
        entity.id = entity_id

        mentions_to_create = []
        for mention_dict in entity_dict.get("mentions", []):
            start_char = mention_dict["start_char"]
            chapter_id = mention_dict.get("chapter_id")
            if callable(find_chapter_id_for_position):
                with contextlib.suppress(Exception):
                    chapter_id = find_chapter_id_for_position(start_char)

            mention = EntityMention(
                entity_id=entity_id,
                surface_form=mention_dict["surface_form"],
                start_char=start_char,
                end_char=mention_dict["end_char"],
                chapter_id=chapter_id,
                confidence=mention_dict.get("confidence", 0.9),
                source=mention_dict.get("source", "cache"),
            )
            mentions_to_create.append(mention)

        if mentions_to_create:
            entity_repo.create_mentions_batch(mentions_to_create)

        entities.append(entity)

    return entities


def _chapter_text_hash(text: str) -> str:
    """Hash deterministico del texto de un capitulo para cache incremental."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _serialize_chapter_mentions_for_cache(raw_mentions: list, chapter_start: int) -> str:
    """
    Serializa menciones NER con offsets locales al capitulo.

    Guardar offsets locales permite reutilizar cache aunque cambie la
    posicion global del capitulo en el documento.
    """
    payload: list[dict[str, Any]] = []
    for ent in raw_mentions:
        local_start = max(0, int(ent.start_char) - chapter_start)
        local_end = max(local_start, int(ent.end_char) - chapter_start)
        payload.append(
            {
                "text": ent.text,
                "label": ent.label.value if hasattr(ent.label, "value") else str(ent.label),
                "start_char": local_start,
                "end_char": local_end,
                "confidence": float(ent.confidence),
                "source": ent.source,
            }
        )
    return json.dumps(payload, ensure_ascii=False)


def _restore_chapter_mentions_from_cache(mentions_json: str, chapter_start: int) -> list:
    """Restaura menciones NER cacheadas y vuelve a offsets globales."""
    from narrative_assistant.nlp.ner import EntityLabel, ExtractedEntity

    data = json.loads(mentions_json) if mentions_json else []
    restored: list[ExtractedEntity] = []
    for item in data:
        label_raw = item.get("label", "MISC")
        try:
            label = EntityLabel(label_raw)
        except ValueError:
            label = EntityLabel.MISC

        start_char = chapter_start + int(item.get("start_char", 0))
        end_char = chapter_start + int(item.get("end_char", 0))
        if end_char < start_char:
            end_char = start_char

        restored.append(
            ExtractedEntity(
                text=item.get("text", ""),
                label=label,
                start_char=start_char,
                end_char=end_char,
                confidence=float(item.get("confidence", 0.8)),
                source=item.get("source", "chapter_cache"),
            )
        )

    return restored


def _serialize_coref_result_for_cache(coref_result) -> str:
    """Serializa CorefResult a JSON para cache."""
    data: dict[str, Any] = {
        "chains": [],
        "unresolved": [],
        "method_contributions": {},
        "voting_details": [],
        "processing_time_ms": coref_result.processing_time_ms,
    }

    for chain in coref_result.chains:
        chain_dict = {
            "main_mention": chain.main_mention,
            "entity_id": chain.entity_id,
            "confidence": chain.confidence,
            "methods_agreed": [m.value for m in chain.methods_agreed],
            "mentions": [
                {
                    "text": m.text,
                    "start_char": m.start_char,
                    "end_char": m.end_char,
                    "mention_type": m.mention_type.value,
                    "gender": m.gender.value,
                    "number": m.number.value,
                    "sentence_idx": m.sentence_idx,
                    "chapter_idx": m.chapter_idx,
                    "head_text": m.head_text,
                    "context": m.context,
                }
                for m in chain.mentions
            ],
        }
        data["chains"].append(chain_dict)

    for mention in coref_result.unresolved:
        data["unresolved"].append(
            {
                "text": mention.text,
                "start_char": mention.start_char,
                "end_char": mention.end_char,
                "mention_type": mention.mention_type.value,
            }
        )

    for method, count in coref_result.method_contributions.items():
        data["method_contributions"][method.value] = count

    for detail in coref_result.voting_details.values():
        data["voting_details"].append(detail.to_dict())

    return json.dumps(data, ensure_ascii=False)


def _restore_coref_result_from_cache(chains_json: str):
    """Restaura CorefResult desde JSON de cache."""
    from narrative_assistant.nlp.coreference_resolver import (
        CoreferenceChain,
        CorefMethod,
        CorefResult,
        Gender,
        Mention,
        MentionType,
        MentionVotingDetail,
        Number,
    )

    data = json.loads(chains_json)
    result = CorefResult()

    for chain_dict in data.get("chains", []):
        chain = CoreferenceChain()
        chain.main_mention = chain_dict.get("main_mention")
        chain.entity_id = chain_dict.get("entity_id")
        chain.confidence = chain_dict.get("confidence", 0.0)
        chain.methods_agreed = [
            CorefMethod(value) for value in chain_dict.get("methods_agreed", [])
        ]
        for mention_dict in chain_dict.get("mentions", []):
            mention = Mention(
                text=mention_dict["text"],
                start_char=mention_dict["start_char"],
                end_char=mention_dict["end_char"],
                mention_type=MentionType(mention_dict["mention_type"]),
                gender=Gender(mention_dict.get("gender", "unknown")),
                number=Number(mention_dict.get("number", "unknown")),
                sentence_idx=mention_dict.get("sentence_idx", 0),
                chapter_idx=mention_dict.get("chapter_idx"),
                head_text=mention_dict.get("head_text"),
                context=mention_dict.get("context"),
            )
            chain.mentions.append(mention)
        result.chains.append(chain)

    for mention_dict in data.get("unresolved", []):
        result.unresolved.append(
            Mention(
                text=mention_dict["text"],
                start_char=mention_dict["start_char"],
                end_char=mention_dict["end_char"],
                mention_type=MentionType(mention_dict["mention_type"]),
                gender=Gender(mention_dict.get("gender", "unknown")),
                number=Number(mention_dict.get("number", "unknown")),
            )
        )

    for method_str, count in data.get("method_contributions", {}).items():
        try:
            result.method_contributions[CorefMethod(method_str)] = count
        except ValueError:
            pass

    for detail_dict in data.get("voting_details", []):
        detail = MentionVotingDetail.from_dict(detail_dict)
        key = (detail.anaphor_start, detail.anaphor_end)
        result.voting_details[key] = detail

    result.processing_time_ms = data.get("processing_time_ms", 0.0)
    return result
