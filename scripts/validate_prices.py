#!/usr/bin/env python3
"""
Validate extracted poutine price data.

Checks for:
- Missing regular size prices
- Outliers (>2 standard deviations from city mean)
- Stale data (>6 months old)
- Schema compliance
- Size ordering (small < regular < large)

Usage:
    python scripts/validate_prices.py
    python scripts/validate_prices.py --strict
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, stdev
from typing import Optional

# Price sanity bounds (CAD)
MIN_PRICE = 5.00
MAX_PRICE = 25.00

# Staleness threshold
STALE_DAYS = 180  # 6 months

# Required confidence values
VALID_CONFIDENCE = {"high", "medium", "low"}


class ValidationError:
    """Represents a validation error or warning."""

    def __init__(self, level: str, restaurant: str, city: str, message: str):
        self.level = level  # "error" or "warning"
        self.restaurant = restaurant
        self.city = city
        self.message = message

    def __str__(self):
        return f"[{self.level.upper()}] {self.city}/{self.restaurant}: {self.message}"


def load_prices(prices_path: Path) -> list[dict]:
    """Load price data from JSON file."""
    with open(prices_path) as f:
        data = json.load(f)
    return data.get("prices", [])


def validate_required_fields(entry: dict) -> list[ValidationError]:
    """Check that required fields are present."""
    errors = []
    required = ["city", "restaurant_name", "extraction_date", "prices", "confidence"]

    city = entry.get("city", "Unknown")
    restaurant = entry.get("restaurant_name", "Unknown")

    for field in required:
        if field not in entry or entry[field] is None:
            errors.append(ValidationError(
                "error", restaurant, city, f"Missing required field: {field}"
            ))

    return errors


def validate_confidence(entry: dict) -> list[ValidationError]:
    """Check that confidence is a valid value."""
    errors = []
    city = entry.get("city", "Unknown")
    restaurant = entry.get("restaurant_name", "Unknown")
    confidence = entry.get("confidence")

    if confidence and confidence not in VALID_CONFIDENCE:
        errors.append(ValidationError(
            "error", restaurant, city,
            f"Invalid confidence value: '{confidence}' (must be high/medium/low)"
        ))

    return errors


def validate_prices(entry: dict) -> list[ValidationError]:
    """Validate price values and ordering."""
    errors = []
    city = entry.get("city", "Unknown")
    restaurant = entry.get("restaurant_name", "Unknown")
    prices = entry.get("prices", {})

    # Check that at least one price exists
    has_price = any(
        prices.get(size) is not None
        for size in ["small", "regular", "large"]
    )
    if not has_price:
        errors.append(ValidationError(
            "error", restaurant, city, "No prices provided"
        ))
        return errors

    # Check for regular price (warning if missing)
    if prices.get("regular") is None:
        errors.append(ValidationError(
            "warning", restaurant, city, "Missing regular size price"
        ))

    # Check price bounds
    for size, price in prices.items():
        if price is None:
            continue
        if price < MIN_PRICE:
            errors.append(ValidationError(
                "warning", restaurant, city,
                f"{size.capitalize()} price ${price:.2f} is below minimum (${MIN_PRICE})"
            ))
        if price > MAX_PRICE:
            errors.append(ValidationError(
                "warning", restaurant, city,
                f"{size.capitalize()} price ${price:.2f} is above maximum (${MAX_PRICE})"
            ))

    # Check size ordering (small < regular < large)
    small = prices.get("small")
    regular = prices.get("regular")
    large = prices.get("large")

    if small is not None and regular is not None and small >= regular:
        errors.append(ValidationError(
            "warning", restaurant, city,
            f"Small (${small:.2f}) >= Regular (${regular:.2f})"
        ))

    if regular is not None and large is not None and regular >= large:
        errors.append(ValidationError(
            "warning", restaurant, city,
            f"Regular (${regular:.2f}) >= Large (${large:.2f})"
        ))

    return errors


def validate_date(entry: dict) -> list[ValidationError]:
    """Check that extraction date is valid and not stale."""
    errors = []
    city = entry.get("city", "Unknown")
    restaurant = entry.get("restaurant_name", "Unknown")
    date_str = entry.get("extraction_date")

    if not date_str:
        return errors  # Already caught by required fields check

    try:
        extraction_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        errors.append(ValidationError(
            "error", restaurant, city,
            f"Invalid date format: '{date_str}' (expected YYYY-MM-DD)"
        ))
        return errors

    # Check if date is in the future
    if extraction_date > datetime.now():
        errors.append(ValidationError(
            "error", restaurant, city,
            f"Extraction date {date_str} is in the future"
        ))
        return errors

    # Check for stale data
    stale_threshold = datetime.now() - timedelta(days=STALE_DAYS)
    if extraction_date < stale_threshold:
        errors.append(ValidationError(
            "warning", restaurant, city,
            f"Data is stale (extracted {date_str}, over {STALE_DAYS} days ago)"
        ))

    return errors


def validate_url(entry: dict) -> list[ValidationError]:
    """Validate source URL format."""
    errors = []
    city = entry.get("city", "Unknown")
    restaurant = entry.get("restaurant_name", "Unknown")
    url = entry.get("source_url")

    if url is None:
        return errors  # Null URL is allowed

    if not isinstance(url, str):
        errors.append(ValidationError(
            "error", restaurant, city, "source_url must be a string or null"
        ))
        return errors

    if not url.startswith(("http://", "https://")):
        errors.append(ValidationError(
            "error", restaurant, city,
            f"Invalid URL format: '{url}' (must start with http:// or https://)"
        ))

    return errors


def find_outliers(prices: list[dict]) -> list[ValidationError]:
    """Find price outliers using standard deviation."""
    errors = []

    # Group by city
    city_prices: dict[str, list[tuple[str, float]]] = {}
    for entry in prices:
        city = entry.get("city")
        restaurant = entry.get("restaurant_name", "Unknown")
        regular = entry.get("prices", {}).get("regular")

        if city and regular is not None:
            if city not in city_prices:
                city_prices[city] = []
            city_prices[city].append((restaurant, regular))

    # Find outliers per city
    for city, price_list in city_prices.items():
        if len(price_list) < 3:
            continue  # Need at least 3 data points

        values = [p[1] for p in price_list]
        city_mean = mean(values)
        city_stdev = stdev(values)

        if city_stdev == 0:
            continue

        for restaurant, price in price_list:
            z_score = abs(price - city_mean) / city_stdev
            if z_score > 2:
                errors.append(ValidationError(
                    "warning", restaurant, city,
                    f"Outlier: ${price:.2f} is {z_score:.1f} std devs from city mean ${city_mean:.2f}"
                ))

    return errors


def find_duplicates(prices: list[dict]) -> list[ValidationError]:
    """Find duplicate restaurant entries within a city."""
    errors = []
    seen: dict[str, set[str]] = {}  # city -> set of restaurant names

    for entry in prices:
        city = entry.get("city", "Unknown")
        restaurant = entry.get("restaurant_name", "Unknown")

        if city not in seen:
            seen[city] = set()

        if restaurant in seen[city]:
            errors.append(ValidationError(
                "error", restaurant, city, "Duplicate restaurant entry"
            ))
        else:
            seen[city].add(restaurant)

    return errors


def validate_all(prices: list[dict]) -> list[ValidationError]:
    """Run all validation checks."""
    all_errors = []

    # Per-entry validations
    for entry in prices:
        all_errors.extend(validate_required_fields(entry))
        all_errors.extend(validate_confidence(entry))
        all_errors.extend(validate_prices(entry))
        all_errors.extend(validate_date(entry))
        all_errors.extend(validate_url(entry))

    # Cross-entry validations
    all_errors.extend(find_outliers(prices))
    all_errors.extend(find_duplicates(prices))

    return all_errors


def filter_valid_prices(
    prices: list[dict],
    errors: list[ValidationError],
) -> list[dict]:
    """Filter out entries with errors (keep those with only warnings)."""
    # Find entries with errors
    error_keys = set()
    for error in errors:
        if error.level == "error":
            error_keys.add((error.city, error.restaurant))

    # Keep entries without errors
    valid = []
    for entry in prices:
        key = (entry.get("city", "Unknown"), entry.get("restaurant_name", "Unknown"))
        if key not in error_keys:
            valid.append(entry)

    return valid


def main():
    parser = argparse.ArgumentParser(
        description="Validate poutine price data"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/prices_raw.json"),
        help="Input file path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/prices_validated.json"),
        help="Output file path for validated data",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only show summary, not individual errors",
    )
    args = parser.parse_args()

    # Load prices
    script_dir = Path(__file__).parent.parent
    input_path = script_dir / args.input

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    prices = load_prices(input_path)
    print(f"Loaded {len(prices)} price entries from {input_path}")

    if not prices:
        print("No price entries to validate.")
        # Write empty validated file
        output_path = script_dir / args.output
        with open(output_path, "w") as f:
            json.dump({"validation_date": datetime.now().strftime("%Y-%m-%d"), "prices": []}, f, indent=2)
        return

    # Validate
    errors = validate_all(prices)

    # Count by level
    error_count = sum(1 for e in errors if e.level == "error")
    warning_count = sum(1 for e in errors if e.level == "warning")

    # Display errors
    if not args.quiet:
        for error in sorted(errors, key=lambda e: (e.city, e.restaurant)):
            print(error)

    print(f"\nValidation complete: {error_count} errors, {warning_count} warnings")

    # Filter valid entries
    if args.strict:
        # In strict mode, warnings are also excluded
        valid_prices = [
            p for p in prices
            if not any(
                e.city == p.get("city") and e.restaurant == p.get("restaurant_name")
                for e in errors
            )
        ]
    else:
        valid_prices = filter_valid_prices(prices, errors)

    print(f"Valid entries: {len(valid_prices)} / {len(prices)}")

    # Save validated data
    output_path = script_dir / args.output
    output_data = {
        "validation_date": datetime.now().strftime("%Y-%m-%d"),
        "prices": valid_prices,
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"Saved validated data to {output_path}")

    # Exit with error code if there were errors
    if error_count > 0:
        sys.exit(1)
    if args.strict and warning_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
