"""
Debug script to find all input elements on Beacon page
"""
from playwright.sync_api import sync_playwright
import time

search_url = "https://beacon.schneidercorp.com/Application.aspx?AppID=327&LayerID=3469&PageTypeID=2&PageID=2307"

print("Finding all elements on Beacon page...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    
    # Navigate to search page
    print("1. Navigating to search page...")
    page.goto(search_url, wait_until="domcontentloaded")
    time.sleep(3)
    
    # Click Agree if present
    try:
        agree_btn = page.locator('text=Agree').first
        if agree_btn.is_visible(timeout=2000):
            print("2. Clicking Agree...")
            agree_btn.click()
            time.sleep(5)
    except:
        pass
    
    # Wait longer for map to load
    print("3. Waiting for page to fully load...")
    time.sleep(10)
    
    # Find all input elements
    print("\n4. Finding all input elements...")
    inputs = page.locator('input').all()
    print(f"   Found {len(inputs)} input elements:")
    for i, inp in enumerate(inputs):
        try:
            inp_id = inp.get_attribute('id') or 'no-id'
            inp_type = inp.get_attribute('type') or 'text'
            inp_name = inp.get_attribute('name') or 'no-name'
            inp_placeholder = inp.get_attribute('placeholder') or ''
            is_visible = inp.is_visible()
            print(f"   [{i}] id={inp_id}, type={inp_type}, name={inp_name}, placeholder={inp_placeholder}, visible={is_visible}")
        except:
            pass
    
    # Try clicking on "Search" tab
    print("\n5. Looking for Search tab...")
    try:
        search_tab = page.locator('text=Search').first
        if search_tab.is_visible(timeout=2000):
            print("   Found Search tab, clicking...")
            search_tab.click()
            time.sleep(3)
            
            # Try again to find inputs
            print("\n6. Finding inputs after clicking Search tab...")
            inputs = page.locator('input').all()
            print(f"   Found {len(inputs)} input elements:")
            for i, inp in enumerate(inputs):
                try:
                    inp_id = inp.get_attribute('id') or 'no-id'
                    inp_type = inp.get_attribute('type') or 'text'
                    inp_name = inp.get_attribute('name') or 'no-name'
                    inp_placeholder = inp.get_attribute('placeholder') or ''
                    is_visible = inp.is_visible()
                    print(f"   [{i}] id={inp_id}, type={inp_type}, name={inp_name}, placeholder={inp_placeholder}, visible={is_visible}")
                except:
                    pass
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n7. Keeping browser open for inspection...")
    time.sleep(60)
    
    browser.close()

print("\nDone!")
