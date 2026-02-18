"""
Tests para análisis temporal cross-book.

Cubre:
- Reglas de detección (age_inconsistency, date_conflict)
- Dataclasses (CrossBookTemporalIssue, CrossBookTemporalReport)
- BookTemporalData
- Edge cases
"""

from datetime import date

import pytest

from narrative_assistant.analysis.temporal_alignment import (
    AGE_TOLERANCE_YEARS,
    BookTemporalData,
    CrossBookTemporalAnalyzer,
    CrossBookTemporalIssue,
    CrossBookTemporalReport,
    CrossBookTemporalType,
    _check_age_inconsistency,
    _check_date_conflict,
)

# ============================================================================
# Helpers
# ============================================================================

def _book(pid: int, name: str, order: int, **kwargs) -> BookTemporalData:
    return BookTemporalData(project_id=pid, project_name=name, book_order=order, **kwargs)


# ============================================================================
# CrossBookTemporalIssue
# ============================================================================

class TestCrossBookTemporalIssue:
    def test_to_dict(self):
        issue = CrossBookTemporalIssue(
            issue_type=CrossBookTemporalType.AGE_INCONSISTENCY,
            entity_name="Juan",
            description="edad retrocede",
            book_a_name="L1",
            book_b_name="L2",
            book_a_chapter=10,
            book_b_chapter=1,
            severity="critical",
            confidence=0.9,
        )
        d = issue.to_dict()
        assert d["issue_type"] == "cross_book_age_inconsistency"
        assert d["entity_name"] == "Juan"
        assert d["severity"] == "critical"
        assert d["confidence"] == 0.9


# ============================================================================
# CrossBookTemporalReport
# ============================================================================

class TestCrossBookTemporalReport:
    def test_empty_report(self):
        r = CrossBookTemporalReport(collection_id=1, collection_name="Saga")
        d = r.to_dict()
        assert d["summary"]["total_issues"] == 0
        assert d["summary"]["by_type"] == {}
        assert d["summary"]["by_severity"] == {}

    def test_report_with_issues(self):
        issues = [
            CrossBookTemporalIssue(
                issue_type=CrossBookTemporalType.AGE_INCONSISTENCY,
                entity_name="A", description="d1",
                book_a_name="L1", book_b_name="L2",
                severity="critical",
            ),
            CrossBookTemporalIssue(
                issue_type=CrossBookTemporalType.DATE_CONFLICT,
                entity_name="B", description="d2",
                book_a_name="L1", book_b_name="L2",
                severity="low",
            ),
        ]
        r = CrossBookTemporalReport(
            collection_id=1, collection_name="Saga",
            issues=issues, books_analyzed=2, entity_links_analyzed=5,
        )
        d = r.to_dict()
        assert d["summary"]["total_issues"] == 2
        assert d["summary"]["by_type"]["cross_book_age_inconsistency"] == 1
        assert d["summary"]["by_type"]["cross_book_date_conflict"] == 1
        assert d["summary"]["by_severity"]["critical"] == 1
        assert d["summary"]["by_severity"]["low"] == 1


# ============================================================================
# _check_age_inconsistency
# ============================================================================

class TestAgeInconsistency:
    def test_age_decreases_between_books(self):
        """Personaje más joven en libro posterior → critical."""
        book_a = _book(1, "Libro 1", order=1)
        book_b = _book(2, "Libro 2", order=2)
        ages_a = [(10, 30, None)]  # cap 10, edad 30
        ages_b = [(1, 25, None)]   # cap 1, edad 25
        issues = _check_age_inconsistency("Juan", ages_a, ages_b, book_a, book_b)
        assert len(issues) == 1
        assert issues[0].issue_type == CrossBookTemporalType.AGE_INCONSISTENCY
        assert issues[0].severity == "critical"
        assert "30" in issues[0].description
        assert "25" in issues[0].description

    def test_age_increases_normally(self):
        """Personaje envejece normalmente → sin issue."""
        book_a = _book(1, "L1", order=1)
        book_b = _book(2, "L2", order=2)
        ages_a = [(10, 30, None)]
        ages_b = [(1, 35, None)]
        issues = _check_age_inconsistency("Juan", ages_a, ages_b, book_a, book_b)
        assert len(issues) == 0

    def test_age_with_dates_consistent(self):
        """Con fechas, envejecimiento coherente → sin issue."""
        book_a = _book(1, "L1", order=1)
        book_b = _book(2, "L2", order=2)
        ages_a = [(10, 30, date(2000, 6, 15))]
        ages_b = [(1, 35, date(2005, 6, 15))]  # 5 años después, 5 años más
        issues = _check_age_inconsistency("Juan", ages_a, ages_b, book_a, book_b)
        assert len(issues) == 0

    def test_age_with_dates_mismatch(self):
        """Con fechas, envejecimiento no coherente → high."""
        book_a = _book(1, "L1", order=1)
        book_b = _book(2, "L2", order=2)
        ages_a = [(10, 30, date(2000, 1, 1))]
        ages_b = [(1, 40, date(2005, 1, 1))]  # 5 años después pero envejece 10
        issues = _check_age_inconsistency("Juan", ages_a, ages_b, book_a, book_b)
        assert len(issues) == 1
        assert issues[0].severity == "high"
        assert issues[0].metadata["years_passed"] == 5.0

    def test_same_order_no_issue(self):
        book_a = _book(1, "L1", order=1)
        book_b = _book(2, "L2", order=1)
        ages_a = [(10, 30, None)]
        ages_b = [(1, 25, None)]
        issues = _check_age_inconsistency("Juan", ages_a, ages_b, book_a, book_b)
        assert len(issues) == 0

    def test_empty_ages(self):
        book_a = _book(1, "L1", order=1)
        book_b = _book(2, "L2", order=2)
        issues = _check_age_inconsistency("Juan", [], [], book_a, book_b)
        assert len(issues) == 0

    def test_reversed_book_order(self):
        """book_b tiene orden menor → se invierte correctamente."""
        book_a = _book(1, "Libro 2", order=2)
        book_b = _book(2, "Libro 1", order=1)
        ages_a = [(1, 25, None)]  # Book A = posterior, edad 25
        ages_b = [(10, 30, None)]  # Book B = anterior, edad 30
        issues = _check_age_inconsistency("Juan", ages_a, ages_b, book_a, book_b)
        assert len(issues) == 1
        assert issues[0].severity == "critical"

    def test_within_tolerance(self):
        """Diferencia dentro de la tolerancia (2 años) → sin issue."""
        book_a = _book(1, "L1", order=1)
        book_b = _book(2, "L2", order=2)
        ages_a = [(10, 30, date(2000, 1, 1))]
        ages_b = [(1, 36, date(2005, 1, 1))]  # 5 años, envejece 6 → diff 1 < tol 2
        issues = _check_age_inconsistency("Juan", ages_a, ages_b, book_a, book_b)
        assert len(issues) == 0


# ============================================================================
# _check_date_conflict
# ============================================================================

class TestDateConflict:
    def test_significant_overlap(self):
        """Libro B empieza 2 años antes de que termine libro A → issue."""
        book_a = _book(1, "L1", order=1,
                       time_span=(date(2000, 1, 1), date(2005, 12, 31)))
        book_b = _book(2, "L2", order=2,
                       time_span=(date(2003, 6, 1), date(2010, 12, 31)))
        issues = _check_date_conflict("entity", book_a, book_b)
        assert len(issues) == 1
        assert issues[0].issue_type == CrossBookTemporalType.DATE_CONFLICT

    def test_no_overlap(self):
        """Sin solapamiento → sin issue."""
        book_a = _book(1, "L1", order=1,
                       time_span=(date(2000, 1, 1), date(2005, 12, 31)))
        book_b = _book(2, "L2", order=2,
                       time_span=(date(2006, 1, 1), date(2010, 12, 31)))
        issues = _check_date_conflict("entity", book_a, book_b)
        assert len(issues) == 0

    def test_small_overlap_tolerated(self):
        """Solapamiento pequeño (< 1 año) → tolerado."""
        book_a = _book(1, "L1", order=1,
                       time_span=(date(2000, 1, 1), date(2005, 12, 31)))
        book_b = _book(2, "L2", order=2,
                       time_span=(date(2005, 6, 1), date(2010, 12, 31)))
        issues = _check_date_conflict("entity", book_a, book_b)
        assert len(issues) == 0

    def test_no_time_spans(self):
        book_a = _book(1, "L1", order=1)
        book_b = _book(2, "L2", order=2)
        issues = _check_date_conflict("entity", book_a, book_b)
        assert len(issues) == 0

    def test_wrong_order(self):
        """book_a no es anterior → sin issue."""
        book_a = _book(1, "L1", order=2,
                       time_span=(date(2000, 1, 1), date(2005, 12, 31)))
        book_b = _book(2, "L2", order=1,
                       time_span=(date(1995, 1, 1), date(2010, 12, 31)))
        issues = _check_date_conflict("entity", book_a, book_b)
        assert len(issues) == 0


# ============================================================================
# CrossBookTemporalAnalyzer
# ============================================================================

class TestCrossBookTemporalAnalyzer:
    def test_init(self):
        analyzer = CrossBookTemporalAnalyzer()
        assert analyzer._db is None

    def test_init_with_db(self):
        mock_db = object()
        analyzer = CrossBookTemporalAnalyzer(db=mock_db)
        assert analyzer._db is mock_db
