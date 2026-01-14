#!/usr/bin/env python3
"""
Validate JSON data files against their schemas.

Usage:
    python scripts/validate_schemas.py
    python scripts/validate_schemas.py --verbose
"""

import argparse
import json
import sys
from pathlib import Path

import jsonschema
from jsonschema import Draft7Validator, ValidationError


# Mapping of data files to their schemas
FILE_SCHEMA_MAP = {
    "data/restaurants_raw.json": "schemas/restaurant_raw.schema.json",
    "data/cities_final.json": "schemas/city_final.schema.json",
    "data/minimum_wages.json": "schemas/minimum_wage.schema.json",
}

# Price entries are in an array, need special handling
PRICE_FILES = ["data/prices_raw.json", "data/prices_validated.json"]
PRICE_SCHEMA = "schemas/price_entry.schema.json"


def load_json(path: Path) -> dict:
    """Load and parse JSON file."""
    with open(path) as f:
        return json.load(f)


def validate_file(
    data_path: Path,
    schema_path: Path,
    verbose: bool = False,
) -> list[str]:
    """
    Validate a data file against a schema.

    Returns list of error messages (empty if valid).
    """
    errors = []

    try:
        data = load_json(data_path)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]
    except FileNotFoundError:
        return [f"File not found: {data_path}"]

    try:
        schema = load_json(schema_path)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return [f"Schema error: {e}"]

    # Validate
    validator = Draft7Validator(schema)
    validation_errors = list(validator.iter_errors(data))

    for error in validation_errors:
        path = " -> ".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"{path}: {error.message}")

    return errors


def validate_price_entries(
    data_path: Path,
    schema_path: Path,
    verbose: bool = False,
) -> list[str]:
    """
    Validate price entry files (array of entries).

    Returns list of error messages.
    """
    errors = []

    try:
        data = load_json(data_path)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]
    except FileNotFoundError:
        # Price files may not exist yet
        if verbose:
            print(f"  Skipping (not found): {data_path}")
        return []

    try:
        schema = load_json(schema_path)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return [f"Schema error: {e}"]

    # Get prices array
    prices = data.get("prices", [])
    if not prices:
        if verbose:
            print(f"  No price entries to validate in {data_path}")
        return []

    # Validate each entry
    validator = Draft7Validator(schema)
    for i, entry in enumerate(prices):
        entry_errors = list(validator.iter_errors(entry))
        for error in entry_errors:
            path = " -> ".join(str(p) for p in error.absolute_path) or "(root)"
            restaurant = entry.get("restaurant_name", f"entry[{i}]")
            errors.append(f"{restaurant} -> {path}: {error.message}")

    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Validate JSON data files against schemas"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent.parent
    all_errors = {}
    files_checked = 0

    print("Validating JSON schemas...\n")

    # Validate standard files
    for data_file, schema_file in FILE_SCHEMA_MAP.items():
        data_path = script_dir / data_file
        schema_path = script_dir / schema_file

        if not data_path.exists():
            if args.verbose:
                print(f"Skipping (not found): {data_file}")
            continue

        if args.verbose:
            print(f"Validating {data_file}...")

        errors = validate_file(data_path, schema_path, args.verbose)
        files_checked += 1

        if errors:
            all_errors[data_file] = errors
            print(f"  FAIL: {data_file} ({len(errors)} errors)")
        elif args.verbose:
            print(f"  OK: {data_file}")

    # Validate price files
    schema_path = script_dir / PRICE_SCHEMA
    for price_file in PRICE_FILES:
        data_path = script_dir / price_file

        if not data_path.exists():
            if args.verbose:
                print(f"Skipping (not found): {price_file}")
            continue

        if args.verbose:
            print(f"Validating {price_file}...")

        errors = validate_price_entries(data_path, schema_path, args.verbose)
        files_checked += 1

        if errors:
            all_errors[price_file] = errors
            print(f"  FAIL: {price_file} ({len(errors)} errors)")
        elif args.verbose:
            print(f"  OK: {price_file}")

    # Summary
    print(f"\nValidation complete: {files_checked} files checked")

    if all_errors:
        print(f"\n{len(all_errors)} file(s) with validation errors:\n")
        for file, errors in all_errors.items():
            print(f"{file}:")
            for error in errors[:10]:  # Limit to first 10 errors per file
                print(f"  - {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")
            print()
        sys.exit(1)
    else:
        print("All files valid!")


if __name__ == "__main__":
    main()
