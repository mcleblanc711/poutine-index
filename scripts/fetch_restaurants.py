#!/usr/bin/env python3
"""
Fetch poutine restaurants from Google Places API for target cities.

Requires GOOGLE_PLACES_API_KEY environment variable.

Usage:
    python scripts/fetch_restaurants.py
    python scripts/fetch_restaurants.py --city "Montreal"
    python scripts/fetch_restaurants.py --dry-run
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# Fast food chains to exclude
FAST_FOOD_BLOCKLIST = {
    "mcdonald's",
    "mcdonalds",
    "mcdonald",
    "burger king",
    "wendy's",
    "wendys",
    "harvey's",
    "harveys",
    "new york fries",
    "smoke's poutinerie",
    "smokes poutinerie",
    "a&w",
    "kfc",
    "kentucky fried chicken",
    "dairy queen",
    "tim hortons",
    "tim horton's",
    "taco bell",
    "subway",
    "popeyes",
    "five guys",
    "costco",
    "walmart",
}

# Google Places API endpoints
PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def get_api_key() -> str:
    """Get Google Places API key from environment."""
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        print("Error: GOOGLE_PLACES_API_KEY environment variable is not set.")
        print("\nTo set up Google Places API:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing one")
        print("3. Enable the Places API")
        print("4. Create an API key")
        print("5. Set the environment variable:")
        print('   export GOOGLE_PLACES_API_KEY="your-api-key"')
        sys.exit(1)
    return api_key


def load_cities(cities_path: Path) -> list[dict]:
    """Load target cities from JSON file."""
    with open(cities_path) as f:
        data = json.load(f)
    return data["cities"]


def is_fast_food(name: str) -> bool:
    """Check if restaurant name matches a fast food chain."""
    name_lower = name.lower()
    return any(chain in name_lower for chain in FAST_FOOD_BLOCKLIST)


def search_restaurants(
    api_key: str,
    lat: float,
    lon: float,
    radius: int = 15000,
    max_results: int = 20,
) -> list[dict]:
    """
    Search for poutine restaurants near given coordinates.

    Args:
        api_key: Google Places API key
        lat: Latitude
        lon: Longitude
        radius: Search radius in meters (default 15km)
        max_results: Maximum number of results to return

    Returns:
        List of restaurant dictionaries
    """
    restaurants = []
    next_page_token = None

    while len(restaurants) < max_results:
        params = {
            "key": api_key,
            "location": f"{lat},{lon}",
            "radius": radius,
            "keyword": "poutine restaurant",
            "type": "restaurant",
        }

        if next_page_token:
            params["pagetoken"] = next_page_token

        response = requests.get(PLACES_NEARBY_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data["status"] not in ("OK", "ZERO_RESULTS"):
            print(f"  API error: {data['status']}")
            if "error_message" in data:
                print(f"  Message: {data['error_message']}")
            break

        for place in data.get("results", []):
            if len(restaurants) >= max_results:
                break

            name = place.get("name", "")
            if is_fast_food(name):
                continue

            restaurants.append({
                "name": name,
                "place_id": place.get("place_id"),
                "address": place.get("vicinity"),
                "lat": place["geometry"]["location"]["lat"],
                "lon": place["geometry"]["location"]["lng"],
                "rating": place.get("rating"),
                "user_ratings_total": place.get("user_ratings_total"),
            })

        next_page_token = data.get("next_page_token")
        if not next_page_token:
            break

        # Google requires a short delay before using next_page_token
        import time
        time.sleep(2)

    return restaurants


def get_restaurant_website(api_key: str, place_id: str) -> Optional[str]:
    """Fetch restaurant website from Place Details API."""
    params = {
        "key": api_key,
        "place_id": place_id,
        "fields": "website",
    }

    response = requests.get(PLACES_DETAILS_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    if data["status"] == "OK":
        return data.get("result", {}).get("website")
    return None


def fetch_all_restaurants(
    api_key: str,
    cities: list[dict],
    target_per_city: int = 15,
    fetch_websites: bool = True,
) -> list[dict]:
    """
    Fetch restaurants for all target cities.

    Args:
        api_key: Google Places API key
        cities: List of city dictionaries with lat/lon
        target_per_city: Target number of restaurants per city
        fetch_websites: Whether to fetch website URLs (additional API calls)

    Returns:
        List of all restaurant dictionaries
    """
    all_restaurants = []

    for city in cities:
        print(f"Fetching restaurants for {city['name']}...")

        restaurants = search_restaurants(
            api_key,
            city["lat"],
            city["lon"],
            max_results=target_per_city,
        )

        for restaurant in restaurants:
            restaurant["city"] = city["name"]

            if fetch_websites and restaurant.get("place_id"):
                website = get_restaurant_website(api_key, restaurant["place_id"])
                restaurant["website"] = website

        print(f"  Found {len(restaurants)} restaurants")
        all_restaurants.extend(restaurants)

    return all_restaurants


def main():
    parser = argparse.ArgumentParser(
        description="Fetch poutine restaurants from Google Places API"
    )
    parser.add_argument(
        "--city",
        help="Fetch for a specific city only",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fetched without making API calls",
    )
    parser.add_argument(
        "--no-websites",
        action="store_true",
        help="Skip fetching website URLs (fewer API calls)",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=15,
        help="Target number of restaurants per city (default: 15)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/restaurants_raw.json"),
        help="Output file path",
    )
    args = parser.parse_args()

    # Load cities
    script_dir = Path(__file__).parent.parent
    cities_path = script_dir / "data" / "cities.json"
    cities = load_cities(cities_path)

    # Filter to specific city if requested
    if args.city:
        cities = [c for c in cities if c["name"].lower() == args.city.lower()]
        if not cities:
            print(f"Error: City '{args.city}' not found in cities.json")
            sys.exit(1)

    if args.dry_run:
        print("Dry run - would fetch restaurants for:")
        for city in cities:
            print(f"  - {city['name']}, {city['province']} ({city['lat']}, {city['lon']})")
        print(f"\nTarget: {args.target} restaurants per city")
        print(f"Total cities: {len(cities)}")
        return

    # Get API key
    api_key = get_api_key()

    # Fetch restaurants
    restaurants = fetch_all_restaurants(
        api_key,
        cities,
        target_per_city=args.target,
        fetch_websites=not args.no_websites,
    )

    # Save results
    output_path = script_dir / args.output
    output_data = {
        "fetch_date": datetime.now().strftime("%Y-%m-%d"),
        "restaurants": restaurants,
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nSaved {len(restaurants)} restaurants to {output_path}")

    # Summary by city
    print("\nSummary by city:")
    city_counts = {}
    for r in restaurants:
        city_counts[r["city"]] = city_counts.get(r["city"], 0) + 1
    for city, count in sorted(city_counts.items()):
        print(f"  {city}: {count}")


if __name__ == "__main__":
    main()
