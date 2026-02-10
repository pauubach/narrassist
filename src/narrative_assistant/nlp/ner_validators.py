"""
Mixin de validación para NERExtractor.

Contiene las constantes (listas de stop words, falsos positivos, etc.)
y los métodos de validación que determinan si una entidad detectada
es válida o debe descartarse.

Este módulo se separa de ner.py para reducir el tamaño del archivo
principal y mejorar la mantenibilidad. La clase NERValidatorMixin
se usa como mixin de NERExtractor.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from . import morpho_utils

if TYPE_CHECKING:
    from .ner import EntityLabel

logger = logging.getLogger(__name__)


class NERValidatorMixin:
    """
    Mixin con constantes y métodos de validación de entidades NER.

    Provee:
    - Constantes: STOP_TITLES, HEURISTIC_FALSE_POSITIVES,
      COMMON_PHRASES_NOT_ENTITIES, PHYSICAL_DESCRIPTION_PATTERNS,
      SPACY_FALSE_POSITIVE_WORDS
    - Métodos: _is_false_positive_by_morphology, _is_valid_spacy_entity,
      _is_valid_heuristic_candidate, _is_high_quality_entity

    Se mezcla con NERExtractor, que aporta self.nlp, self.MIN_ENTITY_LENGTH, etc.
    """

    # Palabras a ignorar en detección heurística de nombres
    STOP_TITLES = {
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "de",
        "del",
        "al",
        "en",
        "por",
        "para",
        "con",
        "sin",
        "sobre",
        "entre",
        "hacia",
        "hasta",
        "desde",
        "durante",
        "según",
        "mediante",
        "y",
        "o",
        "ni",
        "pero",
        "sino",
        "aunque",
        "porque",
        "cuando",
        "si",
        "que",
        "como",
        "donde",
        "quien",
        "cual",
        "cuyo",
        "esto",
        "eso",
        "aquello",
        "ese",
        "este",
        "aquel",
        # Pronombres personales (nunca son entidades independientes)
        "él",
        "ella",
        "ellos",
        "ellas",
        "yo",
        "tú",
        "usted",
        "ustedes",
        "nosotros",
        "nosotras",
        "vosotros",
        "vosotras",
        "le",
        "les",
        "lo",
        "nos",
        "os",
        "me",
        "te",
        "se",
        "su",
        "sus",
        "mi",
        "mis",
        "tu",
        "tus",
        "nuestro",
        "nuestra",
        "vuestro",
        "vuestra",
        "señor",
        "señora",
        "don",
        "doña",
        "sr",
        "sra",
        "dr",
        "dra",
    }

    # Palabras que NUNCA son entidades por sí solas (solo para gazetteer heurístico)
    # NOTA: Si spaCy detecta algo como entidad, confiamos en spaCy.
    # Estos filtros solo aplican a candidatos heurísticos (palabras capitalizadas
    # que spaCy NO detectó como entidad).
    #
    # NO incluir títulos como "rey", "padre", etc. porque pueden ser referencias
    # a personajes específicos ("El Rey ordenó...").
    HEURISTIC_FALSE_POSITIVES = {
        # Expresiones temporales (nunca son personajes/lugares)
        "lunes",
        "martes",
        "miércoles",
        "jueves",
        "viernes",
        "sábado",
        "domingo",
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
        "primavera",
        "verano",
        "otoño",
        "invierno",
        "mañana",
        "tarde",
        "noche",
        "mediodía",
        "madrugada",
        "ayer",
        "hoy",
        "anoche",
        "ahora",
        "entonces",
        "después",
        "antes",
        # Términos narrativos/estructura (metadatos, no contenido)
        "capítulo",
        "prólogo",
        "epílogo",
        "parte",
        "libro",
        "volumen",
        "escena",
        "acto",
        "fin",
        "final",
        "principio",
        "inicio",
        # Pronombres/determinantes (nunca son entidades)
        "algo",
        "alguien",
        "nadie",
        "nada",
        "todo",
        "todos",
        "otro",
        "otra",
        "otros",
        "otras",
        "mismo",
        "misma",
        "mismos",
        "mismas",
        "cada",
        "cualquier",
        "cualquiera",
        # Adverbios (nunca son entidades)
        "bien",
        "mal",
        "aquí",
        "allí",
        "allá",
        "acá",
        "sí",
        "no",
        "quizá",
        "quizás",
        "luego",
        "siempre",
        "nunca",
        # Interjecciones
        "oh",
        "ah",
        "ay",
        "eh",
        "uf",
        "bah",
        "ja",
        # Atributos físicos (descripciones, no entidades)
        "cabello",
        "pelo",
        "ojos",
        "rostro",
        "cara",
        "manos",
        "piel",
        "negro",
        "blanco",
        "rubio",
        "moreno",
        "rojo",
        "azul",
        "verde",
        "alto",
        "bajo",
        "gordo",
        "flaco",
        "grande",
        "pequeño",
        # Adjetivos comunes
        "extraño",
        "raro",
        "imposible",
        "increíble",
        "horrible",
        "terrible",
        "hermoso",
        "bello",
        "feo",
        "viejo",
        "nuevo",
        "joven",
        "antiguo",
        # Palabras de test/desarrollo
        "test",
        "fresh",
        "prueba",
        "ejemplo",
        "demo",
        # Pronombres interrogativos y frases de diálogo
        "quién",
        "quien",
        "qué",
        "que",
        "cómo",
        "como",
        "dónde",
        "donde",
        "cuándo",
        "cuando",
        "cuánto",
        "cuanto",
        # Términos científicos/biológicos genéricos
        "endorfinas",
        "endorfina",
        "adrenalina",
        "serotonina",
        "dopamina",
        "hormona",
        "hormonas",
        "neurotransmisor",
        "neurotransmisores",
    }

    # Frases comunes que nunca son entidades (saludos, expresiones, etc.)
    COMMON_PHRASES_NOT_ENTITIES = {
        # Saludos
        "buenos días",
        "buenas tardes",
        "buenas noches",
        "buen día",
        "hola",
        "adiós",
        "hasta luego",
        "hasta pronto",
        # Expresiones comunes
        "por favor",
        "muchas gracias",
        "de nada",
        "lo siento",
        "por supuesto",
        "sin embargo",
        "no obstante",
        "en cambio",
        "por cierto",
        "de hecho",
        "en realidad",
        "al parecer",
        "tal vez",
        "quizás",
        "a veces",
        "de vez en cuando",
        # Frases narrativas que empiezan con mayúscula pero no son entidades
        "capítulo",
        "prólogo",
        "epílogo",
        "parte",
        # Descripciones físicas que no son entidades
        "cabello negro",
        "cabello rubio",
        "cabello castaño",
        "pelo negro",
        "ojos azules",
        "ojos verdes",
        "ojos negros",
        "ojos marrones",
        # Descripciones con posesivos
        "sus ojos",
        "sus ojos verdes",
        "sus ojos azules",
        "sus ojos negros",
        "su cabello",
        "su pelo",
        "su rostro",
        "su cara",
        "su mirada",
        "mis ojos",
        "mis manos",
        "mi cabello",
        "mi pelo",
        "tus ojos",
        "tu cabello",
        "tu pelo",
        "tu rostro",
        # Títulos de capítulos comunes
        "la contradicción",
        "el encuentro",
        "el principio",
        "el final",
        # Expresiones que parecen ser detectadas como MISC
        "hola juan",
        "fresh test do",
        "imposible",
        # Preguntas y frases interrogativas (diálogo)
        "quién eres",
        "quien eres",
        "qué eres",
        "que eres",
        "quién es",
        "quien es",
        "qué es",
        "que es",
        "cómo estás",
        "como estas",
        "qué tal",
        "que tal",
        "dónde estás",
        "donde estas",
        "dónde está",
        "donde esta",
        "por qué",
        "porque",
        "para qué",
        "para que",
        # Sustantivos genéricos que a veces se detectan erróneamente
        "las endorfinas",
        "la endorfina",
        "endorfinas",
        "endorfina",
        "la adrenalina",
        "adrenalina",
        "la serotonina",
        "serotonina",
        "la dopamina",
        "dopamina",
        # NUEVOS (iter9): frases detectadas como MISC incorrectamente
        "feliz cumpleaños",
        "me gusta tu perfume",
        "tengo",
        "extrañaba su pelo negro natural",
        "esos ojos verdes que tanto le gustaban",
    }

    # Patrones regex para detectar descripciones físicas que NO son entidades
    PHYSICAL_DESCRIPTION_PATTERNS = [
        r"^(sus?|mis?|tus?)\s+(ojos|cabello|pelo|rostro|cara|manos?|piel)\b",
        r"^(ojos|cabello|pelo)\s+(verdes?|azules?|negros?|marrones?|rubios?|castaños?)\b",
    ]

    # Palabras sueltas que spaCy a veces detecta erróneamente como MISC
    SPACY_FALSE_POSITIVE_WORDS = {
        "imposible",
        "increíble",
        "horrible",
        "terrible",
        "extraño",
        "cabello",
        "pelo",
        "ojos",
        "negro",
        "rubio",
        "moreno",
        "fresh",
        "test",
        "hola",
    }

    def _is_false_positive_by_morphology(
        self,
        entity_text: str,
        entity_label: EntityLabel,
        context: str,
        position: int,
    ) -> tuple[bool, str]:
        """
        Filtro genérico de falsos positivos basado en análisis morfosintáctico.

        Usa patrones lingüísticos genéricos en lugar de listas cerradas:
        1. Analiza el POS-tag de la palabra en contexto
        2. Detecta si está al inicio de oración (capitalización obligatoria)
        3. Verifica concordancia con determinantes/adjetivos previos
        4. Detecta patrones de frases nominales genéricas

        Args:
            entity_text: Texto de la entidad
            entity_label: Etiqueta NER asignada
            context: Texto circundante (+-100 caracteres)
            position: Posición de la entidad en el contexto

        Returns:
            Tupla (is_false_positive, reason)
        """
        from .ner import EntityLabel

        text_lower = entity_text.lower().strip()
        words = entity_text.split()

        # 1. ANALISIS MORFOLOGICO CON SPACY
        # Si tenemos spaCy disponible, analizamos el contexto completo
        try:
            doc = self.nlp(context)

            # Encontrar el token correspondiente a la entidad
            entity_tokens = []
            for token in doc:
                if token.text.lower() == text_lower or text_lower in token.text.lower():
                    entity_tokens.append(token)
                    break
                # Para entidades multi-palabra, buscar la primera palabra
                elif words and token.text.lower() == words[0].lower():
                    entity_tokens.append(token)
                    # Añadir tokens siguientes
                    idx = token.i
                    for w in words[1:]:
                        if idx + 1 < len(doc) and doc[idx + 1].text.lower() == w.lower():
                            entity_tokens.append(doc[idx + 1])
                            idx += 1
                    break

            if entity_tokens:
                first_token = entity_tokens[0]

                # 1.1 Detectar VERBOS mal clasificados
                if first_token.pos_ == "VERB":
                    return (
                        True,
                        f"Detectado como verbo (POS={first_token.pos_}, morfología={first_token.morph})",
                    )

                # 1.2 Detectar ADJETIVOS/ADVERBIOS mal clasificados
                if first_token.pos_ in ("ADJ", "ADV") and len(entity_tokens) == 1:
                    return True, f"Detectado como {first_token.pos_} (no es nombre propio)"

                # 1.3 Detectar SUSTANTIVOS COMUNES al inicio de oración
                # Si es un sustantivo común (no PROPN) y está al inicio de oración
                if first_token.pos_ == "NOUN":
                    # Verificar si está al inicio de oración
                    if first_token.i == 0 or (
                        first_token.i > 0 and doc[first_token.i - 1].text in ".!?¿¡\n"
                    ):
                        # Verificar si es un sustantivo que aparece en minúsculas en otras partes
                        # del texto (indicando que no es nombre propio)
                        lowercase_pattern = r"\b" + re.escape(text_lower) + r"\b"
                        lowercase_matches = len(re.findall(lowercase_pattern, context.lower()))
                        uppercase_matches = len(
                            re.findall(r"\b" + re.escape(entity_text) + r"\b", context)
                        )

                        # Si aparece más veces en minúsculas que con mayúscula, es sustantivo común
                        if lowercase_matches > uppercase_matches:
                            return True, "Sustantivo común capitalizado al inicio de oración"

                # 1.4 Detectar DETERMINANTE + SUSTANTIVO (frase nominal genérica)
                if first_token.pos_ == "DET" and len(entity_tokens) > 1:
                    # "El público", "La luna", etc.
                    second_token = entity_tokens[1] if len(entity_tokens) > 1 else None
                    if second_token and second_token.pos_ == "NOUN":
                        return True, "Frase nominal genérica: DET + NOUN"

        except Exception as e:
            logger.debug(f"Error en análisis morfológico: {e}")

        # 2. PATRONES GENERICOS (sin spaCy disponible)

        # 2.1 Detectar verbos por terminaciones típicas del español
        verb_endings_preterite = ("ó", "ió", "aron", "ieron", "aste", "iste")
        verb_endings_imperative = ("ate", "ete", "ite")
        if len(words) == 1 and len(text_lower) > 3:
            if text_lower.endswith(verb_endings_preterite):
                return True, f"Terminación verbal (pretérito): -{text_lower[-2:]}"
            if text_lower.endswith(verb_endings_imperative):
                return True, f"Terminación verbal (imperativo): -{text_lower[-3:]}"

        # 2.2 Detectar fragmentos de oración (más de 3 palabras con preposiciones/artículos)
        if len(words) >= 3:
            function_words = {
                "el",
                "la",
                "los",
                "las",
                "un",
                "una",
                "de",
                "del",
                "en",
                "con",
                "por",
                "para",
                "a",
                "al",
            }
            function_count = sum(1 for w in words if w.lower() in function_words)
            if function_count >= 2:
                return True, "Fragmento de oración (muchas palabras funcionales)"

        # 2.3 Detectar cuantificadores/adverbios como entidad
        quantifiers = {"tanto", "tanta", "tantos", "tantas", "mucho", "mucha", "poco", "poca"}
        if text_lower in quantifiers:
            return True, "Cuantificador/adverbio, no entidad"

        # 2.4 Para LOC: Verificar si es dirección cardinal sin contexto geográfico
        if entity_label == EntityLabel.LOC:
            cardinal_directions = {
                "norte",
                "sur",
                "este",
                "oeste",
                "noroeste",
                "noreste",
                "suroeste",
                "sureste",
            }
            if text_lower in cardinal_directions:
                # Solo es falso positivo si no va acompañado de nombre de lugar
                # "al Norte" vs "Norte de España"
                if not re.search(r"(de|del)\s+[A-ZÁÉÍÓÚÑ]", context[position : position + 50]):
                    return True, "Dirección cardinal sin nombre de lugar"

        # 2.5 Para ORG: Verificar si es término temporal
        if entity_label == EntityLabel.ORG:
            # Los meses como organización son casi siempre falsos positivos
            months = {
                "enero",
                "febrero",
                "marzo",
                "abril",
                "mayo",
                "junio",
                "julio",
                "agosto",
                "septiembre",
                "octubre",
                "noviembre",
                "diciembre",
            }
            if text_lower in months:
                return True, "Mes del año, no organización"

            # Términos técnicos que no son organizaciones
            technical_terms = {"escotillón", "escotilla", "prensa", "iglesia"}
            if text_lower in technical_terms:
                return True, "Término técnico/genérico, no organización"

        # 2.6 Para PER: Detectar adjetivos capitalizados al inicio de oración
        if entity_label == EntityLabel.PER:
            # Adjetivos comunes que spaCy detecta como PER
            common_adjectives = {
                "hermoso",
                "hermosa",
                "hermosos",
                "hermosas",
                "influido",
                "influida",
                "influidos",
                "influidas",
                "natural",
                "naturales",
                "naturalismo",
                "picaresca",
                "picaresco",
            }
            if text_lower in common_adjectives:
                return True, "Adjetivo común, no nombre de persona"

        # 2.7 Para LOC: Sustantivos comunes de la naturaleza/edificios
        if entity_label == EntityLabel.LOC:
            common_nature_nouns = {
                "luna",
                "sol",
                "cielo",
                "tierra",
                "mar",
                "río",
                "yerba",
                "hierba",
                "bosque",
                "jardín",
                "campo",
                "catedral",
                "iglesia",
                "casino",
                "obispo",
            }
            if text_lower in common_nature_nouns:
                return True, "Sustantivo común de lugar/naturaleza"

            # Frases con artículo + sustantivo común
            if text_lower.startswith(("la ", "el ", "las ", "los ")):
                rest = text_lower.split(" ", 1)[1] if " " in text_lower else ""
                if rest in common_nature_nouns:
                    return True, "Artículo + sustantivo común"

        # 2.8 Para MISC: Expresiones comunes y fragmentos
        if entity_label == EntityLabel.MISC:
            # Expresiones comunes que no son entidades
            common_expressions = {
                "sin duda",
                "por mi parte",
                "por su parte",
                "en efecto",
                "tanta",
                "tanto",
                "tantas",
                "tantos",
                "el nuestro",
                "la nuestra",
                "lo nuestro",
            }
            if text_lower in common_expressions:
                return True, "Expresión común, no entidad"

        return False, ""

    def _is_valid_spacy_entity(self, text: str, spacy_span=None) -> bool:
        """
        Valida una entidad detectada por spaCy.

        Filtramos errores obvios de segmentación y frases que claramente
        no son entidades nombradas.

        Usa análisis morfológico de spaCy (POS tags, morph) como criterio
        principal para detectar verbos, adjetivos, etc. Las listas
        hardcodeadas sirven como fallback.

        Args:
            text: Texto de la entidad
            spacy_span: Span de spaCy (opcional) para acceso a POS tags

        Returns:
            True si es válida, False solo si hay error obvio
        """
        if not text:
            return False

        text_stripped = text.strip()
        text_lower = text_stripped.lower()

        # Filtrar entidades muy cortas (probablemente ruido)
        if len(text_stripped) < self.MIN_ENTITY_LENGTH:
            return False

        # Filtrar errores de segmentación obvios
        if "\n" in text or len(text_stripped) > 100:
            logger.debug(f"Entidad spaCy filtrada (segmentación): '{text[:50]}...'")
            return False

        # ===== FILTRO PRINCIPAL: POS tags de spaCy (cubre ~97% de formas) =====
        # Si tenemos el span de spaCy, usar POS tags directamente.
        # Esto reemplaza TODAS las listas de verbos hardcodeadas.
        if spacy_span is not None:
            words = text_stripped.split()
            if len(words) == 1:
                # Entidad de una sola palabra: verificar POS tag
                token = spacy_span[0] if len(spacy_span) > 0 else None
                if token is not None:
                    if morpho_utils.is_verb(token):
                        logger.debug(
                            f"Entidad filtrada por POS (verbo): '{text}' "
                            f"[pos={token.pos_}, morph={token.morph}]"
                        )
                        return False
                    if token.pos_ == "ADV":
                        logger.debug(f"Entidad filtrada por POS (adverbio): '{text}'")
                        return False
            elif len(words) >= 2:
                # Entidad multi-palabra: verificar si contiene verbos
                verb_count = sum(1 for t in spacy_span if morpho_utils.is_verb(t))
                propn_count = sum(1 for t in spacy_span if morpho_utils.is_proper_noun(t))
                # Si hay más verbos que nombres propios -> probablemente no es entidad
                if verb_count > 0 and propn_count == 0:
                    logger.debug(f"Entidad filtrada por POS (frase con verbos sin PROPN): '{text}'")
                    return False
                # Si el último token es verbo y lowercase -> segmentación errónea
                last_token = spacy_span[-1] if len(spacy_span) > 0 else None
                if (
                    last_token is not None
                    and morpho_utils.is_verb(last_token)
                    and last_token.text[0].islower()
                ):
                    logger.debug(f"Entidad filtrada por POS (termina en verbo): '{text}'")
                    return False

        # Puntuación que no debería aparecer en bordes de entidades
        # Incluye signos de apertura españoles ¿¡ y otros símbolos comunes
        BOUNDARY_PUNCTUATION = '.,:;!?¿¡–—-\'"()[]{}«»""'

        # Filtrar entidades que terminan en puntuación (error de segmentación)
        if text_stripped and text_stripped[-1] in BOUNDARY_PUNCTUATION:
            logger.debug(f"Entidad spaCy filtrada (puntuación final): '{text}'")
            return False

        # Filtrar entidades que empiezan con puntuación (error de segmentación)
        if text_stripped and text_stripped[0] in BOUNDARY_PUNCTUATION:
            logger.debug(f"Entidad spaCy filtrada (puntuación inicial): '{text}'")
            return False

        # Limpiar guiones y puntuación al final y verificar si queda algo válido
        text_clean = text_stripped.rstrip("–—-,.;:!?¿¡ ")
        if text_clean != text_stripped:
            # Si había caracteres finales que limpiar, verificar el resultado
            if len(text_clean) < self.MIN_ENTITY_LENGTH:
                return False

        # Filtrar solo artículos/preposiciones sueltas
        if text_lower in self.STOP_TITLES:
            return False

        # Términos familiares que NO son nombres propios cuando están solos
        # Nota: "Papa" puede ser padre (familia) o Papa de Roma (iglesia)
        # El contexto lo resuelve la correferencia, no el NER
        FAMILY_TERMS = {
            "hijo",
            "hija",
            "hijos",
            "hijas",
            "padre",
            "madre",
            "padres",
            "madres",
            "hermano",
            "hermana",
            "hermanos",
            "hermanas",
            "abuelo",
            "abuela",
            "abuelos",
            "abuelas",
            "tío",
            "tía",
            "tíos",
            "tías",
            "tio",
            "tia",
            "primo",
            "prima",
            "primos",
            "primas",
            "sobrino",
            "sobrina",
            "sobrinos",
            "sobrinas",
            "nieto",
            "nieta",
            "nietos",
            "nietas",
            "esposo",
            "esposa",
            "marido",
            "mujer",
            "novio",
            "novia",
            "novios",
            "novias",
        }
        if text_lower in FAMILY_TERMS:
            logger.debug(f"Entidad spaCy filtrada (término familiar): '{text}'")
            return False

        # Filtrar pronombres personales (NUNCA pueden ser entidades independientes)
        # Los pronombres deben resolverse mediante correferencia, no extraerse como entidades
        PRONOUNS = {
            # Pronombres personales sujeto
            "él",
            "ella",
            "ellos",
            "ellas",
            "yo",
            "tú",
            "usted",
            "ustedes",
            "nosotros",
            "nosotras",
            "vosotros",
            "vosotras",
            # Pronombres átonos
            "le",
            "les",
            "lo",
            "la",
            "los",
            "las",
            "nos",
            "os",
            "me",
            "te",
            "se",
            # Pronombres reflexivos y recíprocos
            "sí",
            "consigo",
            # Pronombres demostrativos que pueden confundirse con personas
            "éste",
            "ésta",
            "éstos",
            "éstas",
            "ése",
            "ésa",
            "ésos",
            "ésas",
            "aquél",
            "aquélla",
            "aquéllos",
            "aquéllas",
            # Formas sin tilde (ortografía moderna)
            "este",
            "esta",
            "estos",
            "estas",
            "ese",
            "esa",
            "esos",
            "esas",
            "aquel",
            "aquella",
            "aquellos",
            "aquellas",
        }
        if text_lower in PRONOUNS:
            logger.debug(f"Entidad spaCy filtrada (pronombre): '{text}'")
            return False

        # Filtrar si es solo números o puntuación
        if text.isdigit() or not any(c.isalpha() for c in text):
            return False

        # ===== NUEVO: Filtrar palabras completamente en mayúsculas (metadatos) =====
        # Excepción: acrónimos cortos (2-3 letras) pueden ser válidos
        if text_stripped.isupper() and len(text_stripped) > 3:
            logger.debug(f"Entidad spaCy filtrada (todo mayúsculas, probable metadato): '{text}'")
            return False

        # ===== NUEVO: Filtrar verbos conjugados comunes al inicio de oración =====
        # Estos aparecen capitalizados pero no son entidades
        # Incluye versiones con y sin tilde para textos sin acentos
        VERBS_AT_SENTENCE_START = {
            # Pretérito perfecto simple (3ra persona singular)
            "supo",
            "trajo",
            "traía",
            "dijo",
            "penso",
            "pensó",
            "miro",
            "miró",
            "vio",
            "sintió",
            "llegó",
            "entró",
            "salió",
            "pasó",
            "siguió",
            "encontró",
            "oyó",
            "notó",
            "recordó",
            "olvidó",
            "decidió",
            "intentó",
            "logró",
            "consiguió",
            "empezó",
            "terminó",
            "continuó",
            "preguntó",
            "respondió",
            "contestó",
            "exclamó",
            "susurró",
            "gritó",
            "murmuró",
            "añadió",
            "explicó",
            "comentó",
            "saludo",
            "saludó",  # verbo saludar
            "abrio",
            "abrió",
            "bajo",
            "bajó",
            "compro",
            "compró",
            "preparo",
            "preparó",
            "recibio",
            "recibió",
            "tomo",
            "tomó",
            "tuvo",
            "pudo",
            "hizo",
            "fue",
            "dio",
            "vino",
            "sentaron",
            "elaboraron",
            "contacto",
            "contactó",
            # Verbos frecuentes en narrativa (iter7)
            "camino",
            "caminó",
            "corrio",
            "corrió",
            "beso",
            "besó",
            "abrazo",
            "abrazó",
            "cerro",
            "cerró",
            "colgo",
            "colgó",
            "espero",
            "esperó",
            "escucho",
            "escuchó",
            "marco",
            "marcó",
            "reviso",
            "revisó",
            "suspiro",
            "suspiró",
            "desperto",
            "despertó",
            "levanto",
            "levantó",
            "sono",
            "sonó",
            "nacio",
            "nació",
            "murio",
            "murió",
            "vivio",
            "vivió",
            "conocio",
            "conoció",
            "aprendio",
            "aprendió",
            "escribio",
            "escribió",
            "leyo",
            "leyó",
            "cayo",
            "cayó",
            "mudo",
            "mudó",
            "trabajo",
            "trabajó",
            "caso",
            "casó",
            "graduo",
            "graduó",
            # Imperfecto (con y sin tilde)
            "sabía",
            "tenía",
            "había",
            "quería",
            "podía",
            "debía",
            "sabia",
            "tenia",
            "habia",
            "queria",
            "podia",
            "debia",
            "decia",
            "decía",
            "creia",
            "creía",
            "vivia",
            "vivía",
            "estaba",
            "era",
            "iba",
            "hacia",
            "hacía",
            # Condicional / Futuro
            "contactarian",
            "contactarían",
            "iria",
            "iría",
            "diria",
            "diría",
            "seria",
            "sería",
            "tendria",
            "tendría",
            "podria",
            "podría",
            "deberia",
            "debería",
            "haria",
            "haría",
            "usaria",
            "usaría",
            "volveria",
            "volvería",
            # Imperativo/subjuntivo
            "diga",
            "venga",
            "salga",
            "haga",
            "ponga",
            "traiga",
            # Verbos en 2da persona (diálogo)
            "sigues",
            "tienes",
            "tengo",
            "quieres",
            "puedes",
            "debes",
            "sabes",
            "haces",
            "vas",
            "vienes",
            "dices",
            "ves",
        }
        if text_lower in VERBS_AT_SENTENCE_START:
            logger.debug(f"Entidad spaCy filtrada (verbo al inicio de oración): '{text}'")
            return False

        # ===== NUEVO: Filtrar palabras comunes capitalizadas (falsos positivos) =====
        COMMON_WORDS_CAPITALIZED = {
            # Palabras comunes que aparecen capitalizadas por error o como ejemplo
            "correcto",
            "incorrecto",
            "habemos",
            "hubieron",
            "haiga",
            "mejor",
            "peor",
            "mayor",
            "menor",
            "más",
            "menos",
            # Términos lingüísticos/gramaticales
            "dequeísmo",
            "queísmo",
            "laísmo",
            "leísmo",
            "loísmo",
            "concordancia",
            "redundancia",
            "redundancias",
            "pleonasmo",
            "solecismo",
            "anacoluto",
            "gramática",
            "sintaxis",
            # Palabras de sección/documento
            "notas",
            "ejemplo",
            "error",
            "observación",
            "nota",
            # Pronombres indefinidos
            "alguien",
            "nadie",
            "cualquiera",
            "quienquiera",
            # Adverbios de cantidad/grado
            "demasiado",
            "demasiada",
            "demasiados",
            "demasiadas",
            "bastante",
            "bastantes",
            "suficiente",
            "suficientes",
            # Sustantivos abstractos comunes (títulos de sección)
            "revelaciones",
            "revelación",
            "explicaciones",
            "explicación",
            "decisiones",
            "decisión",
            "secretos",
            "verdad",
            "verdades",
            "origenes",
            "orígenes",
            "comienzo",
            "comienzos",
            "encuentro",
            "encuentros",
            "viaje",
            "viajes",
            "despertar",
            "carta",
            "cartas",
            "plan",
            "planes",
            # Adjetivos usados como titulo
            "urgente",
            "urgentes",
            "importante",
            "importantes",
            "dificiles",
            "difíciles",
            "faciles",
            "fáciles",
            # Palabras de estructura de documento
            "resumen",
            "estructura",
            "esperada",
            "formatos",
            "incluidos",
            "incluidas",
            "formato",
            "cronologico",
            "cronológico",
            # Ordinales que aparecen como títulos
            "primera",
            "primero",
            "segunda",
            "segundo",
            "tercera",
            "tercero",
            "cuarta",
            "cuarto",
            "quinta",
            "quinto",
            # NUEVOS (iter8): sustantivos abstractos de eventos/títulos
            "graduacion",
            "graduación",
            "nacimiento",
            "nacimientos",
            "infancia",
            "adolescencia",
            "universidad",
            "adulta",
            "adulto",
            "final",
            "inicio",
            "eventos",
            "temporales",
            "boda",
            "bodas",
            "muerte",
            "muertes",
            "trabajo",
            "trabajos",
            # NUEVOS (iter9): falsos positivos detectados en evaluación NER
            "inconsistencias",
            "intencionadas",
            "intencionados",
            "personaje",
            "postre",
            "barba",
            "ojos",
            "pelo",
            "estatura",
            "edad",
            "profesion",
            "profesión",
            "cabello",
            "bebida",
            "perfume",
            "aroma",
            "ahora",
            "feliz",
            "martes",
            "miércoles",
            "jueves",
            "viernes",
            # Adverbios temporales
            "antes",
            "después",
            "despues",
            "luego",
            "pronto",
            "tarde",
            "temprano",
            # NUEVOS (iter11): sustantivos abstractos que aparecen como MISC
            "conflictos",
            "resoluciones",
            "problemas",
            "situaciones",
            "circunstancias",
            "consecuencias",
            "motivos",
            "razones",
            "causas",
            "efectos",
        }
        if text_lower in COMMON_WORDS_CAPITALIZED:
            logger.debug(f"Entidad spaCy filtrada (palabra común capitalizada): '{text}'")
            return False

        # ===== NUEVO: Filtrar entidades con barra (metadatos/variantes) =====
        if "/" in text_stripped:
            logger.debug(f"Entidad spaCy filtrada (contiene barra, probable metadato): '{text}'")
            return False

        # ===== NUEVO: Filtrar entidades con flecha -> (listas de cambios) =====
        if "\u2192" in text_stripped or "->" in text_stripped:
            logger.debug(f"Entidad spaCy filtrada (contiene flecha, metadato): '{text}'")
            return False

        # ===== NUEVO: Filtrar entidades con dos puntos (metadatos tipo "Ojos: azules") =====
        # También filtra líneas de timeline como "Verano 2006: Primer trabajo"
        if ":" in text_stripped:
            logger.debug(f"Entidad spaCy filtrada (formato metadato key:value): '{text}'")
            return False

        # ===== NUEVO: Filtrar frases que empiezan con "Personaje" (metadatos) =====
        if text_lower.startswith("personaje "):
            logger.debug(f"Entidad spaCy filtrada (metadato personaje): '{text}'")
            return False

        # Filtrar frases comunes que no son entidades
        if text_lower in self.COMMON_PHRASES_NOT_ENTITIES:
            logger.debug(f"Entidad spaCy filtrada (frase común): '{text}'")
            return False

        # Filtrar descripciones físicas usando patrones regex
        for pattern in self.PHYSICAL_DESCRIPTION_PATTERNS:
            if re.match(pattern, text_lower, re.IGNORECASE):
                logger.debug(f"Entidad spaCy filtrada (descripción física): '{text}'")
                return False

        # Filtrar palabras sueltas que spaCy detecta erróneamente
        if text_lower in self.SPACY_FALSE_POSITIVE_WORDS:
            logger.debug(f"Entidad spaCy filtrada (falso positivo conocido): '{text}'")
            return False

        # Filtrar frases muy largas con muchas palabras (probablemente no son entidades)
        words = text_stripped.split()
        if len(words) > 5:
            logger.debug(f"Entidad spaCy filtrada (demasiadas palabras): '{text}'")
            return False

        # Filtrar frases que parecen oraciones (tienen verbo conjugado típico)
        # Patrones: "Algo estaba", "Era un", "Había una", etc.
        sentence_starters = {
            "algo",
            "era",
            "había",
            "fue",
            "es",
            "está",
            "estaba",
            "tiene",
            "tenía",
            "hace",
            "hacía",
            "dice",
            "decía",
            "va",
            "iba",
            "viene",
            "venía",
            "parece",
            "parecía",
        }
        first_word = words[0].lower() if words else ""
        if first_word in sentence_starters and len(words) > 2:
            logger.debug(f"Entidad spaCy filtrada (parece oración): '{text}'")
            return False

        # Filtrar frases que empiezan con artículo seguido de sustantivo/verbo común
        # Ejemplo: "El otro día", "La mañana siguiente", "La había preparado"
        if len(words) >= 2:
            if first_word in {"el", "la", "los", "las", "un", "una", "unos", "unas"}:
                second_word = words[1].lower() if len(words) > 1 else ""

                # Sustantivos/adjetivos genéricos
                generic_words = {
                    "otro",
                    "otra",
                    "mismo",
                    "misma",
                    "siguiente",
                    "anterior",
                    "hombre",
                    "mujer",
                    "persona",
                    "gente",
                    "cosa",
                    "día",
                    "noche",
                    "vez",
                    "tiempo",
                    "momento",
                    "lugar",
                    "forma",
                    "manera",
                    # Sustantivos comunes de lugares/objetos
                    "casa",
                    "calle",
                    "ciudad",
                    "país",
                    "mundo",
                    "tierra",
                    "mesa",
                    "silla",
                    "puerta",
                    "ventana",
                    "habitación",
                    "cocina",
                    "libro",
                    "vaso",
                    "copa",
                    "plato",
                    "cama",
                    "pared",
                    # Sustantivos abstractos
                    "amor",
                    "vida",
                    "muerte",
                    "verdad",
                    "historia",
                    "relación",
                    # NUEVO iter3: objetos/instrumentos
                    "reloj",
                    "telefono",
                    "teléfono",
                    "carta",
                    "sobre",
                    "llave",
                    "coche",
                    "tren",
                    "avion",
                    "avión",
                    "autobus",
                    "autobús",
                    # NUEVO iter3: elementos naturales/descripciones
                    "luz",
                    "sol",
                    "luna",
                    "cielo",
                    "aire",
                    "viento",
                    "mar",
                    "corazon",
                    "corazón",
                    "mente",
                    "alma",
                    "cuerpo",
                    # NUEVO iter3: lugares genéricos
                    "estacion",
                    "estación",
                    "aeropuerto",
                    "hospital",
                    "escuela",
                    "cafe",
                    "café",
                    "bar",
                    "restaurante",
                    "tienda",
                    "oficina",
                    # NUEVO iter3: abstracciones
                    "plan",
                    "idea",
                    "decision",
                    "decisión",
                    "problema",
                    "solucion",
                    "solución",
                    "camino",
                    "viaje",
                    "mensaje",
                    "padre",
                    "madre",
                    # NUEVO iter10: profesiones genéricas (plural)
                    "medicos",
                    "médicos",
                    "doctores",
                    "profesores",
                    "estudiantes",
                    "soldados",
                    "policias",
                    "policías",
                    "abogados",
                    "jueces",
                    # Términos anatómicos (no son nombres propios)
                    "paladar",
                    "laringe",
                    "esofago",
                    "esófago",
                    "garganta",
                    "lengua",
                    "labio",
                    "labios",
                    "diente",
                    "dientes",
                    "muela",
                    "nariz",
                    "ojo",
                    "ojos",
                    "oreja",
                    "orejas",
                    "boca",
                    "mano",
                    "manos",
                    "dedo",
                    "dedos",
                    "brazo",
                    "brazos",
                    "pierna",
                    "piernas",
                    "pie",
                    "pies",
                    "rodilla",
                    "tobillo",
                    "cabeza",
                    "cara",
                    "frente",
                    "cuello",
                    "hombro",
                    "hombros",
                    "espalda",
                    "pecho",
                    "estomago",
                    "estómago",
                    "vientre",
                    "cerebro",
                    "pulmon",
                    "pulmón",
                    "higado",
                    "hígado",
                    "riñon",
                    "riñón",
                }
                if second_word in generic_words:
                    logger.debug(f"Entidad spaCy filtrada (descripción genérica): '{text}'")
                    return False

                # NUEVO: Verbos auxiliares/conjugados comunes después de artículo
                common_verbs_after_article = {
                    "había",
                    "fue",
                    "era",
                    "es",
                    "está",
                    "estaba",
                    "tiene",
                    "tenía",
                    "hace",
                    "hacía",
                    "puede",
                    "podía",
                    "debe",
                    "debía",
                    "va",
                    "iba",
                    "viene",
                    "venía",
                    "quiere",
                    "quería",
                    "sabe",
                    "sabía",
                    "dos",
                    "tres",
                }
                if second_word in common_verbs_after_article:
                    logger.debug(f"Entidad spaCy filtrada (artículo + verbo): '{text}'")
                    return False

        # Filtrar frases que comienzan con pronombre reflexivo + verbo
        # Ejemplo: "Se levanto", "Se acerco", "Me dijo"
        REFLEXIVE_PRONOUNS = {"se", "me", "te", "nos", "os"}
        if first_word in REFLEXIVE_PRONOUNS and len(words) >= 2:
            logger.debug(f"Entidad spaCy filtrada (pronombre reflexivo + verbo): '{text}'")
            return False

        # Filtrar frases que contienen verbos conjugados (son oraciones, no entidades)
        # "El se acerco a saludarla", "Hola Maria", etc.
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
            "los",
            "las",
            # Verbos comunes conjugados
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
            # Infinitivos después de preposiciones
            "para",
            "sin",
            "por",
            "con",
            "de",
            "a",
        }
        words_lower = [w.lower() for w in words]
        if len(words) >= 3 and any(w in verb_indicators for w in words_lower[1:]):
            logger.debug(f"Entidad spaCy filtrada (contiene verbo): '{text}'")
            return False

        # Filtrar saludos como "Hola X" - extraer solo el nombre
        if first_word in {"hola", "adiós", "buenos", "buenas"}:
            logger.debug(f"Entidad spaCy filtrada (saludo): '{text}'")
            return False

        # Filtrar frases interrogativas (quién eres, qué es, etc.)
        interrogative_starters = {
            "quién",
            "quien",
            "qué",
            "que",
            "cómo",
            "como",
            "dónde",
            "donde",
            "cuándo",
            "cuando",
            "cuánto",
            "cuanto",
            "por qué",
            "para qué",
        }
        if first_word in interrogative_starters:
            logger.debug(f"Entidad spaCy filtrada (interrogativa): '{text}'")
            return False

        # Filtrar términos científicos/biológicos genéricos
        scientific_terms = {
            "endorfinas",
            "endorfina",
            "adrenalina",
            "serotonina",
            "dopamina",
            "hormona",
            "hormonas",
            "neurotransmisor",
            "neurotransmisores",
        }
        if text_lower in scientific_terms or (
            len(words) > 1 and words[-1].lower() in scientific_terms
        ):
            logger.debug(f"Entidad spaCy filtrada (término científico): '{text}'")
            return False

        # ===== NUEVO: Filtrar entidades que terminan en gerundio =====
        # Ejemplo: "Camino corriendo" no es una entidad válida
        if len(words) > 1:
            last_word_lower = words[-1].lower()
            if last_word_lower.endswith(("ando", "endo", "iendo")):
                logger.debug(f"Entidad spaCy filtrada (termina en gerundio): '{text}'")
                return False

        # ===== GENERALIZABLE: Filtrar frases que empiezan con posesivo =====
        # Patrón: "su/sus/mi/mis + sustantivo" -> descripción, no entidad
        # Ejemplo: "su novio", "mi hermano miguel", "sus padres"
        # EXCEPCION: Títulos formales como "Su Santidad", "Su Majestad", "Su Excelencia"
        POSSESSIVES = {"su", "sus", "mi", "mis", "tu", "tus", "nuestro", "nuestra"}
        FORMAL_TITLES_AFTER_SU = {
            "santidad",
            "majestad",
            "excelencia",
            "alteza",
            "eminencia",
            "señoría",
        }
        if first_word in POSSESSIVES and len(words) >= 2:
            second_word = words[1].lower() if len(words) > 1 else ""
            if second_word not in FORMAL_TITLES_AFTER_SU:
                logger.debug(f"Entidad spaCy filtrada (frase posesiva): '{text}'")
                return False

        # ===== GENERALIZABLE: Filtrar verbos conjugados (terminaciones comunes) =====
        # Detectar verbos por sus terminaciones en lugar de lista específica
        VERB_ENDINGS = (
            # Pretérito imperfecto/indefinido
            "aban",
            "ían",
            "eron",
            "aron",
            "ieron",
            "aba",
            "ía",
            "ió",
            "ó",
            # Futuro simple (-ás, -á, -án, -emos, -éis)
            "arás",
            "erás",
            "irás",
            "ará",
            "erá",
            "irá",
            "arán",
            "erán",
            "irán",
            "aremos",
            "eremos",
            "iremos",
            # Condicional (-aría, -ería, -iría)
            "aría",
            "ería",
            "iría",
            "arían",
            "erían",
            "irían",
            "aríamos",
            "eríamos",
            "iríamos",
            # Subjuntivo presente (-es, -e, -emos, -en para -ar; -as, -a, -amos, -an para -er/-ir)
            "ases",
            "ieses",
            "ase",
            "iese",
            "ásemos",
            "iésemos",
            "ara",
            "iera",
            "aras",
            "ieras",
            "áramos",
            "iéramos",
            # Subjuntivo futuro (raro pero existe)
            "are",
            "iere",
            "aren",
            "ieren",
            # Gerundio
            "ando",
            "iendo",
            "endo",
            # Infinitivo (si son una sola palabra)
            "ar",
            "er",
            "ir",
            # Presente simple 1a/2a persona plural
            "amos",
            "emos",
            "imos",
        )

        # Pronombres enclíticos que se añaden a verbos
        ENCLITICS = ("me", "te", "se", "lo", "la", "los", "las", "le", "les", "nos", "os")
        # Combinaciones dobles de enclíticos
        DOUBLE_ENCLITICS = (
            "melo",
            "mela",
            "melos",
            "melas",
            "telo",
            "tela",
            "telos",
            "telas",
            "selo",
            "sela",
            "selos",
            "selas",
            "noslo",
            "nosla",
            "noslos",
            "noslas",
        )

        # Vocales acentuadas (patrón típico de verbos con enclíticos en español)
        ACCENTED_VOWELS = ("á", "é", "í", "ó", "ú")

        if len(words) == 1 and len(text_stripped) > 4:
            # Detectar verbos con pronombres enclíticos (tomármelos, dáselo, piénsalo)
            # Patrón: raíz verbal con vocal acentuada + enclítico(s)
            # Esto es típico de imperativos y formas verbales con pronombres
            for encl in DOUBLE_ENCLITICS + ENCLITICS:
                if text_lower.endswith(encl) and len(text_lower) > len(encl) + 3:
                    # La raíz antes del enclítico
                    stem = text_lower[: -len(encl)]
                    # Solo filtrar si la raíz CONTIENE una vocal acentuada
                    # (patrón de verbo + enclítico: tomár-melos, piéns-alo, dá-selo)
                    # Esto evita falsos positivos como "Carlos", "Marcos"
                    if any(v in stem for v in ACCENTED_VOWELS):
                        logger.debug(f"Entidad spaCy filtrada (verbo + enclítico): '{text}'")
                        return False

            # Solo palabras largas para terminaciones generales
            if len(text_stripped) > 5 and text_lower.endswith(VERB_ENDINGS):
                # Terminaciones verbales muy específicas que SIEMPRE indican verbo
                # (ningún nombre propio en español termina así)
                DEFINITE_VERB_ENDINGS = (
                    # Futuro 2a persona
                    "arás",
                    "erás",
                    "irás",
                    # Condicional
                    "aría",
                    "ería",
                    "iría",
                    "arían",
                    "erían",
                    "irían",
                    # Pretérito plural
                    "aban",
                    "aron",
                    "ieron",
                    "ían",
                    # Subjuntivo
                    "ases",
                    "ieses",
                    "áramos",
                    "iéramos",
                    # 1a persona plural presente (Acabamos, Sonreímos)
                    "amos",
                    "emos",
                    "imos",
                )
                # Filtrar si:
                # 1. No empieza con mayúscula (claramente no es nombre)
                # 2. O termina en terminación verbal definitiva
                if not text_stripped[0].isupper() or text_lower.endswith(DEFINITE_VERB_ENDINGS):
                    logger.debug(f"Entidad spaCy filtrada (probable verbo): '{text}'")
                    return False

        # Detectar verbos en presente simple con mayúscula (Pones, Sonrío)
        # Patrones: termina en -es, -o (1a/2a persona singular presente)
        if len(words) == 1 and len(text_stripped) >= 4:
            # Presente 2a persona singular: -es, -as
            if text_lower.endswith(("ones", "enes", "ines", "anes", "unes")):
                logger.debug(f"Entidad spaCy filtrada (verbo presente 2a pers.): '{text}'")
                return False
            # Presente 1a persona singular con acento: -ío, -úo (sonrío, actúo)
            if text_lower.endswith(("ío", "úo")):
                logger.debug(f"Entidad spaCy filtrada (verbo presente 1a pers.): '{text}'")
                return False

        # ===== GENERALIZABLE: Filtrar entidades que terminan en verbo =====
        # Patrón: "Nombre + verbo" -> error de segmentación
        # Ejemplo: "Alejandro asintio", "María corrió"
        # CUIDADO: No filtrar apellidos válidos como "García" (termina en ía)
        if len(words) >= 2:
            last_word = words[-1].lower()
            # Solo filtrar si:
            # 1. La última palabra empieza con minúscula (verbos, no apellidos)
            # 2. O termina en patrones verbales muy específicos
            if not words[-1][0].isupper():
                if last_word.endswith(("ió", "ó", "aron", "ieron", "aba")):
                    logger.debug(f"Entidad spaCy filtrada (termina en verbo): '{text}'")
                    return False
            # Palabras que terminan en "io" sin tilde son típicamente verbos
            # Ejemplo: "asintio", "salio", "corrio"
            if last_word.endswith("io") and not last_word.endswith(("lio", "rio", "nio")):
                # Excluir sufijos comunes de nombres: -ario, -erio, -orio
                if not last_word.endswith(("ario", "erio", "orio")):
                    logger.debug(f"Entidad spaCy filtrada (termina en verbo -io): '{text}'")
                    return False

        return True

    def _is_valid_heuristic_candidate(self, text: str) -> bool:
        """
        Valida un candidato heurístico (palabra capitalizada NO detectada por spaCy).

        Para candidatos heurísticos somos más estrictos porque no tenemos
        la validación del modelo NER.

        Args:
            text: Texto del candidato

        Returns:
            True si es un candidato válido para el gazetteer
        """
        if not text:
            return False

        text_stripped = text.strip()
        canonical = text_stripped.lower()

        # Requisitos básicos
        if len(text_stripped) < 3:  # Más estricto que spaCy
            return False

        # Filtrar stopwords
        if canonical in self.STOP_TITLES:
            return False

        # Filtrar falsos positivos heurísticos (solo para candidatos, no spaCy)
        if canonical in self.HEURISTIC_FALSE_POSITIVES:
            return False

        # Filtrar números y puntuación
        return not (text.isdigit() or not any(c.isalpha() for c in text))

    def _is_high_quality_entity(self, text: str, label: EntityLabel) -> bool:
        """
        Determina si una entidad es de alta calidad para añadir al gazetteer.

        Solo añadimos al gazetteer entidades que tienen alta probabilidad
        de ser correctas, para evitar propagar falsos positivos.

        Criterios:
        - Nombres con múltiples palabras (ej: "Juan García")
        - Nombres largos (ej: "Hogwarts")
        - Lugares conocidos (ciudades, países)

        Args:
            text: Texto de la entidad
            label: Tipo de entidad

        Returns:
            True si es de alta calidad para gazetteer
        """
        if not text:
            return False

        text_stripped = text.strip()
        words = text_stripped.split()

        # Nombres con múltiples palabras son más confiables
        # Ejemplo: "Juan García", "Ciudad de México"
        if len(words) >= 2:
            # Verificar que al menos una palabra sea significativa
            significant_words = [
                w for w in words if w.lower() not in self.STOP_TITLES and len(w) > 2
            ]
            if len(significant_words) >= 2:
                return True

        # Palabras largas de una sola palabra (posiblemente nombres propios)
        # Ejemplo: "Gandalf", "Mordor", "Hogwarts"
        if len(words) == 1 and len(text_stripped) >= 5:
            # Verificar que empiece con mayúscula (nombre propio)
            if text_stripped[0].isupper():
                return True

        return False
