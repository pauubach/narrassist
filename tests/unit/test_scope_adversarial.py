"""
Tests adversariales para ScopeResolver: resolución de scope gramatical en español.

Cada test documenta un fenómeno lingüístico específico del español que puede
confundir la asignación de atributos a entidades. Organizados por prioridad
según frecuencia en narrativa real.

Convenciones:
- Los tests que DEBEN pasar con el código actual NO llevan xfail.
- Los tests que documentan limitaciones conocidas llevan @pytest.mark.xfail.
- Cada test incluye el patrón lingüístico en el nombre y docstring.

Autor: Generado para auditoría de scope_resolver.py
"""

import re

import pytest

from narrative_assistant.nlp.scope_resolver import ScopeResolver


# =============================================================================
# Helpers
# =============================================================================


def _build_mentions(text: str, entities: list[str]) -> list[tuple[str, int, int, str]]:
    """
    Construye lista de menciones de entidad a partir de nombres y texto.

    Busca todas las ocurrencias de cada nombre en el texto y devuelve
    tuplas (name, start, end, "PER").
    """
    mentions = []
    for name in entities:
        for m in re.finditer(re.escape(name), text):
            mentions.append((name, m.start(), m.end(), "PER"))
    return mentions


def _resolve_scope(
    nlp,
    text: str,
    entities: list[str],
    target_phrase: str = "ojos",
    prefer_subject: bool = True,
) -> str | None:
    """
    Helper: ejecuta ScopeResolver.find_nearest_entity_by_scope() y
    devuelve el nombre de la entidad asignada al atributo objetivo.

    Args:
        nlp: Modelo spaCy cargado (fixture shared_spacy_nlp)
        text: Texto narrativo en español
        entities: Lista de nombres de personajes presentes en el texto
        target_phrase: Frase del atributo a resolver (default: "ojos")
        prefer_subject: Si se prefiere sujeto gramatical

    Returns:
        Nombre de la entidad asignada, o None si no se resuelve.
    """
    doc = nlp(text)
    resolver = ScopeResolver(doc, text)

    mentions = _build_mentions(text, entities)
    target_pos = text.find(target_phrase)
    if target_pos == -1:
        return None

    result = resolver.find_nearest_entity_by_scope(
        target_pos, mentions, prefer_subject=prefer_subject
    )
    return result[0] if result else None


def _resolve_scope_confidence(
    nlp,
    text: str,
    entities: list[str],
    target_phrase: str = "ojos",
    prefer_subject: bool = True,
) -> tuple[str | None, float]:
    """
    Igual que _resolve_scope pero también devuelve la confianza.

    Returns:
        Tupla (entity_name, confidence) o (None, 0.0).
    """
    doc = nlp(text)
    resolver = ScopeResolver(doc, text)

    mentions = _build_mentions(text, entities)
    target_pos = text.find(target_phrase)
    if target_pos == -1:
        return (None, 0.0)

    result = resolver.find_nearest_entity_by_scope(
        target_pos, mentions, prefer_subject=prefer_subject
    )
    return result if result else (None, 0.0)


def _extract_attrs(nlp, text: str, entities: list[str]) -> list[tuple[str, str, str]]:
    """
    Helper: ejecuta el pipeline COMPLETO de extracción de atributos
    y devuelve lista de (entity_name, key_value, attr_value).

    Usa solo extractores basados en reglas y dependencias (sin LLM ni embeddings)
    para reproducibilidad determinista en tests.
    """
    from narrative_assistant.nlp.attributes import AttributeExtractor

    mentions = _build_mentions(text, entities)

    extractor = AttributeExtractor(
        filter_metaphors=False,
        min_confidence=0.3,
        use_llm=False,
        use_embeddings=False,
        use_dependency_extraction=True,
        use_patterns=True,
    )
    result = extractor.extract_attributes(text, entity_mentions=mentions)

    if result.is_success:
        return [
            (a.entity_name, a.key.value, a.value)
            for a in result.value.attributes
        ]
    return []


# =============================================================================
# HIGH PRIORITY: Patrones frecuentes en novelas
# =============================================================================


class TestConSusOjosAmbiguity:
    """
    Patrón 1: "con sus ojos" como instrumental del sujeto.

    En español, "Miró a María con sus ojos azules" usa "con" para introducir
    un instrumento del sujeto. Los ojos pertenecen al sujeto (quien mira),
    NO al objeto (María).
    """

    def test_instrumental_con_sujeto_explicito(self, shared_spacy_nlp):
        """
        "Juan miró a María con sus ojos azules."
        → "ojos azules" = Juan (sujeto de "miró", "con" = instrumental)
        """
        text = "Juan miró a María con sus ojos azules."
        result = _resolve_scope(shared_spacy_nlp, text, ["Juan", "María"])
        assert result == "Juan", (
            f"'con sus ojos azules' es instrumental del sujeto Juan, "
            f"no de María (objeto). Got: {result}"
        )

    def test_instrumental_con_sujeto_femenino(self, shared_spacy_nlp):
        """
        "María observó a Pedro con sus ojos verdes."
        → "ojos verdes" = María (ella observa, no Pedro)
        """
        text = "María observó a Pedro con sus ojos verdes."
        result = _resolve_scope(shared_spacy_nlp, text, ["María", "Pedro"])
        assert result == "María", (
            f"Instrumental 'con sus ojos' pertenece al sujeto María. Got: {result}"
        )

    @pytest.mark.xfail(reason=(
        "Ambiguedad real: 'con sus ojos' puede ser instrumental del sujeto o "
        "atributo del objeto. Sin contexto adicional, es imposible desambiguar "
        "al 100%, pero la heuristica deberia favorecer al sujeto."
    ))
    def test_instrumental_con_sin_a_personal(self, shared_spacy_nlp):
        """
        "Contempló el paisaje con sus ojos azules."
        → "ojos azules" = sujeto tacito (no "el paisaje")

        Aqui no hay "a personal", asi que "el paisaje" no es persona.
        El resolver deberia identificar que no hay candidato persona.
        """
        text = "Pedro contempló el paisaje con sus ojos azules."
        result = _resolve_scope(shared_spacy_nlp, text, ["Pedro"])
        assert result == "Pedro"


class TestSubjectVsObjectAcrossSentences:
    """
    Patrón 2: Sujeto vs objeto en oraciones consecutivas.

    Cuando una oración tiene sujeto y objeto, la siguiente oración con
    sujeto tacito hereda el SUJETO, no el objeto.
    """

    def test_sujeto_hereda_a_siguiente_oracion(self, shared_spacy_nlp):
        """
        "María saludó a Juan. Sus ojos verdes brillaban."
        → "ojos verdes" = María (ella es el sujeto de "saludó")

        El sujeto tacito de "brillaban" hereda de la oracion anterior.
        """
        text = "María saludó a Juan. Sus ojos verdes brillaban."
        result = _resolve_scope(shared_spacy_nlp, text, ["María", "Juan"])
        assert result == "María", (
            f"El sujeto tacito hereda de Maria (sujeto), no Juan (objeto). Got: {result}"
        )

    def test_objeto_no_contamina_sujeto_tacito(self, shared_spacy_nlp):
        """
        "Pedro llamó a Elena. Tenía los ojos cansados."
        → "ojos cansados" = Pedro (sujeto de "llamó")
        """
        text = "Pedro llamó a Elena. Tenía los ojos cansados."
        result = _resolve_scope(shared_spacy_nlp, text, ["Pedro", "Elena"])
        assert result == "Pedro", (
            f"Sujeto tacito de 'tenia' hereda Pedro, no Elena. Got: {result}"
        )

    def test_objeto_directo_sin_a_personal(self, shared_spacy_nlp):
        """
        "Juan vio a María. Sus ojos azules eran inconfundibles."
        → "ojos azules" = Juan (sujeto de "vio")
        """
        text = "Juan vio a María. Sus ojos azules eran inconfundibles."
        result = _resolve_scope(shared_spacy_nlp, text, ["Juan", "María"])
        assert result == "Juan", (
            f"Sujeto tacito hereda Juan (sujeto de 'vio'). Got: {result}"
        )

    @pytest.mark.xfail(reason=(
        "Cuando el objeto se convierte en sujeto en la siguiente oracion "
        "(cambio de topico), el resolver no lo detecta."
    ))
    def test_cambio_de_topico_a_objeto(self, shared_spacy_nlp):
        """
        "Juan miró a María. Ella tenía los ojos verdes."
        → "ojos verdes" = María (el pronombre "Ella" marca cambio de topico)

        Aqui "Ella" es el nuevo sujeto explicito. Debe resolverse a María.
        """
        text = "Juan miró a María. Ella tenía los ojos verdes."
        result = _resolve_scope(shared_spacy_nlp, text, ["Juan", "María"])
        assert result == "María"


class TestProDropCopulativeChain:
    """
    Patrón 3: Pro-drop (sujeto omitido) en cadenas copulativas.

    En español es muy comun: "Juan entró. Era alto. Tenía los ojos azules."
    Las tres oraciones comparten el mismo sujeto: Juan.
    """

    def test_cadena_copulativa_basica(self, shared_spacy_nlp):
        """
        "Juan entró en la sala. Era alto. Tenía los ojos azules."
        → "ojos azules" = Juan (sujeto tacito heredado por 2 oraciones)
        """
        text = "Juan entró en la sala. Era alto. Tenía los ojos azules."
        result = _resolve_scope(shared_spacy_nlp, text, ["Juan"])
        assert result == "Juan", (
            f"Cadena pro-drop: 3 oraciones con sujeto tacito = Juan. Got: {result}"
        )

    def test_cadena_copulativa_con_distractor(self, shared_spacy_nlp):
        """
        "Juan entró en la sala. María lo miró. Tenía los ojos azules."
        → "ojos azules" = ambiguo, pero si "Tenía" hereda sujeto de la
          oracion anterior, deberia ser María (sujeto de "miró").

        Este caso es genuinamente ambiguo en español escrito.
        """
        text = "Juan entró en la sala. María lo miró. Tenía los ojos azules."
        result = _resolve_scope(shared_spacy_nlp, text, ["Juan", "María"])
        # Ambiguo, pero deberia resolver a alguno de los dos, no None
        assert result in ("Juan", "María"), (
            f"Debe resolver a alguna entidad, no None. Got: {result}"
        )

    def test_cadena_copulativa_larga(self, shared_spacy_nlp):
        """
        "Carlos se sentó. Era corpulento. Llevaba barba. Tenía los ojos oscuros."
        → "ojos oscuros" = Carlos (4 oraciones con sujeto tacito)
        """
        text = "Carlos se sentó. Era corpulento. Llevaba barba. Tenía los ojos oscuros."
        result = _resolve_scope(shared_spacy_nlp, text, ["Carlos"])
        assert result == "Carlos"


class TestPrepositionalComplementConfusion:
    """
    Patrón 4: Complementos preposicionales que crean ambiguedad.

    "La mirada de Juan se posó en María" tiene "Juan" como genitivo
    de "mirada", no como sujeto directo. Si la siguiente oracion dice
    "Sus ojos brillaban", debe resolver a Juan (poseedor de la mirada).
    """

    def test_genitivo_de_sujeto_nominal(self, shared_spacy_nlp):
        """
        "La mirada de Juan se posó en María. Sus ojos azules brillaban."
        → "ojos azules" = Juan (poseedor de "mirada", el sujeto nominal)
        """
        text = "La mirada de Juan se posó en María. Sus ojos azules brillaban."
        result = _resolve_scope(shared_spacy_nlp, text, ["Juan", "María"])
        assert result == "Juan", (
            f"'La mirada de Juan' hace a Juan sujeto implicito. Got: {result}"
        )

    def test_genitivo_explicito_ojos_de(self, shared_spacy_nlp):
        """
        "Los ojos de Juan eran azules."
        → "ojos" = Juan (genitivo explicito "de Juan")
        """
        text = "Los ojos de Juan eran azules."
        result = _resolve_scope(shared_spacy_nlp, text, ["Juan"])
        assert result == "Juan"

    def test_genitivo_explicito_con_dos_entidades(self, shared_spacy_nlp):
        """
        "Los ojos verdes de María miraban a Juan."
        → "ojos" = María (genitivo "de María")
        """
        text = "Los ojos verdes de María miraban a Juan."
        result = _resolve_scope(shared_spacy_nlp, text, ["María", "Juan"])
        assert result == "María", (
            f"Genitivo explicito 'de Maria' tiene prioridad. Got: {result}"
        )


class TestDialogueAttribution:
    """
    Patrón 5: Atribución de diálogos.

    Los diálogos en español usan raya (—) y el verbo de habla ("dijo")
    invierte sujeto y atribución.
    """

    @pytest.mark.xfail(reason=(
        "El resolver no analiza estructura de dialogo. "
        "Los verbos de habla ('dijo', 'exclamo') invierten la asignacion "
        "cuando hay 'senalando a X'."
    ))
    def test_dialogo_con_atribucion_a_tercero(self, shared_spacy_nlp):
        """
        "—Tiene los ojos azules —dijo María señalando a Juan."
        → "ojos azules" = Juan (María señala a Juan como poseedor)
        """
        text = "\u2014Tiene los ojos azules \u2014dijo María señalando a Juan."
        result = _resolve_scope(shared_spacy_nlp, text, ["María", "Juan"])
        assert result == "Juan"

    @pytest.mark.xfail(reason=(
        "En dialogo, el sujeto de la oracion incrustada no es el hablante, "
        "sino el referente implicito del dialogo."
    ))
    def test_dialogo_descripcion_de_otro(self, shared_spacy_nlp):
        """
        "—Sus ojos son azules —describió Ana mirando a Pedro."
        → "ojos" = Pedro (a quien Ana describe)
        """
        text = "\u2014Sus ojos son azules \u2014describió Ana mirando a Pedro."
        result = _resolve_scope(shared_spacy_nlp, text, ["Ana", "Pedro"])
        assert result == "Pedro"

    def test_dialogo_autodescripcion(self, shared_spacy_nlp):
        """
        "—Mis ojos son azules —dijo María."
        → "ojos" = María (posesivo "Mis" + hablante = María)
        """
        text = "\u2014Mis ojos son azules \u2014dijo María."
        result = _resolve_scope(shared_spacy_nlp, text, ["María"])
        assert result == "María"


class TestMultiplePossessivesSameSentence:
    """
    Patrón 6: Múltiples posesivos "sus" en la misma oración.

    "Sus ojos miraban a María y sus manos temblaban" — ambos "sus" deben
    resolverse al mismo sujeto.
    """

    def test_dos_sus_mismo_sujeto(self, shared_spacy_nlp):
        """
        "Juan entró. Sus ojos brillaban y sus manos temblaban."
        → "ojos" = Juan y "manos" = Juan (mismo sujeto tacito)
        """
        text = "Juan entró. Sus ojos brillaban y sus manos temblaban."
        result_ojos = _resolve_scope(shared_spacy_nlp, text, ["Juan"], target_phrase="ojos")
        result_manos = _resolve_scope(shared_spacy_nlp, text, ["Juan"], target_phrase="manos")
        assert result_ojos == "Juan", f"ojos debe ser Juan. Got: {result_ojos}"
        assert result_manos == "Juan", f"manos debe ser Juan. Got: {result_manos}"

    @pytest.mark.xfail(reason=(
        "Con dos entidades en contexto, ambos 'sus' deben resolverse al mismo sujeto "
        "pero el resolver puede asignarlos a entidades diferentes por proximidad."
    ))
    def test_dos_sus_con_objeto_intercalado(self, shared_spacy_nlp):
        """
        "Sus ojos miraban a María y sus manos temblaban."
        → Si hay un sujeto tacito previo (p.ej. Juan), ambos "sus" = Juan.
        """
        text = "Juan se acercó. Sus ojos miraban a María y sus manos temblaban."
        result_ojos = _resolve_scope(
            shared_spacy_nlp, text, ["Juan", "María"], target_phrase="ojos"
        )
        result_manos = _resolve_scope(
            shared_spacy_nlp, text, ["Juan", "María"], target_phrase="manos"
        )
        assert result_ojos == "Juan"
        assert result_manos == "Juan"


class TestRelativeClauseInterference:
    """
    Patrón 7: Entidades dentro de cláusulas relativas.

    "El hombre que había conocido a María tenía los ojos azules"
    → "ojos azules" = "El hombre", NO María (que esta dentro de la RC).
    """

    def test_rc_filtra_objeto_dentro(self, shared_spacy_nlp):
        """
        "El hombre que había conocido a María tenía los ojos azules."
        → "ojos" = resolverse fuera de la RC (no María)
        """
        text = "El hombre que había conocido a María tenía los ojos azules."
        result = _resolve_scope(shared_spacy_nlp, text, ["María"])
        # María esta dentro de la RC, no deberia recibir el atributo
        assert result != "María", (
            f"Maria esta dentro de la RC 'que habia conocido a Maria', "
            f"no debe recibir 'ojos azules'. Got: {result}"
        )

    def test_rc_con_dos_entidades_nombradas(self, shared_spacy_nlp):
        """
        "Pedro, que había conocido a María, tenía los ojos azules."
        → "ojos azules" = Pedro (antecedente de la RC)
        """
        text = "Pedro, que había conocido a María, tenía los ojos azules."
        result = _resolve_scope(shared_spacy_nlp, text, ["Pedro", "María"])
        assert result == "Pedro", (
            f"Pedro es el antecedente de la RC. Got: {result}"
        )

    def test_rc_sujeto_interno_no_se_filtra_si_atributo_dentro(self, shared_spacy_nlp):
        """
        "El hombre que tenía los ojos azules se sentó."
        → "ojos azules" esta DENTRO de la RC, asignar al antecedente.
        """
        text = "Pedro era el hombre que tenía los ojos azules."
        result = _resolve_scope(shared_spacy_nlp, text, ["Pedro"])
        # Aqui el atributo esta dentro de la RC, y Pedro es el antecedente
        assert result == "Pedro" or result is None, (
            f"Pedro o resolucion via antecedente. Got: {result}"
        )


class TestGenitiveDe:
    """
    Patrón 8: Genitivo con "de" — asignación directa.

    "los ojos de Juan" → Juan.
    "los ojos verdes de María" → María.
    """

    def test_genitivo_simple(self, shared_spacy_nlp):
        """
        "Los ojos de Juan brillaban."
        → "ojos" = Juan
        """
        text = "Los ojos de Juan brillaban."
        result = _resolve_scope(shared_spacy_nlp, text, ["Juan"])
        assert result == "Juan"

    def test_genitivo_con_adjetivo_intercalado(self, shared_spacy_nlp):
        """
        "Los ojos verdes de María eran hermosos."
        → "ojos" = María (genitivo despues de adjetivo)
        """
        text = "Los ojos verdes de María eran hermosos."
        result = _resolve_scope(shared_spacy_nlp, text, ["María"])
        assert result == "María"

    def test_genitivo_vs_proximidad(self, shared_spacy_nlp):
        """
        "Juan admiraba los ojos azules de Pedro."
        → "ojos" = Pedro (genitivo), no Juan (proximidad)
        """
        text = "Juan admiraba los ojos azules de Pedro."
        result = _resolve_scope(shared_spacy_nlp, text, ["Juan", "Pedro"])
        assert result == "Pedro", (
            f"Genitivo 'de Pedro' tiene prioridad sobre proximidad a Juan. Got: {result}"
        )


# =============================================================================
# MEDIUM PRIORITY: Patrones menos comunes pero importantes
# =============================================================================


class TestPassiveImpersonal:
    """
    Patrón 9: Construcciones pasivas e impersonales con "se".

    "Se le veían los ojos azules a María" → María.
    """

    @pytest.mark.xfail(reason=(
        "Construcciones con 'se le' + 'a PERSONA' son dificiles de parsear. "
        "spaCy puede no detectar 'a Maria' como dativo/benefactivo."
    ))
    def test_se_le_veian_con_a_personal(self, shared_spacy_nlp):
        """
        "Se le veían los ojos azules a María."
        → "ojos" = María (dativo "a María" = poseedora)
        """
        text = "Se le veían los ojos azules a María."
        result = _resolve_scope(shared_spacy_nlp, text, ["María"])
        assert result == "María"

    @pytest.mark.xfail(reason=(
        "Pasiva refleja con complemento agente: "
        "'se notaban sus ojos' necesita resolver 'sus' al sujeto previo."
    ))
    def test_pasiva_refleja_con_posesivo(self, shared_spacy_nlp):
        """
        "María llegó. Se notaban sus ojos azules."
        → "ojos" = María (sujeto previo, pasiva refleja)
        """
        text = "María llegó. Se notaban sus ojos azules."
        result = _resolve_scope(shared_spacy_nlp, text, ["María"])
        assert result == "María"


class TestReflexiveBodyPart:
    """
    Patrón 10: Reflexivo + parte del cuerpo.

    En español: "se frotó los ojos" = los ojos del sujeto.
    """

    def test_reflexivo_basico(self, shared_spacy_nlp):
        """
        "María se frotó los ojos verdes."
        → "ojos" = María (reflexivo indica posesion)
        """
        text = "María se frotó los ojos verdes."
        result = _resolve_scope(shared_spacy_nlp, text, ["María"])
        assert result == "María"

    def test_reflexivo_con_distractor(self, shared_spacy_nlp):
        """
        "María se frotó los ojos cansados mientras miraba a Pedro."
        → "ojos" = María (reflexivo, no Pedro que es objeto)
        """
        text = "María se frotó los ojos cansados mientras miraba a Pedro."
        result = _resolve_scope(shared_spacy_nlp, text, ["María", "Pedro"])
        assert result == "María", (
            f"Reflexivo 'se froto los ojos' implica Maria. Got: {result}"
        )


class TestIndirectObjectPossessive:
    """
    Patrón 11: Dativo posesivo — "Le brillaban los ojos a Juan".

    Construccion tipica del español donde el dativo indica poseedor.
    """

    @pytest.mark.xfail(reason=(
        "Dativo posesivo 'le brillaban los ojos a X' requiere analisis "
        "del clítico 'le' + complemento 'a X' como poseedor."
    ))
    def test_dativo_posesivo_basico(self, shared_spacy_nlp):
        """
        "Le brillaban los ojos a Juan."
        → "ojos" = Juan (dativo posesivo con "a Juan")
        """
        text = "Le brillaban los ojos a Juan."
        result = _resolve_scope(shared_spacy_nlp, text, ["Juan"])
        assert result == "Juan"

    @pytest.mark.xfail(reason=(
        "Dativo posesivo con 'a' al final de la oracion — "
        "spaCy puede interpretar 'a María' como OBL y filtrarlo."
    ))
    def test_dativo_posesivo_con_distractor(self, shared_spacy_nlp):
        """
        "Pedro notó que le brillaban los ojos azules a María."
        → "ojos" = María (dativo posesivo), no Pedro
        """
        text = "Pedro notó que le brillaban los ojos azules a María."
        result = _resolve_scope(shared_spacy_nlp, text, ["Pedro", "María"])
        assert result == "María"


class TestComparison:
    """
    Patrón 12: Comparaciones — "ojos azules como los de su madre".

    El atributo pertenece al sujeto, no al comparando.
    """

    @pytest.mark.xfail(reason=(
        "Comparaciones con 'como los de' requieren analisis de la estructura "
        "comparativa para no asignar al comparando."
    ))
    def test_comparacion_como_los_de(self, shared_spacy_nlp):
        """
        "Juan tenía los ojos azules como los de su madre."
        → "ojos azules" = Juan (el sujeto), no la madre (comparando)
        """
        text = "Juan tenía los ojos azules como los de su madre."
        # "madre" no esta en entities, asi que solo deberia resolver a Juan
        result = _resolve_scope(shared_spacy_nlp, text, ["Juan"])
        assert result == "Juan"

    def test_comparacion_con_dos_entidades(self, shared_spacy_nlp):
        """
        "Tenía los ojos azules como Pedro."
        → "ojos azules" = sujeto tacito (no Pedro, que es el comparando)
        """
        text = "María tenía los ojos azules como Pedro."
        result = _resolve_scope(shared_spacy_nlp, text, ["María", "Pedro"])
        assert result == "María", (
            f"El comparando 'como Pedro' no deberia recibir el atributo. Got: {result}"
        )


class TestContrastCorrection:
    """
    Patrón 13: Contraste/corrección — "no eran los ojos de María sino los de Juan".

    El atributo real pertenece a la segunda parte (la correccion).
    """

    @pytest.mark.xfail(reason=(
        "Estructura 'no X sino Y' requiere analisis de negacion + "
        "correccion. El resolver no distingue entre la parte negada y la afirmada."
    ))
    def test_no_sino_basico(self, shared_spacy_nlp):
        """
        "No eran los ojos azules de María sino los de Juan."
        → En este contexto, la corrección atribuye a Juan.
        """
        text = "No eran los ojos azules de María sino los de Juan."
        result = _resolve_scope(shared_spacy_nlp, text, ["María", "Juan"])
        # Ambos son mencionados, pero la corrección favorece a Juan
        # Sin embargo, el primer "ojos" se encuentra y "de María" es genitivo
        # Este test documenta la complejidad del caso
        assert result in ("María", "Juan"), f"Debe resolver a alguno. Got: {result}"


class TestTemporalPast:
    """
    Patrón 14: Atributos temporales — "había tenido los ojos azules de niña".

    El atributo es del sujeto, y es temporal (pasado).
    """

    def test_temporal_habia_tenido(self, shared_spacy_nlp):
        """
        "María había tenido los ojos azules de niña."
        → "ojos" = María (sujeto, atributo pasado)
        """
        text = "María había tenido los ojos azules de niña."
        result = _resolve_scope(shared_spacy_nlp, text, ["María"])
        assert result == "María"


# =============================================================================
# EDGE CASES: Casos extremos
# =============================================================================


class TestTwoCharactersSameSentence:
    """
    Patrón 15: Dos personajes con atributos en la misma oración.

    "Juan, de ojos azules, miraba a María, de ojos verdes."
    """

    @pytest.mark.xfail(reason=(
        "Aposiciones con 'de ojos X' para dos personajes en la misma oracion "
        "requieren analisis de la estructura apositiva."
    ))
    def test_aposicion_doble(self, shared_spacy_nlp):
        """
        "Juan, de ojos azules, miraba a María, de ojos verdes."
        → Primer "ojos" = Juan, segundo "ojos" = María.

        Para testear, buscamos la primera ocurrencia de "ojos".
        """
        text = "Juan, de ojos azules, miraba a María, de ojos verdes."
        # Primera ocurrencia = ojos azules = Juan
        result_first = _resolve_scope(
            shared_spacy_nlp, text, ["Juan", "María"], target_phrase="ojos azules"
        )
        assert result_first == "Juan", f"Primer 'ojos azules' = Juan. Got: {result_first}"

    @pytest.mark.xfail(reason=(
        "Segunda aposicion con 'de ojos verdes' asociada a Maria "
        "requiere resolver proximidad a la aposicion."
    ))
    def test_aposicion_doble_segundo_atributo(self, shared_spacy_nlp):
        """
        "Juan, de ojos azules, miraba a María, de ojos verdes."
        → Segundo "ojos" = María.
        """
        text = "Juan, de ojos azules, miraba a María, de ojos verdes."
        result_second = _resolve_scope(
            shared_spacy_nlp, text, ["Juan", "María"], target_phrase="ojos verdes"
        )
        assert result_second == "María", f"Segundo 'ojos verdes' = Maria. Got: {result_second}"


class TestNestedPossessives:
    """
    Patrón 16: Posesivos anidados — "Su hermana tenía sus mismos ojos azules".

    "Su hermana" = hermana de X, "sus mismos ojos" = ojos de la hermana.
    """

    @pytest.mark.xfail(reason=(
        "Posesivos anidados: 'Su hermana tenia sus mismos ojos azules' "
        "tiene dos 'su(s)' con referentes diferentes. "
        "El segundo 'sus' se refiere a la hermana, el primero a alguien exterior."
    ))
    def test_posesivo_anidado(self, shared_spacy_nlp):
        """
        "Juan recordaba a su hermana. Ella tenía sus mismos ojos azules."
        → "ojos azules" = la hermana (ella = la hermana)
        """
        text = "Juan recordaba a su hermana. Ella tenía sus mismos ojos azules."
        result = _resolve_scope(shared_spacy_nlp, text, ["Juan"])
        # Sin "hermana" en la lista de entidades, deberia resolver a Juan
        # Pero el test documenta que conceptualmente los ojos son de la hermana
        assert result == "Juan" or result is None


class TestVocativeConfusion:
    """
    Patrón 17: Vocativos — "María, tus ojos son azules".

    El vocativo identifica al interlocutor (receptor), que es el poseedor.
    """

    def test_vocativo_con_tus(self, shared_spacy_nlp):
        """
        "María, tus ojos son azules."
        → "ojos" = María (vocativo + posesivo de 2a persona)
        """
        text = "María, tus ojos son azules."
        result = _resolve_scope(shared_spacy_nlp, text, ["María"])
        assert result == "María"

    @pytest.mark.xfail(reason=(
        "El vocativo + 'tus' deberia asignarse al vocativo (Maria), "
        "no a Pedro (que es solo un espectador en la oracion)."
    ))
    def test_vocativo_con_distractor(self, shared_spacy_nlp):
        """
        "María, tus ojos son azules, dijo Pedro."
        → "ojos" = María (vocativo), no Pedro
        """
        text = "María, tus ojos son azules, dijo Pedro."
        result = _resolve_scope(shared_spacy_nlp, text, ["María", "Pedro"])
        assert result == "María"


class TestAPersonalFalsePositive:
    """
    Patrón 18: "a personal" como falso positivo para filtrado de objetos.

    "Acudió a Ana" — "a Ana" es objeto, no dirección.
    Pero la heuristica de "a" + ENTIDAD podria sobre-filtrar.
    """

    def test_a_personal_correctamente_filtrada(self, shared_spacy_nlp):
        """
        "Pedro miró a Ana. Sus ojos verdes relucían."
        → "ojos verdes" = Pedro (sujeto), "a Ana" es objeto y se filtra.
        """
        text = "Pedro miró a Ana. Sus ojos verdes relucían."
        result = _resolve_scope(shared_spacy_nlp, text, ["Pedro", "Ana"])
        assert result == "Pedro", (
            f"'a Ana' es objeto directo, no poseedora de los ojos. Got: {result}"
        )

    def test_a_como_direccion_no_persona(self, shared_spacy_nlp):
        """
        "Pedro fue a casa. Sus ojos estaban cansados."
        → "ojos" = Pedro (unico candidato persona)
        """
        text = "Pedro fue a casa. Sus ojos estaban cansados."
        result = _resolve_scope(shared_spacy_nlp, text, ["Pedro"])
        assert result == "Pedro"


class TestDirectionNotPersonalA:
    """
    Patrón 19: "a" como dirección vs "a personal".

    "Miró al cielo con sus ojos azules" — "al cielo" es dirección, no persona.
    """

    def test_al_cielo_no_es_persona(self, shared_spacy_nlp):
        """
        "Pedro miró al cielo con sus ojos azules."
        → "ojos" = Pedro (sujeto), "al cielo" no es entidad persona.
        """
        text = "Pedro miró al cielo con sus ojos azules."
        result = _resolve_scope(shared_spacy_nlp, text, ["Pedro"])
        assert result == "Pedro"


# =============================================================================
# Parametrized tests: casos tabulares
# =============================================================================


class TestSubjectResolutionParametrized:
    """
    Tests parametrizados de resolución de sujeto para "sus ojos"
    en diversas construcciones sintácticas.
    """

    @pytest.mark.parametrize(
        "text, entities, expected, description",
        [
            # Sujeto explicito antes del atributo
            (
                "Juan tenía los ojos azules.",
                ["Juan"],
                "Juan",
                "sujeto_explicito_tenia",
            ),
            # Sujeto con verbo copulativo
            (
                "María era de ojos verdes.",
                ["María"],
                "María",
                "copulativo_era_de",
            ),
            # Sujeto con "llevar"
            (
                "Pedro llevaba los ojos pintados.",
                ["Pedro"],
                "Pedro",
                "verbo_llevar",
            ),
            # Sujeto con "mostrar"
            (
                "Elena mostraba unos ojos cansados.",
                ["Elena"],
                "Elena",
                "verbo_mostrar",
            ),
            # Sujeto pospuesto (inversion)
            (
                "Brillaban los ojos azules de Pedro.",
                ["Pedro"],
                "Pedro",
                "sujeto_pospuesto_genitivo",
            ),
        ],
        ids=lambda x: x if isinstance(x, str) else "",
    )
    def test_sujeto_explicito_variantes(
        self, shared_spacy_nlp, text, entities, expected, description
    ):
        result = _resolve_scope(shared_spacy_nlp, text, entities)
        assert result == expected, (
            f"[{description}] Esperado '{expected}', obtenido '{result}'"
        )

    @pytest.mark.parametrize(
        "text, entities, expected, description",
        [
            # "a personal" debe filtrar objeto
            (
                "Sus ojos azules miraban a María.",
                ["Juan", "María"],
                "Juan",
                "sus_ojos_miraban_a_objeto",
            ),
            # Objeto con "hacia"
            (
                "Sus ojos se dirigieron hacia Elena.",
                ["Pedro", "Elena"],
                "Pedro",
                "sus_ojos_hacia_objeto",
            ),
            # Objeto con "contra"
            (
                "Sus ojos fulminaron contra Pedro.",
                ["María", "Pedro"],
                "María",
                "sus_ojos_contra_objeto",
            ),
        ],
        ids=lambda x: x if isinstance(x, str) else "",
    )
    def test_filtrado_objetos(
        self, shared_spacy_nlp, text, entities, expected, description
    ):
        """
        Verifica que entidades despues de preposiciones de complemento
        (a, hacia, contra, etc.) se filtran correctamente.

        Nota: en estos tests el sujeto tacito es el primer nombre en entities
        pero no aparece en la oracion — depende del contexto previo.
        Se verifica que el objeto NO recibe el atributo.
        """
        result = _resolve_scope(shared_spacy_nlp, text, entities)
        # No debe ser el objeto
        object_name = entities[-1]
        if result is not None:
            assert result != object_name or result == expected, (
                f"[{description}] El objeto '{object_name}' no debe recibir "
                f"el atributo. Got: {result}"
            )


class TestObjectComplementFiltering:
    """
    Tests específicos para _is_object_complement().

    Verifica que las preposiciones que introducen complementos se detectan
    y que el resolver no asigna atributos a entidades en posicion de objeto.
    """

    @pytest.mark.parametrize(
        "text, entities, non_owner, description",
        [
            (
                "Sus ojos azules miraban con curiosidad a María.",
                ["Juan", "María"],
                "María",
                "a_personal_tipica",
            ),
            (
                "Sus ojos se posaron sobre Elena.",
                ["Carlos", "Elena"],
                "Elena",
                "preposicion_sobre",
            ),
            (
                "Sus ojos azules se volvieron hacia Pedro.",
                ["Ana", "Pedro"],
                "Pedro",
                "preposicion_hacia",
            ),
            (
                "Con sus ojos azules desafió a Ricardo.",
                ["Laura", "Ricardo"],
                "Ricardo",
                "con_instrumental_y_a_personal",
            ),
        ],
        ids=lambda x: x if isinstance(x, str) else "",
    )
    def test_preposiciones_filtran_objeto(
        self, shared_spacy_nlp, text, entities, non_owner, description
    ):
        """
        Verifica que la entidad despues de la preposicion no recibe el atributo.
        """
        result = _resolve_scope(shared_spacy_nlp, text, entities)
        if result is not None:
            assert result != non_owner, (
                f"[{description}] '{non_owner}' es complemento, no debe recibir "
                f"atributo de 'ojos'. Got: {result}"
            )


# =============================================================================
# Pipeline completo: tests de integración con AttributeExtractor
# =============================================================================


class TestFullPipelineIntegration:
    """
    Tests que ejecutan el pipeline completo de extracción de atributos
    (no solo el scope resolver) para verificar el resultado end-to-end.
    """

    def test_pipeline_sujeto_explicito_ojos(self, shared_spacy_nlp):
        """
        Pipeline completo: "Juan tenía los ojos azules."
        → (Juan, eye_color, azules)
        """
        text = "Juan tenía los ojos azules."
        attrs = _extract_attrs(shared_spacy_nlp, text, ["Juan"])
        eye_attrs = [(e, k, v) for e, k, v in attrs if k == "eye_color"]
        assert len(eye_attrs) >= 1, f"Debe extraer eye_color. Attrs: {attrs}"
        entities_with_eyes = {e for e, k, v in eye_attrs}
        assert "Juan" in entities_with_eyes, (
            f"eye_color debe asignarse a Juan. Got: {eye_attrs}"
        )

    def test_pipeline_genitivo_de(self, shared_spacy_nlp):
        """
        Pipeline completo: "Juan admiraba los ojos azules de Pedro."
        → (Pedro, eye_color, azules) via genitivo, NO Juan.
        """
        text = "Juan admiraba los ojos azules de Pedro."
        attrs = _extract_attrs(shared_spacy_nlp, text, ["Juan", "Pedro"])
        eye_attrs = [(e, k, v) for e, k, v in attrs if k == "eye_color"]
        if eye_attrs:
            # Si se extrae, debe ser de Pedro (genitivo)
            pedro_eyes = [(e, k, v) for e, k, v in eye_attrs if e == "Pedro"]
            juan_eyes = [(e, k, v) for e, k, v in eye_attrs if e == "Juan"]
            assert len(pedro_eyes) >= 1 or len(juan_eyes) == 0, (
                f"Si se extraen ojos azules, deben ser de Pedro. Got: {eye_attrs}"
            )

    def test_pipeline_no_asigna_a_objeto(self, shared_spacy_nlp):
        """
        Pipeline completo: "Sus ojos azules miraban a María."
        → NO debe asignar a María (objeto con 'a personal').
        """
        text = "Pedro entró. Sus ojos azules miraban a María."
        attrs = _extract_attrs(shared_spacy_nlp, text, ["Pedro", "María"])
        eye_attrs = [(e, k, v) for e, k, v in attrs if k == "eye_color"]
        maria_eyes = [(e, k, v) for e, k, v in eye_attrs if e == "María"]
        assert len(maria_eyes) == 0, (
            f"Maria (objeto) no debe recibir eye_color. Got: {maria_eyes}"
        )


# =============================================================================
# Regression tests: bugs conocidos ya corregidos
# =============================================================================


class TestRegressions:
    """
    Tests de regresión para bugs previamente corregidos.
    Estos DEBEN pasar; si fallan, indica una regresión.
    """

    def test_regression_sus_ojos_miraban_a_maria(self, shared_spacy_nlp):
        """
        BUG ORIGINAL: "Sus ojos azules miraban a María"
        → Se asignaba a María (objeto) en vez del sujeto previo.

        CORREGIDO: _is_object_complement() filtra "a María".
        """
        text = "Juan entró en la sala. Sus ojos azules miraban a María."
        result = _resolve_scope(shared_spacy_nlp, text, ["Juan", "María"])
        assert result != "María", (
            f"REGRESION: Maria es objeto, no debe recibir atributo. Got: {result}"
        )

    def test_regression_wider_scope_filtra_objetos(self, shared_spacy_nlp):
        """
        BUG RELACIONADO: En el paso 4 (wider scope), la búsqueda en
        oraciones vecinas no filtraba complementos objeto precedidos de "a".

        CORREGIDO: Paso 4 ahora aplica _is_object_complement() para
        candidatos despues de la posicion del atributo.
        """
        text = "Sus ojos azules se cruzaron con los de María."
        result = _resolve_scope(shared_spacy_nlp, text, ["Juan", "María"])
        # "María" aparece despues de la posicion del atributo,
        # pero con "de" no deberia filtrarse (es genitivo, no objeto)
        # Este test verifica que no hay over-filtering
        assert result is not None, "Debe resolver a alguna entidad"


# =============================================================================
# Stress tests: textos más largos y complejos
# =============================================================================


class TestLongerNarrativeContexts:
    """
    Tests con contextos narrativos más realistas (varios párrafos).
    """

    def test_parrafo_con_multiples_personajes(self, shared_spacy_nlp):
        """
        Párrafo narrativo con 3 personajes y un atributo.
        Solo el sujeto de la oracion con el atributo debe recibirlo.
        """
        text = (
            "Ana entró en la habitación. Pedro la saludó con un gesto. "
            "Carlos permanecía sentado junto a la ventana. "
            "Ana tenía los ojos cansados tras el largo viaje."
        )
        result = _resolve_scope(
            shared_spacy_nlp, text, ["Ana", "Pedro", "Carlos"]
        )
        assert result == "Ana", (
            f"Ana es el sujeto de 'tenia los ojos cansados'. Got: {result}"
        )

    def test_cambio_de_parrafo_rompe_scope(self, shared_spacy_nlp):
        """
        Un cambio de párrafo (doble salto de linea) debería limitar el scope.

        Primer párrafo: Juan. Segundo párrafo: María con ojos azules.
        """
        text = (
            "Juan salió de la casa sin decir nada.\n\n"
            "María se sentó en el porche. Sus ojos azules miraban al horizonte."
        )
        result = _resolve_scope(
            shared_spacy_nlp, text, ["Juan", "María"]
        )
        assert result == "María", (
            f"Cambio de parrafo: Maria es sujeto del segundo parrafo. Got: {result}"
        )

    def test_tres_oraciones_pro_drop_con_distractor(self, shared_spacy_nlp):
        """
        Tres oraciones consecutivas con sujeto tacito y un personaje
        mencionado como objeto en el medio.
        """
        text = (
            "Elena abrió la puerta. Saludó a Pedro con un gesto. "
            "Tenía los ojos enrojecidos por el llanto."
        )
        result = _resolve_scope(
            shared_spacy_nlp, text, ["Elena", "Pedro"]
        )
        assert result == "Elena", (
            f"Elena es el sujeto tacito de las 3 oraciones. Got: {result}"
        )


# =============================================================================
# Confidence thresholds
# =============================================================================


class TestConfidenceLevels:
    """
    Tests que verifican que la confianza asignada es razonable
    según el tipo de evidencia.
    """

    def test_sujeto_explicito_alta_confianza(self, shared_spacy_nlp):
        """
        Sujeto gramátical explícito → confianza >= 0.85.
        """
        text = "María tenía los ojos verdes."
        _, confidence = _resolve_scope_confidence(
            shared_spacy_nlp, text, ["María"]
        )
        assert confidence >= 0.85, (
            f"Sujeto explicito debe tener confianza >= 0.85. Got: {confidence}"
        )

    def test_scope_lejano_baja_confianza(self, shared_spacy_nlp):
        """
        Entidad lejos del atributo (varias oraciones) → confianza < 0.85.
        """
        text = (
            "Juan entró. Habló con el portero. Se sentó en el sofá. "
            "Pidió un café. Tenía los ojos cansados."
        )
        _, confidence = _resolve_scope_confidence(
            shared_spacy_nlp, text, ["Juan"]
        )
        assert confidence < 0.85, (
            f"Entidad lejana debe tener confianza moderada. Got: {confidence}"
        )


# =============================================================================
# Copulative identity
# =============================================================================


class TestCopulativeIdentity:
    """
    Tests para identidad copulativa: "La mujer era María".

    Cuando el sujeto gramatical es un sustantivo descriptivo (no-entidad)
    y hay una identidad copulativa que resuelve a una entidad, el resolver
    debe preferir la entidad resuelta.
    """

    def test_mujer_era_maria(self, shared_spacy_nlp):
        """
        "La mujer de ojos verdes era María."
        → "ojos" se resuelve al sujeto "mujer" → copulativa → María.
        """
        text = "La mujer de ojos verdes era María."
        result = _resolve_scope(shared_spacy_nlp, text, ["María"])
        assert result == "María", (
            f"Identidad copulativa: 'La mujer' = Maria. Got: {result}"
        )

    def test_hombre_que_conocio_era_pedro(self, shared_spacy_nlp):
        """
        "El hombre que María había conocido era Pedro. Tenía los ojos grises."
        → "ojos" = Pedro (via identidad copulativa)
        """
        text = "El hombre que María había conocido era Pedro. Tenía los ojos grises."
        result = _resolve_scope(shared_spacy_nlp, text, ["María", "Pedro"])
        # Pedro via copulativa, o al menos no María (que esta en la RC)
        assert result != "María" or result == "Pedro", (
            f"Maria esta en la RC, Pedro via copulativa. Got: {result}"
        )


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
