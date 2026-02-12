# Test Commands

## Quick Test with Greene County

```bash
curl -X 'POST' \
  'http://localhost:8000/jobs/create' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'parcel_file=@Greene Example.txt;type=text/plain' \
  -F 'shapefile_zip=@Greene County Land Parcels.zip;type=application/x-zip-compressed' \
  -F 'county=Greene' \
  -F 'crs_id=7284' \
  -F 'gis_url=https://greenein.wthgis.com/'
```

Response:
```json
{
  "job_id": "uuid-here",
  "status": "pending",
  "message": "Job created for X parcels in Greene county",
  "platform": "wthgis",
  "parcel_count": X,
  "created_at": "2024-01-01T00:00:00"
}
```

## Check Job Status

```bash
# Replace {job_id} with the ID from create response
curl http://localhost:8000/jobs/{job_id}
```

## Monitor Progress (Watch)

```bash
# Windows PowerShell
while ($true) { 
  curl http://localhost:8000/jobs/{job_id} | ConvertFrom-Json | Select-Object status, current_step, progress
  Start-Sleep -Seconds 5
}

# Linux/Mac
watch -n 5 'curl -s http://localhost:8000/jobs/{job_id} | jq ".status, .current_step, .progress"'
```

## Download Results

Once status is "completed":

```bash
# Get download URLs
curl http://localhost:8000/jobs/{job_id} | jq '.results'

# Download Excel
curl http://localhost:8000/jobs/{job_id}/download/excel

# Download DXF
curl http://localhost:8000/jobs/{job_id}/download/dxf

# Download CSV
curl http://localhost:8000/jobs/{job_id}/download/csv

# Download PDFs (ZIP)
curl http://localhost:8000/jobs/{job_id}/download/pdfs
```

## List All Jobs

```bash
curl http://localhost:8000/jobs
```

## Delete Job

```bash
curl -X DELETE http://localhost:8000/jobs/{job_id}
```

## Other Counties

### Jennings County
```bash
curl -X 'POST' \
  'http://localhost:8000/jobs/create' \
  -H 'Content-Type: multipart/form-data' \
  -F 'parcel_file=@parcels.txt' \
  -F 'shapefile_zip=@shapefiles.zip' \
  -F 'county=Jennings' \
  -F 'crs_id=2965' \
  -F 'gis_url=https://jenningsin.wthgis.com/'
```

### Monroe County
```bash
curl -X 'POST' \
  'http://localhost:8000/jobs/create' \
  -H 'Content-Type: multipart/form-data' \
  -F 'parcel_file=@parcels.txt' \
  -F 'shapefile_zip=@shapefiles.zip' \
  -F 'county=Monroe' \
  -F 'crs_id=7338' \
  -F 'gis_url=https://monroein.elevatemaps.io/'
```

### Brown County
```bash
curl -X 'POST' \
  'http://localhost:8000/jobs/create' \
  -H 'Content-Type: multipart/form-data' \
  -F 'parcel_file=@parcels.txt' \
  -F 'shapefile_zip=@shapefiles.zip' \
  -F 'county=Brown' \
  -F 'crs_id=7270' \
  -F 'gis_url=http://brown.in.wthgis.com/'
```

## Common CRS IDs (Indiana)

| CRS ID | Name | Counties |
|--------|------|----------|
| 2965 | NAD83 / Indiana East (ftUS) | Eastern counties |
| 2966 | NAD83 / Indiana West (ftUS) | Western counties |
| 7284 | NAD83(2011) / InGCS Daviess-Greene (ftUS) | Daviess, Greene |
| 7338 | NAD83(2011) / InGCS Monroe-Morgan (ftUS) | Monroe, Morgan |
| 7270 | NAD83(2011) / InGCS Brown (ftUS) | Brown |

See `apps/web/src/data/epsg/Indiana.json` for full list.

## Troubleshooting

### Job Status "failed"
```bash
# Check error message
curl http://localhost:8000/jobs/{job_id} | jq '.error'
```

### No parcels found
- Verify parcel IDs match the format expected by the county
- Check GIS URL is correct and accessible
- Try searching manually on the GIS portal

### Shapefile issues
- Ensure ZIP contains .shp, .shx, .dbf files
- Verify parcel ID column exists in shapefile
- Check shapefile projection matches county

### Worker not processing
- Check server logs for errors
- Verify MongoDB and Azure connections
- Restart server: `npm run dev:api`

## Expected Processing Times

- 10 parcels: ~2-3 minutes
- 50 parcels: ~5-8 minutes
- 100 parcels: ~10-15 minutes
- 200 parcels: ~20-30 minutes

Times include:
- Browser lookup (batch)
- Data scraping with polite delays
- PDF downloads
- Shapefile processing
- DXF/CSV generation
- Azure uploads
