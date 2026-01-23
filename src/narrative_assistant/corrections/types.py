"""
Tipos de issues de corrección editorial.

Cada enum define los tipos específicos de problemas que puede detectar
cada detector. Se usan para categorizar las alertas en la UI.
"""

from enum import Enum


class TypographyIssueType(Enum):
    """Tipos de problemas tipográficos."""

    WRONG_DASH_DIALOGUE = "wrong_dash_dialogue"  # Guion incorrecto en diálogo
    WRONG_DASH_RANGE = "wrong_dash_range"  # Guion incorrecto en rango (1990-2000)
    WRONG_DASH_INCISO = "wrong_dash_inciso"  # Guion incorrecto en inciso
    WRONG_QUOTE_STYLE = "wrong_quote_style"  # Estilo de comillas incorrecto
    MIXED_QUOTES = "mixed_quotes"  # Mezcla de estilos de comillas
    WRONG_ELLIPSIS = "wrong_ellipsis"  # Puntos suspensivos mal formados
    SPACING_BEFORE_PUNCT = "spacing_before_punct"  # Espacio antes de puntuación
    SPACING_AFTER_PUNCT = "spacing_after_punct"  # Falta espacio después de puntuación
    MULTIPLE_SPACES = "multiple_spaces"  # Espacios múltiples


class RepetitionIssueType(Enum):
    """Tipos de repeticiones detectadas."""

    LEXICAL_CLOSE = "lexical_close"  # Palabra repetida muy cerca
    SENTENCE_START = "sentence_start"  # Oraciones que empiezan igual
    PARAGRAPH_START = "paragraph_start"  # Párrafos que empiezan igual
    CACOPHONY = "cacophony"  # Sonidos repetidos (potencial cacofonía)


class AgreementIssueType(Enum):
    """Tipos de errores de concordancia."""

    GENDER_DISAGREEMENT = "gender_disagreement"  # Discordancia de género
    NUMBER_DISAGREEMENT = "number_disagreement"  # Discordancia de número
    SUBJECT_VERB = "subject_verb"  # Sujeto-verbo no concuerdan


class TerminologyIssueType(Enum):
    """Tipos de inconsistencias terminológicas."""

    VARIANT_TERM = "variant_term"  # Término variante de otro más usado
    INCONSISTENT_NAME = "inconsistent_name"  # Nombre propio con variaciones
    MIXED_REGISTER = "mixed_register"  # Mezcla de registros (formal/informal)


class RegionalIssueType(Enum):
    """Tipos de variaciones regionales detectadas."""

    MIXED_REGIONAL = "mixed_regional"  # Mezcla de variantes regionales
    UNCOMMON_IN_REGION = "uncommon_in_region"  # Término poco común en la región configurada
    SUGGESTED_ALTERNATIVE = "suggested_alternative"  # Alternativa regional sugerida


class FieldTermIssueType(Enum):
    """Tipos de problemas con terminología de campo especializado."""

    UNEXPECTED_FIELD_TERM = "unexpected_field_term"  # Término de un campo no configurado
    NEEDS_GLOSSARY = "needs_glossary"  # Término técnico que puede necesitar explicación
    MIXED_FIELDS = "mixed_fields"  # Mezcla de terminología de diferentes campos
    REGISTER_MISMATCH = "register_mismatch"  # Registro no coincide con el esperado


class ClarityIssueType(Enum):
    """Tipos de problemas de claridad."""

    SENTENCE_TOO_LONG = "sentence_too_long"  # Oración excesivamente larga
    SENTENCE_LONG_WARNING = "sentence_long_warning"  # Oración larga (advertencia)
    TOO_MANY_SUBORDINATES = "too_many_subordinates"  # Demasiadas subordinadas
    PARAGRAPH_NO_PAUSES = "paragraph_no_pauses"  # Párrafo sin pausas
    RUN_ON_SENTENCE = "run_on_sentence"  # Oración sin pausa adecuada


class GrammarIssueType(Enum):
    """Tipos de errores gramaticales específicos del español."""

    LEISMO = "leismo"  # Uso de 'le' en lugar de 'lo/la'
    LAISMO = "laismo"  # Uso de 'la' en lugar de 'le'
    LOISMO = "loismo"  # Uso de 'lo' en lugar de 'le'
    DEQUEISMO = "dequeismo"  # Uso incorrecto de 'de que'
    QUEISMO = "queismo"  # Omisión incorrecta de 'de' antes de 'que'
    GENDER_AGREEMENT = "gender_agreement"  # Concordancia de género
    NUMBER_AGREEMENT = "number_agreement"  # Concordancia de número
    ADJECTIVE_AGREEMENT = "adjective_agreement"  # Concordancia de adjetivo
    REDUNDANCY = "redundancy"  # Expresiones redundantes


class AnglicismsIssueType(Enum):
    """Tipos de anglicismos detectados."""

    RAW_ANGLICISM = "raw_anglicism"  # Anglicismo crudo sin adaptar
    MORPHOLOGICAL = "morphological_anglicism"  # Detectado por patrón morfológico
    SEMANTIC_CALQUE = "semantic_calque"  # Calco semántico


class GlossaryIssueType(Enum):
    """Tipos de problemas de glosario detectados."""

    VARIANT_USED = "variant_used"  # Se usó una variante en lugar del término canónico
    UNDEFINED_INVENTED = "undefined_invented"  # Término que parece inventado sin definición
    UNDEFINED_TECHNICAL = "undefined_technical"  # Término técnico sin definición
    INCONSISTENT_USAGE = "inconsistent_usage"  # Uso inconsistente de un término


class AnacolutoIssueType(Enum):
    """Tipos de anacolutos (rupturas sintácticas)."""

    NOMINATIVUS_PENDENS = "nominativus_pendens"  # Sujeto inicial "colgado" sin conexión
    BROKEN_CONSTRUCTION = "broken_construction"  # Cambio de construcción a mitad de oración
    INCOMPLETE_CLAUSE = "incomplete_clause"  # Subordinada o principal incompleta
    SUBJECT_SHIFT = "subject_shift"  # Cambio inesperado de sujeto
    DANGLING_MODIFIER = "dangling_modifier"  # Modificador sin referente claro


class POVIssueType(Enum):
    """Tipos de problemas de punto de vista narrativo."""

    PERSON_SHIFT = "person_shift"  # Cambio de persona gramatical (1ra a 3ra, etc.)
    FOCALIZER_SHIFT = "focalizer_shift"  # Cambio de focalizador (quién percibe/piensa)
    TU_USTED_MIX = "tu_usted_mix"  # Mezcla de tú/usted en el mismo contexto
    INCONSISTENT_OMNISCIENCE = "inconsistent_omniscience"  # Omnisciencia inconsistente


class CorrectionCategory(Enum):
    """Categorías principales de correcciones."""

    TYPOGRAPHY = "typography"  # Tipografía (guiones, comillas, espacios)
    REPETITION = "repetition"  # Repeticiones léxicas
    AGREEMENT = "agreement"  # Concordancia gramatical
    PUNCTUATION = "punctuation"  # Puntuación
    TERMINOLOGY = "terminology"  # Terminología inconsistente
    REGIONAL = "regional"  # Vocabulario regional
    CLARITY = "clarity"  # Claridad/estilo
    GRAMMAR = "grammar"  # Errores gramaticales (leísmo, dequeísmo, etc.)
    ANGLICISMS = "anglicisms"  # Anglicismos innecesarios
    CRUTCH_WORDS = "crutch_words"  # Muletillas del autor
    GLOSSARY = "glossary"  # Glosario del proyecto
    ANACOLUTO = "anacoluto"  # Anacolutos (rupturas sintácticas)
    POV = "pov"  # Punto de vista narrativo
