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
WORKER_POLL_INTERVAL = 5  # seconds between polling for new jobs
JOB_RETENTION_DAYS = 3    # days to keep completed jobs before cleanup

# Scraping Configuration (polite delays for GIS portals)
SCRAPER_PAGE_DELAY_MIN = 2.5  # seconds between HTML requests
SCRAPER_PAGE_DELAY_MAX = 6.0
SCRAPER_PDF_DELAY_MIN = 6.0   # seconds between PDF downloads
SCRAPER_PDF_DELAY_MAX = 12.0
SCRAPER_BROWSER_TIMEOUT_MS = 35000  # 35 seconds

# API Configuration
API_TITLE = "County Research Automation API"
API_VERSION = "2.0.0"
API_DESCRIPTION = "API for automating county parcel research and GIS data extraction"

# File Upload Limits
MAX_UPLOAD_SIZE_MB = 5120  # 5 GB in megabytes
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# CORS Configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

print("✓ Environment variables loaded")
