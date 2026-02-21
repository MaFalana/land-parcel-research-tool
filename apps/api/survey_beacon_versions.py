"""
Survey all Beacon counties to identify interface versions and variations
"""
from playwright.sync_api import sync_playwright
import json
import time

# Load Indiana counties
with open('apps/web/src/data/gis/Indiana.json', 'r') as f:
    counties = json.load(f)

# Filter Beacon counties
beacon_counties = [
    c for c in counties 
    if 'beacon.schneidercorp.com' in c.get('url', '')
]

print(f"Found {len(beacon_counties)} Beacon counties")
print("=" * 80)

results = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15000)
    
    for idx, county_data in enumerate(beacon_counties, 1):
        county = county_data['county']
        url = county_data['url']
        
        print(f"\n[{idx}/{len(beacon_counties)}] {county} County")
        print(f"URL: {url}")
        
        result = {
            'county': county,
            'url': url,
            'status': 'unknown',
            'search_inputs': [],
            'page_title': '',
            'has_agree_button': False,
            'interface_type': 'unknown'
        }
        
        try:
            # Navigate
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            time.sleep(3)
            
            # Check for Agree button
            try:
                agree_btn = page.locator('text=Agree').first
                if agree_btn.is_visible(timeout=2000):
                    result['has_agree_button'] = True
                    agree_btn.click()
                    time.sleep(3)
            except:
                pass
            
            # Get page title
            result['page_title'] = page.title()
            
            # Wait for page to settle
            time.sleep(5)
            
            # Find all visible input elements
            inputs = page.locator('input').all()
            for inp in inputs:
                try:
                    if inp.is_visible():
                        inp_id = inp.get_attribute('id') or ''
                        inp_type = inp.get_attribute('type') or ''
                        inp_placeholder = inp.get_attribute('placeholder') or ''
                        
                        if inp_type in ['text', 'search'] or 'search' in inp_placeholder.lower() or 'parcel' in inp_id.lower():
                            result['search_inputs'].append({
                                'id': inp_id,
                                'type': inp_type,
                                'placeholder': inp_placeholder
                            })
                except:
                    pass
            
            # Determine interface type based on search input
            if any('topSearchControl' in inp['id'] for inp in result['search_inputs']):
                result['interface_type'] = 'new_beacon'
            elif any('txtParcelID' in inp['id'] for inp in result['search_inputs']):
                result['interface_type'] = 'old_beacon'
            elif result['search_inputs']:
                result['interface_type'] = 'unknown_beacon'
            else:
                result['interface_type'] = 'no_search_input'
            
            result['status'] = 'success'
            print(f"  ✓ Interface: {result['interface_type']}")
            print(f"  ✓ Search inputs: {len(result['search_inputs'])}")
            if result['search_inputs']:
                for inp in result['search_inputs']:
                    print(f"    - id={inp['id']}, type={inp['type']}, placeholder={inp['placeholder']}")
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            print(f"  ✗ Error: {e}")
        
        results.append(result)
        
        # Small delay between counties
        time.sleep(2)
    
    browser.close()

# Save results
with open('beacon_survey_results.json', 'w') as f:
    json.dump(results, f, indent=2)

# Print summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

interface_counts = {}
for r in results:
    itype = r['interface_type']
    interface_counts[itype] = interface_counts.get(itype, 0) + 1

print("\nInterface Types:")
for itype, count in sorted(interface_counts.items(), key=lambda x: -x[1]):
    print(f"  {itype}: {count} counties")

print("\nCounties by Interface Type:")
for itype in sorted(interface_counts.keys()):
    counties_with_type = [r['county'] for r in results if r['interface_type'] == itype]
    print(f"\n{itype} ({len(counties_with_type)}):")
    for c in counties_with_type:
        print(f"  - {c}")

print(f"\nDetailed results saved to: beacon_survey_results.json")
