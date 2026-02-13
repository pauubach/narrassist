"""
Scoring de ambigüedad para resolución de sujetos omitidos (pro-drop).

En español, el sujeto puede omitirse cuando la conjugación verbal es
inequívoca ("Salió furioso" → ¿quién salió?). Este módulo puntúa
candidatos usando múltiples factores y calcula un score de ambigüedad
que indica si la resolución es clara o disputada.

BK-13: Pro-drop Ambiguity Scoring
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .coreference_resolver import Gender, Mention, MentionType, Number

logger = logging.getLogger(__name__)


@dataclass
class SaliencyEntry:
    """Datos de saliencia para una entidad."""

    entity_name: str
    mention_count: int = 0
    last_position: int = 0
    subject_count: int = 0
    total_roles: int = 0


class SaliencyTracker:
    """Tracker multi-factor de saliencia de entidades para un segmento de texto."""

    def __init__(self) -> None:
        self._entries: dict[str, SaliencyEntry] = {}
        self._text_length: int = 0
        self._max_mentions: int = 0

    @classmethod
    def build_from_mentions(
        cls, mentions: list[Mention], text_length: int = 0
    ) -> SaliencyTracker:
        """Construye un tracker a partir de una lista de menciones."""
        tracker = cls()
        tracker._text_length = text_length

        for m in mentions:
            if m.mention_type == MentionType.PROPER_NOUN:
                key = m.text.lower()
                tracker.update(key, m.start_char, is_subject=False)

        return tracker

    def update(self, entity_name: str, position: int, is_subject: bool) -> None:
        """Actualiza la saliencia de una entidad."""
        key = entity_name.lower()
        if key not in self._entries:
            self._entries[key] = SaliencyEntry(entity_name=key)

        entry = self._entries[key]
        entry.mention_count += 1
        entry.last_position = max(entry.last_position, position)
        entry.total_roles += 1
        if is_subject:
            entry.subject_count += 1

        self._max_mentions = max(self._max_mentions, entry.mention_count)

    def get_saliency(self, entity_name: str) -> float:
        """Retorna saliencia normalizada 0-1 para una entidad."""
        key = entity_name.lower()
        entry = self._entries.get(key)
        if not entry or self._max_mentions == 0:
            return 0.0

        freq_score = entry.mention_count / self._max_mentions

        # Bonus por rol de sujeto
        subj_ratio = (
            entry.subject_count / entry.total_roles if entry.total_roles > 0 else 0.0
        )
        subj_bonus = subj_ratio * 0.3

        return min(1.0, freq_score * 0.7 + subj_bonus)

    def get_recency(self, entity_name: str, current_pos: int) -> float:
        """Retorna score de recencia 0-1 (mayor = más reciente)."""
        key = entity_name.lower()
        entry = self._entries.get(key)
        if not entry:
            return 0.0

        distance = current_pos - entry.last_position
        if distance <= 0:
            return 1.0

        # Decay exponencial: distancia 0 → 1.0, 500+ → ~0
        return max(0.0, 1.0 - (distance / 500.0))


@dataclass
class CandidateScore:
    """Score de un candidato para resolución de pro-drop."""

    mention: Mention
    score: float
    factors: dict[str, float] = field(default_factory=dict)
    reasoning: str = ""


class ProDropAmbiguityScorer:
    """Puntúa candidatos para resolución de pronombre cero con detección de ambigüedad."""

    FACTOR_WEIGHTS = {
        "recency": 0.30,
        "saliency": 0.25,
        "gender": 0.20,
        "discourse": 0.15,
        "number": 0.10,
    }

    def score_candidates(
        self,
        zero: Mention,
        candidates: list[Mention],
        tracker: SaliencyTracker,
        text: str,
    ) -> list[CandidateScore]:
        """Puntúa todos los candidatos para un sujeto omitido. Retorna ordenados por score desc."""
        if not candidates:
            return []

        text_length = len(text) if text else 1
        scored: list[CandidateScore] = []

        for candidate in candidates:
            factors: dict[str, float] = {}
            reasons: list[str] = []

            # Recencia
            recency = self._score_recency(zero, candidate, text_length)
            factors["recency"] = recency
            if recency > 0.7:
                reasons.append("muy cercano")

            # Saliencia
            saliency = self._score_saliency(candidate, tracker)
            factors["saliency"] = saliency
            if saliency > 0.5:
                reasons.append(f"saliente ({saliency:.2f})")

            # Concordancia de género
            gender = self._score_gender(zero, candidate)
            factors["gender"] = gender
            if gender < 0.5:
                reasons.append("género no concuerda")

            # Discurso (sujeto de oración anterior)
            discourse = self._score_discourse(zero, candidate)
            factors["discourse"] = discourse
            if discourse > 0.5:
                reasons.append("sujeto previo")

            # Concordancia de número
            number = self._score_number(zero, candidate)
            factors["number"] = number
            if number < 0.5:
                reasons.append("número no concuerda")

            # Score ponderado
            total = sum(
                factors[k] * self.FACTOR_WEIGHTS[k] for k in self.FACTOR_WEIGHTS
            )

            scored.append(
                CandidateScore(
                    mention=candidate,
                    score=total,
                    factors=factors,
                    reasoning=(
                        "; ".join(reasons) if reasons else "sin factores destacados"
                    ),
                )
            )

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored

    @staticmethod
    def calculate_ambiguity(scores: list[CandidateScore]) -> float:
        """
        Calcula ambigüedad de la resolución.

        1.0 = máxima ambigüedad (top-2 empatados)
        0.0 = sin ambigüedad (ganador claro o un solo candidato)
        """
        if len(scores) <= 1:
            return 0.0

        best = scores[0].score
        second = scores[1].score

        if best <= 0:
            return 1.0

        margin = (best - second) / best
        return max(0.0, min(1.0, 1.0 - margin))

    def _score_recency(
        self, zero: Mention, candidate: Mention, text_length: int
    ) -> float:
        """Score por cercanía posicional. Mayor = más cerca."""
        distance = zero.start_char - candidate.end_char
        if distance <= 0:
            return 0.1  # Candidato después del verbo: poco probable

        # Normalizar: 0 chars → 1.0, 500+ → ~0
        return max(0.0, 1.0 - (distance / 500.0))

    def _score_saliency(self, candidate: Mention, tracker: SaliencyTracker) -> float:
        """Score por saliencia en el discurso."""
        return tracker.get_saliency(candidate.text)

    def _score_gender(self, zero: Mention, candidate: Mention) -> float:
        """Score por concordancia de género. 1.0 si concuerda, 0.0 si no."""
        if zero.gender == Gender.UNKNOWN or candidate.gender == Gender.UNKNOWN:
            return 0.5  # No se puede determinar → neutro
        return 1.0 if zero.gender == candidate.gender else 0.0

    def _score_discourse(self, zero: Mention, candidate: Mention) -> float:
        """Score por posición discursiva. Bonus si es sujeto de oración anterior."""
        sentence_dist = zero.sentence_idx - candidate.sentence_idx
        if sentence_dist == 1:
            # Oración inmediatamente anterior: alta probabilidad
            if candidate.mention_type == MentionType.PROPER_NOUN:
                return 1.0
            return 0.7
        elif sentence_dist == 0:
            # Misma oración (antes del verbo)
            return 0.8
        elif sentence_dist == 2:
            return 0.3
        return 0.0

    def _score_number(self, zero: Mention, candidate: Mention) -> float:
        """Score por concordancia de número. 1.0 si concuerda, 0.0 si no."""
        if zero.number == Number.UNKNOWN or candidate.number == Number.UNKNOWN:
            return 0.5  # No se puede determinar → neutro
        return 1.0 if zero.number == candidate.number else 0.0
