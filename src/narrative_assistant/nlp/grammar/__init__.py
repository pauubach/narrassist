"""
Módulo de corrección gramatical para el Asistente de Corrección Narrativa.

Proporciona detección de errores gramaticales usando múltiples métodos:

SIEMPRE ACTIVOS (sin dependencias externas):
- Reglas propias de español (dequeísmo, queísmo, laísmo, concordancia...)
- Patrones regex para errores comunes
- Análisis de dependencias con spaCy

OPCIONALES (requieren configuración):
- LanguageTool local (+2000 reglas, requiere Java)
- LLM local para análisis contextual (requiere Ollama)

Uso:
    from narrative_assistant.nlp.grammar import get_grammar_checker

    checker = get_grammar_checker()
    result = checker.check(text)

    if result.is_success:
        for issue in result.value.issues:
            print(f"{issue.text} - {issue.explanation}")

    # Verificar si LanguageTool está disponible (opcional)
    if checker.languagetool_available:
        print("LanguageTool activo: +2000 reglas adicionales")

Configuración (en AppConfig.grammar o variables de entorno):
    - NA_USE_LANGUAGETOOL: true/false (default: true)
    - NA_GRAMMAR_USE_LLM: true/false (default: false)
    - NA_GRAMMAR_MIN_CONFIDENCE: 0.0-1.0 (default: 0.5)
"""

from .base import (
    GrammarDetectionMethod,
    GrammarErrorType,
    GrammarIssue,
    GrammarReport,
    GrammarSeverity,
)
from .grammar_checker import (
    GrammarChecker,
    get_grammar_checker,
    reset_grammar_checker,
)
from .languagetool_client import (
    LanguageToolClient,
    LTCheckResult,
    LTClientError,
    LTMatch,
    get_languagetool_client,
    is_languagetool_available,
    reset_languagetool_client,
)
from .languagetool_manager import (
    # Instalador
    InstallProgress,
    LanguageToolInstaller,
    LanguageToolManager,
    ensure_languagetool_running,
    get_install_progress,
    get_languagetool_manager,
    is_languagetool_installed,
    is_lt_installing,
    start_lt_installation,
    stop_languagetool,
)
from .spanish_rules import (
    SpanishRulesConfig,
    apply_spanish_rules,
    check_adjective_agreement,
    check_dequeismo,
    check_gender_agreement,
    check_laismo,
    check_loismo,
    check_number_agreement,
    check_punctuation,
    check_queismo,
    check_redundancy,
)

__all__ = [
    # Types
    "GrammarIssue",
    "GrammarReport",
    "GrammarErrorType",
    "GrammarSeverity",
    "GrammarDetectionMethod",
    # Checker
    "GrammarChecker",
    "get_grammar_checker",
    "reset_grammar_checker",
    # Spanish rules (propias, sin dependencias)
    "SpanishRulesConfig",
    "apply_spanish_rules",
    "check_dequeismo",
    "check_queismo",
    "check_laismo",
    "check_loismo",
    "check_gender_agreement",
    "check_number_agreement",
    "check_adjective_agreement",
    "check_redundancy",
    "check_punctuation",
    # LanguageTool (opcional)
    "LTMatch",
    "LTCheckResult",
    "LTClientError",
    "LanguageToolClient",
    "get_languagetool_client",
    "is_languagetool_available",
    "reset_languagetool_client",
    # LanguageTool Manager (inicio automático)
    "LanguageToolManager",
    "get_languagetool_manager",
    "ensure_languagetool_running",
    "stop_languagetool",
    "is_languagetool_installed",
    # LanguageTool Installer (instalación desde UI)
    "InstallProgress",
    "LanguageToolInstaller",
    "get_install_progress",
    "is_lt_installing",
    "start_lt_installation",
]
