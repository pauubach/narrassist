"""
Mixin de coreference resolver: Mention extraction (full NER, simple, definite NPs, zero mentions).

Extraido de coreference_resolver.py para reducir complejidad del monolito.
"""

from __future__ import annotations

import logging
import re

from .coreference_resolver import (
    ALL_PERSON_NOUNS,
    DEFINITE_ARTICLES,
    PERSON_NOUNS_FEMININE,
    PERSON_NOUNS_MASCULINE,
    SPANISH_DEMONSTRATIVES,
    SPANISH_POSSESSIVES,
    SPANISH_PRONOUNS,
    Gender,
    Mention,
    MentionType,
    Number,
)

logger = logging.getLogger(__name__)


class CorefMentionExtractionMixin:
    """
    Mixin: Mention extraction (full NER, simple, definite NPs, zero mentions).

    Requiere que la clase que hereda tenga:
    - self.config (CorefConfig)
    - self.methods (dict[CorefMethod, CorefMethodInterface])
    """

    def _extract_mentions(
        self,
        text: str,
        chapters: list[dict] | None = None,
    ) -> list[Mention]:
        """Extrae menciones del texto usando spaCy."""
        mentions = []

        try:
            from ..nlp.spacy_gpu import load_spacy_model

            nlp = load_spacy_model()
        except Exception as e:
            logger.warning(f"No se pudo cargar spaCy para extracción: {e}")
            # Fallback a extracción simple
            return self._extract_mentions_simple(text, chapters)

        doc = nlp(text)

        # Mapear posición a capítulo
        def get_chapter_idx(char_pos: int) -> int | None:
            if not chapters:
                return None
            for i, ch in enumerate(chapters):
                if ch.get("start_char", 0) <= char_pos < ch.get("end_char", len(text)):
                    return i
            return None

        # Mapear oración a índice real (no índice de token)
        sentence_to_idx = {}
        for i, sent in enumerate(doc.sents):
            sentence_to_idx[sent.start] = i

        def get_sentence_idx(token_or_span) -> int:
            """Obtiene el índice real de la oración (0, 1, 2, ...)."""
            sent = token_or_span.sent if hasattr(token_or_span, "sent") else None
            if sent is None:
                return 0
            return sentence_to_idx.get(sent.start, 0)

        # Extraer entidades nombradas (nombres propios)
        for ent in doc.ents:
            if ent.label_ in ("PER", "PERSON", "LOC", "ORG"):
                # Filtrar menciones inválidas
                if not self._is_valid_mention(ent.text):
                    logger.debug(f"Mención filtrada: '{ent.text}'")
                    continue

                gender, number = self._infer_gender_number(ent.text, doc[ent.start])
                mentions.append(
                    Mention(
                        text=ent.text,
                        start_char=ent.start_char,
                        end_char=ent.end_char,
                        mention_type=MentionType.PROPER_NOUN,
                        gender=gender,
                        number=number,
                        sentence_idx=get_sentence_idx(doc[ent.start]),
                        chapter_idx=get_chapter_idx(ent.start_char),
                        context=self._get_context(
                            text, None, window=50, start=ent.start_char, end=ent.end_char
                        ),
                    )
                )

        # Extraer pronombres
        for token in doc:
            text_lower = token.text.lower()

            # Pronombres personales
            if text_lower in SPANISH_PRONOUNS:
                gender, number = SPANISH_PRONOUNS[text_lower]
                mentions.append(
                    Mention(
                        text=token.text,
                        start_char=token.idx,
                        end_char=token.idx + len(token.text),
                        mention_type=MentionType.PRONOUN,
                        gender=gender,
                        number=number,
                        sentence_idx=get_sentence_idx(token),
                        chapter_idx=get_chapter_idx(token.idx),
                        context=self._get_context(
                            text, None, window=50, start=token.idx, end=token.idx + len(token.text)
                        ),
                    )
                )

            # Demostrativos
            elif text_lower in SPANISH_DEMONSTRATIVES:
                gender, number = SPANISH_DEMONSTRATIVES[text_lower]
                mentions.append(
                    Mention(
                        text=token.text,
                        start_char=token.idx,
                        end_char=token.idx + len(token.text),
                        mention_type=MentionType.DEMONSTRATIVE,
                        gender=gender,
                        number=number,
                        sentence_idx=get_sentence_idx(token),
                        chapter_idx=get_chapter_idx(token.idx),
                    )
                )

            # Posesivos (su, sus, mi, mis, tu, tus, etc.)
            # IMPORTANTE: Clasificados como POSSESSIVE, no PRONOUN
            elif text_lower in SPANISH_POSSESSIVES:
                gender, number = SPANISH_POSSESSIVES[text_lower]
                mentions.append(
                    Mention(
                        text=token.text,
                        start_char=token.idx,
                        end_char=token.idx + len(token.text),
                        mention_type=MentionType.POSSESSIVE,
                        gender=gender,
                        number=number,
                        sentence_idx=get_sentence_idx(token),
                        chapter_idx=get_chapter_idx(token.idx),
                        context=self._get_context(
                            text, None, window=50, start=token.idx, end=token.idx + len(token.text)
                        ),
                    )
                )

        # Extraer sintagmas nominales definidos (DEFINITE_NP)
        # Patrones como "el padre", "la niña", "el conductor del autobús"
        definite_nps = self._extract_definite_nps(doc, text, get_sentence_idx, get_chapter_idx)
        mentions.extend(definite_nps)

        # Extraer sujetos omitidos (pro-drop / ZERO)
        # Solo 3ª persona singular/plural — 1ª/2ª persona no son útiles para correferencia
        zero_mentions = self._extract_zero_mentions(doc, text, get_sentence_idx, get_chapter_idx)
        mentions.extend(zero_mentions)

        n_total = len(mentions)
        n_zero = len(zero_mentions)
        logger.info(
            "Menciones extraídas: %d total, %d ZERO/pro-drop (%.0f%%)",
            n_total,
            n_zero,
            (n_zero / n_total * 100) if n_total else 0,
        )

        # Ordenar por posición
        mentions.sort(key=lambda m: m.start_char)

        return mentions

    def _extract_mentions_simple(
        self,
        text: str,
        chapters: list[dict] | None = None,
    ) -> list[Mention]:
        """Extracción simple de menciones sin spaCy."""
        mentions = []

        # Buscar pronombres con regex
        for pronoun, (gender, number) in SPANISH_PRONOUNS.items():
            pattern = rf"\b{re.escape(pronoun)}\b"
            for match in re.finditer(pattern, text, re.IGNORECASE):
                mentions.append(
                    Mention(
                        text=match.group(),
                        start_char=match.start(),
                        end_char=match.end(),
                        mention_type=MentionType.PRONOUN,
                        gender=gender,
                        number=number,
                    )
                )

        # Buscar posesivos con regex
        for possessive, (gender, number) in SPANISH_POSSESSIVES.items():
            pattern = rf"\b{re.escape(possessive)}\b"
            for match in re.finditer(pattern, text, re.IGNORECASE):
                mentions.append(
                    Mention(
                        text=match.group(),
                        start_char=match.start(),
                        end_char=match.end(),
                        mention_type=MentionType.POSSESSIVE,
                        gender=gender,
                        number=number,
                    )
                )

        mentions.sort(key=lambda m: m.start_char)
        return mentions

    def _extract_definite_nps(
        self,
        doc,
        text: str,
        get_sentence_idx,
        get_chapter_idx,
    ) -> list[Mention]:
        """
        Extrae sintagmas nominales definidos que refieren a personas.

        Detecta patrones como:
        - "el padre", "la niña", "el joven"
        - "el conductor del autobús", "la mujer de la tienda"
        - "el viejo profesor", "la joven estudiante"

        Returns:
            Lista de menciones de tipo DEFINITE_NP
        """
        mentions = []
        seen_spans = set()  # Evitar duplicados

        # Estrategia 1: Usar chunks de spaCy para sintagmas nominales
        for chunk in doc.noun_chunks:
            chunk_text = chunk.text.strip()
            chunk_lower = chunk_text.lower()

            # Debe empezar con artículo definido
            first_word = chunk_lower.split()[0] if chunk_lower else ""
            if first_word not in DEFINITE_ARTICLES:
                continue

            # La cabeza del chunk debe ser un sustantivo de persona
            head = chunk.root
            head_lemma = head.lemma_.lower()

            if head_lemma not in ALL_PERSON_NOUNS:
                continue

            # Evitar duplicados y solapamientos con entidades ya detectadas
            span_key = (chunk.start_char, chunk.end_char)
            if span_key in seen_spans:
                continue
            seen_spans.add(span_key)

            # Determinar género y número
            # El artículo tiene prioridad para sustantivos ambiguos (estudiante, colega, etc.)
            art_gender, _ = DEFINITE_ARTICLES.get(first_word, (Gender.UNKNOWN, Number.UNKNOWN))

            # Si el sustantivo está SOLO en masculino o SOLO en femenino, usar eso
            in_masc = head_lemma in PERSON_NOUNS_MASCULINE
            in_fem = head_lemma in PERSON_NOUNS_FEMININE

            if in_masc and not in_fem:
                gender = Gender.MASCULINE
            elif in_fem and not in_masc:
                gender = Gender.FEMININE
            else:
                # Sustantivo ambiguo o desconocido: usar el artículo
                gender = art_gender

            # Número del artículo
            _, number = DEFINITE_ARTICLES.get(first_word, (Gender.UNKNOWN, Number.UNKNOWN))

            mentions.append(
                Mention(
                    text=chunk_text,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    mention_type=MentionType.DEFINITE_NP,
                    gender=gender,
                    number=number,
                    sentence_idx=get_sentence_idx(head),
                    chapter_idx=get_chapter_idx(chunk.start_char),
                    head_text=head.text,
                    context=self._get_context(
                        text, None, window=50, start=chunk.start_char, end=chunk.end_char
                    ),
                )
            )

        # Estrategia 2: Regex para patrones no capturados por chunks
        # Patrones como "el conductor del autobús"
        for article, (art_gender, art_number) in DEFINITE_ARTICLES.items():
            # Patrón: artículo + (adjetivo?) + sustantivo_persona + (complemento?)
            for noun in ALL_PERSON_NOUNS:
                # Patrón simple: "el padre", "la niña"
                pattern = rf"\b{article}\s+{noun}\b"
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    span_key = (match.start(), match.end())
                    if span_key in seen_spans:
                        continue

                    # Verificar que no está dentro de un span ya detectado
                    is_subspan = any(
                        s <= match.start() and e >= match.end() for (s, e) in seen_spans
                    )
                    if is_subspan:
                        continue

                    seen_spans.add(span_key)

                    # Determinar género del sustantivo
                    if noun in PERSON_NOUNS_MASCULINE:
                        gender = Gender.MASCULINE
                    elif noun in PERSON_NOUNS_FEMININE:
                        gender = Gender.FEMININE
                    else:
                        gender = art_gender

                    mentions.append(
                        Mention(
                            text=match.group(),
                            start_char=match.start(),
                            end_char=match.end(),
                            mention_type=MentionType.DEFINITE_NP,
                            gender=gender,
                            number=art_number,
                            head_text=noun,
                        )
                    )

        return mentions

    def _extract_zero_mentions(
        self,
        doc,
        text: str,
        get_sentence_idx,
        get_chapter_idx,
    ) -> list[Mention]:
        """
        Extrae menciones de sujeto omitido (pro-drop) en verbos finitos.

        En español, el sujeto puede omitirse cuando la conjugación verbal
        es inequívoca. Solo se extraen menciones de 3ª persona (singular
        y plural) porque 1ª/2ª persona raramente son útiles para
        correferencia narrativa.

        Se genera con confianza baja (0.4) para evitar contaminar cadenas
        existentes en la resolución posterior.

        Returns:
            Lista de menciones de tipo ZERO
        """
        mentions = []

        # Posiciones de sujetos explícitos ya detectados (para evitar duplicar)
        explicit_subj_verbs: set[int] = set()
        for token in doc:
            if token.dep_ in ("nsubj", "nsubj:pass") and token.head.pos_ == "VERB":
                explicit_subj_verbs.add(token.head.i)

        for token in doc:
            # Solo verbos finitos
            if token.pos_ != "VERB":
                continue
            morph = str(token.morph)
            if "VerbForm=Fin" not in morph:
                continue

            # Saltar si ya tiene sujeto explícito
            if token.i in explicit_subj_verbs:
                continue

            # Solo 3ª persona — 1ª/2ª no son útiles para correferencia narrativa
            if "Person=3" not in morph:
                continue

            # Inferir número
            if "Number=Sing" in morph:
                number = Number.SINGULAR
            elif "Number=Plur" in morph:
                number = Number.PLURAL
            else:
                continue  # No se puede determinar

            # Inferir género del contexto verbal:
            # Buscar participios/adjetivos que concuerden con el sujeto omitido
            # "Salió cansada" → femenino, "Llegó enfadado" → masculino
            gender = self._infer_gender_from_context(token, doc)

            # Representación textual: verbo entre corchetes (ASCII-safe)
            zero_text = f"[PRO {token.text}]"

            mentions.append(
                Mention(
                    text=zero_text,
                    start_char=token.idx,
                    end_char=token.idx + len(token.text),
                    mention_type=MentionType.ZERO,
                    gender=gender,
                    number=number,
                    sentence_idx=get_sentence_idx(token),
                    chapter_idx=get_chapter_idx(token.idx),
                    context=self._get_context(
                        text, None, window=50, start=token.idx, end=token.idx + len(token.text)
                    ),
                )
            )

        logger.debug(f"Extraídas {len(mentions)} menciones pro-drop (ZERO)")
        return mentions
