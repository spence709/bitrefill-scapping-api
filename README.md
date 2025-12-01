# Bitrefill eSIM Scraper

An API-based scraper to extract eSIM card information from Bitrefill, including:
- **Works in**: Countries where the eSIM works
- **Plans**: Available data plans (e.g., 1GB 7 Days, 10GB 30 Days)
- **Prices**: Price for each plan

## Requirements

- Python 3.7+
- requests library

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the API scraper (recommended - faster and more reliable):
```bash
python api_scraper.py
```

Or use the Selenium-based scraper (slower, but works if API changes):
```bash
python scraper.py
```

The API scraper will:
1. Fetch eSIM products from Bitrefill's API
2. For each product, extract:
   - Product name
   - URL
   - Countries where it works
   - Available plans
   - Prices for each plan
3. Save results to `bitrefill_esims.json`

## Output

The results are saved in JSON format:
```json
[
  {
    "name": "eSIM North America",
    "url": "https://www.bitrefill.com/us/en/esims/bitrefill-esim-north-america/",
    "works_in": ["USA", "Canada", "Mexico"],
    "plans": [
      {
        "plan": "1GB, 7 Days",
        "price": "$6.27"
      },
      {
        "plan": "2GB, 15 Days",
        "price": "$10.50"
      }
    ]
  }
]
```

## Configuration

You can modify the scraper behavior in `scraper.py`:
- Set `headless=True` in `main()` to run without opening a browser window
- Adjust delays and timeouts as needed

## Notes

- The scraper uses Selenium to handle JavaScript-rendered content
- Some pages may take time to load, so delays are included
- If a product's price cannot be extracted, it will be `null` in the output

