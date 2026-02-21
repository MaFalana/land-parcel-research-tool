"""
Test script for Beacon scraper

Tests with Wells County and a few sample parcel IDs
"""
import os
import tempfile
from scrapers.beacon_scraper import BeaconScraper

# Test configuration
COUNTY = "Wells"
# PageTypeID=2 is the search page, PageTypeID=1 is property details
BASE_URL = "https://beacon.schneidercorp.com/Application.aspx?AppID=173&LayerID=2165&PageTypeID=2&PageID=1119"

# Sample parcel IDs for Wells County
TEST_PARCELS = [
    "90-08-09-400-024.010-004",
    "90-08-09-400-038.000-004",
    "90-08-09-400-020.001-004",
    "90-08-09-100-044.000-004",
    "90-08-09-100-025.002-004",
    "90-08-09-100-007.001-003",
    "90-08-09-100-031.000-004"
]

def create_test_parcel_file():
    """Create a temporary file with test parcel IDs"""
    temp_dir = tempfile.gettempdir()
    test_file = os.path.join(temp_dir, "test_parcels.txt")
    
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
    print("Beacon Scraper Test")
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
            job_id="test_beacon_001",
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
        # Cleanup test file
        if os.path.exists(parcel_file):
            os.remove(parcel_file)
            print(f"Cleaned up test file: {parcel_file}")
        
        # Cleanup temp output directory if test failed
        temp_output = os.path.join(tempfile.gettempdir(), "parcel_jobs", "test_beacon_001")
        if os.path.exists(temp_output):
            import shutil
            shutil.rmtree(temp_output)
            print(f"Cleaned up temp directory: {temp_output}")

if __name__ == "__main__":
    main()
