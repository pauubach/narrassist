"""Tests para el modulo de analisis de registro."""

from unittest.mock import MagicMock, patch

import pytest

from narrative_assistant.voice.register import (
    COLLOQUIAL_INDICATORS,
    CONTEXTUAL_COLLOQUIAL_PATTERNS,
    FORMAL_INDICATORS,
    MIN_COLLOQUIAL_INDICATORS,
    MIN_FORMAL_INDICATORS,
    RegisterAnalysis,
    RegisterAnalyzer,
    RegisterChange,
    RegisterChangeDetector,
    RegisterType,
    analyze_register_changes,
)

# ============================================================================
# Tests para RegisterAnalyzer
# ============================================================================


class TestRegisterAnalyzer:
    """Tests para RegisterAnalyzer."""

    def test_init(self):
        """Test inicializacion del analizador."""
        analyzer = RegisterAnalyzer()
        assert analyzer.formal_set
        assert analyzer.colloquial_set
        assert len(analyzer.technical_patterns) > 0
        assert len(analyzer.poetic_patterns) > 0

    def test_analyze_empty_text(self):
        """Test analisis de texto vacio."""
        analyzer = RegisterAnalyzer()
        result = analyzer.analyze_segment("", 1, 0)

        assert result.primary_register == RegisterType.NEUTRAL
        assert result.confidence == 0.0

    def test_analyze_formal_text(self):
        """Test deteccion de registro formal."""
        analyzer = RegisterAnalyzer()
        text = (
            "Contempló la vastedad del horizonte mientras la melancolía "
            "se apoderaba de su alma. No obstante, mantuvo la compostura. "
            "Asimismo, percibió que el transcurrir del tiempo era inexorable."
        )
        result = analyzer.analyze_segment(text, 1, 0)

        assert result.primary_register == RegisterType.FORMAL_LITERARY
        assert len(result.formal_indicators) >= 3
        assert result.confidence > 0.3

    def test_analyze_colloquial_text(self):
        """Test deteccion de registro coloquial."""
        analyzer = RegisterAnalyzer()
        text = (
            "Bro, eso mola mogollon. Es flipante guay, chaval. "
            "Tope chungo el colega ese, mazo de flipando."
        )
        result = analyzer.analyze_segment(text, 1, 0)

        assert result.primary_register == RegisterType.COLLOQUIAL
        assert len(result.colloquial_indicators) >= 2
        assert result.confidence > 0.3

    def test_analyze_technical_text(self):
        """Test deteccion de registro tecnico."""
        analyzer = RegisterAnalyzer()
        text = (
            "El diagnostico revelaba una patologia compleja. "
            "La etiologia permanecia indeterminada y el pronostico era reservado. "
            "Se requeria una intervencion quirurgica de urgencia."
        )
        result = analyzer.analyze_segment(text, 1, 0)

        assert result.primary_register == RegisterType.TECHNICAL
        assert len(result.technical_terms) >= 2

    def test_analyze_poetic_text(self):
        """Test deteccion de registro poetico."""
        analyzer = RegisterAnalyzer()
        text = (
            "El cielo sangraba carmesi mientras la luna danzaba "
            "entre las nubes eternas. El viento susurraba "
            "como una brisa de cristal en la eternidad."
        )
        result = analyzer.analyze_segment(text, 1, 0)

        assert result.primary_register == RegisterType.POETIC
        assert len(result.poetic_devices) >= 1

    def test_analyze_neutral_text(self):
        """Test deteccion de registro neutral."""
        analyzer = RegisterAnalyzer()
        text = (
            "Juan entro en la habitacion. Miro a su alrededor. "
            "Habia una mesa y dos sillas. Se sento y espero."
        )
        result = analyzer.analyze_segment(text, 1, 0)

        assert result.primary_register == RegisterType.NEUTRAL

    def test_analyze_dialogue_flag(self):
        """Test que el flag de dialogo se preserva."""
        analyzer = RegisterAnalyzer()

        result_narration = analyzer.analyze_segment("Texto de prueba", 1, 0, is_dialogue=False)
        result_dialogue = analyzer.analyze_segment("Texto de prueba", 1, 0, is_dialogue=True)

        assert result_narration.is_dialogue is False
        assert result_dialogue.is_dialogue is True

    def test_register_scores_sum_to_one(self):
        """Test que los scores suman aproximadamente 1."""
        analyzer = RegisterAnalyzer()
        text = "Un texto cualquiera para analizar el registro narrativo."
        result = analyzer.analyze_segment(text, 1, 0)

        total = sum(result.register_scores.values())
        assert 0.99 <= total <= 1.01  # Tolerance for floating point


# ============================================================================
# Tests de falsos positivos (regresion)
# ============================================================================


class TestFalsePositiveRegression:
    """Tests de regresion para falsos positivos conocidos."""

    def test_sus_not_colloquial(self):
        """'sus' (pronombre posesivo) NO debe ser indicador coloquial."""
        assert "sus" not in COLLOQUIAL_INDICATORS

        analyzer = RegisterAnalyzer()
        text = "Sus ojos azules brillaban con la luz del amanecer. Sus manos temblaban."
        result = analyzer.analyze_segment(text, 1, 0)

        assert result.primary_register == RegisterType.NEUTRAL
        assert "sus" not in result.colloquial_indicators

    def test_fuerte_not_colloquial(self):
        """'fuerte' (adjetivo estándar) NO debe ser indicador coloquial."""
        assert "fuerte" not in COLLOQUIAL_INDICATORS

        analyzer = RegisterAnalyzer()
        text = "Era un hombre fuerte, con brazos de hierro. Su voz fuerte resonaba."
        result = analyzer.analyze_segment(text, 1, 0)

        assert "fuerte" not in result.colloquial_indicators

    def test_plan_not_colloquial(self):
        """'plan' (sustantivo estándar) NO debe ser indicador coloquial."""
        assert "plan" not in COLLOQUIAL_INDICATORS

    def test_brutal_not_colloquial(self):
        """'brutal' (adjetivo estándar) NO debe ser indicador coloquial."""
        assert "brutal" not in COLLOQUIAL_INDICATORS

    def test_rato_not_colloquial(self):
        """'rato' (temporal estándar) NO debe ser indicador coloquial."""
        assert "rato" not in COLLOQUIAL_INDICATORS

    def test_locura_not_colloquial(self):
        """'locura' (sustantivo estándar) NO debe ser indicador coloquial."""
        assert "locura" not in COLLOQUIAL_INDICATORS

    def test_single_indicator_stays_neutral(self):
        """Un solo indicador coloquial no debe cambiar el registro."""
        analyzer = RegisterAnalyzer()
        # Solo "mola" como indicador, insuficiente (MIN_COLLOQUIAL_INDICATORS = 2)
        text = "Eso mola, pero el resto de la oración es completamente normal y estándar."
        result = analyzer.analyze_segment(text, 1, 0)

        assert result.primary_register == RegisterType.NEUTRAL

    def test_multiple_indicators_detects_colloquial(self):
        """Multiples indicadores coloquiales SI deben detectar el registro."""
        analyzer = RegisterAnalyzer()
        text = "Mola mogollon, chaval, es flipante lo guay que es."
        result = analyzer.analyze_segment(text, 1, 0)

        assert result.primary_register == RegisterType.COLLOQUIAL
        assert len(result.colloquial_indicators) >= MIN_COLLOQUIAL_INDICATORS

    def test_poetic_pattern_no_trivial_possessives(self):
        """Patron poetico NO debe capturar comparaciones triviales."""
        analyzer = RegisterAnalyzer()
        text = "Los libros, como los de mi abuelo, estaban viejos."
        result = analyzer.analyze_segment(text, 1, 0)

        assert len(result.poetic_devices) == 0

    def test_poetic_pattern_matches_real_simile(self):
        """Patron poetico SI debe capturar similes elaborados."""
        analyzer = RegisterAnalyzer()
        text = "Brillaba como una estrella de diamante en la noche oscura."
        result = analyzer.analyze_segment(text, 1, 0)

        assert len(result.poetic_devices) >= 1

    def test_test_document_rich_no_false_positives(self):
        """El test_document_rich no debe generar cambios de registro."""
        try:
            with open("test_books/test_documents/test_document_rich.txt", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip("test_document_rich.txt not available")

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        segments = []
        current_pos = 0
        for para in paragraphs:
            is_dialogue = para.startswith(("\u2014", "-", "\u00ab", '"', "'"))
            if len(para) > 50:
                segments.append((para, 1, current_pos, is_dialogue))
            current_pos += len(para) + 2

        detector = RegisterChangeDetector()
        detector.analyze_document(segments)
        changes = detector.detect_changes(min_severity="medium")

        # Texto neutral simple no debe generar cambios
        assert len(changes) == 0, (
            f"Se detectaron {len(changes)} cambios falsos: "
            + ", ".join(f"{c.from_register.value}->{c.to_register.value}" for c in changes)
        )


# ============================================================================
# Tests para RegisterChangeDetector
# ============================================================================


class TestRegisterChangeDetector:
    """Tests para RegisterChangeDetector."""

    def test_init(self):
        """Test inicializacion del detector."""
        detector = RegisterChangeDetector()
        assert detector.analyzer is not None
        assert detector.analyses == []

    def test_init_with_custom_analyzer(self):
        """Test inicializacion con analizador personalizado."""
        analyzer = RegisterAnalyzer()
        detector = RegisterChangeDetector(analyzer)
        assert detector.analyzer is analyzer

    def test_analyze_document(self):
        """Test analisis de documento completo."""
        detector = RegisterChangeDetector()
        segments = [
            ("Primer segmento de texto.", 1, 0, False),
            ("Segundo segmento de texto.", 1, 100, False),
            ("Dialogo del personaje.", 1, 200, True),
        ]

        analyses = detector.analyze_document(segments)

        assert len(analyses) == 3
        assert analyses[2].is_dialogue is True

    def test_detect_high_severity_change(self):
        """Test deteccion de cambio de alta severidad."""
        detector = RegisterChangeDetector()
        segments = [
            # Formal/literario (multiples indicadores)
            (
                "Contempló la vastedad del horizonte mientras la melancolía "
                "se apoderaba de su alma. No obstante, mantuvo la compostura. "
                "Asimismo, percibió que el transcurrir era inexorable.",
                1,
                0,
                False,
            ),
            # Coloquial con multiples indicadores inequivocos
            (
                "Bro, eso mola mogollon, es flipante guay chaval. "
                "Tope chungo colega, mazo flipando tronco.",
                1,
                500,
                False,
            ),
        ]

        detector.analyze_document(segments)
        changes = detector.detect_changes(min_severity="high")

        assert len(changes) >= 1
        assert changes[0].severity == "high"
        assert changes[0].from_register == RegisterType.FORMAL_LITERARY
        assert changes[0].to_register == RegisterType.COLLOQUIAL

    def test_detect_medium_severity_change(self):
        """Test deteccion de cambio de severidad media."""
        detector = RegisterChangeDetector()
        segments = [
            ("Un texto neutral sin marcadores especificos de ningun tipo.", 1, 0, False),
            ("Bro mola mogollon flipante guay chaval tope chungo.", 1, 100, False),
        ]

        detector.analyze_document(segments)
        changes = detector.detect_changes(min_severity="medium")

        assert len(changes) >= 1

    def test_dialogue_excluded_from_changes(self):
        """Test que dialogos no generan cambios de registro."""
        detector = RegisterChangeDetector()
        segments = [
            ("Contempló la vastedad del horizonte asimismo.", 1, 0, False),
            ("Bro, mola mogollon chaval!", 1, 100, True),  # Dialogo
            ("Percibió que el transcurrir era inexorable.", 1, 200, False),
        ]

        detector.analyze_document(segments)
        changes = detector.detect_changes(min_severity="low")

        # No debe detectar cambio porque el coloquial es dialogo
        high_changes = [c for c in changes if c.severity == "high"]
        assert len(high_changes) == 0

    def test_no_changes_same_register(self):
        """Test sin cambios cuando registro es consistente."""
        detector = RegisterChangeDetector()
        segments = [
            ("Contempló la vastedad del horizonte asimismo.", 1, 0, False),
            ("Percibió la magnanimidad del acontecer no obstante.", 1, 100, False),
            ("Observó el transcurrir sempiterno en consecuencia.", 1, 200, False),
        ]

        detector.analyze_document(segments)
        changes = detector.detect_changes(min_severity="low")

        # Todos son formales, no hay cambios
        assert len(changes) == 0

    def test_get_register_distribution(self):
        """Test distribucion de registros."""
        detector = RegisterChangeDetector()
        segments = [
            ("Contempló la vastedad asimismo.", 1, 0, False),
            ("Contempló el horizonte no obstante.", 1, 100, False),
            ("Texto neutral simple.", 2, 0, False),
        ]

        detector.analyze_document(segments)
        distribution = detector.get_register_distribution()

        assert isinstance(distribution, dict)
        assert RegisterType.FORMAL_LITERARY in distribution

    def test_get_summary(self):
        """Test resumen del analisis."""
        detector = RegisterChangeDetector()
        segments = [
            ("Texto de narracion.", 1, 0, False),
            ("Dialogo del personaje.", 1, 100, True),
            ("Mas narracion.", 1, 200, False),
        ]

        detector.analyze_document(segments)
        summary = detector.get_summary()

        assert summary["total_segments"] == 3
        assert summary["narrative_segments"] == 2
        assert summary["dialogue_segments"] == 1
        assert "distribution" in summary
        assert "dominant_register" in summary

    def test_empty_document(self):
        """Test documento vacio."""
        detector = RegisterChangeDetector()

        analyses = detector.analyze_document([])
        changes = detector.detect_changes()
        summary = detector.get_summary()

        assert len(analyses) == 0
        assert len(changes) == 0
        assert summary["total_segments"] == 0


# ============================================================================
# Tests para RegisterAnalysis dataclass
# ============================================================================


class TestRegisterAnalysis:
    """Tests para RegisterAnalysis."""

    def test_to_dict(self):
        """Test conversion a diccionario."""
        analysis = RegisterAnalysis(
            text_segment="Texto de prueba",
            chapter=1,
            position=0,
            is_dialogue=False,
            primary_register=RegisterType.FORMAL_LITERARY,
            register_scores={r: 0.2 for r in RegisterType},
            confidence=0.5,
            formal_indicators=["contemplar"],
            colloquial_indicators=[],
            technical_terms=[],
            poetic_devices=[],
        )

        d = analysis.to_dict()

        assert d["chapter"] == 1
        assert d["primary_register"] == "formal_literary"
        assert "formal_literary" in d["register_scores"]


# ============================================================================
# Tests para RegisterChange dataclass
# ============================================================================


class TestRegisterChange:
    """Tests para RegisterChange."""

    def test_to_dict(self):
        """Test conversion a diccionario."""
        change = RegisterChange(
            from_register=RegisterType.FORMAL_LITERARY,
            to_register=RegisterType.COLLOQUIAL,
            chapter=1,
            position=100,
            context_before="Texto formal",
            context_after="Texto coloquial",
            severity="high",
            explanation="Cambio de registro",
        )

        d = change.to_dict()

        assert d["from_register"] == "formal_literary"
        assert d["to_register"] == "colloquial"
        assert d["severity"] == "high"


# ============================================================================
# Tests para funcion de conveniencia
# ============================================================================


class TestAnalyzeRegisterChanges:
    """Tests para analyze_register_changes."""

    def test_basic_usage(self):
        """Test uso basico de la funcion."""
        segments = [
            ("Contempló la vastedad asimismo no obstante inexorable.", 1, 0, False),
            ("Mola mogollon chaval flipante guay tope chungo colega.", 1, 100, False),
        ]

        analyses, changes = analyze_register_changes(segments)

        assert len(analyses) == 2
        assert len(changes) >= 1


# ============================================================================
# Tests de integracion
# ============================================================================


class TestRegisterIntegration:
    """Tests de integracion del sistema de registro."""

    def test_full_document_analysis(self):
        """Test analisis completo de documento con multiples registros."""
        detector = RegisterChangeDetector()

        segments = [
            # Cap 1: Formal literario
            (
                "Contempló la vastedad del horizonte mientras la melancolía "
                "se apoderaba de su alma. No obstante, mantuvo la compostura.",
                1,
                0,
                False,
            ),
            # Cap 1: Dialogo coloquial (no cuenta)
            ("\u2014Bro, mola mogollon esto, chaval flipante!", 1, 500, True),
            # Cap 2: Tecnico
            (
                "El diagnóstico revelaba una patología compleja. "
                "La etiología permanecía indeterminada.",
                2,
                0,
                False,
            ),
            # Cap 2: Poetico
            (
                "El cielo sangraba carmesi mientras la luna danzaba susurraba "
                "entre las nubes flotaba murmuraba.",
                2,
                300,
                False,
            ),
            # Cap 3: Formal otra vez
            (
                "Asimismo, percibió que el transcurrir del tiempo era inexorable. "
                "Por ende, decidió actuar no obstante.",
                3,
                0,
                False,
            ),
        ]

        analyses = detector.analyze_document(segments)
        changes = detector.detect_changes(min_severity="low")

        assert len(analyses) == 5

        # Debe haber cambios entre cap 1->2 y dentro de cap 2
        assert len(changes) >= 1

        # Verificar que el dialogo no esta en los cambios
        for change in changes:
            assert "Bro" not in change.context_before
            assert "Bro" not in change.context_after

    def test_register_consistency_check(self):
        """Test verificacion de consistencia de registro."""
        detector = RegisterChangeDetector()

        # Documento consistentemente formal
        segments = [
            ("Contempló la vastedad del horizonte asimismo.", 1, 0, False),
            ("Percibió la magnanimidad del acontecer no obstante.", 1, 100, False),
            ("Observó el transcurrir sempiterno en consecuencia.", 1, 200, False),
            ("Contempló nuevamente la vastedad por ende.", 1, 300, False),
        ]

        detector.analyze_document(segments)
        changes = detector.detect_changes(min_severity="low")

        # No debe haber cambios significativos
        assert len(changes) == 0

        # Todos deben ser formales
        for analysis in detector.analyses:
            assert analysis.primary_register == RegisterType.FORMAL_LITERARY

    def test_mixed_document_report(self):
        """Test reporte de documento mezclado."""
        detector = RegisterChangeDetector()

        segments = [
            ("Contempló la vastedad asimismo no obstante inexorable.", 1, 0, False),
            ("Bro mola mogollon flipante guay chaval tope chungo.", 1, 100, False),
            ("El diagnóstico revelaba una patología compleja.", 2, 0, False),
        ]

        detector.analyze_document(segments)
        summary = detector.get_summary()

        assert summary["total_segments"] == 3
        assert len(summary["distribution"]) >= 2


# ============================================================================
# Tests para deteccion contextual de palabras ambiguas
# ============================================================================


class TestContextualColloquialPatterns:
    """Tests para patrones contextuales de palabras ambiguas."""

    def test_fuerte_exclamation_is_colloquial(self):
        """'¡Qué fuerte!' debe detectarse como coloquial."""
        analyzer = RegisterAnalyzer()
        # Necesitamos al menos MIN_COLLOQUIAL_INDICATORS, así que añadimos otro inequívoco
        text = "¡Qué fuerte, bro! No me lo puedo creer, mola mogollon."
        result = analyzer.analyze_segment(text, 1, 0)
        assert "fuerte" in result.colloquial_indicators

    def test_fuerte_adjective_not_colloquial(self):
        """'hombre fuerte' NO debe detectarse como coloquial."""
        analyzer = RegisterAnalyzer()
        text = "Era un hombre fuerte que cargaba piedras todos los días."
        result = analyzer.analyze_segment(text, 1, 0)
        assert "fuerte" not in result.colloquial_indicators

    def test_brutal_exclamation_is_colloquial(self):
        """'Es brutal' como exclamación debe detectarse."""
        analyzer = RegisterAnalyzer()
        text = "¡Es brutal! Mola mogollon, chaval."
        result = analyzer.analyze_segment(text, 1, 0)
        assert "brutal" in result.colloquial_indicators

    def test_brutal_adjective_not_colloquial(self):
        """'ataque brutal' NO debe detectarse."""
        analyzer = RegisterAnalyzer()
        text = "Fue un ataque brutal que dejó secuelas permanentes."
        result = analyzer.analyze_segment(text, 1, 0)
        assert "brutal" not in result.colloquial_indicators

    def test_locura_exclamation_is_colloquial(self):
        """'¡Qué locura!' debe detectarse."""
        analyzer = RegisterAnalyzer()
        text = "¡Qué locura, bro! Flipante, mola mogollon."
        result = analyzer.analyze_segment(text, 1, 0)
        assert "locura" in result.colloquial_indicators

    def test_locura_standard_not_colloquial(self):
        """'la locura del rey' NO debe detectarse."""
        analyzer = RegisterAnalyzer()
        text = "La locura del rey llevó al país a la ruina."
        result = analyzer.analyze_segment(text, 1, 0)
        assert "locura" not in result.colloquial_indicators

    def test_pasada_exclamation_is_colloquial(self):
        """'¡Qué pasada!' debe detectarse."""
        analyzer = RegisterAnalyzer()
        text = "¡Qué pasada! Mola mogollon esto, chaval."
        result = analyzer.analyze_segment(text, 1, 0)
        assert "pasada" in result.colloquial_indicators

    def test_pasada_temporal_not_colloquial(self):
        """'la semana pasada' NO debe detectarse."""
        analyzer = RegisterAnalyzer()
        text = "La semana pasada fuimos al centro comercial."
        result = analyzer.analyze_segment(text, 1, 0)
        assert "pasada" not in result.colloquial_indicators

    def test_crack_praise_is_colloquial(self):
        """'eres un crack' debe detectarse."""
        analyzer = RegisterAnalyzer()
        text = "Eres un crack, bro. Mola mogollon lo que haces."
        result = analyzer.analyze_segment(text, 1, 0)
        assert "crack" in result.colloquial_indicators

    def test_crack_noun_not_colloquial(self):
        """'el crack del 29' NO debe detectarse."""
        analyzer = RegisterAnalyzer()
        text = "El crack bursátil de 1929 devastó la economía mundial."
        result = analyzer.analyze_segment(text, 1, 0)
        assert "crack" not in result.colloquial_indicators

    def test_rollo_exclamation_is_colloquial(self):
        """'qué rollo' debe detectarse."""
        analyzer = RegisterAnalyzer()
        text = "Qué rollo patatero, mola mogollon menos que ayer, chaval."
        result = analyzer.analyze_segment(text, 1, 0)
        assert "rollo" in result.colloquial_indicators

    def test_rollo_object_not_colloquial(self):
        """'rollo de papel' NO debe detectarse."""
        analyzer = RegisterAnalyzer()
        text = "Compró un rollo de papel higiénico en el supermercado."
        result = analyzer.analyze_segment(text, 1, 0)
        assert "rollo" not in result.colloquial_indicators

    def test_all_patterns_have_word_in_ambiguous_set(self):
        """Todas las palabras de patrones contextuales deben estar en _ambiguous_words."""
        analyzer = RegisterAnalyzer()
        for word, _ in CONTEXTUAL_COLLOQUIAL_PATTERNS:
            assert word in analyzer._ambiguous_words


# ============================================================================
# Tests para _extract_sentence
# ============================================================================


class TestExtractSentence:
    """Tests para el helper _extract_sentence."""

    def test_extracts_correct_sentence(self):
        """Debe extraer la oración que contiene la palabra."""
        text = "Primera oración aquí. La fuerte tormenta llegó. Tercera oración."
        result = RegisterAnalyzer._extract_sentence(text, "fuerte")
        assert result is not None
        assert "fuerte" in result.lower()

    def test_returns_none_for_missing_word(self):
        """Debe devolver None si la palabra no está en el texto."""
        text = "No hay nada relevante aquí."
        result = RegisterAnalyzer._extract_sentence(text, "fuerte")
        assert result is None

    def test_handles_exclamation_marks(self):
        """Debe manejar signos de exclamación como separadores."""
        text = "¡Qué fuerte! No me lo creo."
        result = RegisterAnalyzer._extract_sentence(text, "fuerte")
        assert result is not None
        assert "fuerte" in result.lower()


# ============================================================================
# Tests para LLM fallback
# ============================================================================


class TestLLMFallback:
    """Tests para el fallback LLM en palabras ambiguas."""

    def test_llm_fallback_disabled_by_default(self):
        """El fallback LLM debe estar desactivado por defecto."""
        analyzer = RegisterAnalyzer()
        assert analyzer._use_llm_fallback is False

    def test_llm_fallback_enabled_on_init(self):
        """El fallback LLM se activa al crearlo con use_llm_fallback=True."""
        analyzer = RegisterAnalyzer(use_llm_fallback=True)
        assert analyzer._use_llm_fallback is True

    @patch("narrative_assistant.voice.register.RegisterAnalyzer._check_ambiguous_word_llm")
    def test_llm_called_for_unresolved_ambiguous_word(self, mock_llm):
        """LLM se llama para palabras ambiguas que no matchean regex."""
        mock_llm.return_value = True  # LLM dice "es coloquial"
        analyzer = RegisterAnalyzer(use_llm_fallback=True)

        # "fuerte" aparece pero NO en contexto exclamativo → regex no matchea
        # Con LLM fallback activo, debe consultar al LLM
        text = "Eso fue algo muy fuerte para todos nosotros, mola mogollon."
        result = analyzer.analyze_segment(text, 1, 0)

        mock_llm.assert_called()
        # Verificar que se llamó con "fuerte" como argumento
        call_args = mock_llm.call_args_list
        fuerte_called = any(args[0][0] == "fuerte" for args in call_args)
        assert fuerte_called

    @patch("narrative_assistant.voice.register.RegisterAnalyzer._check_ambiguous_word_llm")
    def test_llm_not_called_when_regex_matches(self, mock_llm):
        """LLM NO se llama si el regex ya resolvió la palabra."""
        analyzer = RegisterAnalyzer(use_llm_fallback=True)

        # "¡Qué fuerte!" matchea el regex → no necesita LLM
        text = "¡Qué fuerte, mola mogollon esto chaval!"
        analyzer.analyze_segment(text, 1, 0)

        # Verificar que NO se llamó con "fuerte"
        for call in mock_llm.call_args_list:
            assert call[0][0] != "fuerte", "LLM should not be called for regex-resolved word"

    @patch("narrative_assistant.voice.register.RegisterAnalyzer._check_ambiguous_word_llm")
    def test_llm_not_called_when_disabled(self, mock_llm):
        """LLM NO se llama cuando use_llm_fallback=False."""
        analyzer = RegisterAnalyzer(use_llm_fallback=False)

        text = "Eso fue algo muy fuerte para todos."
        analyzer.analyze_segment(text, 1, 0)

        mock_llm.assert_not_called()

    @patch("narrative_assistant.voice.register.RegisterAnalyzer._check_ambiguous_word_llm")
    def test_llm_returns_none_word_ignored(self, mock_llm):
        """Si LLM devuelve None (no disponible), la palabra se ignora."""
        mock_llm.return_value = None
        analyzer = RegisterAnalyzer(use_llm_fallback=True)

        text = "Eso fue fuerte para todos."
        result = analyzer.analyze_segment(text, 1, 0)

        assert "fuerte" not in result.colloquial_indicators

    @patch("narrative_assistant.voice.register.RegisterAnalyzer._check_ambiguous_word_llm")
    def test_llm_returns_false_word_not_colloquial(self, mock_llm):
        """Si LLM dice 'no coloquial', la palabra se ignora."""
        mock_llm.return_value = False
        analyzer = RegisterAnalyzer(use_llm_fallback=True)

        text = "Era un hombre fuerte y valiente."
        result = analyzer.analyze_segment(text, 1, 0)

        assert "fuerte" not in result.colloquial_indicators

    def test_check_ambiguous_word_llm_cache(self):
        """El cache LLM evita llamadas duplicadas."""
        analyzer = RegisterAnalyzer(use_llm_fallback=True)

        # Pre-fill cache
        analyzer._llm_cache["fuerte:Era un hombre fuerte y valiente"] = False

        result = analyzer._check_ambiguous_word_llm("fuerte", "Era un hombre fuerte y valiente")
        assert result is False  # From cache, no LLM call

    @patch("narrative_assistant.llm.client.get_llm_client")
    def test_check_ambiguous_word_llm_unavailable(self, mock_get_client):
        """Si el LLM no está disponible, devuelve None."""
        mock_get_client.return_value = None
        analyzer = RegisterAnalyzer(use_llm_fallback=True)

        result = analyzer._check_ambiguous_word_llm("fuerte", "¡Qué fuerte tío!")

        # Should return None since client is None
        assert result is None
