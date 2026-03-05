from __future__ import annotations

import narrative_assistant.persistence.event_repository as event_repo_module
from narrative_assistant.persistence.event_repository import (
    EventRepository,
    get_event_repository,
)


class _DbWithPath:
    def __init__(self, path: str):
        self.db_path = path


class _DbWithoutPath:
    pass


def test_explicit_db_bypasses_singleton():
    db = _DbWithPath("explicit.db")

    repo1 = get_event_repository(db=db)  # type: ignore[arg-type]
    repo2 = get_event_repository(db=db)  # type: ignore[arg-type]

    assert repo1 is not repo2
    assert repo1.db is db
    assert repo2.db is db


def test_singleton_refreshes_when_db_path_changes(monkeypatch):
    db_old = _DbWithPath("old.db")
    db_new = _DbWithPath("new.db")

    monkeypatch.setattr(event_repo_module, "_event_repository", EventRepository(db_old))  # type: ignore[arg-type]
    monkeypatch.setattr(event_repo_module, "get_database", lambda: db_new)

    repo = get_event_repository()
    assert repo.db is db_new


def test_singleton_does_not_match_distinct_db_without_path(monkeypatch):
    db_old = _DbWithoutPath()
    db_new = _DbWithoutPath()

    monkeypatch.setattr(event_repo_module, "_event_repository", EventRepository(db_old))  # type: ignore[arg-type]
    monkeypatch.setattr(event_repo_module, "get_database", lambda: db_new)

    repo = get_event_repository()
    assert repo.db is db_new
