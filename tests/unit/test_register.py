"""Tests para el modulo de analisis de registro."""

import pytest
from narrative_assistant.voice.register import (
    RegisterType,
    RegisterAnalysis,
    RegisterChange,
    RegisterAnalyzer,
    RegisterChangeDetector,
    FORMAL_INDICATORS,
    COLLOQUIAL_INDICATORS,
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
            "Bro, eso mola mogollon. Es una pasada guay, chaval. "
            "Flipante el crack ese, tiene un flow brutal."
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
            "entre las nubes eternas. El viento susurraba murmuraba "
            "danzaba flotaba como gotas de rocio del eterno amanecer."
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
            # Formal/literario
            ("Contempló la vastedad del horizonte mientras la melancolía "
             "se apoderaba de su alma. No obstante, mantuvo la compostura. "
             "Asimismo, percibió que el transcurrir era inexorable.", 1, 0, False),
            # Coloquial con lenguaje juvenil
            ("Bro, eso mola mogollon, es una pasada guay chaval. "
             "Flipante crack, tiene un flow brutal.", 1, 500, False),
        ]

        detector.analyze_document(segments)
        changes = detector.detect_changes(min_severity='high')

        assert len(changes) >= 1
        assert changes[0].severity == 'high'
        assert changes[0].from_register == RegisterType.FORMAL_LITERARY
        assert changes[0].to_register == RegisterType.COLLOQUIAL

    def test_detect_medium_severity_change(self):
        """Test deteccion de cambio de severidad media."""
        detector = RegisterChangeDetector()
        segments = [
            ("Un texto neutral sin marcadores especificos de ningun tipo.", 1, 0, False),
            ("Bro flipaba mogollon con la movida guay chaval crack.", 1, 100, False),
        ]

        detector.analyze_document(segments)
        changes = detector.detect_changes(min_severity='medium')

        assert len(changes) >= 1

    def test_dialogue_excluded_from_changes(self):
        """Test que dialogos no generan cambios de registro."""
        detector = RegisterChangeDetector()
        segments = [
            ("Contempló la vastedad del horizonte asimismo.", 1, 0, False),
            ("Bro, mola mogollon crack!", 1, 100, True),  # Dialogo
            ("Percibió que el transcurrir era inexorable.", 1, 200, False),
        ]

        detector.analyze_document(segments)
        changes = detector.detect_changes(min_severity='low')

        # No debe detectar cambio porque el coloquial es dialogo
        high_changes = [c for c in changes if c.severity == 'high']
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
        changes = detector.detect_changes(min_severity='low')

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

        assert summary['total_segments'] == 3
        assert summary['narrative_segments'] == 2
        assert summary['dialogue_segments'] == 1
        assert 'distribution' in summary
        assert 'dominant_register' in summary

    def test_empty_document(self):
        """Test documento vacio."""
        detector = RegisterChangeDetector()

        analyses = detector.analyze_document([])
        changes = detector.detect_changes()
        summary = detector.get_summary()

        assert len(analyses) == 0
        assert len(changes) == 0
        assert summary['total_segments'] == 0


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
            formal_indicators=['contemplar'],
            colloquial_indicators=[],
            technical_terms=[],
            poetic_devices=[]
        )

        d = analysis.to_dict()

        assert d['chapter'] == 1
        assert d['primary_register'] == 'formal_literary'
        assert 'formal_literary' in d['register_scores']


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
            severity='high',
            explanation="Cambio de registro"
        )

        d = change.to_dict()

        assert d['from_register'] == 'formal_literary'
        assert d['to_register'] == 'colloquial'
        assert d['severity'] == 'high'


# ============================================================================
# Tests para funcion de conveniencia
# ============================================================================

class TestAnalyzeRegisterChanges:
    """Tests para analyze_register_changes."""

    def test_basic_usage(self):
        """Test uso basico de la funcion."""
        segments = [
            ("Contempló la vastedad asimismo no obstante.", 1, 0, False),
            ("El tio flipaba mogollon con la movida guay.", 1, 100, False),
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
            ("Contempló la vastedad del horizonte mientras la melancolía "
             "se apoderaba de su alma. No obstante, mantuvo la compostura.", 1, 0, False),

            # Cap 1: Dialogo coloquial (no cuenta)
            ("—Bro, mola mogollon esto, chaval crack!", 1, 500, True),

            # Cap 2: Tecnico
            ("El diagnóstico revelaba una patología compleja. "
             "La etiología permanecía indeterminada.", 2, 0, False),

            # Cap 2: Poetico
            ("El cielo sangraba carmesi mientras la luna danzaba susurraba "
             "entre las nubes flotaba murmuraba.", 2, 300, False),

            # Cap 3: Formal otra vez
            ("Asimismo, percibió que el transcurrir del tiempo era inexorable. "
             "Por ende, decidió actuar no obstante.", 3, 0, False),
        ]

        analyses = detector.analyze_document(segments)
        changes = detector.detect_changes(min_severity='low')

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
        changes = detector.detect_changes(min_severity='low')

        # No debe haber cambios significativos
        assert len(changes) == 0

        # Todos deben ser formales
        for analysis in detector.analyses:
            assert analysis.primary_register == RegisterType.FORMAL_LITERARY

    def test_mixed_document_report(self):
        """Test reporte de documento mezclado."""
        detector = RegisterChangeDetector()

        segments = [
            ("Contempló la vastedad asimismo no obstante.", 1, 0, False),
            ("Bro flipaba mogollon con la pasada guay crack.", 1, 100, False),
            ("El diagnóstico revelaba una patología compleja.", 2, 0, False),
        ]

        detector.analyze_document(segments)
        summary = detector.get_summary()

        assert summary['total_segments'] == 3
        assert len(summary['distribution']) >= 2
