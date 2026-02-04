"""
Módulo de corrección ortográfica para el Asistente de Corrección Narrativa.

Proporciona detección de errores ortográficos usando múltiples métodos:

## Sistema de Votación Multi-Corrector (Recomendado)

Combina múltiples correctores con votación ponderada por confianza:
- pyspellchecker (Pure Python, español incluido)
- chunspell/hunspell (diccionario profesional)
- symspellpy (algoritmo SymSpell de alta velocidad)
- LanguageTool (gramática + ortografía)
- LLM local como árbitro para casos dudosos

Uso:
    from narrative_assistant.nlp.orthography import get_voting_spelling_checker

    checker = get_voting_spelling_checker()
    result = checker.check(text, known_entities=["María", "Juan"])

    if result.is_success:
        for issue in result.value.issues:
            print(f"{issue.word} -> {issue.suggestions}")

## Corrector Simple (Legacy)

Uso:
    from narrative_assistant.nlp.orthography import get_spelling_checker

    checker = get_spelling_checker()
    result = checker.check(text)
"""

from .base import (
    SpellingErrorType,
    SpellingIssue,
    SpellingReport,
    SpellingSeverity,
)
from .spelling_checker import (
    SpellingChecker,
    get_spelling_checker,
    reset_spelling_checker,
)

# Sistema de votación multi-corrector
try:
    from .voting_checker import (
        Vote,
        VotingResult,
        VotingSpellingChecker,
        get_voting_spelling_checker,
        reset_voting_spelling_checker,
    )

    _VOTING_AVAILABLE = True
except ImportError:
    _VOTING_AVAILABLE = False
    VotingSpellingChecker = None
    get_voting_spelling_checker = None
    reset_voting_spelling_checker = None
    VotingResult = None
    Vote = None

__all__ = [
    # Types
    "SpellingIssue",
    "SpellingReport",
    "SpellingErrorType",
    "SpellingSeverity",
    # Legacy checker
    "SpellingChecker",
    "get_spelling_checker",
    "reset_spelling_checker",
    # Voting checker (recommended)
    "VotingSpellingChecker",
    "get_voting_spelling_checker",
    "reset_voting_spelling_checker",
    "VotingResult",
    "Vote",
]
