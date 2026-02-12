# Testing Guide

## Pre-Flight Checks

### 1. Test Imports

Before starting the server, verify all dependencies are installed:

```bash
cd apps/api
python test_imports.py
```

Expected output:
```
✓ Testing FastAPI...
✓ Testing database...
✓ Testing Azure...
✓ Testing GIS libraries...
✓ Testing scraping libraries...
✓ Testing auth...
✓ Testing data processing...

✅ All imports successful!

✓ Testing config...
✓ Testing models...
✓ Testing routes...
✓ Testing scrapers...
✓ Testing utils...
✓ Testing worker...
✓ Testing scheduler...
✓ Testing auth...

✅ All application imports successful!

🚀 Ready to start the server with: npm run dev:api
```

If you see errors, install missing dependencies:
```bash
pip install -e .
python -m playwright install chromium
```

### 2. Check Environment Variables

Verify your `.env` file has the required variables:

```bash
# Check if .env exists
ls -la .env

# View (without exposing secrets)
cat .env | grep -v "CONNECTION_STRING"
```

Minimum required:
```env
MONGO_CONNECTION_STRING="mongodb://..."
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."
NAME="county_research"
```

### 3. Test Database Connection

```python
# Quick test
python -c "from config.main import DB; print('DB Connected:', DB.db.name)"
```

## Starting the Server

### Option 1: Using npm (Recommended)

From project root:
```bash
npm run dev:api
```

This runs: `cd apps/api && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000`

### Option 2: Direct uvicorn

From `apps/api` directory:
```bash
cd apps/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: Python directly

From `apps/api` directory:
```bash
cd apps/api
python main.py
```

## Verify Server is Running

### 1. Health Check

```bash
curl http://localhost:8000/health
```

Expected: `{"ok": true}`

### 2. API Root

```bash
curl http://localhost:8000/
```

Expected: JSON with API info

### 3. API Documentation

Open in browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing Without Authentication

For development, disable authentication:

```env
# In .env
REQUIRE_AUTH="false"
```

Restart the server.

## Testing API Endpoints

### 1. List Jobs (Empty)

```bash
curl http://localhost:8000/jobs
```

Expected:
```json
{
  "jobs": [],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

### 2. Create Test Job (Manual)

You'll need actual files for this. Create test files:

**test_parcels.txt:**
```
12-34-56-789-012.000-001
12-34-56-789-013.000-001
```

**test_shapefiles.zip:**
- Create a ZIP with sample shapefiles

Then:
```bash
curl -X POST "http://localhost:8000/jobs/create" \
  -F "parcel_file=@test_parcels.txt" \
  -F "shapefile_zip=@test_shapefiles.zip" \
  -F "county=Test" \
  -F "crs_id=2965" \
  -F "gis_url=https://jenningsin.wthgis.com"
```

### 3. Check Job Status

```bash
curl http://localhost:8000/jobs/{job_id}
```

Replace `{job_id}` with the ID from step 2.

## Testing with Authentication

### 1. Enable Authentication

```env
# In .env
REQUIRE_AUTH="true"
AZURE_TENANT_ID="your-tenant-id"
AZURE_CLIENT_ID="your-client-id"
```

Restart the server.

### 2. Get a Test Token

You'll need to get a token from Azure AD. Options:

**Option A: Use Postman**
1. Create new request
2. Authorization → OAuth 2.0
3. Configure with your Azure AD details
4. Get token

**Option B: Use Azure CLI**
```bash
az login
az account get-access-token --resource {CLIENT_ID}
```

**Option C: Use frontend** (once implemented)

### 3. Test with Token

```bash
curl http://localhost:8000/jobs \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Testing Worker

### 1. Check Worker Started

Look for this in server logs:
```
Background worker thread started successfully
```

### 2. Create a Job

Create a job (see above) and watch the logs. You should see:
```
Processing job {job_id} for {county} county
WTHGIS Scraper: Processing X parcels...
```

### 3. Monitor Progress

Poll the job status:
```bash
watch -n 2 'curl -s http://localhost:8000/jobs/{job_id} | jq .progress'
```

## Testing Scheduler

### 1. Check Scheduler Started

Look for this in server logs:
```
JobCleanupScheduler started (retention: 3 days)
```

### 2. Manual Cleanup Test

Create a Python script:
```python
from config.main import DB
from scheduler import JobCleanupScheduler

scheduler = JobCleanupScheduler(DB, retention_days=0)  # Delete all jobs
scheduler.cleanup_now()
```

Run:
```bash
python -c "from config.main import DB; from scheduler import JobCleanupScheduler; s = JobCleanupScheduler(DB, retention_days=0); s.cleanup_now()"
```

## Common Issues

### "ModuleNotFoundError: No module named 'X'"

```bash
pip install -e .
```

### "playwright._impl._api_types.Error: Executable doesn't exist"

```bash
python -m playwright install chromium
```

### "pymongo.errors.ServerSelectionTimeoutError"

- Check MongoDB is running
- Verify MONGO_CONNECTION_STRING in .env
- Check network connectivity

### "azure.core.exceptions.ResourceNotFoundError"

- Check AZURE_STORAGE_CONNECTION_STRING in .env
- Verify container exists
- Check Azure credentials

### "Port 8000 already in use"

```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 {PID}  # macOS/Linux
taskkill /PID {PID} /F  # Windows

# Or use different port
uvicorn main:app --reload --port 8001
```

### Worker not processing jobs

1. Check logs for errors
2. Verify MongoDB connection
3. Check job status in database:
   ```python
   from config.main import DB
   jobs = list(DB.parcelJobsCollection.find())
   print(jobs)
   ```

### "Invalid token" errors

- Verify AZURE_TENANT_ID and AZURE_CLIENT_ID match
- Check token hasn't expired
- Verify token audience matches CLIENT_ID

## Integration Testing

### Test Full Workflow

1. **Start server**
   ```bash
   npm run dev:api
   ```

2. **Create job** (with real data)
   ```bash
   curl -X POST "http://localhost:8000/jobs/create" \
     -F "parcel_file=@real_parcels.txt" \
     -F "shapefile_zip=@real_shapefiles.zip" \
     -F "county=Jennings" \
     -F "crs_id=2965" \
     -F "gis_url=https://jenningsin.wthgis.com"
   ```

3. **Monitor progress**
   ```bash
   # Get job ID from step 2
   JOB_ID="abc-123-def-456"
   
   # Watch progress
   watch -n 5 "curl -s http://localhost:8000/jobs/$JOB_ID | jq '.progress, .current_step'"
   ```

4. **Wait for completion** (may take 10-15 minutes for 100 parcels)

5. **Download results**
   ```bash
   # Get download URLs
   curl http://localhost:8000/jobs/$JOB_ID | jq '.results'
   
   # Download files
   curl "http://localhost:8000/jobs/$JOB_ID/download/excel" | jq -r '.download_url' | xargs curl -O
   curl "http://localhost:8000/jobs/$JOB_ID/download/dxf" | jq -r '.download_url' | xargs curl -O
   curl "http://localhost:8000/jobs/$JOB_ID/download/csv" | jq -r '.download_url' | xargs curl -O
   ```

6. **Verify outputs**
   - Open Excel file - check data is populated
   - Open DXF in AutoCAD/QGIS - check boundaries and labels
   - Open CSV - check coordinates

## Performance Testing

### Test with Different Parcel Counts

- 10 parcels: ~2-3 minutes
- 50 parcels: ~5-8 minutes
- 100 parcels: ~10-15 minutes
- 200 parcels: ~20-30 minutes

### Monitor Resource Usage

```bash
# CPU and Memory
top  # macOS/Linux
taskmgr  # Windows

# Disk space
df -h  # macOS/Linux
```

## Logs

### View Logs

```bash
# Server logs (stdout)
# Visible in terminal where you ran npm run dev:api

# Or redirect to file
npm run dev:api > api.log 2>&1 &
tail -f api.log
```

### Log Levels

The application logs:
- INFO: Normal operations
- WARNING: Non-critical issues
- ERROR: Failures that need attention

## Next Steps

Once basic testing passes:

1. ✅ Test with real Jennings County data
2. ✅ Verify DXF output in CAD software
3. ✅ Test with different counties
4. ✅ Test authentication flow
5. ✅ Load test with 500+ parcels
6. ✅ Test cleanup scheduler
7. ✅ Deploy to staging environment

## Automated Testing (Future)

Create `tests/` directory with:
- `test_api.py` - API endpoint tests
- `test_scraper.py` - Scraper tests
- `test_exporter.py` - Label exporter tests
- `test_auth.py` - Authentication tests

Run with:
```bash
pytest tests/
```
