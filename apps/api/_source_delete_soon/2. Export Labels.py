import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from pyproj import CRS
import ezdxf

# -------------------------
# USER CONFIG
# -------------------------
PARCEL_SHP = "Greene County Land Parcels IDHS.shp"          # path to your parcel shapefile
SCRAPER_CSV = "scraped.xlsx"         # path to your scraper csv
CRS_JSON = "Indiana.json"          # your CRS json file
TARGET_CRS_ID = 7284                # _id from your CRS json (example)

OUTPUT_CSV = "labels.csv"
OUTPUT_DXF = "labels.dxf"

TEXT_HEIGHT = 5                     # drawing units (feet)
LAYER_NAME = "PARCEL_LABELS"
#LAYER_NAME = "S_PROP_Property owner"

# -------------------------
# LOAD CRS JSON
# -------------------------
with open(CRS_JSON, "r") as f:
    crs_list = json.load(f)

target_crs_entry = next(c for c in crs_list if c["_id"] == TARGET_CRS_ID)
target_crs = CRS.from_proj4(target_crs_entry["proj4"])

print(f"Using CRS: {target_crs_entry['name']}")

# -------------------------
# LOAD DATA
# -------------------------
gdf = gpd.read_file(PARCEL_SHP)
df = pd.read_excel(SCRAPER_CSV, header=1)  # Skip first row, use second row as header

# Debug: print columns
print("Shapefile columns:", gdf.columns.tolist())
print("Excel columns:", df.columns.tolist())
print("\nFirst few rows of Excel:")
print(df.head())

# normalize parcel id - extract the formatted ID from IDPARCEL
# The IDPARCEL has extra digits at the start, we need to extract the part that matches Excel format
# Format in Excel: 28-08-22-442-023.000-025
# Format in IDPARCEL: 1400816928-08-22-442-023.000-025 (starts with extra digits before the dash)

def extract_parcel_id(idparcel):
    """Extract the formatted parcel ID from IDPARCEL by finding the pattern XX-XX-XX-"""
    idparcel_str = str(idparcel).strip()
    # Find the first occurrence of pattern like "28-08-22-" (2 digits, dash, 2 digits, dash, 2 digits, dash)
    import re
    match = re.search(r'\d{2}-\d{2}-\d{2}-', idparcel_str)
    if match:
        return idparcel_str[match.start():]
    return idparcel_str

gdf["PARCELID_JOIN"] = gdf["IDPARCEL"].apply(extract_parcel_id)
df["PARCELID_JOIN"] = df["PARCELID"].astype(str).str.strip()

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

# -------------------------
# JOIN
# -------------------------
joined = gdf.merge(df, left_on="PARCELID_JOIN", right_on="PARCELID_JOIN", how="inner")

if joined.empty:
    raise Exception("Join produced zero records. Check PARCELID fields.")

# -------------------------
# COMPUTE LABEL POINT
# -------------------------
# Store original geometry for boundaries
joined["boundary_geom"] = joined.geometry

joined["label_point"] = joined.geometry.representative_point()
labels = gpd.GeoDataFrame(joined, geometry="label_point", crs=gdf.crs)

# -------------------------
# REPROJECT
# -------------------------
labels = labels.to_crs(target_crs)

# Also reproject the boundary geometry
labels["boundary_geom"] = labels["boundary_geom"].to_crs(target_crs)

labels["X"] = labels.geometry.x
labels["Y"] = labels.geometry.y

# -------------------------
# BUILD LABEL TEXT
# -------------------------
def build_label(row):
    parts = []
    
    # Add parcel number (no space after #)
    parts.append(f"PARCEL# {row['PARCELID_JOIN']}")
    
    # Add owner name (capitalized)
    if "Name" in row and pd.notna(row["Name"]):
        parts.append(str(row["Name"]).upper())
    
    # Add instrument number or book/page
    if "Inst. # -or- book/page" in row and pd.notna(row["Inst. # -or- book/page"]):
        inst = str(row["Inst. # -or- book/page"]).strip()
        if inst and inst.lower() != 'nan':  # Make sure it's not empty or 'nan'
            # Check if it's in book/page format (contains /)
            if "/" in inst:
                book, page = inst.split("/", 1)
                parts.append(f"BK. {book.strip()}, PG. {page.strip()}")
            else:
                parts.append(f"INST# {inst}")
    
    return "\n".join(parts)

labels["LABEL"] = labels.apply(build_label, axis=1)

# Debug: show some sample labels
print("\nSample labels:")
for i in range(min(5, len(labels))):
    print(f"\n--- Label {i+1} ---")
    print(labels.iloc[i]["LABEL"])
    print(f"Inst value: {labels.iloc[i]['Inst. # -or- book/page']}")

# -------------------------
# EXPORT CSV
# -------------------------
labels[["PARCELID_JOIN", "X", "Y", "LABEL"]].to_csv(OUTPUT_CSV, index=False)
print(f"Wrote {OUTPUT_CSV}")

# -------------------------
# EXPORT DXF
# -------------------------
doc = ezdxf.new(units=0)  # 0 = Unitless
msp = doc.modelspace()

if LAYER_NAME not in doc.layers:
    doc.layers.add(name=LAYER_NAME)

# Add parcel boundaries layer
BOUNDARY_LAYER = "PARCEL_BOUNDARIES_NOTES"
if BOUNDARY_LAYER not in doc.layers:
    doc.layers.add(name=BOUNDARY_LAYER)

# Add parcel boundaries
print(f"Adding {len(labels)} parcel boundaries...")
for idx, row in labels.iterrows():
    geom = row["boundary_geom"]
    print(f"Processing parcel {idx}: geometry type = {geom.geom_type}")
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
for _, row in labels.iterrows():
    msp.add_mtext(
        row["LABEL"],
        dxfattribs={
            "layer": LAYER_NAME,
            "char_height": TEXT_HEIGHT,
            "insert": (row["X"], row["Y"]),
            "attachment_point": 5,  # 5 = middle center
        }
    )

doc.saveas(OUTPUT_DXF)
print(f"Wrote {OUTPUT_DXF}")
