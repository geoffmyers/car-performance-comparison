"""Tests for etl.core.converters.ValueConverter."""

import pytest

from etl.core.converters import ValueConverter


@pytest.fixture
def conv() -> ValueConverter:
    return ValueConverter()


class TestParseTime:
    def test_mm_ss_fraction(self, conv: ValueConverter):
        assert conv.parse_time("6:45.123") == 405.123

    def test_mm_ss_no_fraction(self, conv: ValueConverter):
        assert conv.parse_time("6:45") == 405.0

    def test_plain_seconds_float(self, conv: ValueConverter):
        assert conv.parse_time("45.5") == 45.5

    def test_seconds_with_unit_suffix(self, conv: ValueConverter):
        assert conv.parse_time("45.5s") == 45.5
        assert conv.parse_time("45.5 sec") == 45.5

    def test_empty_returns_none(self, conv: ValueConverter):
        assert conv.parse_time("") is None
        assert conv.parse_time(None) is None

    def test_garbage_returns_none(self, conv: ValueConverter):
        assert conv.parse_time("N/A") is None


class TestParseSpeed:
    def test_mph_only_derives_kmh(self, conv: ValueConverter):
        mph, kmh = conv.parse_speed("200 mph")
        assert mph == 200.0
        assert kmh == pytest.approx(321.9, abs=0.1)

    def test_kmh_only_derives_mph(self, conv: ValueConverter):
        mph, kmh = conv.parse_speed("320 km/h")
        assert kmh == 320.0
        assert mph == pytest.approx(198.8, abs=0.1)

    def test_both_units_present_uses_both(self, conv: ValueConverter):
        mph, kmh = conv.parse_speed("200 mph (321.9 km/h)")
        assert mph == 200.0
        assert kmh == 321.9

    def test_bare_number_assumes_mph(self, conv: ValueConverter):
        mph, kmh = conv.parse_speed("200")
        assert mph == 200.0
        assert kmh == pytest.approx(321.9, abs=0.1)

    def test_empty_returns_none_none(self, conv: ValueConverter):
        assert conv.parse_speed("") == (None, None)


class TestParsePower:
    def test_hp_derives_kw(self, conv: ValueConverter):
        hp, kw = conv.parse_power("500 hp")
        assert hp == 500.0
        assert kw == pytest.approx(373.0, abs=1)

    def test_kw_derives_hp(self, conv: ValueConverter):
        hp, kw = conv.parse_power("373 kW")
        assert kw == 373.0
        assert hp == pytest.approx(500.0, abs=1)

    def test_ps_converts_to_hp_and_kw(self, conv: ValueConverter):
        hp, kw = conv.parse_power("507 PS")
        assert hp == pytest.approx(500.0, abs=1)
        assert kw is not None

    def test_combined_string_prefers_explicit_units(self, conv: ValueConverter):
        hp, kw = conv.parse_power("1,550 kW (2,079 hp; 2,107 PS)")
        assert hp == 2079.0
        assert kw == 1550.0

    def test_bare_number_assumes_hp(self, conv: ValueConverter):
        hp, kw = conv.parse_power("500")
        assert hp == 500.0
        assert kw is not None


class TestParseFloat:
    def test_thousands_separator(self, conv: ValueConverter):
        assert conv.parse_float("1,234.56") == 1234.56

    def test_plain_integer_string(self, conv: ValueConverter):
        assert conv.parse_float("1234") == 1234.0

    @pytest.mark.parametrize("value", ["N/A", "n/a", "-", "", "—"])
    def test_placeholder_values_return_none(self, conv: ValueConverter, value: str):
        assert conv.parse_float(value) is None

    def test_strips_known_unit_suffix(self, conv: ValueConverter):
        assert conv.parse_float("450 hp") == 450.0


class TestParseYear:
    def test_extracts_four_digit_year(self, conv: ValueConverter):
        assert conv.parse_year("Model year 2024 refresh") == "2024"

    def test_no_year_returns_none(self, conv: ValueConverter):
        assert conv.parse_year("no year here") is None

    def test_empty_returns_none(self, conv: ValueConverter):
        assert conv.parse_year("") is None


class TestCleanText:
    def test_strips_wikipedia_footnote(self, conv: ValueConverter):
        assert conv.clean_text("500 hp[1]") == "500 hp"

    def test_strips_citation_needed(self, conv: ValueConverter):
        assert "citation" not in conv.clean_text("Fast car (citation needed)").lower()

    def test_collapses_whitespace(self, conv: ValueConverter):
        assert conv.clean_text("  a   b  ") == "a b"

    def test_empty_returns_empty(self, conv: ValueConverter):
        assert conv.clean_text("") == ""


class TestDetectPropulsion:
    def test_electric_keyword(self, conv: ValueConverter):
        assert conv.detect_propulsion("electric motor", "Model S") == "Electric"

    def test_hybrid_with_ice_components_is_petrol_hybrid(self, conv: ValueConverter):
        assert conv.detect_propulsion("hybrid V6 turbo", "") == "Electric/Petrol"

    def test_diesel_ice(self, conv: ValueConverter):
        assert conv.detect_propulsion("2.0L turbo diesel V6", "") == "Diesel"

    def test_petrol_ice(self, conv: ValueConverter):
        assert conv.detect_propulsion("naturally aspirated V8", "") == "Petrol"

    def test_unknown_returns_empty(self, conv: ValueConverter):
        assert conv.detect_propulsion("", "", "") == ""


class TestUnitConversionHelpers:
    def test_mph_to_kmh(self, conv: ValueConverter):
        assert conv.convert_mph_to_kmh(100) == pytest.approx(160.9, abs=0.1)

    def test_kmh_to_mph(self, conv: ValueConverter):
        assert conv.convert_kmh_to_mph(160.934) == pytest.approx(100.0, abs=0.1)

    def test_hp_to_kw(self, conv: ValueConverter):
        assert conv.convert_hp_to_kw(100) == pytest.approx(74.57, abs=0.1)

    def test_kw_to_hp(self, conv: ValueConverter):
        assert conv.convert_kw_to_hp(100) == pytest.approx(134.1, abs=0.1)


class TestFormatLapTime:
    def test_minutes_and_seconds(self, conv: ValueConverter):
        assert conv.format_lap_time(405.3) == "6:45.30"

    def test_under_a_minute(self, conv: ValueConverter):
        assert conv.format_lap_time(45.2) == "45.20"

    def test_none_returns_empty_string(self, conv: ValueConverter):
        assert conv.format_lap_time(None) == ""
