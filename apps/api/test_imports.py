#!/usr/bin/env python3
"""
Quick test script to verify all imports work before starting the server
"""

print("Testing imports...")

try:
    print("✓ Testing FastAPI...")
    from fastapi import FastAPI
    
    print("✓ Testing database...")
    from pymongo import MongoClient
    
    print("✓ Testing Azure...")
    from azure.storage.blob import BlobServiceClient
    
    print("✓ Testing GIS libraries...")
    import geopandas
    import shapely
    import pyproj
    import ezdxf
    
    print("✓ Testing scraping libraries...")
    from playwright.sync_api import sync_playwright
    from bs4 import BeautifulSoup
    
    print("✓ Testing auth...")
    import jwt
    
    print("✓ Testing data processing...")
    import pandas
    import openpyxl
    
    print("\n✅ All imports successful!")
    print("\nNow testing application imports...")
    
    print("✓ Testing models...")
    from models.ParcelJob import ParcelJob
    
    print("✓ Testing routes...")
    from routes.jobs import jobs_router
    
    print("✓ Testing scrapers...")
    from scrapers.wthgis_scraper import WTHGISScraper
    
    print("✓ Testing utils...")
    from utils.label_exporter import LabelExporter
    from utils.file_parser import parse_parcel_file
    
    print("✓ Testing worker...")
    from worker import ParcelJobWorker
    
    print("✓ Testing scheduler...")
    from scheduler import JobCleanupScheduler
    
    print("✓ Testing auth...")
    from auth.entra_id import get_current_user
    
    print("\n⚠️  Skipping config/DB test (requires valid .env credentials)")
    print("   To test DB connection, ensure .env has valid:")
    print("   - MONGO_CONNECTION_STRING")
    print("   - AZURE_STORAGE_CONNECTION_STRING")
    
    print("\n✅ All application imports successful!")
    print("\n🚀 Ready to start the server with: npm run dev:api")
    
except ImportError as e:
    print(f"\n❌ Import failed: {e}")
    print("\nPlease install missing dependencies:")
    print("  pip install -e .")
    print("  python -m playwright install chromium")
    exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
