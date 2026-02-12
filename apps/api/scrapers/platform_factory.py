"""
Factory for creating platform-specific scrapers
"""
from scrapers.base_scraper import BaseScraper
from scrapers.wthgis_scraper import WTHGISScraper
# TODO: Import other scrapers when implemented
# from scrapers.beacon_scraper import BeaconScraper
# from scrapers.elevate_scraper import ElevateScraper
# from scrapers.portico_scraper import PorticoScraper


def get_scraper(platform: str) -> BaseScraper:
    """
    Get the appropriate scraper for a GIS platform
    
    Args:
        platform: Platform name (wthgis, beacon, elevate, portico)
        
    Returns:
        Platform-specific scraper instance
        
    Raises:
        ValueError: If platform is not supported
    """
    scrapers = {
        "wthgis": WTHGISScraper,
        # TODO: Add other scrapers
        # "beacon": BeaconScraper,
        # "elevate": ElevateScraper,
        # "portico": PorticoScraper,
    }
    
    scraper_class = scrapers.get(platform.lower())
    
    if not scraper_class:
        raise ValueError(
            f"Unsupported platform: {platform}. "
            f"Supported platforms: {', '.join(scrapers.keys())}"
        )
    
    return scraper_class()
