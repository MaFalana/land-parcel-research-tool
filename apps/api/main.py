from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import sys
import asyncio

# Import configuration
from config.settings import (
    API_TITLE,
    API_VERSION,
    API_DESCRIPTION,
    CORS_ORIGINS,
    WORKER_POLL_INTERVAL,
    JOB_RETENTION_DAYS
)
from config.main import DB

# Import routers
from routes.jobs import jobs_router
from worker import ParcelJobWorker
from scheduler import JobCleanupScheduler

# On Windows, set event loop policy for Playwright support
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(jobs_router)

@app.on_event("startup")
async def startup_event():
    """
    FastAPI startup event handler.
    
    This function runs when the application starts and:
    1. Resets any stale "processing" jobs to "pending" status
    2. Starts the background worker thread
    3. Starts the job cleanup scheduler
    """
    print("\n🚀 Starting County Research Automation API...")
    
    # Reset stale jobs that were processing when the app shut down
    try:
        result = DB.parcelJobsCollection.update_many(
            {"status": "processing"},
            {"$set": {"status": "pending", "updated_at": datetime.utcnow()}}
        )
        if result.modified_count > 0:
            print(f"✓ Reset {result.modified_count} stale jobs to pending")
    except Exception as e:
        print(f"✗ Failed to reset stale jobs: {e}")
    
    # Start the worker thread
    try:
        worker = ParcelJobWorker(DB, poll_interval=WORKER_POLL_INTERVAL)
        worker.start()
        print(f"✓ Worker started (poll interval: {WORKER_POLL_INTERVAL}s)")
    except Exception as e:
        print(f"✗ Failed to start worker: {e}")
    
    # Start the cleanup scheduler
    try:
        scheduler = JobCleanupScheduler(DB, retention_days=JOB_RETENTION_DAYS)
        scheduler.start()
        print(f"✓ Cleanup scheduler started (retention: {JOB_RETENTION_DAYS} days)")
    except Exception as e:
        print(f"✗ Failed to start scheduler: {e}")
    
    print("✅ API ready!\n")


@app.get(
    '/',
    summary="API root",
    description="Get basic API information and available endpoints.",
    tags=["Root"]
)
def root():
    """
    API root endpoint.
    
    Returns basic information about the API and links to documentation.
    """
    data = {
        "name": API_TITLE,
        "version": API_VERSION,
        "description": API_DESCRIPTION,
        "framework": "FastAPI",
        "documentation": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "health": "/health",
        "endpoints": {
            "jobs": "/jobs/",
            "create_job": "/jobs/create",
            "job_status": "/jobs/{job_id}",
            "download": "/jobs/{job_id}/download/{file_type}"
        }
    }

    return data

@app.get("/health")
def health():
    return {"ok": True}

# Start the server when the script is run directly
if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    #uvicorn.run()