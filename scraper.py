"""
Bitrefill eSIM Scraper
Scrapes all eSIM cards from Bitrefill and extracts:
- Works in (countries)
- Plans (data plans)
- Prices
"""

import json
import time
import logging
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BitrefillESimScraper:
    def __init__(self, headless: bool = False):
        """Initialize the scraper with Chrome driver"""
        self.base_url = "https://www.bitrefill.com/us/en/esims/"
        self.headless = headless
        self.driver = None
        self.results = []
        
    def setup_driver(self):
        """Setup Chrome driver with options"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)
        logger.info("Chrome driver initialized")
        
    def get_all_esim_links(self) -> List[Dict[str, str]]:
        """Get all eSIM product links from the listing page"""
        logger.info(f"Navigating to {self.base_url}")
        self.driver.get(self.base_url)
        time.sleep(5)  # Wait for page to load
        
        esim_products = []
        
        try:
            # Wait for the product list to load
            wait = WebDriverWait(self.driver, 20)
            
            # Scroll to load all products (lazy loading)
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            while scroll_attempts < 5:  # Limit scroll attempts
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                scroll_attempts += 1
            
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            # Find all eSIM product links - look for links in list items
            product_links = wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "a[href*='/esims/bitrefill-esim-']")
                )
            )
            
            logger.info(f"Found {len(product_links)} potential eSIM links")
            
            # Extract unique product URLs and names
            seen_urls = set()
            for link in product_links:
                try:
                    href = link.get_attribute('href')
                    if href and href not in seen_urls:
                        # Get product name - try multiple methods
                        name = None
                        # Try to get name from link text or aria-label
                        name = link.text.strip()
                        if not name:
                            name = link.get_attribute('name')
                        if not name:
                            name = link.get_attribute('aria-label')
                        # If still no name, try to extract from URL
                        if not name and '/bitrefill-esim-' in href:
                            name = href.split('/bitrefill-esim-')[-1].rstrip('/').replace('-', ' ').title()
                        
                        if name and name not in ['', 'Unknown']:
                            esim_products.append({
                                'name': name,
                                'url': href
                            })
                            seen_urls.add(href)
                except Exception as e:
                    logger.warning(f"Error extracting link: {e}")
                    continue
            
            logger.info(f"Found {len(esim_products)} unique eSIM products")
            return esim_products
            
        except TimeoutException:
            logger.error("Timeout waiting for product list to load")
            return []
        except Exception as e:
            logger.error(f"Error getting eSIM links: {e}")
            return []
    
    def extract_works_in(self) -> List[str]:
        """Extract 'Works in' countries from the product page"""
        countries = []
        try:
            wait = WebDriverWait(self.driver, 10)
            
            # Method 1: Look for "Works in" text and find nearby elements
            works_in_selectors = [
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'works in')]",
                "//*[contains(text(), 'Works in')]",
            ]
            
            works_in_element = None
            for selector in works_in_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        text = elem.text.lower()
                        if 'works in' in text or 'works:' in text:
                            works_in_element = elem
                            break
                    if works_in_element:
                        break
                except NoSuchElementException:
                    continue
            
            if works_in_element:
                # Get parent container
                try:
                    parent = works_in_element.find_element(By.XPATH, "./ancestor::*[contains(@class, 'container') or contains(@class, 'section')][1]")
                except:
                    parent = works_in_element.find_element(By.XPATH, "./..")
                
                # Look for country flags with aria-label
                flag_elements = parent.find_elements(
                    By.CSS_SELECTOR, 
                    "[aria-label*='Flag for']"
                )
                
                for flag in flag_elements:
                    aria_label = flag.get_attribute('aria-label') or ''
                    if 'Flag for' in aria_label:
                        country = aria_label.replace('Flag for', '').strip()
                        if country and country not in countries:
                            countries.append(country)
                
                # Also look for country names in text near flags
                all_text = parent.text
                # Look for country names that might be listed
                if all_text:
                    # Try to find country names after "Works in" or "Works:"
                    import re
                    works_in_match = re.search(r'works\s*[:\s]+(.*?)(?:\n|$)', all_text, re.IGNORECASE)
                    if works_in_match:
                        countries_text = works_in_match.group(1)
                        # Common country patterns
                        country_patterns = [
                            r'\b(USA|United States)\b',
                            r'\b(Canada)\b',
                            r'\b(Mexico)\b',
                            r'\b(UK|United Kingdom)\b',
                            r'\b(Germany)\b',
                            r'\b(France)\b',
                            r'\b(Italy)\b',
                            r'\b(Spain)\b',
                            r'\b(Japan)\b',
                            r'\b(China)\b',
                            r'\b(India)\b',
                            r'\b(Australia)\b',
                            r'\b(Brazil)\b',
                            r'\b(UAE|United Arab Emirates)\b',
                        ]
                        for pattern in country_patterns:
                            matches = re.findall(pattern, countries_text, re.IGNORECASE)
                            for match in matches:
                                country = match if isinstance(match, str) else match[0]
                                if country and country not in countries:
                                    countries.append(country)
            
            # Method 2: Look for all flag elements on the page near product details
            if not countries:
                flag_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    "[aria-label*='Flag for']"
                )
                
                # Filter flags that are likely in the "Works in" section
                # (not in navigation or footer)
                for flag in flag_elements:
                    try:
                        # Check if flag is in main content area
                        location = flag.location
                        if location['y'] > 200 and location['y'] < 2000:  # Rough content area
                            aria_label = flag.get_attribute('aria-label') or ''
                            if 'Flag for' in aria_label:
                                country = aria_label.replace('Flag for', '').strip()
                                if country and country not in countries:
                                    countries.append(country)
                    except:
                        continue
            
            return countries
            
        except Exception as e:
            logger.warning(f"Error extracting 'Works in' countries: {e}")
            return []
    
    def extract_plans_and_prices(self) -> List[Dict[str, str]]:
        """Extract all available plans and their prices"""
        plans = []
        
        try:
            wait = WebDriverWait(self.driver, 10)
            
            # Find the plan selector/dropdown - look for button with "Select your plan"
            plan_button = None
            try:
                plan_button = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'select your plan')]")
                    )
                )
            except:
                try:
                    plan_button = self.driver.find_element(
                        By.CSS_SELECTOR,
                        "button[name*='Select your plan'], button[aria-label*='Select your plan']"
                    )
                except:
                    pass
            
            if plan_button:
                # Scroll to button
                self.driver.execute_script("arguments[0].scrollIntoView(true);", plan_button)
                time.sleep(1)
                
                # Click to open the dropdown
                self.driver.execute_script("arguments[0].click();", plan_button)
                time.sleep(2)  # Wait for dropdown to open
                
                # Find all plan options in the listbox
                plan_options = []
                try:
                    # Look for options in listbox
                    listbox = self.driver.find_element(By.CSS_SELECTOR, "[role='listbox']")
                    plan_options = listbox.find_elements(By.CSS_SELECTOR, "[role='option']")
                except:
                    # Fallback: look for any option elements
                    plan_options = self.driver.find_elements(By.CSS_SELECTOR, "[role='option']")
                
                logger.info(f"Found {len(plan_options)} plan options")
                
                # Extract plan names
                plan_names = []
                for option in plan_options:
                    try:
                        plan_text = option.text.strip() or option.get_attribute('name') or option.get_attribute('aria-label')
                        if plan_text and ('GB' in plan_text or 'MB' in plan_text or 'Day' in plan_text):
                            # Clean up plan text
                            plan_text = ' '.join(plan_text.split())  # Normalize whitespace
                            if plan_text not in plan_names:
                                plan_names.append(plan_text)
                    except Exception as e:
                        logger.warning(f"Error extracting plan name: {e}")
                        continue
                
                # Now get prices for each plan by selecting them
                for plan_name in plan_names:
                    try:
                        # Click the plan button again to reopen dropdown
                        self.driver.execute_script("arguments[0].click();", plan_button)
                        time.sleep(1)
                        
                        # Find and click the specific plan option
                        option_found = False
                        for option in plan_options:
                            option_text = option.text.strip() or option.get_attribute('name') or option.get_attribute('aria-label')
                            if plan_name in option_text or option_text in plan_name:
                                self.driver.execute_script("arguments[0].click();", option)
                                time.sleep(2)  # Wait for price to update
                                option_found = True
                                break
                        
                        if not option_found:
                            continue
                        
                        # Now find the price - it should be displayed somewhere on the page
                        price = None
                        
                        # Look for price near the plan selector
                        try:
                            # Find price element near the form/plan selector
                            form = plan_button.find_element(By.XPATH, "./ancestor::form[1]")
                            # Look for price in various formats
                            price_elements = form.find_elements(
                                By.XPATH, 
                                ".//*[contains(text(), '$')]"
                            )
                            
                            for price_elem in price_elements:
                                price_text = price_elem.text
                                import re
                                # Match price patterns like $6.27, $10.50, etc.
                                price_match = re.search(r'\$[\d,]+\.?\d{0,2}', price_text)
                                if price_match:
                                    price = price_match.group()
                                    # Validate it's a reasonable price (between $1 and $1000)
                                    price_num = float(price.replace('$', '').replace(',', ''))
                                    if 1 <= price_num <= 1000:
                                        break
                        except Exception as e:
                            logger.debug(f"Error finding price in form: {e}")
                        
                        # If still no price, try to find it in the product details area
                        if not price:
                            try:
                                # Get the main product section
                                main_section = self.driver.find_element(
                                    By.CSS_SELECTOR,
                                    "main, [role='main'], .product-details, section"
                                )
                                price_elements = main_section.find_elements(
                                    By.XPATH,
                                    ".//*[contains(text(), '$')]"
                                )
                                
                                for price_elem in price_elements:
                                    price_text = price_elem.text
                                    import re
                                    price_match = re.search(r'\$[\d,]+\.?\d{0,2}', price_text)
                                    if price_match:
                                        price_candidate = price_match.group()
                                        # Validate it's a reasonable price
                                        try:
                                            price_num = float(price_candidate.replace('$', '').replace(',', ''))
                                            if 1 <= price_num <= 1000:
                                                price = price_candidate
                                                break
                                        except:
                                            continue
                            except Exception as e:
                                logger.debug(f"Error finding price in main section: {e}")
                        
                        # Last resort: check page source for price data
                        if not price:
                            try:
                                page_source = self.driver.page_source
                                import re
                                # Look for price patterns in the HTML
                                price_matches = re.findall(r'\$[\d,]+\.?\d{0,2}', page_source)
                                for price_candidate in price_matches:
                                    try:
                                        price_num = float(price_candidate.replace('$', '').replace(',', ''))
                                        if 1 <= price_num <= 1000:
                                            price = price_candidate
                                            break
                                    except:
                                        continue
                            except:
                                pass
                        
                        plans.append({
                            'plan': plan_name,
                            'price': price
                        })
                        
                    except Exception as e:
                        logger.warning(f"Error extracting price for plan {plan_name}: {e}")
                        # Still add the plan without price
                        plans.append({
                            'plan': plan_name,
                            'price': None
                        })
                
                # Close dropdown if still open
                try:
                    self.driver.execute_script("arguments[0].blur();", plan_button)
                except:
                    pass
            
            # If no plans found, try alternative method
            if not plans:
                logger.warning("No plans found with dropdown method, trying alternative...")
                # Look for plan information in page text
                page_text = self.driver.find_element(By.TAG_NAME, 'body').text
                import re
                # Look for patterns like "1GB, 7 Days" or "1GB 7 Days"
                plan_patterns = re.findall(r'(\d+\s*GB[,\s]+\d+\s*Days?)', page_text, re.IGNORECASE)
                for pattern in plan_patterns:
                    if pattern not in [p['plan'] for p in plans]:
                        plans.append({
                            'plan': pattern,
                            'price': None
                        })
            
            return plans
            
        except Exception as e:
            logger.warning(f"Error extracting plans and prices: {e}")
            return []
    
    def scrape_product_details(self, product_url: str, product_name: str) -> Optional[Dict]:
        """Scrape details for a single eSIM product"""
        logger.info(f"Scraping product: {product_name}")
        logger.info(f"URL: {product_url}")
        
        try:
            self.driver.get(product_url)
            time.sleep(3)  # Wait for page to load
            
            # Extract product details
            works_in = self.extract_works_in()
            plans = self.extract_plans_and_prices()
            
            # Get the product name from the page if available
            try:
                page_name = self.driver.find_element(By.TAG_NAME, 'h1').text
                if page_name:
                    product_name = page_name
            except:
                pass
            
            product_data = {
                'name': product_name,
                'url': product_url,
                'works_in': works_in,
                'plans': plans
            }
            
            logger.info(f"Extracted data for {product_name}: {len(works_in)} countries, {len(plans)} plans")
            return product_data
            
        except Exception as e:
            logger.error(f"Error scraping product {product_name}: {e}")
            return None
    
    def scrape_all(self):
        """Scrape all eSIM products"""
        try:
            self.setup_driver()
            
            # Get all eSIM product links
            esim_products = self.get_all_esim_links()
            
            if not esim_products:
                logger.warning("No eSIM products found. Trying alternative method...")
                # Alternative: Try to get products from the page directly
                self.driver.get(self.base_url)
                time.sleep(5)
                
                # Look for product cards/items
                product_cards = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "[href*='/esims/bitrefill-esim-']"
                )
                
                for card in product_cards[:50]:  # Limit to first 50
                    try:
                        href = card.get_attribute('href')
                        name = card.text.strip() or card.get_attribute('name')
                        if href and name and '/esims/bitrefill-esim-' in href:
                            esim_products.append({
                                'name': name,
                                'url': href
                            })
                    except:
                        continue
            
            logger.info(f"Found {len(esim_products)} eSIM products to scrape")
            
            # Scrape each product
            for idx, product in enumerate(esim_products, 1):
                logger.info(f"Processing {idx}/{len(esim_products)}: {product['name']}")
                product_data = self.scrape_product_details(product['url'], product['name'])
                
                if product_data:
                    self.results.append(product_data)
                
                # Small delay between requests
                time.sleep(2)
            
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
    """Main function to run the scraper"""
    scraper = BitrefillESimScraper(headless=False)  # Set to True for headless mode
    results = scraper.scrape_all()
    scraper.save_results()
    
    print(f"\nScraping completed!")
    print(f"Total products scraped: {len(results)}")
    print(f"Results saved to bitrefill_esims.json")


if __name__ == "__main__":
    main()

