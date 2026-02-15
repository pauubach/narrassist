"""
Detectores de correcciones editoriales.

Cada detector analiza un tipo específico de problema y genera
CorrectionIssue que se presentan al corrector como sugerencias.
"""

from .agreement import AgreementDetector
from .anacoluto import AnacolutoDetector
from .anglicisms import AnglicismsDetector
from .clarity import ClarityDetector
from .crutch_words import CrutchWordsDetector
from .field_terminology import FieldTerminologyDetector
from .glossary import GlossaryDetector
from .grammar import GrammarDetector
from .acronyms import AcronymDetector
from .coherence import CoherenceDetector
from .orthographic_variants import OrthographicVariantsDetector
from .pov import POVDetector
from .references import ReferencesDetector
from .scientific_structure import ScientificStructureDetector
from .regional import RegionalDetector
from .style_register import StyleRegisterDetector
from .repetition import RepetitionDetector
from .terminology import TerminologyDetector
from .typography import TypographyDetector

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
    "ReferencesDetector",
    "AcronymDetector",
    "ScientificStructureDetector",
    "StyleRegisterDetector",
    "CoherenceDetector",
]
