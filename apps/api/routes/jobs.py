from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import Optional
from datetime import datetime
import uuid
import os
import tempfile
from config.main import DB
from models.ParcelJob import ParcelJob, ParcelJobProgress, ParcelJobResult
from utils.file_parser import parse_parcel_file, validate_parcel_ids
from auth.entra_id import get_current_user

jobs_router = APIRouter(prefix="/jobs", tags=["Jobs"])


def detect_platform(url: str) -> str:
    """Detect GIS platform from URL"""
    url_lower = url.lower()
    
    if "wthgis.com" in url_lower:
        return "wthgis"
    elif "beacon.schneidercorp.com" in url_lower:
        return "beacon"
    elif "elevatemaps.io" in url_lower:
        return "elevate"
    elif "portico.mygisonline.com" in url_lower or "mygisonline.com" in url_lower:
        return "portico"
    else:
        return "unknown"


@jobs_router.post("/create")
async def create_parcel_job(
    parcel_file: UploadFile = File(..., description="File containing parcel IDs (TXT, CSV, or XLSX)"),
    shapefile_zip: UploadFile = File(..., description="ZIP file containing shapefiles"),
    county: str = Form(..., description="County name"),
    crs_id: int = Form(..., description="EPSG code for target CRS"),
    gis_url: str = Form(..., description="GIS portal URL"),
    user: Optional[dict] = Depends(get_current_user)
):
    """
    Create a new parcel research job
    
    Accepts:
    - Parcel file (TXT, CSV, or XLSX)
    - Shapefile ZIP
    - County, CRS, and GIS URL
    
    Returns job ID for tracking progress
    """
    job_id = str(uuid.uuid4())
    
    # Validate parcel file
    parcel_ext = parcel_file.filename.split('.')[-1].lower()
    if f'.{parcel_ext}' not in ['.txt', '.csv', '.xlsx']:
        raise HTTPException(
            status_code=400,
            detail="Invalid parcel file type. Allowed: TXT, CSV, XLSX"
        )
    
    # Validate shapefile
    if not shapefile_zip.filename.endswith('.zip'):
        raise HTTPException(
            status_code=400,
            detail="Shapefile must be a ZIP file"
        )
    
    # Parse parcel IDs to get count
    parcel_ids = await parse_parcel_file(parcel_file)
    parcel_ids = validate_parcel_ids(parcel_ids, max_count=1000)
    parcel_count = len(parcel_ids)
    
    # Reset file pointer after parsing
    await parcel_file.seek(0)
    
    # Detect platform
    platform = detect_platform(gis_url)
    
    # Create temporary directory for this job
    temp_dir = os.path.join(tempfile.gettempdir(), "parcel_jobs", job_id)
    os.makedirs(temp_dir, exist_ok=True)
    
    # Save parcel file locally
    parcel_local_path = os.path.join(temp_dir, f"parcels.{parcel_ext}")
    with open(parcel_local_path, "wb") as f:
        f.write(await parcel_file.read())
    
    # Save shapefile ZIP locally
    shapefile_local_path = os.path.join(temp_dir, "shapefiles.zip")
    with open(shapefile_local_path, "wb") as f:
        f.write(await shapefile_zip.read())
    
    # Upload to Azure for backup/persistence
    azure_parcel_path = f"jobs/{job_id}/parcels.{parcel_ext}"
    azure_shapefile_path = f"jobs/{job_id}/shapefiles.zip"
    
    DB.az.upload_file(parcel_local_path, azure_parcel_path)
    DB.az.upload_file(shapefile_local_path, azure_shapefile_path)
    
    # Create job in database
    job = ParcelJob(
        id=job_id,
        user_id=user.get("user_id") if user else None,
        user_email=user.get("email") if user else None,
        user_name=user.get("name") if user else None,
        county=county,
        crs_id=crs_id,
        gis_url=gis_url,
        platform=platform,
        parcel_file_path=parcel_local_path,
        shapefile_zip_path=shapefile_local_path,
        azure_parcel_path=azure_parcel_path,
        azure_shapefile_path=azure_shapefile_path,
        status="pending",
        parcel_count=parcel_count,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    DB.parcelJobsCollection.insert_one(job._to_dict())
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": f"Job created for {parcel_count} parcels in {county} county",
        "platform": platform,
        "parcel_count": parcel_count,
        "created_at": job.created_at
    }


@jobs_router.get("/{job_id}")
async def get_job_status(job_id: str, user: Optional[dict] = Depends(get_current_user)):
    """
    Get the status and progress of a parcel job
    
    Returns current status, progress, and results if completed
    Users can only access their own jobs
    """
    job_data = DB.parcelJobsCollection.find_one({"_id": job_id})
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Verify user owns this job (if authenticated)
    if user and user.get("user_id"):
        if job_data.get("user_id") != user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied: You can only view your own jobs")
    
    job = ParcelJob(**job_data)
    
    # Calculate progress percentage
    progress_pct = 0.0
    if job.parcel_count > 0:
        progress_pct = (job.parcels_completed / job.parcel_count) * 100
    
    response = {
        "job_id": job.id,
        "status": job.status,
        "county": job.county,
        "platform": job.platform,
        "current_step": job.current_step,
        "progress": {
            "total": job.parcel_count,
            "completed": job.parcels_completed,
            "failed": job.parcels_failed,
            "percentage": round(progress_pct, 2)
        },
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "completed_at": job.completed_at
    }
    
    # Add results if completed
    if job.status == "completed" and job.results:
        response["results"] = job.results
    
    # Add error if failed
    if job.status == "failed" and job.error_message:
        response["error"] = job.error_message
    
    return response


@jobs_router.get("/{job_id}/download/{file_type}")
async def download_job_result(job_id: str, file_type: str, user: Optional[dict] = Depends(get_current_user)):
    """
    Get download URL for job result files
    
    file_type: "excel", "dxf", "csv", "pdfs"
    Users can only download their own job results
    """
    job_data = DB.parcelJobsCollection.find_one({"_id": job_id})
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Verify user owns this job (if authenticated)
    if user and user.get("user_id"):
        if job_data.get("user_id") != user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied: You can only download your own job results")
    
    job = ParcelJob(**job_data)
    
    if job.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed. Current status: {job.status}"
        )
    
    if not job.results:
        raise HTTPException(status_code=404, detail="No results available")
    
    # Map file type to result key
    file_map = {
        "excel": "excel_url",
        "dxf": "dxf_url",
        "csv": "csv_url",
        "pdfs": "pdfs_zip_url"
    }
    
    if file_type not in file_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(file_map.keys())}"
        )
    
    url_key = file_map[file_type]
    download_url = job.results.get(url_key)
    
    if not download_url:
        raise HTTPException(
            status_code=404,
            detail=f"{file_type} file not available"
        )
    
    return {
        "job_id": job_id,
        "file_type": file_type,
        "download_url": download_url
    }


@jobs_router.delete("/{job_id}")
async def delete_job(job_id: str, user: Optional[dict] = Depends(get_current_user)):
    """
    Delete a job and its associated files
    
    Removes job from database and deletes files from Azure storage
    Users can only delete their own jobs
    """
    job_data = DB.parcelJobsCollection.find_one({"_id": job_id})
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Verify user owns this job (if authenticated)
    if user and user.get("user_id"):
        if job_data.get("user_id") != user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied: You can only delete your own jobs")
    
    # Delete from database
    DB.parcelJobsCollection.delete_one({"_id": job_id})
    
    # Delete Azure files
    try:
        # Delete all blobs with prefix jobs/{job_id}/
        prefix = f"jobs/{job_id}/"
        blob_list = DB.az.container_client.list_blobs(name_starts_with=prefix)
        deleted_count = 0
        for blob in blob_list:
            DB.az.container_client.delete_blob(blob.name)
            deleted_count += 1
        
        print(f"Deleted {deleted_count} blobs for job {job_id}")
    except Exception as e:
        print(f"Error deleting Azure files for job {job_id}: {e}")
    
    # Delete local temp files
    try:
        import shutil
        temp_dir = os.path.join(tempfile.gettempdir(), "parcel_jobs", job_id)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"Error deleting local files for job {job_id}: {e}")
    
    return {
        "message": f"Job {job_id} deleted successfully"
    }


@jobs_router.get("/")
async def list_jobs(limit: int = 50, offset: int = 0, user: Optional[dict] = Depends(get_current_user)):
    """
    List jobs for the current user with pagination
    
    Returns list of jobs sorted by creation date (newest first)
    Users only see their own jobs (filtered by user_id)
    """
    # Build query filter
    query_filter = {}
    if user and user.get("user_id"):
        # Filter by user_id if authenticated
        query_filter["user_id"] = user["user_id"]
    
    jobs = list(
        DB.parcelJobsCollection
        .find(query_filter)
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )
    
    total = DB.parcelJobsCollection.count_documents(query_filter)
    
    return {
        "jobs": [ParcelJob(**job).model_dump(by_alias=True) for job in jobs],
        "total": total,
        "limit": limit,
        "offset": offset
    }
