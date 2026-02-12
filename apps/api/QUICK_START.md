# Quick Start Guide

## Installation

```bash
# 1. Install Python dependencies (using pip with pyproject.toml)
pip install -e .

# Or if you prefer to install directly:
pip install fastapi uvicorn pymongo azure-storage-blob pydantic python-multipart \
    openpyxl pandas geopandas shapely pyproj ezdxf playwright beautifulsoup4 \
    requests "pyjwt[crypto]" cryptography

# 2. Install Playwright browser
python -m playwright install chromium

# 3. Copy environment file
cp env.example .env

# 4. Edit .env with your credentials
# - MongoDB connection string
# - Azure Storage connection string
# - Azure Entra ID credentials (optional)
```

## Configuration

Edit `.env`:

```env
MONGO_CONNECTION_STRING="mongodb://localhost:27017"
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."
NAME="county_research"

# Optional: Enable authentication
REQUIRE_AUTH="false"
AZURE_TENANT_ID=""
AZURE_CLIENT_ID=""
```

## Run

```bash
# Development
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Usage Example

### 1. Create Job

```bash
curl -X POST "http://localhost:8000/jobs/create" \
  -F "parcel_file=@parcels.txt" \
  -F "shapefile_zip=@shapefiles.zip" \
  -F "county=Jennings" \
  -F "crs_id=2965" \
  -F "gis_url=https://jenningsin.wthgis.com"
```

Response:
```json
{
  "job_id": "abc-123-def-456",
  "status": "pending",
  "message": "Job created for 150 parcels in Jennings county",
  "platform": "wthgis",
  "parcel_count": 150
}
```

### 2. Check Status

```bash
curl "http://localhost:8000/jobs/abc-123-def-456"
```

Response:
```json
{
  "job_id": "abc-123-def-456",
  "status": "processing",
  "current_step": "Scraping 150 parcels from wthgis",
  "progress": {
    "total": 150,
    "completed": 75,
    "failed": 2,
    "percentage": 50.0
  }
}
```

### 3. Download Results

```bash
# Excel
curl "http://localhost:8000/jobs/abc-123-def-456/download/excel"

# DXF
curl "http://localhost:8000/jobs/abc-123-def-456/download/dxf"

# CSV
curl "http://localhost:8000/jobs/abc-123-def-456/download/csv"

# PDFs (ZIP)
curl "http://localhost:8000/jobs/abc-123-def-456/download/pdfs"
```

## Input Files

### Parcel File (parcels.txt)
```
12-34-56-789-012.000-001
12-34-56-789-013.000-001
12-34-56-789-014.000-001
```

### Shapefile ZIP (shapefiles.zip)
Must contain:
- `*.shp` - Geometry
- `*.shx` - Index
- `*.dbf` - Attributes
- `*.prj` - Projection (optional)

## Output Files

- **Excel**: Enriched parcel data with owner info
- **DXF**: CAD file with boundaries and labels
- **CSV**: Label coordinates
- **PDFs**: Property Record Cards (ZIP)

## Troubleshooting

### "No matching parcel IDs found"
- Check parcel ID format matches shapefile
- Verify shapefile has IDPARCEL or similar column

### "Could not find parcel in WTHGIS search"
- Verify parcel ID is correct
- Check GIS URL is accessible
- Try searching manually on the portal

### "Authentication required"
- Set `REQUIRE_AUTH="false"` in .env for testing
- Or provide valid Bearer token in Authorization header

### Worker not processing jobs
- Check logs for errors
- Verify MongoDB connection
- Restart the API

## Monitoring

```bash
# Check logs
tail -f logs/api.log

# List jobs
curl "http://localhost:8000/jobs?limit=10"

# Health check
curl "http://localhost:8000/health"
```

## Cleanup

Jobs are automatically deleted after 3 days. To manually trigger cleanup:

```python
from scheduler import JobCleanupScheduler
from config.main import DB

scheduler = JobCleanupScheduler(DB)
scheduler.cleanup_now()
```

## Support

- API Docs: http://localhost:8000/docs
- Implementation Guide: IMPLEMENTATION_COMPLETE.md
- Architecture: README_SIMPLIFIED.md
