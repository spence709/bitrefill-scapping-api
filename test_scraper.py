"""
Test script to debug and test the Bitrefill scraper
Run this to test scraping a single product
"""

from scraper import BitrefillESimScraper
import json

def test_single_product():
    """Test scraping a single product"""
    scraper = BitrefillESimScraper(headless=False)
    scraper.setup_driver()
    
    # Test with North America eSIM
    test_url = "https://www.bitrefill.com/us/en/esims/bitrefill-esim-north-america/"
    test_name = "eSIM North America"
    
    result = scraper.scrape_product_details(test_url, test_name)
    
    if result:
        print("\n" + "="*50)
        print("SCRAPED DATA:")
        print("="*50)
        print(json.dumps(result, indent=2))
        print("="*50)
        
        print(f"\nProduct: {result['name']}")
        print(f"Works in: {', '.join(result['works_in']) if result['works_in'] else 'Not found'}")
        print(f"\nPlans found: {len(result['plans'])}")
        for plan in result['plans']:
            print(f"  - {plan['plan']}: {plan['price'] or 'Price not found'}")
    else:
        print("Failed to scrape product")
    
    scraper.driver.quit()

if __name__ == "__main__":
    test_single_product()

