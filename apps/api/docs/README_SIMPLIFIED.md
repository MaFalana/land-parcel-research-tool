# County Research Automation API - Simplified Architecture

## Overview

Streamlined API for automating county parcel research with GIS data extraction and label generation.

## Architecture

### Single Unified Workflow

```
POST /jobs/create
  ↓
[Upload Files: Parcels + Shapefiles]
  ↓
[Background Worker Processes Job]
  ├─ Step 1: Parse parcel IDs
  ├─ Step 2: Scrape GIS portal (platform auto-detected)
  ├─ Step 3: Download Property Record Card PDFs
  ├─ Step 4: Match with shapefiles
  ├─ Step 5: Generate DXF + CSV labels
  └─ Step 6: Upload results to Azure
  ↓
GET /jobs/{job_id}
  ↓
GET /jobs/{job_id}/download/{file_type}
```

## API Endpoints

### Create Job
```http
POST /jobs/create
Content-Type: multipart/form-data

parcel_file: File (TXT, CSV, or XLSX)
shapefile_zip: File (ZIP containing .shp, .shx, .dbf, etc.)
county: String
crs_id: Integer (EPSG code)
gis_url: String
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Job created for 150 parcels in Jennings county",
  "platform": "wthgis",
  "parcel_count": 150,
  "created_at": "2024-01-01T00:00:00"
}
```

### Get Job Status
```http
GET /jobs/{job_id}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "county": "Jennings",
  "platform": "wthgis",
  "current_step": "Scraping 150 parcels from wthgis",
  "progress": {
    "total": 150,
    "completed": 75,
    "failed": 2,
    "percentage": 50.0
  },
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:05:00"
}
```

**When completed:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "county": "Jennings",
  "platform": "wthgis",
  "progress": {
    "total": 150,
    "completed": 148,
    "failed": 2,
    "percentage": 100.0
  },
  "results": {
    "excel_url": "https://storage.blob.core.windows.net/.../parcels_enriched.xlsx",
    "dxf_url": "https://storage.blob.core.windows.net/.../labels.dxf",
    "csv_url": "https://storage.blob.core.windows.net/.../labels.csv",
    "pdfs_zip_url": "https://storage.blob.core.windows.net/.../property_cards.zip"
  },
  "created_at": "2024-01-01T00:00:00",
  "completed_at": "2024-01-01T00:15:00"
}
```

### Download Result File
```http
GET /jobs/{job_id}/download/{file_type}
```

**file_type:** `excel`, `dxf`, `csv`, `pdfs`

**Response:**
```json
{
  "job_id": "uuid",
  "file_type": "excel",
  "download_url": "https://storage.blob.core.windows.net/.../parcels_enriched.xlsx"
}
```

### List Jobs
```http
GET /jobs?limit=50&offset=0
```

### Delete Job
```http
DELETE /jobs/{job_id}
```

## File Formats

### Input: Parcel File
- **TXT**: One parcel ID per line
- **CSV**: First column or column named "Parcel ID"
- **XLSX**: First column or column named "Parcel ID"

Example:
```
12-34-56-789-012.000-001
12-34-56-789-013.000-001
12-34-56-789-014.000-001
```

### Input: Shapefile ZIP
Must contain at minimum:
- `.shp` - Shape geometry
- `.shx` - Shape index
- `.dbf` - Attribute database
- `.prj` - Projection (optional but recommended)

### Output: Enriched Excel
Columns:
- Parcel ID
- Owner Name, Address, City, State, Zip
- Property Address, City, State, Zip
- Legal Description
- Document/Instrument Number
- Report Card Path
- Status, Notes

### Output: DXF File
Contains:
- Parcel boundaries (PARCEL_BOUNDARIES_NOTES layer)
- Label text (PARCEL_LABELS layer)
  - Parcel number
  - Owner name
  - Instrument/Book-Page reference

### Output: CSV File
Columns: PARCELID, X, Y, LABEL

## Platform Detection

Platform is auto-detected from GIS URL:

| URL Pattern | Platform |
|-------------|----------|
| `wthgis.com` | WTHGIS (ThinkGIS) |
| `beacon.schneidercorp.com` | Beacon (Schneider Corp) |
| `elevatemaps.io` | Elevate Maps |
| `mygisonline.com` | Portico (MyGIS) |

## Background Worker

The worker processes jobs asynchronously:

1. **Polls** for pending jobs every 5 seconds
2. **Processes** jobs in FIFO order
3. **Updates** progress in real-time
4. **Handles** failures gracefully with error messages
5. **Cleans up** temporary files after completion

## Job Lifecycle

```
pending → processing → completed
                    ↘ failed
```

Jobs are automatically deleted after 3 days (configurable).

## File Storage

### Temporary Storage (Server)
- `/tmp/parcel_jobs/{job_id}/`
  - Input files (parcels, shapefiles)
  - Scraped data
  - Generated outputs

### Permanent Storage (Azure)
- `jobs/{job_id}/parcels.*` - Input parcel file
- `jobs/{job_id}/shapefiles.zip` - Input shapefile ZIP
- `jobs/{job_id}/results/parcels_enriched.xlsx` - Output Excel
- `jobs/{job_id}/results/labels.dxf` - Output DXF
- `jobs/{job_id}/results/labels.csv` - Output CSV
- `jobs/{job_id}/results/property_cards.zip` - Output PDFs

## Frontend Integration

### Example: Create Job

```javascript
const formData = new FormData();
formData.append('parcel_file', parcelFile);
formData.append('shapefile_zip', shapefileZip);
formData.append('county', 'Jennings');
formData.append('crs_id', 2965);
formData.append('gis_url', 'https://jenningsin.wthgis.com');

const response = await fetch('/jobs/create', {
  method: 'POST',
  body: formData
});

const { job_id } = await response.json();
```

### Example: Poll for Status

```javascript
const pollStatus = async (jobId) => {
  const response = await fetch(`/jobs/${jobId}`);
  const job = await response.json();
  
  if (job.status === 'completed') {
    // Show download links
    console.log('Excel:', job.results.excel_url);
    console.log('DXF:', job.results.dxf_url);
    console.log('CSV:', job.results.csv_url);
    console.log('PDFs:', job.results.pdfs_zip_url);
  } else if (job.status === 'failed') {
    console.error('Job failed:', job.error);
  } else {
    // Show progress
    console.log(`Progress: ${job.progress.percentage}%`);
    setTimeout(() => pollStatus(jobId), 2000); // Poll every 2 seconds
  }
};
```

## Project Structure

```
apps/api/
├── main.py                          # FastAPI app + worker startup
├── worker.py                        # Background job processor
├── config/
│   └── main.py                      # DB and Azure config
├── models/
│   ├── Job.py                       # Legacy job model
│   └── ParcelJob.py                 # Parcel job model
├── routes/
│   └── jobs.py                      # Job management endpoints
├── scrapers/
│   ├── base_scraper.py              # Abstract scraper class
│   ├── platform_factory.py         # Scraper factory
│   ├── wthgis_scraper.py            # WTHGIS implementation
│   ├── beacon_scraper.py            # TODO
│   ├── elevate_scraper.py           # TODO
│   └── portico_scraper.py           # TODO
├── processors/
│   └── label_exporter.py            # DXF/CSV generation
├── storage/
│   ├── az.py                        # Azure storage manager
│   └── db.py                        # MongoDB manager
└── utils/
    └── file_parser.py               # File parsing utilities
```

## Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.10"
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
pymongo = "^4.5.0"
azure-storage-blob = "^12.19.0"
pydantic = "^2.4.0"
python-multipart = "^0.0.6"
openpyxl = "^3.1.2"
pandas = "^2.1.0"
geopandas = "^0.14.0"
shapely = "^2.0.0"
pyproj = "^3.6.0"
ezdxf = "^1.1.0"
playwright = "^1.40.0"
beautifulsoup4 = "^4.12.0"
requests = "^2.31.0"
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt
python -m playwright install chromium

# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Access API documentation
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

## Next Steps

1. ✅ Simplified API structure
2. ✅ Job queue system with background worker
3. ✅ File upload handling
4. ✅ Platform auto-detection
5. ⏳ Implement WTHGIS scraper (from source code)
6. ⏳ Implement label exporter (from source code)
7. ⏳ Implement other platform scrapers
8. ⏳ Add job cleanup scheduler (3-day retention)
9. ⏳ Add authentication (Entra ID)
10. ⏳ Add rate limiting

## Notes

- Frontend bundles county/CRS JSON data (no `/data` endpoints needed)
- Platform-specific routes removed (auto-detection instead)
- Single unified job creation endpoint
- Async processing with real-time progress updates
- Automatic cleanup of old jobs and files
- All results stored in Azure for reliability
