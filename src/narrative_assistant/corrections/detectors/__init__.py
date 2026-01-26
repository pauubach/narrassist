"""
Detectores de correcciones editoriales.

Cada detector analiza un tipo específico de problema y genera
CorrectionIssue que se presentan al corrector como sugerencias.
"""

from .typography import TypographyDetector
from .repetition import RepetitionDetector
from .agreement import AgreementDetector
from .terminology import TerminologyDetector
from .regional import RegionalDetector
from .field_terminology import FieldTerminologyDetector
from .clarity import ClarityDetector
from .grammar import GrammarDetector
from .anglicisms import AnglicismsDetector
from .crutch_words import CrutchWordsDetector
from .glossary import GlossaryDetector
from .anacoluto import AnacolutoDetector
from .pov import POVDetector
from .orthographic_variants import OrthographicVariantsDetector

__all__ = [
    "TypographyDetector",
    "RepetitionDetector",
    "AgreementDetector",
    "TerminologyDetector",
    "RegionalDetector",
    "FieldTerminologyDetector",
    "ClarityDetector",
    "GrammarDetector",
    "AnglicismsDetector",
    "CrutchWordsDetector",
    "GlossaryDetector",
    "AnacolutoDetector",
    "POVDetector",
    "OrthographicVariantsDetector",
]
