"""
Reglas gramaticales del español implementadas en Python.

Este módulo proporciona detección de errores gramaticales comunes sin
dependencias externas (usa spaCy que ya está instalado).

Reglas implementadas:
- Dequeísmo: "pienso de que" → "pienso que"
- Queísmo: "me alegro que" → "me alegro de que"
- Leísmo/Laísmo/Loísmo: uso incorrecto de pronombres
- Concordancia de género y número
- Expresiones redundantes
"""

import re
from dataclasses import dataclass

from spacy.tokens import Doc

from .base import (
    LEMMA_REDUNDANCIES,
    REDUNDANT_EXPRESSIONS,
    GrammarDetectionMethod,
    GrammarErrorType,
    GrammarIssue,
    GrammarSeverity,
)

# S15: Detector híbrido de 'a' tónica (lista + automático)
try:
    from .stress_detector import requires_masculine_article
    STRESS_DETECTOR_AVAILABLE = True
except ImportError:
    STRESS_DETECTOR_AVAILABLE = False
    def requires_masculine_article(*args, **kwargs):
        """Fallback cuando stress_detector no está disponible."""
        return False

# =============================================================================
# Listas de verbos para reglas de dequeísmo/queísmo
# =============================================================================

# Verbos que NUNCA llevan "de" antes de "que" (dequeísmo si lo llevan)
DEQUEISMO_VERBS = {
    # Verbos de pensamiento/opinión
    "pensar",
    "creer",
    "opinar",
    "considerar",
    "suponer",
    "imaginar",
    "sospechar",
    "presumir",
    "estimar",
    "juzgar",
    "entender",
    # Verbos de comunicación
    "decir",
    "afirmar",
    "negar",
    "asegurar",
    "sostener",
    "manifestar",
    "expresar",
    "indicar",
    "señalar",
    "comunicar",
    "anunciar",
    "advertir",
    "declarar",
    "proclamar",
    "revelar",
    "confesar",
    "reconocer",
    "comentar",
    "mencionar",
    "explicar",
    "contar",
    "relatar",
    # Verbos de percepción
    "ver",
    "notar",
    "observar",
    "percibir",
    "sentir",
    "oír",
    "escuchar",
    "comprobar",
    "constatar",
    "verificar",
    "descubrir",
    # Verbos de resultado/parecer
    "parecer",
    "resultar",
    "suceder",
    "ocurrir",
    "pasar",
    # Verbos de deseo/necesidad
    "desear",
    "querer",
    "necesitar",
    "esperar",
    "preferir",
    "pretender",
    "intentar",
    "procurar",
    "lograr",
    "conseguir",
    # Verbos de conocimiento
    "saber",
    "conocer",
    "ignorar",
    "dudar",
    "recordar",
}

# Verbos que SÍ llevan "de" antes de "que" (queísmo si no lo llevan)
QUEISMO_VERBS = {
    # Verbos pronominales con "de"
    "acordarse",
    "alegrarse",
    "arrepentirse",
    "avergonzarse",
    "convencerse",
    "enterarse",
    "olvidarse",
    "quejarse",
    "lamentarse",
    "jactarse",
    "ufanarse",
    "vanagloriarse",
    "preocuparse",
    "asegurarse",
    "cerciorarse",
    "percatarse",
    # Expresiones con "estar"
    "estar seguro",
    "estar convencido",
    "estar persuadido",
    "estar harto",
    "estar cansado",
    # Expresiones con "tener"
    "tener la certeza",
    "tener la seguridad",
    "tener la impresión",
    "tener miedo",
    "tener la sensación",
    "tener la sospecha",
    # Expresiones con "darse"
    "darse cuenta",
    # Otros verbos que rigen "de"
    "tratar",
    "depender",
    "carecer",
    "prescindir",
    "abstenerse",
    "guardarse",
    "librarse",
    "encargarse",
    "ocuparse",
    "responsabilizarse",
}

# Sustantivos que rigen "de que"
QUEISMO_NOUNS = {
    "seguridad",
    "certeza",
    "convicción",
    "convencimiento",
    "impresión",
    "sensación",
    "sospecha",
    "temor",
    "miedo",
    "esperanza",
    "posibilidad",
    "probabilidad",
    "necesidad",
    "condición",
    "hecho",
    "idea",
    "opinión",
    "creencia",
}


# =============================================================================
# Reglas de Dequeísmo
# =============================================================================


def check_dequeismo(doc: Doc) -> list[GrammarIssue]:
    """
    Detectar dequeísmo: uso incorrecto de "de que" donde solo debe ir "que".

    Ejemplos de dequeísmo:
    - "Pienso de que vendrá" → "Pienso que vendrá"
    - "Me dijo de que vendría" → "Me dijo que vendría"
    - "Es seguro de que llueve" → "Es seguro que llueve"

    IMPORTANTE: No es dequeísmo cuando "de que" depende de un verbo que SÍ lo requiere:
    - "me di cuenta de que creía" → CORRECTO (depende de "darse cuenta", no de "creer")
    - "estaba seguro de que venía" → CORRECTO (depende de "estar seguro", no del verbo subordinado)
    """
    issues = []
    text_lower = doc.text.lower()

    # Patrones comunes de conjugación para verbos de dequeísmo
    # Incluimos formas conjugadas frecuentes
    DEQUEISMO_PATTERNS = {
        # pensar
        "pienso",
        "piensas",
        "piensa",
        "pensamos",
        "pensáis",
        "piensan",
        "pensaba",
        "pensabas",
        "pensábamos",
        "pensaban",
        "pensé",
        "pensaste",
        "pensó",
        "pensaron",
        # creer
        "creo",
        "crees",
        "cree",
        "creemos",
        "creéis",
        "creen",
        "creía",
        "creías",
        "creíamos",
        "creían",
        "creí",
        "creíste",
        "creyó",
        "creyeron",
        # opinar
        "opino",
        "opinas",
        "opina",
        "opinamos",
        "opinan",
        "opinaba",
        "opinaban",
        "opiné",
        "opinó",
        # considerar
        "considero",
        "considera",
        "consideramos",
        "consideran",
        "consideraba",
        "consideré",
        "consideró",
        # suponer
        "supongo",
        "supones",
        "supone",
        "suponemos",
        "suponen",
        "suponía",
        "supuse",
        "supuso",
        # imaginar
        "imagino",
        "imaginas",
        "imagina",
        "imaginamos",
        "imaginan",
        "imaginaba",
        "imaginé",
        "imaginó",
        # decir
        "digo",
        "dices",
        "dice",
        "decimos",
        "dicen",
        "decía",
        "decían",
        "dije",
        "dijiste",
        "dijo",
        "dijeron",
        # afirmar
        "afirmo",
        "afirma",
        "afirmamos",
        "afirman",
        "afirmaba",
        "afirmé",
        "afirmó",
        # parecer
        "parece",
        "parecía",
        # resultar
        "resulta",
        "resultaba",
    }

    # Patrones que CANCELAN el dequeísmo (si aparecen antes, "de que" es correcto)
    # Estos son verbos/expresiones que SÍ requieren "de que"
    QUEISMO_PATTERNS_BEFORE = {
        # darse cuenta
        "cuenta",
        "di cuenta",
        "darse cuenta",
        "dando cuenta",
        "dado cuenta",
        # estar seguro/convencido
        "seguro",
        "segura",
        "convencido",
        "convencida",
        "persuadido",
        "persuadida",
        # acordarse
        "acuerdo",
        "acordaba",
        "acordé",
        "acordó",
        # olvidarse
        "olvidé",
        "olvidó",
        "olvidaba",
        # enterarse
        "enteré",
        "enteró",
        "enteraba",
        # alegrarse
        "alegro",
        "alegraba",
        "alegré",
        # arrepentirse
        "arrepiento",
        "arrepentía",
        # tener certeza/seguridad
        "certeza",
        "seguridad",
        "impresión",
        "sensación",
        # a pesar, a fin, a condición
        "pesar",
        "fin",
        "condición",
        # antes, después (cuando llevan "de")
        "antes",
        "después",
    }

    # Buscar patrón "de que" en el texto
    for match in re.finditer(r"\bde\s+que\b", text_lower):
        start, end = match.span()

        # Encontrar el contexto antes de "de que"
        context_before = text_lower[:start].strip()
        words_before = context_before.split()

        if not words_before:
            continue

        # PRIMERO: Verificar si hay un patrón que CANCELA el dequeísmo
        # (es decir, si "de que" es correcto porque depende de algo que lo requiere)
        is_valid_de_que = False
        # Revisar las últimas 10 palabras para contexto más amplio
        context_words = words_before[-10:] if len(words_before) >= 10 else words_before
        context_str = " ".join(context_words)

        for valid_pattern in QUEISMO_PATTERNS_BEFORE:
            if valid_pattern in context_str:
                is_valid_de_que = True
                break

        if is_valid_de_que:
            continue  # No es dequeísmo, saltar

        # Buscar el verbo que precede a "de que"
        verb_found = None
        is_dequeismo = False

        # Revisar las últimas palabras para encontrar el verbo
        for i in range(min(5, len(words_before)), 0, -1):
            word = words_before[-i].strip(".,;:¿?¡!—\"'")

            # Primero buscar en patrones exactos (conjugaciones conocidas)
            if word in DEQUEISMO_PATTERNS:
                verb_found = word
                is_dequeismo = True
                break

            # Luego buscar por raíz del verbo (fallback)
            for verb in DEQUEISMO_VERBS:
                # Solo comparar si la palabra tiene al menos 4 caracteres
                if len(word) >= 4 and len(verb) >= 4:
                    # Comparar raíz (primeros 4-5 caracteres)
                    if word[:4] == verb[:4] or word[:5] == verb[:5]:
                        verb_found = verb
                        is_dequeismo = True
                        break

            if is_dequeismo:
                break

        if is_dequeismo and verb_found:
            # Encontrar la oración completa
            sentence = _find_sentence(doc, start)

            issues.append(
                GrammarIssue(
                    text="de que",
                    start_char=start,
                    end_char=end,
                    sentence=sentence,
                    error_type=GrammarErrorType.DEQUEISMO,
                    severity=GrammarSeverity.ERROR,
                    suggestion="que",
                    confidence=0.75,  # Reducida porque puede haber falsos positivos
                    detection_method=GrammarDetectionMethod.RULE,
                    explanation=f"Dequeísmo: '{verb_found}' no lleva 'de' antes de 'que'",
                    rule_id="DEQUEISMO_VERB",
                )
            )

    return issues


def check_dequeismo_spacy(doc: Doc) -> list[GrammarIssue]:
    """
    Detectar dequeísmo usando análisis sintáctico de spaCy.

    Más preciso que regex pero más lento.

    IMPORTANTE: Busca hacia atrás en la cadena de dependencias para encontrar
    el verbo REGENTE real. Por ejemplo, en "me di cuenta de que creía que vendría",
    el verbo regente de "de que" es "dar cuenta" (correcto), no "creer".
    """
    issues = []

    # Verbos/expresiones que REQUIEREN "de que" (si gobiernan, no es dequeísmo)
    QUEISMO_LEMMAS = {
        "acordar",
        "alegrar",
        "arrepentir",
        "avergonzar",
        "convencer",
        "enterar",
        "olvidar",
        "quejar",
        "lamentar",
        "jactar",
        "ufanar",
        "preocupar",
        "asegurar",
        "cerciorar",
        "percatar",
        "depender",
        "tratar",  # "se trata de que"
    }

    # Sustantivos/adjetivos que rigen "de que"
    QUEISMO_NOMINALS = {
        "cuenta",
        "seguro",
        "segura",
        "convencido",
        "convencida",
        "persuadido",
        "persuadida",
        "harto",
        "harta",
        "cansado",
        "cansada",
        "certeza",
        "seguridad",
        "impresión",
        "sensación",
        "sospecha",
        "condición",
        "fin",
        "pesar",  # a condición de que, a fin de que, a pesar de que
    }

    for i, token in enumerate(doc):
        # Buscar "de" seguido de "que"
        if token.lower_ == "de" and i + 1 < len(doc) and doc[i + 1].lower_ == "que":
            # Buscar hacia atrás en la cadena de dependencias para encontrar
            # el verbo regente REAL (no el verbo subordinado)
            current = token
            governing_verb = None
            found_queismo_pattern = False
            max_depth = 10  # Límite de profundidad para evitar loops infinitos

            depth = 0
            while depth < max_depth:
                depth += 1
                head = current.head

                # Si llegamos a la raíz, parar
                if head == current:
                    break

                # Verificar si el head es un verbo pronominal que requiere "de que"
                if head.pos_ == "VERB":
                    verb_lemma = head.lemma_.lower()

                    # Caso especial: "darse cuenta de que" - buscar "cuenta" como objeto
                    if verb_lemma == "dar":
                        for child in head.children:
                            if child.lower_ == "cuenta":
                                found_queismo_pattern = True
                                break

                    # Verbos pronominales que requieren "de que"
                    if verb_lemma in QUEISMO_LEMMAS:
                        found_queismo_pattern = True
                        break

                    # Si es un verbo de dequeísmo y aún no encontramos patrón de queísmo
                    if verb_lemma in DEQUEISMO_VERBS and not found_queismo_pattern:
                        governing_verb = head
                        # Seguir buscando por si hay un verbo regente más arriba
                        # que sí requiera "de que"

                # Verificar si hay un sustantivo/adjetivo que rige "de que"
                elif head.pos_ in ("NOUN", "ADJ"):
                    if head.lower_ in QUEISMO_NOMINALS:
                        found_queismo_pattern = True
                        break

                current = head

            # Solo reportar dequeísmo si:
            # 1. Encontramos un verbo de dequeísmo
            # 2. NO hay ningún patrón de queísmo que lo gobierne
            if governing_verb and not found_queismo_pattern:
                sentence = governing_verb.sent.text if governing_verb.sent else ""

                # Incluir el verbo en el texto reportado para mejor contexto
                # Ej: "pensaba de que" en lugar de solo "de que"
                error_text = f"{governing_verb.text} de que"

                issues.append(
                    GrammarIssue(
                        text=error_text,
                        start_char=governing_verb.idx,
                        end_char=doc[i + 1].idx + len(doc[i + 1]),
                        sentence=sentence,
                        error_type=GrammarErrorType.DEQUEISMO,
                        severity=GrammarSeverity.ERROR,
                        suggestion=f"{governing_verb.text} que",
                        confidence=0.9,
                        detection_method=GrammarDetectionMethod.SPACY_DEP,
                        explanation=f"Dequeísmo: '{governing_verb.text}' no lleva 'de' antes de 'que'",
                        rule_id="DEQUEISMO_SPACY",
                    )
                )

    return issues


# =============================================================================
# Reglas de Queísmo
# =============================================================================


def check_queismo(doc: Doc) -> list[GrammarIssue]:
    """
    Detectar queísmo: omisión incorrecta de "de" antes de "que".

    Ejemplos de queísmo:
    - "Me alegro que vengas" → "Me alegro de que vengas"
    - "Me acuerdo que llovía" → "Me acuerdo de que llovía"
    - "Estoy seguro que viene" → "Estoy seguro de que viene"
    """
    issues = []
    text_lower = doc.text.lower()

    # Patrones de queísmo con verbos pronominales
    queismo_patterns = [
        # Verbos pronominales + que (sin "de")
        (
            r"\b(me|te|se|nos|os)\s+(alegr[oaáé]\w*|arrepient[oaáé]\w*|acuerd[oaáé]\w*|"
            r"olvid[oaáé]\w*|quej[oaáé]\w*|enter[oaáé]\w*|convenc[íi]\w*|"
            r"percataron?|cercioraron?)\s+que\b",
            "verbo pronominal",
        ),
        # "estar seguro/convencido que" (sin "de")
        (
            r"\best[áaoy]\w*\s+(segur[oa]|convencid[oa]|persuadid[oa]|hart[oa]|cansad[oa])\s+que\b",
            "estar + adjetivo",
        ),
        # "darse cuenta que" (sin "de")
        (r"\b(me|te|se|nos|os)\s+d[ioaá]\w*\s+cuenta\s+que\b", "darse cuenta"),
        # "tener la certeza/seguridad que" (sin "de")
        (
            r"\bteng[oa]\w*\s+(la\s+)?(certeza|seguridad|impresión|sensación|sospecha)\s+que\b",
            "tener + sustantivo",
        ),
        # "a pesar que" (sin "de")
        (r"\ba\s+pesar\s+que\b", "a pesar de que"),
        # "a fin que" (sin "de")
        (r"\ba\s+fin\s+que\b", "a fin de que"),
        # "a condición que" (sin "de")
        (r"\ba\s+condición\s+que\b", "a condición de que"),
        # "antes que" en sentido temporal (sin "de")
        (
            r"\bantes\s+que\s+(él|ella|yo|tú|nosotros|ellos|llegara|viniera|saliera)\b",
            "antes de que",
        ),
        # "después que" (sin "de")
        (r"\bdespués\s+que\b", "después de que"),
    ]

    for pattern, pattern_type in queismo_patterns:
        for match in re.finditer(pattern, text_lower):
            start, end = match.span()
            matched_text = match.group()

            # Encontrar dónde insertar "de"
            que_pos = matched_text.rfind("que")
            suggestion = matched_text[:que_pos] + "de " + matched_text[que_pos:]

            sentence = _find_sentence(doc, start)

            issues.append(
                GrammarIssue(
                    text=doc.text[start:end],
                    start_char=start,
                    end_char=end,
                    sentence=sentence,
                    error_type=GrammarErrorType.QUEISMO,
                    severity=GrammarSeverity.ERROR,
                    suggestion=suggestion,
                    confidence=0.85,
                    detection_method=GrammarDetectionMethod.RULE,
                    explanation=f"Queísmo ({pattern_type}): falta 'de' antes de 'que'",
                    rule_id="QUEISMO_PATTERN",
                )
            )

    return issues


# =============================================================================
# Reglas de Leísmo/Laísmo/Loísmo
# =============================================================================


def check_laismo(doc: Doc) -> list[GrammarIssue]:
    """
    Detectar laísmo: uso de "la/las" como complemento indirecto.

    Ejemplos de laísmo:
    - "La dije que viniera" → "Le dije que viniera"
    - "La di un regalo" → "Le di un regalo"
    """
    issues = []

    # Verbos que típicamente llevan CI (complemento indirecto)
    ci_verbs = {
        "decir",
        "dar",
        "contar",
        "preguntar",
        "explicar",
        "enseñar",
        "mostrar",
        "regalar",
        "enviar",
        "escribir",
        "pedir",
        "rogar",
        "suplicar",
        "ordenar",
        "mandar",
        "permitir",
        "prohibir",
        "aconsejar",
        "recomendar",
        "sugerir",
        "ofrecer",
        "prometer",
        "comunicar",
        "informar",
        "advertir",
        "avisar",
        "notificar",
        "preparar",  # preparar algo A alguien = Le preparé una sorpresa
    }

    for i, token in enumerate(doc):
        # Buscar "la" o "las" seguido de verbo CI
        if token.lower_ in ("la", "las") and token.pos_ == "PRON":
            # Verificar si el siguiente token es un verbo de CI
            if i + 1 < len(doc):
                next_token = doc[i + 1]

                # Verificar si es un verbo de CI
                if next_token.pos_ == "VERB":
                    verb_lemma = next_token.lemma_.lower()

                    if verb_lemma in ci_verbs:
                        suggestion = "le" if token.lower_ == "la" else "les"
                        sentence = token.sent.text if token.sent else ""

                        issues.append(
                            GrammarIssue(
                                text=f"{token.text} {next_token.text}",
                                start_char=token.idx,
                                end_char=next_token.idx + len(next_token),
                                sentence=sentence,
                                error_type=GrammarErrorType.LAISMO,
                                severity=GrammarSeverity.WARNING,
                                suggestion=f"{suggestion} {next_token.text}",
                                confidence=0.75,
                                detection_method=GrammarDetectionMethod.SPACY_DEP,
                                explanation=f"Posible laísmo: usar '{suggestion}' como complemento indirecto",
                                rule_id="LAISMO",
                            )
                        )

    # También buscar con regex para casos que spaCy no detecte
    # Patrones con tilde (alta confianza: 0.85)
    laismo_patterns_high_conf = [
        (r"\b(la|las)\s+(dije|dijo|dijeron|diré|dirá|dirán|decía|decían)\b", "decir"),
        (r"\b(la|las)\s+(di|dio|dieron|daré|dará|darán|daba|daban)\b", "dar"),
        (r"\b(la|las)\s+(conté|contó|contaron|contaré|contará)\b", "contar"),
        (r"\b(la|las)\s+(pregunté|preguntó|preguntaron)\b", "preguntar"),
        (r"\b(la|las)\s+(expliqué|explicó|explicaron)\b", "explicar"),
        (r"\b(la|las)\s+(pedí|pidió|pidieron)\b", "pedir"),
        (r"\b(la|las)\s+(regalé|regaló|regalaron)\b", "regalar"),
        (r"\b(la|las)\s+(preparé|preparó|prepararon|preparaba|preparaban)\b", "preparar"),
        # Tiempos compuestos con tilde
        (
            r"\b(la|las)\s+(había|habían|habré|habrá|habría|habrían)\s+"
            r"(dicho|dado|contado|preguntado|explicado|pedido|regalado|preparado|enviado|escrito|"
            r"ofrecido|prometido|comunicado|informado|advertido|mostrado|enseñado)\b",
            "tiempo compuesto CI",
        ),
    ]

    # Patrones sin tilde (menor confianza: 0.65 - podría ser texto sin acentos)
    laismo_patterns_low_conf = [
        (r"\b(la|las)\s+(dire|dira|diran|decia|decian)\b", "decir"),
        (r"\b(la|las)\s+(dare|dara|daran)\b", "dar"),
        (r"\b(la|las)\s+(conte|conto|contare|contara)\b", "contar"),
        (r"\b(la|las)\s+(pregunte|pregunto)\b", "preguntar"),
        (r"\b(la|las)\s+(explique|explico)\b", "explicar"),
        (r"\b(la|las)\s+(pedi|pidio)\b", "pedir"),
        (r"\b(la|las)\s+(regale|regalo)\b", "regalar"),
        (r"\b(la|las)\s+(prepare|preparo)\b", "preparar"),
        # Tiempos compuestos sin tilde
        (
            r"\b(la|las)\s+(habia|habian|habre|habra|habria|habrian)\s+"
            r"(dicho|dado|contado|preguntado|explicado|pedido|regalado|preparado|enviado|escrito|"
            r"ofrecido|prometido|comunicado|informado|advertido|mostrado|enseñado)\b",
            "tiempo compuesto CI",
        ),
    ]

    text_lower = doc.text.lower()

    # Procesar ambos grupos de patrones
    all_patterns = [
        (laismo_patterns_high_conf, 0.85, "LAISMO_REGEX"),
        (laismo_patterns_low_conf, 0.65, "LAISMO_REGEX_NOTILDE"),
    ]

    for patterns, confidence, rule_id in all_patterns:
        for pattern, verb in patterns:
            for match in re.finditer(pattern, text_lower):
                start, end = match.span()

                # Evitar duplicados con la detección spaCy o patrones anteriores
                already_found = any(
                    issue.start_char == start and "LAISMO" in issue.rule_id for issue in issues
                )
                if already_found:
                    continue

                matched_text = match.group()
                pronoun = "la" if "la " in matched_text[:4] else "las"
                suggestion = matched_text.replace(pronoun, "le" if pronoun == "la" else "les", 1)

                sentence = _find_sentence(doc, start)

                explanation = f"Laísmo: el verbo '{verb}' requiere complemento indirecto (le/les)"
                if rule_id == "LAISMO_REGEX_NOTILDE":
                    explanation += " (texto sin acentos, verificar contexto)"

                issues.append(
                    GrammarIssue(
                        text=doc.text[start:end],
                        start_char=start,
                        end_char=end,
                        sentence=sentence,
                        error_type=GrammarErrorType.LAISMO,
                        severity=GrammarSeverity.WARNING,
                        suggestion=suggestion,
                        confidence=confidence,
                        detection_method=GrammarDetectionMethod.RULE,
                        explanation=explanation,
                        rule_id=rule_id,
                    )
                )

    return issues


def check_loismo(doc: Doc) -> list[GrammarIssue]:
    """
    Detectar loísmo: uso de "lo/los" como complemento indirecto.

    Ejemplos de loísmo:
    - "Lo dije que viniera" → "Le dije que viniera"

    Nota: El loísmo es menos común que el laísmo.
    """
    issues = []

    # Patrones de loísmo (menos común, ser más cauto)
    loismo_patterns = [
        (r"\b(lo|los)\s+(dije|dijo|dijeron)\s+a\s+(él|ellos)\b", "decir"),
        (r"\b(lo|los)\s+(di|dio|dieron)\s+a\s+(él|ellos)\b", "dar"),
    ]

    text_lower = doc.text.lower()
    for pattern, _verb in loismo_patterns:
        for match in re.finditer(pattern, text_lower):
            start, end = match.span()
            matched_text = match.group()

            pronoun = "lo" if matched_text.startswith("lo ") else "los"
            suggestion = matched_text.replace(pronoun, "le" if pronoun == "lo" else "les", 1)

            sentence = _find_sentence(doc, start)

            issues.append(
                GrammarIssue(
                    text=doc.text[start:end],
                    start_char=start,
                    end_char=end,
                    sentence=sentence,
                    error_type=GrammarErrorType.LOISMO,
                    severity=GrammarSeverity.WARNING,
                    suggestion=suggestion,
                    confidence=0.7,
                    detection_method=GrammarDetectionMethod.RULE,
                    explanation="Posible loísmo: usar 'le/les' como complemento indirecto",
                    rule_id="LOISMO",
                )
            )

    return issues


# =============================================================================
# Reglas de Concordancia
# =============================================================================


def check_gender_agreement(doc: Doc) -> list[GrammarIssue]:
    """
    Detectar errores de concordancia de género entre determinante y sustantivo.

    Usa la información morfológica de spaCy para detectar discordancias.
    Si spaCy no proporciona género (ej: cuando marca palabra como PROPN por error),
    usa listas de palabras comunes como fallback.
    Ejemplos:
    - "el casa" → "la casa"
    - "la libro" → "el libro"
    - "la amor" → "el amor"
    """
    issues = []

    # Sustantivos femeninos que llevan "el" por empezar con "a/ha" tónica (singular)
    # Regla RAE: En singular usan "el"/"un", en plural usan "las"/"unas"
    # Ej: "el ama" (✓), "la ama" (✗), "las amas" (✓)
    #
    # Lista ampliada (S15) basada en investigación de fuentes oficiales:
    # - RAE: https://www.rae.es/buen-uso-español/el-artículo-ante-nombres-femeninos-comenzados-por-a-tónica
    # - Hispanoteca, Kwiziq, Berges Institute
    # - Ver: docs/research/S15_feminine_a_tonica_detection.md
    # FIXME: Estas listas se usarán en futura implementación de detector de artículos (S15+)
    # FEMININE_WITH_EL = {
    #     # Grupo 1: Palabras comunes (uso frecuente)
    #     "agua", "águila", "alma", "arma", "hambre", "área", "aula", "hacha", "hada",
    #     "ama", "ala", "alba", "alga", "anca", "ancla", "ansia", "arca", "arpa",
    #     "asa", "aspa", "asta", "aura", "ave", "aya", "habla", "haba",
    #
    #     # Grupo 2: Palabras adicionales (investigación S15)
    #     "acta", "afta", "agria", "alca", "ánfora", "ánima", "ánade", "aria",
    #     "ascua", "asma", "áurea",
    #
    #     # Grupo 3: Palabras técnicas/cultas (uso menos frecuente)
    #     "álgebra", "áncora", "ápoda", "árula", "átala", "ábside",
    #
    #     # Nota: "hache" (letra H) es EXCEPCIÓN, usa "la hache" (ver FEMININE_WITH_LA_EXCEPTIONS)
    # }
    #
    # # EXCEPCIONES: Sustantivos femeninos con 'a' tónica que usan "la" (NO "el")
    # # Según RAE: https://www.rae.es/dpd/el
    # FEMININE_WITH_LA_EXCEPTIONS = {
    #     # 1. Nombres de letras del abecedario
    #     "a",      # "la a" (letra)
    #     "hache",  # "la hache" (letra H)
    #     "alfa",   # "la alfa" (letra griega)
    #
    #     # 2. Sustantivos de género común (cuando designan mujeres)
    #     # "la árabe", "la ácrata" (pero "el árabe" para hombres)
    #     # Nota: Estos se manejan mediante contexto (difícil de detectar sin análisis semántico)
    #
    #     # 3. Topónimos (uso fluctuante, no forzar)
    #     # "la/el Argelia", "la/el Ática"
    # }

    # Fallback: palabras muy comunes con género conocido
    # (Usado cuando spaCy no proporciona morfología, ej: detecta como PROPN)
    COMMON_FEMININE = {
        "casa",
        "mesa",
        "silla",
        "ventana",
        "puerta",
        "cama",
        "cocina",
        "sala",
        "habitación",
        "ciudad",
        "persona",
        "vida",
        "muerte",
        "historia",
        "idea",
        "palabra",
        "calle",
        "familia",
        "mujer",
        "madre",
        "hija",
        "hermana",
    }
    COMMON_MASCULINE = {
        "libro",
        "coche",
        "perro",
        "gato",
        "día",
        "tiempo",
        "momento",
        "año",
        "hombre",
        "padre",
        "hijo",
        "hermano",
        "amor",
        "trabajo",
        "dinero",
        "mundo",
        "país",
        "lugar",
        "nombre",
        "color",
        "problema",
        "sistema",
    }

    for i, token in enumerate(doc):
        # Buscar determinantes (el, la, un, una)
        if token.pos_ == "DET" and token.lower_ in ("el", "la", "un", "una"):
            det = token
            det_lower = det.lower_

            # Obtener género del determinante
            det_gender = getattr(det, "morph", {}).get("Gender")
            det_gender = det_gender[0] if det_gender else None
            if not det_gender:
                # Inferir del texto
                det_gender = "Masc" if det_lower in ("el", "un") else "Fem"

            # Buscar el sustantivo que sigue (verificando si hay adjetivos interpuestos)
            j = i + 1
            has_interposed_adjective = False
            while j < len(doc) and doc[j].pos_ == "ADJ":
                has_interposed_adjective = True
                j += 1

            # Aceptar NOUN o PROPN (spaCy a veces marca sustantivos como PROPN en contexto erróneo)
            if j < len(doc) and doc[j].pos_ in ("NOUN", "PROPN"):
                noun = doc[j]
                noun_lower = noun.lower_

                # Caso especial: sustantivos femeninos con "a/ha" tónica
                # Regla RAE: En SINGULAR llevan "el"/"un" (por eufonía)
                # IMPORTANTE: Solo si NO hay adjetivo interpuesto
                # ✓ "el ama" (sin adjetivo)
                # ✓ "la antigua ama" (con adjetivo → usa artículo femenino)
                # ✗ "la ama" (sin adjetivo → debe ser "el ama")
                # En PLURAL llevan "las"/"unas" (normal)

                # S15: Usar detector híbrido (lista + automático)
                # Determinar si es plural
                noun_is_plural_morph = getattr(noun, "morph", {}).get("Number")
                noun_is_plural = noun_is_plural_morph and noun_is_plural_morph[0] == "Plur"

                # Heurística si spaCy no da número
                if not noun_is_plural:
                    noun_is_plural = noun_lower.endswith("s")

                # Usar detector híbrido para verificar si requiere "el"
                # PERO SOLO si no hay adjetivo interpuesto
                needs_masculine = (
                    not has_interposed_adjective
                    and requires_masculine_article(
                        word=noun_lower,
                        is_feminine=True,  # Asumimos que es femenino si llegamos aquí
                        is_plural=noun_is_plural,
                        use_static_list=True,  # Siempre usar lista estática (fast path)
                        use_automatic_detection=STRESS_DETECTOR_AVAILABLE,  # Auto solo si disponible
                    )
                )

                if needs_masculine:
                    # SINGULAR: debe usar "el"/"un", NO "la"/"una"
                    if not noun_is_plural and det_lower in ("la", "una"):
                        issues.append(
                            GrammarIssue(
                                text=f"{det.text} {noun.text}",
                                start_char=det.idx,
                                end_char=noun.idx + len(noun),
                                sentence=det.sent.text if det.sent else "",
                                error_type=GrammarErrorType.GENDER_AGREEMENT,
                                severity=GrammarSeverity.ERROR,
                                suggestion=f"{'el' if det_lower == 'la' else 'un'} {noun_lower}",
                                confidence=0.95,
                                detection_method=GrammarDetectionMethod.SPACY_DEP,
                                explanation=f"'{noun_lower}' (singular) lleva '{'el' if det_lower == 'la' else 'un'}' por empezar con 'a' tónica",
                                rule_id="GENDER_AGREEMENT_A_TONICA_SINGULAR",
                            )
                        )
                    # PLURAL: debe usar "las"/"unas", NO "los"/"unos"
                    elif noun_is_plural and det_lower in ("los", "unos"):
                        issues.append(
                            GrammarIssue(
                                text=f"{det.text} {noun.text}",
                                start_char=det.idx,
                                end_char=noun.idx + len(noun),
                                sentence=det.sent.text if det.sent else "",
                                error_type=GrammarErrorType.GENDER_AGREEMENT,
                                severity=GrammarSeverity.ERROR,
                                suggestion=f"{'las' if det_lower == 'los' else 'unas'} {noun_lower}",
                                confidence=0.95,
                                detection_method=GrammarDetectionMethod.SPACY_DEP,
                                explanation=f"'{noun_lower}' (plural) es femenino, debe usar '{'las' if det_lower == 'los' else 'unas'}'",
                                rule_id="GENDER_AGREEMENT_A_TONICA_PLURAL",
                            )
                        )
                    continue  # No verificar más para estos

                # Obtener género del sustantivo de spaCy
                noun_gender = getattr(noun, "morph", {}).get("Gender")
                noun_gender = noun_gender[0] if noun_gender else None

                # Fallback: usar listas de palabras comunes si spaCy no tiene info
                if not noun_gender:
                    if noun_lower in COMMON_FEMININE:
                        noun_gender = "Fem"
                    elif noun_lower in COMMON_MASCULINE:
                        noun_gender = "Masc"
                    else:
                        continue  # Sin información de género, no podemos verificar

                # Verificar concordancia de género
                if det_gender != noun_gender:
                    # Sugerir corrección
                    if noun_gender == "Fem":
                        correct_det = "la" if det_lower in ("el", "la") else "una"
                    else:  # Masc
                        correct_det = "el" if det_lower in ("el", "la") else "un"

                    noun_gender_es = "femenino" if noun_gender == "Fem" else "masculino"

                    issues.append(
                        GrammarIssue(
                            text=f"{det.text} {noun.text}",
                            start_char=det.idx,
                            end_char=noun.idx + len(noun),
                            sentence=det.sent.text if det.sent else "",
                            error_type=GrammarErrorType.GENDER_AGREEMENT,
                            severity=GrammarSeverity.ERROR,
                            suggestion=f"{correct_det} {noun_lower}",
                            confidence=0.95,
                            detection_method=GrammarDetectionMethod.SPACY_DEP,
                            explanation=f"'{noun_lower}' es {noun_gender_es}, usar '{correct_det}'",
                            rule_id="GENDER_AGREEMENT",
                        )
                    )

    return issues


def check_number_agreement(doc: Doc) -> list[GrammarIssue]:
    """
    Detectar errores de concordancia de número.

    Ejemplos:
    - "los casa" → "las casas" o "la casa"
    - "el libros" → "los libros" o "el libro"
    """
    issues = []

    # Determinantes plurales conocidos (incluye posesivos plurales)
    PLURAL_DETERMINERS = {
        "los",
        "las",
        "unos",
        "unas",  # Artículos
        "mis",
        "tus",
        "sus",  # Posesivos plurales
        "nuestros",
        "nuestras",  # Posesivos 1a persona plural
        "vuestros",
        "vuestras",  # Posesivos 2a persona plural
        "estos",
        "estas",
        "esos",
        "esas",  # Demostrativos plurales
        "aquellos",
        "aquellas",
        "algunos",
        "algunas",
        "varios",
        "varias",  # Indefinidos plurales
        "muchos",
        "muchas",
        "pocos",
        "pocas",
        "todos",
        "todas",
    }

    for i, token in enumerate(doc):
        if token.pos_ == "DET":
            det_lower = token.lower_
            det_number = "plural" if det_lower in PLURAL_DETERMINERS else "singular"

            # Buscar el sustantivo
            if i + 1 < len(doc):
                j = i + 1
                # Saltar adjetivos
                while j < len(doc) and doc[j].pos_ == "ADJ":
                    j += 1

                if j < len(doc) and doc[j].pos_ == "NOUN":
                    noun = doc[j]

                    # Determinar número del sustantivo
                    noun_number = "plural" if noun.lower_.endswith("s") else "singular"

                    # Excepciones: palabras que terminan en "s" pero son singular
                    singular_ending_s = {
                        "lunes",
                        "martes",
                        "miércoles",
                        "jueves",
                        "viernes",
                        "crisis",
                        "análisis",
                        "tesis",
                        "dosis",
                        "virus",
                    }
                    if noun.lower_ in singular_ending_s:
                        noun_number = "singular"

                    # Verificar concordancia
                    if det_number != noun_number:
                        sentence = token.sent.text if token.sent else ""

                        issues.append(
                            GrammarIssue(
                                text=f"{token.text} {noun.text}",
                                start_char=token.idx,
                                end_char=noun.idx + len(noun),
                                sentence=sentence,
                                error_type=GrammarErrorType.NUMBER_AGREEMENT,
                                severity=GrammarSeverity.WARNING,
                                suggestion=None,  # Difícil sugerir sin contexto
                                confidence=0.7,
                                detection_method=GrammarDetectionMethod.SPACY_DEP,
                                explanation=f"Posible error de concordancia de número entre '{token.text}' y '{noun.text}'",
                                rule_id="NUMBER_AGREEMENT",
                            )
                        )

    # Fallback: detección por regex para casos que spaCy no detecta
    # "Los/Las" (plural) + sustantivo singular común
    COMMON_SINGULAR_NOUNS = {
        "casa",
        "mesa",
        "silla",
        "puerta",
        "ventana",
        "cama",
        "calle",
        "ciudad",
        "libro",
        "coche",
        "perro",
        "gato",
        "árbol",
        "día",
        "niño",
        "niña",
        "hombre",
        "mujer",
        "persona",
        "cosa",
        "lugar",
        "tiempo",
        "año",
        "mes",
        "palabra",
        "idea",
        "historia",
        "vida",
        "mundo",
        "país",
        "nombre",
    }

    text_lower = doc.text.lower()

    # Detectar determinante plural + sustantivo singular
    for noun in COMMON_SINGULAR_NOUNS:
        for det in ["los", "las", "unos", "unas"]:
            pattern = rf"\b{det}\s+{re.escape(noun)}\b"
            for match in re.finditer(pattern, text_lower):
                start, end = match.span()
                # Verificar que no esté ya detectado
                already_found = any(
                    i.start_char == start and i.error_type == GrammarErrorType.NUMBER_AGREEMENT
                    for i in issues
                )
                if not already_found:
                    issues.append(
                        GrammarIssue(
                            text=doc.text[start:end],
                            start_char=start,
                            end_char=end,
                            sentence=_find_sentence(doc, start),
                            error_type=GrammarErrorType.NUMBER_AGREEMENT,
                            severity=GrammarSeverity.WARNING,
                            suggestion=None,
                            confidence=0.85,
                            detection_method=GrammarDetectionMethod.RULE,
                            explanation=f"Error de concordancia: '{det}' (plural) con '{noun}' (singular)",
                            rule_id="NUMBER_AGREEMENT_REGEX",
                        )
                    )

    return issues


def check_adjective_agreement(doc: Doc) -> list[GrammarIssue]:
    """
    Detectar errores de concordancia sustantivo-adjetivo.

    Usa la información morfológica de spaCy y las dependencias sintácticas
    para detectar discordancias solo cuando el adjetivo modifica al sustantivo.

    Ejemplos:
    - "casa antiguo" → "casa antigua" (género)
    - "vaso llenos" → "vaso lleno" / "vasos llenos" (número)

    NOTA: Se usa el análisis de dependencias de spaCy (dep_) para evitar
    falsos positivos como "barba espesa y ojos marrones" donde "espesa"
    modifica a "barba", no a "ojos".
    """
    issues = []

    for i, token in enumerate(doc):
        if token.pos_ == "NOUN":
            noun = token

            # Obtener género y número del sustantivo de spaCy
            noun_gender = getattr(noun, "morph", {}).get("Gender")
            noun_number = getattr(noun, "morph", {}).get("Number")

            if not noun_gender and not noun_number:
                continue  # Sin información morfológica, saltar

            noun_gender = noun_gender[0] if noun_gender else None
            noun_number = noun_number[0] if noun_number else None

            # Buscar adjetivos que REALMENTE modifiquen este sustantivo
            # usando dependencias sintácticas de spaCy
            modifying_adjs = []

            # Buscar adjetivos que son hijos directos del sustantivo con dep='amod'
            # NOTA: Solo usamos amod (adjectival modifier) para evitar falsos positivos
            # donde el sustantivo está relacionado con un adjetivo pero no modificado por él
            for child in noun.children:
                if child.pos_ == "ADJ" and child.dep_ == "amod":
                    modifying_adjs.append(child)

            # Si no encontramos modificadores por dependencias, usar proximidad
            # pero con restricciones más estrictas
            if not modifying_adjs:
                # Solo buscar adjetivo inmediatamente antes o después
                for j in [i - 1, i + 1]:
                    if 0 <= j < len(doc):
                        adj_token = doc[j]
                        # Verificar que no haya conjunción separando
                        if adj_token.pos_ == "ADJ":
                            # Evitar falso positivo si hay conjunción entre medio
                            has_conj_between = False
                            start_idx = min(i, j)
                            end_idx = max(i, j)
                            for k in range(start_idx, end_idx + 1):
                                if doc[k].pos_ == "CCONJ" or doc[k].text in (
                                    ",",
                                    "y",
                                    "e",
                                    "o",
                                    "u",
                                ):
                                    has_conj_between = True
                                    break
                            if not has_conj_between:
                                modifying_adjs.append(adj_token)

            for adj in modifying_adjs:
                if adj.pos_ != "ADJ":
                    continue

                # IMPORTANTE: Excluir participios que son parte de tiempos compuestos
                # "haber conocido la derrota" → "conocido" no debe concordar con "derrota"
                # Detectar si el adjetivo es realmente un participio (termina en -ado/-ido)
                adj_text_lower = adj.text.lower()
                is_participle = adj_text_lower.endswith(("ado", "ido", "eso", "cho", "to"))

                if is_participle:
                    # Verificar si hay un auxiliar "haber" antes
                    has_haber_before = False
                    for prev_idx in range(max(0, adj.i - 5), adj.i):
                        prev_token = doc[prev_idx]
                        if prev_token.lemma_.lower() == "haber" or prev_token.lower_ in (
                            "he",
                            "has",
                            "ha",
                            "hemos",
                            "habéis",
                            "han",
                            "había",
                            "habías",
                            "habíamos",
                            "habían",
                            "hube",
                            "hubiste",
                            "hubo",
                            "hubimos",
                            "hubieron",
                            "habré",
                            "habrás",
                            "habrá",
                            "habremos",
                            "habrán",
                            "habría",
                            "habrías",
                            "habríamos",
                            "habrían",
                            "haya",
                            "hayas",
                            "hayamos",
                            "hayan",
                            "hubiera",
                            "hubieras",
                            "hubiera",
                            "hubiéramos",
                            "hubieran",
                            "hubiese",
                            "hubieses",
                            "hubiese",
                            "hubiésemos",
                            "hubiesen",
                        ):
                            has_haber_before = True
                            break

                    if has_haber_before:
                        continue  # Es tiempo compuesto, no verificar concordancia

                # Obtener género y número del adjetivo de spaCy
                adj_gender_list = getattr(adj, "morph", {}).get("Gender")
                adj_number_list = getattr(adj, "morph", {}).get("Number")

                adj_gender: str | None = adj_gender_list[0] if adj_gender_list else None
                adj_number: str | None = adj_number_list[0] if adj_number_list else None

                # Corregir errores de spaCy en número de adjetivos
                # Si termina en -es/-os/-as es muy probable que sea plural
                adj_lower = adj.lower_
                if adj_lower.endswith(("es", "os", "as")) and adj_number == "Sing":
                    adj_number = "Plur"  # Corregir a plural
                elif not adj_lower.endswith(("s", "es")) and adj_number == "Plur":
                    adj_number = "Sing"  # Corregir a singular

                # Verificar concordancia de género
                if noun_gender and adj_gender and noun_gender != adj_gender:
                    adj_lower = adj.lower_
                    # Sugerir corrección
                    if noun_gender == "Fem" and adj_lower.endswith("o"):
                        suggestion = adj_lower[:-1] + "a"
                    elif noun_gender == "Masc" and adj_lower.endswith("a"):
                        suggestion = adj_lower[:-1] + "o"
                    else:
                        suggestion = None

                    sentence = token.sent.text if token.sent else ""
                    issues.append(
                        GrammarIssue(
                            text=f"{noun.text} {adj.text}",
                            start_char=min(noun.idx, adj.idx),
                            end_char=max(noun.idx + len(noun), adj.idx + len(adj)),
                            sentence=sentence,
                            error_type=GrammarErrorType.ADJECTIVE_AGREEMENT,
                            severity=GrammarSeverity.ERROR,
                            suggestion=f"{noun.text} {suggestion}" if suggestion else None,
                            confidence=0.9,  # Alta confianza con morfología de spaCy
                            detection_method=GrammarDetectionMethod.SPACY_DEP,
                            explanation=f"Error de concordancia de género: '{getattr(noun, 'text', '')}' es {str(noun_gender).lower()} pero '{getattr(adj, 'text', '')}' es {str(adj_gender).lower()}",
                            rule_id="ADJECTIVE_GENDER_AGREEMENT",
                        )
                    )

                # Verificar concordancia de número
                elif noun_number and adj_number and noun_number != adj_number:
                    sentence = token.sent.text if token.sent else ""
                    noun_num_es = "singular" if noun_number == "Sing" else "plural"
                    adj_num_es = "singular" if adj_number == "Sing" else "plural"
                    issues.append(
                        GrammarIssue(
                            text=f"{noun.text} {adj.text}",
                            start_char=min(noun.idx, adj.idx),
                            end_char=max(noun.idx + len(noun), adj.idx + len(adj)),
                            sentence=sentence,
                            error_type=GrammarErrorType.ADJECTIVE_AGREEMENT,
                            severity=GrammarSeverity.WARNING,
                            suggestion=None,
                            confidence=0.85,
                            detection_method=GrammarDetectionMethod.SPACY_DEP,
                            explanation=f"Error de concordancia de número: '{noun.text}' es {noun_num_es} pero '{adj.text}' es {adj_num_es}",
                            rule_id="ADJECTIVE_NUMBER_AGREEMENT",
                        )
                    )

    return issues


# =============================================================================
# Reglas de Redundancia
# =============================================================================


def check_redundancy(doc: Doc) -> list[GrammarIssue]:
    """
    Detectar expresiones redundantes.

    Usa lematización de spaCy para detectar cualquier conjugación del verbo.
    Ejemplos:
    - "subir/subió/subía arriba" → "subir"
    - "bajar/bajó/bajaban abajo" → "bajar"
    - "volver a repetir" → "repetir"
    """
    issues = []

    # 1. Detección por lemas (verbo + adverbio redundante)
    # Esto detecta cualquier conjugación del verbo gracias a spaCy
    for i, token in enumerate(doc):
        if token.pos_ == "VERB":
            verb_lemma = token.lemma_.lower()

            # Buscar adverbio siguiente (puede haber palabras entre medio)
            for j in range(i + 1, min(i + 4, len(doc))):  # Máximo 3 tokens después
                next_token = doc[j]
                if next_token.pos_ == "ADV" or next_token.lower_ in (
                    "arriba",
                    "abajo",
                    "afuera",
                    "adentro",
                ):
                    adv_lower = next_token.lower_

                    # Verificar si es redundancia conocida
                    key = (verb_lemma, adv_lower)
                    if key in LEMMA_REDUNDANCIES:
                        LEMMA_REDUNDANCIES[key]
                        sentence = token.sent.text if token.sent else ""

                        issues.append(
                            GrammarIssue(
                                text=f"{token.text} {adv_lower}",
                                start_char=token.idx,
                                end_char=next_token.idx + len(next_token),
                                sentence=sentence,
                                error_type=GrammarErrorType.REDUNDANCY,
                                severity=GrammarSeverity.STYLE,
                                suggestion=token.text,  # Solo el verbo sin el adverbio
                                confidence=0.95,
                                detection_method=GrammarDetectionMethod.SPACY_DEP,
                                explanation=f"Redundancia: '{adv_lower}' es innecesario con '{verb_lemma}'",
                                rule_id="REDUNDANCY_LEMMA",
                            )
                        )
                        break  # Solo reportar una vez por verbo

    # 2. Detección por expresiones fijas (regex)
    # Para expresiones que no son verbo+adverbio
    text_lower = doc.text.lower()

    for redundant, correction in REDUNDANT_EXPRESSIONS.items():
        pattern = r"\b" + re.escape(redundant) + r"\b"

        for match in re.finditer(pattern, text_lower):
            start, end = match.span()
            # Evitar duplicados si ya se detectó por lemas
            already_found = any(
                abs(i.start_char - start) < 5 and i.error_type == GrammarErrorType.REDUNDANCY
                for i in issues
            )
            if not already_found:
                sentence = _find_sentence(doc, start)

                issues.append(
                    GrammarIssue(
                        text=doc.text[start:end],
                        start_char=start,
                        end_char=end,
                        sentence=sentence,
                        error_type=GrammarErrorType.REDUNDANCY,
                        severity=GrammarSeverity.STYLE,
                        suggestion=correction,
                        confidence=0.9,
                        detection_method=GrammarDetectionMethod.RULE,
                        explanation=f"Expresión redundante: '{redundant}' puede simplificarse",
                        rule_id="REDUNDANCY",
                    )
                )

    return issues


# =============================================================================
# Reglas de Puntuación
# =============================================================================


def check_punctuation(doc: Doc) -> list[GrammarIssue]:
    """
    Detectar errores básicos de puntuación.
    """
    issues = []
    text = doc.text

    # Patrones de puntuación incorrecta
    patterns = [
        # Espacio antes de puntuación
        (r"\s+[,;:\.!\?]", "Espacio antes de signo de puntuación", GrammarSeverity.WARNING),
        # Falta espacio después de puntuación (excepto al final)
        (
            r"[,;:][^\s\n\d]",
            "Falta espacio después de signo de puntuación",
            GrammarSeverity.WARNING,
        ),
        # Múltiples signos de puntuación (excepto ... y ?! o !?)
        (r"[,;:]{2,}", "Signos de puntuación duplicados", GrammarSeverity.ERROR),
        # Coma antes de "y" en lista de dos elementos (posible error)
        # (r'\w+,\s+y\s+\w+(?!\s*,)', "Posible coma innecesaria antes de 'y'", GrammarSeverity.INFO),
        # Punto y coma seguido de mayúscula (posible error)
        (r";\s*[A-ZÁÉÍÓÚÑ]", "Después de punto y coma suele ir minúscula", GrammarSeverity.INFO),
    ]

    for pattern, explanation, severity in patterns:
        for match in re.finditer(pattern, text):
            start, end = match.span()

            issues.append(
                GrammarIssue(
                    text=match.group(),
                    start_char=start,
                    end_char=end,
                    sentence=_find_sentence(doc, start),
                    error_type=GrammarErrorType.PUNCTUATION,
                    severity=severity,
                    suggestion=None,
                    confidence=0.7,
                    detection_method=GrammarDetectionMethod.RULE,
                    explanation=explanation,
                    rule_id="PUNCTUATION",
                )
            )

    return issues


# =============================================================================
# Otras reglas comunes
# =============================================================================


def check_habemos(doc: Doc) -> list[GrammarIssue]:
    """
    Detectar uso incorrecto de *habemos.

    - "Habemos muchos" → "Hay muchos" / "Somos muchos"
    """
    issues = []

    for match in re.finditer(r"\bhabemos\b", doc.text.lower()):
        start, end = match.span()

        issues.append(
            GrammarIssue(
                text=doc.text[start:end],
                start_char=start,
                end_char=end,
                sentence=_find_sentence(doc, start),
                error_type=GrammarErrorType.INFINITIVE_ERROR,
                severity=GrammarSeverity.ERROR,
                suggestion="hay / somos",
                alternatives=["hay", "somos"],
                confidence=0.95,
                detection_method=GrammarDetectionMethod.RULE,
                explanation="'Habemos' es incorrecto; usar 'hay' (existencia) o 'somos' (pertenencia)",
                rule_id="HABEMOS",
            )
        )

    return issues


def check_gerund_posterioridad(doc: Doc) -> list[GrammarIssue]:
    """
    Detectar gerundio de posterioridad (uso incorrecto).

    - "Salió corriendo, llegando a las 5" → El gerundio indica acción simultánea, no posterior
    """
    issues = []

    # Patrón: verbo en pasado + coma + gerundio (posible posterioridad)
    pattern = r"\b\w+[óé]\s*,\s*\w+[ae]ndo\b"

    for match in re.finditer(pattern, doc.text.lower()):
        start, end = match.span()

        issues.append(
            GrammarIssue(
                text=doc.text[start:end],
                start_char=start,
                end_char=end,
                sentence=_find_sentence(doc, start),
                error_type=GrammarErrorType.GERUND_ERROR,
                severity=GrammarSeverity.INFO,
                suggestion=None,
                confidence=0.5,
                detection_method=GrammarDetectionMethod.RULE,
                explanation="Posible gerundio de posterioridad: el gerundio expresa acción simultánea, no posterior",
                rule_id="GERUND_POSTERIORIDAD",
            )
        )

    return issues


# =============================================================================
# Función principal que ejecuta todas las reglas
# =============================================================================


@dataclass
class SpanishRulesConfig:
    """Configuración para las reglas de español."""

    check_dequeismo: bool = True
    check_queismo: bool = True
    check_laismo: bool = True
    check_loismo: bool = True
    check_gender: bool = True
    check_number: bool = True
    check_adjective: bool = True  # Concordancia sustantivo-adjetivo
    check_redundancy: bool = True
    check_punctuation: bool = True
    check_other: bool = True

    # Usar análisis spaCy más preciso (más lento)
    use_spacy_analysis: bool = True

    # Umbral mínimo de confianza para reportar
    min_confidence: float = 0.5


def apply_spanish_rules(doc: Doc, config: SpanishRulesConfig | None = None) -> list[GrammarIssue]:
    """
    Aplicar todas las reglas de español al documento.

    Args:
        doc: Documento spaCy procesado
        config: Configuración de qué reglas aplicar

    Returns:
        Lista de errores gramaticales detectados
    """
    if config is None:
        config = SpanishRulesConfig()

    issues: list[GrammarIssue] = []

    # Dequeísmo
    if config.check_dequeismo:
        if config.use_spacy_analysis:
            issues.extend(check_dequeismo_spacy(doc))
        issues.extend(check_dequeismo(doc))

    # Queísmo
    if config.check_queismo:
        issues.extend(check_queismo(doc))

    # Laísmo
    if config.check_laismo:
        issues.extend(check_laismo(doc))

    # Loísmo
    if config.check_loismo:
        issues.extend(check_loismo(doc))

    # Concordancia de género
    if config.check_gender:
        issues.extend(check_gender_agreement(doc))

    # Concordancia de número
    if config.check_number:
        issues.extend(check_number_agreement(doc))

    # Concordancia sustantivo-adjetivo
    if config.check_adjective:
        issues.extend(check_adjective_agreement(doc))

    # Redundancias
    if config.check_redundancy:
        issues.extend(check_redundancy(doc))

    # Puntuación
    if config.check_punctuation:
        issues.extend(check_punctuation(doc))

    # Otras reglas
    if config.check_other:
        issues.extend(check_habemos(doc))
        issues.extend(check_gerund_posterioridad(doc))

    # Filtrar por confianza mínima
    issues = [i for i in issues if i.confidence >= config.min_confidence]

    # Eliminar duplicados por posición
    issues = _deduplicate_issues(issues)

    return issues


# =============================================================================
# Utilidades
# =============================================================================


def _find_sentence(doc: Doc, char_pos: int) -> str:
    """Encontrar la oración que contiene una posición de carácter."""
    for sent in doc.sents:
        if sent.start_char <= char_pos < sent.end_char:
            return str(sent.text)
    return ""


def _deduplicate_issues(issues: list[GrammarIssue]) -> list[GrammarIssue]:
    """Eliminar issues duplicados, manteniendo el de mayor confianza."""
    if not issues:
        return issues

    # Agrupar por posición
    by_position: dict[tuple[int, int], list[GrammarIssue]] = {}
    for issue in issues:
        key = (issue.start_char, issue.end_char)
        if key not in by_position:
            by_position[key] = []
        by_position[key].append(issue)

    # Mantener el de mayor confianza de cada grupo
    result = []
    for group in by_position.values():
        best = max(group, key=lambda x: x.confidence)
        result.append(best)

    # Ordenar por posición
    result.sort(key=lambda x: x.start_char)

    return result
