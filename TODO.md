# Poutine Index - TODO

## Project Status
- [x] Initial project setup complete
- [x] Frontend with Leaflet.js map working
- [x] 4 placeholder cities with test data (Montreal, Toronto, Vancouver, Calgary)
- [x] GitHub repo created: https://github.com/mcleblanc711/poutine-index
- [x] GitHub Pages enabled: https://mcleblanc711.github.io/poutine-index/

## Next Steps

### 1. Data Collection (Priority: High)
- [x] Set up Google Cloud account and enable Places API
- [x] Set environment variable: `export GOOGLE_PLACES_API_KEY="your-key"`
- [x] Run `python3 scripts/fetch_restaurants.py` to get restaurant data for all 24 cities
- [x] Review `data/restaurants_raw.json` output (352 restaurants fetched)

### 2. Price Extraction (Priority: High)
For each city, visit restaurant websites and extract classic poutine prices:
- [ ] Montreal (needs real data to replace placeholder)
- [ ] Toronto (needs real data to replace placeholder)
- [ ] Vancouver (needs real data to replace placeholder)
- [ ] Calgary (needs real data to replace placeholder)
- [ ] Edmonton
- [ ] Ottawa-Gatineau
- [ ] Winnipeg
- [ ] Quebec City
- [ ] Hamilton
- [ ] Kitchener-Waterloo
- [ ] London
- [ ] Victoria
- [ ] Halifax
- [ ] Oshawa
- [ ] Windsor
- [ ] Saskatoon
- [ ] Regina
- [ ] St. Catharines-Niagara
- [ ] St. John's
- [ ] Kelowna
- [ ] Banff
- [ ] Yellowknife
- [ ] Whitehorse
- [ ] Iqaluit

**Price extraction format** (add to `data/prices_raw.json`):
```json
{
  "city": "CityName",
  "restaurant_name": "Restaurant Name",
  "source_url": "https://restaurant-website.com/menu",
  "extraction_date": "2025-01-13",
  "prices": {
    "small": 7.50,
    "regular": 10.00,
    "large": 13.50
  },
  "notes": "Any relevant notes",
  "confidence": "high"
}
```

### 3. Data Pipeline (Priority: Medium)
- [ ] Run `python3 scripts/validate_prices.py` to validate extracted prices
- [ ] Fix any validation errors/warnings
- [ ] Run `python3 scripts/aggregate_data.py` to generate final data
- [ ] Verify map displays all cities correctly

### 4. Add City-Level Average Wage Data (Priority: Medium)
Currently uses provincial minimum wage. Add city-level average/median wage for better affordability comparison:
- [ ] Research Statistics Canada data sources for city-level wages (Census, Labour Force Survey)
- [ ] Create `data/city_wages.json` with average hourly wage per CMA
- [ ] Update `scripts/aggregate_data.py` to incorporate city wages
- [ ] Add second affordability metric: "minutes of average wage work"
- [ ] Update frontend popup to show both min wage and avg wage affordability
- [ ] Update methodology.html to explain the two metrics

**Potential data sources:**
- Statistics Canada Table 14-10-0064-01 (Employee wages by occupation, annual)
- Statistics Canada Table 14-10-0340-01 (Employee wages by industry, CMA)
- Census 2021 median income by CMA

### 5. Repository Cleanup (Priority: Low)
- [ ] Update README.md - replace `YOUR_USERNAME` with `mcleblanc711`
- [ ] Update index.html - fix GitHub links
- [ ] Update methodology.html - fix GitHub links
- [ ] Run full test suite: `pytest scripts/tests/ -v`

### 6. Future Enhancements (Priority: Low)
- [ ] Add more restaurants per city for better sample size
- [ ] Set up quarterly data refresh schedule
- [ ] Consider adding historical price tracking
- [ ] Add city search/filter functionality

## Quick Commands
```bash
# Start local server
python3 -m http.server 8000

# Fetch restaurants (requires API key)
python3 scripts/fetch_restaurants.py

# Validate prices
python3 scripts/validate_prices.py

# Generate final data
python3 scripts/aggregate_data.py

# Validate JSON schemas
python3 scripts/validate_schemas.py

# Run tests
pip3 install pytest jsonschema requests
pytest scripts/tests/ -v --ignore=scripts/tests/test_frontend.py
```

## Notes for Claude Code
- Project uses Python 3.11+
- Frontend is static HTML/CSS/JS with Leaflet.js
- Data pipeline: fetch_restaurants → prices_raw → validate_prices → aggregate_data → cities_final
- Classic poutine only: fries + cheese curds + gravy (no loaded variants)
- Exclude fast food chains (McDonald's, Smoke's Poutinerie, etc.)
