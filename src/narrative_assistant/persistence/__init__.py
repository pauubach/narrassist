"""
Persistence module - Base de datos, sesiones, historial y fingerprinting.
"""

from .analysis import (
    AnalysisPhase,
    AnalysisRepository,
    AnalysisRun,
    AnalysisStatus,
    Interaction,
    InteractionType,
    PacingMetrics,
    RegisterChange,
    Relationship,
    RelationType,
    Tone,
    get_analysis_repository,
    reset_analysis_repository,
)
from .database import (
    Database,
    delete_and_recreate_database,
    get_database,
    repair_database,
    reset_database,
)
from .document_fingerprint import DocumentFingerprint, FingerprintMatcher
from .glossary import GlossaryEntry, GlossaryRepository
from .history import ChangeType, HistoryEntry, HistoryManager
from .project import Project, ProjectManager
from .session import AlertAction, Session, SessionManager
from .timeline import TemporalMarkerData, TimelineEventData, TimelineRepository

__all__ = [
    # Database
    "Database",
    "get_database",
    "reset_database",
    "repair_database",
    "delete_and_recreate_database",
    # Project
    "Project",
    "ProjectManager",
    # Fingerprint
    "DocumentFingerprint",
    "FingerprintMatcher",
    # Session
    "Session",
    "SessionManager",
    "AlertAction",
    # History
    "HistoryEntry",
    "HistoryManager",
    "ChangeType",
    # Timeline
    "TimelineRepository",
    "TimelineEventData",
    "TemporalMarkerData",
    # Glossary
    "GlossaryEntry",
    "GlossaryRepository",
    # Analysis
    "AnalysisRepository",
    "AnalysisRun",
    "AnalysisPhase",
    "Relationship",
    "Interaction",
    "RegisterChange",
    "PacingMetrics",
    "get_analysis_repository",
    "reset_analysis_repository",
    "AnalysisStatus",
    "RelationType",
    "InteractionType",
    "Tone",
]
