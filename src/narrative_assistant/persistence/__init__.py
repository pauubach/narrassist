"""
Persistence module - Base de datos, sesiones, historial y fingerprinting.
"""

from .database import Database, get_database, reset_database
from .project import Project, ProjectManager
from .document_fingerprint import DocumentFingerprint, FingerprintMatcher
from .session import Session, SessionManager, AlertAction
from .history import HistoryEntry, HistoryManager, ChangeType
from .timeline import TimelineRepository, TimelineEventData, TemporalMarkerData
from .analysis import (
    AnalysisRepository,
    AnalysisRun,
    AnalysisPhase,
    Relationship,
    Interaction,
    RegisterChange,
    PacingMetrics,
    get_analysis_repository,
    reset_analysis_repository,
    AnalysisStatus,
    RelationType,
    InteractionType,
    Tone,
)

__all__ = [
    # Database
    "Database",
    "get_database",
    "reset_database",
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
