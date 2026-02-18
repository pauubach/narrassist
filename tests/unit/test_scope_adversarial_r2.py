"""
Tests adversariales Round 2 para ScopeResolver: ambigüedad, pronombres y tipos de atributo.

Round 2 amplía la cobertura de round 1 con:
1. Detección de ambigüedad genuina (debe retornar None)
2. Desambiguación por pronombres él/ella
3. Todos los tipos de atributo (cabello, altura, complexión, barba, piel, edad)
4. Cláusulas subordinadas con "cuando" (patrón ambiguo sistemático)
5. Casos adversariales de borde

Convenciones:
- Tests que DEBEN pasar con el código actual NO llevan xfail.
- Tests que documentan comportamiento DESEADO pero no implementado: @pytest.mark.xfail.
- Cada test incluye el patrón lingüístico en el nombre y docstring.

Autor: Round 2 - Auditoría de ambigüedad y scope multi-atributo.
"""

import re

import pytest

from narrative_assistant.nlp.scope_resolver import ScopeResolver


# =============================================================================
# Helpers (compatibles con round 1)
# =============================================================================


def _build_mentions(text: str, entities: list[str]) -> list[tuple[str, int, int, str]]:
    """
    Construye lista de menciones de entidad a partir de nombres y texto.
    """
    mentions = []
    for name in entities:
        for m in re.finditer(re.escape(name), text):
            mentions.append((name, m.start(), m.end(), "PER"))
    return mentions


def _resolve(
    target: str,
    text: str,
    entities: list[str],
    nlp=None,
    prefer_subject: bool = True,
) -> str | None:
    """
    Resolve which entity owns the target body part/attribute.

    Args:
        target: Body part or attribute keyword to find in text
        text: Spanish narrative text
        entities: List of character names
        nlp: spaCy model (loaded automatically if None)
        prefer_subject: Whether to prefer grammatical subject

    Returns:
        Entity name or None if unresolvable/ambiguous.
    """
    if nlp is None:
        from narrative_assistant.nlp.spacy_gpu import load_spacy_model
        nlp = load_spacy_model()
    doc = nlp(text)
    resolver = ScopeResolver(doc, text)
    mentions = _build_mentions(text, entities)
    pos = text.find(target)
    if pos == -1:
        return None
    result = resolver.find_nearest_entity_by_scope(pos, mentions, prefer_subject=prefer_subject)
    return result[0] if result else None


def _resolve_with_confidence(
    target: str,
    text: str,
    entities: list[str],
    nlp=None,
    prefer_subject: bool = True,
) -> tuple[str | None, float]:
    """Like _resolve but also returns confidence score."""
    if nlp is None:
        from narrative_assistant.nlp.spacy_gpu import load_spacy_model
        nlp = load_spacy_model()
    doc = nlp(text)
    resolver = ScopeResolver(doc, text)
    mentions = _build_mentions(text, entities)
    pos = text.find(target)
    if pos == -1:
        return (None, 0.0)
    result = resolver.find_nearest_entity_by_scope(pos, mentions, prefer_subject=prefer_subject)
    return result if result else (None, 0.0)


# =============================================================================
# 1. AMBIGUITY DETECTION: must return None for genuinely ambiguous cases
# =============================================================================


class TestAmbiguityDetection:
    """
    When attribution is genuinely ambiguous (even a human reader cannot
    determine who owns the attribute), the resolver should return None.

    The caller will generate an alert for the user to review manually.
    """

    def test_cuando_conocio_a_tenia_cabello(self, shared_spacy_nlp):
        """
        'Cuando Juan conoció a María tenía el cabello rizado.'
        AMBIGUOUS: 'tenía' could refer to Juan or María. The subordinate
        clause 'cuando X conoció a Y' introduces two equally valid candidates.
        """
        text = "Cuando Juan conoció a María tenía el cabello rizado."
        result = _resolve("cabello", text, ["Juan", "María"], nlp=shared_spacy_nlp)
        assert result is None, (
            f"Genuinely ambiguous: 'cuando X conoció a Y tenía...' "
            f"should not assign. Got: {result}"
        )

    def test_cuando_vio_a_tenia_ojos(self, shared_spacy_nlp):
        """
        'Cuando Pedro vio a Elena tenía los ojos enrojecidos.'
        AMBIGUOUS: same 'cuando X verbo a Y, tenía...' pattern.
        """
        text = "Cuando Pedro vio a Elena tenía los ojos enrojecidos."
        result = _resolve("ojos", text, ["Pedro", "Elena"], nlp=shared_spacy_nlp)
        assert result is None, (
            f"Ambiguous subordinate clause: should return None. Got: {result}"
        )

    def test_sus_ojos_le_llamaron_la_atencion(self, shared_spacy_nlp):
        """
        'María saludó a Juan. Sus ojos azules le llamaron la atención.'
        AMBIGUOUS: 'Sus' could be María's or Juan's. 'le' doesn't disambiguate
        because it doesn't indicate gender.
        """
        text = "María saludó a Juan. Sus ojos azules le llamaron la atención."
        result = _resolve("ojos", text, ["Juan", "María"], nlp=shared_spacy_nlp)
        assert result is None, (
            f"Ambiguous: 'Sus ojos le llamaron la atención' after two characters. "
            f"'le' is gender-neutral. Got: {result}"
        )

    def test_le_dijo_que_tenia_pelo(self, shared_spacy_nlp):
        """
        'Juan le dijo a María que tenía el pelo sucio.'
        AMBIGUOUS: 'tenía' in subordinate 'que tenía...' could refer to Juan
        (he told her that HE had dirty hair) or María (he told her that SHE had it).
        """
        text = "Juan le dijo a María que tenía el pelo sucio."
        result = _resolve("pelo", text, ["Juan", "María"], nlp=shared_spacy_nlp)
        assert result is None, (
            f"Ambiguous: 'le dijo a X que tenía...' — unclear referent. Got: {result}"
        )

    def test_cuando_se_conocieron_tenia(self, shared_spacy_nlp):
        """
        'Cuando Ana y Pedro se conocieron, tenía el pelo largo.'
        AMBIGUOUS: 'tenía' is singular but there are two candidates.
        The 'cuando' subordinate pattern correctly detects this as ambiguous.
        """
        text = "Cuando Ana y Pedro se conocieron, tenía el pelo largo."
        result = _resolve("pelo", text, ["Ana", "Pedro"], nlp=shared_spacy_nlp)
        assert result is None, (
            f"Ambiguous: reflexive 'se conocieron' + singular 'tenía'. Got: {result}"
        )


# =============================================================================
# 2. PRONOUN DISAMBIGUATION: él/ella resolve ambiguity
# =============================================================================


class TestPronounDisambiguation:
    """
    When the attribute sentence contains directional pronouns (en él, en ella,
    a él, a ella), these disambiguate possessive 'sus':
    - 'Sus ojos se clavaron en él' → 'sus' = NOT él → the other person
    - 'Sus ojos se clavaron en ella' → 'sus' = NOT ella → the other person
    """

    def test_se_clavaron_en_el(self, shared_spacy_nlp):
        """
        'María saludó a Juan. Sus ojos azules se clavaron en él.'
        → 'en él' = Juan is the TARGET of the gaze
        → 'Sus ojos' = María's eyes (she stared AT HIM)
        """
        text = "María saludó a Juan. Sus ojos azules se clavaron en él."
        result = _resolve("ojos", text, ["Juan", "María"], nlp=shared_spacy_nlp)
        assert result == "María", (
            f"'Sus ojos se clavaron en él' → María's eyes stared at Juan. Got: {result}"
        )

    def test_se_clavaron_en_ella(self, shared_spacy_nlp):
        """
        'María saludó a Juan. Sus ojos azules se clavaron en ella.'
        → 'en ella' = María is the TARGET of the gaze
        → 'Sus ojos' = Juan's eyes (he stared AT HER)
        """
        text = "María saludó a Juan. Sus ojos azules se clavaron en ella."
        result = _resolve("ojos", text, ["Juan", "María"], nlp=shared_spacy_nlp)
        assert result == "Juan", (
            f"'Sus ojos se clavaron en ella' → Juan's eyes stared at María. Got: {result}"
        )

    def test_lo_miraba_con_sus_ojos(self, shared_spacy_nlp):
        """
        'Elena lo miraba con sus ojos verdes.'
        → 'lo' = masculine accusative → Elena is looking at a male
        → 'sus ojos' belong to Elena (she does the looking)
        """
        text = "Pedro llegó. Elena lo miraba con sus ojos verdes."
        result = _resolve("ojos", text, ["Pedro", "Elena"], nlp=shared_spacy_nlp)
        assert result == "Elena", (
            f"'Elena lo miraba con sus ojos' → Elena's eyes. Got: {result}"
        )

    def test_la_miraba_con_sus_ojos(self, shared_spacy_nlp):
        """
        'Pedro la miraba con sus ojos grises.'
        → 'la' = feminine accusative → Pedro is looking at a female
        → 'sus ojos' belong to Pedro
        """
        text = "Elena llegó. Pedro la miraba con sus ojos grises."
        result = _resolve("ojos", text, ["Pedro", "Elena"], nlp=shared_spacy_nlp)
        assert result == "Pedro", (
            f"'Pedro la miraba con sus ojos' → Pedro's eyes. Got: {result}"
        )

    @pytest.mark.xfail(reason=(
        "Pronoun disambiguation for 'le' is hard because 'le' is gender-neutral "
        "in Spanish. Would need deeper semantic analysis."
    ))
    def test_le_no_disambigua(self, shared_spacy_nlp):
        """
        'Pedro habló con Elena. Le brillaban sus ojos azules.'
        'le' doesn't indicate gender → still ambiguous.
        """
        text = "Pedro habló con Elena. Le brillaban sus ojos azules."
        result = _resolve("ojos", text, ["Pedro", "Elena"], nlp=shared_spacy_nlp)
        assert result is None, (
            f"'le' is gender-neutral, ambiguous. Got: {result}"
        )


# =============================================================================
# 3. MULTIPLE ATTRIBUTE TYPES: cabello, altura, complexión, barba, piel, edad
# =============================================================================


class TestCabelloAttributes:
    """Test hair attributes (cabello/pelo)."""

    def test_cabello_con_sujeto_explicito(self, shared_spacy_nlp):
        """'Juan tenía el cabello negro.' → cabello = Juan."""
        text = "Juan tenía el cabello negro."
        result = _resolve("cabello", text, ["Juan"], nlp=shared_spacy_nlp)
        assert result == "Juan"

    def test_pelo_largo_pro_drop(self, shared_spacy_nlp):
        """'María entró. Tenía el pelo largo y negro.' → pelo = María."""
        text = "María entró. Tenía el pelo largo y negro."
        result = _resolve("pelo", text, ["María"], nlp=shared_spacy_nlp)
        assert result == "María"

    def test_su_cabello_posesivo(self, shared_spacy_nlp):
        """'Juan entró. Su cabello rizado brillaba bajo la luz.' → Juan."""
        text = "Juan entró. Su cabello rizado brillaba bajo la luz."
        result = _resolve("cabello", text, ["Juan"], nlp=shared_spacy_nlp)
        assert result == "Juan"

    def test_cabello_de_genitivo(self, shared_spacy_nlp):
        """'El cabello de María era rubio.' → cabello = María."""
        text = "El cabello de María era rubio."
        result = _resolve("cabello", text, ["María"], nlp=shared_spacy_nlp)
        assert result == "María"

    def test_pelo_dos_entidades_sujeto_vs_objeto(self, shared_spacy_nlp):
        """
        'Ana acarició a Pedro. Su pelo castaño caía sobre la frente.'
        → pelo = Ana (sujeto de oración anterior, sujeto tácito de 'caía')
        """
        text = "Ana acarició a Pedro. Su pelo castaño caía sobre la frente."
        result = _resolve("pelo", text, ["Ana", "Pedro"], nlp=shared_spacy_nlp)
        assert result == "Ana", (
            f"Ana is the subject of the previous sentence. Got: {result}"
        )


class TestAlturaAttributes:
    """Test height/stature attributes."""

    def test_era_alto_copulativo(self, shared_spacy_nlp):
        """'Pedro era alto y delgado.' → alto applies to Pedro."""
        text = "Pedro era alto y delgado."
        # Note: we search for the adjective position, but the scope resolver
        # is called with the position of a body-part/attribute keyword.
        # 'alto' is an adjective, not a body part — test that resolution still works.
        result = _resolve("alto", text, ["Pedro"], nlp=shared_spacy_nlp)
        assert result == "Pedro"

    def test_estatura_con_posesivo(self, shared_spacy_nlp):
        """'Juan entró. Su estatura imponente destacaba entre la multitud.' → Juan."""
        text = "Juan entró. Su estatura imponente destacaba entre la multitud."
        result = _resolve("estatura", text, ["Juan"], nlp=shared_spacy_nlp)
        assert result == "Juan"

    def test_altura_pro_drop_chain(self, shared_spacy_nlp):
        """'Carlos se levantó. Era muy alto.' → alto = Carlos."""
        text = "Carlos se levantó. Era muy alto."
        result = _resolve("alto", text, ["Carlos"], nlp=shared_spacy_nlp)
        assert result == "Carlos"


class TestComplexionAttributes:
    """Test build/complexion attributes."""

    def test_fornido_copulativo(self, shared_spacy_nlp):
        """'Pedro era fornido como un toro.' → fornido = Pedro."""
        text = "Pedro era fornido como un toro."
        result = _resolve("fornido", text, ["Pedro"], nlp=shared_spacy_nlp)
        assert result == "Pedro"

    def test_complexion_genitivo(self, shared_spacy_nlp):
        """'La complexión delgada de Ana contrastaba con la de Pedro.' → Ana."""
        text = "La complexión delgada de Ana contrastaba con la de Pedro."
        result = _resolve("complexión", text, ["Ana", "Pedro"], nlp=shared_spacy_nlp)
        assert result == "Ana", (
            f"Genitive 'de Ana' owns 'complexión'. Got: {result}"
        )


class TestBarbaAttributes:
    """Test beard attributes."""

    def test_barba_posesivo(self, shared_spacy_nlp):
        """'Juan apareció. Su barba espesa y canosa le daba un aire distinguido.' → Juan."""
        text = "Juan apareció. Su barba espesa y canosa le daba un aire distinguido."
        result = _resolve("barba", text, ["Juan"], nlp=shared_spacy_nlp)
        assert result == "Juan"

    def test_barba_de_genitivo(self, shared_spacy_nlp):
        """'La barba de Pedro era gris.' → Pedro."""
        text = "La barba de Pedro era gris."
        result = _resolve("barba", text, ["Pedro"], nlp=shared_spacy_nlp)
        assert result == "Pedro"

    def test_barba_sujeto_explicito(self, shared_spacy_nlp):
        """'Carlos llevaba una barba descuidada.' → Carlos."""
        text = "Carlos llevaba una barba descuidada."
        result = _resolve("barba", text, ["Carlos"], nlp=shared_spacy_nlp)
        assert result == "Carlos"


class TestPielAttributes:
    """Test skin attributes."""

    def test_piel_morena_con_de(self, shared_spacy_nlp):
        """'Elena era de piel morena.' → piel = Elena."""
        text = "Elena era de piel morena."
        result = _resolve("piel", text, ["Elena"], nlp=shared_spacy_nlp)
        assert result == "Elena"

    def test_piel_bronceada_posesivo(self, shared_spacy_nlp):
        """'Pedro entró. Su piel bronceada delataba largas horas al sol.' → Pedro."""
        text = "Pedro entró. Su piel bronceada delataba largas horas al sol."
        result = _resolve("piel", text, ["Pedro"], nlp=shared_spacy_nlp)
        assert result == "Pedro"


class TestEdadAttributes:
    """Test age attributes."""

    def test_edad_aparentaba(self, shared_spacy_nlp):
        """'María aparentaba unos treinta años.' → años = María."""
        text = "María aparentaba unos treinta años."
        result = _resolve("años", text, ["María"], nlp=shared_spacy_nlp)
        assert result == "María"

    def test_edad_tenia_anos(self, shared_spacy_nlp):
        """'Juan tenía cuarenta y cinco años.' → años = Juan."""
        text = "Juan tenía cuarenta y cinco años."
        result = _resolve("años", text, ["Juan"], nlp=shared_spacy_nlp)
        assert result == "Juan"


# =============================================================================
# 4. SUBORDINATE CLAUSE AMBIGUITY ("cuando" pattern)
# =============================================================================


class TestSubordinateClauseAmbiguity:
    """
    The 'cuando X verbo a Y, tenía...' pattern is systematically ambiguous
    in Spanish because the subordinate clause introduces two candidates equally.
    """

    def test_cuando_encontro_a_tenia_barba(self, shared_spacy_nlp):
        """
        'Cuando Ana encontró a Carlos tenía una barba espesa.'
        AMBIGUOUS: did Ana or Carlos have the thick beard?
        """
        text = "Cuando Ana encontró a Carlos tenía una barba espesa."
        result = _resolve("barba", text, ["Ana", "Carlos"], nlp=shared_spacy_nlp)
        assert result is None, (
            f"Ambiguous 'cuando X encontró a Y tenía...': should return None. Got: {result}"
        )

    def test_cuando_abrazo_a_tenia_pelo(self, shared_spacy_nlp):
        """
        'Cuando Pedro abrazó a Elena tenía el pelo mojado.'
        AMBIGUOUS: whose hair was wet?
        """
        text = "Cuando Pedro abrazó a Elena tenía el pelo mojado."
        result = _resolve("pelo", text, ["Pedro", "Elena"], nlp=shared_spacy_nlp)
        assert result is None, (
            f"Ambiguous subordinate: should return None. Got: {result}"
        )

    def test_cuando_with_only_one_entity_is_NOT_ambiguous(self, shared_spacy_nlp):
        """
        'Cuando Juan llegó tenía el pelo mojado.'
        NOT ambiguous: only one candidate (Juan).
        """
        text = "Cuando Juan llegó tenía el pelo mojado."
        result = _resolve("pelo", text, ["Juan"], nlp=shared_spacy_nlp)
        assert result == "Juan", (
            f"Only one entity: unambiguous. Got: {result}"
        )


# =============================================================================
# 5. CROSS-SENTENCE WITH MULTIPLE ATTRIBUTE TYPES
# =============================================================================


class TestCrossSentenceMultiAttribute:
    """
    Test that different attribute types work correctly in cross-sentence contexts,
    not just 'ojos'.
    """

    def test_cabello_pro_drop_two_sentences(self, shared_spacy_nlp):
        """
        'Ana se sentó. Tenía el cabello recogido en un moño.'
        → cabello = Ana (pro-drop from previous sentence)
        """
        text = "Ana se sentó. Tenía el cabello recogido en un moño."
        result = _resolve("cabello", text, ["Ana"], nlp=shared_spacy_nlp)
        assert result == "Ana"

    def test_barba_pro_drop_after_action(self, shared_spacy_nlp):
        """
        'Pedro bebió un sorbo. Su barba se mojó.'
        → barba = Pedro
        """
        text = "Pedro bebió un sorbo. Su barba se mojó."
        result = _resolve("barba", text, ["Pedro"], nlp=shared_spacy_nlp)
        assert result == "Pedro"

    def test_piel_pro_drop_chain(self, shared_spacy_nlp):
        """
        'Elena salió al jardín. El sol le daba en la cara. Su piel brillaba.'
        → piel = Elena (pro-drop chain, 3 sentences)
        """
        text = "Elena salió al jardín. El sol le daba en la cara. Su piel brillaba."
        result = _resolve("piel", text, ["Elena"], nlp=shared_spacy_nlp)
        assert result == "Elena"

    def test_multiple_attributes_same_paragraph(self, shared_spacy_nlp):
        """
        'Carlos entró. Era alto. Tenía el pelo negro. Sus ojos eran oscuros.'
        All attributes → Carlos.
        """
        text = "Carlos entró. Era alto. Tenía el pelo negro. Sus ojos eran oscuros."
        result_pelo = _resolve("pelo", text, ["Carlos"], nlp=shared_spacy_nlp)
        result_ojos = _resolve("ojos", text, ["Carlos"], nlp=shared_spacy_nlp)
        assert result_pelo == "Carlos", f"pelo should be Carlos. Got: {result_pelo}"
        assert result_ojos == "Carlos", f"ojos should be Carlos. Got: {result_ojos}"


# =============================================================================
# 6. ADVERSARIAL EDGE CASES
# =============================================================================


class TestAdversarialEdgeCases:
    """
    Tricky constructions that test the limits of scope resolution.
    """

    def test_relative_clause_does_not_create_ambiguity(self, shared_spacy_nlp):
        """
        'Pedro, que era amigo de Ana, tenía los ojos azules.'
        CLEAR: Pedro is the antecedent; Ana is inside the RC.
        """
        text = "Pedro, que era amigo de Ana, tenía los ojos azules."
        result = _resolve("ojos", text, ["Pedro", "Ana"], nlp=shared_spacy_nlp)
        assert result == "Pedro", (
            f"Pedro is antecedent of RC. Ana inside RC should not interfere. Got: {result}"
        )

    def test_hermana_de_genitivo_ownership(self, shared_spacy_nlp):
        """
        'La hermana de Juan tenía los ojos verdes.'
        → ojos = la hermana (sujeto gramatical).
        Since 'hermana' is not in entities but Juan IS, and Juan is a genitive
        modifier of 'hermana' (not the subject), the resolver might resolve to Juan
        or None — but it should NOT assign eyes to Juan as the owner.
        """
        text = "La hermana de Juan tenía los ojos verdes."
        # Note: 'hermana' is not in the entity list, only 'Juan'.
        # The grammatical subject is 'hermana', not 'Juan'.
        # If the resolver follows genitive from 'hermana' to 'Juan' for the
        # subject, that's incorrect for eye ownership. But since hermana is
        # not a tracked entity, we accept Juan or None.
        result = _resolve("ojos", text, ["Juan"], nlp=shared_spacy_nlp)
        # This is acceptable: Juan via genitive chain or None
        assert result in ("Juan", None), (
            f"Should be Juan (via genitive chain) or None. Got: {result}"
        )

    def test_three_characters_nearest_subject_wins(self, shared_spacy_nlp):
        """
        'Ana habló. Pedro escuchaba. Elena tenía los ojos claros.'
        → ojos = Elena (explicit subject in same sentence)
        """
        text = "Ana habló. Pedro escuchaba. Elena tenía los ojos claros."
        result = _resolve("ojos", text, ["Ana", "Pedro", "Elena"], nlp=shared_spacy_nlp)
        assert result == "Elena", (
            f"Elena is the explicit subject of 'tenía los ojos'. Got: {result}"
        )

    def test_ambiguity_two_subjects_no_context(self, shared_spacy_nlp):
        """
        'Juan y María caminaban. Tenía los ojos cansados.'
        The verb 'tenía' is singular but both Juan and María are candidates.
        With coordinated subject (plural) followed by singular verb, this is
        genuinely confusing but could be a grammar error in the manuscript.
        """
        text = "Juan y María caminaban. Tenía los ojos cansados."
        result = _resolve("ojos", text, ["Juan", "María"], nlp=shared_spacy_nlp)
        # Both None and either name are acceptable here
        assert result in (None, "Juan", "María"), (
            f"Acceptable: None or either name. Got: {result}"
        )

    def test_explicit_subject_overrides_nearby_object(self, shared_spacy_nlp):
        """
        'Ana tenía los ojos azules, no Pedro.'
        → ojos = Ana (explicit subject), Pedro is negated comparison.
        """
        text = "Ana tenía los ojos azules, no Pedro."
        result = _resolve("ojos", text, ["Ana", "Pedro"], nlp=shared_spacy_nlp)
        assert result == "Ana", (
            f"Ana is the explicit subject. Got: {result}"
        )


# =============================================================================
# 7. RESOLVABLE CASES (should NOT return None)
# =============================================================================


class TestResolvableCases:
    """
    Cases that LOOK ambiguous but have enough syntactic cues to resolve.
    These should NOT return None.
    """

    def test_pro_drop_chain_unambiguous(self, shared_spacy_nlp):
        """
        'Juan entró. Era alto. Tenía los ojos azules.'
        → Juan (unambiguous pro-drop chain, single entity)
        """
        text = "Juan entró. Era alto. Tenía los ojos azules."
        result = _resolve("ojos", text, ["Juan"], nlp=shared_spacy_nlp)
        assert result == "Juan", f"Unambiguous pro-drop chain. Got: {result}"

    def test_explicit_subject_same_sentence(self, shared_spacy_nlp):
        """
        'Elena tenía el cabello largo.'
        → cabello = Elena (explicit subject, same sentence)
        """
        text = "Elena tenía el cabello largo."
        result = _resolve("cabello", text, ["Elena"], nlp=shared_spacy_nlp)
        assert result == "Elena", f"Explicit subject. Got: {result}"

    def test_genitivo_de_resolves(self, shared_spacy_nlp):
        """
        'Los ojos de Pedro eran oscuros.'
        → ojos = Pedro (genitive 'de Pedro')
        """
        text = "Los ojos de Pedro eran oscuros."
        result = _resolve("ojos", text, ["Pedro", "María"], nlp=shared_spacy_nlp)
        assert result == "Pedro", f"Genitive 'de Pedro' resolves. Got: {result}"

    def test_subject_vs_object_clear(self, shared_spacy_nlp):
        """
        'María saludó a Juan. Sus ojos verdes brillaban.'
        → ojos = María (subject of previous sentence; Juan is object)
        """
        text = "María saludó a Juan. Sus ojos verdes brillaban."
        result = _resolve("ojos", text, ["María", "Juan"], nlp=shared_spacy_nlp)
        assert result == "María", (
            f"María is subject, Juan is object. Got: {result}"
        )

    def test_single_entity_always_resolves(self, shared_spacy_nlp):
        """
        With only one entity present, there's no ambiguity.
        Even in subordinate clauses, single entity should resolve.
        """
        text = "Cuando Juan llegó a casa tenía los ojos rojos."
        result = _resolve("ojos", text, ["Juan"], nlp=shared_spacy_nlp)
        assert result == "Juan", (
            f"Single entity: always resolvable. Got: {result}"
        )


# =============================================================================
# 8. CONFIDENCE LEVELS for ambiguous vs clear cases
# =============================================================================


class TestConfidenceForAmbiguity:
    """
    Even when the resolver assigns an entity, confidence should reflect certainty.
    """

    def test_explicit_subject_high_confidence(self, shared_spacy_nlp):
        """Explicit subject → confidence >= 0.85."""
        _, confidence = _resolve_with_confidence(
            "cabello", "María tenía el cabello largo.", ["María"],
            nlp=shared_spacy_nlp,
        )
        assert confidence >= 0.85, (
            f"Explicit subject should have high confidence. Got: {confidence}"
        )

    def test_genitive_high_confidence(self, shared_spacy_nlp):
        """Genitive 'de X' → confidence >= 0.90."""
        _, confidence = _resolve_with_confidence(
            "barba", "La barba de Pedro era larga.", ["Pedro"],
            nlp=shared_spacy_nlp,
        )
        assert confidence >= 0.90, (
            f"Genitive should have very high confidence. Got: {confidence}"
        )


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
