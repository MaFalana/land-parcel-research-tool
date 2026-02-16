# Pre-Supplied Shapefiles

## Overview

The system now supports pre-supplied parcel shapefiles stored in Azure Blob Storage. This reduces user error and ensures consistent, up-to-date parcel data for all Indiana counties.

## Azure Storage Structure

```
Container: hwc-land-parcel-automater
Path: GIS/Indiana/Parcels/Current/{County}.zip

Example:
- GIS/Indiana/Parcels/Current/Allen.zip
- GIS/Indiana/Parcels/Current/Marion.zip
- GIS/Indiana/Parcels/Current/De Kalb.zip
```

## How It Works

### Job Creation Flow

1. User submits a job with county name and parcel IDs
2. Backend checks if shapefile exists at: `GIS/Indiana/Parcels/Current/{County}.zip`
3. If found: Downloads and uses pre-supplied shapefile
4. If not found: Requires user to upload custom shapefile

### Frontend Behavior

- Shapefile upload is hidden by default
- Shows message: "Using pre-supplied shapefiles for {County} County"
- User can click "Upload custom shapefiles" to override with their own
- Review step shows whether pre-supplied or custom shapefiles are used

## County Name Matching

County names must match exactly between:
- Frontend: `apps/web/src/data/gis/Indiana.json`
- Azure blob names: `{County}.zip`

### Special Cases

Counties with spaces or special characters:
- "De Kalb" → `De Kalb.zip` (with space)
- "La Porte" → `La Porte.zip` (with space)
- "St. Joseph" → `St. Joseph.zip` (with period and space)

## Updating Shapefiles

### Annual Update Process

1. Download new shapefiles from Indiana GIS sources
2. Verify shapefile contents (must include .shp, .shx, .dbf, .prj files)
3. Zip each county's shapefiles
4. Upload to Azure at: `GIS/Indiana/Parcels/Current/{County}.zip`
5. Test with a sample job to verify

### Shapefile Requirements

Each ZIP must contain:
- `Parcel.shp` - Main shapefile
- `Parcel.shx` - Shape index
- `Parcel.dbf` - Attribute database
- `Parcel.prj` - Projection information
- `Parcel.cfg` or `Parcel.cpg` - Character encoding (optional)

## API Changes

### POST /jobs/create

**Before:**
```
shapefile_zip: UploadFile (required)
```

**After:**
```
shapefile_zip: Optional[UploadFile] (optional)
```

If `shapefile_zip` is not provided, the backend will:
1. Check Azure for pre-supplied shapefile
2. Use it if found
3. Return error if not found and no upload provided

## Benefits

- Reduces user error (wrong files, corrupted uploads)
- Ensures data consistency across all jobs
- Faster job submission (no large file upload)
- Centralized data management
- Easy annual updates

## Fallback to Custom Upload

Users can still upload custom shapefiles when:
- County not in pre-supplied collection
- Testing with custom/modified data
- Using non-standard parcel boundaries
- Working with historical data

## Monitoring

Check Azure Blob Storage to verify all 92 Indiana counties have shapefiles:

```bash
python apps/api/test_azure_parcels.py
```

Expected output: 92 counties listed
