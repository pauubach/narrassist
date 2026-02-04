"""
Re-exporta el módulo de pacing desde narrative_assistant.analysis.pacing.

Este archivo existe por compatibilidad. El módulo principal está en:
  src/narrative_assistant/analysis/pacing.py

Usar preferentemente:
  from narrative_assistant.analysis.pacing import get_pacing_analyzer
"""

# Re-exportar desde el módulo principal
from ...analysis.pacing import (
    PacingAnalysisResult,
    PacingAnalyzer,
    PacingIssue,
    PacingIssueType,
    PacingMetrics,
    PacingSeverity,
    analyze_pacing,
    get_pacing_analyzer,
)

__all__ = [
    "PacingAnalyzer",
    "PacingAnalysisResult",
    "PacingMetrics",
    "PacingIssue",
    "PacingIssueType",
    "PacingSeverity",
    "analyze_pacing",
    "get_pacing_analyzer",
]
