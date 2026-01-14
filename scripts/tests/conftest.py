"""
Pytest configuration and fixtures for Poutine Index tests.
"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def data_dir(project_root: Path) -> Path:
    """Return the data directory."""
    return project_root / "data"


@pytest.fixture
def schemas_dir(project_root: Path) -> Path:
    """Return the schemas directory."""
    return project_root / "schemas"


@pytest.fixture
def cities_data(data_dir: Path) -> dict:
    """Load cities.json data."""
    with open(data_dir / "cities.json") as f:
        return json.load(f)


@pytest.fixture
def minimum_wages_data(data_dir: Path) -> dict:
    """Load minimum_wages.json data."""
    with open(data_dir / "minimum_wages.json") as f:
        return json.load(f)


@pytest.fixture
def cities_final_data(data_dir: Path) -> dict:
    """Load cities_final.json data."""
    with open(data_dir / "cities_final.json") as f:
        return json.load(f)


@pytest.fixture
def restaurants_raw_data(data_dir: Path) -> dict:
    """Load restaurants_raw.json data if it exists."""
    path = data_dir / "restaurants_raw.json"
    if not path.exists():
        return {"fetch_date": None, "restaurants": []}
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def prices_raw_data(data_dir: Path) -> dict:
    """Load prices_raw.json data if it exists."""
    path = data_dir / "prices_raw.json"
    if not path.exists():
        return {"prices": []}
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def valid_province_codes() -> set:
    """Return set of valid Canadian province/territory codes."""
    return {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}


@pytest.fixture
def fast_food_blocklist() -> set:
    """Return set of blocked fast food chain names (lowercase)."""
    return {
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


# Canada bounding box
CANADA_LAT_MIN = 41.0
CANADA_LAT_MAX = 84.0
CANADA_LON_MIN = -141.0
CANADA_LON_MAX = -52.0


@pytest.fixture
def canada_bounds() -> dict:
    """Return Canada's geographic bounding box."""
    return {
        "lat_min": CANADA_LAT_MIN,
        "lat_max": CANADA_LAT_MAX,
        "lon_min": CANADA_LON_MIN,
        "lon_max": CANADA_LON_MAX,
    }
