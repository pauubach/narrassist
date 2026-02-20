"""
Clasificación de identidad entre versiones de manuscritos.

Objetivo:
- Detectar same_document / uncertain / different_document
- Persistir decisiones y señales para auditoría
- Aplicar política de riesgo por licencias para casos "uncertain"
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

IDENTITY_SAME_DOCUMENT = "same_document"
IDENTITY_UNCERTAIN = "uncertain"
IDENTITY_DIFFERENT_DOCUMENT = "different_document"


@dataclass(frozen=True)
class IdentitySignals:
    """Señales explicables para decisión de identidad."""

    word_ratio: float
    paragraph_overlap: float
    shingle_jaccard: float
    segment_overlap: float
    average_segment_delta: float
    weighted_score: float

    def to_dict(self) -> dict[str, float]:
        return {
            "word_ratio": round(self.word_ratio, 4),
            "paragraph_overlap": round(self.paragraph_overlap, 4),
            "shingle_jaccard": round(self.shingle_jaccard, 4),
            "segment_overlap": round(self.segment_overlap, 4),
            "average_segment_delta": round(self.average_segment_delta, 4),
            "weighted_score": round(self.weighted_score, 4),
        }


@dataclass(frozen=True)
class IdentityDecision:
    """Resultado de clasificación."""

    classification: str
    confidence: float
    signals: IdentitySignals
    recommended_full_run: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "confidence": round(self.confidence, 4),
            "signals": self.signals.to_dict(),
            "recommended_full_run": self.recommended_full_run,
        }


class ManuscriptIdentityService:
    """Servicio de comparación robusta entre versión previa y nueva."""

    def _normalize(self, text: str) -> str:
        normalized = text.lower()
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = re.sub(r"[^\w\s]", "", normalized)
        return normalized.strip()

    def _paragraph_hashes(self, text: str) -> set[str]:
        hashes: set[str] = set()
        for block in re.split(r"\n\s*\n", text):
            paragraph = self._normalize(block)
            if len(paragraph) < 40:
                continue
            digest = hashlib.sha256(paragraph.encode("utf-8")).hexdigest()[:16]
            hashes.add(digest)
        return hashes

    def _shingles(self, text: str, n: int = 7, max_shingles: int = 6000) -> set[int]:
        normalized = self._normalize(text)
        if not normalized:
            return set()
        if len(normalized) <= n:
            return {hash(normalized) & 0xFFFFFFFF}
        result: set[int] = set()
        limit = len(normalized) - n + 1
        for i in range(limit):
            result.add(hash(normalized[i : i + n]) & 0xFFFFFFFF)
            if len(result) >= max_shingles:
                break
        return result

    def _segment_hashes(self, text: str, segment_chars: int = 1800) -> list[str]:
        normalized = self._normalize(text)
        if not normalized:
            return []
        hashes: list[str] = []
        for i in range(0, len(normalized), segment_chars):
            chunk = normalized[i : i + segment_chars]
            if len(chunk) < 120:
                continue
            hashes.append(hashlib.sha256(chunk.encode("utf-8")).hexdigest()[:24])
        return hashes

    def _jaccard(self, left: set[Any], right: set[Any]) -> float:
        if not left or not right:
            return 0.0
        union = left | right
        if not union:
            return 0.0
        return len(left & right) / len(union)

    def _compute_signals(self, old_text: str, new_text: str) -> IdentitySignals:
        old_words = max(1, len(old_text.split()))
        new_words = max(1, len(new_text.split()))
        word_ratio = min(old_words, new_words) / max(old_words, new_words)

        old_paragraphs = self._paragraph_hashes(old_text)
        new_paragraphs = self._paragraph_hashes(new_text)
        paragraph_overlap = self._jaccard(old_paragraphs, new_paragraphs)

        old_shingles = self._shingles(old_text)
        new_shingles = self._shingles(new_text)
        shingle_jaccard = self._jaccard(old_shingles, new_shingles)

        old_segments = self._segment_hashes(old_text)
        new_segments = self._segment_hashes(new_text)
        old_seg_set = set(old_segments)
        new_seg_set = set(new_segments)
        segment_overlap = self._jaccard(old_seg_set, new_seg_set)
        average_segment_delta = 1.0 - segment_overlap

        weighted_score = (
            (word_ratio * 0.20)
            + (paragraph_overlap * 0.30)
            + (shingle_jaccard * 0.35)
            + (segment_overlap * 0.15)
        )

        return IdentitySignals(
            word_ratio=word_ratio,
            paragraph_overlap=paragraph_overlap,
            shingle_jaccard=shingle_jaccard,
            segment_overlap=segment_overlap,
            average_segment_delta=average_segment_delta,
            weighted_score=weighted_score,
        )

    def classify(self, old_text: str, new_text: str) -> IdentityDecision:
        if not old_text.strip() or not new_text.strip():
            signals = self._compute_signals(old_text=old_text, new_text=new_text)
            return IdentityDecision(
                classification=IDENTITY_UNCERTAIN,
                confidence=0.5,
                signals=signals,
                recommended_full_run=True,
            )

        signals = self._compute_signals(old_text=old_text, new_text=new_text)
        score = signals.weighted_score
        old_words = len(old_text.split())
        new_words = len(new_text.split())
        is_short_document = min(old_words, new_words) < 300

        if is_short_document:
            short_score = (
                (signals.shingle_jaccard * 0.65)
                + (signals.word_ratio * 0.20)
                + (signals.paragraph_overlap * 0.15)
            )
            if short_score >= 0.70:
                classification = IDENTITY_SAME_DOCUMENT
                confidence = min(0.98, 0.65 + short_score * 0.33)
            elif short_score <= 0.30 and signals.shingle_jaccard <= 0.25:
                classification = IDENTITY_DIFFERENT_DOCUMENT
                confidence = min(0.98, 0.70 + (1.0 - short_score) * 0.25)
            else:
                classification = IDENTITY_UNCERTAIN
                confidence = 0.5 + abs(short_score - 0.5) * 0.3
            return IdentityDecision(
                classification=classification,
                confidence=confidence,
                signals=signals,
                recommended_full_run=signals.average_segment_delta > 0.20,
            )

        if score >= 0.78 and signals.word_ratio >= 0.55:
            classification = IDENTITY_SAME_DOCUMENT
            confidence = min(0.99, 0.70 + score * 0.30)
        elif score <= 0.40 or signals.word_ratio < 0.35:
            classification = IDENTITY_DIFFERENT_DOCUMENT
            confidence = min(0.99, 0.65 + (1.0 - score) * 0.35)
        else:
            classification = IDENTITY_UNCERTAIN
            confidence = 0.5 + abs(score - 0.63)

        recommended_full_run = signals.average_segment_delta > 0.25

        return IdentityDecision(
            classification=classification,
            confidence=confidence,
            signals=signals,
            recommended_full_run=recommended_full_run,
        )


class ManuscriptIdentityRepository:
    """Persistencia de checks de identidad y riesgo por licencia."""

    def __init__(self, db: Any):
        self.db = db

    def record_check(
        self,
        project_id: int,
        license_subject: str,
        previous_fingerprint: str,
        candidate_fingerprint: str,
        decision: IdentityDecision,
    ) -> int:
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO manuscript_identity_checks (
                    project_id,
                    license_subject,
                    previous_document_fingerprint,
                    candidate_document_fingerprint,
                    classification,
                    confidence,
                    score,
                    signals_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    license_subject,
                    previous_fingerprint,
                    candidate_fingerprint,
                    decision.classification,
                    decision.confidence,
                    decision.signals.weighted_score,
                    json.dumps(decision.signals.to_dict(), ensure_ascii=False),
                ),
            )
            return int(cursor.lastrowid)

    def get_last_check(self, project_id: int) -> dict[str, Any] | None:
        row = self.db.fetchone(
            """
            SELECT id, project_id, license_subject,
                   previous_document_fingerprint, candidate_document_fingerprint,
                   classification, confidence, score, signals_json, created_at
            FROM manuscript_identity_checks
            WHERE project_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (project_id,),
        )
        if not row:
            return None

        signals: dict[str, Any] = {}
        raw_signals = row["signals_json"]
        if raw_signals:
            try:
                signals = json.loads(raw_signals)
            except json.JSONDecodeError:
                signals = {}

        return {
            "id": int(row["id"]),
            "project_id": int(row["project_id"]),
            "license_subject": row["license_subject"],
            "previous_document_fingerprint": row["previous_document_fingerprint"],
            "candidate_document_fingerprint": row["candidate_document_fingerprint"],
            "classification": row["classification"],
            "confidence": float(row["confidence"] or 0.0),
            "score": float(row["score"] or 0.0),
            "signals": signals,
            "created_at": row["created_at"],
        }

    def uncertain_count_rolling(self, license_subject: str, days: int = 30) -> int:
        row = self.db.fetchone(
            """
            SELECT COUNT(*) AS cnt
            FROM manuscript_identity_checks
            WHERE license_subject = ?
              AND classification = ?
              AND datetime(created_at) >= datetime(?)
            """,
            (
                license_subject,
                IDENTITY_UNCERTAIN,
                (datetime.utcnow() - timedelta(days=days)).isoformat(),
            ),
        )
        return int(row["cnt"]) if row else 0

    def upsert_risk_state(
        self,
        license_subject: str,
        uncertain_count_30d: int,
        review_required: bool,
    ) -> None:
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO manuscript_identity_risk_state (
                    license_subject,
                    uncertain_count_30d,
                    review_required,
                    updated_at
                ) VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(license_subject) DO UPDATE SET
                    uncertain_count_30d = excluded.uncertain_count_30d,
                    review_required = excluded.review_required,
                    updated_at = datetime('now')
                """,
                (
                    license_subject,
                    uncertain_count_30d,
                    1 if review_required else 0,
                ),
            )

    def append_risk_event(
        self,
        license_subject: str,
        event_type: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO manuscript_identity_risk_events (
                    license_subject,
                    event_type,
                    details_json
                ) VALUES (?, ?, ?)
                """,
                (
                    license_subject,
                    event_type,
                    json.dumps(details or {}, ensure_ascii=False),
                ),
            )
