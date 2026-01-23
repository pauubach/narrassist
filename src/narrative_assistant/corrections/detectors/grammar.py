"""
Detector de problemas gramaticales.

Integra las reglas gramaticales del español con el sistema de correcciones.
Incluye:
- Dequeísmo / Queísmo
- Laísmo / Loísmo
- Concordancia de género y número
- Expresiones redundantes
"""

from typing import Optional

from ..base import BaseDetector, CorrectionIssue
from ..config import GrammarConfig
from ..types import CorrectionCategory, GrammarIssueType
from ...nlp.grammar.spanish_rules import (
    apply_spanish_rules,
    SpanishRulesConfig,
    GrammarSeverity,
)


class GrammarDetector(BaseDetector):
    """
    Detector de errores gramaticales del español.

    Usa el módulo de reglas gramaticales existente y convierte los resultados
    al formato CorrectionIssue del sistema de correcciones.
    """

    def __init__(self, config: Optional[GrammarConfig] = None):
        self.config = config or GrammarConfig()

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.GRAMMAR

    @property
    def requires_spacy(self) -> bool:
        return True  # Las reglas gramaticales necesitan spaCy

    def detect(
        self,
        text: str,
        chapter_index: Optional[int] = None,
        spacy_doc=None,
        **kwargs,
    ) -> list[CorrectionIssue]:
        """
        Detecta errores gramaticales en el texto.

        Args:
            text: Texto a analizar
            chapter_index: Índice del capítulo
            spacy_doc: Documento spaCy pre-procesado

        Returns:
            Lista de CorrectionIssue encontrados
        """
        if not self.config.enabled:
            return []

        if spacy_doc is None:
            # Necesitamos spaCy para las reglas gramaticales
            return []

        # Configurar qué reglas aplicar basado en la configuración
        rules_config = SpanishRulesConfig(
            check_dequeismo=self.config.check_dequeismo,
            check_queismo=self.config.check_queismo,
            check_laismo=self.config.check_laismo,
            check_loismo=self.config.check_loismo,
            check_gender=self.config.check_gender_agreement,
            check_number=self.config.check_number_agreement,
            check_adjective=self.config.check_adjective_agreement,
            check_redundancy=self.config.check_redundancy,
            check_punctuation=False,  # Ya tenemos TypographyDetector
            check_other=self.config.check_other,
            use_spacy_analysis=True,
            min_confidence=self.config.min_confidence,
        )

        # Aplicar reglas
        grammar_issues = apply_spanish_rules(spacy_doc, rules_config)

        # Convertir a CorrectionIssue
        issues: list[CorrectionIssue] = []

        for gi in grammar_issues:
            # Mapear tipo de error a issue_type
            issue_type = self._map_issue_type(gi.error_type.value)

            # Mapear severidad
            confidence = gi.confidence

            issues.append(
                CorrectionIssue(
                    category=self.category.value,
                    issue_type=issue_type,
                    start_char=gi.start_char,
                    end_char=gi.end_char,
                    text=gi.text,
                    explanation=gi.explanation,
                    suggestion=gi.suggestion,
                    confidence=confidence,
                    context=gi.sentence[:150] if gi.sentence else self._extract_context(text, gi.start_char, gi.end_char),
                    chapter_index=chapter_index,
                    rule_id=gi.rule_id,
                    extra_data={
                        "severity": gi.severity.value,
                        "detection_method": gi.detection_method.value,
                        "alternatives": gi.alternatives,
                    },
                )
            )

        return issues

    def _map_issue_type(self, error_type: str) -> str:
        """Mapea el tipo de error gramatical al issue_type del sistema."""
        mapping = {
            "dequeismo": GrammarIssueType.DEQUEISMO.value,
            "queismo": GrammarIssueType.QUEISMO.value,
            "laismo": GrammarIssueType.LAISMO.value,
            "loismo": GrammarIssueType.LOISMO.value,
            "leismo": GrammarIssueType.LEISMO.value,
            "gender_agreement": GrammarIssueType.GENDER_AGREEMENT.value,
            "number_agreement": GrammarIssueType.NUMBER_AGREEMENT.value,
            "adjective_agreement": GrammarIssueType.ADJECTIVE_AGREEMENT.value,
            "redundancy": GrammarIssueType.REDUNDANCY.value,
            "punctuation": "punctuation_error",
            "infinitive_error": "infinitive_error",
            "gerund_error": "gerund_error",
        }
        return mapping.get(error_type, error_type)
