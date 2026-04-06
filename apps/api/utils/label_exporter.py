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


def normalize_to_state_parcel(pid: str) -> str:
    """
    Normalize any parcel ID format to state parcel number (digits only).
    
    Examples:
        "40-09-33-140-011.001-004" -> "400933140011001004"
        "29-05-10-000-010.001"     -> "290510000010001"
        "400933140011001004"       -> "400933140011001004"  (already normalized)
        "1400816928-08-22-442-023.000-025" -> extract & normalize
    """
    pid_str = str(pid).strip()
    if pid_str.lower() in ['nan', 'none', '']:
        return pid_str
    
    # If it has dashes, it's a formatted parcel ID - first extract the real part
    # Some IDs have extra prefix digits before the XX-XX-XX pattern
    match = re.search(r'\d{2}-\d{2}-\d{2}-', pid_str)
    if match:
        pid_str = pid_str[match.start():]
    
    # Strip all dashes and dots to get state parcel number
    return re.sub(r'[-.]', '', pid_str)


def build_label(row: pd.Series) -> str:
    """
    Build label text from parcel data.
    Always uses state parcel number for output.
    
    Format:
    PARCEL# {state_parcel_id}
    {OWNER NAME}
    INST# {number} or BK. {book}, PG. {page}
    """
    parts = []
    
    # Add parcel number - prefer state parcel format
    if "STATE_PARCEL_JOIN" in row and pd.notna(row["STATE_PARCEL_JOIN"]):
        parts.append(f"PARCEL# {row['STATE_PARCEL_JOIN']}")
    elif "PARCELID_JOIN" in row and pd.notna(row["PARCELID_JOIN"]):
        parts.append(f"PARCEL# {row['PARCELID_JOIN']}")
    elif "Parcel ID" in row and pd.notna(row["Parcel ID"]):
        parts.append(f"PARCEL# {normalize_to_state_parcel(str(row['Parcel ID']))}")
    
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
        if inst and inst.lower() != 'nan':
            if "/" in inst:
                book, page = inst.split("/", 1)
                parts.append(f"BK. {book.strip()}, PG. {page.strip()}")
            else:
                parts.append(f"INST# {inst}")
    
    return "\n".join(parts)


class LabelExporter:
    """
    Processes scraped parcel data and shapefiles to generate labels.
    
    Matching strategy:
    - Always joins on STATE_PARC (state parcel number, digits only)
    - Accepts any input format (formatted or numeric) and normalizes
    - Outputs always use state parcel number
    """
    
    def __init__(
        self,
        scraped_excel_path: str,
        shapefile_zip_path: str,
        crs_id: int,
        job_id: str
    ):
        self.scraped_excel_path = scraped_excel_path
        self.shapefile_zip_path = shapefile_zip_path
        self.crs_id = crs_id
        self.job_id = job_id
        
        self.output_dir = os.path.join(
            tempfile.gettempdir(), "parcel_jobs", job_id, "output"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.shapefile_dir = os.path.join(
            tempfile.gettempdir(), "parcel_jobs", job_id, "shapefiles"
        )
        os.makedirs(self.shapefile_dir, exist_ok=True)

    def _find_shapefile(self) -> str:
        """Extract ZIP and find Parcels.shp"""
        print("Extracting shapefiles...")
        with zipfile.ZipFile(self.shapefile_zip_path, 'r') as zip_ref:
            print(f"ZIP contents: {zip_ref.namelist()}")
            zip_ref.extractall(self.shapefile_dir)
        
        for root, dirs, files in os.walk(self.shapefile_dir):
            for file in files:
                if file.lower() in ['parcels.shp', 'parcel.shp']:
                    return os.path.join(root, file)
        
        extracted = []
        for root, dirs, files in os.walk(self.shapefile_dir):
            for file in files:
                extracted.append(os.path.relpath(os.path.join(root, file), self.shapefile_dir))
        raise FileNotFoundError(
            f"No Parcels.shp found in ZIP. Files: {extracted}"
        )
    
    def _find_excel_parcel_col(self, df: pd.DataFrame) -> str:
        """Find the parcel ID column in Excel data."""
        for col in df.columns:
            if 'parcel' in str(col).lower() and 'id' in str(col).lower():
                return col
        raise ValueError(f"Could not find parcel ID column in Excel. Columns: {df.columns.tolist()}")

    def export(self) -> Dict[str, str]:
        """Generate DXF label file."""
        print(f"LabelExporter: Starting export for job {self.job_id}")
        
        # Load shapefile
        shp_path = self._find_shapefile()
        print(f"Found shapefile: {shp_path}")
        gdf = gpd.read_file(shp_path)
        print(f"Loaded {len(gdf)} parcels from shapefile")
        print(f"Shapefile columns: {gdf.columns.tolist()}")
        
        # Load Excel
        print("Loading scraped data...")
        try:
            df = pd.read_excel(self.scraped_excel_path, header=0)
        except Exception:
            df = pd.read_excel(self.scraped_excel_path, header=1)
        print(f"Loaded {len(df)} parcels from Excel")
        print(f"Excel columns: {df.columns.tolist()}")
        
        # Debug: column analysis
        print(f"\n=== SHAPEFILE COLUMN ANALYSIS ===")
        for col in gdf.columns:
            if col == 'geometry':
                continue
            non_null = gdf[col].notna().sum()
            if non_null > 0:
                samples = gdf[col].head(3).tolist()
                print(f"  {col}: {non_null}/{len(gdf)} non-null, samples: {samples}")
        print(f"=== END ===\n")
        
        # --- BUILD JOIN KEY: always normalize to state parcel number ---
        
        # Shapefile side: prefer STATE_PARC, fall back to normalizing PARCEL_ID
        if 'STATE_PARC' in gdf.columns and gdf['STATE_PARC'].notna().sum() > 0:
            print("Using STATE_PARC from shapefile (primary)")
            gdf["STATE_PARCEL_JOIN"] = gdf['STATE_PARC'].astype(str).str.strip()
        elif 'PARCEL_ID' in gdf.columns and gdf['PARCEL_ID'].notna().sum() > 0:
            print("STATE_PARC not available, normalizing PARCEL_ID to state parcel format")
            gdf["STATE_PARCEL_JOIN"] = gdf['PARCEL_ID'].apply(normalize_to_state_parcel)
        elif 'IDPARCEL' in gdf.columns and gdf['IDPARCEL'].notna().sum() > 0:
            print("Using IDPARCEL, normalizing to state parcel format")
            gdf["STATE_PARCEL_JOIN"] = gdf['IDPARCEL'].apply(normalize_to_state_parcel)
        else:
            raise ValueError("Could not find STATE_PARC, PARCEL_ID, or IDPARCEL in shapefile")
        
        print(f"Sample shapefile join keys: {gdf['STATE_PARCEL_JOIN'].dropna().head(5).tolist()}")
        
        # Excel side: find parcel ID column and normalize to state parcel number
        parcel_col_excel = self._find_excel_parcel_col(df)
        print(f"Using Excel column: {parcel_col_excel}")
        df["STATE_PARCEL_JOIN"] = df[parcel_col_excel].apply(normalize_to_state_parcel)
        print(f"Sample Excel join keys: {df['STATE_PARCEL_JOIN'].head(5).tolist()}")
        
        # --- MATCH ---
        excel_ids = set(df["STATE_PARCEL_JOIN"])
        shape_ids = set(gdf["STATE_PARCEL_JOIN"])
        matches = excel_ids.intersection(shape_ids)
        print(f"\nExact match: {len(matches)}/{len(excel_ids)} parcels")
        
        # If no exact matches, try prefix matching.
        # Users may input local IDs without the township suffix, e.g.:
        #   Input:    "290510000010001"     (15 digits)
        #   Shapefile: "290510000010001013"  (18 digits, with township)
        # In this case the input is a prefix of the state parcel number.
        if len(matches) == 0:
            print("No exact matches. Trying prefix match (input may lack township suffix)...")
            
            # Build a prefix lookup: for each shapefile ID, index all prefixes
            # that could match a shorter input ID
            prefix_map = {}  # excel_id -> shapefile_state_parcel
            for eid in excel_ids:
                for sid in shape_ids:
                    if sid.startswith(eid):
                        prefix_map[eid] = sid
                        break
            
            if prefix_map:
                print(f"Prefix match: {len(prefix_map)}/{len(excel_ids)} parcels")
                # Update Excel join keys to the full state parcel number
                df["STATE_PARCEL_JOIN"] = df["STATE_PARCEL_JOIN"].map(
                    lambda x: prefix_map.get(x, x)
                )
                matches = set(df["STATE_PARCEL_JOIN"]).intersection(shape_ids)
                print(f"After prefix resolution: {len(matches)} matches")
        
        if len(matches) == 0:
            # Diagnostic dump
            print("\n=== MATCH FAILURE DIAGNOSTICS ===")
            print(f"Excel IDs (first 5): {list(excel_ids)[:5]}")
            print(f"Shapefile IDs (first 5): {list(shape_ids)[:5]}")
            for col in gdf.columns:
                if col not in ('geometry', 'STATE_PARCEL_JOIN'):
                    samples = gdf[col].dropna().head(3).tolist()
                    if samples:
                        print(f"  {col}: {samples}")
            print("=== END DIAGNOSTICS ===")
            raise ValueError(
                "No matching parcel IDs found. Both Excel and shapefile IDs were "
                "normalized to state parcel format (digits only) but no overlap was found."
            )
        
        # --- JOIN ---
        print("Joining data...")
        joined = gdf.merge(df, on="STATE_PARCEL_JOIN", how="inner")
        
        if joined.empty:
            raise ValueError("Join produced zero records.")
        
        print(f"Joined {len(joined)} parcels")
        
        # Store original geometry for boundaries
        joined["boundary_geom"] = joined.geometry
        
        # Compute label points
        print("Computing label points...")
        joined["label_point"] = joined.geometry.representative_point()
        labels = gpd.GeoDataFrame(joined, geometry="label_point", crs=gdf.crs)
        
        # Reproject
        print(f"Reprojecting to EPSG:{self.crs_id}...")
        target_crs = CRS.from_epsg(self.crs_id)
        labels = labels.to_crs(target_crs)
        labels["boundary_geom"] = labels["boundary_geom"].to_crs(target_crs)
        
        labels["X"] = labels.geometry.x
        labels["Y"] = labels.geometry.y
        
        # Build labels (uses state parcel number)
        print("Building labels...")
        labels["LABEL"] = labels.apply(build_label, axis=1)
        
        # Debug: sample labels
        print("\nSample labels:")
        for i in range(min(3, len(labels))):
            print(f"\n--- Label {i+1} ---")
            print(labels.iloc[i]["LABEL"])
        
        # --- EXPORT DXF ---
        dxf_path = os.path.join(self.output_dir, "labels.dxf")
        print("Creating DXF...")
        
        doc = ezdxf.new(units=0)
        msp = doc.modelspace()
        
        if BOUNDARY_LAYER not in doc.layers:
            doc.layers.add(name=BOUNDARY_LAYER)
        if LABEL_LAYER not in doc.layers:
            doc.layers.add(name=LABEL_LAYER)
        
        # Add parcel boundaries
        print(f"Adding {len(labels)} parcel boundaries...")
        for idx, row in labels.iterrows():
            geom = row["boundary_geom"]
            if geom.geom_type == 'Polygon':
                coords = list(geom.exterior.coords)
                msp.add_lwpolyline(coords, dxfattribs={"layer": BOUNDARY_LAYER, "closed": True})
            elif geom.geom_type == 'MultiPolygon':
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
                    "attachment_point": 5,  # middle center
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
