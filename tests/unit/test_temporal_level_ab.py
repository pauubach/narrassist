"""Tests para mejoras de Nivel A (regex hardening) y Nivel B (LLM extraction)."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from narrative_assistant.entities.models import Entity, EntityType
from narrative_assistant.temporal.llm_extraction import (
    LLMTemporalInstance,
    build_instance_id,
    extract_temporal_instances_llm,
    merge_with_regex_instances,
    resolve_entity_ids,
    _parse_llm_response,
    _validate_item,
)
from narrative_assistant.temporal.markers import (
    AGE_PHASE_ALIASES,
    LIFE_EVENT_PHASE_MAP,
    TemporalMarkerExtractor,
    _METAPHORICAL_AGE_THRESHOLD,
)


# ============================================================================
# Level A: Extended Phase Aliases
# ============================================================================


class TestExtendedPhaseAliases:
    """Tests para alias de fase expandidos."""

    def test_new_child_aliases(self):
        """bebé, criatura, crío se mapean a child."""
        for alias in ("bebé", "criatura", "crío", "cría", "chiquillo", "chiquilla"):
            assert AGE_PHASE_ALIASES[alias] == "child", f"{alias} debería ser child"

    def test_new_teen_aliases(self):
        """muchacho, chaval, chico se mapean a teen."""
        for alias in ("muchacho", "muchacha", "chaval", "chavala", "chico", "chica"):
            assert AGE_PHASE_ALIASES[alias] == "teen", f"{alias} debería ser teen"

    def test_new_young_aliases(self):
        """mozo/moza se mapean a young."""
        assert AGE_PHASE_ALIASES["mozo"] == "young"
        assert AGE_PHASE_ALIASES["moza"] == "young"

    def test_new_adult_aliases(self):
        """maduro/madura se mapean a adult."""
        assert AGE_PHASE_ALIASES["maduro"] == "adult"
        assert AGE_PHASE_ALIASES["madura"] == "adult"

    def test_new_elder_aliases(self):
        """anciano, abuelo, senectud se mapean a elder."""
        for alias in ("anciano", "anciana", "abuelo", "abuela", "senectud"):
            assert AGE_PHASE_ALIASES[alias] == "elder", f"{alias} debería ser elder"

    def test_pubertad_is_teen(self):
        assert AGE_PHASE_ALIASES["pubertad"] == "teen"


class TestLifeEventPhaseMap:
    """Tests para inferencia de fase por evento vital."""

    def test_educational_events(self):
        """Eventos educativos mapean a fases esperadas."""
        assert LIFE_EVENT_PHASE_MAP["guardería"][0] == "child"
        assert LIFE_EVENT_PHASE_MAP["instituto"][0] == "teen"
        assert LIFE_EVENT_PHASE_MAP["universidad"][0] == "young"

    def test_elder_events(self):
        """Jubilación y residencia mapean a elder."""
        assert LIFE_EVENT_PHASE_MAP["jubilación"][0] == "elder"
        assert LIFE_EVENT_PHASE_MAP["residencia de ancianos"][0] == "elder"

    def test_military_is_young(self):
        assert LIFE_EVENT_PHASE_MAP["mili"][0] == "young"


class TestMetaphoricalAgeGuard:
    """Tests para guardia contra edades metafóricas."""

    def test_threshold_is_130(self):
        assert _METAPHORICAL_AGE_THRESHOLD == 130

    def test_metaphorical_age_1000_discarded(self):
        """'mil años' no debe generar instancia con edad 1000."""
        extractor = TemporalMarkerExtractor()
        markers = extractor.extract("Tenía mil años encima, estaba agotado.")
        ages = [m.age for m in markers if m.age is not None]
        # 1000 no debe aparecer como edad
        assert 1000 not in ages

    def test_normal_age_passes(self):
        """Edad normal (40) sí pasa el filtro."""
        extractor = TemporalMarkerExtractor()
        markers = extractor.extract("Tenía 40 años cuando empezó.")
        ages = [m.age for m in markers if m.age is not None]
        assert 40 in ages

    def test_edge_age_130_passes(self):
        """130 años es el límite, todavía pasa."""
        extractor = TemporalMarkerExtractor()
        markers = extractor.extract("Tenía 130 años la tortuga.")
        ages = [m.age for m in markers if m.age is not None]
        assert 130 in ages


class TestAdjacentPhaseDetection:
    """Tests para detección de fase adyacente al nombre."""

    def test_anciano_adjacent(self):
        """'el anciano Pedro' debe detectar @phase:elder."""
        extractor = TemporalMarkerExtractor()
        mentions = [(1, 11, 16)]  # "Pedro" at char 11-16
        markers = extractor.extract_with_entities(
            "el anciano Pedro caminaba despacio.", mentions,
        )
        phases = [m.age_phase for m in markers if m.age_phase]
        assert "elder" in phases

    def test_chaval_adjacent(self):
        """'el chaval Pedro' debe detectar @phase:teen."""
        extractor = TemporalMarkerExtractor()
        mentions = [(1, 10, 15)]  # "Pedro" at char 10-15
        markers = extractor.extract_with_entities(
            "el chaval Pedro saltó la valla.", mentions,
        )
        phases = [m.age_phase for m in markers if m.age_phase]
        assert "teen" in phases

    def test_muchacha_adjacent(self):
        """'la muchacha Ana' debe detectar @phase:teen."""
        extractor = TemporalMarkerExtractor()
        mentions = [(2, 12, 15)]  # "Ana" at char 12-15
        markers = extractor.extract_with_entities(
            "la muchacha Ana sonrió tímidamente.", mentions,
        )
        phases = [m.age_phase for m in markers if m.age_phase]
        assert "teen" in phases


class TestLifeEventInference:
    """Tests para inferencia de fase por evento vital en texto."""

    def test_universidad_infers_young(self):
        """Mención de universidad cerca de personaje infiere phase:young."""
        extractor = TemporalMarkerExtractor()
        text = "Ana recordaba sus años de universidad con cariño."
        mentions = [(1, 0, 3)]  # "Ana" at 0-3
        markers = extractor.extract_with_entities(text, mentions)
        phases = [m.age_phase for m in markers if m.age_phase]
        assert "young" in phases

    def test_jubilacion_infers_elder(self):
        """Mención de jubilación infiere phase:elder."""
        extractor = TemporalMarkerExtractor()
        text = "Tras la jubilación, Pedro se dedicó a viajar."
        mentions = [(2, 20, 25)]  # "Pedro" at 20-25
        markers = extractor.extract_with_entities(text, mentions)
        phases = [m.age_phase for m in markers if m.age_phase]
        assert "elder" in phases


class TestNewCharacterAgePatterns:
    """Tests para nuevos patrones de CHARACTER_AGE."""

    def test_rondaba_los_cuarenta(self):
        """'rondaba los 40' detecta edad 40."""
        extractor = TemporalMarkerExtractor()
        markers = extractor.extract("Juan rondaba los 40 cuando llegó al pueblo.")
        ages = [m.age for m in markers if m.age is not None]
        assert 40 in ages

    def test_pasados_los_sesenta(self):
        """'pasados los 60' detecta edad 60."""
        extractor = TemporalMarkerExtractor()
        markers = extractor.extract("Pasados los 60, decidió retirarse.")
        ages = [m.age for m in markers if m.age is not None]
        assert 60 in ages

    def test_apenas_quince(self):
        """'apenas 15 años' detecta edad 15."""
        extractor = TemporalMarkerExtractor()
        markers = extractor.extract("Con apenas 15 años ya trabajaba en el campo.")
        ages = [m.age for m in markers if m.age is not None]
        assert 15 in ages

    def test_cerca_de_los_treinta(self):
        """'cerca de los 30 años' detecta edad 30."""
        extractor = TemporalMarkerExtractor()
        markers = extractor.extract("Estaba cerca de los 30 años cuando se casó.")
        ages = [m.age for m in markers if m.age is not None]
        assert 30 in ages


# ============================================================================
# Level B: LLM Extraction
# ============================================================================


class TestLLMTemporalInstanceBuildId:
    """Tests para build_instance_id."""

    def test_age_instance(self):
        inst = LLMTemporalInstance("Ana", "age", 40, "40 años", 0.9, entity_id=1)
        assert build_instance_id(inst) == "1@age:40"

    def test_phase_instance(self):
        inst = LLMTemporalInstance("Ana", "phase", "elder", "jubilada", 0.8, entity_id=1)
        assert build_instance_id(inst) == "1@phase:elder"

    def test_year_instance(self):
        inst = LLMTemporalInstance("Ana", "year", 1985, "en 1985", 0.9, entity_id=1)
        assert build_instance_id(inst) == "1@year:1985"

    def test_offset_positive(self):
        inst = LLMTemporalInstance("Ana", "offset", 5, "5 años después", 0.8, entity_id=1)
        assert build_instance_id(inst) == "1@offset_years:+5"

    def test_offset_negative(self):
        inst = LLMTemporalInstance("Ana", "offset", -3, "3 años antes", 0.8, entity_id=1)
        assert build_instance_id(inst) == "1@offset_years:-3"

    def test_no_entity_id_returns_none(self):
        inst = LLMTemporalInstance("Ana", "age", 40, "40 años", 0.9, entity_id=None)
        assert build_instance_id(inst) is None


class TestResolveEntityIds:
    """Tests para resolve_entity_ids."""

    def test_resolves_by_name(self):
        instances = [
            LLMTemporalInstance("Ana", "age", 40, "40 años", 0.9),
            LLMTemporalInstance("Pedro", "phase", "young", "joven", 0.8),
        ]
        name_map = {"ana": 1, "pedro": 2}
        resolved = resolve_entity_ids(instances, name_map)
        assert len(resolved) == 2
        assert resolved[0].entity_id == 1
        assert resolved[1].entity_id == 2

    def test_unknown_name_filtered(self):
        instances = [
            LLMTemporalInstance("Desconocido", "age", 30, "30 años", 0.9),
        ]
        resolved = resolve_entity_ids(instances, {"ana": 1})
        assert len(resolved) == 0


class TestMergeWithRegex:
    """Tests para merge_with_regex_instances."""

    def test_new_instance_passes(self):
        """LLM instance no existente en regex pasa el merge."""
        regex_ids = {"1@age:40"}
        llm = [LLMTemporalInstance("Ana", "phase", "elder", "jubilada", 0.8, entity_id=1)]
        new = merge_with_regex_instances(regex_ids, llm)
        assert len(new) == 1

    def test_duplicate_instance_filtered(self):
        """LLM instance que ya existe en regex se descarta."""
        regex_ids = {"1@age:40"}
        llm = [LLMTemporalInstance("Ana", "age", 40, "40 años", 0.9, entity_id=1)]
        new = merge_with_regex_instances(regex_ids, llm)
        assert len(new) == 0


class TestValidateItem:
    """Tests para _validate_item."""

    def test_valid_age_item(self):
        item = {
            "entity": "Ana",
            "type": "age",
            "value": 40,
            "evidence": "tenía 40 años",
            "confidence": 0.9,
        }
        result = _validate_item(item, {"ana"}, "Ana tenía 40 años", 0.6)
        assert result is not None
        assert result.instance_type == "age"
        assert result.value == 40

    def test_unknown_entity_rejected(self):
        item = {
            "entity": "Desconocido",
            "type": "age",
            "value": 40,
            "evidence": "40 años",
            "confidence": 0.9,
        }
        result = _validate_item(item, {"ana"}, "texto", 0.6)
        assert result is None

    def test_low_confidence_rejected(self):
        item = {
            "entity": "Ana",
            "type": "age",
            "value": 40,
            "evidence": "40 años",
            "confidence": 0.3,
        }
        result = _validate_item(item, {"ana"}, "Ana tenía 40 años", 0.6)
        assert result is None

    def test_invalid_type_rejected(self):
        item = {
            "entity": "Ana",
            "type": "invalid_type",
            "value": 40,
            "evidence": "40 años",
            "confidence": 0.9,
        }
        result = _validate_item(item, {"ana"}, "texto", 0.6)
        assert result is None

    def test_age_over_130_rejected(self):
        item = {
            "entity": "Ana",
            "type": "age",
            "value": 500,
            "evidence": "500 años",
            "confidence": 0.9,
        }
        result = _validate_item(item, {"ana"}, "texto", 0.6)
        assert result is None

    def test_invalid_phase_rejected(self):
        item = {
            "entity": "Ana",
            "type": "phase",
            "value": "bebé",
            "evidence": "era un bebé",
            "confidence": 0.9,
        }
        result = _validate_item(item, {"ana"}, "era un bebé", 0.6)
        assert result is None  # "bebé" is not in _VALID_PHASES

    def test_evidence_not_in_text_reduces_confidence(self):
        """Evidencia inventada reduce confianza y puede caer bajo umbral."""
        item = {
            "entity": "Ana",
            "type": "age",
            "value": 40,
            "evidence": "esto no está en el texto original",
            "confidence": 0.7,
        }
        # 0.7 * 0.6 = 0.42 < 0.6 → rejected
        result = _validate_item(item, {"ana"}, "Ana vivía en Madrid", 0.6)
        assert result is None


class TestParseLLMResponse:
    """Tests para _parse_llm_response."""

    def test_valid_json_array(self):
        response = json.dumps([
            {"entity": "Ana", "type": "age", "value": 40, "evidence": "40 años", "confidence": 0.9}
        ])
        instances = _parse_llm_response(response, ["Ana"], "Ana tenía 40 años", 0.6)
        assert len(instances) == 1
        assert instances[0].value == 40

    def test_json_with_extra_text(self):
        """LLM a veces envuelve JSON con texto extra."""
        response = 'Aquí está el resultado:\n[{"entity": "Ana", "type": "phase", "value": "elder", "evidence": "jubilada", "confidence": 0.8}]\nEso es todo.'
        instances = _parse_llm_response(response, ["Ana"], "Ana, ya jubilada", 0.6)
        assert len(instances) == 1

    def test_empty_array(self):
        instances = _parse_llm_response("[]", ["Ana"], "texto", 0.6)
        assert len(instances) == 0

    def test_invalid_json(self):
        instances = _parse_llm_response("esto no es json", ["Ana"], "texto", 0.6)
        assert len(instances) == 0

    def test_no_json_at_all(self):
        instances = _parse_llm_response("No se detectó información temporal.", ["Ana"], "texto", 0.6)
        assert len(instances) == 0


class TestExtractTemporalInstancesLLMGraceful:
    """Tests para graceful degradation cuando LLM no está disponible."""

    @patch("narrative_assistant.llm.client.is_llm_available", return_value=False)
    def test_returns_empty_when_llm_unavailable(self, mock_avail):
        result = extract_temporal_instances_llm("texto", ["Ana"])
        assert result == []

    def test_returns_empty_for_empty_input(self):
        result = extract_temporal_instances_llm("", ["Ana"])
        assert result == []

    def test_returns_empty_for_no_entities(self):
        result = extract_temporal_instances_llm("texto", [])
        assert result == []
