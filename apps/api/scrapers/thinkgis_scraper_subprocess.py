"""
ThinkGIS scraper using subprocess approach for Windows compatibility
This script is called as a subprocess to avoid asyncio threading issues on Windows
"""
import sys
import json
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import re


def batch_lookup_parcels_subprocess(parcel_ids, base_url, browser_timeout_ms=35000):
    """
    Lookup parcels using sync_playwright in a subprocess.
    This avoids the Windows threading + asyncio issues.
    """
    results = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.set_default_timeout(browser_timeout_ms)

        page.goto(base_url, wait_until="domcontentloaded")
        time.sleep(2)
        
        for idx, parcel_id in enumerate(parcel_ids, 1):
            print(f"[{idx}/{len(parcel_ids)}] Looking up {parcel_id}...", file=sys.stderr)
            
            try:
                # Search
                box = page.locator('input#searchBox')
                box.click()
                time.sleep(0.3)
                box.fill("")
                box.fill(str(parcel_id).strip())
                time.sleep(0.3)
                box.press("Enter")
                
                # Wait for results
                try:
                    page.wait_for_function(
                        "() => !document.getElementById('infoWindow').innerText.includes('Searching...')",
                        timeout=browser_timeout_ms
                    )
                except PlaywrightTimeoutError:
                    pass
                
                time.sleep(1.5)
                
                # Get the Property Card link
                prop_card_link = page.locator('a:has-text("Show Property Card")').first
                
                if prop_card_link.count() == 0:
                    print(f"  ⚠ No Property Card link found for {parcel_id}", file=sys.stderr)
                    continue
                
                href = prop_card_link.get_attribute('href')
                
                # Extract DSID and FeatureID
                dsid_match = re.search(r"DSID=(\d+)", href)
                feature_match = re.search(r"FeatureID=(\d+)", href)
                
                if dsid_match and feature_match:
                    dsid = dsid_match.group(1)
                    feature_id = feature_match.group(1)
                    
                    # Capture the info panel HTML
                    info_html = page.locator('#infoWindow').inner_html()
                    
                    results[parcel_id] = {
                        "dsid": dsid,
                        "feature_id": feature_id,
                        "info_html": info_html
                    }
                    print(f"  ✓ DSID={dsid}, FeatureID={feature_id}", file=sys.stderr)
                else:
                    print(f"  ⚠ Could not extract DSID/FeatureID from: {href}", file=sys.stderr)
                
            except Exception as e:
                print(f"  ✗ Error: {e}", file=sys.stderr)
                continue
        
        browser.close()
    
    return results


if __name__ == "__main__":
    # Read input from stdin
    print("Subprocess started, reading input...", file=sys.stderr)
    input_data = json.loads(sys.stdin.read())
    
    parcel_ids = input_data["parcel_ids"]
    base_url = input_data["base_url"]
    browser_timeout_ms = input_data.get("browser_timeout_ms", 35000)
    
    print(f"Processing {len(parcel_ids)} parcels from {base_url}", file=sys.stderr)
    
    # Run the lookup
    results = batch_lookup_parcels_subprocess(parcel_ids, base_url, browser_timeout_ms)
    
    print(f"Lookup complete, returning {len(results)} results", file=sys.stderr)
    
    # Output results as JSON to stdout
    print(json.dumps(results))
