#!/usr/bin/env python3
"""
Aggregate validated price data into city-level statistics.

Reads validated price data and minimum wage data, calculates per-city
statistics, and outputs the final data file for the frontend.

Usage:
    python scripts/aggregate_data.py
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Optional


def load_json(path: Path) -> dict:
    """Load JSON file."""
    with open(path) as f:
        return json.load(f)


def load_cities(script_dir: Path) -> list[dict]:
    """Load target cities."""
    data = load_json(script_dir / "data" / "cities.json")
    return data["cities"]


def load_minimum_wages(script_dir: Path) -> dict[str, float]:
    """Load minimum wages by province code."""
    data = load_json(script_dir / "data" / "minimum_wages.json")
    return {code: info["hourly_wage"] for code, info in data["wages"].items()}


def load_validated_prices(script_dir: Path) -> list[dict]:
    """Load validated price entries."""
    data = load_json(script_dir / "data" / "prices_validated.json")
    return data.get("prices", [])


def calculate_stats(values: list[float]) -> Optional[dict]:
    """Calculate statistics for a list of values."""
    if not values:
        return None

    return {
        "mean": round(mean(values), 2),
        "median": round(median(values), 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
    }


def aggregate_city_data(
    city: dict,
    prices: list[dict],
    min_wage: float,
) -> dict:
    """
    Aggregate price data for a single city.

    Args:
        city: City information (name, province, lat, lon)
        prices: List of price entries for this city
        min_wage: Provincial minimum wage

    Returns:
        Aggregated city data dictionary
    """
    # Extract prices by size
    small_prices = [
        p["prices"]["small"]
        for p in prices
        if p["prices"].get("small") is not None
    ]
    regular_prices = [
        p["prices"]["regular"]
        for p in prices
        if p["prices"].get("regular") is not None
    ]
    large_prices = [
        p["prices"]["large"]
        for p in prices
        if p["prices"].get("large") is not None
    ]

    # Calculate statistics
    price_stats = {
        "small": calculate_stats(small_prices),
        "regular": calculate_stats(regular_prices),
        "large": calculate_stats(large_prices),
    }

    # Calculate affordability index
    # (regular_price / min_wage) * 60 = minutes of work
    regular_mean = price_stats["regular"]["mean"] if price_stats["regular"] else None
    if regular_mean is not None and min_wage > 0:
        affordability_index = round((regular_mean / min_wage) * 60, 2)
    else:
        affordability_index = 0

    return {
        "name": city["name"],
        "province": city["province"],
        "lat": city["lat"],
        "lon": city["lon"],
        "prices": price_stats,
        "sample_size": len(prices),
        "minimum_wage": min_wage,
        "affordability_index": affordability_index,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate price data into city-level statistics"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/cities_final.json"),
        help="Output file path",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent.parent

    # Load data
    print("Loading data...")
    cities = load_cities(script_dir)
    min_wages = load_minimum_wages(script_dir)
    prices = load_validated_prices(script_dir)

    print(f"  {len(cities)} target cities")
    print(f"  {len(min_wages)} provinces with wage data")
    print(f"  {len(prices)} validated price entries")

    # Group prices by city
    prices_by_city: dict[str, list[dict]] = {}
    for entry in prices:
        city_name = entry.get("city")
        if city_name:
            if city_name not in prices_by_city:
                prices_by_city[city_name] = []
            prices_by_city[city_name].append(entry)

    # Aggregate each city
    print("\nAggregating city data...")
    aggregated_cities = []
    missing_wage = []

    for city in cities:
        province = city["province"]
        min_wage = min_wages.get(province)

        if min_wage is None:
            missing_wage.append((city["name"], province))
            min_wage = 0

        city_prices = prices_by_city.get(city["name"], [])
        aggregated = aggregate_city_data(city, city_prices, min_wage)
        aggregated_cities.append(aggregated)

        status = f"{len(city_prices)} restaurants"
        if not city_prices:
            status = "no data"
        print(f"  {city['name']}: {status}")

    # Warn about missing wage data
    if missing_wage:
        print("\nWarning: Missing minimum wage data for:")
        for city_name, province in missing_wage:
            print(f"  {city_name} ({province})")

    # Build output
    output_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "data_version": "1.0.0",
        "cities": aggregated_cities,
    }

    # Save
    output_path = script_dir / args.output
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nSaved aggregated data to {output_path}")

    # Summary
    cities_with_data = sum(1 for c in aggregated_cities if c["sample_size"] > 0)
    total_samples = sum(c["sample_size"] for c in aggregated_cities)
    print(f"\nSummary:")
    print(f"  Cities with data: {cities_with_data} / {len(cities)}")
    print(f"  Total samples: {total_samples}")

    if cities_with_data > 0:
        # Price range
        regular_prices = [
            c["prices"]["regular"]["mean"]
            for c in aggregated_cities
            if c["prices"]["regular"] is not None
        ]
        if regular_prices:
            print(f"  Regular price range: ${min(regular_prices):.2f} - ${max(regular_prices):.2f}")

        # Affordability range
        affordability = [
            c["affordability_index"]
            for c in aggregated_cities
            if c["affordability_index"] > 0
        ]
        if affordability:
            print(f"  Affordability range: {min(affordability):.0f} - {max(affordability):.0f} minutes")


if __name__ == "__main__":
    main()
