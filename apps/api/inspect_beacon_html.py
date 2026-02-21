"""
Inspect Beacon HTML to understand the page structure
"""
from playwright.sync_api import sync_playwright
import time
from bs4 import BeautifulSoup

search_url = "https://beacon.schneidercorp.com/Application.aspx?AppID=327&LayerID=3469&PageTypeID=2&PageID=2307"

print("Inspecting Beacon HTML structure...")
print(f"URL: {search_url}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    
    # Navigate
    print("1. Navigating...")
    page.goto(search_url, wait_until="domcontentloaded")
    time.sleep(3)
    
    # Click Agree
    try:
        agree_btn = page.locator('text=Agree').first
        if agree_btn.is_visible(timeout=2000):
            print("2. Clicking Agree...")
            agree_btn.click()
            time.sleep(5)
    except:
        pass
    
    # Get HTML
    print("3. Extracting HTML...\n")
    html = page.content()
    
    # Save full HTML
    with open('/tmp/beacon_full.html', 'w') as f:
        f.write(html)
    print("Full HTML saved to: /tmp/beacon_full.html")
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find all inputs
    print("\n" + "="*80)
    print("ALL INPUT ELEMENTS")
    print("="*80)
    inputs = soup.find_all('input')
    for i, inp in enumerate(inputs):
        inp_id = inp.get('id', 'no-id')
        inp_type = inp.get('type', 'text')
        inp_name = inp.get('name', 'no-name')
        inp_class = inp.get('class', [])
        inp_placeholder = inp.get('placeholder', '')
        inp_value = inp.get('value', '')
        print(f"\n[{i}] Input:")
        print(f"  id: {inp_id}")
        print(f"  type: {inp_type}")
        print(f"  name: {inp_name}")
        print(f"  class: {inp_class}")
        print(f"  placeholder: {inp_placeholder}")
        print(f"  value: {inp_value[:50] if inp_value else ''}")
    
    # Find all forms
    print("\n" + "="*80)
    print("ALL FORM ELEMENTS")
    print("="*80)
    forms = soup.find_all('form')
    for i, form in enumerate(forms):
        form_id = form.get('id', 'no-id')
        form_action = form.get('action', 'no-action')
        form_method = form.get('method', 'no-method')
        print(f"\n[{i}] Form:")
        print(f"  id: {form_id}")
        print(f"  action: {form_action}")
        print(f"  method: {form_method}")
    
    # Find all divs with id containing 'search'
    print("\n" + "="*80)
    print("DIVS WITH 'SEARCH' IN ID")
    print("="*80)
    search_divs = soup.find_all('div', id=lambda x: x and 'search' in x.lower())
    for div in search_divs:
        print(f"\nDiv id: {div.get('id')}")
        print(f"  class: {div.get('class')}")
        print(f"  content preview: {str(div)[:200]}")
    
    # Find all iframes
    print("\n" + "="*80)
    print("IFRAMES")
    print("="*80)
    iframes = soup.find_all('iframe')
    for i, iframe in enumerate(iframes):
        iframe_id = iframe.get('id', 'no-id')
        iframe_src = iframe.get('src', 'no-src')
        print(f"\n[{i}] Iframe:")
        print(f"  id: {iframe_id}")
        print(f"  src: {iframe_src}")
    
    # Check if there's an iframe and inspect it
    if iframes:
        print("\n" + "="*80)
        print("INSPECTING IFRAME CONTENT")
        print("="*80)
        try:
            # Get first iframe
            iframe_element = page.frame_locator('iframe').first
            
            # Try to find inputs in iframe
            iframe_inputs = iframe_element.locator('input').all()
            print(f"\nFound {len(iframe_inputs)} inputs in iframe:")
            for i, inp in enumerate(iframe_inputs):
                try:
                    inp_id = inp.get_attribute('id') or 'no-id'
                    inp_type = inp.get_attribute('type') or 'text'
                    is_visible = inp.is_visible()
                    print(f"  [{i}] id={inp_id}, type={inp_type}, visible={is_visible}")
                except:
                    pass
        except Exception as e:
            print(f"Error inspecting iframe: {e}")
    
    # Look for any element with text containing "parcel"
    print("\n" + "="*80)
    print("ELEMENTS WITH 'PARCEL' TEXT")
    print("="*80)
    parcel_elements = soup.find_all(string=lambda text: text and 'parcel' in text.lower())
    for i, elem in enumerate(parcel_elements[:10]):  # First 10
        parent = elem.parent
        print(f"\n[{i}] {parent.name} tag:")
        print(f"  text: {elem.strip()[:100]}")
        print(f"  parent id: {parent.get('id', 'no-id')}")
        print(f"  parent class: {parent.get('class', [])}")
    
    print("\n\nKeeping browser open for 30 seconds...")
    time.sleep(30)
    
    browser.close()

print("\nDone!")
