"""
Test script to list parcel shapefiles in Azure Blob Storage
"""
import os
from dotenv import load_dotenv
from storage.az import AzureStorageManager

# Load environment variables
load_dotenv()

# Initialize Azure Storage Manager
container_name = os.getenv("NAME", "hwc-land-parcel-automater")
az = AzureStorageManager(container_name)

# List all blobs in the GIS/Indiana/Parcels/Current/ directory
prefix = "GIS/Indiana/Parcels/Current/"
print(f"Listing blobs with prefix: {prefix}\n")

blob_list = az.container_client.list_blobs(name_starts_with=prefix)

counties = []
for blob in blob_list:
    blob_name = blob.name
    # Extract county name from path
    if blob_name.endswith('.zip'):
        county_file = blob_name.replace(prefix, '')
        county_name = county_file.replace('.zip', '')
        counties.append(county_name)
        print(f"  {county_name}.zip")

print(f"\nTotal counties found: {len(counties)}")
print(f"\nCounty names: {sorted(counties)}")
