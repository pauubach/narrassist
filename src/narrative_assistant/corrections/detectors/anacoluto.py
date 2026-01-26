"""
Detector de anacolutos (rupturas sintácticas).

Un anacoluto es una ruptura en la construcción gramatical de una oración,
donde la estructura iniciada no se completa o cambia a mitad de camino.

Detecta:
- Nominativus pendens: sujeto inicial sin conexión con el predicado
- Cambios de construcción: empezar con una estructura y cambiar a otra
- Cláusulas incompletas: subordinadas que no se cierran
- Cambios de sujeto problemáticos
- Modificadores sin referente claro (dangling modifiers)
"""

import re
from typing import Optional

from ..base import BaseDetector, CorrectionIssue
from ..config import AnacolutoConfig
from ..types import CorrectionCategory, AnacolutoIssueType


class AnacolutoDetector(BaseDetector):
    """
    Detecta anacolutos y rupturas sintácticas en el texto.

    Utiliza análisis de dependencias sintácticas de spaCy para identificar
    oraciones con estructuras gramaticales incompletas o rotas.
    """

    # Patrones para detectar marcadores de subordinación
    SUBORDINATE_MARKERS = re.compile(
        r'\b(que|quien|quienes|cual|cuales|cuyo|cuya|cuyos|cuyas|'
        r'donde|cuando|como|mientras|aunque|porque|si|sino|'
        r'ya que|puesto que|dado que|a pesar de que|pese a que|'
        r'con tal de que|siempre que|una vez que|antes de que|después de que)\b',
        re.IGNORECASE
    )

    # Patrones de inicio que pueden indicar nominativus pendens
    NOMINATIVUS_PATTERNS = [
        # "Juan, su hermano llegó" - nombre seguido de coma y pronombre posesivo
        re.compile(r'^([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s*,\s+(su|sus|mi|mis|tu|tus)\s', re.IGNORECASE),
        # "En cuanto a Juan, su hermano..."
        re.compile(r'^(en cuanto a|respecto a|en lo que respecta a|por lo que respecta a)\s+[^,]+,\s+(su|sus)\s', re.IGNORECASE),
        # "Lo que pasa es que" seguido de muchas subordinadas
        re.compile(r'^lo que pasa es que\b', re.IGNORECASE),
    ]

    # Marcadores de gerundio inicial (posible dangling modifier)
    GERUND_START = re.compile(r'^([A-ZÁÉÍÓÚÑ][a-záéíóúñ]*ndo)\b', re.IGNORECASE)

    # Patrón para detectar fin de oración
    SENTENCE_END = re.compile(r'[.!?]+(?:\s|$|"|\)|»|\')')

    def __init__(self, config: Optional[AnacolutoConfig] = None):
        self.config = config or AnacolutoConfig()
        self._nlp = None

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.ANACOLUTO

    @property
    def requires_spacy(self) -> bool:
        return True

    def _get_nlp(self):
        """Obtiene el modelo spaCy, cargándolo bajo demanda."""
        if self._nlp is None:
            try:
                from narrative_assistant.nlp.spacy_gpu import load_spacy_model
                self._nlp = load_spacy_model()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"No se pudo cargar spaCy: {e}")
                return None
        return self._nlp

    def detect(
        self,
        text: str,
        chapter_index: Optional[int] = None,
        **kwargs,
    ) -> list[CorrectionIssue]:
        """
        Detecta anacolutos en el texto.

        Args:
            text: Texto a analizar
            chapter_index: Índice del capítulo

        Returns:
            Lista de CorrectionIssue encontrados
        """
        if not self.config.enabled:
            return []

        issues: list[CorrectionIssue] = []

        # Dividir en oraciones
        sentences = self._split_sentences(text)

        for sentence_text, start, end in sentences:
            # Ignorar oraciones muy cortas
            word_count = len(sentence_text.split())
            if word_count < self.config.min_sentence_words:
                continue

            # Detectar nominativus pendens (sin spaCy)
            if self.config.check_nominativus_pendens:
                issue = self._check_nominativus_pendens(
                    sentence_text, start, end, chapter_index, text
                )
                if issue:
                    issues.append(issue)

            # Detectar construcciones rotas (requiere spaCy)
            nlp = self._get_nlp()
            if nlp:
                if self.config.check_broken_construction:
                    issue = self._check_broken_construction(
                        sentence_text, start, end, chapter_index, text, nlp
                    )
                    if issue:
                        issues.append(issue)

                if self.config.check_incomplete_clause:
                    issue = self._check_incomplete_clause(
                        sentence_text, start, end, chapter_index, text, nlp
                    )
                    if issue:
                        issues.append(issue)

                if self.config.check_dangling_modifier:
                    issue = self._check_dangling_modifier(
                        sentence_text, start, end, chapter_index, text, nlp
                    )
                    if issue:
                        issues.append(issue)

                if self.config.check_subject_shift:
                    issue = self._check_subject_shift(
                        sentence_text, start, end, chapter_index, text, nlp
                    )
                    if issue:
                        issues.append(issue)

        return issues

    def _split_sentences(self, text: str) -> list[tuple[str, int, int]]:
        """
        Divide el texto en oraciones, retornando (oración, start, end).
        """
        sentences = []
        current_start = 0

        for match in self.SENTENCE_END.finditer(text):
            end = match.end()
            sentence_text = text[current_start:end].strip()

            if sentence_text:
                sentences.append((sentence_text, current_start, end))

            current_start = end

        # Última oración si no termina en punto
        if current_start < len(text):
            remaining = text[current_start:].strip()
            if remaining and len(remaining) > 20:
                sentences.append((remaining, current_start, len(text)))

        return sentences

    def _check_nominativus_pendens(
        self,
        sentence: str,
        start: int,
        end: int,
        chapter_index: Optional[int],
        full_text: str,
    ) -> Optional[CorrectionIssue]:
        """
        Detecta nominativus pendens (sujeto "colgado").

        Ejemplo: "Juan, su hermano llegó tarde" -> "El hermano de Juan llegó tarde"
        """
        for pattern in self.NOMINATIVUS_PATTERNS:
            match = pattern.match(sentence)
            if match:
                return CorrectionIssue(
                    category=self.category.value,
                    issue_type=AnacolutoIssueType.NOMINATIVUS_PENDENS.value,
                    start_char=start,
                    end_char=end,
                    text=sentence[:100] + "..." if len(sentence) > 100 else sentence,
                    explanation=(
                        "Posible nominativus pendens: el sujeto inicial parece "
                        "desconectado del resto de la oración. "
                        "Considere reformular para una conexión más clara."
                    ),
                    suggestion=(
                        "Reformule la oración para conectar el sujeto con el predicado, "
                        "o use una construcción diferente."
                    ),
                    confidence=self.config.base_confidence,
                    context=self._extract_context(full_text, start, end),
                    chapter_index=chapter_index,
                    rule_id="ANACOLUTO_NOMINATIVUS",
                    extra_data={
                        "matched_pattern": pattern.pattern[:50],
                    },
                )
        return None

    def _check_broken_construction(
        self,
        sentence: str,
        start: int,
        end: int,
        chapter_index: Optional[int],
        full_text: str,
        nlp,
    ) -> Optional[CorrectionIssue]:
        """
        Detecta cambios de construcción sintáctica a mitad de oración.

        Usa análisis de dependencias para detectar oraciones donde la estructura
        cambia abruptamente.
        """
        # Contar subordinadas
        subordinates = self.SUBORDINATE_MARKERS.findall(sentence)
        sub_count = len(subordinates)

        # Si hay muchas subordinadas, analizar más a fondo
        if sub_count >= 3:
            doc = nlp(sentence)

            # Buscar si hay múltiples raíces (verbos principales)
            roots = [token for token in doc if token.dep_ == "ROOT"]

            # Buscar cláusulas sin verbo finito
            verbs = [token for token in doc if token.pos_ == "VERB"]
            finite_verbs = [
                v for v in verbs
                if v.morph.get("VerbForm") and v.morph.get("VerbForm")[0] in ["Fin"]
            ]

            # Heurística: muchas subordinadas + múltiples raíces = posible rotura
            if len(roots) > 1 or (sub_count > 3 and len(finite_verbs) < sub_count):
                return CorrectionIssue(
                    category=self.category.value,
                    issue_type=AnacolutoIssueType.BROKEN_CONSTRUCTION.value,
                    start_char=start,
                    end_char=end,
                    text=sentence[:100] + "..." if len(sentence) > 100 else sentence,
                    explanation=(
                        f"Oración compleja con {sub_count} subordinadas encadenadas. "
                        f"La estructura parece romperse o perder el hilo sintáctico. "
                        f"Considere dividirla en oraciones más simples."
                    ),
                    suggestion=(
                        "Divida la oración en varias más cortas, asegurando que "
                        "cada una tenga una estructura completa."
                    ),
                    confidence=min(0.9, self.config.base_confidence + (sub_count - 3) * 0.05),
                    context=self._extract_context(full_text, start, end),
                    chapter_index=chapter_index,
                    rule_id="ANACOLUTO_BROKEN",
                    extra_data={
                        "subordinate_count": sub_count,
                        "subordinates": subordinates[:5],
                        "root_count": len(roots),
                    },
                )
        return None

    def _check_incomplete_clause(
        self,
        sentence: str,
        start: int,
        end: int,
        chapter_index: Optional[int],
        full_text: str,
        nlp,
    ) -> Optional[CorrectionIssue]:
        """
        Detecta cláusulas incompletas (subordinadas que no se cierran).
        """
        doc = nlp(sentence)

        # Buscar subordinadas sin verbo finito
        # Esto es una heurística simplificada
        sconj_tokens = [token for token in doc if token.pos_ == "SCONJ"]

        for sconj in sconj_tokens:
            # Buscar si hay un verbo después de la conjunción subordinante
            has_verb_after = False
            for token in doc:
                if token.i > sconj.i and token.pos_ == "VERB":
                    has_verb_after = True
                    break

            if not has_verb_after:
                # Encontramos una subordinada sin verbo
                return CorrectionIssue(
                    category=self.category.value,
                    issue_type=AnacolutoIssueType.INCOMPLETE_CLAUSE.value,
                    start_char=start,
                    end_char=end,
                    text=sentence[:100] + "..." if len(sentence) > 100 else sentence,
                    explanation=(
                        f"La cláusula introducida por '{sconj.text}' parece incompleta. "
                        f"Falta el verbo o la estructura está incompleta."
                    ),
                    suggestion="Complete la cláusula subordinada o reformule la oración.",
                    confidence=0.7,
                    context=self._extract_context(full_text, start, end),
                    chapter_index=chapter_index,
                    rule_id="ANACOLUTO_INCOMPLETE",
                    extra_data={
                        "subordinator": sconj.text,
                    },
                )

        return None

    def _check_dangling_modifier(
        self,
        sentence: str,
        start: int,
        end: int,
        chapter_index: Optional[int],
        full_text: str,
        nlp,
    ) -> Optional[CorrectionIssue]:
        """
        Detecta modificadores "colgantes" (dangling modifiers).

        Ejemplo: "Caminando por el parque, el perro ladró" (¿quién caminaba?)
        """
        # Detectar oraciones que empiezan con gerundio
        match = self.GERUND_START.match(sentence)
        if match:
            doc = nlp(sentence)

            # Encontrar el gerundio
            gerund = None
            for token in doc:
                if token.pos_ == "VERB" and token.morph.get("VerbForm") == ["Ger"]:
                    gerund = token
                    break

            if gerund:
                # Buscar el sujeto de la oración principal
                main_subject = None
                for token in doc:
                    if token.dep_ in ["nsubj", "nsubj:pass"]:
                        main_subject = token
                        break

                # Si el sujeto es inanimado y el gerundio implica acción animada
                if main_subject:
                    # Heurística simple: si el gerundio está lejos del sujeto
                    # y el sujeto es después del gerundio, puede ser dangling
                    if main_subject.i > gerund.i + 3:
                        # Verbos que típicamente requieren agente animado
                        animate_verbs = {
                            "caminando", "corriendo", "pensando", "mirando",
                            "hablando", "escribiendo", "leyendo", "trabajando",
                            "jugando", "comiendo", "durmiendo", "esperando"
                        }
                        gerund_lemma = gerund.lemma_.lower()

                        if gerund_lemma in animate_verbs or gerund.text.lower() in animate_verbs:
                            return CorrectionIssue(
                                category=self.category.value,
                                issue_type=AnacolutoIssueType.DANGLING_MODIFIER.value,
                                start_char=start,
                                end_char=end,
                                text=sentence[:100] + "..." if len(sentence) > 100 else sentence,
                                explanation=(
                                    f"El gerundio '{gerund.text}' al inicio de la oración "
                                    f"puede no referirse claramente al sujeto "
                                    f"'{main_subject.text}'. Esto puede causar ambigüedad."
                                ),
                                suggestion=(
                                    "Asegúrese de que el sujeto de la oración sea también "
                                    "el agente del gerundio, o reformule la oración."
                                ),
                                confidence=0.65,
                                context=self._extract_context(full_text, start, end),
                                chapter_index=chapter_index,
                                rule_id="ANACOLUTO_DANGLING",
                                extra_data={
                                    "gerund": gerund.text,
                                    "subject": main_subject.text,
                                },
                            )
        return None

    def _check_subject_shift(
        self,
        sentence: str,
        start: int,
        end: int,
        chapter_index: Optional[int],
        full_text: str,
        nlp,
    ) -> Optional[CorrectionIssue]:
        """
        Detecta cambios problemáticos de sujeto dentro de una oración.

        Un cambio de sujeto problemático ocurre cuando:
        - El sujeto cambia a mitad de oración sin conector apropiado
        - Hay ambigüedad sobre quién realiza la acción
        - Se mezclan sujetos de forma confusa

        Ejemplo problemático: "Juan salió corriendo y tropezó María"
        (¿Quién tropezó? Ambiguo porque falta "y" o cambio de sujeto explícito)
        """
        doc = nlp(sentence)

        # Encontrar todos los sujetos (nsubj, nsubj:pass)
        subjects = []
        for token in doc:
            if token.dep_ in ["nsubj", "nsubj:pass"]:
                subjects.append({
                    "token": token,
                    "text": token.text,
                    "pos": token.i,
                    "head_verb": token.head,
                })

        # Si hay menos de 2 sujetos, no hay cambio
        if len(subjects) < 2:
            return None

        # Analizar si los cambios de sujeto son problemáticos
        for i in range(1, len(subjects)):
            prev_subj = subjects[i - 1]
            curr_subj = subjects[i]

            # Ignorar si son el mismo sujeto (correferencia obvia)
            if prev_subj["text"].lower() == curr_subj["text"].lower():
                continue

            # Ignorar si uno es pronombre que podría referirse al otro
            pronouns = {"él", "ella", "ellos", "ellas", "este", "esta", "ese", "esa"}
            if curr_subj["text"].lower() in pronouns:
                continue

            # Verificar si hay conector entre los sujetos
            tokens_between = [
                t for t in doc
                if prev_subj["pos"] < t.i < curr_subj["pos"]
            ]

            # Conectores que hacen válido un cambio de sujeto
            valid_connectors = {
                "y", "pero", "aunque", "mientras", "cuando", "porque",
                "sin embargo", "no obstante", "además", "también",
                "por su parte", "en cambio", "mientras tanto",
            }

            has_valid_connector = any(
                t.text.lower() in valid_connectors or
                t.dep_ == "cc"  # Conjunción coordinante
                for t in tokens_between
            )

            # Si no hay conector válido y los verbos están cerca, es problemático
            if not has_valid_connector:
                # Verificar que los verbos de ambos sujetos estén en la misma cláusula
                prev_verb = prev_subj["head_verb"]
                curr_verb = curr_subj["head_verb"]

                # Si los verbos son diferentes y no hay subordinación clara
                if prev_verb != curr_verb:
                    # Verificar si hay puntuación de separación
                    text_between = sentence[
                        prev_subj["token"].idx + len(prev_subj["text"]):
                        curr_subj["token"].idx
                    ]

                    # Si no hay coma ni punto y coma, es más problemático
                    if "," not in text_between and ";" not in text_between:
                        return CorrectionIssue(
                            category=self.category.value,
                            issue_type=AnacolutoIssueType.SUBJECT_SHIFT.value,
                            start_char=start,
                            end_char=end,
                            text=sentence[:100] + "..." if len(sentence) > 100 else sentence,
                            explanation=(
                                f"Cambio de sujeto potencialmente confuso: "
                                f"'{prev_subj['text']}' → '{curr_subj['text']}' "
                                f"sin conector o puntuación clara. "
                                f"El lector puede perder el hilo de quién realiza cada acción."
                            ),
                            suggestion=(
                                "Añada un conector ('y', 'mientras', 'por su parte') "
                                "o separe las oraciones con puntuación."
                            ),
                            confidence=self.config.base_confidence,
                            context=self._extract_context(full_text, start, end),
                            chapter_index=chapter_index,
                            rule_id="ANACOLUTO_SUBJECT_SHIFT",
                            extra_data={
                                "previous_subject": prev_subj["text"],
                                "current_subject": curr_subj["text"],
                            },
                        )

        return None
