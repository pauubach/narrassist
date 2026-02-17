"""
Corrector semántico - Detecta palabras correctas usadas en contexto incorrecto.

Sistema genérico basado en CONFUSION_PAIRS con detección dual (keywords + embeddings).

Total: 58 pares de confusión implementados:
- 5 confusiones semánticas (riegos/riesgos, actitud/aptitud, infringir/infligir, etc.)
- 8 imperativos incorrectos (callar→callad, venir→venid, ir→id, etc.)
- 45 homofonías comunes del español:
  * Triple/cuádruple: ha/ah/a, haya/halla/aya/allá, hay/ahí/ay, vaya/valla/baya
  * Dobles: echo/hecho, tubo/tuvo, haber/a ver, botar/votar, grabar/gravar,
    revelar/rebelar, vaca/baca, hasta/asta, hierba/hierva, sabia/savia,
    caza/casa, coser/cocer

Ejemplos:
- "riegos de seguridad" → "riesgos de seguridad" (riegos=irrigación, incorrecto)
- "¡Callar todos!" → "¡Callad todos!" (infinitivo usado como imperativo)
- "A comido" → "Ha comido" (preposición vs verbo haber)
- "Voy haber" → "Voy a ver" (verbo haber vs preposición+ver)
- "Espero que allá gente" → "Espero que haya gente" (adverbio vs verbo haber)
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

from .base import SpellingErrorType, SpellingIssue, SpellingSeverity, DetectionMethod


logger = logging.getLogger(__name__)


# =============================================================================
# Pares de palabras confundibles con sus contextos típicos
# =============================================================================

@dataclass
class ConfusionPair:
    """Par de palabras que se confunden frecuentemente."""

    wrong_word: str  # Palabra usada incorrectamente
    correct_word: str  # Palabra correcta en este contexto
    wrong_meaning: str  # Significado de la palabra incorrecta
    correct_meaning: str  # Significado de la palabra correcta
    wrong_context_keywords: list[str]  # Palabras clave del contexto donde está mal usada
    correct_context_keywords: list[str]  # Palabras clave del contexto correcto de wrong_word


# Pares conocidos de confusiones semánticas
CONFUSION_PAIRS = [
    ConfusionPair(
        wrong_word="riegos",
        correct_word="riesgos",
        wrong_meaning="irrigación, regar",
        correct_meaning="peligros, amenazas",
        wrong_context_keywords=[
            # Contexto de peligros (debería ser "riesgos")
            "seguridad", "salud", "laboral", "trabajo", "accidente",
            "mercado", "financiero", "económico", "inversión",
            "amenaza", "peligro", "evaluación", "análisis", "gestión",
            "prevención", "mitigación", "protección", "control",
            "asociado", "inherente", "potencial", "grave", "alto", "medio", "bajo",
        ],
        correct_context_keywords=[
            # Contexto agrícola (correcto para "riegos")
            "agrícola", "campo", "cultivo", "riego", "regadío", "regar",
            "aspersión", "goteo", "acequia", "canal", "agua", "hidráulico",
            "irrigación", "drenaje", "hectárea", "sembrado", "tierra", "parcela", "finca",
        ],
    ),

    ConfusionPair(
        wrong_word="actitud",
        correct_word="aptitud",
        wrong_meaning="comportamiento, disposición",
        correct_meaning="capacidad, habilidad",
        wrong_context_keywords=[
            # Contexto de capacidad/habilidad (debería ser "aptitud")
            "capacidad", "habilidad", "destreza", "competencia",
            "idóneo", "cualificado", "preparado", "formación",
            "examen", "prueba", "requisito", "necesaria", "suficiente",
        ],
        correct_context_keywords=[
            # Contexto de comportamiento (correcto para "actitud")
            "comportamiento", "disposición", "postura", "ánimo",
            "positiva", "negativa", "proactiva", "pasiva",
            "cambiar", "mejorar", "mostrar", "tener",
        ],
    ),

    ConfusionPair(
        wrong_word="aptitud",
        correct_word="actitud",
        wrong_meaning="capacidad, habilidad",
        correct_meaning="comportamiento, disposición",
        wrong_context_keywords=[
            # Contexto de comportamiento (debería ser "actitud")
            "comportamiento", "disposición", "postura", "ánimo",
            "positiva", "negativa", "proactiva", "pasiva", "optimista",
            "cambiar", "mejorar", "mostrar", "tener", "adoptar",
        ],
        correct_context_keywords=[
            # Contexto de capacidad (correcto para "aptitud")
            "capacidad", "habilidad", "destreza", "competencia",
            "examen", "prueba", "test", "evaluar",
        ],
    ),

    ConfusionPair(
        wrong_word="infringir",
        correct_word="infligir",
        wrong_meaning="violar norma/ley",
        correct_meaning="causar daño/castigo",
        wrong_context_keywords=[
            # Contexto de causar daño (debería ser "infligir")
            "daño", "castigo", "dolor", "sufrimiento", "herida",
            "tortura", "maltrato", "pena", "lesión",
            "causar", "provocar", "ocasionar",
        ],
        correct_context_keywords=[
            # Contexto de violar normas (correcto para "infringir")
            "ley", "norma", "regla", "reglamento", "ordenanza",
            "violar", "vulnerar", "incumplir", "contravenir",
            "sanción", "multa", "infracción",
        ],
    ),

    ConfusionPair(
        wrong_word="infligir",
        correct_word="infringir",
        wrong_meaning="causar daño/castigo",
        correct_meaning="violar norma/ley",
        wrong_context_keywords=[
            # Contexto de violar normas (debería ser "infringir")
            "ley", "norma", "regla", "reglamento", "código",
            "violar", "vulnerar", "incumplir", "quebrantar",
            "sanción", "multa", "infracción", "penalización",
        ],
        correct_context_keywords=[
            # Contexto de causar daño (correcto para "infligir")
            "daño", "castigo", "dolor", "sufrimiento", "pena",
            "tortura", "maltrato", "herida", "lesión",
        ],
    ),

    ConfusionPair(
        wrong_word="prescribir",
        correct_word="proscribir",
        wrong_meaning="recetar, indicar",
        correct_meaning="prohibir, desterrar",
        wrong_context_keywords=[
            # Contexto de prohibir (debería ser "proscribir")
            "prohibir", "prohibición", "ilegal", "vetar", "desterrar",
            "censurar", "eliminar", "suprimir", "expulsar",
            "ley", "decreto", "ordenanza",
        ],
        correct_context_keywords=[
            # Contexto médico (correcto para "prescribir")
            "médico", "doctor", "receta", "medicamento", "tratamiento",
            "recetar", "indicar", "paciente", "tomar", "dosis",
        ],
    ),

    ConfusionPair(
        wrong_word="proscribir",
        correct_word="prescribir",
        wrong_meaning="prohibir, desterrar",
        correct_meaning="recetar, indicar",
        wrong_context_keywords=[
            # Contexto médico (debería ser "prescribir")
            "médico", "doctor", "receta", "medicamento", "fármaco",
            "tratamiento", "paciente", "dosis", "tomar",
        ],
        correct_context_keywords=[
            # Contexto de prohibir (correcto para "proscribir")
            "prohibir", "ilegal", "vetar", "censurar",
            "ley", "decreto", "eliminar", "suprimir",
        ],
    ),

    ConfusionPair(
        wrong_word="absorber",
        correct_word="absolver",
        wrong_meaning="succionar, embeber",
        correct_meaning="perdonar, exculpar",
        wrong_context_keywords=[
            # Contexto jurídico/religioso (debería ser "absolver")
            "juez", "tribunal", "sentencia", "acusado", "culpa",
            "juicio", "pecado", "confesión", "perdonar",
            "cargo", "delito", "inocente", "exculpar",
        ],
        correct_context_keywords=[
            # Contexto físico (correcto para "absorber")
            "esponja", "líquido", "agua", "humedad", "impacto",
            "succionar", "embeber", "material", "capacidad",
        ],
    ),

    ConfusionPair(
        wrong_word="absolver",
        correct_word="absorber",
        wrong_meaning="perdonar, exculpar",
        correct_meaning="succionar, embeber",
        wrong_context_keywords=[
            # Contexto físico (debería ser "absorber")
            "líquido", "agua", "humedad", "impacto", "energía",
            "esponja", "material", "superficie", "capacidad",
        ],
        correct_context_keywords=[
            # Contexto jurídico (correcto para "absolver")
            "juez", "tribunal", "sentencia", "acusado",
            "juicio", "pecado", "cargo", "delito",
        ],
    ),

    # =========================================================================
    # Imperativos incorrectos (infinitivo usado como imperativo plural)
    # =========================================================================
    # Muy común: "callar" en lugar de "callad", "venir" en lugar de "venid"

    ConfusionPair(
        wrong_word="callar",
        correct_word="callad",
        wrong_meaning="infinitivo: acción de callar",
        correct_meaning="imperativo plural: orden de callar",
        wrong_context_keywords=[
            # Contexto imperativo (debería ser "callad")
            "¡", "!", "vosotros", "ahora", "todos", "ya",
            "por favor", "silencio", "inmediatamente",
        ],
        correct_context_keywords=[
            # Contexto infinitivo (correcto para "callar")
            "hay que", "debe", "tiene que", "va a", "quiere",
            "necesita", "intenta", "trata de", "voy a",
            "para", "sin", "antes de", "después de",
        ],
    ),

    ConfusionPair(
        wrong_word="venir",
        correct_word="venid",
        wrong_meaning="infinitivo",
        correct_meaning="imperativo plural",
        wrong_context_keywords=[
            # Contexto imperativo (debería ser "venid")
            "¡", "!", "vosotros", "aquí", "ahora", "todos",
            "rápido", "ya", "conmigo", "inmediatamente",
        ],
        correct_context_keywords=[
            # Contexto infinitivo (correcto para "venir")
            "hay que", "debe", "tiene que", "va a", "quiere",
            "puede", "para", "sin", "antes de", "voy a",
        ],
    ),

    ConfusionPair(
        wrong_word="ir",
        correct_word="id",
        wrong_meaning="infinitivo",
        correct_meaning="imperativo plural",
        wrong_context_keywords=[
            # Contexto imperativo (debería ser "id")
            "¡", "!", "vosotros", "ahora", "ya", "todos",
            "allí", "allá", "inmediatamente", "rápido",
        ],
        correct_context_keywords=[
            # Contexto infinitivo (correcto para "ir")
            "hay que", "debe", "tiene que", "va a", "voy a",
            "puede", "para", "sin", "quiere", "necesita",
            "antes de", "después de",
        ],
    ),

    ConfusionPair(
        wrong_word="salir",
        correct_word="salid",
        wrong_meaning="infinitivo",
        correct_meaning="imperativo plural",
        wrong_context_keywords=[
            # Contexto imperativo (debería ser "salid")
            "¡", "!", "vosotros", "ahora", "ya", "todos",
            "rápido", "inmediatamente", "aquí",
        ],
        correct_context_keywords=[
            # Contexto infinitivo (correcto para "salir")
            "hay que", "debe", "tiene que", "va a", "voy a",
            "puede", "para", "sin", "quiere", "necesita",
        ],
    ),

    ConfusionPair(
        wrong_word="hacer",
        correct_word="haced",
        wrong_meaning="infinitivo",
        correct_meaning="imperativo plural",
        wrong_context_keywords=[
            # Contexto imperativo (debería ser "haced")
            "¡", "!", "vosotros", "ahora", "ya", "todos",
            "inmediatamente", "rápido", "esto", "eso",
        ],
        correct_context_keywords=[
            # Contexto infinitivo (correcto para "hacer")
            "hay que", "debe", "tiene que", "va a", "voy a",
            "puede", "para", "sin", "quiere", "trata de",
        ],
    ),

    ConfusionPair(
        wrong_word="decir",
        correct_word="decid",
        wrong_meaning="infinitivo",
        correct_meaning="imperativo plural",
        wrong_context_keywords=[
            # Contexto imperativo (debería ser "decid")
            "¡", "!", "vosotros", "ahora", "ya", "todos",
            "verdad", "inmediatamente", "qué", "me",
        ],
        correct_context_keywords=[
            # Contexto infinitivo (correcto para "decir")
            "hay que", "debe", "tiene que", "va a", "voy a",
            "puede", "para", "sin", "quiere", "trata de",
        ],
    ),

    ConfusionPair(
        wrong_word="mirar",
        correct_word="mirad",
        wrong_meaning="infinitivo",
        correct_meaning="imperativo plural",
        wrong_context_keywords=[
            # Contexto imperativo (debería ser "mirad")
            "¡", "!", "vosotros", "aquí", "ahí", "esto",
            "eso", "bien", "todos",
        ],
        correct_context_keywords=[
            # Contexto infinitivo (correcto para "mirar")
            "hay que", "debe", "tiene que", "va a", "voy a",
            "puede", "para", "sin", "quiere",
        ],
    ),

    ConfusionPair(
        wrong_word="escuchar",
        correct_word="escuchad",
        wrong_meaning="infinitivo",
        correct_meaning="imperativo plural",
        wrong_context_keywords=[
            # Contexto imperativo (debería ser "escuchad")
            "¡", "!", "vosotros", "atención", "bien", "todos",
            "ahora", "esto",
        ],
        correct_context_keywords=[
            # Contexto infinitivo (correcto para "escuchar")
            "hay que", "debe", "tiene que", "va a", "voy a",
            "puede", "para", "sin", "música",
        ],
    ),

    # =========================================================================
    # Confusiones comunes haber/a ver, echo/hecho, etc.
    # =========================================================================

    ConfusionPair(
        wrong_word="halla",
        correct_word="haya",
        wrong_meaning="verbo hallar (encontrar)",
        correct_meaning="verbo haber (subjuntivo)",
        wrong_context_keywords=[
            # Contexto de verbo haber (debería ser "haya")
            "que", "aunque", "cuando", "si", "tal vez", "quizá",
            "espero", "dudo", "puede", "es posible", "ojalá",
            "no creo", "no", "sin que", "antes de que",
        ],
        correct_context_keywords=[
            # Contexto de hallar/encontrar (correcto para "halla")
            "se", "lo", "la", "algo", "tesoro", "solución",
            "encuentra", "descubre", "ubicado", "situado",
        ],
    ),

    ConfusionPair(
        wrong_word="haya",
        correct_word="halla",
        wrong_meaning="verbo haber (subjuntivo)",
        correct_meaning="verbo hallar (encontrar)",
        wrong_context_keywords=[
            # Contexto de hallar (debería ser "halla")
            "se", "lo", "la", "algo", "cerca", "lejos",
            "aquí", "ahí", "allí", "donde", "ubicado",
        ],
        correct_context_keywords=[
            # Contexto de haber (correcto para "haya")
            "que", "no", "aunque", "cuando", "espero",
            "dudo", "puede", "posible", "ojalá", "tal vez",
        ],
    ),

    ConfusionPair(
        wrong_word="echo",
        correct_word="hecho",
        wrong_meaning="verbo echar (tirar, arrojar)",
        correct_meaning="verbo hacer (participio)",
        wrong_context_keywords=[
            # Contexto de participio hacer (debería ser "hecho")
            "he", "has", "ha", "han", "había", "habían",
            "bien", "mal", "ya", "sido", "estado",
        ],
        correct_context_keywords=[
            # Contexto de echar (correcto para "echo")
            "te", "me", "lo", "la", "fuera", "menos",
            "basura", "mano", "cuenta", "culpa",
        ],
    ),

    ConfusionPair(
        wrong_word="hecho",
        correct_word="echo",
        wrong_meaning="verbo hacer (participio)",
        correct_meaning="verbo echar (tirar)",
        wrong_context_keywords=[
            # Contexto de echar (debería ser "echo")
            "te", "me", "lo", "la", "fuera", "menos",
            "de", "un vistazo", "mano", "cuenta",
        ],
        correct_context_keywords=[
            # Contexto de hacer (correcto para "hecho")
            "he", "has", "ha", "han", "había", "habían",
            "bien", "mal", "sido", "es un",
        ],
    ),

    ConfusionPair(
        wrong_word="tubo",
        correct_word="tuvo",
        wrong_meaning="objeto cilíndrico hueco",
        correct_meaning="verbo tener (pasado)",
        wrong_context_keywords=[
            # Contexto de verbo tener (debería ser "tuvo")
            "él", "ella", "que", "lugar", "éxito", "problema",
            "idea", "tiempo", "oportunidad", "suerte", "razón",
        ],
        correct_context_keywords=[
            # Contexto de objeto (correcto para "tubo")
            "de", "ensayo", "escape", "agua", "gas", "metal",
            "plástico", "roto", "nuevo", "PVC",
        ],
    ),

    ConfusionPair(
        wrong_word="tuvo",
        correct_word="tubo",
        wrong_meaning="verbo tener (pasado)",
        correct_meaning="objeto cilíndrico",
        wrong_context_keywords=[
            # Contexto de objeto (debería ser "tubo")
            "de", "ensayo", "escape", "agua", "metal",
            "plástico", "roto", "diámetro",
        ],
        correct_context_keywords=[
            # Contexto de verbo (correcto para "tuvo")
            "que", "lugar", "éxito", "problema", "idea",
            "tiempo", "suerte", "razón", "ella", "él",
        ],
    ),

    ConfusionPair(
        wrong_word="haber",
        correct_word="a ver",
        wrong_meaning="verbo haber (infinitivo)",
        correct_meaning="preposición + verbo ver",
        wrong_context_keywords=[
            # Contexto de "a ver" (debería ser "a ver")
            "voy", "vamos", "venga", "ven", "déjame",
            "si", "qué", "cómo", "quién", "cuándo",
        ],
        correct_context_keywords=[
            # Contexto de "haber" (correcto)
            "debe", "tiene que", "puede", "va a", "suele",
            "sin", "por", "de", "tras", "después de",
        ],
    ),

    ConfusionPair(
        wrong_word="a ver",
        correct_word="haber",
        wrong_meaning="preposición + verbo ver",
        correct_meaning="verbo haber",
        wrong_context_keywords=[
            # Contexto de haber (debería ser "haber")
            "debe", "tiene que", "puede", "va a", "suele",
            "de", "por", "sin", "tras", "después de",
        ],
        correct_context_keywords=[
            # Contexto de "a ver" (correcto)
            "voy", "vamos", "ven", "déjame", "venga",
            "si", "qué", "cómo",
        ],
    ),

    # =========================================================================
    # Triple homofonía: ha / ah / a
    # =========================================================================

    ConfusionPair(
        wrong_word="a",
        correct_word="ha",
        wrong_meaning="preposición",
        correct_meaning="verbo haber (3ª singular)",
        wrong_context_keywords=[
            # Contexto de verbo haber (debería ser "ha")
            "comido", "hecho", "sido", "estado", "tenido",
            "llegado", "visto", "dicho", "ido", "venido",
            "pasado", "ocurrido", "terminado", "comenzado",
            "de ser", "de estar", "de tener", "de hacer",
        ],
        correct_context_keywords=[
            # Contexto de preposición (correcto para "a")
            "casa", "pie", "mano", "voy", "vas", "va",
            "ir", "venir", "llegar", "partir", "salir",
            "distancia", "dirección", "hacia", "junto",
        ],
    ),

    ConfusionPair(
        wrong_word="a",
        correct_word="ah",
        wrong_meaning="preposición",
        correct_meaning="interjección",
        wrong_context_keywords=[
            # Contexto de interjección (debería ser "ah")
            "!", "¡", "ya", "entiendo", "claro", "sí",
            "bueno", "vale", "ok", "cierto", "verdad",
        ],
        correct_context_keywords=[
            # Contexto de preposición (correcto para "a")
            "casa", "pie", "mano", "voy", "vas", "va",
            "ir", "venir", "llegar",
        ],
    ),

    ConfusionPair(
        wrong_word="ha",
        correct_word="a",
        wrong_meaning="verbo haber (3ª singular)",
        correct_meaning="preposición",
        wrong_context_keywords=[
            # Contexto de preposición (debería ser "a")
            "casa", "pie", "mano", "voy", "vas", "va",
            "ir", "venir", "llegar", "partir", "salir",
            "distancia", "dirección", "hacia",
        ],
        correct_context_keywords=[
            # Contexto de verbo haber (correcto para "ha")
            "comido", "hecho", "sido", "estado", "tenido",
            "llegado", "visto", "dicho", "ido", "venido",
            "de ser", "de estar",
        ],
    ),

    ConfusionPair(
        wrong_word="ah",
        correct_word="ha",
        wrong_meaning="interjección",
        correct_meaning="verbo haber (3ª singular)",
        wrong_context_keywords=[
            # Contexto de verbo haber (debería ser "ha")
            "comido", "hecho", "sido", "estado", "tenido",
            "llegado", "visto", "dicho", "ido", "venido",
            "pasado", "ocurrido",
        ],
        correct_context_keywords=[
            # Contexto de interjección (correcto para "ah")
            "!", "¡", "ya", "entiendo", "claro", "sí",
            "bueno", "vale",
        ],
    ),

    # =========================================================================
    # Triple/Cuádruple homofonía: haya / halla / aya / allá
    # =========================================================================

    ConfusionPair(
        wrong_word="aya",
        correct_word="haya",
        wrong_meaning="niñera (arcaico)",
        correct_meaning="verbo haber (subjuntivo)",
        wrong_context_keywords=[
            # Contexto de verbo haber (debería ser "haya")
            "que", "aunque", "cuando", "si", "tal vez", "quizá",
            "espero", "dudo", "puede", "posible", "ojalá",
        ],
        correct_context_keywords=[
            # Contexto de niñera (correcto para "aya", muy raro)
            "niñera", "criada", "niños", "cuidar", "servicio",
        ],
    ),

    ConfusionPair(
        wrong_word="aya",
        correct_word="halla",
        wrong_meaning="niñera (arcaico)",
        correct_meaning="verbo hallar",
        wrong_context_keywords=[
            # Contexto de hallar (debería ser "halla")
            "se", "lo", "la", "encuentra", "ubicado", "situado",
        ],
        correct_context_keywords=[
            # Contexto de niñera (correcto para "aya")
            "niñera", "criada", "niños",
        ],
    ),

    ConfusionPair(
        wrong_word="allá",
        correct_word="haya",
        wrong_meaning="adverbio de lugar (lejos)",
        correct_meaning="verbo haber (subjuntivo)",
        wrong_context_keywords=[
            # Contexto de verbo haber (debería ser "haya")
            "que", "aunque", "cuando", "si", "tal vez",
            "espero", "dudo", "puede", "posible",
        ],
        correct_context_keywords=[
            # Contexto de lugar lejano (correcto para "allá")
            "más", "lejos", "allí", "aquí", "arriba",
            "abajo", "está", "ve", "mira",
        ],
    ),

    ConfusionPair(
        wrong_word="allá",
        correct_word="halla",
        wrong_meaning="adverbio de lugar (lejos)",
        correct_meaning="verbo hallar",
        wrong_context_keywords=[
            # Contexto de hallar (debería ser "halla")
            "se", "lo", "la", "encuentra", "ubicado",
        ],
        correct_context_keywords=[
            # Contexto de lugar (correcto para "allá")
            "más", "lejos", "allí", "aquí", "está",
        ],
    ),

    # =========================================================================
    # Triple homofonía: hay / ahí / ay
    # =========================================================================

    ConfusionPair(
        wrong_word="ahí",
        correct_word="hay",
        wrong_meaning="adverbio de lugar (ahí)",
        correct_meaning="verbo haber (existencia)",
        wrong_context_keywords=[
            # Contexto de verbo haber (debería ser "hay")
            "que", "mucho", "poco", "algo", "nada",
            "alguien", "nadie", "gente", "personas",
            "problema", "solución", "tiempo",
        ],
        correct_context_keywords=[
            # Contexto de lugar (correcto para "ahí")
            "está", "mira", "pon", "deja", "ve",
            "allí", "aquí", "cerca", "delante",
        ],
    ),

    ConfusionPair(
        wrong_word="ahí",
        correct_word="ay",
        wrong_meaning="adverbio de lugar",
        correct_meaning="interjección de dolor",
        wrong_context_keywords=[
            # Contexto de interjección (debería ser "ay")
            "!", "¡", "dolor", "madre", "dios",
            "qué", "duele", "pobre",
        ],
        correct_context_keywords=[
            # Contexto de lugar (correcto para "ahí")
            "está", "mira", "pon", "deja",
        ],
    ),

    ConfusionPair(
        wrong_word="ay",
        correct_word="hay",
        wrong_meaning="interjección de dolor",
        correct_meaning="verbo haber (existencia)",
        wrong_context_keywords=[
            # Contexto de verbo haber (debería ser "hay")
            "que", "mucho", "poco", "algo", "nada",
            "alguien", "nadie", "gente",
        ],
        correct_context_keywords=[
            # Contexto de interjección (correcto para "ay")
            "!", "¡", "dolor", "madre", "dios",
            "qué", "duele",
        ],
    ),

    ConfusionPair(
        wrong_word="hay",
        correct_word="ahí",
        wrong_meaning="verbo haber (existencia)",
        correct_meaning="adverbio de lugar",
        wrong_context_keywords=[
            # Contexto de lugar (debería ser "ahí")
            "está", "mira", "pon", "deja", "ve",
            "allí", "aquí", "cerca",
        ],
        correct_context_keywords=[
            # Contexto de verbo haber (correcto para "hay")
            "que", "mucho", "poco", "algo", "nada",
            "alguien", "nadie",
        ],
    ),

    # =========================================================================
    # Triple homofonía: vaya / valla / baya
    # =========================================================================

    ConfusionPair(
        wrong_word="valla",
        correct_word="vaya",
        wrong_meaning="cerca, obstáculo",
        correct_meaning="verbo ir (subjuntivo)",
        wrong_context_keywords=[
            # Contexto de verbo ir (debería ser "vaya")
            "que", "aunque", "cuando", "si", "ojalá",
            "espero", "dudo", "puede", "no creo",
            "antes de que", "sin que",
        ],
        correct_context_keywords=[
            # Contexto de cerca/obstáculo (correcto para "valla")
            "publicitaria", "madera", "metal", "saltar",
            "rodear", "cercar", "límite", "frontera",
        ],
    ),

    ConfusionPair(
        wrong_word="valla",
        correct_word="baya",
        wrong_meaning="cerca, obstáculo",
        correct_meaning="fruto carnoso",
        wrong_context_keywords=[
            # Contexto de fruto (debería ser "baya")
            "fruto", "uva", "tomate", "fruta", "arándano",
            "comer", "dulce", "planta",
        ],
        correct_context_keywords=[
            # Contexto de cerca (correcto para "valla")
            "publicitaria", "madera", "metal", "saltar",
        ],
    ),

    ConfusionPair(
        wrong_word="baya",
        correct_word="vaya",
        wrong_meaning="fruto carnoso",
        correct_meaning="verbo ir (subjuntivo)",
        wrong_context_keywords=[
            # Contexto de verbo ir (debería ser "vaya")
            "que", "aunque", "cuando", "espero", "ojalá",
        ],
        correct_context_keywords=[
            # Contexto de fruto (correcto para "baya")
            "fruto", "uva", "arándano", "comer",
        ],
    ),

    # =========================================================================
    # Homofonía: botar / votar
    # =========================================================================

    ConfusionPair(
        wrong_word="botar",
        correct_word="votar",
        wrong_meaning="saltar, rebotar",
        correct_meaning="emitir voto",
        wrong_context_keywords=[
            # Contexto de votar (debería ser "votar")
            "elecciones", "votación", "candidato", "urna",
            "sufragio", "democracia", "partido", "político",
            "referéndum", "papeleta",
        ],
        correct_context_keywords=[
            # Contexto de botar (correcto)
            "pelota", "balón", "saltar", "rebotar",
            "tirar", "basura", "bote",
        ],
    ),

    ConfusionPair(
        wrong_word="votar",
        correct_word="botar",
        wrong_meaning="emitir voto",
        correct_meaning="saltar, rebotar",
        wrong_context_keywords=[
            # Contexto de botar (debería ser "botar")
            "pelota", "balón", "saltar", "rebotar",
            "tirar", "basura", "bote",
        ],
        correct_context_keywords=[
            # Contexto de votar (correcto)
            "elecciones", "candidato", "urna", "democracia",
        ],
    ),

    # =========================================================================
    # Homofonía: grabar / gravar
    # =========================================================================

    ConfusionPair(
        wrong_word="grabar",
        correct_word="gravar",
        wrong_meaning="registrar sonido/imagen",
        correct_meaning="imponer impuesto",
        wrong_context_keywords=[
            # Contexto de impuesto (debería ser "gravar")
            "impuesto", "tributo", "tasa", "fiscal",
            "hacienda", "contribución", "carga",
        ],
        correct_context_keywords=[
            # Contexto de registrar (correcto para "grabar")
            "vídeo", "audio", "cámara", "micrófono",
            "disco", "sonido", "imagen", "película",
        ],
    ),

    ConfusionPair(
        wrong_word="gravar",
        correct_word="grabar",
        wrong_meaning="imponer impuesto",
        correct_meaning="registrar sonido/imagen",
        wrong_context_keywords=[
            # Contexto de registrar (debería ser "grabar")
            "vídeo", "audio", "cámara", "micrófono",
            "disco", "sonido", "película",
        ],
        correct_context_keywords=[
            # Contexto de impuesto (correcto para "gravar")
            "impuesto", "tributo", "fiscal", "hacienda",
        ],
    ),

    # =========================================================================
    # Homofonía: revelar / rebelar
    # =========================================================================

    ConfusionPair(
        wrong_word="revelar",
        correct_word="rebelar",
        wrong_meaning="descubrir secreto",
        correct_meaning="sublevarse",
        wrong_context_keywords=[
            # Contexto de rebelarse (debería ser "rebelar")
            "sublevarse", "levantarse", "contra", "autoridad",
            "protesta", "rebeldía", "rebelión", "insurrección",
        ],
        correct_context_keywords=[
            # Contexto de revelar (correcto)
            "secreto", "verdad", "fotografía", "descubrir",
            "mostrar", "información", "dato",
        ],
    ),

    ConfusionPair(
        wrong_word="rebelar",
        correct_word="revelar",
        wrong_meaning="sublevarse",
        correct_meaning="descubrir secreto",
        wrong_context_keywords=[
            # Contexto de revelar (debería ser "revelar")
            "secreto", "verdad", "fotografía", "descubrir",
            "mostrar", "información",
        ],
        correct_context_keywords=[
            # Contexto de rebelarse (correcto)
            "contra", "autoridad", "rebeldía", "protesta",
        ],
    ),

    # =========================================================================
    # Homofonía: vaca / baca
    # =========================================================================

    ConfusionPair(
        wrong_word="vaca",
        correct_word="baca",
        wrong_meaning="animal bovino",
        correct_meaning="portaequipajes de vehículo",
        wrong_context_keywords=[
            # Contexto de portaequipajes (debería ser "baca")
            "coche", "auto", "vehículo", "techo", "equipaje",
            "maleta", "carga", "portaequipajes",
        ],
        correct_context_keywords=[
            # Contexto de animal (correcto para "vaca")
            "animal", "leche", "granja", "campo", "bovino",
            "ternero", "mugir", "pasto",
        ],
    ),

    ConfusionPair(
        wrong_word="baca",
        correct_word="vaca",
        wrong_meaning="portaequipajes",
        correct_meaning="animal bovino",
        wrong_context_keywords=[
            # Contexto de animal (debería ser "vaca")
            "animal", "leche", "granja", "campo", "bovino",
            "mugir", "pasto",
        ],
        correct_context_keywords=[
            # Contexto de portaequipajes (correcto para "baca")
            "coche", "techo", "equipaje", "maleta",
        ],
    ),

    # =========================================================================
    # Homofonía: hasta / asta
    # =========================================================================

    ConfusionPair(
        wrong_word="hasta",
        correct_word="asta",
        wrong_meaning="preposición (límite)",
        correct_meaning="palo de bandera / cuerno",
        wrong_context_keywords=[
            # Contexto de asta (debería ser "asta")
            "bandera", "cuerno", "palo", "toro", "ciervo",
            "mástil", "izar",
        ],
        correct_context_keywords=[
            # Contexto de preposición (correcto para "hasta")
            "luego", "pronto", "mañana", "aquí", "allí",
            "el final", "que", "cuando",
        ],
    ),

    ConfusionPair(
        wrong_word="asta",
        correct_word="hasta",
        wrong_meaning="palo de bandera / cuerno",
        correct_meaning="preposición (límite)",
        wrong_context_keywords=[
            # Contexto de preposición (debería ser "hasta")
            "luego", "pronto", "mañana", "aquí", "allí",
            "el final", "que",
        ],
        correct_context_keywords=[
            # Contexto de asta (correcto)
            "bandera", "cuerno", "toro", "mástil",
        ],
    ),

    # =========================================================================
    # Homofonía: hierba / hierva
    # =========================================================================

    ConfusionPair(
        wrong_word="hierba",
        correct_word="hierva",
        wrong_meaning="planta",
        correct_meaning="verbo hervir (subjuntivo)",
        wrong_context_keywords=[
            # Contexto de hervir (debería ser "hierva")
            "que", "agua", "cuando", "aunque", "espero",
            "dudo", "hervir", "ebullición",
        ],
        correct_context_keywords=[
            # Contexto de planta (correcto para "hierba")
            "planta", "jardín", "verde", "césped",
            "cortar", "prado", "campo",
        ],
    ),

    ConfusionPair(
        wrong_word="hierva",
        correct_word="hierba",
        wrong_meaning="verbo hervir (subjuntivo)",
        correct_meaning="planta",
        wrong_context_keywords=[
            # Contexto de planta (debería ser "hierba")
            "planta", "jardín", "verde", "césped",
            "cortar", "prado",
        ],
        correct_context_keywords=[
            # Contexto de hervir (correcto para "hierva")
            "que", "agua", "hervir", "ebullición",
        ],
    ),

    # =========================================================================
    # Homofonía: sabia / savia
    # =========================================================================

    ConfusionPair(
        wrong_word="sabia",
        correct_word="savia",
        wrong_meaning="mujer con sabiduría",
        correct_meaning="líquido de plantas",
        wrong_context_keywords=[
            # Contexto de savia (debería ser "savia")
            "planta", "árbol", "líquido", "vegetal",
            "circula", "nutriente", "tallo",
        ],
        correct_context_keywords=[
            # Contexto de sabiduría (correcto para "sabia")
            "mujer", "persona", "conocimiento", "inteligente",
            "experta", "erudita",
        ],
    ),

    ConfusionPair(
        wrong_word="savia",
        correct_word="sabia",
        wrong_meaning="líquido de plantas",
        correct_meaning="mujer con sabiduría",
        wrong_context_keywords=[
            # Contexto de sabiduría (debería ser "sabia")
            "mujer", "persona", "conocimiento", "inteligente",
            "experta",
        ],
        correct_context_keywords=[
            # Contexto de savia (correcto)
            "planta", "árbol", "líquido", "vegetal",
        ],
    ),

    # =========================================================================
    # Homofonía: caza / casa
    # =========================================================================

    ConfusionPair(
        wrong_word="caza",
        correct_word="casa",
        wrong_meaning="acción de cazar",
        correct_meaning="vivienda",
        wrong_context_keywords=[
            # Contexto de vivienda (debería ser "casa")
            "hogar", "vivienda", "vivo", "habito",
            "piso", "dormitorio", "cocina", "sala",
            "alquiler", "hipoteca", "mi", "tu", "su",
        ],
        correct_context_keywords=[
            # Contexto de cazar (correcto para "caza")
            "cazador", "rifle", "escopeta", "animal",
            "monte", "jabalí", "ciervo", "temporada",
        ],
    ),

    ConfusionPair(
        wrong_word="casa",
        correct_word="caza",
        wrong_meaning="vivienda",
        correct_meaning="acción de cazar",
        wrong_context_keywords=[
            # Contexto de cazar (debería ser "caza")
            "cazador", "rifle", "animal", "monte",
        ],
        correct_context_keywords=[
            # Contexto de vivienda (correcto para "casa")
            "hogar", "vivo", "piso", "mi", "tu",
        ],
    ),

    # =========================================================================
    # Homofonía: coser / cocer
    # =========================================================================

    ConfusionPair(
        wrong_word="coser",
        correct_word="cocer",
        wrong_meaning="unir con hilo",
        correct_meaning="cocinar con agua",
        wrong_context_keywords=[
            # Contexto de cocinar (debería ser "cocer")
            "hervir", "agua", "cocina", "olla", "fuego",
            "patatas", "verduras", "alimento", "ebullición",
        ],
        correct_context_keywords=[
            # Contexto de coser (correcto)
            "aguja", "hilo", "tela", "botón", "máquina",
            "coser", "ropa", "costura",
        ],
    ),

    ConfusionPair(
        wrong_word="cocer",
        correct_word="coser",
        wrong_meaning="cocinar con agua",
        correct_meaning="unir con hilo",
        wrong_context_keywords=[
            # Contexto de coser (debería ser "coser")
            "aguja", "hilo", "tela", "botón", "ropa",
        ],
        correct_context_keywords=[
            # Contexto de cocinar (correcto para "cocer")
            "agua", "cocina", "olla", "fuego", "hervir",
        ],
    ),
]


# Ventana de contexto (palabras antes/después)
CONTEXT_WINDOW = 8  # ~8 palabras = ~120 caracteres


class SemanticChecker:
    """
    Detector genérico de palabras fuera de contexto semántico.

    Usa dos métodos:
    1. Keywords: Búsqueda rápida de palabras clave del contexto
    2. Embeddings: Análisis de similitud semántica (opcional, más preciso)
    """

    def __init__(self, use_embeddings: bool = True):
        """
        Args:
            use_embeddings: Si True, usar embeddings para detección (más preciso pero más lento)
        """
        self.use_embeddings = use_embeddings and EMBEDDINGS_AVAILABLE
        self._model: Optional[SentenceTransformer] = None

        if self.use_embeddings:
            try:
                # Lazy loading del modelo
                from narrative_assistant.nlp.embeddings import EmbeddingsModel
                embeddings_model = EmbeddingsModel()
                self._model = embeddings_model.model
                logger.info("SemanticChecker: usando embeddings para detección semántica")
            except Exception as e:
                logger.warning(f"No se pudo cargar modelo de embeddings: {e}")
                self.use_embeddings = False

    def check(self, text: str, window: int = CONTEXT_WINDOW) -> list[SpellingIssue]:
        """
        Detectar palabras correctas usadas en contexto semántico incorrecto.

        Args:
            text: Texto a analizar
            window: Ventana de contexto (palabras antes/después)

        Returns:
            Lista de issues detectados
        """
        issues = []

        for pair in CONFUSION_PAIRS:
            # Buscar todas las ocurrencias de la palabra potencialmente incorrecta
            pattern = rf"\b{re.escape(pair.wrong_word)}\b"

            for match in re.finditer(pattern, text, re.IGNORECASE):
                start_char = match.start()
                end_char = match.end()
                word = match.group()

                # Extraer ventana de contexto
                before_start = max(0, start_char - (window * 15))  # ~15 chars por palabra
                after_end = min(len(text), end_char + (window * 15))
                context = text[before_start:after_end].lower()

                # Método 1: Keyword matching (rápido)
                in_wrong_context = self._check_keywords(context, pair.wrong_context_keywords)
                in_correct_context = self._check_keywords(context, pair.correct_context_keywords)

                # Método 2: Embeddings (más preciso, opcional)
                semantic_mismatch = False
                confidence = 0.70  # Base para keyword matching

                if self.use_embeddings and self._model and in_wrong_context:
                    semantic_mismatch, embedding_confidence = self._check_embeddings(
                        context, pair
                    )
                    if semantic_mismatch:
                        confidence = max(confidence, embedding_confidence)

                # Decisión: marcar si está en contexto incorrecto Y NO en contexto correcto
                should_flag = (
                    in_wrong_context  # Keywords indican contexto incorrecto
                    and not in_correct_context  # NO hay keywords del contexto correcto
                ) or semantic_mismatch  # O embeddings confirman incoherencia

                if should_flag:
                    sentence = _extract_sentence(text, start_char)

                    explanation = (
                        f'Posible confusión: "{pair.wrong_word}" ({pair.wrong_meaning}) '
                        f'en lugar de "{pair.correct_word}" ({pair.correct_meaning})'
                    )

                    issues.append(
                        SpellingIssue(
                            word=word,
                            start_char=start_char,
                            end_char=end_char,
                            sentence=sentence,
                            error_type=SpellingErrorType.SEMANTIC,
                            severity=SpellingSeverity.WARNING,
                            suggestions=[pair.correct_word],
                            best_suggestion=pair.correct_word,
                            confidence=confidence,
                            detection_method=DetectionMethod.CONTEXT if not semantic_mismatch else DetectionMethod.LLM,
                            explanation=explanation,
                        )
                    )

        return issues

    def _check_keywords(self, context: str, keywords: list[str]) -> bool:
        """Verificar si alguna keyword aparece en el contexto como palabra completa."""
        # Usar word boundaries para evitar falsos positivos
        # (ej: "riego" no debe matchear dentro de "riegos")
        for keyword in keywords:
            # Pattern con word boundaries
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, context, re.IGNORECASE):
                return True
        return False

    def _check_embeddings(
        self, context: str, pair: ConfusionPair
    ) -> tuple[bool, float]:
        """
        Verificar incoherencia semántica usando embeddings.

        Returns:
            (is_mismatch, confidence)
        """
        if not self._model:
            return False, 0.0

        try:
            # Crear dos versiones del contexto: con palabra incorrecta y correcta
            context_with_wrong = context
            context_with_correct = context.replace(pair.wrong_word, pair.correct_word)

            # Obtener embeddings
            embeddings = self._model.encode([context_with_wrong, context_with_correct])

            # Calcular similitud coseno
            from numpy import dot
            from numpy.linalg import norm

            similarity = dot(embeddings[0], embeddings[1]) / (
                norm(embeddings[0]) * norm(embeddings[1])
            )

            # Si reemplazar la palabra AUMENTA la coherencia significativamente,
            # entonces la palabra original estaba fuera de contexto
            # Umbral: si similitud < 0.92, significa que la corrección mejora el texto
            threshold = 0.92
            is_mismatch = similarity < threshold

            # Confianza: cuánto mejora la corrección (1.0 - similarity)
            confidence = min(0.95, 0.70 + (threshold - similarity) * 2)

            return is_mismatch, confidence

        except Exception as e:
            logger.debug(f"Error en _check_embeddings: {e}")
            return False, 0.0


def check_semantic_context(text: str, window: int = CONTEXT_WINDOW) -> list[SpellingIssue]:
    """
    Función helper para detección semántica rápida.

    Args:
        text: Texto a analizar
        window: Ventana de contexto

    Returns:
        Lista de issues
    """
    checker = SemanticChecker(use_embeddings=True)
    return checker.check(text, window)


def _extract_sentence(text: str, position: int, max_len: int = 200) -> str:
    """Extraer oración que contiene la posición dada."""
    # Buscar hacia atrás hasta . ! ? o inicio
    start = position
    while start > 0 and text[start - 1] not in ".!?\n":
        start -= 1
        if position - start > max_len:
            break

    # Buscar hacia adelante hasta . ! ? o fin
    end = position
    while end < len(text) and text[end] not in ".!?\n":
        end += 1
        if end - position > max_len:
            break

    sentence = text[start:end].strip()
    if len(sentence) > max_len:
        sentence = sentence[:max_len] + "..."

    return sentence
