"""
Detector de errores de concordancia gramatical.

Detecta discordancias de género y número entre:
- Sustantivos y sus determinantes/adjetivos
- Sujetos y verbos

Requiere spaCy para el análisis morfológico.
"""

from ..base import BaseDetector, CorrectionIssue
from ..config import AgreementConfig
from ..types import AgreementIssueType, CorrectionCategory


class AgreementDetector(BaseDetector):
    """
    Detecta errores de concordancia de género y número.

    Usa el análisis morfológico de spaCy para verificar que
    determinantes, adjetivos y sustantivos concuerden.
    """

    # Sustantivos con género gramatical diferente al aparente
    # (terminan en -a pero son masculinos, o viceversa)
    IRREGULAR_GENDER = {
        # Masculinos que terminan en -a
        "problema": "Masc",
        "tema": "Masc",
        "sistema": "Masc",
        "programa": "Masc",
        "clima": "Masc",
        "idioma": "Masc",
        "drama": "Masc",
        "dilema": "Masc",
        "poema": "Masc",
        "esquema": "Masc",
        "diploma": "Masc",
        "fantasma": "Masc",
        "mapa": "Masc",
        "día": "Masc",
        "sofá": "Masc",
        "planeta": "Masc",
        "cometa": "Masc",  # El cometa (astro)
        # Femeninos que terminan en -o
        "mano": "Fem",
        "foto": "Fem",
        "moto": "Fem",
        "radio": "Fem",  # La radio (aparato)
        # Otros irregulares
        "agua": "Fem",  # El agua (artículo masculino por eufonía, pero es femenino)
        "águila": "Fem",
        "alma": "Fem",
        "arma": "Fem",
        "hambre": "Fem",
    }

    # Sustantivos ambiguos (aceptan ambos géneros)
    AMBIGUOUS_GENDER = {
        "mar",  # El mar / La mar
        "azúcar",  # El azúcar / La azúcar
        "arte",  # El arte / Las artes
        "calor",  # El calor / La calor (regional)
    }

    def __init__(self, config: AgreementConfig | None = None):
        self.config = config or AgreementConfig()

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.AGREEMENT

    @property
    def requires_spacy(self) -> bool:
        return True

    def detect(
        self,
        text: str,
        chapter_index: int | None = None,
        spacy_doc=None,
    ) -> list[CorrectionIssue]:
        """
        Detecta errores de concordancia en el texto.

        Args:
            text: Texto a analizar
            chapter_index: Índice del capítulo
            spacy_doc: Documento spaCy (requerido)

        Returns:
            Lista de CorrectionIssue encontrados
        """
        if not self.config.enabled:
            return []

        if spacy_doc is None:
            # Sin spaCy no podemos hacer análisis morfológico
            return []

        issues: list[CorrectionIssue] = []

        # Detectar discordancia de género
        if self.config.check_gender:
            issues.extend(self._check_gender_agreement(spacy_doc, text, chapter_index))

        # Detectar discordancia de número
        if self.config.check_number:
            issues.extend(self._check_number_agreement(spacy_doc, text, chapter_index))

        return issues

    def _check_gender_agreement(
        self, doc, text: str, chapter_index: int | None
    ) -> list[CorrectionIssue]:
        """Verifica concordancia de género entre sustantivos y modificadores."""
        issues = []

        for token in doc:
            # Solo nos interesan sustantivos
            if token.pos_ != "NOUN":
                continue

            # Obtener género del sustantivo
            noun_gender = self._get_gender(token)
            if noun_gender is None:
                continue

            # Verificar determinantes y adjetivos relacionados
            for child in token.children:
                if child.pos_ not in ("DET", "ADJ"):
                    continue

                # SKIP: Si el adjetivo es un participio en construcción de gerundio/absoluto
                # Ej: "con la mandíbula apretada, visiblemente furioso"
                # "apretada" SÍ modifica "mandíbula", pero "furioso" modifica al SUJETO
                if child.pos_ == "ADJ" and self._is_subject_modifier(child):
                    continue  # No verificar, probablemente concuerda con el sujeto

                child_gender = self._get_gender(child)
                if child_gender is None:
                    continue

                # Comparar géneros
                if noun_gender != child_gender:
                    # Verificar si es un caso especial (ej: "el agua")
                    if self._is_valid_exception(token, child):
                        continue

                    confidence = self._calculate_confidence(token, child)
                    if confidence < self.config.min_confidence:
                        continue

                    issues.append(
                        CorrectionIssue(
                            category=self.category.value,
                            issue_type=AgreementIssueType.GENDER_DISAGREEMENT.value,
                            start_char=min(token.idx, child.idx),
                            end_char=max(
                                token.idx + len(token.text),
                                child.idx + len(child.text),
                            ),
                            text=f"{child.text} {token.text}",
                            explanation=(
                                f"Posible discordancia de género: "
                                f"'{child.text}' ({self._gender_name(child_gender)}) "
                                f"con '{token.text}' ({self._gender_name(noun_gender)})"
                            ),
                            suggestion=None,  # Corrector decide
                            confidence=confidence,
                            context=self._extract_context(
                                text, child.idx, token.idx + len(token.text)
                            ),
                            chapter_index=chapter_index,
                            rule_id="AGREE_GENDER",
                            extra_data={
                                "noun": token.text,
                                "noun_gender": noun_gender,
                                "modifier": child.text,
                                "modifier_gender": child_gender,
                            },
                        )
                    )

        return issues

    def _check_number_agreement(
        self, doc, text: str, chapter_index: int | None
    ) -> list[CorrectionIssue]:
        """Verifica concordancia de número entre sustantivos y modificadores."""
        issues = []

        for token in doc:
            if token.pos_ != "NOUN":
                continue

            # Obtener número del sustantivo
            noun_number = self._get_number(token)
            if noun_number is None:
                continue

            # Verificar determinantes y adjetivos relacionados
            for child in token.children:
                if child.pos_ not in ("DET", "ADJ"):
                    continue

                child_number = self._get_number(child)
                if child_number is None:
                    continue

                # Comparar números
                if noun_number != child_number:
                    confidence = self._calculate_confidence(token, child)
                    if confidence < self.config.min_confidence:
                        continue

                    issues.append(
                        CorrectionIssue(
                            category=self.category.value,
                            issue_type=AgreementIssueType.NUMBER_DISAGREEMENT.value,
                            start_char=min(token.idx, child.idx),
                            end_char=max(
                                token.idx + len(token.text),
                                child.idx + len(child.text),
                            ),
                            text=f"{child.text} {token.text}",
                            explanation=(
                                f"Posible discordancia de número: "
                                f"'{child.text}' ({self._number_name(child_number)}) "
                                f"con '{token.text}' ({self._number_name(noun_number)})"
                            ),
                            suggestion=None,
                            confidence=confidence,
                            context=self._extract_context(
                                text, child.idx, token.idx + len(token.text)
                            ),
                            chapter_index=chapter_index,
                            rule_id="AGREE_NUMBER",
                            extra_data={
                                "noun": token.text,
                                "noun_number": noun_number,
                                "modifier": child.text,
                                "modifier_number": child_number,
                            },
                        )
                    )

        return issues

    def _get_gender(self, token) -> str | None:
        """Obtiene el género de un token."""
        # Primero verificar irregulares
        lemma = token.lemma_.lower()
        if lemma in self.IRREGULAR_GENDER:
            return self.IRREGULAR_GENDER[lemma]

        # Sustantivos ambiguos - no reportar
        if lemma in self.AMBIGUOUS_GENDER:
            return None

        # Usar morfología de spaCy
        gender = token.morph.get("Gender")
        if gender:
            return str(gender[0])  # "Masc" o "Fem"

        return None

    def _get_number(self, token) -> str | None:
        """Obtiene el número de un token."""
        number = token.morph.get("Number")
        if number:
            return str(number[0])  # "Sing" o "Plur"
        return None

    def _is_subject_modifier(self, adj_token) -> bool:
        """
        Detecta si un adjetivo probablemente modifica al SUJETO de la oración
        en lugar del sustantivo más cercano.

        Ejemplos:
        - "dijo Carlos con la mandíbula apretada, visiblemente furioso"
          → "furioso" modifica a "Carlos" (sujeto), no a "mandíbula"
        - "María salió de la habitación, furiosa"
          → "furiosa" modifica a "María" (sujeto)

        Heurísticas:
        1. Adjetivo después de coma seguida de verbo conjugado
        2. Adjetivo modificado por adverbio de modo (visiblemente, claramente)
        3. Adjetivo en construcción absoluta (separado por coma)
        """
        # Buscar si hay adverbio de modo modificando este adjetivo
        for child in adj_token.children:
            if child.pos_ == "ADV" and child.dep_ == "advmod":
                # Adverbios como "visiblemente", "claramente" sugieren modificación del sujeto
                return True

        # Verificar si está después de una coma (construcción absoluta)
        idx = adj_token.i
        if idx > 0:
            prev_token = adj_token.doc[idx - 1]
            if prev_token.text == ",":
                # Adjetivo después de coma probablemente modifica al sujeto
                return True

        # Verificar si hay preposición "con" antes (complemento circunstancial)
        # "con la mandíbula apretada" → "apretada" SÍ modifica "mandíbula"
        # pero si hay coma después, el siguiente adjetivo modifica al sujeto
        head = adj_token.head
        if head.pos_ == "NOUN":
            for sibling in head.children:
                if sibling.dep_ == "case" and sibling.lower_ == "con":
                    # Es parte de un complemento con "con", probablemente modifica al sustantivo
                    return False

        return False

    def _is_valid_exception(self, noun, modifier) -> bool:
        """Verifica si es una excepción válida (ej: el agua)."""
        lemma = noun.lemma_.lower()

        # Sustantivos femeninos que usan artículo masculino por eufonía
        # (empiezan por a- o ha- tónicas)
        euphonic_feminines = {
            "agua",
            "águila",
            "alma",
            "arma",
            "área",
            "aula",
            "hambre",
            "hada",
            "hacha",
            "habla",
            "ama",
            "ala",
            "alba",
            "alga",
        }

        if lemma in euphonic_feminines:
            # Solo aplica con artículos, no con adjetivos
            if modifier.pos_ == "DET" and modifier.lemma_.lower() in ("el", "un"):
                return True

        return False

    def _calculate_confidence(self, noun, modifier) -> float:
        """Calcula confianza basada en la distancia y tipo de relación."""
        # Modificadores directamente adyacentes = más confianza
        distance = abs(noun.i - modifier.i)

        if distance == 1:
            return 0.9
        elif distance <= 3:
            return 0.8
        elif distance <= 5:
            return 0.7
        else:
            return 0.6

    def _gender_name(self, gender: str) -> str:
        """Nombre legible del género."""
        return {
            "Masc": "masculino",
            "Fem": "femenino",
        }.get(gender, gender)

    def _number_name(self, number: str) -> str:
        """Nombre legible del número."""
        return {
            "Sing": "singular",
            "Plur": "plural",
        }.get(number, number)
