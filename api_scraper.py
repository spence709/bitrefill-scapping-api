"""
Bitrefill eSIM API Scraper
Scrapes eSIM data from Bitrefill's API by executing fetch calls inside the browser
"""

import json
import logging
import time
from typing import List, Dict, Optional
from urllib.parse import urlencode
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BitrefillESimAPIScraper:
    def __init__(self, country: str = "US", headless: bool = False):
        """Initialize the API scraper"""
        self.base_url = "https://www.bitrefill.com"
        self.api_base = f"{self.base_url}/api"
        self.country = country
        self.headless = headless
        self.driver = None
        self.results = []
        
    def setup_driver_and_get_cookies(self):
        """Setup Selenium driver, navigate to site to get past Cloudflare, then extract cookies"""
        logger.info("Setting up browser to get past Cloudflare...")
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Setup ChromeDriver - try multiple methods
        import os
        import platform
        
        driver_path = None
        
        # Method 1: Try to use manually fixed ChromeDriver (win64)
        if platform.machine() == 'AMD64':
            cache_dir = os.path.join(os.path.expanduser('~'), '.wdm', 'drivers', 'chromedriver', 'win64')
            if os.path.exists(cache_dir):
                # Find the latest version
                versions = [d for d in os.listdir(cache_dir) if os.path.isdir(os.path.join(cache_dir, d))]
                if versions:
                    latest_version = sorted(versions)[-1]
                    potential_path = os.path.join(cache_dir, latest_version, 'chromedriver.exe')
                    if os.path.exists(potential_path):
                        driver_path = potential_path
                        logger.info(f"Using manually installed win64 ChromeDriver: {driver_path}")
        
        # Method 2: Try ChromeDriverManager
        if not driver_path:
            try:
                driver_path = ChromeDriverManager().install()
                # Check if it's win32 on 64-bit system
                if 'win32' in driver_path.lower() and platform.machine() == 'AMD64':
                    logger.warning("ChromeDriverManager downloaded win32 version. Checking for win64...")
                    # Look for win64 in parent directory
                    parent = os.path.dirname(os.path.dirname(driver_path))
                    win64_dir = os.path.join(parent, 'win64')
                    if os.path.exists(win64_dir):
                        # Find latest version in win64
                        versions = [d for d in os.listdir(win64_dir) if os.path.isdir(os.path.join(win64_dir, d))]
                        if versions:
                            latest = sorted(versions)[-1]
                            win64_path = os.path.join(win64_dir, latest, 'chromedriver.exe')
                            if os.path.exists(win64_path):
                                driver_path = win64_path
                                logger.info(f"Found win64 ChromeDriver: {driver_path}")
            except Exception as e:
                logger.warning(f"ChromeDriverManager failed: {e}")
        
        # Method 3: Let Selenium find it automatically
        if driver_path and os.path.exists(driver_path):
            service = Service(driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            logger.info("Trying to use system ChromeDriver...")
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
            except Exception as e:
                logger.error(f"Failed to initialize Chrome driver: {e}")
                logger.error("\nTo fix this, run: python fix_chromedriver.py")
                raise
        
        # Navigate to the site to get past Cloudflare
        logger.info("Navigating to Bitrefill to get cookies...")
        self.driver.get(f"{self.base_url}/us/en/esims/")
        time.sleep(5)  # Wait for Cloudflare check to complete
        
        # Extract cookies and set them in requests session
        cookies = self.driver.get_cookies()
        for cookie in cookies:
            self.session.cookies.set(cookie['name'], cookie['value'])
        
        # Set headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Referer': f'{self.base_url}/us/en/esims/',
            'Origin': self.base_url
        })
        
        logger.info("Cookies extracted, ready to make API calls")

    def fetch_json_via_browser(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        method: str = "GET",
        payload: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """
        Execute a fetch call inside the browser context and return JSON.
        """
        if not self.driver:
            raise RuntimeError("Browser driver not initialized")

        if endpoint.startswith("http"):
            url = endpoint
        else:
            prefix = "" if endpoint.startswith("/") else "/"
            url = f"{self.base_url}{prefix}{endpoint}"

        if params:
            query = urlencode(params)
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{query}"

        payload_str = json.dumps(payload) if isinstance(payload, dict) else payload

        script = """
const url = arguments[0];
const method = arguments[1];
const payload = arguments[2];
const callback = arguments[3];
const headers = {
  'accept': 'application/json',
  'content-type': 'application/json'
};
const options = { method, headers };
if (payload) {
  options.body = payload;
}
fetch(url, options)
  .then(resp => {
    if (!resp.ok) {
      throw new Error('HTTP ' + resp.status);
    }
    return resp.json();
  })
  .then(data => callback({ success: true, data }))
  .catch(err => callback({ success: false, error: err.message }));
"""

        result = self.driver.execute_async_script(
            script,
            url,
            method.upper(),
            payload_str,
        )

        if result and result.get("success"):
            return result.get("data")

        error_msg = result.get("error") if result else "Unknown error"
        logger.warning(f"Browser fetch failed ({url}): {error_msg}")
        return None
        
    def get_all_esim_products(self) -> List[Dict]:
        """Get all eSIM products from the API"""
        logger.info("Fetching eSIM products from API...")

        params = {
            "country": self.country,
            "s": 1,
            "limit": 100,
            "exclude_bill_pay_products": 1,
            "exclude_out_of_stock": 1,
        }

        data = self.fetch_json_via_browser("/api/omni", params=params)

        if not data:
            logger.warning("Failed to fetch omni product list via browser fetch")
            return []

        if isinstance(data, dict):
            products = data.get("products", []) or data.get("data", []) or []
        elif isinstance(data, list):
            products = data
        else:
            products = []

        esim_products = []
        for product in products:
            product_id = (
                product.get("id", "")
                or product.get("slug", "")
                or product.get("name", "")
            )
            if "esim" in str(product_id).lower():
                esim_products.append(
                    {
                        "id": product_id,
                        "name": product.get("name", product_id),
                        "slug": product.get("slug", product_id),
                    }
                )

        logger.info(f"Found {len(esim_products)} eSIM products from omni endpoint")
        return esim_products
    
    def get_product_details(self, product_id: str) -> Optional[Dict]:
        """Get detailed product information including plans and prices"""
        logger.info(f"Fetching details for product: {product_id}")
        
        params = {"source": "esim"}
        data = self.fetch_json_via_browser(f"/api/product/{product_id}", params=params)

        if not data:
            logger.warning(f"Browser fetch failed for product {product_id}")
            return None

        return data
    
    def extract_works_in(self, product_data: Dict) -> List[str]:
        """Extract countries where the eSIM works"""
        countries = []
        
        try:
            # Look for countries in various possible fields
            country_fields = [
                'countries',
                'supported_countries',
                'works_in',
                'coverage',
                'coverage_countries',
                'regions',
            ]
            
            for field in country_fields:
                if field in product_data:
                    countries_data = product_data[field]
                    if isinstance(countries_data, list):
                        for country in countries_data:
                            if isinstance(country, dict):
                                country_name = country.get('name') or country.get('country') or country.get('code')
                            else:
                                country_name = str(country)
                            if country_name and country_name not in countries:
                                countries.append(country_name)
                    elif isinstance(countries_data, str):
                        countries.append(countries_data)
            
            # Also check for country codes or flags
            if 'country_codes' in product_data:
                codes = product_data['country_codes']
                if isinstance(codes, list):
                    countries.extend([str(c) for c in codes if c not in countries])
            
        except Exception as e:
            logger.warning(f"Error extracting 'Works in' countries: {e}")
        
        return countries
    
    def extract_plans_and_prices(self, product_data: Dict) -> List[Dict[str, str]]:
        """Extract available plans and their prices"""
        plans = []
        
        try:
            # Look for plans in various possible fields
            plan_fields = [
                'plans',
                'options',
                'variants',
                'denominations',
                'data_plans',
                'packages',
            ]
            
            for field in plan_fields:
                if field in product_data:
                    plans_data = product_data[field]
                    if isinstance(plans_data, list):
                        for plan in plans_data:
                            plan_info = {}
                            
                            # Extract plan name/description
                            plan_name = (
                                plan.get('name') or 
                                plan.get('description') or 
                                plan.get('label') or
                                plan.get('data') or
                                f"{plan.get('data_amount', '')} {plan.get('data_unit', '')}, {plan.get('duration', '')} {plan.get('duration_unit', 'Days')}"
                            )
                            
                            # Extract price
                            price = (
                                plan.get('price') or 
                                plan.get('amount') or 
                                plan.get('cost') or
                                plan.get('usd_price')
                            )
                            
                            # Format price
                            if price:
                                if isinstance(price, (int, float)):
                                    price = f"${price:.2f}"
                                elif isinstance(price, str) and not price.startswith('$'):
                                    try:
                                        price_num = float(price)
                                        price = f"${price_num:.2f}"
                                    except:
                                        price = f"${price}"
                            
                            if plan_name:
                                plans.append({
                                    'plan': str(plan_name).strip(),
                                    'price': price
                                })
            
            # If no plans found, try to construct from product data
            if not plans:
                # Check if there are denomination ranges
                if 'min_denomination' in product_data and 'max_denomination' in product_data:
                    min_denom = product_data.get('min_denomination')
                    max_denom = product_data.get('max_denomination')
                    plans.append({
                        'plan': f"From {min_denom} to {max_denom}",
                        'price': None
                    })
            
        except Exception as e:
            logger.warning(f"Error extracting plans and prices: {e}")
        
        return plans
    
    def scrape_all(self):
        """Scrape all eSIM products"""
        try:
            # Setup driver and get cookies
            self.setup_driver_and_get_cookies()
            
            # Get all eSIM products
            products = self.get_all_esim_products()
            
            # If we didn't get products from omni, try to get from known eSIM slugs
            if not products:
                logger.info("No products from API, trying known eSIM slugs...")
                known_esims = [
                    'bitrefill-esim-north-america',
                    'bitrefill-esim-usa',
                    'bitrefill-esim-global',
                    'bitrefill-esim-europe',
                    'bitrefill-esim-united-arab-emirates',
                    'bitrefill-esim-united-kingdom',
                    'bitrefill-esim-canada',
                    'bitrefill-esim-mexico',
                    'bitrefill-esim-asia',
                    'bitrefill-esim-latam',
                    'bitrefill-esim-oceania',
                    'bitrefill-esim-africa',
                    'bitrefill-esim-middle-east',
                ]
                
                # Also try to get from the listing page by checking what products are loaded
                # For now, use known slugs
                products = [{'id': slug, 'name': slug.replace('bitrefill-esim-', '').replace('-', ' ').title(), 'slug': slug} 
                           for slug in known_esims]
            
            logger.info(f"Processing {len(products)} eSIM products...")
            
            # Get details for each product
            for idx, product in enumerate(products, 1):
                product_id = product.get('id') or product.get('slug')
                product_name = product.get('name', product_id)
                
                logger.info(f"Processing {idx}/{len(products)}: {product_name}")
                
                product_data = self.get_product_details(product_id)
                
                if product_data:
                    # Extract information
                    works_in = self.extract_works_in(product_data)
                    plans = self.extract_plans_and_prices(product_data)
                    
                    # Get product name from API if available
                    api_name = product_data.get('name') or product_data.get('title') or product_name
                    
                    result = {
                        'name': api_name,
                        'id': product_id,
                        'url': f"{self.base_url}/us/en/esims/{product_id}/",
                        'works_in': works_in,
                        'plans': plans,
                        'raw_data': product_data  # Include raw data for debugging
                    }
                    
                    self.results.append(result)
                    logger.info(f"✓ Extracted: {len(works_in)} countries, {len(plans)} plans")
                else:
                    logger.warning(f"✗ Failed to get data for {product_name}")
                
                # Small delay between requests
                time.sleep(1)
            
            return self.results
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("Browser closed")
    
    def save_results(self, filename: str = 'bitrefill_esims.json'):
        """Save scraped results to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to {filename}")


def main():
    """Main function to run the API scraper"""
    scraper = BitrefillESimAPIScraper(country="US", headless=False)
    results = scraper.scrape_all()
    scraper.save_results()
    
    print(f"\n{'='*50}")
    print(f"Scraping completed!")
    print(f"Total products scraped: {len(results)}")
    print(f"Results saved to bitrefill_esims.json")
    print(f"{'='*50}\n")
    
    # Print summary
    for result in results:
        print(f"\n{result['name']}")
        print(f"  Works in: {', '.join(result['works_in']) if result['works_in'] else 'Not found'}")
        print(f"  Plans: {len(result['plans'])}")
        for plan in result['plans'][:3]:  # Show first 3 plans
            print(f"    - {plan['plan']}: {plan['price'] or 'N/A'}")


if __name__ == "__main__":
    main()

