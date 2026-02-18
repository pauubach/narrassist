"""
Tests para el validador LLM de contradicciones cross-book.

Usa mocks para el cliente LLM — no requiere Ollama real.
"""

import pytest
from unittest.mock import MagicMock, patch

from narrative_assistant.analysis.contradiction_validator import (
    MIN_CONFIDENCE_FOR_LLM,
    VERDICT_MULTIPLIERS,
    ContradictionValidator,
    ValidationResult,
    reset_contradiction_validator,
)
from narrative_assistant.analysis.cross_book_events import EventContradiction
from narrative_assistant.analysis.event_types import EventType


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset singleton entre tests."""
    reset_contradiction_validator()
    yield
    reset_contradiction_validator()


@pytest.fixture
def sample_contradiction():
    return EventContradiction(
        rule="death_then_alive",
        entity_name="Juan",
        description="Juan muere en «Libro 1» pero aparece vivo en «Libro 2»",
        event_a_type=EventType.DEATH.value,
        event_b_type=EventType.DECISION.value,
        book_a_name="Libro 1",
        book_b_name="Libro 2",
        confidence=0.9,
    )


@pytest.fixture
def low_confidence_contradiction():
    return EventContradiction(
        rule="location_impossibility",
        entity_name="Ana",
        description="Ana en Madrid y Tokio",
        event_a_type=EventType.LOCATION_CHANGE.value,
        event_b_type=EventType.LOCATION_CHANGE.value,
        book_a_name="L1",
        book_b_name="L2",
        confidence=0.3,
    )


# ============================================================================
# ValidationResult
# ============================================================================

class TestValidationResult:
    def test_is_valid_confirmed(self, sample_contradiction):
        r = ValidationResult(
            contradiction=sample_contradiction,
            verdict="CONFIRMED",
            original_confidence=0.9,
            adjusted_confidence=0.95,
            reasoning="test",
        )
        assert r.is_valid

    def test_is_valid_probable(self, sample_contradiction):
        r = ValidationResult(
            contradiction=sample_contradiction,
            verdict="PROBABLE",
            original_confidence=0.9,
            adjusted_confidence=0.9,
            reasoning="test",
        )
        assert r.is_valid

    def test_not_valid_doubtful(self, sample_contradiction):
        r = ValidationResult(
            contradiction=sample_contradiction,
            verdict="DOUBTFUL",
            original_confidence=0.9,
            adjusted_confidence=0.5,
            reasoning="test",
        )
        assert not r.is_valid

    def test_not_valid_dismissed(self, sample_contradiction):
        r = ValidationResult(
            contradiction=sample_contradiction,
            verdict="DISMISSED",
            original_confidence=0.9,
            adjusted_confidence=0.1,
            reasoning="test",
        )
        assert not r.is_valid


# ============================================================================
# ContradictionValidator — sin LLM
# ============================================================================

class TestValidatorNoLLM:
    def test_fallback_when_no_client(self, sample_contradiction):
        validator = ContradictionValidator()
        validator._client_checked = True
        validator._client = None

        result = validator.validate_single(sample_contradiction)
        assert result.verdict == "PROBABLE"
        assert result.adjusted_confidence == sample_contradiction.confidence
        assert "sin LLM" in result.reasoning

    def test_is_available_false_when_no_client(self):
        validator = ContradictionValidator()
        validator._client_checked = True
        validator._client = None
        assert not validator.is_available

    def test_low_confidence_skips_llm(self, low_confidence_contradiction):
        """Contradicciones con confianza baja no se envían al LLM."""
        mock_client = MagicMock()
        mock_client.is_available = True
        validator = ContradictionValidator()
        validator._client_checked = True
        validator._client = mock_client

        result = validator.validate_single(low_confidence_contradiction)
        assert result.verdict == "DOUBTFUL"
        assert result.adjusted_confidence < low_confidence_contradiction.confidence
        # No debería haber llamado al LLM
        mock_client.voting_query.assert_not_called()
        mock_client.complete.assert_not_called()


# ============================================================================
# ContradictionValidator — con LLM mockeado
# ============================================================================

class TestValidatorWithMockedLLM:
    def _make_validator_with_mock(self, voting_result=None, complete_result=None):
        mock_client = MagicMock()
        mock_client.is_available = True

        if voting_result is not None:
            mock_voting = MagicMock()
            mock_voting.is_valid = True
            mock_voting.consensus = voting_result
            mock_voting.models_used = ["qwen3", "deepseek-r1"]
            mock_client.voting_query.return_value = mock_voting
        else:
            mock_client.voting_query.side_effect = Exception("voting not available")
            mock_client.complete.return_value = complete_result

        validator = ContradictionValidator()
        validator._client_checked = True
        validator._client = mock_client
        return validator

    @patch("narrative_assistant.analysis.contradiction_validator.get_contradiction_validator")
    def test_confirmed_verdict(self, _, sample_contradiction):
        validator = self._make_validator_with_mock(voting_result={
            "verdict": "CONFIRMED",
            "reasoning": "Muerte explícita sin ambigüedad",
            "adjusted_confidence": 0.95,
            "narrative_explanation": None,
        })
        result = validator.validate_single(
            sample_contradiction,
            context_a="Juan murió en el hospital.",
            context_b="Juan decidió viajar.",
        )
        assert result.verdict == "CONFIRMED"
        assert result.adjusted_confidence > sample_contradiction.confidence * 0.9
        assert result.models_used == ["qwen3", "deepseek-r1"]

    def test_dismissed_verdict(self, sample_contradiction):
        validator = self._make_validator_with_mock(voting_result={
            "verdict": "DISMISSED",
            "reasoning": "Muerte presunta, no confirmada",
            "adjusted_confidence": 0.1,
            "narrative_explanation": "Muerte presunta resuelta",
        })
        result = validator.validate_single(sample_contradiction)
        assert result.verdict == "DISMISSED"
        assert not result.is_valid
        assert result.narrative_explanation == "Muerte presunta resuelta"

    def test_fallback_to_simple_completion(self, sample_contradiction):
        """Si voting_query falla, usa complete() como fallback."""
        import json
        response_json = json.dumps({
            "verdict": "PROBABLE",
            "reasoning": "Posible contradicción",
            "adjusted_confidence": 0.7,
            "narrative_explanation": None,
        })
        validator = self._make_validator_with_mock(
            voting_result=None,
            complete_result=response_json,
        )
        result = validator.validate_single(sample_contradiction)
        assert result.verdict == "PROBABLE"

    def test_batch_validation(self):
        contradictions = [
            EventContradiction(
                rule="death_then_alive", entity_name=f"Persona {i}",
                description=f"desc {i}",
                event_a_type="death", event_b_type="decision",
                book_a_name="L1", book_b_name="L2",
                confidence=0.8,
            )
            for i in range(3)
        ]
        validator = self._make_validator_with_mock(voting_result={
            "verdict": "CONFIRMED",
            "reasoning": "OK",
            "adjusted_confidence": 0.9,
            "narrative_explanation": None,
        })
        results = validator.validate_batch(contradictions)
        assert len(results) == 3
        assert all(r.verdict == "CONFIRMED" for r in results)


# ============================================================================
# _parse_response
# ============================================================================

class TestParseResponse:
    def test_valid_json(self):
        import json
        validator = ContradictionValidator()
        response = json.dumps({
            "verdict": "CONFIRMED",
            "reasoning": "test reasoning",
            "adjusted_confidence": 0.85,
            "narrative_explanation": None,
        })
        result = validator._parse_response(response)
        assert result is not None
        assert result["verdict"] == "CONFIRMED"
        assert result["adjusted_confidence"] == 0.85

    def test_lowercase_verdict_normalized(self):
        import json
        validator = ContradictionValidator()
        response = json.dumps({
            "verdict": "confirmed",
            "reasoning": "test",
        })
        result = validator._parse_response(response)
        assert result["verdict"] == "CONFIRMED"

    def test_spanish_verdict_mapped(self):
        import json
        validator = ContradictionValidator()
        response = json.dumps({
            "verdict": "DESCARTADO",
            "reasoning": "No es contradicción",
        })
        result = validator._parse_response(response)
        assert result["verdict"] == "DISMISSED"

    def test_unknown_verdict_defaults_doubtful(self):
        import json
        validator = ContradictionValidator()
        response = json.dumps({
            "verdict": "MAYBE",
            "reasoning": "Not sure",
        })
        result = validator._parse_response(response)
        assert result["verdict"] == "DOUBTFUL"

    def test_missing_keys_defaults_doubtful(self):
        """Sin verdict ni reasoning, el parser normaliza a DOUBTFUL."""
        import json
        validator = ContradictionValidator()
        response = json.dumps({"foo": "bar"})
        result = validator._parse_response(response)
        # validate_llm_response puede devolver dict parcial, el parser lo normaliza
        if result is not None:
            assert result["verdict"] == "DOUBTFUL"

    def test_invalid_confidence_clamped(self):
        import json
        validator = ContradictionValidator()
        response = json.dumps({
            "verdict": "PROBABLE",
            "reasoning": "test",
            "adjusted_confidence": 1.5,
        })
        result = validator._parse_response(response)
        assert result["adjusted_confidence"] == 1.0


# ============================================================================
# VERDICT_MULTIPLIERS
# ============================================================================

class TestVerdictMultipliers:
    def test_confirmed_boosts(self):
        assert VERDICT_MULTIPLIERS["CONFIRMED"] > 1.0

    def test_dismissed_reduces(self):
        assert VERDICT_MULTIPLIERS["DISMISSED"] < 0.5

    def test_probable_neutral(self):
        assert VERDICT_MULTIPLIERS["PROBABLE"] == 1.0

    def test_doubtful_reduces(self):
        assert VERDICT_MULTIPLIERS["DOUBTFUL"] < 1.0
