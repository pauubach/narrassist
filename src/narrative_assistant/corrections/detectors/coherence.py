"""
Detector de coherencia editorial entre párrafos.

Detecta:
- Párrafos redundantes (repiten ideas anteriores)
- Saltos temáticos bruscos entre párrafos consecutivos
- Párrafos que deberían unificarse o separarse
- Transiciones pobres entre párrafos

Usa un sistema de 3-tier fallback:
1. LLM (Ollama) — análisis semántico completo
2. Embeddings (sentence-transformers) — similitud vectorial
3. Jaccard bag-of-words — heurístico léxico
"""

from __future__ import annotations

import json
import logging
import re

from ..base import BaseDetector, CorrectionIssue
from ..config import CoherenceConfig
from ..types import CoherenceIssueType, CorrectionCategory

logger = logging.getLogger(__name__)

# Umbral de similitud para considerar párrafos redundantes (embeddings)
_EMBEDDING_REDUNDANCY_THRESHOLD = 0.85

# Umbral de similitud Jaccard para considerar párrafos redundantes
_JACCARD_REDUNDANCY_THRESHOLD = 0.60

# Tamaño de chunk de párrafos para enviar al LLM
_LLM_CHUNK_SIZE = 8

# Timeout por chunk LLM (segundos)
_LLM_CHUNK_TIMEOUT = 120.0

# Stopwords para Jaccard (excluir palabras muy comunes)
_STOPWORDS = frozenset({
    "de", "la", "el", "en", "y", "a", "los", "las", "del", "al", "un", "una",
    "que", "es", "se", "no", "con", "por", "para", "su", "lo", "como", "más",
    "pero", "sus", "le", "ya", "o", "fue", "este", "ha", "sí", "porque",
    "esta", "entre", "cuando", "muy", "sin", "sobre", "ser", "también",
    "me", "hasta", "hay", "donde", "quien", "desde", "nos", "durante",
    "uno", "ni", "ante", "ellos", "e", "esto", "mí", "antes", "ese",
    "todo", "son", "dos", "puede", "cada", "así", "mismo",
})


class CoherenceDetector(BaseDetector):
    """Detecta problemas de coherencia editorial entre párrafos."""

    def __init__(self, config: CoherenceConfig | None = None):
        self.config = config or CoherenceConfig()

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.COHERENCE

    @property
    def requires_llm(self) -> bool:
        return True

    def detect(
        self,
        text: str,
        chapter_index: int | None = None,
        **kwargs,
    ) -> list[CorrectionIssue]:
        if not self.config.enabled:
            return []

        # Dividir en párrafos
        paragraphs = self._split_paragraphs(text)

        # Filtrar párrafos sustantivos (>= min_paragraph_words)
        substantive: list[tuple[int, str, int]] = []  # (index_original, texto, pos)
        for idx, (para_text, para_pos) in enumerate(paragraphs):
            word_count = len(para_text.split())
            if word_count >= self.config.min_paragraph_words:
                substantive.append((idx, para_text, para_pos))

        if len(substantive) < 2:
            return []

        # Limitar a max_paragraphs
        substantive = substantive[: self.config.max_paragraphs]

        # Intentar 3 tiers en orden
        issues: list[CorrectionIssue] = []
        method_used = "none"

        # Tier 1: LLM
        if self.config.use_llm:
            llm_issues = self._analyze_with_llm(substantive, text, chapter_index)
            if llm_issues is not None:
                issues = llm_issues
                method_used = "llm"

        # Tier 2: Embeddings (si LLM no disponible o falló)
        if method_used == "none":
            emb_issues = self._analyze_with_embeddings(substantive, text, chapter_index)
            if emb_issues is not None:
                issues = emb_issues
                method_used = "embeddings"

        # Tier 3: Jaccard heurístico (siempre disponible)
        if method_used == "none":
            issues = self._analyze_with_jaccard(substantive, text, chapter_index)
            method_used = "jaccard"

        # Anotar method_used en cada issue
        for issue in issues:
            if issue.extra_data:
                issue.extra_data["method_used"] = method_used
            else:
                issue.extra_data = {"method_used": method_used}

        return issues

    # =========================================================================
    # Tier 1: LLM (Ollama)
    # =========================================================================

    def _analyze_with_llm(
        self,
        paragraphs: list[tuple[int, str, int]],
        full_text: str,
        chapter_index: int | None,
    ) -> list[CorrectionIssue] | None:
        """Analiza coherencia con LLM. Retorna None si LLM no disponible."""
        try:
            from narrative_assistant.llm.client import get_llm_client, get_llm_scheduler
            from narrative_assistant.llm.prompts import COHERENCE_SYSTEM, COHERENCE_TEMPLATE
            from narrative_assistant.llm.sanitization import (
                sanitize_for_prompt,
                validate_llm_response,
            )
        except ImportError:
            logger.debug("LLM imports no disponibles, saltando tier LLM")
            return None

        client = get_llm_client()
        if not client or not client.is_available:
            logger.debug("LLM client no disponible, saltando tier LLM")
            return None

        scheduler = get_llm_scheduler()
        issues: list[CorrectionIssue] = []

        # Procesar en chunks
        for chunk_start in range(0, len(paragraphs), _LLM_CHUNK_SIZE):
            chunk = paragraphs[chunk_start : chunk_start + _LLM_CHUNK_SIZE]

            # Ceder al chat interactivo entre chunks
            if scheduler:
                try:
                    scheduler.yield_to_chat()
                except Exception:
                    pass

            # Construir texto de párrafos numerados
            numbered_paragraphs = []
            for i, (orig_idx, para_text, _) in enumerate(chunk):
                safe_text = sanitize_for_prompt(para_text, max_length=1500)
                numbered_paragraphs.append(f"[{chunk_start + i}] {safe_text}")

            paragraphs_text = "\n\n".join(numbered_paragraphs)

            prompt = COHERENCE_TEMPLATE.format(
                document_type="académico",
                start_index=chunk_start,
                paragraphs=paragraphs_text,
            )

            try:
                response = client.complete(
                    prompt=prompt,
                    system=COHERENCE_SYSTEM,
                    temperature=self.config.temperature,
                )
            except Exception as e:
                logger.warning("Error en llamada LLM para coherencia: %s", e)
                return None

            if not response:
                logger.debug("LLM retornó respuesta vacía para coherencia")
                return None

            data = validate_llm_response(response, expected_keys=["issues"])
            if not data:
                logger.warning("Respuesta LLM no válida para coherencia")
                return None

            llm_issues = data.get("issues", [])
            for raw_issue in llm_issues:
                if not isinstance(raw_issue, dict):
                    continue

                confidence = raw_issue.get("confidence", 0.0)
                if confidence < 0.70:
                    continue

                issue_type = raw_issue.get("type", "")
                para_indices = raw_issue.get("paragraph_indices", [])

                # Mapear tipo
                mapped_type = self._map_llm_issue_type(issue_type)
                if not mapped_type:
                    continue

                # Determinar posición en el texto original
                if para_indices and isinstance(para_indices, list):
                    # El LLM recibe índices absolutos en el prompt ([chunk_start+i])
                    # así que devuelve índices absolutos → usar directamente
                    first_idx = para_indices[0]
                    abs_idx = first_idx
                    if 0 <= abs_idx < len(paragraphs):
                        _, para_text, para_pos = paragraphs[abs_idx]
                        start_char = para_pos
                        end_char = para_pos + len(para_text)
                    else:
                        start_char, end_char = 0, min(50, len(full_text))
                else:
                    start_char, end_char = 0, min(50, len(full_text))

                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=mapped_type,
                        start_char=start_char,
                        end_char=end_char,
                        text=full_text[start_char:end_char][:150],
                        explanation=raw_issue.get("explanation", "Problema de coherencia detectado."),
                        suggestion=raw_issue.get("suggestion"),
                        confidence=min(0.95, float(confidence)),
                        context=self._extract_context(full_text, start_char, end_char),
                        chapter_index=chapter_index,
                        rule_id=f"COHERENCE_{mapped_type.upper()}",
                        extra_data={
                            "paragraph_indices": para_indices,
                        },
                    )
                )

        return issues

    # =========================================================================
    # Tier 2: Embeddings
    # =========================================================================

    def _analyze_with_embeddings(
        self,
        paragraphs: list[tuple[int, str, int]],
        full_text: str,
        chapter_index: int | None,
    ) -> list[CorrectionIssue] | None:
        """Analiza coherencia por similitud de embeddings. Retorna None si no disponible."""
        try:
            from narrative_assistant.nlp.embeddings import get_embeddings_model

            model = get_embeddings_model()
        except Exception:
            logger.debug("Embeddings no disponibles, saltando tier embeddings")
            return None

        issues: list[CorrectionIssue] = []

        # Codificar todos los párrafos
        texts = [p[1] for p in paragraphs]
        try:
            embeddings = model.encode(texts, normalize=True, show_progress=False)
        except Exception as e:
            logger.warning("Error al codificar embeddings: %s", e)
            return None

        import numpy as np

        # Comparar párrafos consecutivos
        for i in range(len(paragraphs) - 1):
            sim = float(np.dot(embeddings[i], embeddings[i + 1]))

            # Muy alta similitud → redundante
            if sim >= _EMBEDDING_REDUNDANCY_THRESHOLD:
                _, para_text, para_pos = paragraphs[i + 1]
                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=CoherenceIssueType.REDUNDANT_PARAGRAPH.value,
                        start_char=para_pos,
                        end_char=para_pos + len(para_text),
                        text=para_text[:150],
                        explanation=(
                            f"Este párrafo tiene una similitud muy alta ({sim:.0%}) "
                            f"con el párrafo anterior. Podrían ser redundantes."
                        ),
                        suggestion="Considere fusionar estos párrafos o eliminar la información duplicada.",
                        confidence=min(0.90, 0.70 + (sim - _EMBEDDING_REDUNDANCY_THRESHOLD) * 2),
                        context=self._extract_context(full_text, para_pos, para_pos + len(para_text)),
                        chapter_index=chapter_index,
                        rule_id="COHERENCE_REDUNDANT_PARAGRAPH",
                        extra_data={
                            "paragraph_indices": [i, i + 1],
                            "similarity": round(sim, 3),
                        },
                    )
                )

        return issues

    # =========================================================================
    # Tier 3: Jaccard (heurístico)
    # =========================================================================

    def _analyze_with_jaccard(
        self,
        paragraphs: list[tuple[int, str, int]],
        full_text: str,
        chapter_index: int | None,
    ) -> list[CorrectionIssue]:
        """Analiza coherencia con similitud Jaccard de bag-of-words."""
        issues: list[CorrectionIssue] = []

        # Tokenizar párrafos (bag of content words)
        bags = [self._bag_of_words(p[1]) for p in paragraphs]

        for i in range(len(paragraphs) - 1):
            if not bags[i] or not bags[i + 1]:
                continue

            jaccard = self._jaccard_similarity(bags[i], bags[i + 1])

            if jaccard >= _JACCARD_REDUNDANCY_THRESHOLD:
                _, para_text, para_pos = paragraphs[i + 1]
                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=CoherenceIssueType.REDUNDANT_PARAGRAPH.value,
                        start_char=para_pos,
                        end_char=para_pos + len(para_text),
                        text=para_text[:150],
                        explanation=(
                            f"Este párrafo comparte mucho vocabulario ({jaccard:.0%}) "
                            f"con el anterior. Podría ser redundante."
                        ),
                        suggestion="Considere fusionar estos párrafos o eliminar la información duplicada.",
                        confidence=min(0.85, 0.65 + (jaccard - _JACCARD_REDUNDANCY_THRESHOLD) * 0.5),
                        context=self._extract_context(full_text, para_pos, para_pos + len(para_text)),
                        chapter_index=chapter_index,
                        rule_id="COHERENCE_REDUNDANT_PARAGRAPH",
                        extra_data={
                            "paragraph_indices": [i, i + 1],
                            "jaccard_similarity": round(jaccard, 3),
                        },
                    )
                )

        return issues

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _split_paragraphs(text: str) -> list[tuple[str, int]]:
        """Divide texto en párrafos, retornando (texto, posición)."""
        result: list[tuple[str, int]] = []
        parts = re.split(r"\n\s*\n", text)
        current_pos = 0

        for part in parts:
            stripped = part.strip()
            if stripped:
                # Posición real en el texto original
                actual_pos = text.find(stripped, current_pos)
                if actual_pos == -1:
                    actual_pos = current_pos
                result.append((stripped, actual_pos))
            current_pos += len(part) + 1  # +1 for the split separator

        return result

    @staticmethod
    def _bag_of_words(text: str) -> set[str]:
        """Extrae bag-of-words sin stopwords."""
        words = re.findall(r"\b\w{3,}\b", text.lower())
        return {w for w in words if w not in _STOPWORDS}

    @staticmethod
    def _jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
        """Calcula similitud Jaccard entre dos conjuntos."""
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def _map_llm_issue_type(raw_type: str) -> str | None:
        """Mapea tipo de issue del LLM a CoherenceIssueType."""
        mapping = {
            "redundant": CoherenceIssueType.REDUNDANT_PARAGRAPH.value,
            "redundant_paragraph": CoherenceIssueType.REDUNDANT_PARAGRAPH.value,
            "topic_discontinuity": CoherenceIssueType.TOPIC_DISCONTINUITY.value,
            "logical_gap": CoherenceIssueType.TOPIC_DISCONTINUITY.value,
            "split_suggested": CoherenceIssueType.SPLIT_SUGGESTED.value,
            "split": CoherenceIssueType.SPLIT_SUGGESTED.value,
            "merge_suggested": CoherenceIssueType.MERGE_SUGGESTED.value,
            "merge": CoherenceIssueType.MERGE_SUGGESTED.value,
            "weak_transition": CoherenceIssueType.WEAK_TRANSITION.value,
            "irrelevant": CoherenceIssueType.IRRELEVANT_PARAGRAPH.value,
            "irrelevant_paragraph": CoherenceIssueType.IRRELEVANT_PARAGRAPH.value,
        }
        return mapping.get(raw_type)
