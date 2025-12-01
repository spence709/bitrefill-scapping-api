"""
Bitrefill eSIM Scraper API
FastAPI application to serve scraped eSIM data.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from scraper import BitrefillESimScraper
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Bitrefill eSIM Scraper API",
    description="API to extract eSIM card information from Bitrefill",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global scraper instance
scraper = None
cached_data = None
cache_lock = asyncio.Lock()


class Plan(BaseModel):
    """Data plan model."""
    name: str
    data: Optional[str] = None
    validity: Optional[str] = None
    price: Optional[str] = None


class ESimProduct(BaseModel):
    """eSIM product model."""
    country: str
    countries_covered: List[str]
    plans: List[Plan]


class ESimResponse(BaseModel):
    """Response model for eSIM data."""
    products: List[ESimProduct]
    total_count: int


@app.on_event("startup")
async def startup_event():
    """Initialize the scraper on startup."""
    global scraper
    scraper = BitrefillESimScraper()
    await scraper.init_browser()
    logger.info("Scraper initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    global scraper
    if scraper:
        await scraper.close_browser()
    logger.info("Scraper closed")


async def get_esim_data(force_refresh: bool = False) -> List[dict]:
    """Get eSIM data, using cache if available."""
    global cached_data, cache_lock
    
    if not force_refresh and cached_data:
        return cached_data
    
    async with cache_lock:
        # Double-check after acquiring lock
        if not force_refresh and cached_data:
            return cached_data
        
        try:
            logger.info("Scraping eSIM data from Bitrefill...")
            data = await scraper.scrape_esim_data()
            cached_data = data
            logger.info(f"Scraped {len(data)} eSIM products")
            return data
        except Exception as e:
            logger.error(f"Error scraping data: {e}")
            if cached_data:
                logger.warning("Returning cached data due to error")
                return cached_data
            raise


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Bitrefill eSIM Scraper API",
        "version": "1.0.0",
        "description": "API to extract eSIM card information from Bitrefill",
        "endpoints": {
            "/esims": "Get all eSIM products",
            "/esims/{country}": "Get eSIM products for a specific country",
            "/refresh": "Force refresh the cached data"
        }
    }


@app.get("/esims", response_model=ESimResponse, tags=["eSIMs"])
async def get_esims(force_refresh: bool = False):
    """
    Get all eSIM products.
    
    Args:
        force_refresh: If True, force a fresh scrape instead of using cache.
    
    Returns:
        List of all eSIM products with countries, plans, and prices.
    """
    try:
        data = await get_esim_data(force_refresh=force_refresh)
        
        # Convert to response model
        products = []
        for item in data:
            plans = [
                Plan(
                    name=plan.get('name', 'Unknown'),
                    data=plan.get('data'),
                    validity=plan.get('validity'),
                    price=plan.get('price')
                )
                for plan in item.get('plans', [])
            ]
            
            products.append(ESimProduct(
                country=item.get('country', 'Unknown'),
                countries_covered=item.get('countries_covered', []),
                plans=plans
            ))
        
        return ESimResponse(
            products=products,
            total_count=len(products)
        )
    except Exception as e:
        logger.error(f"Error in get_esims: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/esims/{country}", response_model=ESimResponse, tags=["eSIMs"])
async def get_esims_by_country(country: str, force_refresh: bool = False):
    """
    Get eSIM products for a specific country.
    
    Args:
        country: Country name to filter by (case-insensitive).
        force_refresh: If True, force a fresh scrape instead of using cache.
    
    Returns:
        Filtered list of eSIM products for the specified country.
    """
    try:
        data = await get_esim_data(force_refresh=force_refresh)
        
        # Filter by country (case-insensitive)
        country_lower = country.lower()
        filtered_data = [
            item for item in data
            if country_lower in item.get('country', '').lower() or
            any(country_lower in c.lower() for c in item.get('countries_covered', []))
        ]
        
        # Convert to response model
        products = []
        for item in filtered_data:
            plans = [
                Plan(
                    name=plan.get('name', 'Unknown'),
                    data=plan.get('data'),
                    validity=plan.get('validity'),
                    price=plan.get('price')
                )
                for plan in item.get('plans', [])
            ]
            
            products.append(ESimProduct(
                country=item.get('country', 'Unknown'),
                countries_covered=item.get('countries_covered', []),
                plans=plans
            ))
        
        return ESimResponse(
            products=products,
            total_count=len(products)
        )
    except Exception as e:
        logger.error(f"Error in get_esims_by_country: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/refresh", tags=["Cache"])
async def refresh_cache():
    """
    Force refresh the cached eSIM data.
    
    Returns:
        Confirmation message with the number of products scraped.
    """
    try:
        data = await get_esim_data(force_refresh=True)
        return {
            "message": "Cache refreshed successfully",
            "products_count": len(data)
        }
    except Exception as e:
        logger.error(f"Error refreshing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "scraper_initialized": scraper is not None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

