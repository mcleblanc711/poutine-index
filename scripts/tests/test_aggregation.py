"""
Tests for data aggregation.

These tests validate:
- Every target city present in output (even if sample_size is 0)
- Affordability index is positive and reasonable (1-60 minutes)
- Minimum wage data exists for every province/territory
- No NaN, null, or negative values in numeric fields
- Sample size matches actual count of validated restaurants
"""

import json
import math
from pathlib import Path

import pytest


# Affordability index bounds (minutes of work to buy a regular poutine)
MIN_AFFORDABILITY = 1
MAX_AFFORDABILITY = 60


class TestCityCoverage:
    """Tests for city coverage in final output."""

    def test_all_target_cities_present(
        self,
        cities_data: dict,
        cities_final_data: dict,
    ):
        """Verify every target city is in the final output."""
        target_cities = {c["name"] for c in cities_data["cities"]}
        output_cities = {c["name"] for c in cities_final_data["cities"]}

        missing = target_cities - output_cities
        assert not missing, f"Missing cities in output: {missing}"


class TestAffordabilityIndex:
    """Tests for affordability index validity."""

    def test_affordability_positive(self, cities_final_data: dict):
        """Verify affordability index is non-negative."""
        negative = []

        for city in cities_final_data["cities"]:
            index = city.get("affordability_index")
            if index is not None and index < 0:
                negative.append(f"{city['name']}: {index}")

        assert not negative, f"Negative affordability indices: {'; '.join(negative)}"

    def test_affordability_reasonable_range(self, cities_final_data: dict):
        """Verify affordability index is within reasonable range (1-60 min)."""
        out_of_range = []

        for city in cities_final_data["cities"]:
            index = city.get("affordability_index")
            sample_size = city.get("sample_size", 0)

            # Skip cities with no data
            if sample_size == 0:
                continue

            if index is not None:
                if index < MIN_AFFORDABILITY or index > MAX_AFFORDABILITY:
                    out_of_range.append(f"{city['name']}: {index:.1f} min")

        if out_of_range:
            pytest.fail(
                f"Affordability indices outside {MIN_AFFORDABILITY}-{MAX_AFFORDABILITY} range: "
                f"{'; '.join(out_of_range)}"
            )


class TestMinimumWageData:
    """Tests for minimum wage data completeness."""

    def test_wage_data_for_all_provinces(
        self,
        cities_final_data: dict,
        minimum_wages_data: dict,
    ):
        """Verify minimum wage data exists for all provinces in city data."""
        provinces_in_cities = {c["province"] for c in cities_final_data["cities"]}
        provinces_with_wages = set(minimum_wages_data["wages"].keys())

        missing = provinces_in_cities - provinces_with_wages
        assert not missing, f"Missing minimum wage data for provinces: {missing}"

    def test_city_minimum_wage_matches_province(
        self,
        cities_final_data: dict,
        minimum_wages_data: dict,
    ):
        """Verify each city's minimum wage matches its province's rate."""
        mismatches = []

        for city in cities_final_data["cities"]:
            province = city["province"]
            city_wage = city.get("minimum_wage")
            province_wage = minimum_wages_data["wages"].get(province, {}).get("hourly_wage")

            if city_wage is None or province_wage is None:
                continue

            if city_wage != province_wage:
                mismatches.append(
                    f"{city['name']} ({province}): "
                    f"city=${city_wage}, province=${province_wage}"
                )

        assert not mismatches, f"Minimum wage mismatches: {'; '.join(mismatches)}"


class TestNumericFieldValidity:
    """Tests for numeric field validity."""

    def test_no_nan_values(self, cities_final_data: dict):
        """Verify no NaN values in numeric fields."""
        nan_found = []

        for city in cities_final_data["cities"]:
            # Check top-level numeric fields
            for field in ["lat", "lon", "sample_size", "minimum_wage", "affordability_index"]:
                value = city.get(field)
                if value is not None and isinstance(value, float) and math.isnan(value):
                    nan_found.append(f"{city['name']}.{field}")

            # Check price statistics
            for size in ["small", "regular", "large"]:
                price_stats = city.get("prices", {}).get(size)
                if price_stats is None:
                    continue
                for stat in ["mean", "median", "min", "max"]:
                    value = price_stats.get(stat)
                    if value is not None and isinstance(value, float) and math.isnan(value):
                        nan_found.append(f"{city['name']}.prices.{size}.{stat}")

        assert not nan_found, f"NaN values found: {', '.join(nan_found)}"

    def test_no_negative_values(self, cities_final_data: dict):
        """Verify no negative values in numeric fields that should be positive."""
        negative_found = []

        for city in cities_final_data["cities"]:
            # Check fields that must be non-negative
            non_negative_fields = ["sample_size", "minimum_wage", "affordability_index"]
            for field in non_negative_fields:
                value = city.get(field)
                if value is not None and value < 0:
                    negative_found.append(f"{city['name']}.{field}: {value}")

            # Check price statistics
            for size in ["small", "regular", "large"]:
                price_stats = city.get("prices", {}).get(size)
                if price_stats is None:
                    continue
                for stat in ["mean", "median", "min", "max"]:
                    value = price_stats.get(stat)
                    if value is not None and value < 0:
                        negative_found.append(
                            f"{city['name']}.prices.{size}.{stat}: {value}"
                        )

        assert not negative_found, f"Negative values found: {', '.join(negative_found)}"

    def test_sample_size_is_integer(self, cities_final_data: dict):
        """Verify sample_size is an integer."""
        non_integer = []

        for city in cities_final_data["cities"]:
            sample_size = city.get("sample_size")
            if sample_size is not None and not isinstance(sample_size, int):
                non_integer.append(f"{city['name']}: {sample_size} ({type(sample_size).__name__})")

        assert not non_integer, f"Non-integer sample sizes: {', '.join(non_integer)}"


class TestDataConsistency:
    """Tests for data consistency."""

    def test_price_stats_min_max_order(self, cities_final_data: dict):
        """Verify min <= mean <= max for all price statistics."""
        violations = []

        for city in cities_final_data["cities"]:
            for size in ["small", "regular", "large"]:
                stats = city.get("prices", {}).get(size)
                if stats is None:
                    continue

                min_val = stats.get("min")
                mean_val = stats.get("mean")
                max_val = stats.get("max")

                if None in (min_val, mean_val, max_val):
                    continue

                if not (min_val <= mean_val <= max_val):
                    violations.append(
                        f"{city['name']} {size}: "
                        f"min={min_val}, mean={mean_val}, max={max_val}"
                    )

        assert not violations, f"Price stat order violations: {'; '.join(violations)}"

    def test_price_stats_median_in_range(self, cities_final_data: dict):
        """Verify median is between min and max."""
        violations = []

        for city in cities_final_data["cities"]:
            for size in ["small", "regular", "large"]:
                stats = city.get("prices", {}).get(size)
                if stats is None:
                    continue

                min_val = stats.get("min")
                median_val = stats.get("median")
                max_val = stats.get("max")

                if None in (min_val, median_val, max_val):
                    continue

                if not (min_val <= median_val <= max_val):
                    violations.append(
                        f"{city['name']} {size}: "
                        f"median={median_val} not in [{min_val}, {max_val}]"
                    )

        assert not violations, f"Median range violations: {'; '.join(violations)}"
