"""
Hamilton County (ArcGIS Experience) scraper

Handles scraping from Hamilton County's ArcGIS Experience portal.
This is a JavaScript-heavy site that requires Playwright for interaction.

Workflow:
1. Navigate to ArcGIS Experience page
2. Search for parcel by Parcel ID
3. Click on search result to open popup
4. Navigate to property information page (external link)
5. Extract owner data from Ownership Information tab
6. Navigate to Property Assessment tab
7. Download most recent Property Record Card PDF
"""
from scrapers.base_scraper import BaseScraper
from typing import Dict, Callable, Optional
import os
import tempfile
import time
import random
import re
import requests
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from datetime import datetime


class HamiltonScraper(BaseScraper):
    """Scraper for Hamilton County ArcGIS Experience platform"""
    
    def __init__(self):
        super().__init__()
        self.platform_name = "Hamilton County ArcGIS"
        # Delay ranges (in seconds)
        self.page_delay_range = (2, 4)  # 2-4 seconds between page requests
        self.pdf_delay_range = (1, 3)   # 1-3 seconds before PDF downloads
    
    def scrape_parcels(
        self,
        parcel_file_path: str,
        base_url: str,
        county: str,
        job_id: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict:
        """
        Scrape parcel data from Hamilton County ArcGIS Experience portal
        
        Steps:
        1. Parse parcel IDs from input file
        2. Open browser and navigate to ArcGIS Experience
        3. For each parcel: search, extract data, download PRC
        4. Save to Excel with progress tracking
        
        Args:
            parcel_file_path: Path to file with parcel IDs
            base_url: ArcGIS Experience URL
            county: County name
            job_id: Job ID for output files
            progress_callback: Function to report progress
            
        Returns:
            Dict with excel_path and stats
        """
        # Parse parcel IDs
        parcel_ids = self.read_parcel_ids(parcel_file_path)
        total_parcels = len(parcel_ids)
        
        print(f"Hamilton Scraper: Processing {total_parcels} parcels for {county} county")
        
        # Create output directories
        output_dir = os.path.join(tempfile.gettempdir(), "parcel_jobs", job_id, "output")
        pdfs_dir = os.path.join(output_dir, "property_cards")
        os.makedirs(pdfs_dir, exist_ok=True)
        
        # Create Excel workbook
        excel_path = os.path.join(output_dir, f"{county}_hamilton_data.xlsx")
        wb = self._create_excel_template(county)
        ws = wb.active
        
        # Track progress
        processed = 0
        failed = 0
        
        # Create requests session for PDF downloads
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/pdf,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        })
        
        # Launch browser
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
                # Navigate to ArcGIS Experience
                print(f"Navigating to: {base_url}")
                page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
                
                # Wait for page to load (ArcGIS Experience is heavy)
                page.wait_for_timeout(5000)
                
                # TODO: Find and wait for search box to be ready
                print("Waiting for search interface to load...")
                
                # Process each parcel
                for idx, parcel_id in enumerate(parcel_ids, start=1):
                    row_num = idx + 2  # Data starts at row 3 (1-indexed)
                    
                    try:
                        print(f"Processing {idx}/{total_parcels}: {parcel_id}")
                        
                        # Search for parcel and extract data
                        parcel_data = self._search_parcel(page, parcel_id, base_url)
                        
                        if parcel_data:
                            # Write to Excel
                            ws.cell(row_num, 1, parcel_id)
                            ws.cell(row_num, 2, parcel_data.get('state_parcel_no', ''))
                            ws.cell(row_num, 3, parcel_data.get('owner_name', ''))
                            ws.cell(row_num, 4, parcel_data.get('owner_address', ''))
                            ws.cell(row_num, 5, parcel_data.get('owner_city', ''))
                            ws.cell(row_num, 6, parcel_data.get('owner_state', ''))
                            ws.cell(row_num, 7, parcel_data.get('owner_zip', ''))
                            ws.cell(row_num, 8, parcel_data.get('parcel_address', ''))
                            ws.cell(row_num, 9, parcel_data.get('parcel_city', ''))
                            ws.cell(row_num, 10, parcel_data.get('parcel_state', ''))
                            ws.cell(row_num, 11, parcel_data.get('parcel_zip', ''))
                            ws.cell(row_num, 12, parcel_data.get('legal_description', ''))
                            ws.cell(row_num, 13, parcel_data.get('latest_deed_date', ''))
                            ws.cell(row_num, 14, parcel_data.get('document_number', ''))
                            ws.cell(row_num, 15, parcel_data.get('deed_code', ''))
                            
                            # Download PRC PDF if available
                            prc_path = ''
                            if parcel_data.get('prc_url'):
                                try:
                                    owner_stub = self._owner_filename_stub(parcel_data.get('owner_name', 'Unknown'))
                                    pdf_filename = self._safe_filename(f"{owner_stub}_{parcel_id}.pdf")
                                    prc_full_path = os.path.join(pdfs_dir, pdf_filename)
                                    
                                    self._download_prc(session, parcel_data['prc_url'], prc_full_path)
                                    prc_path = prc_full_path
                                    print(f"  ✓ Downloaded PRC: {pdf_filename}")
                                except Exception as e:
                                    print(f"  ✗ Failed to download PRC: {e}")
                                    prc_path = f"ERROR: {str(e)[:50]}"
                            
                            ws.cell(row_num, 16, prc_path)
                            ws.cell(row_num, 17, 'SUCCESS')
                            
                            processed += 1
                        else:
                            ws.cell(row_num, 1, parcel_id)
                            ws.cell(row_num, 17, 'NOT_FOUND')
                            failed += 1
                        
                        # Save progress every 10 parcels
                        if idx % 10 == 0:
                            wb.save(excel_path)
                            print(f"Progress saved: {processed} successful, {failed} failed")
                        
                        # Report progress
                        if progress_callback:
                            progress_callback(idx, total_parcels)
                        
                        # Polite delay between parcels
                        delay = random.uniform(*self.page_delay_range)
                        time.sleep(delay)
                        
                    except Exception as e:
                        print(f"Error processing {parcel_id}: {e}")
                        import traceback
                        traceback.print_exc()
                        ws.cell(row_num, 1, parcel_id)
                        ws.cell(row_num, 17, f'ERROR: {str(e)[:50]}')
                        failed += 1
                        continue
                
            finally:
                browser.close()
        
        # Final save
        wb.save(excel_path)
        
        print(f"\nHamilton Scraper: Complete!")
        print(f"  Processed: {processed}/{total_parcels}")
        print(f"  Failed: {failed}")
        print(f"  Excel: {excel_path}")
        print(f"  PDFs: {pdfs_dir}")
        
        return {
            "excel_path": excel_path,
            "pdfs_dir": pdfs_dir,
            "total": total_parcels,
            "processed": processed,
            "failed": failed
        }
    
    def _search_parcel(self, page, parcel_id: str, base_url: str) -> Optional[Dict]:
        """
        Search for a parcel and extract data
        
        Args:
            page: Playwright page object
            parcel_id: Parcel ID to search for
            base_url: Base URL of ArcGIS Experience
        
        Returns dict with parcel data or None if not found
        """
        try:
            # TODO: Implement search logic
            # 1. Find search box
            # 2. Enter parcel ID
            # 3. Wait for results
            # 4. Click on result
            # 5. Extract data from popup or navigate to property page
            
            print(f"  Searching for parcel: {parcel_id}")
            
            # Placeholder - will implement after testing
            return None
            
        except Exception as e:
            print(f"Error searching for parcel {parcel_id}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_excel_template(self, county: str) -> openpyxl.Workbook:
        """Create Excel workbook with formatted headers"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"{county} Parcels"
        
        # Header row
        headers = [
            'Parcel ID',
            'State Parcel No',
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
            'Report Card Path',
            'Status'
        ]
        
        # Style headers
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        
        for col_num, header in enumerate(headers, start=1):
            cell = ws.cell(1, col_num, header)
            cell.font = Font(bold=True, size=12, color="FFFFFF")
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Set column widths
        ws.column_dimensions['A'].width = 25  # Parcel ID
        ws.column_dimensions['B'].width = 25  # State Parcel No
        ws.column_dimensions['C'].width = 30  # Owner Name
        ws.column_dimensions['D'].width = 30  # Owner Address
        ws.column_dimensions['E'].width = 20  # Owner City
        ws.column_dimensions['F'].width = 8   # Owner State
        ws.column_dimensions['G'].width = 12  # Owner Zip
        ws.column_dimensions['H'].width = 30  # Parcel Address
        ws.column_dimensions['I'].width = 20  # Parcel City
        ws.column_dimensions['J'].width = 8   # Parcel State
        ws.column_dimensions['K'].width = 12  # Parcel Zip
        ws.column_dimensions['L'].width = 50  # Legal Description
        ws.column_dimensions['M'].width = 15  # Deed Date
        ws.column_dimensions['N'].width = 20  # Document Number
        ws.column_dimensions['O'].width = 12  # Deed Type
        ws.column_dimensions['P'].width = 50  # Report Card Path
        ws.column_dimensions['Q'].width = 15  # Status
        
        # Freeze header row
        ws.freeze_panes = 'A2'
        
        return wb
    
    def _safe_filename(self, filename: str) -> str:
        """Convert string to safe filename"""
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200-len(ext)] + ext
        return filename
    
    def _owner_filename_stub(self, owner_name: str) -> str:
        """
        Create a short filename stub from owner name
        Takes first 25 chars, removes special chars
        """
        if not owner_name or owner_name == 'Unknown':
            return 'Unknown'
        
        # Take first 25 characters
        stub = owner_name[:25]
        # Remove special characters, keep alphanumeric and spaces
        stub = re.sub(r'[^a-zA-Z0-9\s]', '', stub)
        # Replace spaces with underscores
        stub = stub.replace(' ', '_')
        # Remove multiple underscores
        stub = re.sub(r'_+', '_', stub)
        return stub.strip('_')
    
    def _download_prc(self, session, url: str, output_path: str):
        """Download PRC PDF with polite delay"""
        # Polite delay before download
        delay = random.uniform(*self.pdf_delay_range)
        time.sleep(delay)
        
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
