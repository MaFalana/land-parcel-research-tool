"""
Debug script to understand Beacon page behavior after clicking Agree
"""
from playwright.sync_api import sync_playwright
import time

# Hendricks County URL
base_url = "https://beacon.schneidercorp.com/Application.aspx?AppID=327&LayerID=3469&PageTypeID=1&PageID=2307"
search_url = "https://beacon.schneidercorp.com/Application.aspx?AppID=327&LayerID=3469&PageTypeID=2&PageID=2307"

print("Testing Beacon page behavior...")
print(f"Base URL (PageTypeID=1): {base_url}")
print(f"Search URL (PageTypeID=2): {search_url}")
print()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Non-headless to see what happens
    context = browser.new_context()
    page = context.new_page()
    
    # Navigate to search page
    print("1. Navigating to search page...")
    page.goto(search_url, wait_until="domcontentloaded")
    time.sleep(3)
    print(f"   Current URL: {page.url}")
    print(f"   Page title: {page.title()}")
    
    # Check for Agree button
    print("\n2. Checking for Agree button...")
    agree_selectors = [
        'text=Agree',
        'text=Accept',
        'button:has-text("Agree")',
        'button:has-text("Accept")',
        'input[value*="Agree"]',
        'input[value*="Accept"]'
    ]
    
    agreement_clicked = False
    for selector in agree_selectors:
        try:
            button = page.locator(selector).first
            if button.is_visible(timeout=2000):
                print(f"   Found: {selector}")
                print(f"   URL before click: {page.url}")
                button.click()
                agreement_clicked = True
                time.sleep(5)
                print(f"   URL after click: {page.url}")
                break
        except:
            continue
    
    if not agreement_clicked:
        print("   No agreement button found")
    
    # Check current page
    print(f"\n3. Current state:")
    print(f"   URL: {page.url}")
    print(f"   Title: {page.title()}")
    
    # Try to find search input
    print("\n4. Looking for search input...")
    try:
        search_input = page.locator('input[id*="txtParcelID"]').first
        if search_input.is_visible(timeout=3000):
            print("   ✓ Search input found!")
            print(f"   ID: {search_input.get_attribute('id')}")
        else:
            print("   ✗ Search input not visible")
    except Exception as e:
        print(f"   ✗ Search input not found: {e}")
    
    # If not on search page, navigate there
    if "PageTypeID=2" not in page.url:
        print("\n5. Not on search page, navigating...")
        page.goto(search_url, wait_until="domcontentloaded")
        time.sleep(3)
        print(f"   URL: {page.url}")
        
        # Try again
        try:
            search_input = page.locator('input[id*="txtParcelID"]').first
            if search_input.is_visible(timeout=3000):
                print("   ✓ Search input found after navigation!")
            else:
                print("   ✗ Still not visible")
        except Exception as e:
            print(f"   ✗ Still not found: {e}")
    
    print("\n6. Keeping browser open for 30 seconds for inspection...")
    time.sleep(30)
    
    browser.close()

print("\nDone!")
