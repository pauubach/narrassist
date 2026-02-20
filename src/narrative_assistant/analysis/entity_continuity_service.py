"""
Continuidad de entidades entre versiones de manuscrito.

Este servicio encapsula el matching "same/renamed/new/removed" para:
- reutilizar el mismo algoritmo en diffs y vistas históricas,
- facilitar pruebas de precisión/recall con fixtures.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EntityContinuityMetrics:
    matched: int
    renamed: int
    new_entities: int
    removed_entities: int


class EntityContinuityService:
    """Matcher heurístico de continuidad de entidades entre dos versiones."""

    def __init__(self, rename_threshold: float = 0.78) -> None:
        self.rename_threshold = max(0.0, min(1.0, float(rename_threshold)))

    @staticmethod
    def _strip_accents(value: str) -> str:
        normalized = unicodedata.normalize("NFD", value or "")
        return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")

    @classmethod
    def _normalize_name(cls, value: str) -> str:
        normalized = cls._strip_accents((value or "").lower().strip())
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = re.sub(r"[^\w\s]", "", normalized)
        return normalized.strip()

    @classmethod
    def build_entity_signature(cls, entity: dict[str, Any]) -> dict[str, Any]:
        canonical_name = str(entity.get("canonical_name") or "")
        aliases_raw = entity.get("aliases") or []
        aliases = [str(alias) for alias in aliases_raw if alias]
        normalized_aliases = {cls._normalize_name(alias) for alias in aliases}
        normalized_canonical = cls._normalize_name(canonical_name)
        if normalized_canonical:
            normalized_aliases.add(normalized_canonical)

        return {
            "entity_id": int(entity.get("entity_id") or 0),
            "entity_type": str(entity.get("entity_type") or ""),
            "canonical_name": canonical_name,
            "normalized_name": normalized_canonical,
            "normalized_aliases": normalized_aliases,
            "mention_count": int(entity.get("mention_count") or 0),
            "importance": str(entity.get("importance") or ""),
        }

    @classmethod
    def _token_jaccard(cls, left: str, right: str) -> float:
        left_tokens = set(cls._normalize_name(left).split())
        right_tokens = set(cls._normalize_name(right).split())
        if not left_tokens or not right_tokens:
            return 0.0
        union = left_tokens | right_tokens
        if not union:
            return 0.0
        return len(left_tokens & right_tokens) / len(union)

    def _name_score(self, old_sig: dict[str, Any], new_sig: dict[str, Any]) -> tuple[float, str]:
        old_norm = str(old_sig.get("normalized_name") or "")
        new_norm = str(new_sig.get("normalized_name") or "")
        old_aliases = set(old_sig.get("normalized_aliases") or set())
        new_aliases = set(new_sig.get("normalized_aliases") or set())

        old_mentions = int(old_sig.get("mention_count", 0))
        new_mentions = int(new_sig.get("mention_count", 0))
        mention_ratio = (
            min(old_mentions, new_mentions) / max(old_mentions, new_mentions)
            if old_mentions > 0 and new_mentions > 0
            else 0.5
        )
        importance_bonus = (
            0.05
            if str(old_sig.get("importance") or "") == str(new_sig.get("importance") or "")
            and str(old_sig.get("importance") or "")
            else 0.0
        )

        if old_norm and old_norm == new_norm:
            return min(1.0, 0.90 + (mention_ratio * 0.08) + importance_bonus), "exact_canonical"
        if old_norm and old_norm in new_aliases:
            return min(1.0, 0.86 + (mention_ratio * 0.10) + importance_bonus), "old_in_new_aliases"
        if new_norm and new_norm in old_aliases:
            return min(1.0, 0.83 + (mention_ratio * 0.10) + importance_bonus), "new_in_old_aliases"

        jacc = self._token_jaccard(
            str(old_sig.get("canonical_name") or ""),
            str(new_sig.get("canonical_name") or ""),
        )
        if jacc >= 0.8:
            return min(
                1.0,
                0.78 + ((jacc - 0.8) * 0.35) + (mention_ratio * 0.08) + importance_bonus,
            ), "token_overlap"
        return (jacc * 0.6) + (mention_ratio * 0.15), "weak_overlap"

    def classify_entity_change(
        self,
        old_sig: dict[str, Any],
        new_sig: dict[str, Any] | None,
        score: float,
    ) -> str:
        if new_sig is None:
            return "removed"
        if score < self.rename_threshold:
            return "removed"
        if old_sig.get("normalized_name") == new_sig.get("normalized_name"):
            return "same"
        return "renamed"

    def match_entities_between_versions(
        self,
        old_entities: list[dict[str, Any]],
        new_entities: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], EntityContinuityMetrics]:
        old_signatures = [self.build_entity_signature(entity) for entity in old_entities]
        new_signatures = [self.build_entity_signature(entity) for entity in new_entities]

        unmatched_new: dict[int, dict[str, Any]] = {
            int(sig["entity_id"]): sig for sig in new_signatures if int(sig["entity_id"]) > 0
        }
        links: list[dict[str, Any]] = []
        matched = 0
        renamed = 0
        removed = 0

        for old_sig in old_signatures:
            best_match: dict[str, Any] | None = None
            best_score = 0.0
            best_reason = "none"
            old_type = str(old_sig.get("entity_type") or "")

            for new_sig in unmatched_new.values():
                new_type = str(new_sig.get("entity_type") or "")
                if old_type and new_type and old_type != new_type:
                    continue
                score, reason = self._name_score(old_sig, new_sig)
                if score > best_score:
                    best_match = new_sig
                    best_score = score
                    best_reason = reason

            change_type = self.classify_entity_change(old_sig, best_match, best_score)
            if change_type in {"same", "renamed"} and best_match:
                matched += 1
                if change_type == "renamed":
                    renamed += 1
                links.append(
                    {
                        "old_entity_id": int(old_sig["entity_id"]),
                        "new_entity_id": int(best_match["entity_id"]),
                        "old_name": str(old_sig["canonical_name"] or ""),
                        "new_name": str(best_match["canonical_name"] or ""),
                        "link_type": change_type,
                        "confidence": float(best_score),
                        "reason": best_reason,
                    }
                )
                unmatched_new.pop(int(best_match["entity_id"]), None)
                continue

            removed += 1
            links.append(
                {
                    "old_entity_id": int(old_sig.get("entity_id") or 0) or None,
                    "new_entity_id": None,
                    "old_name": str(old_sig.get("canonical_name") or "") or None,
                    "new_name": None,
                    "link_type": "removed",
                    "confidence": 0.0,
                    "reason": "not_matched",
                }
            )

        for new_sig in unmatched_new.values():
            links.append(
                {
                    "old_entity_id": None,
                    "new_entity_id": int(new_sig["entity_id"]),
                    "old_name": None,
                    "new_name": str(new_sig.get("canonical_name") or "") or None,
                    "link_type": "new",
                    "confidence": 0.0,
                    "reason": "new_entity",
                }
            )

        return links, EntityContinuityMetrics(
            matched=matched,
            renamed=renamed,
            new_entities=len(unmatched_new),
            removed_entities=removed,
        )
