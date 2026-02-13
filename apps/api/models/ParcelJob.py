from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ParcelJob(BaseModel):
    """Model for parcel research jobs"""
    model_config = {"populate_by_name": True}
    
    id: str = Field("", alias="_id", description="Job ID (UUID)")
    
    # User info (from Entra ID)
    user_id: Optional[str] = Field(None, description="User ID (oid from token)")
    user_email: Optional[str] = Field(None, description="User email")
    user_name: Optional[str] = Field(None, description="User display name")
    
    # Input parameters
    county: str = Field(..., description="County name")
    crs_id: int = Field(..., description="EPSG code for coordinate reference system")
    gis_url: str = Field(..., description="GIS portal URL")
    platform: str = Field(..., description="GIS platform type (wthgis, beacon, elevate, portico)")
    
    # File paths
    parcel_file_path: str = Field(..., description="Local path to uploaded parcel file")
    shapefile_zip_path: Optional[str] = Field(None, description="Local path to uploaded shapefile ZIP")
    
    # Azure storage paths
    azure_parcel_path: str = Field(..., description="Azure blob path for parcel file")
    azure_shapefile_path: Optional[str] = Field(None, description="Azure blob path for shapefile ZIP")
    
    # Processing status
    status: str = Field("pending", description="Job status: pending, processing, completed, failed")
    current_step: Optional[str] = Field(None, description="Current processing step")
    progress: dict = Field(default_factory=dict, description="Progress tracking")
    
    # Results
    results: dict = Field(default_factory=dict, description="Job results and output file URLs")
    error_message: Optional[str] = Field(None, description="Error message if job failed")
    
    # Metadata
    parcel_count: int = Field(0, description="Total number of parcels to process")
    parcels_completed: int = Field(0, description="Number of parcels completed")
    parcels_failed: int = Field(0, description="Number of parcels that failed")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(None, description="When job processing started")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)
    
    def _to_dict(self):
        return self.model_dump(by_alias=True)


class ParcelJobProgress(BaseModel):
    """Progress information for a parcel job"""
    total: int
    completed: int
    failed: int
    current_step: Optional[str] = None
    percentage: float = 0.0


class ParcelJobResult(BaseModel):
    """Result files from a completed parcel job"""
    excel_url: Optional[str] = None
    dxf_url: Optional[str] = None
    csv_url: Optional[str] = None
    pdf_count: int = 0
