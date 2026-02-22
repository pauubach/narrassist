"""
Tests unitarios para pro_drop_scorer.py (BK-13).

Verifica el scoring de ambigüedad para resolución de sujetos omitidos
(pro-drop) en español.
"""

import pytest

from narrative_assistant.nlp.coreference_resolver import Gender, Mention, MentionType, Number
from narrative_assistant.nlp.pro_drop_scorer import (
    CandidateScore,
    ProDropAmbiguityScorer,
    SaliencyTracker,
)

# ── Helpers ──────────────────────────────────────────────────────────────


def _make_mention(
    text: str,
    start: int,
    end: int,
    mtype: MentionType = MentionType.PROPER_NOUN,
    gender: Gender = Gender.UNKNOWN,
    number: Number = Number.SINGULAR,
    sentence_idx: int = 0,
) -> Mention:
    return Mention(
        text=text,
        start_char=start,
        end_char=end,
        mention_type=mtype,
        gender=gender,
        number=number,
        sentence_idx=sentence_idx,
    )


# ── SaliencyTracker ─────────────────────────────────────────────────────


class TestSaliencyTracker:
    def test_build_from_mentions(self):
        """build_from_mentions cuenta menciones y posiciones correctamente."""
        mentions = [
            _make_mention("Juan", 0, 4),
            _make_mention("Juan", 50, 54),
            _make_mention("María", 20, 25),
        ]
        tracker = SaliencyTracker.build_from_mentions(mentions, text_length=100)

        assert tracker._entries["juan"].mention_count == 2
        assert tracker._entries["juan"].last_position == 50
        assert tracker._entries["maría"].mention_count == 1

    def test_saliency_high_frequency(self):
        """Entidad con muchas menciones tiene saliencia alta."""
        tracker = SaliencyTracker()
        for i in range(10):
            tracker.update("juan", position=i * 10, is_subject=False)
        tracker.update("maría", position=5, is_subject=False)

        assert tracker.get_saliency("juan") > tracker.get_saliency("maría")
        assert tracker.get_saliency("juan") > 0.5

    def test_recency_close(self):
        """Mención reciente tiene score de recencia alto."""
        tracker = SaliencyTracker()
        tracker.update("juan", position=490, is_subject=False)
        tracker.update("maría", position=100, is_subject=False)

        recency_juan = tracker.get_recency("juan", current_pos=500)
        recency_maria = tracker.get_recency("maría", current_pos=500)

        assert recency_juan > recency_maria
        assert recency_juan > 0.9


# ── ProDropAmbiguityScorer ───────────────────────────────────────────────


class TestProDropAmbiguityScorer:
    @pytest.fixture
    def scorer(self):
        return ProDropAmbiguityScorer()

    def test_single_candidate_no_ambiguity(self, scorer):
        """Un solo candidato → ambigüedad = 0.0."""
        zero = _make_mention(
            "[PRO salió]",
            100,
            105,
            MentionType.ZERO,
            gender=Gender.MASCULINE,
            sentence_idx=5,
        )
        candidate = _make_mention(
            "Juan",
            50,
            54,
            gender=Gender.MASCULINE,
            sentence_idx=4,
        )
        tracker = SaliencyTracker()
        tracker.update("juan", 50, is_subject=True)

        scores = scorer.score_candidates(zero, [candidate], tracker, "x" * 200)
        ambiguity = ProDropAmbiguityScorer.calculate_ambiguity(scores)

        assert ambiguity == 0.0

    def test_two_candidates_same_gender_high_ambiguity(self, scorer):
        """Dos candidatos masculinos cercanos → ambigüedad alta."""
        zero = _make_mention(
            "[PRO salió]",
            100,
            105,
            MentionType.ZERO,
            gender=Gender.MASCULINE,
            sentence_idx=5,
        )
        c1 = _make_mention(
            "Juan",
            60,
            64,
            gender=Gender.MASCULINE,
            sentence_idx=4,
        )
        c2 = _make_mention(
            "Pedro",
            55,
            60,
            gender=Gender.MASCULINE,
            sentence_idx=4,
        )
        tracker = SaliencyTracker()
        tracker.update("juan", 60, is_subject=True)
        tracker.update("pedro", 55, is_subject=True)

        scores = scorer.score_candidates(zero, [c1, c2], tracker, "x" * 200)
        ambiguity = ProDropAmbiguityScorer.calculate_ambiguity(scores)

        assert ambiguity > 0.5, f"Ambigüedad esperada > 0.5, obtenida {ambiguity}"

    def test_gender_mismatch_low_ambiguity(self, scorer):
        """'salió cansada' + 1 masculino + 1 femenina → ambigüedad más baja que mismo género."""
        zero = _make_mention(
            "[PRO salió]",
            100,
            105,
            MentionType.ZERO,
            gender=Gender.FEMININE,
            sentence_idx=5,
        )
        male = _make_mention(
            "Juan",
            60,
            64,
            gender=Gender.MASCULINE,
            sentence_idx=4,
        )
        female = _make_mention(
            "María",
            55,
            60,
            gender=Gender.FEMININE,
            sentence_idx=4,
        )
        tracker = SaliencyTracker()
        tracker.update("juan", 60, is_subject=True)
        tracker.update("maría", 55, is_subject=True)

        scores = scorer.score_candidates(zero, [male, female], tracker, "x" * 200)
        ambiguity = ProDropAmbiguityScorer.calculate_ambiguity(scores)

        # La femenina debería ganar
        assert scores[0].mention.text == "María"
        # El factor de género debe ser discriminante
        maria_score = next(s for s in scores if s.mention.text == "María")
        juan_score = next(s for s in scores if s.mention.text == "Juan")
        assert maria_score.factors["gender"] == 1.0
        assert juan_score.factors["gender"] == 0.0
        # Ambigüedad menor que con dos candidatos del mismo género
        assert ambiguity < 0.95

    def test_discourse_subject_bonus(self, scorer):
        """Sujeto de oración anterior recibe bonus discursivo."""
        zero = _make_mention(
            "[PRO corrió]",
            200,
            206,
            MentionType.ZERO,
            gender=Gender.UNKNOWN,
            sentence_idx=3,
        )
        # Candidato en oración anterior (sentence_idx=2)
        prev_subj = _make_mention(
            "Ana",
            150,
            153,
            gender=Gender.UNKNOWN,
            sentence_idx=2,
        )
        # Candidato lejano (sentence_idx=0)
        far = _make_mention(
            "Luis",
            10,
            14,
            gender=Gender.UNKNOWN,
            sentence_idx=0,
        )
        tracker = SaliencyTracker()
        tracker.update("ana", 150, is_subject=True)
        tracker.update("luis", 10, is_subject=True)

        scores = scorer.score_candidates(zero, [prev_subj, far], tracker, "x" * 300)

        # Ana (oración anterior) debería tener mayor score
        assert scores[0].mention.text == "Ana"
        assert scores[0].factors["discourse"] > scores[1].factors["discourse"]

    def test_number_agreement(self, scorer):
        """Verbo plural + candidato singular → penalizado."""
        zero = _make_mention(
            "[PRO salieron]",
            100,
            108,
            MentionType.ZERO,
            gender=Gender.UNKNOWN,
            number=Number.PLURAL,
            sentence_idx=5,
        )
        singular = _make_mention(
            "Juan",
            60,
            64,
            number=Number.SINGULAR,
            sentence_idx=4,
        )
        plural = _make_mention(
            "Los hermanos",
            50,
            63,
            number=Number.PLURAL,
            sentence_idx=4,
        )
        tracker = SaliencyTracker()
        tracker.update("juan", 60, is_subject=False)
        tracker.update("los hermanos", 50, is_subject=False)

        scores = scorer.score_candidates(zero, [singular, plural], tracker, "x" * 200)

        # El plural debería tener mejor score en number
        plural_score = next(s for s in scores if s.mention.text == "Los hermanos")
        singular_score = next(s for s in scores if s.mention.text == "Juan")

        assert plural_score.factors["number"] > singular_score.factors["number"]


# ── Integration ──────────────────────────────────────────────────────────


class TestProDropIntegration:
    def test_impersonal_se_not_zero(self):
        """'Se vende casa' no se extrae como ZERO (guard de regresión)."""
        # Verifica que MentionType.ZERO no captura impersonales con "se"
        # CorefMentionExtractionMixin es un mixin usado por el resolver
        from narrative_assistant.nlp.coreference_resolver import (
            CorefConfig,
            CoreferenceVotingResolver,
            CorefMethod,
        )

        config = CorefConfig(
            enabled_methods=[CorefMethod.HEURISTICS],
            min_confidence=0.1,
        )
        resolver = CoreferenceVotingResolver(config)
        text = "Se vende casa en el centro."
        result = resolver.resolve_document(text)

        # "Se vende" tiene sujeto explícito ("se"), no debería generar ZERO para "vende"
        zero_mentions = [
            m
            for chain in result.chains
            for m in chain.mentions
            if m.mention_type == MentionType.ZERO and "vende" in m.text
        ]
        assert len(zero_mentions) == 0, "'Se vende' no debería generar mención ZERO"

    def test_heuristics_uses_saliency_tracker(self):
        """HeuristicsCorefMethod con SaliencyTracker produce ranking diferente."""
        from narrative_assistant.nlp.coreference_resolver import HeuristicsCorefMethod

        method = HeuristicsCorefMethod()

        # Crear menciones: Juan aparece mucho, Pedro poco
        mentions = [_make_mention("Juan", i * 20, i * 20 + 4) for i in range(8)] + [
            _make_mention("Pedro", 180, 185)
        ]

        method.set_mention_frequencies(mentions)

        # Verificar que el tracker se construyó
        assert method._saliency_tracker is not None
        assert method._pro_drop_scorer is not None

        # El tracker debería tener saliencia mayor para Juan
        juan_sal = method._saliency_tracker.get_saliency("juan")
        pedro_sal = method._saliency_tracker.get_saliency("pedro")
        assert juan_sal > pedro_sal

        # Resolver un ZERO: el scorer debería usar factores multi-dimensionales
        zero = _make_mention(
            "[PRO salió]",
            200,
            206,
            MentionType.ZERO,
            gender=Gender.MASCULINE,
            sentence_idx=10,
        )
        c_juan = _make_mention(
            "Juan",
            160,
            164,
            gender=Gender.MASCULINE,
            sentence_idx=9,
        )
        c_pedro = _make_mention(
            "Pedro",
            180,
            185,
            gender=Gender.MASCULINE,
            sentence_idx=9,
        )

        results = method.resolve(zero, [c_juan, c_pedro], "contexto de prueba" * 20)

        # Debe retornar resultados para ambos candidatos
        assert len(results) == 2
        # Los resultados deben ser tuplas (Mention, float, str)
        assert all(len(r) == 3 for r in results)


# ── Cross-sentence continuity (T1+T2 en recency) ─────────────────────


class TestRecencyContinuitySignal:
    """Verifica que _score_recency usa T1+T2 para mejorar scoring cross-sentence."""

    @pytest.fixture
    def scorer(self):
        return ProDropAmbiguityScorer()

    def test_gerund_boosts_recency(self, scorer):
        """Gerundio al inicio de oración siguiente sube recency del candidato previo."""
        # "Juan habló con María. Aprovechando la situación, decidió actuar."
        text = "Juan habló con María. Aprovechando la situación, decidió actuar."
        zero = _make_mention("[PRO decidió]", 50, 57, MentionType.ZERO, sentence_idx=1)
        candidate = _make_mention("Juan", 0, 4, sentence_idx=0)

        # Score con texto real (tiene gerundio → boost)
        recency_with_signal = scorer._score_recency(zero, candidate, len(text), text)

        # Score sin texto (sin boost, solo distancia)
        recency_no_text = scorer._score_recency(zero, candidate, len(text), "")

        assert recency_with_signal > recency_no_text

    def test_causal_boosts_recency(self, scorer):
        """Conector causal 'porque' sube recency del candidato previo."""
        text = "Pedro salió corriendo. Porque estaba asustado, no miró atrás."
        zero = _make_mention("[PRO estaba]", 32, 38, MentionType.ZERO, sentence_idx=1)
        candidate = _make_mention("Pedro", 0, 5, sentence_idx=0)

        recency_with = scorer._score_recency(zero, candidate, len(text), text)
        recency_without = scorer._score_recency(zero, candidate, len(text), "")

        assert recency_with > recency_without

    def test_no_signal_no_boost(self, scorer):
        """Sin señal de continuidad, no hay boost."""
        text = "Juan caminaba por la calle. El cielo estaba nublado."
        zero = _make_mention("[PRO estaba]", 35, 41, MentionType.ZERO, sentence_idx=1)
        candidate = _make_mention("Juan", 0, 4, sentence_idx=0)

        recency_with = scorer._score_recency(zero, candidate, len(text), text)
        recency_without = scorer._score_recency(zero, candidate, len(text), "")

        # Sin señal de continuidad → scores iguales
        assert abs(recency_with - recency_without) < 0.01

    def test_abbreviation_doesnt_inflate_distance(self, scorer):
        """'Dr.' no debe crear un break falso que reduzca recency."""
        text = "El Dr. García examinó al paciente. Tenía fiebre alta."
        zero = _make_mention("[PRO Tenía]", 35, 40, MentionType.ZERO, sentence_idx=1)
        # "Dr. García" es un solo entity — el "Dr." no crea break extra
        candidate = _make_mention("García", 7, 13, sentence_idx=0)

        recency = scorer._score_recency(zero, candidate, len(text), text)
        # Solo 1 break real (el punto final de "paciente."), no 2
        assert recency > 0.0
