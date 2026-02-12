"""
Application settings and environment variables
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database
MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING")
NAME = os.getenv("NAME", "county_research")

# Azure Storage
AZURE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")

# Azure Entra ID (Authentication)
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").lower() == "true"

# Worker Configuration
WORKER_POLL_INTERVAL = int(os.getenv("WORKER_POLL_INTERVAL", "5"))
JOB_RETENTION_DAYS = int(os.getenv("JOB_RETENTION_DAYS", "3"))

# Scraping Configuration
SCRAPER_PAGE_DELAY_MIN = float(os.getenv("SCRAPER_PAGE_DELAY_MIN", "2.5"))
SCRAPER_PAGE_DELAY_MAX = float(os.getenv("SCRAPER_PAGE_DELAY_MAX", "6.0"))
SCRAPER_PDF_DELAY_MIN = float(os.getenv("SCRAPER_PDF_DELAY_MIN", "6.0"))
SCRAPER_PDF_DELAY_MAX = float(os.getenv("SCRAPER_PDF_DELAY_MAX", "12.0"))
SCRAPER_BROWSER_TIMEOUT_MS = int(os.getenv("SCRAPER_BROWSER_TIMEOUT_MS", "35000"))

# API Configuration
API_TITLE = "County Research Automation API"
API_VERSION = "2.0.0"
API_DESCRIPTION = "API for automating county parcel research and GIS data extraction"

# CORS Configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

print("✓ Environment variables loaded")
