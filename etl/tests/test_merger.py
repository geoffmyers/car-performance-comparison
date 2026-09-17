"""Tests for etl.core.merger.DataMerger, with emphasis on the duplicate-key
regression from the 2026-09-17 audit: 106 duplicated (manufacturer, model,
year) keys shipped in the database, several because two spellings of the same
manufacturer ("Lucid" / "Lucid Motors") hashed to two different car_ids and so
were never collapsed by deduplicate().
"""

import pytest

from etl.core.manufacturers import ManufacturerNormalizer
from etl.core.merger import DataMerger, generate_car_id
from etl.core.schema import Schema


@pytest.fixture(scope="module")
def normalizer() -> ManufacturerNormalizer:
    return ManufacturerNormalizer()


@pytest.fixture(scope="module")
def schema() -> Schema:
    return Schema()


@pytest.fixture
def merger(normalizer: ManufacturerNormalizer, schema: Schema) -> DataMerger:
    return DataMerger(normalizer, schema)


class TestGenerateCarId:
    """generate_car_id() itself only folds case/punctuation - it has no
    knowledge of manufacturer aliases. That resolution has to happen before
    the call, in DataMerger."""

    def test_deterministic(self):
        assert generate_car_id("2024", "Porsche", "911 GT3 RS") == generate_car_id(
            "2024", "Porsche", "911 GT3 RS"
        )

    def test_case_and_punctuation_insensitive(self):
        assert generate_car_id("2024", "Porsche", "911 GT3 RS") == generate_car_id(
            "2024", "PORSCHE", "911-GT3-RS"
        )

    def test_different_manufacturer_spelling_hashes_differently_on_its_own(self):
        # This is exactly the bug: generate_car_id() alone does NOT know
        # "Lucid" and "Lucid Motors" are the same brand.
        assert generate_car_id("2026", "Lucid", "Air") != generate_car_id(
            "2026", "Lucid Motors", "Air"
        )


class TestCreateKeyResolvesAliases:
    def test_lucid_and_lucid_motors_share_a_key(self, merger: DataMerger):
        car_a = {"year": "2026", "manufacturer": "Lucid", "model": "Air"}
        car_b = {"year": "2026", "manufacturer": "Lucid Motors", "model": "Air"}
        assert merger._create_key(car_a) == merger._create_key(car_b)

    def test_key_without_year(self, merger: DataMerger):
        car_a = {"manufacturer": "Lucid", "model": "Air"}
        car_b = {"manufacturer": "Lucid Motors", "model": "Air"}
        assert merger._create_key(car_a, include_year=False) == merger._create_key(
            car_b, include_year=False
        )


class TestStripManufacturerPrefix:
    """One source (Car & Driver) repeats the manufacturer inside the model
    field ("Audi A6 Allroad" where manufacturer is already "Audi"), which
    otherwise escapes both the merge key and the car_id hash and ships the
    same car twice - the exact defect class of the 2026-09-17 audit, one
    field over from the manufacturer-alias case."""

    @pytest.mark.parametrize(
        ("manufacturer", "model", "expected"),
        [
            ("Audi", "Audi A6 Allroad", "A6 Allroad"),
            ("Chevrolet", "Chevrolet TrailBlazer", "TrailBlazer"),
            ("Nissan", "Nissan GT-R", "GT-R"),
            ("Toyota", "Toyota GR86", "GR86"),
            # Case-insensitive match.
            ("Audi", "AUDI A6 Allroad", "A6 Allroad"),
        ],
    )
    def test_strips_repeated_manufacturer(
        self, merger: DataMerger, manufacturer: str, model: str, expected: str
    ):
        assert merger._strip_manufacturer_prefix(model, manufacturer) == expected

    def test_does_not_strip_when_model_has_no_prefix(self, merger: DataMerger):
        assert merger._strip_manufacturer_prefix("A6 Allroad", "Audi") == "A6 Allroad"

    def test_does_not_strip_a_coincidental_partial_word_match(
        self, merger: DataMerger
    ):
        # "Audio" must not be treated as "Audi" + something.
        assert (
            merger._strip_manufacturer_prefix("Audio System Edition", "Audi")
            == "Audio System Edition"
        )

    def test_empty_inputs(self, merger: DataMerger):
        assert merger._strip_manufacturer_prefix("", "Audi") == ""
        assert merger._strip_manufacturer_prefix("A6 Allroad", "") == "A6 Allroad"

    def test_create_key_unifies_prefixed_and_plain_model(self, merger: DataMerger):
        car_a = {"year": "2020", "manufacturer": "Audi", "model": "A6 Allroad"}
        car_b = {"year": "2020", "manufacturer": "Audi", "model": "Audi A6 Allroad"}
        assert merger._create_key(car_a) == merger._create_key(car_b)

    def test_generate_car_id_unifies_prefixed_and_plain_model(
        self, merger: DataMerger
    ):
        car_a = {"year": "2020", "manufacturer": "Audi", "model": "A6 Allroad"}
        car_b = {"year": "2020", "manufacturer": "Audi", "model": "Audi A6 Allroad"}
        assert merger._generate_car_id(car_a) == merger._generate_car_id(car_b)

    def test_deduplicate_collapses_prefixed_variant_and_keeps_shorter_model(
        self, merger: DataMerger
    ):
        records = [
            {
                "year": "2020",
                "manufacturer": "Audi",
                "model": "Audi A6 Allroad",
                "sources": "Car & Driver",
            },
            {
                "year": "2020",
                "manufacturer": "Audi",
                "model": "A6 Allroad",
                "power_hp": "335",
                "sources": "EPA",
            },
        ]
        result = merger.deduplicate(records)
        assert len(result) == 1
        assert result[0]["model"] == "A6 Allroad"
        assert result[0]["power_hp"] == "335"


class TestGenerateCarIdViaMerger:
    """DataMerger._generate_car_id() is what actually gets called by
    deduplicate(); it must resolve the alias before hashing."""

    def test_lucid_and_lucid_motors_share_a_car_id(self, merger: DataMerger):
        car_a = {"year": "2026", "manufacturer": "Lucid", "model": "Air"}
        car_b = {"year": "2026", "manufacturer": "Lucid Motors", "model": "Air"}
        assert merger._generate_car_id(car_a) == merger._generate_car_id(car_b)


class TestDeduplicate:
    def test_collapses_alias_variant_duplicates(self, merger: DataMerger):
        records = [
            {
                "year": "2026",
                "manufacturer": "Lucid",
                "model": "Air",
                "power_hp": "819",
                "sources": "Car & Driver",
            },
            {
                "year": "2026",
                "manufacturer": "Lucid Motors",
                "model": "Air",
                "top_speed_mph": "168",
                "sources": "Wikipedia",
            },
        ]
        result = merger.deduplicate(records)
        assert len(result) == 1
        merged = result[0]
        # Values from both records survive the merge.
        assert merged["power_hp"] == "819"
        assert merged["top_speed_mph"] == "168"

    def test_true_duplicates_merge_to_one_record(self, merger: DataMerger):
        records = [
            {"year": "2024", "manufacturer": "Porsche", "model": "911 GT3 RS"},
            {"year": "2024", "manufacturer": "Porsche", "model": "911 GT3 RS"},
        ]
        result = merger.deduplicate(records)
        assert len(result) == 1

    def test_distinct_cars_are_not_merged(self, merger: DataMerger):
        records = [
            {"year": "2024", "manufacturer": "Porsche", "model": "911 GT3 RS"},
            {"year": "2024", "manufacturer": "Porsche", "model": "911 Turbo S"},
            {"year": "2023", "manufacturer": "Porsche", "model": "911 GT3 RS"},
        ]
        result = merger.deduplicate(records)
        assert len(result) == 3

    def test_every_result_record_has_a_car_id(self, merger: DataMerger):
        records = [
            {"year": "2024", "manufacturer": "Porsche", "model": "911 GT3 RS"},
            {"year": "2026", "manufacturer": "Lucid Motors", "model": "Air"},
        ]
        result = merger.deduplicate(records)
        assert all(r.get("car_id") for r in result)

    def test_stale_car_id_on_input_is_ignored_and_recomputed(
        self, merger: DataMerger
    ):
        # A record carrying a car_id computed before an alias fix (or by one
        # of the standalone update scripts, before they shared DataMerger)
        # must not block regrouping: deduplicate() always recomputes car_id
        # from the record's own year/manufacturer/model.
        records = [
            {
                "year": "2026",
                "manufacturer": "Lucid",
                "model": "Air",
                "car_id": "stale0000000001",
            },
            {
                "year": "2026",
                "manufacturer": "Lucid Motors",
                "model": "Air",
                "car_id": "stale0000000002",
            },
        ]
        result = merger.deduplicate(records)
        assert len(result) == 1
        assert result[0]["car_id"] not in ("stale0000000001", "stale0000000002")


class TestMergeInto:
    def test_fills_empty_fields_without_overwriting(self, merger: DataMerger):
        existing = {"manufacturer": "Porsche", "model": "911", "power_hp": "500"}
        new = {"power_hp": "9999", "torque": "450 lb-ft"}
        merger._merge_into(existing, new)
        assert existing["power_hp"] == "500"  # not overwritten
        assert existing["torque"] == "450 lb-ft"  # filled in

    def test_propulsion_upgrades_to_more_specific(self, merger: DataMerger):
        existing = {"propulsion": "ICE"}
        new = {"propulsion": "Petrol"}
        merger._merge_into(existing, new)
        assert existing["propulsion"] == "Petrol"

    def test_propulsion_does_not_downgrade(self, merger: DataMerger):
        existing = {"propulsion": "Petrol"}
        new = {"propulsion": "ICE"}
        merger._merge_into(existing, new)
        assert existing["propulsion"] == "Petrol"

    def test_sources_are_combined_without_duplicates(self, merger: DataMerger):
        existing = {"sources": "Car & Driver"}
        new = {"source": "Wikipedia"}
        merger._merge_into(existing, new)
        sources = [s.strip() for s in existing["sources"].split(",")]
        assert "Car & Driver" in sources
        assert "Wikipedia" in sources
        assert len(sources) == 2

    def test_merging_same_source_twice_does_not_duplicate(self, merger: DataMerger):
        existing = {"sources": "Car & Driver"}
        new = {"source": "Car & Driver"}
        merger._merge_into(existing, new)
        sources = [s.strip() for s in existing["sources"].split(",")]
        assert sources == ["Car & Driver"]


class TestNormalizeModel:
    def test_strips_review_suffix(self, merger: DataMerger):
        assert merger._normalize_model("Camaro ZL1 Test") == merger._normalize_model(
            "Camaro ZL1"
        )

    def test_strips_parenthetical_year(self, merger: DataMerger):
        assert "2024" not in merger._normalize_model("Air (2024)")

    def test_lowercases(self, merger: DataMerger):
        assert merger._normalize_model("GT3 RS") == merger._normalize_model("gt3 rs")
