"""
Beacon (Schneider) platform scraper

Handles scraping from beacon.schneidercorp.com portals across multiple counties.
Uses flexible selectors to adapt to county-specific variations in element IDs.
"""
from scrapers.base_scraper import BaseScraper
from typing import Dict, Callable, Optional
import os
import tempfile
import time
import random
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from datetime import datetime


class BeaconScraper(BaseScraper):
    """Scraper for Beacon (Schneider) platform"""
    
    def __init__(self):
        super().__init__()
        self.platform_name = "Beacon"
    
    def scrape_parcels(
        self,
        parcel_file_path: str,
        base_url: str,
        county: str,
        job_id: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict:
        """
        Scrape parcel data from Beacon portal
        
        Steps:
        1. Parse parcel IDs from input file
        2. Extract AppID and LayerID from base_url
        3. Open browser and navigate to Beacon
        4. For each parcel: search, extract data
        5. Save to Excel with progress tracking
        
        Args:
            parcel_file_path: Path to file with parcel IDs
            base_url: Beacon portal URL (contains AppID, LayerID)
            county: County name
            job_id: Job ID for output files
            progress_callback: Function to report progress
            
        Returns:
            Dict with excel_path and stats
        """
        # IMMEDIATE DEBUG
        print("=" * 60)
        print("SCRAPER STARTED")
        print(f"Parcel file: {parcel_file_path}")
        print(f"Base URL: {base_url}")
        print(f"County: {county}")
        print("=" * 60)
        
        # Parse parcel IDs
        parcel_ids = self.read_parcel_ids(parcel_file_path)
        total_parcels = len(parcel_ids)
        
        print(f"Beacon Scraper: Processing {total_parcels} parcels for {county} county")
        
        # Extract AppID and LayerID from URL
        url_params = self._extract_url_params(base_url)
        if not url_params['app_id'] or not url_params['layer_id']:
            raise ValueError(f"Could not extract AppID/LayerID from URL: {base_url}")
        
        print(f"Beacon Config: AppID={url_params['app_id']}, LayerID={url_params['layer_id']}")
        
        # Create output directory
        output_dir = os.path.join(tempfile.gettempdir(), "parcel_jobs", job_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # Create Excel workbook
        excel_path = os.path.join(output_dir, f"{county}_beacon_data.xlsx")
        wb = self._create_excel_template(county)
        ws = wb.active
        
        # Track progress
        processed = 0
        failed = 0
        
        # Launch browser (headless mode with args to avoid detection)
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            
            try:
                # Navigate to Beacon portal
                print(f"Navigating to: {base_url}")
                page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
                
                # Wait a bit for page to settle (don't wait for networkidle - Beacon has background activity)
                page.wait_for_timeout(3000)
                
                # Check if we got an error page
                if "Something went wrong" in page.content():
                    print("Error page detected, retrying...")
                    page.reload(wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)
                
                # Click "Agree" or "Accept" button if present (terms and conditions)
                print("Checking for terms agreement...")
                try:
                    # Try multiple variations of agree/accept buttons
                    agree_selectors = [
                        'text=Agree',
                        'text=Accept',
                        'button:has-text("Agree")',
                        'button:has-text("Accept")',
                        'input[value*="Agree"]',
                        'input[value*="Accept"]'
                    ]
                    
                    for selector in agree_selectors:
                        try:
                            button = page.locator(selector).first
                            if button.is_visible(timeout=3000):
                                print(f"Found agreement button: {selector}")
                                button.click()
                                # Wait for dialog to close
                                page.wait_for_timeout(3000)
                                print("Clicked terms agreement button, page ready")
                                break
                        except:
                            continue
                except Exception as e:
                    print(f"No agreement button found or error: {e}")
                    pass  # No agree button, continue
                
                # Wait for search input to be available
                print("Waiting for search input to be ready...")
                try:
                    page.wait_for_selector('input[id*="txtParcelID"]', state="visible", timeout=10000)
                    print("Search input is ready")
                except Exception as e:
                    print(f"Warning: Search input not found immediately: {e}")
                    # Try waiting a bit more
                    page.wait_for_timeout(3000)
                
                # Process each parcel
                for idx, parcel_id in enumerate(parcel_ids, start=1):
                    row_num = idx + 2  # Data starts at row 3 (1-indexed)
                    
                    try:
                        print(f"Processing {idx}/{total_parcels}: {parcel_id}")
                        
                        # Search for parcel
                        parcel_data = self._search_parcel(page, parcel_id, base_url)
                        
                        if parcel_data:
                            # Write to Excel
                            ws.cell(row_num, 1, parcel_id)  # Column A: Parcel ID
                            ws.cell(row_num, 2, parcel_data.get('owner_name', ''))  # Column B: Owner Name
                            ws.cell(row_num, 3, parcel_data.get('owner_address', ''))  # Column C: Owner Address
                            ws.cell(row_num, 4, parcel_data.get('owner_city', ''))  # Column D: Owner City
                            ws.cell(row_num, 5, parcel_data.get('owner_state', ''))  # Column E: Owner State
                            ws.cell(row_num, 6, parcel_data.get('owner_zip', ''))  # Column F: Owner Zip
                            ws.cell(row_num, 7, parcel_data.get('parcel_address', ''))  # Column G: Parcel Address
                            ws.cell(row_num, 8, parcel_data.get('parcel_city', ''))  # Column H: Parcel City
                            ws.cell(row_num, 9, parcel_data.get('parcel_state', ''))  # Column I: Parcel State
                            ws.cell(row_num, 10, parcel_data.get('parcel_zip', ''))  # Column J: Parcel Zip
                            ws.cell(row_num, 11, parcel_data.get('legal_description', ''))  # Column K: Legal Desc
                            ws.cell(row_num, 12, parcel_data.get('latest_deed_date', ''))  # Column L: Deed Date
                            ws.cell(row_num, 13, parcel_data.get('document_number', ''))  # Column M: Doc #
                            ws.cell(row_num, 14, parcel_data.get('deed_code', ''))  # Column N: Deed Type
                            ws.cell(row_num, 15, 'SUCCESS')  # Column O: Status
                            
                            processed += 1
                        else:
                            # Parcel not found
                            ws.cell(row_num, 1, parcel_id)
                            ws.cell(row_num, 15, 'NOT_FOUND')
                            failed += 1
                        
                        # Save progress every 10 parcels
                        if idx % 10 == 0:
                            wb.save(excel_path)
                            print(f"Progress saved: {processed} successful, {failed} failed")
                        
                        # Report progress
                        if progress_callback:
                            progress_callback(idx, total_parcels)
                        
                        # Polite delay (2-5 seconds)
                        time.sleep(random.uniform(2.0, 5.0))
                        
                    except Exception as e:
                        print(f"Error processing {parcel_id}: {e}")
                        ws.cell(row_num, 1, parcel_id)
                        ws.cell(row_num, 15, f'ERROR: {str(e)[:50]}')
                        failed += 1
                        continue
                
            finally:
                browser.close()
        
        # Final save
        wb.save(excel_path)
        
        print(f"\nBeacon Scraper: Complete!")
        print(f"  Processed: {processed}/{total_parcels}")
        print(f"  Failed: {failed}")
        print(f"  Excel: {excel_path}")
        
        return {
            "excel_path": excel_path,
            "total": total_parcels,
            "processed": processed,
            "failed": failed
        }
    
    def _extract_url_params(self, url: str) -> Dict[str, str]:
        """Extract AppID, LayerID, PageTypeID, PageID from Beacon URL"""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        return {
            'app_id': params.get('AppID', [''])[0],
            'layer_id': params.get('LayerID', [''])[0],
            'page_type_id': params.get('PageTypeID', ['1'])[0],
            'page_id': params.get('PageID', [''])[0]
        }
    
    def _parse_address(self, address_text: str) -> Dict[str, str]:
        """
        Parse address text into components (street, city, state, zip)
        
        Handles formats like:
        - "123 Main St, City, ST 12345"
        - "123 Main St\nCity, ST 12345"
        - "123 Main St City ST 12345"
        """
        import re
        
        result = {
            'street': '',
            'city': '',
            'state': '',
            'zip': ''
        }
        
        if not address_text:
            return result
        
        # Replace newlines with commas for easier parsing
        address_text = address_text.replace('\n', ', ').replace('\r', '')
        
        # Try to extract ZIP code (5 digits or 5+4 format)
        zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', address_text)
        if zip_match:
            result['zip'] = zip_match.group(1)
            # Remove ZIP from text
            address_text = address_text.replace(zip_match.group(0), '').strip()
        
        # Try to extract state (2 letter code before ZIP)
        state_match = re.search(r'\b([A-Z]{2})\s*,?\s*$', address_text)
        if state_match:
            result['state'] = state_match.group(1)
            # Remove state from text
            address_text = address_text[:state_match.start()].strip()
        
        # Split remaining text by comma
        parts = [p.strip() for p in address_text.split(',') if p.strip()]
        
        if len(parts) >= 2:
            # First part is street, last part is city
            result['street'] = parts[0]
            result['city'] = parts[-1]
        elif len(parts) == 1:
            # Only one part - assume it's the street
            result['street'] = parts[0]
        
        return result
    
    def _search_parcel(self, page, parcel_id: str, base_url: str) -> Optional[Dict]:
        """
        Search for a parcel and extract data using flexible selectors
        
        Returns dict with: owner_name, legal_description, latest_deed_date, 
                          document_number, deed_code
        """
        try:
            # Find search input using flexible selector with explicit wait
            search_input = page.locator('input[id*="txtParcelID"]').first
            
            # Wait for it to be ready
            search_input.wait_for(state="visible", timeout=10000)
            
            # Clear and fill search box
            search_input.clear(timeout=5000)
            search_input.fill(parcel_id, timeout=5000)
            search_input.press('Enter')
            
            # Wait for results to load (don't use networkidle - Beacon has background activity)
            page.wait_for_timeout(3000)
            
            # Check if we got results or "no results" message
            # Beacon shows property details if found, or stays on search page if not
            try:
                # Try to find legal description (indicates we found the parcel)
                legal_desc_elem = page.locator('span[id*="lblLegalDescription"]').first
                legal_desc_elem.wait_for(timeout=3000)
            except:
                # Legal description not found = parcel not found
                print(f"Parcel {parcel_id} not found in Beacon")
                page.goto(base_url)  # Go back to search page
                return None
            
            # Extract data
            data = {}
            
            # Owner name (from page title or owner section)
            try:
                owner_elem = page.locator('span[id*="lblOwner"], span[id*="lblOwnerName"]').first
                data['owner_name'] = owner_elem.inner_text(timeout=2000).strip()
            except:
                data['owner_name'] = ''
            
            # Owner address (mailing address)
            try:
                # Try to find owner address - usually in a span with "Address" in the ID
                owner_addr_elem = page.locator('span[id*="lblOwnerAddress"], span[id*="OwnerAddress"]').first
                owner_addr_text = owner_addr_elem.inner_text(timeout=2000).strip()
                
                # Parse address into components
                # Format is usually: "123 Main St, City, ST 12345" or multiple lines
                addr_parts = self._parse_address(owner_addr_text)
                data['owner_address'] = addr_parts.get('street', '')
                data['owner_city'] = addr_parts.get('city', '')
                data['owner_state'] = addr_parts.get('state', '')
                data['owner_zip'] = addr_parts.get('zip', '')
            except:
                data['owner_address'] = ''
                data['owner_city'] = ''
                data['owner_state'] = ''
                data['owner_zip'] = ''
            
            # Parcel address (property location)
            try:
                # Try to find parcel/property address
                parcel_addr_elem = page.locator('span[id*="lblPropertyAddress"], span[id*="lblSitusAddress"], span[id*="lblLocation"]').first
                parcel_addr_text = parcel_addr_elem.inner_text(timeout=2000).strip()
                
                # Parse address into components
                addr_parts = self._parse_address(parcel_addr_text)
                data['parcel_address'] = addr_parts.get('street', '')
                data['parcel_city'] = addr_parts.get('city', '')
                data['parcel_state'] = addr_parts.get('state', '')
                data['parcel_zip'] = addr_parts.get('zip', '')
            except:
                data['parcel_address'] = ''
                data['parcel_city'] = ''
                data['parcel_state'] = ''
                data['parcel_zip'] = ''
            
            # Legal description
            try:
                data['legal_description'] = legal_desc_elem.inner_text().strip()
            except:
                data['legal_description'] = ''
            
            # Transfer history (latest deed)
            try:
                # Find transfer history table
                transfer_table = page.locator('table[id*="gvwTransferHistory"], table[id*="TransferHistory"]').first
                
                # Get first row (most recent transfer)
                first_row = transfer_table.locator('tbody tr').first
                
                # Date is usually in the first cell (th or td)
                date_cell = first_row.locator('th, td').first
                data['latest_deed_date'] = date_cell.inner_text(timeout=2000).strip()
                
                # Document number is usually in 3rd column
                doc_cell = first_row.locator('td').nth(2)
                data['document_number'] = doc_cell.inner_text(timeout=2000).strip()
                
                # Deed code might be in another column (WD, QC, etc.)
                # Try to find it
                try:
                    code_cell = first_row.locator('td').nth(1)
                    code_text = code_cell.inner_text(timeout=1000).strip()
                    # Check if it looks like a deed code (2-3 letters)
                    if len(code_text) <= 3 and code_text.isalpha():
                        data['deed_code'] = code_text
                    else:
                        data['deed_code'] = ''
                except:
                    data['deed_code'] = ''
                    
            except Exception as e:
                print(f"Could not extract transfer history: {e}")
                data['latest_deed_date'] = ''
                data['document_number'] = ''
                data['deed_code'] = ''
            
            # Go back to search page for next parcel
            page.goto(base_url, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            
            return data
            
        except Exception as e:
            print(f"Error searching for parcel {parcel_id}: {e}")
            # Try to recover by going back to search page
            try:
                page.goto(base_url)
            except:
                pass
            return None
    
    def _create_excel_template(self, county: str) -> openpyxl.Workbook:
        """Create Excel workbook with formatted headers"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"{county} Parcels"
        
        # Header row (row 1)
        headers = [
            'Parcel ID',
            'Owner Name',
            'Owner Address',
            'Owner City',
            'Owner State',
            'Owner Zip',
            'Parcel Address',
            'Parcel City',
            'Parcel State',
            'Parcel Zip',
            'Legal Description',
            'Latest Deed Date',
            'Document Number',
            'Deed Type',
            'Status'
        ]
        
        # Style for headers
        header_font = Font(bold=True, size=12)
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal='center', vertical='center')
        
        for col_num, header in enumerate(headers, start=1):
            cell = ws.cell(1, col_num, header)
            cell.font = Font(bold=True, size=12, color="FFFFFF")
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # Set column widths
        ws.column_dimensions['A'].width = 20  # Parcel ID
        ws.column_dimensions['B'].width = 30  # Owner Name
        ws.column_dimensions['C'].width = 30  # Owner Address
        ws.column_dimensions['D'].width = 20  # Owner City
        ws.column_dimensions['E'].width = 8   # Owner State
        ws.column_dimensions['F'].width = 12  # Owner Zip
        ws.column_dimensions['G'].width = 30  # Parcel Address
        ws.column_dimensions['H'].width = 20  # Parcel City
        ws.column_dimensions['I'].width = 8   # Parcel State
        ws.column_dimensions['J'].width = 12  # Parcel Zip
        ws.column_dimensions['K'].width = 50  # Legal Description
        ws.column_dimensions['L'].width = 15  # Deed Date
        ws.column_dimensions['M'].width = 20  # Document Number
        ws.column_dimensions['N'].width = 12  # Deed Type
        ws.column_dimensions['O'].width = 15  # Status
        
        # Freeze header row
        ws.freeze_panes = 'A2'
        
        return wb
