"""
Test script for Beacon scraper - Hendricks County

Tests with Hendricks County to verify flexible selectors work across counties
"""
import os
import tempfile
from scrapers.beacon_scraper import BeaconScraper

# Test configuration
COUNTY = "Hendricks"
# PageTypeID=2 is the search page
BASE_URL = "https://beacon.schneidercorp.com/Application.aspx?AppID=327&LayerID=3469&PageTypeID=2&PageID=2293"

# Sample parcel IDs for Hendricks County (from your original code)
TEST_PARCELS = [
    "32-16-20-220-001.000-011",
    "32-16-20-220-002.000-011",
    "32-16-20-220-003.000-011",
    "32-16-18-320-015.000-012",
    "32-16-18-320-016.000-012"
]

def create_test_parcel_file():
    """Create a temporary file with test parcel IDs"""
    temp_dir = tempfile.gettempdir()
    test_file = os.path.join(temp_dir, "test_parcels_hendricks.txt")
    
    with open(test_file, 'w') as f:
        for parcel_id in TEST_PARCELS:
            f.write(f"{parcel_id}\n")
    
    print(f"Created test file: {test_file}")
    return test_file

def progress_callback(completed, total):
    """Progress callback for testing"""
    print(f"Progress: {completed}/{total} ({(completed/total)*100:.1f}%)")

def main():
    print("=" * 60)
    print("Beacon Scraper Test - Hendricks County")
    print("=" * 60)
    print(f"County: {COUNTY}")
    print(f"URL: {BASE_URL}")
    print(f"Test Parcels: {len(TEST_PARCELS)}")
    print("=" * 60)
    print()
    
    # Create test file
    parcel_file = create_test_parcel_file()
    
    # Initialize scraper
    scraper = BeaconScraper()
    
    # Run scraper
    try:
        result = scraper.scrape_parcels(
            parcel_file_path=parcel_file,
            base_url=BASE_URL,
            county=COUNTY,
            job_id="test_beacon_hendricks_001",
            progress_callback=progress_callback
        )
        
        print()
        print("=" * 60)
        print("Test Results")
        print("=" * 60)
        print(f"Excel file: {result['excel_path']}")
        print(f"Total parcels: {result['total']}")
        print(f"Processed: {result['processed']}")
        print(f"Failed: {result['failed']}")
        print()
        print("✓ Test completed successfully!")
        print()
        print(f"Check the Excel file at: {result['excel_path']}")
        
    except Exception as e:
        print()
        print("=" * 60)
        print("Test Failed!")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if os.path.exists(parcel_file):
            os.remove(parcel_file)
            print(f"Cleaned up test file: {parcel_file}")
        
        # Cleanup temp output directory if test failed
        temp_output = os.path.join(tempfile.gettempdir(), "parcel_jobs", "test_beacon_hendricks_001")
        if os.path.exists(temp_output):
            import shutil
            shutil.rmtree(temp_output)
            print(f"Cleaned up temp directory: {temp_output}")

if __name__ == "__main__":
    main()
