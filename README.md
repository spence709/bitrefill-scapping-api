# Bitrefill eSIM Scraper API

An API-based scraper to extract eSIM card information from Bitrefill, including:

- **Countries**: Countries where the eSIM works
- **Plans**: Available data plans (e.g., 1GB 7 Days, 10GB 30 Days)
- **Prices**: Price for each plan

## Features

- 🚀 FastAPI-based REST API
- 🔄 Automatic caching of scraped data
- 🌍 Filter eSIMs by country
- 📊 Structured JSON responses
- 🔍 Real-time scraping with Playwright

## Installation

### Prerequisites

- Python 3.8 or higher
- pip

### Setup

1. Clone or download this repository

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install chromium
```

## Usage

### Start the API Server

```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Endpoints

#### Get All eSIM Products

```bash
GET /esims
```

**Query Parameters:**
- `force_refresh` (boolean, optional): Force a fresh scrape instead of using cache

**Example:**
```bash
curl http://localhost:8000/esims
```

**Response:**
```json
{
  "products": [
    {
      "country": "Global eSIM",
      "countries_covered": ["United States", "United Kingdom", "France", ...],
      "plans": [
        {
          "name": "1GB 7 Days",
          "data": "1GB",
          "validity": "7 Days",
          "price": "$9.99"
        },
        {
          "name": "10GB 30 Days",
          "data": "10GB",
          "validity": "30 Days",
          "price": "$29.99"
        }
      ]
    }
  ],
  "total_count": 1
}
```

#### Get eSIMs by Country

```bash
GET /esims/{country}
```

**Path Parameters:**
- `country`: Country name (case-insensitive)

**Query Parameters:**
- `force_refresh` (boolean, optional): Force a fresh scrape instead of using cache

**Example:**
```bash
curl http://localhost:8000/esims/United%20States
```

#### Refresh Cache

```bash
POST /refresh
```

Force refresh the cached data by scraping Bitrefill again.

**Example:**
```bash
curl -X POST http://localhost:8000/refresh
```

#### Health Check

```bash
GET /health
```

Check if the API and scraper are running properly.

**Example:**
```bash
curl http://localhost:8000/health
```

#### API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
bitrefill-scapping-api/
├── main.py              # FastAPI application
├── scraper.py           # Bitrefill scraper implementation
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## How It Works

1. The scraper uses Playwright to load the Bitrefill eSIM page
2. It waits for the page to fully load (including JavaScript-rendered content)
3. It extracts product information including:
   - Product names (countries/regions)
   - Countries covered by each eSIM
   - Available data plans
   - Prices for each plan
4. The data is cached to avoid repeated scraping
5. The API serves the data via REST endpoints

## Notes

- The scraper may take 30-60 seconds to complete a full scrape
- Data is cached in memory to improve response times
- Use the `/refresh` endpoint to update the cache
- The scraper respects Bitrefill's robots.txt and rate limits

## Troubleshooting

### Playwright Installation Issues

If you encounter issues installing Playwright browsers:

```bash
# On Linux/Mac
playwright install chromium

# On Windows
python -m playwright install chromium
```

### Scraping Timeout

If scraping times out, you can increase the timeout in `scraper.py`:

```python
await page.goto(self.base_url, wait_until="networkidle", timeout=120000)  # 120 seconds
```

### No Data Returned

If no data is returned:
1. Check if Bitrefill's website structure has changed
2. Verify your internet connection
3. Check the API logs for error messages
4. Try forcing a refresh with `force_refresh=true`

## License

This project is for educational purposes. Please respect Bitrefill's terms of service and robots.txt when using this scraper.

## Contributing

Feel free to submit issues or pull requests to improve the scraper.

