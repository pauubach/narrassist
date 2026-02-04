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

from ..base import BaseDetector, CorrectionIssue
from ..config import POVConfig
from ..types import CorrectionCategory, POVIssueType


class POVDetector(BaseDetector):
    """
    Detecta cambios e inconsistencias en el punto de vista narrativo.

    Analiza el uso de pronombres personales y verbos para identificar
    cambios no intencionales en la perspectiva narrativa.
    """

    # Pronombres de primera persona singular (solo pronombres, no verbos genéricos)
    FIRST_PERSON_SINGULAR_PRONOUNS = re.compile(r"\b(yo|me|mí|conmigo)\b", re.IGNORECASE)

    # Formas verbales específicas de primera persona singular
    # Lista explícita para evitar falsos positivos
    FIRST_PERSON_VERBS = re.compile(
        r"\b(soy|estoy|tengo|hago|voy|digo|sé|veo|quiero|puedo|debo|"
        r"pensé|sentí|miré|caminé|dije|vi|hice|fui|tuve|pude|quise|supe|"
        r"pienso|siento|miro|camino|hablo|escribo|leo|vivo|trabajo|"
        r"creí|sabía|recordé|noté|comprendí|percibí|imaginé|"
        r"creo|noto|comprendo|percibo|imagino|recuerdo)\b",
        re.IGNORECASE,
    )

    # Pronombres de primera persona plural
    FIRST_PERSON_PLURAL_PRONOUNS = re.compile(r"\b(nosotros|nosotras|nos)\b", re.IGNORECASE)

    # Verbos de primera persona plural (lista explícita)
    FIRST_PERSON_PLURAL_VERBS = re.compile(
        r"\b(somos|estamos|tenemos|hacemos|vamos|decimos|sabemos|vemos|"
        r"queremos|podemos|debemos|pensamos|sentimos|miramos|caminamos|"
        r"dijimos|vimos|hicimos|fuimos|tuvimos|pudimos|quisimos|supimos)\b",
        re.IGNORECASE,
    )

    # Pronombres de segunda persona (tú) - solo pronombres
    SECOND_PERSON_TU_PRONOUNS = re.compile(r"\b(tú|te|ti|contigo)\b", re.IGNORECASE)

    # Verbos de segunda persona singular (tú) - lista explícita
    SECOND_PERSON_TU_VERBS = re.compile(
        r"\b(eres|estás|tienes|haces|vas|dices|sabes|ves|quieres|puedes|debes|"
        r"piensas|sientes|miras|caminas|dijiste|viste|hiciste|fuiste|"
        r"tuviste|pudiste|quisiste|supiste|pensaste|sentiste|miraste)\b",
        re.IGNORECASE,
    )

    # Pronombres de segunda persona (usted)
    SECOND_PERSON_USTED = re.compile(r"\b(usted|ustedes)\b", re.IGNORECASE)

    # Pronombres de tercera persona
    THIRD_PERSON = re.compile(
        r"\b(él|ella|ellos|ellas|le|les|lo|la|los|las|se|sí|consigo)\b", re.IGNORECASE
    )

    # Verbos de percepción/pensamiento (para detectar focalizador)
    PERCEPTION_VERBS = re.compile(
        r"\b(pensó|pensaba|sentía|sentido|creía|creyó|imaginó|imaginaba|"
        r"sabía|supo|recordó|recordaba|veía|vio|oyó|oía|notó|notaba|"
        r"comprendió|comprendía|percibió|percibía|"
        r"piensa|siente|cree|imagina|sabe|recuerda|ve|oye|nota|comprende|percibe)\b",
        re.IGNORECASE,
    )

    # Patrón para fin de párrafo
    PARAGRAPH_END = re.compile(r"\n\s*\n")

    def __init__(self, config: POVConfig | None = None):
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
        chapter_index: int | None = None,
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
            paragraph_povs.append(
                {
                    "text": para_text,
                    "start": start,
                    "end": end,
                    "pov": pov,
                }
            )

        # Detectar cambios de persona
        if self.config.check_person_shift:
            issues.extend(self._check_person_shifts(paragraph_povs, chapter_index, text))

        # Detectar mezcla tú/usted
        if self.config.check_tu_usted_mix:
            issues.extend(self._check_tu_usted_mix(paragraph_povs, chapter_index, text))

        # Detectar cambios de focalizador (si hay tercera persona)
        if self.config.check_focalizer_shift:
            issues.extend(self._check_focalizer_shifts(paragraph_povs, chapter_index, text))

        # Detectar omnisciencia inconsistente
        if self.config.check_inconsistent_omniscience:
            issues.extend(self._check_inconsistent_omniscience(paragraph_povs, chapter_index, text))

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
        # Contar ocurrencias de cada tipo (pronombres + verbos)
        first_sing = len(self.FIRST_PERSON_SINGULAR_PRONOUNS.findall(text)) + len(
            self.FIRST_PERSON_VERBS.findall(text)
        )
        first_plur = len(self.FIRST_PERSON_PLURAL_PRONOUNS.findall(text)) + len(
            self.FIRST_PERSON_PLURAL_VERBS.findall(text)
        )
        second_tu = len(self.SECOND_PERSON_TU_PRONOUNS.findall(text)) + len(
            self.SECOND_PERSON_TU_VERBS.findall(text)
        )
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
        chapter_index: int | None,
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
        for _i, para in enumerate(paragraphs):
            current_pov = para["pov"]["dominant"]

            # Ignorar párrafos sin marcadores claros
            if para["pov"]["total_markers"] < 3:
                continue

            if current_pov and prev_pov and current_pov != prev_pov:
                # Verificar que es un cambio significativo (no dentro de diálogo)
                text_snippet = para["text"][:100]
                is_dialogue = text_snippet.strip().startswith(("—", "«", '"', "-"))

                if not is_dialogue:
                    # Determinar la severidad del cambio
                    is_major_shift = (
                        current_pov.startswith("first") and prev_pov.startswith("third")
                    ) or (current_pov.startswith("third") and prev_pov.startswith("first"))

                    confidence = 0.85 if is_major_shift else 0.7

                    issues.append(
                        CorrectionIssue(
                            category=self.category.value,
                            issue_type=POVIssueType.PERSON_SHIFT.value,
                            start_char=para["start"],
                            end_char=para["end"],
                            text=para["text"][:100] + "..."
                            if len(para["text"]) > 100
                            else para["text"],
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
        chapter_index: int | None,
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
                        text=para["text"][:100] + "..."
                        if len(para["text"]) > 100
                        else para["text"],
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
        chapter_index: int | None,
        full_text: str,
    ) -> list[CorrectionIssue]:
        """
        Detecta cambios de focalizador en narrativa de tercera persona.

        El focalizador es el personaje desde cuya perspectiva percibimos
        los eventos (quién piensa, siente, ve).

        Heurística: busca párrafos en tercera persona con verbos de percepción
        donde el sujeto de esos verbos cambia sin transición clara.
        """
        issues = []

        # Solo aplicar si hay tercera persona dominante
        third_person_paragraphs = [
            p
            for p in paragraphs
            if p["pov"]["dominant"] == "third" and len(p["pov"]["perception_verbs"]) > 0
        ]

        if len(third_person_paragraphs) < 2:
            return []

        # Patrones para extraer sujeto del verbo de percepción
        # "María pensó", "él sintió", "la mujer recordó"
        subject_pattern = re.compile(
            r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+|[Éé]l|[Ee]lla)\s+"
            r"(pensó|pensaba|sentía|creía|creyó|imaginó|imaginaba|"
            r"sabía|supo|recordó|recordaba|veía|vio|oyó|oía|notó|notaba|"
            r"comprendió|comprendía|percibió|percibía)",
            re.IGNORECASE,
        )

        prev_para = None
        prev_subjects = set()

        for para in third_person_paragraphs:
            # Extraer sujetos de verbos de percepción en este párrafo
            current_subjects = set()
            for match in subject_pattern.finditer(para["text"]):
                subject = match.group(1).lower()
                # Normalizar pronombres
                if subject in ("él", "ella"):
                    subject = "pronombre_3p"
                current_subjects.add(subject)

            if prev_para and prev_subjects and current_subjects:
                # Verificar si los sujetos cambiaron
                # Excluir pronombres de la comparación (podrían referirse al mismo personaje)
                prev_named = {s for s in prev_subjects if s != "pronombre_3p"}
                curr_named = {s for s in current_subjects if s != "pronombre_3p"}

                # Si hay nombres propios diferentes sin transición
                if prev_named and curr_named and prev_named != curr_named:
                    # Buscar si hay algún indicador de transición
                    para_start_lower = para["text"][:50].lower()
                    transition_markers = [
                        "mientras tanto",
                        "por su parte",
                        "en cambio",
                        "por otro lado",
                        "sin embargo",
                        "entretanto",
                        "al mismo tiempo",
                        "simultáneamente",
                    ]

                    has_transition = any(
                        marker in para_start_lower for marker in transition_markers
                    )

                    if not has_transition:
                        issues.append(
                            CorrectionIssue(
                                category=self.category.value,
                                issue_type=POVIssueType.FOCALIZER_SHIFT.value,
                                start_char=para["start"],
                                end_char=para["end"],
                                text=para["text"][:100] + "..."
                                if len(para["text"]) > 100
                                else para["text"],
                                explanation=(
                                    f"Posible cambio de focalizador: el párrafo anterior "
                                    f"muestra percepciones de {', '.join(prev_named)}, "
                                    f"pero este muestra percepciones de {', '.join(curr_named)}. "
                                    f"Verifique si el cambio de perspectiva es intencional."
                                ),
                                suggestion=(
                                    "Si el cambio es intencional, considere añadir un marcador de transición "
                                    "('Mientras tanto', 'Por su parte') o una separación de escena."
                                ),
                                confidence=0.65,  # Baja porque es heurística
                                context=self._extract_context(
                                    full_text, para["start"], para["end"]
                                ),
                                chapter_index=chapter_index,
                                rule_id="POV_FOCALIZER_SHIFT",
                                extra_data={
                                    "previous_focalizers": list(prev_named),
                                    "current_focalizers": list(curr_named),
                                },
                            )
                        )

            prev_para = para
            prev_subjects = current_subjects

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

    def _check_inconsistent_omniscience(
        self,
        paragraphs: list[dict],
        chapter_index: int | None,
        full_text: str,
    ) -> list[CorrectionIssue]:
        """
        Detecta omnisciencia inconsistente en narrativa de tercera persona.

        Un narrador omnisciente puede acceder a los pensamientos de todos los
        personajes. Pero si el texto alterna entre focalización limitada
        (solo un personaje) y omnisciencia, esto puede confundir al lector.

        Heurística: detecta cuando un texto en tercera persona limitada
        de repente muestra pensamientos de múltiples personajes en el mismo
        párrafo o sección.
        """
        issues = []

        # Solo aplicar a tercera persona
        third_person_paragraphs = [p for p in paragraphs if p["pov"]["dominant"] == "third"]

        if len(third_person_paragraphs) < 3:
            return []

        # Patrones para detectar acceso a pensamientos internos
        internal_thoughts_pattern = re.compile(
            r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+|[Éé]l|[Ee]lla)\s+"
            r"(pensó|pensaba|sintió|sentía|se preguntó|se preguntaba|"
            r"sabía que|no sabía|temía|esperaba|deseaba|creía|imaginó|"
            r"recordó|comprendió|se dio cuenta)",
            re.IGNORECASE,
        )

        # Analizar patrones de focalización
        para_focalizations = []
        for para in third_person_paragraphs:
            focalizers = set()
            for match in internal_thoughts_pattern.finditer(para["text"]):
                subject = match.group(1).lower()
                if subject not in ("él", "ella"):  # Solo nombres propios
                    focalizers.add(subject)
            para_focalizations.append(
                {
                    "para": para,
                    "focalizers": focalizers,
                    "count": len(focalizers),
                }
            )

        # Detectar inconsistencias: si la mayoría de párrafos tienen 0-1 focalizadores
        # pero algunos tienen 2+, puede indicar inconsistencia
        counts = [p["count"] for p in para_focalizations]
        limited_paras = sum(1 for c in counts if c <= 1)
        omniscient_paras = sum(1 for c in counts if c >= 2)

        # Si hay una mezcla clara (mayoría limitado, algunos omniscientes)
        if limited_paras >= 3 and omniscient_paras >= 1:
            # El texto parece mayormente limitado pero hay saltos a omnisciencia
            for pf in para_focalizations:
                if pf["count"] >= 2:
                    para = pf["para"]
                    focalizers = pf["focalizers"]

                    issues.append(
                        CorrectionIssue(
                            category=self.category.value,
                            issue_type=POVIssueType.INCONSISTENT_OMNISCIENCE.value,
                            start_char=para["start"],
                            end_char=para["end"],
                            text=para["text"][:100] + "..."
                            if len(para["text"]) > 100
                            else para["text"],
                            explanation=(
                                f"Posible inconsistencia en la omnisciencia del narrador: "
                                f"este párrafo muestra pensamientos internos de múltiples "
                                f"personajes ({', '.join(focalizers)}), pero el texto parece "
                                f"usar mayormente focalización limitada. Esto puede confundir al lector."
                            ),
                            suggestion=(
                                "Mantenga consistencia en el acceso a pensamientos: "
                                "use omnisciencia total o focalización limitada, pero evite mezclarlos "
                                "sin una estrategia clara."
                            ),
                            confidence=0.6,  # Baja porque requiere análisis narratológico profundo
                            context=self._extract_context(full_text, para["start"], para["end"]),
                            chapter_index=chapter_index,
                            rule_id="POV_INCONSISTENT_OMNISCIENCE",
                            extra_data={
                                "focalizers_in_paragraph": list(focalizers),
                                "limited_paragraphs": limited_paras,
                                "omniscient_paragraphs": omniscient_paras,
                            },
                        )
                    )

        return issues
