"""
Tests for price data validation.

These tests validate:
- Price sanity checks (regular poutine $5-25 CAD)
- Size logic (small < regular < large)
- No duplicate restaurant entries per city
- Required fields present
- URL format validation
- Confidence field values
"""

import json
from pathlib import Path

import pytest


# Price bounds
MIN_PRICE = 5.00
MAX_PRICE = 25.00

VALID_CONFIDENCE = {"high", "medium", "low"}


class TestPriceSanity:
    """Tests for price sanity checks."""

    def test_regular_price_within_bounds(self, prices_raw_data: dict):
        """Verify regular poutine prices are between $5-25 CAD."""
        outliers = []

        for entry in prices_raw_data.get("prices", []):
            regular = entry.get("prices", {}).get("regular")
            if regular is None:
                continue

            if regular < MIN_PRICE or regular > MAX_PRICE:
                outliers.append({
                    "restaurant": entry.get("restaurant_name", "Unknown"),
                    "city": entry.get("city", "Unknown"),
                    "price": regular,
                })

        if outliers:
            outlier_str = "; ".join(
                f"{o['restaurant']} ({o['city']}): ${o['price']:.2f}"
                for o in outliers
            )
            pytest.fail(f"Price outliers found (should be ${MIN_PRICE}-${MAX_PRICE}): {outlier_str}")

    def test_all_prices_positive(self, prices_raw_data: dict):
        """Verify all prices are positive numbers."""
        for entry in prices_raw_data.get("prices", []):
            for size, price in entry.get("prices", {}).items():
                if price is not None:
                    assert price > 0, (
                        f"Non-positive price for {size} at "
                        f"{entry.get('restaurant_name', 'Unknown')}: {price}"
                    )


class TestSizeLogic:
    """Tests for price size ordering."""

    def test_small_less_than_regular(self, prices_raw_data: dict):
        """Verify small < regular when both exist."""
        violations = []

        for entry in prices_raw_data.get("prices", []):
            prices = entry.get("prices", {})
            small = prices.get("small")
            regular = prices.get("regular")

            if small is not None and regular is not None and small >= regular:
                violations.append({
                    "restaurant": entry.get("restaurant_name", "Unknown"),
                    "city": entry.get("city", "Unknown"),
                    "small": small,
                    "regular": regular,
                })

        if violations:
            violation_str = "; ".join(
                f"{v['restaurant']}: small=${v['small']:.2f} >= regular=${v['regular']:.2f}"
                for v in violations
            )
            pytest.fail(f"Size ordering violations: {violation_str}")

    def test_regular_less_than_large(self, prices_raw_data: dict):
        """Verify regular < large when both exist."""
        violations = []

        for entry in prices_raw_data.get("prices", []):
            prices = entry.get("prices", {})
            regular = prices.get("regular")
            large = prices.get("large")

            if regular is not None and large is not None and regular >= large:
                violations.append({
                    "restaurant": entry.get("restaurant_name", "Unknown"),
                    "city": entry.get("city", "Unknown"),
                    "regular": regular,
                    "large": large,
                })

        if violations:
            violation_str = "; ".join(
                f"{v['restaurant']}: regular=${v['regular']:.2f} >= large=${v['large']:.2f}"
                for v in violations
            )
            pytest.fail(f"Size ordering violations: {violation_str}")


class TestDuplicates:
    """Tests for duplicate detection."""

    def test_no_duplicate_restaurants_per_city(self, prices_raw_data: dict):
        """Verify no duplicate restaurant entries within a city."""
        seen: dict[str, set] = {}
        duplicates = []

        for entry in prices_raw_data.get("prices", []):
            city = entry.get("city", "Unknown")
            restaurant = entry.get("restaurant_name", "Unknown")

            if city not in seen:
                seen[city] = set()

            if restaurant in seen[city]:
                duplicates.append(f"{restaurant} in {city}")
            else:
                seen[city].add(restaurant)

        assert not duplicates, f"Duplicate restaurants found: {', '.join(duplicates)}"


class TestRequiredFields:
    """Tests for required field presence."""

    def test_required_fields_present(self, prices_raw_data: dict):
        """Verify all required fields are present in each entry."""
        required = {"city", "restaurant_name", "extraction_date", "prices", "confidence"}
        missing = []

        for i, entry in enumerate(prices_raw_data.get("prices", [])):
            entry_missing = required - set(entry.keys())
            if entry_missing:
                restaurant = entry.get("restaurant_name", f"entry[{i}]")
                missing.append(f"{restaurant}: missing {entry_missing}")

        assert not missing, f"Missing required fields: {'; '.join(missing)}"

    def test_at_least_one_price(self, prices_raw_data: dict):
        """Verify each entry has at least one price."""
        no_prices = []

        for entry in prices_raw_data.get("prices", []):
            prices = entry.get("prices", {})
            has_price = any(
                prices.get(size) is not None
                for size in ["small", "regular", "large"]
            )
            if not has_price:
                no_prices.append(entry.get("restaurant_name", "Unknown"))

        assert not no_prices, f"Entries with no prices: {', '.join(no_prices)}"


class TestUrlFormat:
    """Tests for URL format validation."""

    def test_valid_url_format(self, prices_raw_data: dict):
        """Verify source_url is valid http/https URL or null."""
        invalid = []

        for entry in prices_raw_data.get("prices", []):
            url = entry.get("source_url")

            if url is None:
                continue  # Null is allowed

            if not isinstance(url, str):
                invalid.append(f"{entry.get('restaurant_name', 'Unknown')}: not a string")
                continue

            if not url.startswith(("http://", "https://")):
                invalid.append(f"{entry.get('restaurant_name', 'Unknown')}: {url}")

        assert not invalid, f"Invalid URLs: {'; '.join(invalid)}"


class TestConfidence:
    """Tests for confidence field validation."""

    def test_valid_confidence_values(self, prices_raw_data: dict):
        """Verify confidence is one of: high, medium, low."""
        invalid = []

        for entry in prices_raw_data.get("prices", []):
            confidence = entry.get("confidence")

            if confidence and confidence not in VALID_CONFIDENCE:
                invalid.append(
                    f"{entry.get('restaurant_name', 'Unknown')}: '{confidence}'"
                )

        assert not invalid, f"Invalid confidence values: {'; '.join(invalid)}"
