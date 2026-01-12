"""
Persistence module - Base de datos, sesiones, historial y fingerprinting.
"""

from .database import Database, get_database, reset_database
from .project import Project, ProjectManager
from .document_fingerprint import DocumentFingerprint, FingerprintMatcher
from .session import Session, SessionManager, AlertAction
from .history import HistoryEntry, HistoryManager, ChangeType

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
]
