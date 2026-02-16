"""
Background worker for processing parcel research jobs
"""
import time
import threading
import sys
import asyncio
from datetime import datetime
from typing import Optional
from models.ParcelJob import ParcelJob
from scrapers.platform_factory import get_scraper
from utils.label_exporter import LabelExporter
from config.settings import (
    SCRAPER_PAGE_DELAY_MIN,
    SCRAPER_PAGE_DELAY_MAX,
    SCRAPER_PDF_DELAY_MIN,
    SCRAPER_PDF_DELAY_MAX,
    SCRAPER_BROWSER_TIMEOUT_MS
)
import traceback

# On Windows, set event loop policy to support subprocess operations (required by Playwright)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class ParcelJobWorker:
    """
    Background worker that polls for pending parcel jobs and processes them
    """
    
    def __init__(self, db_manager, poll_interval: int = 5):
        """
        Initialize worker
        
        Args:
            db_manager: DatabaseManager instance
            poll_interval: Seconds between polling for new jobs
        """
        self.db = db_manager
        self.poll_interval = poll_interval
        self.running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the worker in a background thread"""
        if self.running:
            print("Worker already running")
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="ParcelJobWorker")
        self._thread.start()
        print("ParcelJobWorker started")
    
    def stop(self):
        """Stop the worker"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=10)
        print("ParcelJobWorker stopped")
    
    def _run(self):
        """Main worker loop"""
        print("ParcelJobWorker: Starting main loop")
        
        # On Windows, set event loop policy for this thread
        import sys
        import asyncio
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        while self.running:
            try:
                # Get next pending job (FIFO)
                job_data = self.db.parcelJobsCollection.find_one_and_update(
                    {"status": "pending"},
                    {"$set": {
                        "status": "processing",
                        "started_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }},
                    sort=[("created_at", 1)],  # FIFO
                    return_document=True
                )
                
                if job_data:
                    job = ParcelJob(**job_data)
                    print(f"Processing job {job.id} for {job.county} county")
                    self._process_job(job)
                else:
                    # No pending jobs, sleep
                    time.sleep(self.poll_interval)
                    
            except Exception as e:
                print(f"Worker error: {e}")
                traceback.print_exc()
                time.sleep(self.poll_interval)
    
    def _process_job(self, job: ParcelJob):
        """
        Process a single parcel job
        
        Steps:
        1. Parse parcel file
        2. Scrape GIS portal (platform-specific)
        3. Download PDFs
        4. Match with shapefiles
        5. Generate DXF + CSV labels
        6. Upload results to Azure
        """
        try:
            # Check if job was cancelled before starting
            current_job = self.db.parcelJobsCollection.find_one({"_id": job.id})
            if current_job and current_job.get("status") == "cancelled":
                print(f"Job {job.id} was cancelled, skipping processing")
                return
            
            # Step 1: Verify input files exist, download from Azure if missing
            import os
            
            if not os.path.exists(job.parcel_file_path):
                print(f"Parcel file not found locally, downloading from Azure: {job.azure_parcel_path}")
                os.makedirs(os.path.dirname(job.parcel_file_path), exist_ok=True)
                self.db.az.download_file(job.azure_parcel_path, job.parcel_file_path)
            
            if not os.path.exists(job.shapefile_zip_path):
                print(f"Shapefile not found locally, downloading from Azure: {job.azure_shapefile_path}")
                os.makedirs(os.path.dirname(job.shapefile_zip_path), exist_ok=True)
                self.db.az.download_file(job.azure_shapefile_path, job.shapefile_zip_path)
            
            # Step 2: Update status
            self._update_job_status(job.id, "processing", "Parsing parcel file")
            
            # Step 3: Get platform-specific scraper
            scraper = get_scraper(job.platform)
            
            # Step 3: Scrape parcels
            self._update_job_status(job.id, "processing", f"Scraping {job.parcel_count} parcels from {job.platform}")
            
            scraped_data = scraper.scrape_parcels(
                parcel_file_path=job.parcel_file_path,
                base_url=job.gis_url,
                county=job.county,
                job_id=job.id,
                progress_callback=lambda completed, total: self._update_progress(job.id, completed, total)
            )
            
            # Check if cancelled during scraping
            current_job = self.db.parcelJobsCollection.find_one({"_id": job.id})
            if current_job and current_job.get("status") == "cancelled":
                print(f"Job {job.id} was cancelled during scraping")
                return
            
            # Step 4: Process shapefiles and generate labels
            self._update_job_status(job.id, "processing", "Generating labels and DXF")
            
            exporter = LabelExporter(
                scraped_excel_path=scraped_data["excel_path"],
                shapefile_zip_path=job.shapefile_zip_path,
                crs_id=job.crs_id,
                job_id=job.id
            )
            
            output_files = exporter.export()
            
            # Step 5: Upload results to Azure
            self._update_job_status(job.id, "processing", "Uploading results")
            
            results = self._upload_results(job.id, output_files, scraped_data)
            
            # Step 6: Mark as completed
            self.db.parcelJobsCollection.update_one(
                {"_id": job.id},
                {"$set": {
                    "status": "completed",
                    "results": results,
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }}
            )
            
            print(f"Job {job.id} completed successfully")
            
        except Exception as e:
            error_msg = f"Job failed: {str(e)}\n{traceback.format_exc()}"
            print(f"Job {job.id} failed: {error_msg}")
            
            self.db.parcelJobsCollection.update_one(
                {"_id": job.id},
                {"$set": {
                    "status": "failed",
                    "error_message": error_msg,
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }}
            )
    
    def _update_job_status(self, job_id: str, status: str, current_step: str):
        """Update job status and current step"""
        self.db.parcelJobsCollection.update_one(
            {"_id": job_id},
            {"$set": {
                "status": status,
                "current_step": current_step,
                "updated_at": datetime.utcnow()
            }}
        )
    
    def _update_progress(self, job_id: str, completed: int, total: int):
        """Update job progress"""
        self.db.parcelJobsCollection.update_one(
            {"_id": job_id},
            {"$set": {
                "parcels_completed": completed,
                "updated_at": datetime.utcnow()
            }}
        )
    
    def _upload_results(self, job_id: str, output_files: dict, scraped_data: dict) -> dict:
        """
        Upload result files to Azure in jobs/{job_id}/ folder and return public URLs
        
        Args:
            job_id: Job ID
            output_files: Dict with path to DXF file
            scraped_data: Dict with paths to Excel, PDFs
            
        Returns:
            Dict with public URLs for all result files
        """
        results = {}
        
        # All files go in jobs/{job_id}/ folder
        job_folder = f"jobs/{job_id}"
        
        # Upload Excel file
        if "excel_path" in scraped_data:
            blob_name = f"{job_folder}/parcels_enriched.xlsx"
            self.db.az.upload_file(scraped_data["excel_path"], blob_name)
            results["excel_url"] = self.db.az.get_public_url(blob_name)
        
        # Upload DXF file
        if "dxf_path" in output_files:
            blob_name = f"{job_folder}/labels.dxf"
            self.db.az.upload_file(output_files["dxf_path"], blob_name)
            results["dxf_url"] = self.db.az.get_public_url(blob_name)
        
        # Upload PDFs as PRC.zip (extracts to PRC folder)
        if "pdfs_dir" in scraped_data:
            import shutil
            import os
            
            # Create PRC folder structure for ZIP
            temp_prc_dir = f"/tmp/{job_id}_PRC"
            prc_folder = os.path.join(temp_prc_dir, "PRC")
            os.makedirs(prc_folder, exist_ok=True)
            
            # Copy PDFs to PRC folder
            for pdf_file in os.listdir(scraped_data["pdfs_dir"]):
                if pdf_file.endswith('.pdf'):
                    src = os.path.join(scraped_data["pdfs_dir"], pdf_file)
                    dst = os.path.join(prc_folder, pdf_file)
                    shutil.copy2(src, dst)
            
            # Create ZIP (will contain PRC folder)
            prc_zip_path = f"/tmp/{job_id}_PRC.zip"
            shutil.make_archive(
                prc_zip_path.replace('.zip', ''),
                'zip',
                temp_prc_dir
            )
            
            blob_name = f"{job_folder}/PRC.zip"
            self.db.az.upload_file(prc_zip_path, blob_name)
            results["prc_zip_url"] = self.db.az.get_public_url(blob_name)
            
            # Clean up temp files
            if os.path.exists(prc_zip_path):
                os.remove(prc_zip_path)
            if os.path.exists(temp_prc_dir):
                shutil.rmtree(temp_prc_dir)
        
        return results
