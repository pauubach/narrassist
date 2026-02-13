"""
Mixin de coreference resolver: Resolution voting, candidate filtering, chain building.

Extraido de coreference_resolver.py para reducir complejidad del monolito.
"""

from __future__ import annotations

import logging
import re

from .coreference_resolver import (FIRST_PERSON_PRONOUNS, NARRATOR_PATTERNS,
                                   CorefCandidate, CoreferenceChain,
                                   CorefMethod, Gender, Mention, MentionType,
                                   MentionVotingDetail, Number)

logger = logging.getLogger(__name__)


class CorefVotingMixin:
    """
    Mixin: Resolution voting, candidate filtering, chain building.

    Requiere que la clase que hereda tenga:
    - self.config (CorefConfig)
    - self.methods (dict[CorefMethod, CorefMethodInterface])
    """

    def _resolve_first_person(
        self,
        text: str,
        mentions: list[Mention],
        narrator_info: tuple[str, Gender] | None,
    ) -> list[tuple[Mention, Mention, float]]:
        """
        Resuelve menciones de primera persona al narrador.

        Solo asigna al narrador los pronombres que NO están en diálogo.
        """
        if not narrator_info:
            return []

        narrator_name, narrator_gender = narrator_info
        resolved = []

        # Crear mención sintética para el narrador
        narrator_mention = None
        for m in mentions:
            if m.mention_type == MentionType.PROPER_NOUN and m.text == narrator_name:
                narrator_mention = m
                break

        if not narrator_mention:
            # Buscar dónde se presenta el narrador
            for pattern in NARRATOR_PATTERNS:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    narrator_mention = Mention(
                        text=narrator_name,
                        start_char=match.start(1),
                        end_char=match.end(1),
                        mention_type=MentionType.PROPER_NOUN,
                        gender=narrator_gender,
                        number=Number.SINGULAR,
                        sentence_idx=0,  # Se actualizará si es necesario
                    )
                    break

        if not narrator_mention:
            return []

        # Vincular pronombres de primera persona fuera de diálogo
        for m in mentions:
            if m.mention_type != MentionType.PRONOUN:
                continue

            if m.text.lower() not in FIRST_PERSON_PRONOUNS:
                continue

            # Verificar si está en diálogo
            if self._is_in_dialogue(text, m.start_char, m.end_char):
                continue  # No asignar al narrador, puede ser otro personaje

            # Asignar al narrador
            resolved.append((m, narrator_mention, 0.9))
            logger.debug(
                f"'{m.text}' (pos {m.start_char}) -> narrador '{narrator_name}'"
            )

        return resolved

    def _filter_candidates(
        self,
        anaphor: Mention,
        candidates: list[Mention],
    ) -> list[Mention]:
        """Filtra candidatos válidos para una anáfora."""
        valid = []

        for candidate in candidates:
            # Debe estar antes de la anáfora
            if candidate.start_char >= anaphor.start_char:
                continue

            # Respetar límites de capítulo si está configurado
            if self.config.use_chapter_boundaries:
                if (
                    anaphor.chapter_idx is not None
                    and candidate.chapter_idx is not None
                    and anaphor.chapter_idx != candidate.chapter_idx
                ):
                    continue

            # Distancia máxima en oraciones
            sentence_distance = abs(anaphor.sentence_idx - candidate.sentence_idx)
            if sentence_distance > self.config.max_antecedent_distance:
                continue

            valid.append(candidate)

        return valid

    def _get_context(
        self,
        text: str,
        mention: Mention | None,
        window: int = 100,
        start: int | None = None,
        end: int | None = None,
    ) -> str:
        """Obtiene el contexto alrededor de una mención."""
        if mention:
            start = mention.start_char
            end = mention.end_char

        if start is None or end is None:
            return ""

        ctx_start = max(0, start - window)
        ctx_end = min(len(text), end + window)

        return text[ctx_start:ctx_end]

    def _weighted_vote(
        self,
        votes: dict[Mention, list[tuple[float, CorefMethod, str]]],
    ) -> tuple[Mention | None, float, dict[str, dict]]:
        """
        Realiza votación ponderada entre candidatos.

        Args:
            votes: Diccionario de candidato -> lista de (score, método, razón)

        Returns:
            (mejor_candidato, score_final, method_votes_detail)
            method_votes_detail: {method_name: {score, reasoning, weight}} para el candidato ganador
        """
        if not votes:
            return None, 0.0, {}

        candidate_scores: dict[Mention, float] = {}

        for candidate, method_votes in votes.items():
            total_weight = 0.0
            weighted_sum = 0.0

            for score, method, _ in method_votes:
                weight = self.config.method_weights.get(method, 0.1)
                weighted_sum += score * weight
                total_weight += weight

            if total_weight > 0:
                candidate_scores[candidate] = weighted_sum / total_weight

        if not candidate_scores:
            return None, 0.0, {}

        best = max(candidate_scores.items(), key=lambda x: x[1])
        best_candidate = best[0]
        best_score = best[1]

        # Construir detalle de votos del candidato ganador
        method_votes_detail: dict[str, dict] = {}
        for score, method, reasoning in votes.get(best_candidate, []):
            weight = self.config.method_weights.get(method, 0.1)
            method_votes_detail[method.value] = {
                "score": round(score, 3),
                "reasoning": reasoning,
                "weight": round(weight, 2),
                "weighted_score": round(score * weight, 3),
            }

        # BK-13: Calcular ambigüedad entre el mejor y segundo candidato
        sorted_scores = sorted(candidate_scores.values(), reverse=True)
        if len(sorted_scores) >= 2 and sorted_scores[0] > 0:
            ambiguity = 1.0 - (sorted_scores[0] - sorted_scores[1]) / sorted_scores[0]
            ambiguity = max(0.0, min(1.0, ambiguity))
        else:
            ambiguity = 0.0
        method_votes_detail["_ambiguity"] = {
            "score": round(ambiguity, 3),
            "reasoning": "margen entre mejor y segundo candidato",
        }

        return best_candidate, best_score, method_votes_detail

    def _build_chains(
        self,
        resolved_pairs: list[tuple[Mention, Mention, float]],
        antecedents: list[Mention],
    ) -> list[CoreferenceChain]:
        """Construye cadenas de correferencia a partir de pares resueltos."""
        # Usar union-find para agrupar
        parent: dict[Mention, Mention] = {}

        def find(m: Mention) -> Mention:
            if m not in parent:
                parent[m] = m
            if parent[m] != m:
                parent[m] = find(parent[m])
            return parent[m]

        def union(m1: Mention, m2: Mention) -> None:
            r1, r2 = find(m1), find(m2)
            if r1 != r2:
                # Preferir el antecedente como raíz
                if m2.mention_type == MentionType.PROPER_NOUN:
                    parent[r1] = r2
                else:
                    parent[r2] = r1

        # Unir pares resueltos
        for anaphor, antecedent, _ in resolved_pairs:
            union(anaphor, antecedent)

        # Agrupar por raíz
        groups: dict[Mention, list[Mention]] = {}
        all_mentions = set()
        for anaphor, antecedent, _ in resolved_pairs:
            all_mentions.add(anaphor)
            all_mentions.add(antecedent)

        for mention in all_mentions:
            root = find(mention)
            if root not in groups:
                groups[root] = []
            if mention not in groups[root]:
                groups[root].append(mention)

        # Crear cadenas
        chains = []
        for root, members in groups.items():
            chain = CoreferenceChain(
                mentions=sorted(members, key=lambda m: m.start_char)
            )

            # Calcular confianza promedio
            relevant_scores = [
                score
                for a, ant, score in resolved_pairs
                if a in members or ant in members
            ]
            if relevant_scores:
                chain.confidence = sum(relevant_scores) / len(relevant_scores)

            chains.append(chain)

        return chains
