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
        # Parse parcel IDs
        parcel_ids = self._parse_parcel_file(parcel_file_path)
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
        
        # Launch browser
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            try:
                # Navigate to Beacon portal
                page.goto(base_url, wait_until="networkidle", timeout=30000)
                
                # Click "Agree" button if present
                try:
                    agree_button = page.locator('text=Agree').first
                    if agree_button.is_visible(timeout=3000):
                        agree_button.click()
                        page.wait_for_load_state("networkidle")
                except:
                    pass  # No agree button, continue
                
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
                            ws.cell(row_num, 2, parcel_data.get('owner_name', ''))  # Column B: Owner
                            ws.cell(row_num, 3, parcel_data.get('legal_description', ''))  # Column C: Legal Desc
                            ws.cell(row_num, 4, parcel_data.get('latest_deed_date', ''))  # Column D: Deed Date
                            ws.cell(row_num, 5, parcel_data.get('document_number', ''))  # Column E: Doc #
                            ws.cell(row_num, 6, parcel_data.get('deed_code', ''))  # Column F: Deed Type
                            ws.cell(row_num, 7, 'SUCCESS')  # Column G: Status
                            
                            processed += 1
                        else:
                            # Parcel not found
                            ws.cell(row_num, 1, parcel_id)
                            ws.cell(row_num, 7, 'NOT_FOUND')
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
                        ws.cell(row_num, 7, f'ERROR: {str(e)[:50]}')
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
    
    def _search_parcel(self, page, parcel_id: str, base_url: str) -> Optional[Dict]:
        """
        Search for a parcel and extract data using flexible selectors
        
        Returns dict with: owner_name, legal_description, latest_deed_date, 
                          document_number, deed_code
        """
        try:
            # Find search input using flexible selector
            search_input = page.locator('input[id*="txtParcelID"]').first
            
            # Clear and fill search box
            search_input.clear()
            search_input.fill(parcel_id)
            search_input.press('Enter')
            
            # Wait for results to load
            page.wait_for_load_state("networkidle", timeout=10000)
            
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
            page.goto(base_url)
            page.wait_for_load_state("networkidle")
            
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
        ws.column_dimensions['C'].width = 50  # Legal Description
        ws.column_dimensions['D'].width = 15  # Deed Date
        ws.column_dimensions['E'].width = 20  # Document Number
        ws.column_dimensions['F'].width = 12  # Deed Type
        ws.column_dimensions['G'].width = 15  # Status
        
        # Freeze header row
        ws.freeze_panes = 'A2'
        
        return wb
