"""
Mixin de coreference resolver: Gender inference, validation, name dictionaries.

Extraido de coreference_resolver.py para reducir complejidad del monolito.
"""

from __future__ import annotations

import logging
import re

from .coreference_resolver import (
    Gender,
    Mention,
    MentionType,
    Number,
)

logger = logging.getLogger(__name__)


class CorefGenderMixin:
    """
    Mixin: Gender inference, validation, name dictionaries.

    Requiere que la clase que hereda tenga:
    - self.config (CorefConfig)
    - self.methods (dict[CorefMethod, CorefMethodInterface])
    """

    @staticmethod
    def _infer_gender_from_context(verb_token, doc) -> Gender:
        """
        Infiere el género del sujeto omitido (pro-drop) desde el contexto.

        En español, los participios y adjetivos predicativos concuerdan
        con el sujeto: "Salió cansada" → femenino, "Llegó enfadado" → masculino.

        Busca en los hijos del verbo y tokens adyacentes.
        """
        # Buscar participios/adjetivos dependientes del verbo
        for child in verb_token.children:
            morph = str(child.morph)
            if child.pos_ in ("ADJ", "VERB") and "VerbForm=Part" in morph or child.pos_ == "ADJ":
                if "Gender=Fem" in morph:
                    return Gender.FEMININE
                if "Gender=Masc" in morph:
                    return Gender.MASCULINE

        # Buscar en tokens inmediatamente después del verbo (hasta 3 tokens)
        start_idx = verb_token.i + 1
        end_idx = min(start_idx + 3, len(doc))
        for i in range(start_idx, end_idx):
            token = doc[i]
            if token.pos_ in ("PUNCT", "CCONJ", "SCONJ"):
                break  # Fin de cláusula
            morph = str(token.morph)
            if token.pos_ in ("ADJ", "VERB") and ("VerbForm=Part" in morph or token.pos_ == "ADJ"):
                if "Gender=Fem" in morph:
                    return Gender.FEMININE
                if "Gender=Masc" in morph:
                    return Gender.MASCULINE

        return Gender.UNKNOWN

    # Nombres españoles comunes por género (para inferencia cuando spaCy no detecta)
    FEMININE_NAMES = {
        "maría",
        "maria",
        "ana",
        "carmen",
        "laura",
        "marta",
        "elena",
        "sara",
        "paula",
        "lucía",
        "lucia",
        "sofía",
        "sofia",
        "isabel",
        "rosa",
        "pilar",
        "teresa",
        "julia",
        "clara",
        "alicia",
        "beatriz",
        "andrea",
        "cristina",
        "diana",
        "eva",
        "irene",
        "lorena",
        "nuria",
        "olga",
        "patricia",
        "raquel",
        "silvia",
        "susana",
        "verónica",
        "veronica",
        "virginia",
        "inés",
        "ines",
    }

    MASCULINE_NAMES = {
        "juan",
        "pedro",
        "carlos",
        "miguel",
        "josé",
        "jose",
        "antonio",
        "manuel",
        "francisco",
        "david",
        "jorge",
        "pablo",
        "andrés",
        "andres",
        "luis",
        "javier",
        "sergio",
        "fernando",
        "alejandro",
        "alberto",
        "daniel",
        "diego",
        "enrique",
        "felipe",
        "gabriel",
        "héctor",
        "hector",
        "ignacio",
        "jaime",
        "mario",
        "rafael",
        "ramón",
        "ramon",
        "roberto",
        "víctor",
        "victor",
    }

    def _infer_gender_number(self, text: str, token) -> tuple[Gender, Number]:
        """Infiere género y número de un token."""
        gender = Gender.UNKNOWN
        number = Number.UNKNOWN

        morph = str(token.morph)

        if "Gender=Masc" in morph:
            gender = Gender.MASCULINE
        elif "Gender=Fem" in morph:
            gender = Gender.FEMININE

        if "Number=Sing" in morph:
            number = Number.SINGULAR
        elif "Number=Plur" in morph:
            number = Number.PLURAL

        # Si spaCy no detectó género, intentar por nombre propio
        if gender == Gender.UNKNOWN:
            text_lower = text.lower().strip()
            # Extraer primera palabra (nombre) si hay varias
            first_word = text_lower.split()[0] if text_lower else ""

            if first_word in self.FEMININE_NAMES or text_lower in self.FEMININE_NAMES:
                gender = Gender.FEMININE
                logger.debug(f"Género inferido por nombre: {text} -> femenino")
            elif first_word in self.MASCULINE_NAMES or text_lower in self.MASCULINE_NAMES:
                gender = Gender.MASCULINE
                logger.debug(f"Género inferido por nombre: {text} -> masculino")
            # Heurística: nombres terminados en -a suelen ser femeninos en español
            elif first_word.endswith("a") and len(first_word) > 2:
                gender = Gender.FEMININE
                logger.debug(f"Género inferido por terminación -a: {text} -> femenino")
            # Heurística: nombres terminados en -o suelen ser masculinos
            elif first_word.endswith("o") and len(first_word) > 2:
                gender = Gender.MASCULINE
                logger.debug(f"Género inferido por terminación -o: {text} -> masculino")

        return gender, number

    def _is_valid_mention(self, text: str) -> bool:
        """
        Valida si un texto es una mención válida para correferencias.

        Filtra:
        - Saludos como "Hola Juan", "Buenos días María"
        - Frases con verbos (oraciones, no entidades)
        - Textos muy largos o con errores de segmentación
        """
        if not text or len(text) < 2:
            return False

        text_stripped = text.strip()
        text_stripped.lower()
        words = text_stripped.split()

        # Filtrar entidades muy largas (probablemente error de segmentación)
        if len(words) > 5 or len(text_stripped) > 50:
            return False

        # Filtrar saludos: "Hola X", "Buenos días X", etc.
        saludo_starters = {"hola", "adiós", "buenos", "buenas", "hey", "oye"}
        if words and words[0].lower() in saludo_starters:
            return False

        # Filtrar frases que contienen verbos o pronombres clíticos
        verb_indicators = {
            "se",
            "me",
            "te",
            "le",
            "lo",
            "la",
            "nos",
            "os",
            "les",
            "acerco",
            "acercó",
            "dijo",
            "respondió",
            "preguntó",
            "miró",
            "vio",
            "saludo",
            "saludó",
            "entró",
            "salió",
            "llegó",
            "fue",
            "era",
            "estaba",
            "tenía",
            "había",
            "hizo",
            "quería",
            "podía",
            "sabía",
        }
        if len(words) >= 3:
            words_lower = [w.lower() for w in words]
            if any(w in verb_indicators for w in words_lower[1:]):
                return False

        # Filtrar errores de segmentación (saltos de línea, puntuación final)
        return not ("\n" in text or text_stripped and text_stripped[-1] in ".,:;!?")

    def _is_anaphor(self, mention: Mention) -> bool:
        """Determina si una mención es anafórica."""
        return mention.mention_type in (
            MentionType.PRONOUN,
            MentionType.DEMONSTRATIVE,
            MentionType.POSSESSIVE,
        )

    def _is_potential_antecedent(self, mention: Mention) -> bool:
        """Determina si una mención puede ser antecedente."""
        return mention.mention_type in (
            MentionType.PROPER_NOUN,
            MentionType.DEFINITE_NP,
        )
