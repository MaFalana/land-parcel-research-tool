"""
Scheduler for periodic tasks like job cleanup
"""
import time
import threading
from datetime import datetime, timedelta
from typing import Optional
import shutil
import os
import tempfile


class JobCleanupScheduler:
    """
    Scheduler that runs daily to clean up old jobs
    
    Deletes jobs older than retention_days and their associated files
    """
    
    def __init__(self, db_manager, retention_days: int = 3, check_interval_hours: int = 24):
        """
        Initialize scheduler
        
        Args:
            db_manager: DatabaseManager instance
            retention_days: Number of days to keep jobs (default: 3)
            check_interval_hours: Hours between cleanup runs (default: 24)
        """
        self.db = db_manager
        self.retention_days = retention_days
        self.check_interval_seconds = check_interval_hours * 3600
        self.running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the scheduler in a background thread"""
        if self.running:
            print("Cleanup scheduler already running")
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="JobCleanupScheduler")
        self._thread.start()
        print(f"JobCleanupScheduler started (retention: {self.retention_days} days)")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=10)
        print("JobCleanupScheduler stopped")
    
    def _run(self):
        """Main scheduler loop"""
        print("JobCleanupScheduler: Starting main loop")
        
        while self.running:
            try:
                self._cleanup_old_jobs()
                
                # Sleep until next check
                time.sleep(self.check_interval_seconds)
                
            except Exception as e:
                print(f"Cleanup scheduler error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(3600)  # Sleep 1 hour on error
    
    def _cleanup_old_jobs(self):
        """Delete jobs older than retention_days"""
        cutoff_time = datetime.utcnow() - timedelta(days=self.retention_days)
        
        print(f"\n=== Job Cleanup: Deleting jobs older than {cutoff_time} ===")
        
        # Find old jobs
        old_jobs = list(self.db.parcelJobsCollection.find({
            "created_at": {"$lt": cutoff_time}
        }))
        
        if not old_jobs:
            print("No old jobs to clean up")
            return
        
        print(f"Found {len(old_jobs)} old jobs to delete")
        
        deleted_count = 0
        error_count = 0
        
        for job in old_jobs:
            job_id = job["_id"]
            
            try:
                print(f"Deleting job {job_id}...")
                
                # Delete from database
                self.db.parcelJobsCollection.delete_one({"_id": job_id})
                
                # Delete Azure files
                try:
                    prefix = f"jobs/{job_id}/"
                    blob_list = self.db.az.container_client.list_blobs(name_starts_with=prefix)
                    blob_count = 0
                    for blob in blob_list:
                        self.db.az.container_client.delete_blob(blob.name)
                        blob_count += 1
                    
                    if blob_count > 0:
                        print(f"  Deleted {blob_count} Azure blobs")
                except Exception as e:
                    print(f"  Error deleting Azure files: {e}")
                
                # Delete local temp files
                try:
                    temp_dir = os.path.join(tempfile.gettempdir(), "parcel_jobs", job_id)
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                        print(f"  Deleted local temp directory")
                except Exception as e:
                    print(f"  Error deleting local files: {e}")
                
                deleted_count += 1
                
            except Exception as e:
                print(f"Error deleting job {job_id}: {e}")
                error_count += 1
        
        print(f"\nCleanup complete: {deleted_count} jobs deleted, {error_count} errors")
    
    def cleanup_now(self):
        """Manually trigger cleanup (useful for testing)"""
        print("Manual cleanup triggered")
        self._cleanup_old_jobs()
