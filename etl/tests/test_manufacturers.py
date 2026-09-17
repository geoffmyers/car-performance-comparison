"""Tests for etl.core.manufacturers.ManufacturerNormalizer.

The 2026-09-17 duplicate audit found 106 duplicated (manufacturer, model,
year) keys in the shipped database, several caused by a manufacturer having
more than one spelling in the data (e.g. "Lucid" and "Lucid Motors") that the
normalizer did not know were the same brand. These tests pin the aliases
added to close that gap, and the general normalize()/parse_car_name()
contract the merge key depends on.
"""

import pytest

from etl.core.manufacturers import ManufacturerNormalizer


@pytest.fixture(scope="module")
def normalizer() -> ManufacturerNormalizer:
    return ManufacturerNormalizer()


class TestCorporateSuffixAliases:
    """The specific aliases added to fix the Lucid/Lucid Motors duplicate."""

    @pytest.mark.parametrize(
        ("raw", "canonical"),
        [
            ("Lucid Motors", "Lucid"),
            ("Lucid", "Lucid"),
            ("McLaren Automotive", "McLaren"),
            ("Roush Performance", "Roush"),
            ("Saleen Performance", "Saleen"),
            ("RUF Automobile", "Ruf"),
            ("TVR Engineering Ltd", "TVR"),
        ],
    )
    def test_suffix_variant_normalizes_to_canonical(
        self, normalizer: ManufacturerNormalizer, raw: str, canonical: str
    ):
        assert normalizer.normalize(raw) == canonical

    def test_lucid_and_lucid_motors_normalize_identically(
        self, normalizer: ManufacturerNormalizer
    ):
        assert normalizer.normalize("Lucid Motors") == normalizer.normalize("Lucid")


class TestNormalize:
    def test_known_alias_case_insensitive_lowercase(
        self, normalizer: ManufacturerNormalizer
    ):
        assert normalizer.normalize("bmw") == "BMW"

    def test_already_canonical_passes_through(
        self, normalizer: ManufacturerNormalizer
    ):
        assert normalizer.normalize("Porsche") == "Porsche"

    def test_empty_string_returns_empty(self, normalizer: ManufacturerNormalizer):
        assert normalizer.normalize("") == ""

    def test_unknown_manufacturer_title_cased(
        self, normalizer: ManufacturerNormalizer
    ):
        assert normalizer.normalize("some brand nobody knows") == (
            "Some Brand Nobody Knows"
        )


class TestGetCountry:
    def test_known_manufacturer_returns_country_code(
        self, normalizer: ManufacturerNormalizer
    ):
        assert normalizer.get_country("Porsche") == "DE"

    def test_alias_resolves_before_country_lookup(
        self, normalizer: ManufacturerNormalizer
    ):
        # Lucid Motors must resolve to the same country as Lucid, not "".
        assert normalizer.get_country("Lucid Motors") == normalizer.get_country(
            "Lucid"
        )
        assert normalizer.get_country("Lucid Motors") != ""

    def test_unknown_manufacturer_returns_empty(
        self, normalizer: ManufacturerNormalizer
    ):
        assert normalizer.get_country("Not A Real Manufacturer") == ""


class TestParseCarName:
    def test_simple_make_model(self, normalizer: ManufacturerNormalizer):
        assert normalizer.parse_car_name("Porsche 911") == ("Porsche", "911")

    def test_multi_word_manufacturer(self, normalizer: ManufacturerNormalizer):
        manufacturer, model = normalizer.parse_car_name("Alfa Romeo Giulia")
        assert manufacturer == "Alfa Romeo"
        assert model == "Giulia"

    def test_hyphenated_manufacturer(self, normalizer: ManufacturerNormalizer):
        manufacturer, model = normalizer.parse_car_name("Mercedes-AMG GT")
        assert manufacturer == "Mercedes-AMG"
        assert model == "GT"

    def test_model_prefix_before_manufacturer(
        self, normalizer: ManufacturerNormalizer
    ):
        # "80 Napier" -- 80 was the horsepower, Napier the manufacturer.
        manufacturer, model = normalizer.parse_car_name("80 Napier")
        assert manufacturer == "Napier"
        assert "80" in model

    def test_empty_returns_empty_tuple(self, normalizer: ManufacturerNormalizer):
        assert normalizer.parse_car_name("") == ("", "")

    def test_corporate_suffix_variant_in_full_name(
        self, normalizer: ManufacturerNormalizer
    ):
        manufacturer, model = normalizer.parse_car_name("Lucid Motors Air")
        assert manufacturer == "Lucid"
        assert model == "Air"


class TestExtractManufacturerFromMake:
    def test_manufacturer_only(self, normalizer: ManufacturerNormalizer):
        manufacturer, model = normalizer.extract_manufacturer_from_make("Toyota")
        assert manufacturer == "Toyota"
        assert model == ""

    def test_manufacturer_with_model_leak(self, normalizer: ManufacturerNormalizer):
        manufacturer, model = normalizer.extract_manufacturer_from_make(
            "Toyota Prius"
        )
        assert manufacturer == "Toyota"
        assert model == "Prius"

    def test_empty_returns_empty_tuple(self, normalizer: ManufacturerNormalizer):
        assert normalizer.extract_manufacturer_from_make("") == ("", "")


class TestIsKnown:
    def test_known_manufacturer(self, normalizer: ManufacturerNormalizer):
        assert normalizer.is_known("Porsche") is True

    def test_alias_resolves_to_known(self, normalizer: ManufacturerNormalizer):
        assert normalizer.is_known("Lucid Motors") is True

    def test_unknown_manufacturer(self, normalizer: ManufacturerNormalizer):
        assert normalizer.is_known("Not A Real Manufacturer") is False


class TestListManufacturers:
    def test_no_duplicate_canonical_names(self, normalizer: ManufacturerNormalizer):
        names = normalizer.list_manufacturers()
        assert len(names) == len(set(names))

    def test_lucid_is_the_only_lucid_entry(self, normalizer: ManufacturerNormalizer):
        # "Lucid Motors" must be an alias, not a second manufacturer key --
        # this is the exact defect the 2026-09-17 audit found.
        names = normalizer.list_manufacturers()
        assert "Lucid" in names
        assert "Lucid Motors" not in names
