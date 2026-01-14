# Poutine Index

## Project Overview

A "Big Mac Index" style visualization for poutine prices across Canada. Static GitHub Pages site with Leaflet.js map showing average classic poutine prices and an affordability index (minutes of minimum wage work to buy a poutine).

## Key Commands
```bash
# Run all tests
pytest scripts/tests/ -v

# Fetch restaurants from Google Places API (requires GOOGLE_PLACES_API_KEY)
python scripts/fetch_restaurants.py

# Validate price data
python scripts/validate_prices.py

# Regenerate aggregated data for frontend
python scripts/aggregate_data.py

# Validate JSON schemas
python scripts/validate_schemas.py

# Run frontend tests (requires Playwright)
playwright install chromium
pytest scripts/tests/test_frontend.py -v
```

## Data Pipeline

1. `fetch_restaurants.py` → `data/restaurants_raw.json`
2. Manual price extraction (Claude Code) → `data/prices_raw.json`
3. `validate_prices.py` → `data/prices_validated.json`
4. `aggregate_data.py` → `data/cities_final.json` (consumed by frontend)

## Conventions

- **Classic poutine only:** fries, cheese curds, gravy—no loaded/topped variants
- **Size normalization:** Small, Regular, Large. Single-size items count as Regular.
- **Fast food excluded:** McDonald's, Burger King, Harvey's, New York Fries, Smoke's Poutinerie, etc.
- **Affordability index:** `(regular_price / provincial_min_wage) * 60` = minutes of work
- **Currency:** All prices in CAD
- **Coordinates:** lat/lon in decimal degrees

## File Locations

- Frontend: `index.html`, `methodology.html`, `css/`, `js/`
- Data: `data/` (JSON files, do not edit `cities_final.json` directly—regenerate via pipeline)
- Scripts: `scripts/` (Python 3.11+)
- Tests: `scripts/tests/`
- Schemas: `schemas/` (JSON Schema files for validation)

## Price Extraction Workflow

When extracting prices from restaurant websites:

1. Load `data/restaurants_raw.json`
2. Visit each restaurant's website/menu URL
3. Find classic poutine (fries + curds + gravy only, ignore loaded variants)
4. Record prices by size, normalize to Small/Regular/Large
5. Set confidence: "high" (price clearly listed), "medium" (inferred from menu), "low" (estimated)
6. Output to `data/prices_raw.json` following schema in `schemas/price_entry.schema.json`

## Common Issues

- **No menu online:** Set `source_url: null`, `confidence: "low"`, skip or note in `notes` field
- **Only loaded poutines listed:** Skip restaurant, note in `notes`
- **Ambiguous sizes:** Use judgment, document in `notes` (e.g., "Menu says 'regular' and 'large' only, no small")
- **Price ranges:** Use lower bound, note in `notes`

## Target Cities (V1)

Top 20 Canadian CMAs by population, plus:
- Banff, AB
- Yellowknife, NT
- Whitehorse, YT
- Iqaluit, NU

## Fast Food Blocklist

Excluded chains:
- McDonald's
- Burger King
- Harvey's
- New York Fries
- Smoke's Poutinerie
- Wendy's
- A&W
- KFC
- Dairy Queen
- Tim Hortons
