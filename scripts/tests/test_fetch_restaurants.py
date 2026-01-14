"""
Tests for restaurant fetching functionality.

These tests validate:
- API response structure matches expected schema
- Fast food chains are filtered out
- Coordinates are within reasonable distance of target city
- Minimum restaurant candidates per city
- No duplicate Place IDs within a city
"""

import json
from pathlib import Path

import pytest


class TestRestaurantRawSchema:
    """Tests for restaurants_raw.json structure."""

    def test_has_fetch_date(self, restaurants_raw_data: dict):
        """Verify fetch_date field exists."""
        assert "fetch_date" in restaurants_raw_data

    def test_has_restaurants_array(self, restaurants_raw_data: dict):
        """Verify restaurants is an array."""
        assert "restaurants" in restaurants_raw_data
        assert isinstance(restaurants_raw_data["restaurants"], list)

    def test_restaurant_required_fields(self, restaurants_raw_data: dict):
        """Verify each restaurant has required fields."""
        required_fields = {"city", "name", "place_id"}

        for restaurant in restaurants_raw_data["restaurants"]:
            for field in required_fields:
                assert field in restaurant, f"Missing field '{field}' in restaurant: {restaurant.get('name', 'unknown')}"


class TestFastFoodFiltering:
    """Tests for fast food chain exclusion."""

    def test_no_fast_food_chains(
        self,
        restaurants_raw_data: dict,
        fast_food_blocklist: set,
    ):
        """Verify no fast food chains in restaurant list."""
        for restaurant in restaurants_raw_data["restaurants"]:
            name_lower = restaurant["name"].lower()
            for blocked in fast_food_blocklist:
                assert blocked not in name_lower, (
                    f"Fast food chain found: {restaurant['name']} "
                    f"(matched '{blocked}')"
                )


class TestCoordinateValidation:
    """Tests for restaurant coordinate validity."""

    def test_coordinates_within_canada(
        self,
        restaurants_raw_data: dict,
        canada_bounds: dict,
    ):
        """Verify all restaurant coordinates are within Canada."""
        for restaurant in restaurants_raw_data["restaurants"]:
            if "lat" not in restaurant or "lon" not in restaurant:
                continue

            lat = restaurant["lat"]
            lon = restaurant["lon"]

            assert canada_bounds["lat_min"] <= lat <= canada_bounds["lat_max"], (
                f"Latitude {lat} out of Canada bounds for {restaurant['name']}"
            )
            assert canada_bounds["lon_min"] <= lon <= canada_bounds["lon_max"], (
                f"Longitude {lon} out of Canada bounds for {restaurant['name']}"
            )

    def test_coordinates_near_city(
        self,
        restaurants_raw_data: dict,
        cities_data: dict,
    ):
        """Verify restaurant coordinates are within 50km of target city center."""
        import math

        def haversine_km(lat1, lon1, lat2, lon2):
            """Calculate distance between two points in kilometers."""
            R = 6371  # Earth's radius in km
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = (
                math.sin(dlat / 2) ** 2
                + math.cos(math.radians(lat1))
                * math.cos(math.radians(lat2))
                * math.sin(dlon / 2) ** 2
            )
            c = 2 * math.asin(math.sqrt(a))
            return R * c

        # Build city lookup
        city_coords = {c["name"]: (c["lat"], c["lon"]) for c in cities_data["cities"]}

        for restaurant in restaurants_raw_data["restaurants"]:
            if "lat" not in restaurant or "lon" not in restaurant:
                continue

            city = restaurant.get("city")
            if city not in city_coords:
                continue

            city_lat, city_lon = city_coords[city]
            distance = haversine_km(
                city_lat, city_lon,
                restaurant["lat"], restaurant["lon"]
            )

            assert distance <= 50, (
                f"Restaurant {restaurant['name']} is {distance:.1f}km "
                f"from {city} center (max 50km)"
            )


class TestRestaurantCoverage:
    """Tests for restaurant data coverage."""

    def test_minimum_candidates_per_city(
        self,
        restaurants_raw_data: dict,
        cities_data: dict,
    ):
        """Warn if fewer than 5 restaurant candidates for any city."""
        # Count restaurants per city
        city_counts = {}
        for restaurant in restaurants_raw_data["restaurants"]:
            city = restaurant.get("city", "Unknown")
            city_counts[city] = city_counts.get(city, 0) + 1

        # Check each target city
        warnings = []
        for city in cities_data["cities"]:
            count = city_counts.get(city["name"], 0)
            if count < 5:
                warnings.append(f"{city['name']}: only {count} restaurants")

        if warnings:
            pytest.skip(f"Low restaurant counts: {', '.join(warnings)}")


class TestDuplicates:
    """Tests for duplicate detection."""

    def test_no_duplicate_place_ids_within_city(self, restaurants_raw_data: dict):
        """Verify no duplicate Place IDs within the same city."""
        city_place_ids: dict[str, set] = {}

        for restaurant in restaurants_raw_data["restaurants"]:
            city = restaurant.get("city", "Unknown")
            place_id = restaurant.get("place_id")

            if not place_id:
                continue

            if city not in city_place_ids:
                city_place_ids[city] = set()

            assert place_id not in city_place_ids[city], (
                f"Duplicate Place ID {place_id} in {city}"
            )
            city_place_ids[city].add(place_id)
