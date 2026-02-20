"""
Comparación entre versiones de manuscrito (capítulos + entidades).

Incluye:
- Diff de capítulos contra snapshot pre-análisis
- Vinculación de entidades entre versiones (same/renamed/new/removed)
- Persistencia de métricas agregadas por versión
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChapterDiffMetrics:
    total_previous: int
    total_current: int
    modified: int
    added: int
    removed: int
    changed_ratio: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_previous": self.total_previous,
            "total_current": self.total_current,
            "modified": self.modified,
            "added": self.added,
            "removed": self.removed,
            "changed_ratio": round(self.changed_ratio, 4),
        }


@dataclass(frozen=True)
class EntityDiffMetrics:
    matched: int
    renamed: int
    new_entities: int
    removed_entities: int

    def to_dict(self) -> dict[str, int]:
        return {
            "matched": self.matched,
            "renamed": self.renamed,
            "new_entities": self.new_entities,
            "removed_entities": self.removed_entities,
        }


class VersionDiffRepository:
    def __init__(self, db: Any):
        self.db = db

    def _normalize_name(self, value: str) -> str:
        normalized = value.lower().strip()
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = re.sub(r"[^\w\s]", "", normalized)
        return normalized

    def _token_jaccard(self, left: str, right: str) -> float:
        left_tokens = set(self._normalize_name(left).split())
        right_tokens = set(self._normalize_name(right).split())
        if not left_tokens or not right_tokens:
            return 0.0
        union = left_tokens | right_tokens
        if not union:
            return 0.0
        return len(left_tokens & right_tokens) / len(union)

    def _name_score(
        self,
        old_name: str,
        old_aliases: set[str],
        new_name: str,
        new_aliases: set[str],
        old_mentions: int,
        new_mentions: int,
        old_importance: str,
        new_importance: str,
    ) -> tuple[float, str]:
        old_norm = self._normalize_name(old_name)
        new_norm = self._normalize_name(new_name)
        mention_ratio = (
            min(old_mentions, new_mentions) / max(old_mentions, new_mentions)
            if old_mentions > 0 and new_mentions > 0
            else 0.5
        )
        importance_bonus = 0.05 if old_importance == new_importance and old_importance else 0.0
        if old_norm == new_norm:
            return min(1.0, 0.90 + (mention_ratio * 0.08) + importance_bonus), "exact_canonical"
        if old_norm in new_aliases:
            return min(1.0, 0.86 + (mention_ratio * 0.10) + importance_bonus), "old_in_new_aliases"
        if new_norm in old_aliases:
            return min(1.0, 0.83 + (mention_ratio * 0.10) + importance_bonus), "new_in_old_aliases"
        jacc = self._token_jaccard(old_name, new_name)
        if jacc >= 0.8:
            return min(
                1.0, 0.78 + ((jacc - 0.8) * 0.35) + (mention_ratio * 0.08) + importance_bonus
            ), "token_overlap"
        return (jacc * 0.6) + (mention_ratio * 0.15), "weak_overlap"

    def load_snapshot_chapter_texts(self, snapshot_id: int) -> dict[int, str]:
        rows = self.db.fetchall(
            """
            SELECT chapter_number, content_text
            FROM snapshot_chapters
            WHERE snapshot_id = ?
            ORDER BY chapter_number
            """,
            (snapshot_id,),
        )
        return {int(r["chapter_number"]): r["content_text"] or "" for r in rows}

    def compute_chapter_diff(
        self,
        snapshot_id: int | None,
        chapters_data: list[dict[str, Any]],
    ) -> ChapterDiffMetrics:
        if not snapshot_id:
            return ChapterDiffMetrics(
                total_previous=0,
                total_current=len(chapters_data),
                modified=len(chapters_data),
                added=len(chapters_data),
                removed=0,
                changed_ratio=1.0 if chapters_data else 0.0,
            )

        previous = self.load_snapshot_chapter_texts(snapshot_id)
        current = {
            int(ch.get("chapter_number", idx + 1)): (ch.get("content") or "")
            for idx, ch in enumerate(chapters_data)
        }

        prev_keys = set(previous.keys())
        curr_keys = set(current.keys())
        added = len(curr_keys - prev_keys)
        removed = len(prev_keys - curr_keys)
        common = prev_keys & curr_keys

        modified = 0
        for chapter_num in common:
            old = previous.get(chapter_num, "").strip()
            new = current.get(chapter_num, "").strip()
            if old != new:
                modified += 1

        denominator = max(1, len(common) + added + removed)
        changed_ratio = (modified + added + removed) / denominator

        return ChapterDiffMetrics(
            total_previous=len(previous),
            total_current=len(current),
            modified=modified,
            added=added,
            removed=removed,
            changed_ratio=changed_ratio,
        )

    def _load_snapshot_entities(self, snapshot_id: int) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            """
            SELECT original_entity_id, entity_type, canonical_name, aliases, mention_count, importance
            FROM snapshot_entities
            WHERE snapshot_id = ?
            """,
            (snapshot_id,),
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            aliases: list[str] = []
            raw_aliases = row["aliases"]
            if raw_aliases:
                try:
                    parsed = json.loads(raw_aliases)
                    if isinstance(parsed, list):
                        aliases = [str(a) for a in parsed if isinstance(a, str)]
                except json.JSONDecodeError:
                    aliases = []
            result.append(
                {
                    "entity_id": int(row["original_entity_id"]),
                    "entity_type": row["entity_type"] or "",
                    "canonical_name": row["canonical_name"] or "",
                    "aliases": aliases,
                    "mention_count": int(row["mention_count"] or 0),
                    "importance": str(row["importance"] or ""),
                }
            )
        return result

    def _load_current_entities(self, project_id: int) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            """
            SELECT id, entity_type, canonical_name, mention_count, importance
            FROM entities
            WHERE project_id = ? AND is_active = 1
            """,
            (project_id,),
        )
        entities: list[dict[str, Any]] = []
        for row in rows:
            alias_rows = self.db.fetchall(
                """
                SELECT DISTINCT surface_form
                FROM entity_mentions
                WHERE entity_id = ? AND surface_form != ?
                LIMIT 30
                """,
                (int(row["id"]), row["canonical_name"]),
            )
            aliases = [a["surface_form"] for a in alias_rows if a["surface_form"]]
            entities.append(
                {
                    "entity_id": int(row["id"]),
                    "entity_type": row["entity_type"] or "",
                    "canonical_name": row["canonical_name"] or "",
                    "aliases": aliases,
                    "mention_count": int(row["mention_count"] or 0),
                    "importance": str(row["importance"] or ""),
                }
            )
        return entities

    def compute_and_store_entity_links(
        self,
        project_id: int,
        snapshot_id: int | None,
    ) -> EntityDiffMetrics:
        if not snapshot_id:
            current = self._load_current_entities(project_id)
            return EntityDiffMetrics(
                matched=0,
                renamed=0,
                new_entities=len(current),
                removed_entities=0,
            )

        old_entities = self._load_snapshot_entities(snapshot_id)
        new_entities = self._load_current_entities(project_id)

        unmatched_new = {e["entity_id"]: e for e in new_entities}
        links: list[dict[str, Any]] = []
        matched = 0
        renamed = 0
        removed = 0

        for old in old_entities:
            best: dict[str, Any] | None = None
            best_score = 0.0
            best_reason = "none"
            old_type = old["entity_type"]
            old_aliases = {self._normalize_name(a) for a in old["aliases"]}
            old_aliases.add(self._normalize_name(old["canonical_name"]))

            for new in unmatched_new.values():
                new_type = new["entity_type"]
                if old_type and new_type and old_type != new_type:
                    continue
                new_aliases = {self._normalize_name(a) for a in new["aliases"]}
                new_aliases.add(self._normalize_name(new["canonical_name"]))
                score, reason = self._name_score(
                    old_name=old["canonical_name"],
                    old_aliases=old_aliases,
                    new_name=new["canonical_name"],
                    new_aliases=new_aliases,
                    old_mentions=int(old.get("mention_count", 0)),
                    new_mentions=int(new.get("mention_count", 0)),
                    old_importance=str(old.get("importance", "")),
                    new_importance=str(new.get("importance", "")),
                )
                if score > best_score:
                    best = new
                    best_score = score
                    best_reason = reason

            if best and best_score >= 0.78:
                matched += 1
                link_type = (
                    "same"
                    if self._normalize_name(old["canonical_name"])
                    == self._normalize_name(best["canonical_name"])
                    else "renamed"
                )
                if link_type == "renamed":
                    renamed += 1
                links.append(
                    {
                        "old_entity_id": old["entity_id"],
                        "new_entity_id": best["entity_id"],
                        "old_name": old["canonical_name"],
                        "new_name": best["canonical_name"],
                        "link_type": link_type,
                        "confidence": best_score,
                        "reason": best_reason,
                    }
                )
                unmatched_new.pop(best["entity_id"], None)
            else:
                removed += 1
                links.append(
                    {
                        "old_entity_id": old["entity_id"],
                        "new_entity_id": None,
                        "old_name": old["canonical_name"],
                        "new_name": None,
                        "link_type": "removed",
                        "confidence": 0.0,
                        "reason": "not_matched",
                    }
                )

        for new in unmatched_new.values():
            links.append(
                {
                    "old_entity_id": None,
                    "new_entity_id": new["entity_id"],
                    "old_name": None,
                    "new_name": new["canonical_name"],
                    "link_type": "new",
                    "confidence": 0.0,
                    "reason": "new_entity",
                }
            )

        with self.db.connection() as conn:
            conn.execute(
                """
                DELETE FROM entity_version_links
                WHERE project_id = ? AND snapshot_id = ?
                """,
                (project_id, snapshot_id),
            )
            for link in links:
                conn.execute(
                    """
                    INSERT INTO entity_version_links (
                        project_id, snapshot_id,
                        old_entity_id, new_entity_id,
                        old_name, new_name,
                        link_type, confidence, reason_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        snapshot_id,
                        link["old_entity_id"],
                        link["new_entity_id"],
                        link["old_name"],
                        link["new_name"],
                        link["link_type"],
                        link["confidence"],
                        json.dumps({"reason": link["reason"]}, ensure_ascii=False),
                    ),
                )

        return EntityDiffMetrics(
            matched=matched,
            renamed=renamed,
            new_entities=len(unmatched_new),
            removed_entities=removed,
        )

    def upsert_version_diff(
        self,
        project_id: int,
        version_num: int,
        snapshot_id: int | None,
        chapter_metrics: ChapterDiffMetrics,
        entity_metrics: EntityDiffMetrics,
    ) -> None:
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO version_diffs (
                    project_id, version_num, snapshot_id,
                    modified_chapters, added_chapters, removed_chapters,
                    chapter_change_ratio,
                    matched_entities, renamed_entities, new_entities, removed_entities
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, version_num) DO UPDATE SET
                    snapshot_id = excluded.snapshot_id,
                    modified_chapters = excluded.modified_chapters,
                    added_chapters = excluded.added_chapters,
                    removed_chapters = excluded.removed_chapters,
                    chapter_change_ratio = excluded.chapter_change_ratio,
                    matched_entities = excluded.matched_entities,
                    renamed_entities = excluded.renamed_entities,
                    new_entities = excluded.new_entities,
                    removed_entities = excluded.removed_entities
                """,
                (
                    project_id,
                    version_num,
                    snapshot_id,
                    chapter_metrics.modified,
                    chapter_metrics.added,
                    chapter_metrics.removed,
                    chapter_metrics.changed_ratio,
                    entity_metrics.matched,
                    entity_metrics.renamed,
                    entity_metrics.new_entities,
                    entity_metrics.removed_entities,
                ),
            )
