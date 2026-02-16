"""
Test script to check contents of a sample shapefile ZIP from Azure
"""
import os
import zipfile
import tempfile
from dotenv import load_dotenv
from storage.az import AzureStorageManager

# Load environment variables
load_dotenv()

# Initialize Azure Storage Manager
container_name = os.getenv("NAME", "hwc-land-parcel-automater")
az = AzureStorageManager(container_name)

# Download a sample county shapefile
sample_county = "Allen"
blob_path = f"GIS/Indiana/Parcels/Current/{sample_county}.zip"

print(f"Downloading {blob_path}...")

# Download to temp file
temp_zip = os.path.join(tempfile.gettempdir(), f"{sample_county}_test.zip")
az.download_file(blob_path, temp_zip)

print(f"Downloaded to: {temp_zip}")
print(f"\nZIP contents:")

# List contents
with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
    for file_info in zip_ref.filelist:
        print(f"  {file_info.filename} ({file_info.file_size:,} bytes)")

# Check for required files
with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
    files = [f.filename for f in zip_ref.filelist]
    
    print("\n--- File Check ---")
    required = ['.shp', '.shx', '.dbf', '.prj']
    for ext in required:
        found = [f for f in files if f.lower().endswith(ext)]
        status = "✓" if found else "✗"
        print(f"{status} {ext}: {found[0] if found else 'NOT FOUND'}")
    
    print("\nOptional files:")
    optional = ['.cfg', '.cpg', '.idx', '.sbn', '.sbx']
    for ext in optional:
        found = [f for f in files if f.lower().endswith(ext)]
        if found:
            print(f"  {ext}: {found[0]}")

# Clean up
os.remove(temp_zip)
print(f"\nCleaned up temp file")
