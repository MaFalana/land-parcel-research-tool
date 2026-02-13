# Frontend Integration Guide

Complete guide for integrating the County Research Automation API with your frontend.

## API Base URL

**Development:** `http://localhost:8000`
**Production:** `https://your-api-domain.com`

---

## Authentication

### Current Setup (Development)
```
REQUIRE_AUTH="false"
```
- No authentication required
- All endpoints accessible without tokens
- User tracking disabled (user_id = null)

### Production Setup
```
REQUIRE_AUTH="true"
```
- Requires Microsoft Entra ID authentication
- Include Bearer token in all requests:
  ```javascript
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
  ```

---

## API Endpoints

### 1. Create Job
**POST** `/jobs/create`

Creates a new parcel research job.

**Request:**
```javascript
const formData = new FormData();
formData.append('parcel_file', parcelFile);  // File: .txt, .csv, or .xlsx
formData.append('shapefile_zip', shapefileZip);  // File: .zip
formData.append('county', 'Greene');
formData.append('crs_id', 2965);  // EPSG code
formData.append('gis_url', 'https://greenein.wthgis.com/');

const response = await fetch('http://localhost:8000/jobs/create', {
  method: 'POST',
  body: formData
});
```

**Response:**
```json
{
  "job_id": "43d609f4-7ec2-4308-a8b6-8100fa4f0462",
  "status": "pending",
  "message": "Job created for 25 parcels in Greene county",
  "platform": "wthgis",
  "parcel_count": 25,
  "created_at": "2024-01-15T10:00:00Z"
}
```

**Validation:**
- Max file size: 5 GB per file
- Parcel file types: .txt, .csv, .xlsx
- Shapefile must be .zip
- Max 1000 parcels per job

---

### 2. Get Job Status
**GET** `/jobs/{job_id}`

Get current status and progress of a job.

**Request:**
```javascript
const response = await fetch(`http://localhost:8000/jobs/${jobId}`);
const data = await response.json();
```

**Response:**
```json
{
  "job_id": "43d609f4-7ec2-4308-a8b6-8100fa4f0462",
  "status": "processing",
  "county": "Greene",
  "platform": "wthgis",
  "current_step": "Scraping 25 parcels from wthgis",
  "progress": {
    "total": 25,
    "completed": 10,
    "failed": 0,
    "percentage": 40.0
  },
  "timing": {
    "created_at": "2024-01-15T10:00:00Z",
    "started_at": "2024-01-15T10:00:05Z",
    "updated_at": "2024-01-15T10:02:30Z",
    "completed_at": null,
    "elapsed_seconds": 145,
    "estimated_remaining_seconds": 218
  }
}
```

**Status Values:**
- `pending` - Job queued, waiting to start
- `processing` - Currently running
- `completed` - Finished successfully
- `failed` - Error occurred
- `cancelled` - User cancelled

**Progress Indicator Example:**
```javascript
// Show time remaining
if (data.timing.estimated_remaining_seconds) {
  const minutes = Math.ceil(data.timing.estimated_remaining_seconds / 60);
  console.log(`~${minutes} minutes remaining`);
}

// Show progress bar
const percentage = data.progress.percentage;
```

---

### 3. List Jobs
**GET** `/jobs?status={status}&limit={limit}&offset={offset}`

List jobs with optional filtering and pagination.

**Query Parameters:**
- `status` (optional): Filter by status (pending, processing, completed, failed, cancelled)
- `limit` (optional): Max results (default: 50)
- `offset` (optional): Skip results (default: 0)

**Request:**
```javascript
// Get all completed jobs
const response = await fetch('http://localhost:8000/jobs?status=completed');

// Get processing jobs
const response = await fetch('http://localhost:8000/jobs?status=processing');

// Pagination
const response = await fetch('http://localhost:8000/jobs?limit=10&offset=20');
```

**Response:**
```json
{
  "jobs": [
    {
      "_id": "43d609f4-7ec2-4308-a8b6-8100fa4f0462",
      "status": "completed",
      "county": "Greene",
      "platform": "wthgis",
      "parcel_count": 25,
      "created_at": "2024-01-15T10:00:00Z",
      "completed_at": "2024-01-15T10:15:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0,
  "filters": {
    "status": "completed"
  }
}
```

---

### 4. Download Results
**GET** `/jobs/{job_id}/download/{file_type}`

Get download URL for result files.

**File Types:**
- `excel` - Enriched parcel data (.xlsx)
- `dxf` - CAD labels with boundaries (.dxf)
- `prc` - Property Record Cards (.zip containing PRC folder)

**Request:**
```javascript
// Get Excel download URL
const response = await fetch(`http://localhost:8000/jobs/${jobId}/download/excel`);
const data = await response.json();

// Download the file
window.location.href = data.download_url;
```

**Response:**
```json
{
  "job_id": "43d609f4-7ec2-4308-a8b6-8100fa4f0462",
  "file_type": "excel",
  "download_url": "https://hwctopodot.blob.core.windows.net/hwc-land-parcel-automater/jobs/43d609f4-7ec2-4308-a8b6-8100fa4f0462/parcels_enriched.xlsx"
}
```

**Download All Results:**
```javascript
const fileTypes = ['excel', 'dxf', 'prc'];

for (const type of fileTypes) {
  const response = await fetch(`http://localhost:8000/jobs/${jobId}/download/${type}`);
  const data = await response.json();
  
  // Create download link
  const a = document.createElement('a');
  a.href = data.download_url;
  a.download = '';
  a.click();
}
```

---

### 5. Cancel Job
**POST** `/jobs/{job_id}/cancel`

Cancel a pending or processing job.

**Request:**
```javascript
const response = await fetch(`http://localhost:8000/jobs/${jobId}/cancel`, {
  method: 'POST'
});
```

**Response:**
```json
{
  "job_id": "43d609f4-7ec2-4308-a8b6-8100fa4f0462",
  "status": "cancelled",
  "message": "Job cancelled successfully"
}
```

---

### 6. Delete Job
**DELETE** `/jobs/{job_id}`

Delete a job and all its files.

**Request:**
```javascript
const response = await fetch(`http://localhost:8000/jobs/${jobId}`, {
  method: 'DELETE'
});
```

**Response:**
```json
{
  "message": "Job 43d609f4-7ec2-4308-a8b6-8100fa4f0462 deleted successfully"
}
```

---

### 7. Health Check
**GET** `/jobs/health`

Check API health and database connectivity.

**Request:**
```javascript
const response = await fetch('http://localhost:8000/jobs/health');
```

**Response:**
```json
{
  "status": "healthy",
  "database": "healthy",
  "version": "2.0.0"
}
```

---

## Frontend Implementation Examples

### React/TypeScript Example

```typescript
// types.ts
export interface Job {
  _id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  county: string;
  platform: string;
  parcel_count: number;
  progress: {
    total: number;
    completed: number;
    failed: number;
    percentage: number;
  };
  timing: {
    created_at: string;
    started_at?: string;
    elapsed_seconds?: number;
    estimated_remaining_seconds?: number;
  };
  results?: {
    excel_url: string;
    dxf_url: string;
    prc_zip_url: string;
  };
}

// api.ts
const API_BASE = 'http://localhost:8000';

export async function createJob(
  parcelFile: File,
  shapefileZip: File,
  county: string,
  crsId: number,
  gisUrl: string
): Promise<{ job_id: string }> {
  const formData = new FormData();
  formData.append('parcel_file', parcelFile);
  formData.append('shapefile_zip', shapefileZip);
  formData.append('county', county);
  formData.append('crs_id', crsId.toString());
  formData.append('gis_url', gisUrl);

  const response = await fetch(`${API_BASE}/jobs/create`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Failed to create job');
  }

  return response.json();
}

export async function getJobStatus(jobId: string): Promise<Job> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch job status');
  }

  return response.json();
}

export async function listJobs(status?: string): Promise<{ jobs: Job[] }> {
  const url = status 
    ? `${API_BASE}/jobs?status=${status}`
    : `${API_BASE}/jobs`;
    
  const response = await fetch(url);
  return response.json();
}

export async function cancelJob(jobId: string): Promise<void> {
  await fetch(`${API_BASE}/jobs/${jobId}/cancel`, {
    method: 'POST',
  });
}

export async function deleteJob(jobId: string): Promise<void> {
  await fetch(`${API_BASE}/jobs/${jobId}`, {
    method: 'DELETE',
  });
}

// JobProgress.tsx
import { useEffect, useState } from 'react';
import { getJobStatus, Job } from './api';

export function JobProgress({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<Job | null>(null);

  useEffect(() => {
    const interval = setInterval(async () => {
      const data = await getJobStatus(jobId);
      setJob(data);

      // Stop polling if job is done
      if (['completed', 'failed', 'cancelled'].includes(data.status)) {
        clearInterval(interval);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [jobId]);

  if (!job) return <div>Loading...</div>;

  const timeRemaining = job.timing.estimated_remaining_seconds
    ? Math.ceil(job.timing.estimated_remaining_seconds / 60)
    : null;

  return (
    <div>
      <h3>{job.county} County - {job.status}</h3>
      <progress value={job.progress.percentage} max={100} />
      <p>{job.progress.percentage.toFixed(1)}% complete</p>
      <p>{job.progress.completed} / {job.progress.total} parcels</p>
      {timeRemaining && <p>~{timeRemaining} minutes remaining</p>}
      <p>{job.current_step}</p>
    </div>
  );
}
```

---

## Polling Strategy

For real-time updates, poll the status endpoint:

```javascript
async function pollJobStatus(jobId, onUpdate) {
  const poll = async () => {
    const response = await fetch(`http://localhost:8000/jobs/${jobId}`);
    const data = await response.json();
    
    onUpdate(data);
    
    // Stop polling if job is done
    if (['completed', 'failed', 'cancelled'].includes(data.status)) {
      clearInterval(intervalId);
    }
  };
  
  // Poll every 2 seconds
  const intervalId = setInterval(poll, 2000);
  
  // Initial poll
  poll();
  
  return () => clearInterval(intervalId);
}

// Usage
const stopPolling = pollJobStatus('job-id-here', (job) => {
  console.log('Progress:', job.progress.percentage);
});
```

---

## Error Handling

```javascript
async function createJobWithErrorHandling(formData) {
  try {
    const response = await fetch('http://localhost:8000/jobs/create', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const error = await response.json();
      
      if (response.status === 413) {
        throw new Error('File too large (max 5 GB)');
      } else if (response.status === 400) {
        throw new Error(error.detail || 'Invalid request');
      } else {
        throw new Error('Failed to create job');
      }
    }
    
    return await response.json();
    
  } catch (error) {
    console.error('Error creating job:', error);
    throw error;
  }
}
```

---

## CORS Configuration

The API allows all origins by default. For production, update:

```env
CORS_ORIGINS="https://your-frontend-domain.com,https://www.your-frontend-domain.com"
```

---

## Job Lifecycle

```
1. User uploads files → POST /jobs/create
2. Job created with status="pending"
3. Worker picks up job → status="processing"
4. Poll GET /jobs/{job_id} every 2 seconds for updates
5. Job completes → status="completed"
6. Download results → GET /jobs/{job_id}/download/{type}
7. Auto-cleanup after 3 days
```

---

## Best Practices

1. **Polling:** Poll every 2-3 seconds during processing
2. **Stop Polling:** Stop when status is completed/failed/cancelled
3. **File Validation:** Validate files client-side before upload
4. **Error Messages:** Show user-friendly error messages
5. **Progress UI:** Show percentage, time remaining, and current step
6. **Download UX:** Provide clear download buttons for each file type
7. **Cleanup:** Remind users files expire in 3 days

---

## Testing

Use the interactive API docs for testing:
```
http://localhost:8000/docs
```

All endpoints are documented with examples and can be tested directly in the browser.
