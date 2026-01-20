"""
Módulo de análisis de estilo para el Asistente de Corrección Narrativa.

Proporciona detección de:
- Repeticiones léxicas (palabras repetidas en proximidad)
- Repeticiones semánticas (conceptos/ideas repetidos)
- Coherencia narrativa (saltos bruscos entre segmentos)
- Perfiles de voz (patrones estilométricos por personaje)
- Desviaciones de voz (personaje habla fuera de su perfil)

Uso:
    from narrative_assistant.nlp.style import get_repetition_detector, get_coherence_detector

    # Repeticiones
    detector = get_repetition_detector()
    result = detector.detect_lexical(text, min_distance=50)

    for rep in result.value.repetitions:
        print(f"'{rep.word}' repetida {rep.count} veces")

    # Coherencia narrativa
    coherence = get_coherence_detector()
    result = coherence.detect(text)

    for brk in result.value.breaks:
        print(f"Salto de coherencia: {brk.explanation}")
"""

from .repetition_detector import (
    Repetition,
    RepetitionReport,
    RepetitionType,
    RepetitionSeverity,
    RepetitionOccurrence,
    RepetitionDetector,
    get_repetition_detector,
    reset_repetition_detector,
)

from .coherence_detector import (
    CoherenceBreak,
    CoherenceReport,
    CoherenceBreakType,
    CoherenceSeverity,
    CoherenceDetector,
    get_coherence_detector,
    reset_coherence_detector,
)

from .editorial_rules import (
    EditorialRule,
    EditorialRuleType,
    EditorialRuleCategory,
    EditorialIssue,
    EditorialReport,
    EditorialRulesChecker,
    get_editorial_checker,
    reset_editorial_checker,
    PREDEFINED_RULES,
    parse_user_rules,
    check_with_user_rules,
)

__all__ = [
    # Repeticiones
    "Repetition",
    "RepetitionReport",
    "RepetitionType",
    "RepetitionSeverity",
    "RepetitionOccurrence",
    "RepetitionDetector",
    "get_repetition_detector",
    "reset_repetition_detector",
    # Coherencia
    "CoherenceBreak",
    "CoherenceReport",
    "CoherenceBreakType",
    "CoherenceSeverity",
    "CoherenceDetector",
    "get_coherence_detector",
    "reset_coherence_detector",
    # Reglas editoriales
    "EditorialRule",
    "EditorialRuleType",
    "EditorialRuleCategory",
    "EditorialIssue",
    "EditorialReport",
    "EditorialRulesChecker",
    "get_editorial_checker",
    "reset_editorial_checker",
    "PREDEFINED_RULES",
    "parse_user_rules",
    "check_with_user_rules",
]
