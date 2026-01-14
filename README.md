# The Poutine Index

A "Big Mac Index" style visualization for poutine prices across Canada. This static website displays an interactive map showing average classic poutine prices and a "poutine affordability index" (minutes of minimum wage work required to purchase a poutine).

## Live Site

[View the Poutine Index](https://mcleblanc711.github.io/poutine-index/)

## Features

- Interactive Leaflet.js map centered on Canada
- Color-coded markers showing average poutine prices (purple = cheap, orange = expensive)
- Click on any city to see:
  - Average prices for Small, Regular, and Large portions
  - Affordability Index (minutes of minimum wage work)
  - Sample size and provincial minimum wage
- Colorblind-friendly purple-to-orange gradient
- Mobile-responsive design
- Detailed methodology documentation

## Tech Stack

- **Frontend:** Static HTML/CSS/JS (GitHub Pages)
- **Map:** Leaflet.js (no API key required)
- **Data:** JSON files
- **Data Collection:** Google Places API + manual extraction
- **Testing:** pytest, Playwright, JSON Schema validation
- **CI/CD:** GitHub Actions

## Setup

### Prerequisites

- Python 3.11+
- Google Cloud account (for Places API, only needed for data collection)

### Installation

```bash
# Clone the repository
git clone https://github.com/mcleblanc711/poutine-index.git
cd poutine-index

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for frontend tests)
playwright install chromium
```

### Google Places API Setup (for data collection)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Places API**
4. Go to **APIs & Services > Credentials**
5. Create an API key
6. Set the environment variable:
   ```bash
   export GOOGLE_PLACES_API_KEY="your-api-key"
   ```

## Data Pipeline

The data flows through four stages:

```
1. fetch_restaurants.py → data/restaurants_raw.json
2. Manual price extraction → data/prices_raw.json
3. validate_prices.py → data/prices_validated.json
4. aggregate_data.py → data/cities_final.json (consumed by frontend)
```

### Running the Pipeline

```bash
# 1. Fetch restaurants (requires API key)
python scripts/fetch_restaurants.py

# 2. Manually extract prices from restaurant websites
#    (Add entries to data/prices_raw.json following the schema)

# 3. Validate price data
python scripts/validate_prices.py

# 4. Aggregate into final format
python scripts/aggregate_data.py
```

### Dry Run

```bash
# Preview which cities would be fetched without API calls
python scripts/fetch_restaurants.py --dry-run
```

## Running Tests

```bash
# Run all tests
pytest scripts/tests/ -v

# Run without frontend tests (no Playwright needed)
pytest scripts/tests/ -v --ignore=scripts/tests/test_frontend.py

# Run only frontend tests
pytest scripts/tests/test_frontend.py -v

# Validate JSON schemas
python scripts/validate_schemas.py
```

## Project Structure

```
poutine-index/
├── index.html              # Main page with map
├── methodology.html        # Methodology documentation
├── css/
│   └── style.css          # Styles
├── js/
│   └── map.js             # Leaflet.js map logic
├── data/
│   ├── cities.json        # Target cities with coordinates
│   ├── minimum_wages.json # Provincial minimum wages
│   ├── restaurants_raw.json
│   ├── prices_raw.json
│   ├── prices_validated.json
│   └── cities_final.json  # Final data for frontend
├── schemas/               # JSON Schema files
├── scripts/
│   ├── fetch_restaurants.py
│   ├── validate_prices.py
│   ├── aggregate_data.py
│   ├── validate_schemas.py
│   └── tests/
├── .github/workflows/     # CI/CD
├── CLAUDE.md             # Project context for Claude Code
├── requirements.txt
└── README.md
```

## Contributing

### Adding Price Data

1. Fork the repository
2. Add entries to `data/prices_raw.json` following this format:
   ```json
   {
     "city": "Montreal",
     "restaurant_name": "La Banquise",
     "source_url": "https://labanquise.com/menu",
     "extraction_date": "2025-01-15",
     "prices": {
       "small": 8.50,
       "regular": 11.00,
       "large": 14.50
     },
     "notes": "Prices from online menu",
     "confidence": "high"
   }
   ```
3. Run validation: `python scripts/validate_prices.py`
4. Submit a pull request

### Price Guidelines

- **Classic poutine only:** Fries, cheese curds, and gravy (no toppings)
- **Size normalization:**
  - Small: Smallest available
  - Regular: Standard/medium size, or only size if single portion
  - Large: Largest available
- **Confidence levels:**
  - `high`: Price clearly listed on official website
  - `medium`: Inferred from menu or third-party source
  - `low`: Estimated or from older data

## Target Cities

V1 covers the top 20 Canadian CMAs by population, plus:
- Banff, AB
- Yellowknife, NT
- Whitehorse, YT
- Iqaluit, NU

## Excluded Restaurants

Fast food chains are excluded to focus on local establishments:
- McDonald's, Burger King, Wendy's
- Harvey's, A&W, KFC, Dairy Queen
- Smoke's Poutinerie, New York Fries
- Tim Hortons, Subway, Costco, Walmart

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Inspired by [The Economist's Big Mac Index](https://www.economist.com/big-mac-index)
- Map tiles by [OpenStreetMap](https://www.openstreetmap.org/)
- Built with [Leaflet.js](https://leafletjs.com/)
