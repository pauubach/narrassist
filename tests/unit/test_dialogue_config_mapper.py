"""
Tests para dialogue_config_mapper.

Cubre:
- Mapeo de correction_config a dialogue_style_preference
- Mapeo inverso de dialogue_style_preference a correction_config
- Casos de borde y valores por defecto
"""

import pytest

from narrative_assistant.nlp.dialogue_config_mapper import (
    map_correction_config_to_dialogue_preference,
    map_dialogue_preference_to_correction_config,
)


# =============================================================================
# Tests de mapeo correction_config → dialogue_preference
# =============================================================================


class TestCorrectionConfigToPreference:
    """Tests para map_correction_config_to_dialogue_preference."""

    def test_dialogue_dash_em_maps_to_dash(self):
        """dialogue_dash='em' → 'dash'."""
        pref = map_correction_config_to_dialogue_preference("em", None)
        assert pref == "dash"

    def test_dialogue_dash_en_maps_to_dash(self):
        """dialogue_dash='en' → 'dash'."""
        pref = map_correction_config_to_dialogue_preference("en", None)
        assert pref == "dash"

    def test_dialogue_dash_hyphen_maps_to_dash(self):
        """dialogue_dash='hyphen' → 'dash'."""
        pref = map_correction_config_to_dialogue_preference("hyphen", None)
        assert pref == "dash"

    def test_quote_style_angular_maps_to_guillemets(self):
        """quote_style='angular' → 'guillemets'."""
        pref = map_correction_config_to_dialogue_preference(None, "angular")
        assert pref == "guillemets"

    def test_quote_style_curly_maps_to_quotes_typographic(self):
        """quote_style='curly' → 'quotes_typographic'."""
        pref = map_correction_config_to_dialogue_preference(None, "curly")
        assert pref == "quotes_typographic"

    def test_quote_style_straight_maps_to_quotes(self):
        """quote_style='straight' → 'quotes'."""
        pref = map_correction_config_to_dialogue_preference(None, "straight")
        assert pref == "quotes"

    def test_dialogue_dash_takes_priority_over_quote_style(self):
        """dialogue_dash tiene prioridad sobre quote_style."""
        pref = map_correction_config_to_dialogue_preference("em", "angular")
        assert pref == "dash"  # No "guillemets"

    def test_none_dialogue_dash_allows_quote_style(self):
        """dialogue_dash='none' permite usar quote_style."""
        pref = map_correction_config_to_dialogue_preference("none", "angular")
        assert pref == "guillemets"

    def test_both_explicit_none_maps_to_no_check(self):
        """Ambos 'none' explícitamente → 'no_check' (usuario NO quiere validación)."""
        pref = map_correction_config_to_dialogue_preference("none", "none")
        assert pref == "no_check"

    def test_both_null_defaults_to_dash(self):
        """Ambos None → default 'dash'."""
        pref = map_correction_config_to_dialogue_preference(None, None)
        assert pref == "dash"


# =============================================================================
# Tests de mapeo inverso dialogue_preference → correction_config
# =============================================================================


class TestPreferenceToCorrectionConfig:
    """Tests para map_dialogue_preference_to_correction_config."""

    def test_dash_maps_to_em_and_none(self):
        """'dash' → ('em', 'none')."""
        dash, quote = map_dialogue_preference_to_correction_config("dash")
        assert dash == "em"
        assert quote == "none"

    def test_guillemets_maps_to_none_and_angular(self):
        """'guillemets' → ('none', 'angular')."""
        dash, quote = map_dialogue_preference_to_correction_config("guillemets")
        assert dash == "none"
        assert quote == "angular"

    def test_quotes_maps_to_none_and_straight(self):
        """'quotes' → ('none', 'straight')."""
        dash, quote = map_dialogue_preference_to_correction_config("quotes")
        assert dash == "none"
        assert quote == "straight"

    def test_quotes_typographic_maps_to_none_and_curly(self):
        """'quotes_typographic' → ('none', 'curly')."""
        dash, quote = map_dialogue_preference_to_correction_config("quotes_typographic")
        assert dash == "none"
        assert quote == "curly"

    def test_no_check_maps_to_none_none(self):
        """'no_check' → ('none', 'none')."""
        dash, quote = map_dialogue_preference_to_correction_config("no_check")
        assert dash == "none"
        assert quote == "none"

    def test_unknown_preference_defaults_to_em_none(self):
        """Preferencia desconocida → ('em', 'none')."""
        dash, quote = map_dialogue_preference_to_correction_config("unknown")
        assert dash == "em"
        assert quote == "none"


# =============================================================================
# Tests de roundtrip (ida y vuelta)
# =============================================================================


class TestRoundtrip:
    """Tests para verificar consistencia en ambas direcciones."""

    @pytest.mark.parametrize(
        "preference,expected_dash,expected_quote",
        [
            ("dash", "em", "none"),
            ("guillemets", "none", "angular"),
            ("quotes", "none", "straight"),
            ("quotes_typographic", "none", "curly"),
            ("no_check", "none", "none"),
        ],
    )
    def test_preference_to_config_to_preference(self, preference, expected_dash, expected_quote):
        """preference → config → preference debe ser consistente."""
        # 1. preference → config
        dash, quote = map_dialogue_preference_to_correction_config(preference)
        assert dash == expected_dash
        assert quote == expected_quote

        # 2. config → preference (debe volver al original)
        pref_back = map_correction_config_to_dialogue_preference(dash, quote)
        assert pref_back == preference

    @pytest.mark.parametrize(
        "dialogue_dash,quote_style,expected_pref",
        [
            ("em", "none", "dash"),
            ("en", "none", "dash"),
            ("hyphen", "none", "dash"),
            ("none", "angular", "guillemets"),
            ("none", "curly", "quotes_typographic"),
            ("none", "straight", "quotes"),
            ("none", "none", "no_check"),  # Ambos none explícito = no validar
        ],
    )
    def test_config_to_preference_is_deterministic(
        self, dialogue_dash, quote_style, expected_pref
    ):
        """El mapeo config → preference debe ser determinístico."""
        pref = map_correction_config_to_dialogue_preference(dialogue_dash, quote_style)
        assert pref == expected_pref
