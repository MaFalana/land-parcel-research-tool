# User Tracking with Entra ID

## Overview

Jobs are now tied to individual users via Azure Entra ID authentication. Each user can only see and manage their own jobs.

## How It Works

### 1. Job Creation
When a user creates a job, their identity is captured from the Entra ID token:

```python
job = ParcelJob(
    id=job_id,
    user_id=user.get("user_id"),      # oid from token (unique user ID)
    user_email=user.get("email"),      # User's email
    user_name=user.get("name"),        # User's display name
    county=county,
    # ... other fields
)
```

### 2. User Isolation

**List Jobs** - Users only see their own jobs:
```python
GET /jobs
# Returns only jobs where user_id matches the authenticated user
```

**Get Job Status** - Users can only view their own jobs:
```python
GET /jobs/{job_id}
# Returns 403 Forbidden if job belongs to another user
```

**Download Results** - Users can only download their own results:
```python
GET /jobs/{job_id}/download/excel
# Returns 403 Forbidden if job belongs to another user
```

**Delete Job** - Users can only delete their own jobs:
```python
DELETE /jobs/{job_id}
# Returns 403 Forbidden if job belongs to another user
```

### 3. Database Indexes

Optimized queries with compound indexes:
- `user_id` - For filtering by user
- `user_id + created_at` - For efficient user-specific queries
- `status + created_at` - For worker job processing

## User Data Stored

From Entra ID token, we store:

| Field | Source | Description |
|-------|--------|-------------|
| `user_id` | `oid` claim | Unique user identifier (GUID) |
| `user_email` | `preferred_username` or `email` claim | User's email address |
| `user_name` | `name` claim | User's display name |

## Security

### Access Control
- ✅ Users can only create jobs for themselves
- ✅ Users can only view their own jobs
- ✅ Users can only download their own results
- ✅ Users can only delete their own jobs
- ✅ No cross-user data access

### Without Authentication
If `REQUIRE_AUTH=false` (development mode):
- Jobs are created without user info (`user_id=null`)
- All jobs are visible to everyone
- No access restrictions

## Example Flow

```
1. User logs in via Entra ID
   → Frontend gets JWT token
   
2. User creates job
   → POST /jobs/create with Bearer token
   → Backend extracts user info from token
   → Job saved with user_id, user_email, user_name
   
3. User lists jobs
   → GET /jobs with Bearer token
   → Backend filters: WHERE user_id = {authenticated_user_id}
   → Returns only user's jobs
   
4. User tries to access another user's job
   → GET /jobs/{other_user_job_id} with Bearer token
   → Backend checks: job.user_id != authenticated_user_id
   → Returns 403 Forbidden
```

## Database Schema

```javascript
{
  "_id": "uuid",
  "user_id": "oid-from-token",           // NEW: User identifier
  "user_email": "user@company.com",      // NEW: User email
  "user_name": "John Doe",               // NEW: User display name
  "county": "Jennings",
  "crs_id": 2965,
  "gis_url": "https://jenningsin.wthgis.com",
  "platform": "wthgis",
  "status": "pending",
  "parcel_count": 150,
  "created_at": "2024-01-01T00:00:00",
  // ... other fields
}
```

## Admin Access (Future)

To implement admin access that can see all jobs:

```python
# In auth/entra_id.py
def is_admin(user: dict) -> bool:
    return "Admin" in user.get("roles", [])

# In routes/jobs.py
@jobs_router.get("/")
async def list_jobs(user: dict = Depends(get_current_user)):
    query_filter = {}
    
    # Admins see all jobs, regular users see only their own
    if not is_admin(user):
        query_filter["user_id"] = user["user_id"]
    
    jobs = DB.parcelJobsCollection.find(query_filter)
    # ...
```

## Testing

### With Authentication
```bash
# Get token from Entra ID
TOKEN="your-jwt-token"

# Create job (user info captured automatically)
curl -X POST "http://localhost:8000/jobs/create" \
  -H "Authorization: Bearer $TOKEN" \
  -F "parcel_file=@parcels.txt" \
  -F "shapefile_zip=@shapefiles.zip" \
  -F "county=Jennings" \
  -F "crs_id=2965" \
  -F "gis_url=https://jenningsin.wthgis.com"

# List jobs (only your jobs returned)
curl "http://localhost:8000/jobs" \
  -H "Authorization: Bearer $TOKEN"

# Try to access another user's job (should fail)
curl "http://localhost:8000/jobs/{other_user_job_id}" \
  -H "Authorization: Bearer $TOKEN"
# Returns: 403 Forbidden
```

### Without Authentication (Development)
```bash
# Set in .env
REQUIRE_AUTH="false"

# Jobs created without user info
curl -X POST "http://localhost:8000/jobs/create" \
  -F "parcel_file=@parcels.txt" \
  # ... other fields

# All jobs visible
curl "http://localhost:8000/jobs"
```

## Migration

If you have existing jobs without user info:

```python
# Optional: Assign existing jobs to a default user
from config.main import DB

DB.parcelJobsCollection.update_many(
    {"user_id": None},
    {"$set": {
        "user_id": "default-user-id",
        "user_email": "admin@company.com",
        "user_name": "System Admin"
    }}
)
```

## Benefits

1. **Privacy** - Users can't see each other's data
2. **Security** - No unauthorized access to jobs
3. **Audit Trail** - Know who created each job
4. **Multi-tenancy** - Multiple users can use the system simultaneously
5. **Compliance** - Track data access per user

## Summary

- ✅ Jobs are tied to users via `user_id` from Entra ID
- ✅ Users can only access their own jobs
- ✅ 403 Forbidden returned for unauthorized access
- ✅ Optimized database indexes for user queries
- ✅ Works with or without authentication (configurable)
