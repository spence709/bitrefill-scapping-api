"""
Bitrefill eSIM Scraper
Extracts eSIM card information including countries, plans, and prices.
"""
import asyncio
import re
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup


class BitrefillESimScraper:
    """Scraper for Bitrefill eSIM products."""
    
    def __init__(self):
        self.base_url = "https://www.bitrefill.com/us/en/esims/"
        self.browser: Optional[Browser] = None
        
    async def init_browser(self):
        """Initialize the browser."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        
    async def close_browser(self):
        """Close the browser."""
        if self.browser:
            await self.browser.close()
            
    async def scrape_esim_data(self) -> List[Dict]:
        """
        Scrape eSIM data from Bitrefill.
        
        Returns:
            List of dictionaries containing eSIM information:
            [
                {
                    "country": "Country Name",
                    "countries_covered": ["Country1", "Country2", ...],
                    "plans": [
                        {
                            "name": "1GB 7 Days",
                            "data": "1GB",
                            "validity": "7 Days",
                            "price": "$9.99"
                        },
                        ...
                    ]
                },
                ...
            ]
        """
        if not self.browser:
            await self.init_browser()
            
        page = await self.browser.new_page()
        
        try:
            # Navigate to the eSIM page
            await page.goto(self.base_url, wait_until="networkidle", timeout=60000)
            
            # Wait for content to load - try multiple selectors
            selectors = [
                'a[href*="/esim-"]',
                '[data-testid*="product"]',
                '.product-card',
                '[class*="ProductCard"]',
                '[class*="product"]',
                'article',
                'main'
            ]
            
            for selector in selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    break
                except:
                    continue
            
            # Wait for dynamic content to render
            await asyncio.sleep(5)
            
            # Scroll to load lazy-loaded content
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
            
            # Try to extract data using JavaScript evaluation
            products_js = await page.evaluate("""
                () => {
                    const products = [];
                    // Look for product links
                    const links = document.querySelectorAll('a[href*="/esim-"]');
                    links.forEach(link => {
                        const href = link.href || link.getAttribute('href');
                        if (!href) return;
                        
                        // Find parent container
                        let container = link.closest('article, div[class*="card"], div[class*="product"]') || link.parentElement;
                        
                        // Extract text content
                        const text = container ? container.innerText : link.innerText;
                        
                        // Try to find price
                        const priceMatch = text.match(/\\$[\\d,]+(?:\\.\\d{2})?/);
                        const price = priceMatch ? priceMatch[0] : null;
                        
                        // Extract product name
                        const nameElem = container ? 
                            container.querySelector('h2, h3, h4, [class*="title"], [class*="name"]') : 
                            null;
                        const name = nameElem ? nameElem.innerText.trim() : 
                            (link.innerText.trim() || href.split('/').pop().replace(/-/g, ' '));
                        
                        // Extract data and validity from text
                        const dataMatch = text.match(/(\\d+(?:\\.\\d+)?)\\s*(GB|MB)/i);
                        const validityMatch = text.match(/(\\d+)\\s*(days?|day)/i);
                        
                        if (name && name.length > 0) {
                            products.push({
                                name: name,
                                url: href.startsWith('http') ? href : 'https://www.bitrefill.com' + href,
                                price: price,
                                data: dataMatch ? dataMatch[0] : null,
                                validity: validityMatch ? validityMatch[0] : null,
                                text: text.substring(0, 200)
                            });
                        }
                    });
                    return products;
                }
            """)
            
            # If we got products from JS, process them
            if products_js and len(products_js) > 0:
                detailed_products = []
                seen_urls = set()
                
                for product in products_js[:30]:  # Limit to first 30
                    url = product.get('url', '')
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    # Create product entry
                    product_data = {
                        'country': product.get('name', 'Unknown'),
                        'countries_covered': [product.get('name', 'Unknown')],
                        'plans': []
                    }
                    
                    # Add plan if we have data
                    if product.get('data') or product.get('price'):
                        product_data['plans'].append({
                            'name': f"{product.get('data', '')} {product.get('validity', '')}".strip() or 'Standard Plan',
                            'data': product.get('data'),
                            'validity': product.get('validity'),
                            'price': product.get('price')
                        })
                    
                    # Try to get more details from product page
                    try:
                        detailed = await self._scrape_product_details(page, url)
                        if detailed and detailed.get('plans'):
                            product_data = detailed
                    except:
                        pass
                    
                    if product_data.get('plans') or product_data.get('country') != 'Unknown':
                        detailed_products.append(product_data)
                
                if detailed_products:
                    return detailed_products
            
            # Fallback to HTML parsing
            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')
            return self._extract_from_page_content(soup)
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            await page.close()
    
    async def _scrape_product_details(self, page: Page, url: str) -> Optional[Dict]:
        """Scrape details from a specific product page."""
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)
            
            # Try JavaScript extraction first
            product_data_js = await page.evaluate("""
                () => {
                    const data = {
                        name: null,
                        countries: [],
                        plans: []
                    };
                    
                    // Extract product name
                    const nameElem = document.querySelector('h1, h2, [class*="title"], [class*="name"]');
                    if (nameElem) {
                        data.name = nameElem.innerText.trim();
                    }
                    
                    // Extract countries covered
                    const countryText = document.body.innerText;
                    const countryMatch = countryText.match(/works?\\s+in[\\s:]+([^\\n]+)/i);
                    if (countryMatch) {
                        const countries = countryMatch[1].split(/[,&]/).map(c => c.trim()).filter(c => c);
                        data.countries = countries;
                    }
                    
                    // Extract plans
                    const planElements = document.querySelectorAll('[class*="plan"], [class*="option"], [class*="package"], button, [class*="variant"]');
                    planElements.forEach(elem => {
                        const text = elem.innerText;
                        const priceMatch = text.match(/\\$[\\d,]+(?:\\.\\d{2})?/);
                        const dataMatch = text.match(/(\\d+(?:\\.\\d+)?)\\s*(GB|MB)/i);
                        const validityMatch = text.match(/(\\d+)\\s*(days?|day)/i);
                        
                        if (priceMatch || dataMatch) {
                            data.plans.push({
                                name: text.substring(0, 100).trim(),
                                data: dataMatch ? dataMatch[0] : null,
                                validity: validityMatch ? validityMatch[0] : null,
                                price: priceMatch ? priceMatch[0] : null
                            });
                        }
                    });
                    
                    return data;
                }
            """)
            
            if product_data_js and (product_data_js.get('name') or product_data_js.get('plans')):
                return {
                    'country': product_data_js.get('name') or url.split('/')[-1].replace('-', ' ').title(),
                    'countries_covered': product_data_js.get('countries', []) or [product_data_js.get('name', 'Unknown')],
                    'plans': product_data_js.get('plans', [])
                }
            
            # Fallback to HTML parsing
            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')
            
            # Extract product name
            name_elem = soup.find(['h1', 'h2'], class_=re.compile(r'title|name|heading', re.I))
            product_name = name_elem.get_text(strip=True) if name_elem else url.split('/')[-1].replace('-', ' ').title()
            
            # Extract countries covered
            countries = []
            country_elem = soup.find(string=re.compile(r'works in|countries|coverage', re.I))
            if country_elem:
                parent = country_elem.find_parent()
                if parent:
                    country_list = parent.find_all(['li', 'span', 'div'])
                    countries = [c.get_text(strip=True) for c in country_list if c.get_text(strip=True) and len(c.get_text(strip=True)) < 50]
            
            # Extract plans
            plans = []
            plan_sections = soup.find_all(['div', 'section', 'button'], class_=re.compile(r'plan|option|package|variant', re.I))
            
            for plan_section in plan_sections:
                plan_text = plan_section.get_text(strip=True)
                # Parse plan details (e.g., "1GB 7 Days")
                data_match = re.search(r'(\d+(?:\.\d+)?)\s*(GB|MB)', plan_text, re.I)
                validity_match = re.search(r'(\d+)\s*(days?|day)', plan_text, re.I)
                price_match = re.search(r'\$[\d,]+(?:\.\d{2})?', plan_text)
                
                if data_match or price_match:
                    plans.append({
                        'name': plan_text[:100] if len(plan_text) > 100 else plan_text,
                        'data': data_match.group(0) if data_match else None,
                        'validity': validity_match.group(0) if validity_match else None,
                        'price': price_match.group(0) if price_match else None
                    })
            
            if plans or countries or product_name:
                return {
                    'country': product_name,
                    'countries_covered': countries if countries else [product_name],
                    'plans': plans
                }
        except Exception as e:
            print(f"Error scraping product details from {url}: {e}")
        return None
    
    def _extract_from_page_content(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract eSIM data directly from the main page content."""
        products = []
        
        # Look for product cards or sections
        product_sections = soup.find_all(['div', 'article', 'section'], 
                                        class_=re.compile(r'product|card|item|esim', re.I))
        
        for section in product_sections:
            # Extract product name
            name_elem = section.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name|heading', re.I))
            if not name_elem:
                name_elem = section.find(['h2', 'h3', 'h4', 'a'])
            
            if name_elem:
                product_name = name_elem.get_text(strip=True)
                
                # Extract price
                price_elem = section.find(['span', 'div'], class_=re.compile(r'price|cost|amount', re.I))
                price = price_elem.get_text(strip=True) if price_elem else None
                
                # Extract plan information
                plan_text = section.get_text()
                data_match = re.search(r'(\d+(?:\.\d+)?)\s*(GB|MB)', plan_text, re.I)
                validity_match = re.search(r'(\d+)\s*(days?|day)', plan_text, re.I)
                
                plans = []
                if data_match or validity_match:
                    plans.append({
                        'name': f"{data_match.group(0) if data_match else ''} {validity_match.group(0) if validity_match else ''}".strip(),
                        'data': data_match.group(0) if data_match else None,
                        'validity': validity_match.group(0) if validity_match else None,
                        'price': price
                    })
                
                if product_name and (plans or price):
                    products.append({
                        'country': product_name,
                        'countries_covered': [product_name],
                        'plans': plans if plans else [{'name': 'Standard Plan', 'price': price}] if price else []
                    })
        
        return products


async def main():
    """Test the scraper."""
    scraper = BitrefillESimScraper()
    try:
        await scraper.init_browser()
        data = await scraper.scrape_esim_data()
        print(f"Scraped {len(data)} eSIM products")
        for product in data[:5]:  # Print first 5
            print(f"\n{product}")
    finally:
        await scraper.close_browser()


if __name__ == "__main__":
    asyncio.run(main())

