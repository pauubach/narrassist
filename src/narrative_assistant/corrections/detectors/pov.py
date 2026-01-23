"""
Detector de cambios de punto de vista narrativo.

Detecta inconsistencias en la perspectiva narrativa:
- Cambios de persona gramatical (primera a tercera, etc.)
- Cambios de focalizador (quién percibe/piensa)
- Mezcla de tú/usted
- Omnisciencia inconsistente
"""

import re
from collections import Counter
from typing import Optional

from ..base import BaseDetector, CorrectionIssue
from ..config import POVConfig
from ..types import CorrectionCategory, POVIssueType


class POVDetector(BaseDetector):
    """
    Detecta cambios e inconsistencias en el punto de vista narrativo.

    Analiza el uso de pronombres personales y verbos para identificar
    cambios no intencionales en la perspectiva narrativa.
    """

    # Pronombres y verbos de primera persona
    FIRST_PERSON_SINGULAR = re.compile(
        r'\b(yo|me|mí|conmigo)\b|'
        r'\b\w+(o|é|í)\b',  # Verbos: hablo, miré, sentí
        re.IGNORECASE
    )

    # Formas verbales específicas de primera persona singular
    FIRST_PERSON_VERBS = re.compile(
        r'\b(soy|estoy|tengo|hago|voy|digo|sé|veo|quiero|puedo|debo|'
        r'pensé|sentí|miré|caminé|dije|vi|hice|fui|tuve|pude|quise|supe|'
        r'pienso|siento|miro|camino|hablo|escribo|leo|como|vivo|trabajo)\b',
        re.IGNORECASE
    )

    # Pronombres de primera persona plural
    FIRST_PERSON_PLURAL = re.compile(
        r'\b(nosotros|nosotras|nos)\b|'
        r'\b\w+mos\b',  # Verbos: hablamos, miramos
        re.IGNORECASE
    )

    # Pronombres de segunda persona (tú)
    SECOND_PERSON_TU = re.compile(
        r'\b(tú|te|ti|contigo)\b|'
        r'\b\w+(as|es|ás|és)\b',  # Verbos: hablas, miras, podrás
        re.IGNORECASE
    )

    # Pronombres de segunda persona (usted)
    SECOND_PERSON_USTED = re.compile(
        r'\b(usted|ustedes)\b',
        re.IGNORECASE
    )

    # Pronombres de tercera persona
    THIRD_PERSON = re.compile(
        r'\b(él|ella|ellos|ellas|le|les|lo|la|los|las|se|sí|consigo)\b',
        re.IGNORECASE
    )

    # Verbos de percepción/pensamiento (para detectar focalizador)
    PERCEPTION_VERBS = re.compile(
        r'\b(pensó|pensaba|sentía|sentido|creía|creyó|imaginó|imaginaba|'
        r'sabía|supo|recordó|recordaba|veía|vio|oyó|oía|notó|notaba|'
        r'comprendió|comprendía|percibió|percibía|'
        r'piensa|siente|cree|imagina|sabe|recuerda|ve|oye|nota|comprende|percibe)\b',
        re.IGNORECASE
    )

    # Patrón para fin de párrafo
    PARAGRAPH_END = re.compile(r'\n\s*\n')

    def __init__(self, config: Optional[POVConfig] = None):
        self.config = config or POVConfig()
        self._nlp = None

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.POV

    @property
    def requires_spacy(self) -> bool:
        return False  # Funciona con regex, spaCy opcional para mejora

    def detect(
        self,
        text: str,
        chapter_index: Optional[int] = None,
        **kwargs,
    ) -> list[CorrectionIssue]:
        """
        Detecta problemas de punto de vista en el texto.

        Args:
            text: Texto a analizar
            chapter_index: Índice del capítulo

        Returns:
            Lista de CorrectionIssue encontrados
        """
        if not self.config.enabled:
            return []

        issues: list[CorrectionIssue] = []

        # Dividir en párrafos
        paragraphs = self._split_paragraphs(text)

        if len(paragraphs) < self.config.min_paragraphs:
            return []

        # Analizar POV de cada párrafo
        paragraph_povs = []
        for para_text, start, end in paragraphs:
            pov = self._analyze_paragraph_pov(para_text)
            paragraph_povs.append({
                "text": para_text,
                "start": start,
                "end": end,
                "pov": pov,
            })

        # Detectar cambios de persona
        if self.config.check_person_shift:
            issues.extend(
                self._check_person_shifts(paragraph_povs, chapter_index, text)
            )

        # Detectar mezcla tú/usted
        if self.config.check_tu_usted_mix:
            issues.extend(
                self._check_tu_usted_mix(paragraph_povs, chapter_index, text)
            )

        # Detectar cambios de focalizador (si hay tercera persona)
        if self.config.check_focalizer_shift:
            issues.extend(
                self._check_focalizer_shifts(paragraph_povs, chapter_index, text)
            )

        return issues

    def _split_paragraphs(self, text: str) -> list[tuple[str, int, int]]:
        """
        Divide el texto en párrafos, retornando (párrafo, start, end).
        """
        paragraphs = []
        current_start = 0

        for match in self.PARAGRAPH_END.finditer(text):
            end = match.start()
            para_text = text[current_start:end].strip()

            if para_text and len(para_text) > 30:  # Ignorar párrafos muy cortos
                paragraphs.append((para_text, current_start, end))

            current_start = match.end()

        # Último párrafo
        if current_start < len(text):
            remaining = text[current_start:].strip()
            if remaining and len(remaining) > 30:
                paragraphs.append((remaining, current_start, len(text)))

        return paragraphs

    def _analyze_paragraph_pov(self, text: str) -> dict:
        """
        Analiza el punto de vista de un párrafo.

        Returns:
            dict con conteos de cada persona gramatical y POV dominante
        """
        # Contar ocurrencias de cada tipo
        first_sing = len(self.FIRST_PERSON_VERBS.findall(text))
        first_plur = len(self.FIRST_PERSON_PLURAL.findall(text))
        second_tu = len(self.SECOND_PERSON_TU.findall(text))
        second_usted = len(self.SECOND_PERSON_USTED.findall(text))
        third = len(self.THIRD_PERSON.findall(text))

        # Contar verbos de percepción (para focalizador)
        perception = self.PERCEPTION_VERBS.findall(text)

        # Determinar POV dominante
        counts = {
            "first_singular": first_sing,
            "first_plural": first_plur,
            "second_tu": second_tu,
            "second_usted": second_usted,
            "third": third,
        }

        max_count = max(counts.values()) if counts.values() else 0
        dominant = None

        if max_count > 0:
            for pov, count in counts.items():
                if count == max_count:
                    dominant = pov
                    break

        return {
            "counts": counts,
            "dominant": dominant,
            "perception_verbs": perception,
            "total_markers": sum(counts.values()),
        }

    def _check_person_shifts(
        self,
        paragraphs: list[dict],
        chapter_index: Optional[int],
        full_text: str,
    ) -> list[CorrectionIssue]:
        """
        Detecta cambios de persona gramatical entre párrafos.
        """
        issues = []

        # Determinar el POV dominante del texto completo
        all_counts: Counter = Counter()
        for para in paragraphs:
            for pov, count in para["pov"]["counts"].items():
                all_counts[pov] += count

        if not all_counts:
            return []

        # POV principal del capítulo
        chapter_pov = all_counts.most_common(1)[0][0] if all_counts else None

        if not chapter_pov:
            return []

        # Buscar párrafos que cambien de POV
        prev_pov = None
        for i, para in enumerate(paragraphs):
            current_pov = para["pov"]["dominant"]

            # Ignorar párrafos sin marcadores claros
            if para["pov"]["total_markers"] < 3:
                continue

            if current_pov and prev_pov and current_pov != prev_pov:
                # Verificar que es un cambio significativo (no dentro de diálogo)
                text_snippet = para["text"][:100]
                is_dialogue = text_snippet.strip().startswith((
                    "—", "«", '"', "-"
                ))

                if not is_dialogue:
                    # Determinar la severidad del cambio
                    is_major_shift = (
                        (current_pov.startswith("first") and prev_pov.startswith("third")) or
                        (current_pov.startswith("third") and prev_pov.startswith("first"))
                    )

                    confidence = 0.85 if is_major_shift else 0.7

                    issues.append(
                        CorrectionIssue(
                            category=self.category.value,
                            issue_type=POVIssueType.PERSON_SHIFT.value,
                            start_char=para["start"],
                            end_char=para["end"],
                            text=para["text"][:100] + "..." if len(para["text"]) > 100 else para["text"],
                            explanation=(
                                f"Posible cambio de punto de vista: "
                                f"el párrafo anterior usa {self._pov_name(prev_pov)}, "
                                f"pero este usa {self._pov_name(current_pov)}. "
                                f"Verifique si es intencional."
                            ),
                            suggestion=(
                                "Mantenga consistencia en el punto de vista o "
                                "añada una transición clara si el cambio es intencional."
                            ),
                            confidence=confidence,
                            context=self._extract_context(full_text, para["start"], para["end"]),
                            chapter_index=chapter_index,
                            rule_id="POV_PERSON_SHIFT",
                            extra_data={
                                "previous_pov": prev_pov,
                                "current_pov": current_pov,
                                "chapter_dominant_pov": chapter_pov,
                            },
                        )
                    )

            prev_pov = current_pov

        return issues

    def _check_tu_usted_mix(
        self,
        paragraphs: list[dict],
        chapter_index: Optional[int],
        full_text: str,
    ) -> list[CorrectionIssue]:
        """
        Detecta mezcla de tú y usted en el mismo contexto.
        """
        issues = []

        for para in paragraphs:
            tu_count = para["pov"]["counts"]["second_tu"]
            usted_count = para["pov"]["counts"]["second_usted"]

            # Si hay mezcla significativa de tú y usted en el mismo párrafo
            if tu_count > 1 and usted_count > 1:
                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=POVIssueType.TU_USTED_MIX.value,
                        start_char=para["start"],
                        end_char=para["end"],
                        text=para["text"][:100] + "..." if len(para["text"]) > 100 else para["text"],
                        explanation=(
                            f"Mezcla de tratamiento: se detectan {tu_count} usos de 'tú' "
                            f"y {usted_count} usos de 'usted' en el mismo párrafo. "
                            f"Esto puede confundir al lector."
                        ),
                        suggestion=(
                            "Unifique el tratamiento: use consistentemente "
                            "'tú' o 'usted' según el tono del texto."
                        ),
                        confidence=0.85,
                        context=self._extract_context(full_text, para["start"], para["end"]),
                        chapter_index=chapter_index,
                        rule_id="POV_TU_USTED_MIX",
                        extra_data={
                            "tu_count": tu_count,
                            "usted_count": usted_count,
                        },
                    )
                )

        return issues

    def _check_focalizer_shifts(
        self,
        paragraphs: list[dict],
        chapter_index: Optional[int],
        full_text: str,
    ) -> list[CorrectionIssue]:
        """
        Detecta cambios de focalizador en narrativa de tercera persona.

        El focalizador es el personaje desde cuya perspectiva percibimos
        los eventos (quién piensa, siente, ve).
        """
        issues = []

        # Solo aplicar si hay tercera persona dominante
        third_person_paragraphs = [
            p for p in paragraphs
            if p["pov"]["dominant"] == "third" and len(p["pov"]["perception_verbs"]) > 0
        ]

        if len(third_person_paragraphs) < 2:
            return []

        # Agrupar párrafos consecutivos y buscar cambios bruscos
        # de verbos de percepción con diferentes sujetos
        # Esta es una heurística simplificada; una implementación completa
        # requeriría resolución de correferencias
        prev_para = None
        for para in third_person_paragraphs:
            if prev_para:
                # Verificar si hay un cambio significativo en patrones de percepción
                prev_verbs = set(v.lower() for v in prev_para["pov"]["perception_verbs"])
                curr_verbs = set(v.lower() for v in para["pov"]["perception_verbs"])

                # Si ambos tienen muchos verbos de percepción y son diferentes
                if len(prev_verbs) >= 2 and len(curr_verbs) >= 2:
                    # Heurística: si hay verbos en ambos pero el texto no parece continuar
                    # el mismo hilo, puede ser un cambio de focalizador
                    # Esto es muy simplificado; en producción se usaría LLM
                    pass  # Por ahora no generamos alertas aquí sin LLM

            prev_para = para

        return issues

    def _pov_name(self, pov: str) -> str:
        """Nombre legible del POV."""
        names = {
            "first_singular": "primera persona singular (yo)",
            "first_plural": "primera persona plural (nosotros)",
            "second_tu": "segunda persona (tú)",
            "second_usted": "segunda persona (usted)",
            "third": "tercera persona (él/ella)",
        }
        return names.get(pov, pov)
