"""
Tests for data integrity.

These tests validate:
- All JSON files are valid JSON
- cities_final.json validates against schema
- All coordinates are within Canada's bounding box
- All province codes are valid
- Last updated date is not in the future
- No orphaned data references
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


class TestJsonValidity:
    """Tests for JSON file validity."""

    def test_all_json_files_valid(self, data_dir: Path):
        """Verify all JSON files in data/ are parseable."""
        invalid = []

        for json_file in data_dir.glob("*.json"):
            try:
                with open(json_file) as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                invalid.append(f"{json_file.name}: {e}")

        assert not invalid, f"Invalid JSON files: {'; '.join(invalid)}"


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
class TestSchemaValidation:
    """Tests for JSON schema validation."""

    def test_cities_final_validates_against_schema(
        self,
        data_dir: Path,
        schemas_dir: Path,
    ):
        """Verify cities_final.json validates against its schema."""
        with open(data_dir / "cities_final.json") as f:
            data = json.load(f)

        with open(schemas_dir / "city_final.schema.json") as f:
            schema = json.load(f)

        # This will raise ValidationError if invalid
        jsonschema.validate(data, schema)

    def test_minimum_wages_validates_against_schema(
        self,
        data_dir: Path,
        schemas_dir: Path,
    ):
        """Verify minimum_wages.json validates against its schema."""
        with open(data_dir / "minimum_wages.json") as f:
            data = json.load(f)

        with open(schemas_dir / "minimum_wage.schema.json") as f:
            schema = json.load(f)

        jsonschema.validate(data, schema)


class TestCoordinateValidity:
    """Tests for coordinate validity."""

    def test_city_coordinates_within_canada(
        self,
        cities_final_data: dict,
        canada_bounds: dict,
    ):
        """Verify all city coordinates are within Canada's bounding box."""
        out_of_bounds = []

        for city in cities_final_data["cities"]:
            lat = city.get("lat")
            lon = city.get("lon")

            if lat is None or lon is None:
                out_of_bounds.append(f"{city['name']}: missing coordinates")
                continue

            if not (canada_bounds["lat_min"] <= lat <= canada_bounds["lat_max"]):
                out_of_bounds.append(
                    f"{city['name']}: latitude {lat} out of bounds "
                    f"[{canada_bounds['lat_min']}, {canada_bounds['lat_max']}]"
                )

            if not (canada_bounds["lon_min"] <= lon <= canada_bounds["lon_max"]):
                out_of_bounds.append(
                    f"{city['name']}: longitude {lon} out of bounds "
                    f"[{canada_bounds['lon_min']}, {canada_bounds['lon_max']}]"
                )

        assert not out_of_bounds, f"Coordinates out of bounds: {'; '.join(out_of_bounds)}"


class TestProvinceValidity:
    """Tests for province code validity."""

    def test_all_province_codes_valid(
        self,
        cities_final_data: dict,
        valid_province_codes: set,
    ):
        """Verify all province codes are valid Canadian codes."""
        invalid = []

        for city in cities_final_data["cities"]:
            province = city.get("province")
            if province not in valid_province_codes:
                invalid.append(f"{city['name']}: '{province}'")

        assert not invalid, f"Invalid province codes: {', '.join(invalid)}"


class TestDateValidity:
    """Tests for date field validity."""

    def test_last_updated_not_future(self, cities_final_data: dict):
        """Verify last_updated date is not in the future."""
        last_updated = cities_final_data.get("last_updated")
        if last_updated is None:
            pytest.skip("No last_updated field")

        try:
            update_date = datetime.strptime(last_updated, "%Y-%m-%d")
        except ValueError:
            pytest.fail(f"Invalid date format: {last_updated}")

        assert update_date <= datetime.now(), (
            f"last_updated date is in the future: {last_updated}"
        )

    def test_last_updated_format(self, cities_final_data: dict):
        """Verify last_updated is in YYYY-MM-DD format."""
        last_updated = cities_final_data.get("last_updated")
        if last_updated is None:
            pytest.skip("No last_updated field")

        try:
            datetime.strptime(last_updated, "%Y-%m-%d")
        except ValueError:
            pytest.fail(f"Invalid date format (expected YYYY-MM-DD): {last_updated}")


class TestDataReferences:
    """Tests for orphaned data references."""

    def test_cities_reference_valid_provinces(
        self,
        cities_final_data: dict,
        minimum_wages_data: dict,
    ):
        """Verify all cities reference provinces with wage data."""
        available_provinces = set(minimum_wages_data["wages"].keys())
        missing_references = []

        for city in cities_final_data["cities"]:
            province = city.get("province")
            if province and province not in available_provinces:
                missing_references.append(f"{city['name']} -> {province}")

        assert not missing_references, (
            f"Cities reference missing provinces: {', '.join(missing_references)}"
        )

    def test_no_orphaned_restaurant_cities(
        self,
        restaurants_raw_data: dict,
        cities_data: dict,
    ):
        """Verify all restaurants reference valid target cities."""
        target_cities = {c["name"] for c in cities_data["cities"]}
        orphaned = []

        for restaurant in restaurants_raw_data.get("restaurants", []):
            city = restaurant.get("city")
            if city and city not in target_cities:
                orphaned.append(f"{restaurant.get('name', 'Unknown')} -> {city}")

        assert not orphaned, (
            f"Restaurants reference unknown cities: {', '.join(orphaned[:10])}"
            + (f" (and {len(orphaned) - 10} more)" if len(orphaned) > 10 else "")
        )


class TestDataVersioning:
    """Tests for data versioning."""

    def test_data_version_format(self, cities_final_data: dict):
        """Verify data_version follows semver format."""
        version = cities_final_data.get("data_version")
        if version is None:
            pytest.skip("No data_version field")

        import re
        semver_pattern = r"^\d+\.\d+\.\d+$"
        assert re.match(semver_pattern, version), (
            f"Invalid version format (expected X.Y.Z): {version}"
        )
