"""Tests for etl.validators.consistency.ConsistencyValidator's duplicate
detection, the gate that is supposed to fail `python -m etl.cli run --validate`
(and CI) before a shipped database can carry duplicate (year, manufacturer,
model) rows again like the 106 the 2026-09-17 audit found.
"""

import pytest

from etl.core.manufacturers import ManufacturerNormalizer
from etl.validators.base import Severity
from etl.validators.consistency import ConsistencyValidator


@pytest.fixture(scope="module")
def normalizer() -> ManufacturerNormalizer:
    return ManufacturerNormalizer()


@pytest.fixture
def validator(normalizer: ManufacturerNormalizer) -> ConsistencyValidator:
    return ConsistencyValidator(normalizer)


class TestFindDuplicates:
    def test_exact_duplicate_is_an_error(self, validator: ConsistencyValidator):
        data = [
            {"year": "2024", "manufacturer": "Porsche", "model": "911 GT3 RS"},
            {"year": "2024", "manufacturer": "Porsche", "model": "911 GT3 RS"},
        ]
        result = validator.validate(data)
        dup_issues = [i for i in result.issues if i.field == "duplicate"]
        assert len(dup_issues) == 1
        assert dup_issues[0].severity == Severity.ERROR
        assert result.is_valid is False

    def test_manufacturer_alias_variant_is_caught_as_duplicate(
        self, validator: ConsistencyValidator
    ):
        # This is the exact shape of the 2026-09-17 finding: two spellings of
        # the same manufacturer for the same car, year and model.
        data = [
            {"year": "2026", "manufacturer": "Lucid", "model": "Air"},
            {"year": "2026", "manufacturer": "Lucid Motors", "model": "Air"},
        ]
        result = validator.validate(data)
        dup_issues = [i for i in result.issues if i.field == "duplicate"]
        assert len(dup_issues) == 1
        assert result.is_valid is False

    def test_distinct_records_produce_no_duplicate_issue(
        self, validator: ConsistencyValidator
    ):
        data = [
            {"year": "2024", "manufacturer": "Porsche", "model": "911 GT3 RS"},
            {"year": "2024", "manufacturer": "Porsche", "model": "911 Turbo S"},
            {"year": "2023", "manufacturer": "Porsche", "model": "911 GT3 RS"},
        ]
        result = validator.validate(data)
        dup_issues = [i for i in result.issues if i.field == "duplicate"]
        assert dup_issues == []
        assert result.is_valid is True

    def test_case_difference_alone_is_still_a_duplicate(
        self, validator: ConsistencyValidator
    ):
        data = [
            {"year": "2024", "manufacturer": "porsche", "model": "911 gt3 rs"},
            {"year": "2024", "manufacturer": "Porsche", "model": "911 GT3 RS"},
        ]
        result = validator.validate(data)
        dup_issues = [i for i in result.issues if i.field == "duplicate"]
        assert len(dup_issues) == 1
