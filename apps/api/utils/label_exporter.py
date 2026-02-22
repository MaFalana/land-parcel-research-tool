"""
Label exporter - generates DXF and CSV from scraped data and shapefiles
Based on 2. Export Labels.py
"""
import os
import json
import tempfile
import zipfile
import re
from typing import Dict
import pandas as pd
import geopandas as gpd
from pyproj import CRS
import ezdxf


# Text height for DXF labels (in drawing units/feet)
TEXT_HEIGHT = 5
BOUNDARY_LAYER = "PARCEL_BOUNDARIES_NOTES"
LABEL_LAYER = "PARCEL_LABELS"


def extract_parcel_id(idparcel: str) -> str:
    """
    Extract the formatted parcel ID from IDPARCEL by finding the pattern XX-XX-XX-
    
    The IDPARCEL has extra digits at the start, we need to extract the part that matches Excel format
    Format in Excel: 28-08-22-442-023.000-025
    Format in IDPARCEL: 1400816928-08-22-442-023.000-025 (starts with extra digits before the dash)
    """
    idparcel_str = str(idparcel).strip()
    # Find the first occurrence of pattern like "28-08-22-" (2 digits, dash, 2 digits, dash, 2 digits, dash)
    match = re.search(r'\d{2}-\d{2}-\d{2}-', idparcel_str)
    if match:
        return idparcel_str[match.start():]
    return idparcel_str


def build_label(row: pd.Series) -> str:
    """
    Build label text from parcel data
    
    Format:
    PARCEL# {id}
    {OWNER NAME}
    INST# {number} or BK. {book}, PG. {page}
    """
    parts = []
    
    # Add parcel number (no space after #)
    if "PARCELID_JOIN" in row and pd.notna(row["PARCELID_JOIN"]):
        parts.append(f"PARCEL# {row['PARCELID_JOIN']}")
    elif "Parcel ID" in row and pd.notna(row["Parcel ID"]):
        parts.append(f"PARCEL# {row['Parcel ID']}")
    
    # Add owner name (capitalized)
    owner_col = None
    for col in ["Owner Name", "Name", "owner_name"]:
        if col in row and pd.notna(row[col]):
            owner_col = col
            break
    
    if owner_col:
        parts.append(str(row[owner_col]).upper())
    
    # Add instrument number or book/page
    inst_col = None
    for col in ["Document/Instrument", "Inst. # -or- book/page", "document_id"]:
        if col in row and pd.notna(row[col]):
            inst_col = col
            break
    
    if inst_col:
        inst = str(row[inst_col]).strip()
        if inst and inst.lower() != 'nan':  # Make sure it's not empty or 'nan'
            # Check if it's in book/page format (contains /)
            if "/" in inst:
                book, page = inst.split("/", 1)
                parts.append(f"BK. {book.strip()}, PG. {page.strip()}")
            else:
                parts.append(f"INST# {inst}")
    
    return "\n".join(parts)


class LabelExporter:
    """
    Processes scraped parcel data and shapefiles to generate labels
    
    Steps:
    1. Load scraped Excel data
    2. Extract and load shapefiles from ZIP
    3. Join parcel data with shapefile geometries
    4. Reproject to target CRS
    5. Generate label text
    6. Export to DXF and CSV
    """
    
    def __init__(
        self,
        scraped_excel_path: str,
        shapefile_zip_path: str,
        crs_id: int,
        job_id: str
    ):
        """
        Initialize label exporter
        
        Args:
            scraped_excel_path: Path to enriched Excel file from scraper
            shapefile_zip_path: Path to ZIP file containing shapefiles
            crs_id: Target EPSG code for coordinate system
            job_id: Job ID for organizing output files
        """
        self.scraped_excel_path = scraped_excel_path
        self.shapefile_zip_path = shapefile_zip_path
        self.crs_id = crs_id
        self.job_id = job_id
        
        self.output_dir = os.path.join(
            tempfile.gettempdir(),
            "parcel_jobs",
            job_id,
            "output"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Extract shapefiles
        self.shapefile_dir = os.path.join(
            tempfile.gettempdir(),
            "parcel_jobs",
            job_id,
            "shapefiles"
        )
        os.makedirs(self.shapefile_dir, exist_ok=True)
    
    def export(self) -> Dict[str, str]:
        """
        Generate DXF label file
        
        Returns:
            Dict with path to generated file:
                - dxf_path: Path to DXF file
        """
        print(f"LabelExporter: Starting export for job {self.job_id}")
        
        # Extract shapefiles from ZIP
        print("Extracting shapefiles...")
        with zipfile.ZipFile(self.shapefile_zip_path, 'r') as zip_ref:
            # List contents before extraction
            print(f"ZIP contents: {zip_ref.namelist()}")
            zip_ref.extractall(self.shapefile_dir)
        
        # List extracted files
        print(f"Extracted to: {self.shapefile_dir}")
        extracted_files = []
        for root, dirs, files in os.walk(self.shapefile_dir):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), self.shapefile_dir)
                extracted_files.append(rel_path)
        print(f"Extracted files: {extracted_files}")
        
        # Find the Parcels.shp file specifically (search recursively in case files are in subdirectory)
        shp_path = None
        for root, dirs, files in os.walk(self.shapefile_dir):
            for file in files:
                # Look for Parcels.shp or Parcel.shp (case-insensitive)
                if file.lower() in ['parcels.shp', 'parcel.shp']:
                    shp_path = os.path.join(root, file)
                    break
            if shp_path:
                break
        
        if not shp_path:
            raise FileNotFoundError(
                f"No Parcels.shp or Parcel.shp file found in ZIP. "
                f"Extracted files: {extracted_files}. "
                f"Please ensure the shapefile is named 'Parcels.shp' or 'Parcel.shp'."
            )
        
        print(f"Found shapefile: {shp_path}")
        
        # Load shapefile
        print("Loading shapefile...")
        gdf = gpd.read_file(shp_path)
        print(f"Loaded {len(gdf)} parcels from shapefile")
        print(f"Shapefile columns: {gdf.columns.tolist()}")
        
        # Load scraped Excel data
        print("Loading scraped data...")
        # Try to read with header in row 1 (0-indexed) or row 2 (1-indexed)
        try:
            df = pd.read_excel(self.scraped_excel_path, header=0)
        except:
            df = pd.read_excel(self.scraped_excel_path, header=1)
        
        print(f"Loaded {len(df)} parcels from Excel")
        print(f"Excel columns: {df.columns.tolist()}")
        
        # Normalize parcel IDs for joining
        # Find the parcel ID column in shapefile
        parcel_col_shp = None
        for col in gdf.columns:
            if 'parcel' in col.lower() or 'idparcel' in col.lower():
                parcel_col_shp = col
                break
        
        if not parcel_col_shp:
            raise ValueError("Could not find parcel ID column in shapefile")
        
        print(f"Using shapefile column: {parcel_col_shp}")
        
        # Extract formatted parcel IDs from shapefile
        gdf["PARCELID_JOIN"] = gdf[parcel_col_shp].apply(extract_parcel_id)
        
        # Find parcel ID column in Excel - try both Parcel ID and Alternate ID
        parcel_col_excel = None
        for col in df.columns:
            if 'parcel' in str(col).lower() and 'id' in str(col).lower():
                parcel_col_excel = col
                break
        
        if not parcel_col_excel:
            raise ValueError("Could not find parcel ID column in Excel")
        
        print(f"Using Excel column: {parcel_col_excel}")
        
        df["PARCELID_JOIN"] = df[parcel_col_excel].astype(str).str.strip()
        
        # Debug: check sample parcel IDs
        print("\nSample Shapefile IDPARCEL (extracted):")
        print(gdf["PARCELID_JOIN"].head(10).tolist())
        print("\nSample Excel PARCELIDs:")
        print(df["PARCELID_JOIN"].head(10).tolist())
        
        # Check if any Excel PARCELIDs exist in shapefile
        excel_ids = set(df["PARCELID_JOIN"])
        shape_ids = set(gdf["PARCELID_JOIN"])
        matches = excel_ids.intersection(shape_ids)
        print(f"\nMatching PARCELIDs: {len(matches)}")
        
        # If no matches, try using Alternate ID column
        if len(matches) == 0 and "Alternate ID" in df.columns:
            print("No matches with Parcel ID, trying Alternate ID column...")
            df["PARCELID_JOIN"] = df["Alternate ID"].astype(str).str.strip()
            excel_ids = set(df["PARCELID_JOIN"])
            matches = excel_ids.intersection(shape_ids)
            print(f"Matching with Alternate ID: {len(matches)}")
        
        if len(matches) == 0:
            raise ValueError("No matching parcel IDs found between Excel and shapefile. Tried both Parcel ID and Alternate ID columns.")
        
        # Join
        print("Joining data...")
        joined = gdf.merge(df, left_on="PARCELID_JOIN", right_on="PARCELID_JOIN", how="inner")
        
        if joined.empty:
            raise ValueError("Join produced zero records. Check PARCELID fields.")
        
        print(f"Joined {len(joined)} parcels")
        
        # Store original geometry for boundaries
        joined["boundary_geom"] = joined.geometry
        
        # Compute label point (representative point of polygon)
        print("Computing label points...")
        joined["label_point"] = joined.geometry.representative_point()
        labels = gpd.GeoDataFrame(joined, geometry="label_point", crs=gdf.crs)
        
        # Reproject to target CRS
        print(f"Reprojecting to EPSG:{self.crs_id}...")
        target_crs = CRS.from_epsg(self.crs_id)
        labels = labels.to_crs(target_crs)
        
        # Also reproject the boundary geometry
        labels["boundary_geom"] = labels["boundary_geom"].to_crs(target_crs)
        
        # Get X, Y coordinates
        labels["X"] = labels.geometry.x
        labels["Y"] = labels.geometry.y
        
        # Build label text
        print("Building labels...")
        labels["LABEL"] = labels.apply(build_label, axis=1)
        
        # Debug: show some sample labels
        print("\nSample labels:")
        for i in range(min(3, len(labels))):
            print(f"\n--- Label {i+1} ---")
            print(labels.iloc[i]["LABEL"])
        
        # Export DXF
        dxf_path = os.path.join(self.output_dir, "labels.dxf")
        print("Creating DXF...")
        
        doc = ezdxf.new(units=0)  # 0 = Unitless
        msp = doc.modelspace()
        
        # Create layers
        if BOUNDARY_LAYER not in doc.layers:
            doc.layers.add(name=BOUNDARY_LAYER)
        if LABEL_LAYER not in doc.layers:
            doc.layers.add(name=LABEL_LAYER)
        
        # Add parcel boundaries
        print(f"Adding {len(labels)} parcel boundaries...")
        for idx, row in labels.iterrows():
            geom = row["boundary_geom"]
            if geom.geom_type == 'Polygon':
                # Get exterior coordinates
                coords = list(geom.exterior.coords)
                msp.add_lwpolyline(coords, dxfattribs={"layer": BOUNDARY_LAYER, "closed": True})
            elif geom.geom_type == 'MultiPolygon':
                # Handle multipolygons
                for poly in geom.geoms:
                    coords = list(poly.exterior.coords)
                    msp.add_lwpolyline(coords, dxfattribs={"layer": BOUNDARY_LAYER, "closed": True})
        
        # Add labels
        print(f"Adding {len(labels)} labels...")
        for _, row in labels.iterrows():
            msp.add_mtext(
                row["LABEL"],
                dxfattribs={
                    "layer": LABEL_LAYER,
                    "char_height": TEXT_HEIGHT,
                    "insert": (row["X"], row["Y"]),
                    "attachment_point": 5,  # 5 = middle center
                }
            )
        
        doc.saveas(dxf_path)
        print(f"Wrote DXF: {dxf_path}")
        
        print(f"\nLabelExporter: Complete!")
        print(f"  Processed: {len(labels)} parcels")
        print(f"  DXF: {dxf_path}")
        
        return {
            "dxf_path": dxf_path
        }
