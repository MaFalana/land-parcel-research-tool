"""
Configuration module - Database and Azure initialization
"""
from storage.az import AzureStorageManager
from storage.db import DatabaseManager
from config.settings import NAME

# Initialize database manager (singleton)
DB = DatabaseManager()

print(f"✓ Connected to database: {NAME}")
print(f"✓ Connected to Azure storage: {NAME}")
