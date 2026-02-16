from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime
import uuid
import os
import tempfile
import io
from config.main import DB
from config.settings import MAX_UPLOAD_SIZE_BYTES
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
    shapefile_zip: Optional[UploadFile] = File(None, description="ZIP file containing shapefiles (optional if using pre-supplied shapefiles)"),
    county: str = Form(..., description="County name"),
    crs_id: int = Form(..., description="EPSG code for target CRS"),
    gis_url: str = Form(..., description="GIS portal URL"),
    user: Optional[dict] = Depends(get_current_user)
):
    """
    Create a new parcel research job
    
    Accepts:
    - Parcel file (TXT, CSV, or XLSX) - max 5GB
    - Shapefile ZIP (optional) - max 5GB. If not provided, will use pre-supplied shapefiles from Azure
    - County, CRS, and GIS URL
    
    Returns job ID for tracking progress
    """
    job_id = str(uuid.uuid4())
    
    # Validate parcel file size
    parcel_file.file.seek(0, 2)  # Seek to end
    parcel_size = parcel_file.file.tell()
    parcel_file.file.seek(0)  # Reset to start
    
    if parcel_size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Parcel file too large. Max size: {MAX_UPLOAD_SIZE_BYTES / (1024**3):.1f} GB"
        )
    
    # Validate parcel file type
    parcel_ext = parcel_file.filename.split('.')[-1].lower()
    if f'.{parcel_ext}' not in ['.txt', '.csv', '.xlsx']:
        raise HTTPException(
            status_code=400,
            detail="Invalid parcel file type. Allowed: TXT, CSV, XLSX"
        )
    
    # Handle shapefile: try Azure first, then user upload
    use_azure_shapefile = False
    azure_shapefile_source = f"GIS/Indiana/Parcels/Current/{county}.zip"
    
    if shapefile_zip is None:
        # No upload provided, check if Azure has it
        if DB.az.blob_exists(azure_shapefile_source):
            use_azure_shapefile = True
            print(f"Using pre-supplied shapefile from Azure: {azure_shapefile_source}")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"No shapefile provided and no pre-supplied shapefile found for {county} county. Please upload a shapefile ZIP."
            )
    else:
        # User provided upload, validate it
        shapefile_zip.file.seek(0, 2)
        shapefile_size = shapefile_zip.file.tell()
        shapefile_zip.file.seek(0)
        
        if shapefile_size > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Shapefile too large. Max size: {MAX_UPLOAD_SIZE_BYTES / (1024**3):.1f} GB"
            )
        
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
    
    # Handle shapefile based on source
    shapefile_local_path = os.path.join(temp_dir, "shapefiles.zip")
    azure_shapefile_path = None
    
    if use_azure_shapefile:
        # Download from Azure pre-supplied location
        DB.az.download_file(azure_shapefile_source, shapefile_local_path)
        # Don't upload back to Azure (it's already there)
        azure_shapefile_path = azure_shapefile_source
    else:
        # Save user-uploaded shapefile locally
        with open(shapefile_local_path, "wb") as f:
            f.write(await shapefile_zip.read())
        
        # Upload user's shapefile to Azure for backup
        azure_shapefile_path = f"jobs/{job_id}/shapefiles.zip"
        DB.az.upload_file(shapefile_local_path, azure_shapefile_path)
    
    # Upload parcel file to Azure for backup/persistence
    azure_parcel_path = f"jobs/{job_id}/parcels.{parcel_ext}"
    DB.az.upload_file(parcel_local_path, azure_parcel_path)
    
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
    
    # Calculate time estimates for processing jobs
    elapsed_seconds = None
    estimated_remaining_seconds = None
    
    if job.status == "processing" and job.started_at:
        elapsed = datetime.utcnow() - job.started_at
        elapsed_seconds = int(elapsed.total_seconds())
        
        # Estimate remaining time based on progress
        if job.parcels_completed > 0:
            avg_time_per_parcel = elapsed_seconds / job.parcels_completed
            parcels_remaining = job.parcel_count - job.parcels_completed
            estimated_remaining_seconds = int(avg_time_per_parcel * parcels_remaining)
    
    response = {
        "id": job.id,  # Use 'id' instead of 'job_id' for frontend compatibility
        "status": job.status,
        "county": job.county,
        "platform": job.platform,
        "crs_id": job.crs_id,  # Add CRS ID
        "parcel_count": job.parcel_count,  # Add parcel count at top level
        "current_step": job.current_step,
        "error_message": job.error_message,  # Add error message at top level
        "created_at": (job.created_at.isoformat() + 'Z') if job.created_at else None,
        "updated_at": (job.updated_at.isoformat() + 'Z') if job.updated_at else None,
        "started_at": (job.started_at.isoformat() + 'Z') if job.started_at else None,
        "completed_at": (job.completed_at.isoformat() + 'Z') if job.completed_at else None,
        "progress": {
            "total": job.parcel_count,
            "completed": job.parcels_completed,
            "failed": job.parcels_failed,
            "percentage": round(progress_pct, 2)
        },
        "timing": {
            "elapsed_seconds": elapsed_seconds,
            "estimated_remaining_seconds": estimated_remaining_seconds
        }
    }
    
    # Add results if completed
    if job.status == "completed" and job.results:
        response["results"] = job.results
    
    return response


@jobs_router.get("/{job_id}/download/{file_type}")
async def download_job_result(job_id: str, file_type: str, user: Optional[dict] = Depends(get_current_user)):
    """
    Download job result files directly
    
    file_type: "excel", "labels" (DXF labels ZIP)
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
    
    # Map file type to result key and content type
    file_map = {
        "excel": {
            "key": "excel_url",
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "extension": "xlsx"
        },
        "labels": {
            "key": "dxf_url",  # This points to labels.dxf file
            "content_type": "application/dxf",  # DXF is a CAD format
            "extension": "dxf"
        },
        "prc": {
            "key": "prc_zip_url",
            "content_type": "application/zip",
            "extension": "zip"
        }
    }
    
    if file_type not in file_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(file_map.keys())}"
        )
    
    file_info = file_map[file_type]
    azure_path = job.results.get(file_info["key"])
    
    if not azure_path:
        raise HTTPException(
            status_code=404,
            detail=f"{file_type} file not available"
        )
    
    # Extract blob name from URL if it's a full URL
    # URLs look like: https://account.blob.core.windows.net/container/path/to/file
    if azure_path.startswith("http"):
        # Extract the blob path after the container name
        parts = azure_path.split(f"/{DB.az.container_name}/")
        if len(parts) > 1:
            azure_path = parts[1]
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid Azure URL format: {azure_path}"
            )
    
    # Download file from Azure
    try:
        file_data = DB.az.download_file_bytes(azure_path)
        
        # Create filename
        filename = f"{job.county}_{file_type}.{file_info['extension']}"
        
        # Return file as streaming response
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=file_info["content_type"],
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        import traceback
        error_detail = f"Failed to download file from '{azure_path}': {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Log to console
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download file: {str(e)}"
        )


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
async def list_jobs(
    limit: int = 50, 
    offset: int = 0, 
    status: Optional[str] = None,
    user: Optional[dict] = Depends(get_current_user)
):
    """
    List jobs for the current user with pagination and filtering
    
    Query parameters:
    - limit: Max number of jobs to return (default: 50)
    - offset: Number of jobs to skip (default: 0)
    - status: Filter by status (pending, processing, completed, failed, cancelled)
    
    Returns list of jobs sorted by creation date (newest first)
    Users only see their own jobs (filtered by user_id)
    """
    # Build query filter
    query_filter = {}
    if user and user.get("user_id"):
        # Filter by user_id if authenticated
        query_filter["user_id"] = user["user_id"]
    
    # Add status filter if provided
    if status:
        valid_statuses = ["pending", "processing", "completed", "failed", "cancelled"]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Allowed: {', '.join(valid_statuses)}"
            )
        query_filter["status"] = status
    
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
        "offset": offset,
        "filters": {
            "status": status
        }
    }


@jobs_router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, user: Optional[dict] = Depends(get_current_user)):
    """
    Cancel a running job
    
    Only pending or processing jobs can be cancelled
    Users can only cancel their own jobs
    """
    job_data = DB.parcelJobsCollection.find_one({"_id": job_id})
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Verify user owns this job (if authenticated)
    if user and user.get("user_id"):
        if job_data.get("user_id") != user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied: You can only cancel your own jobs")
    
    job = ParcelJob(**job_data)
    
    if job.status not in ["pending", "processing"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job.status}"
        )
    
    # Update job status to cancelled
    DB.parcelJobsCollection.update_one(
        {"_id": job_id},
        {"$set": {
            "status": "cancelled",
            "updated_at": datetime.utcnow(),
            "completed_at": datetime.utcnow()
        }}
    )
    
    return {
        "job_id": job_id,
        "status": "cancelled",
        "message": "Job cancelled successfully"
    }


@jobs_router.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring
    
    Returns API status and database connectivity
    """
    try:
        # Test database connection
        DB.parcelJobsCollection.find_one({})
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "version": "2.0.0"
    }
