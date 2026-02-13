# GeoJSON Polygon Layer - Usage Examples

## Example 1: Indiana County Map with Selection

```jsx
import { HwcMap } from "@hwc/map";
import { useState } from "react";
import countyBoundaries from "./data/County Boundaries (2023).geojson";

function CountyMap() {
  const [selectedCounty, setSelectedCounty] = useState(null);

  return (
    <div style={{ height: "600px" }}>
      <HwcMap
        items={[]} // No markers, just polygons
        initialCenter={[39.8, -86.15]} // Center of Indiana
        initialZoom={7}
        minZoom={6}
        maxZoom={12}
        fitBoundsOnLoad={false}
        
        // GeoJSON polygon props
        geoJsonData={countyBoundaries}
        selectedPolygonId={selectedCounty}
        onPolygonClick={(feature) => {
          const countyName = feature.properties.name;
          setSelectedCounty(countyName);
          console.log("Selected:", countyName);
        }}
        
        // Custom styling
        polygonDefaultStyle={{
          color: "#2563eb",
          weight: 2,
          opacity: 0.8,
          fillOpacity: 0.15,
          fillColor: "#3b82f6"
        }}
        polygonHoverStyle={{
          weight: 3,
          opacity: 1,
          fillOpacity: 0.3
        }}
        polygonSelectedStyle={{
          color: "#dc2626",
          weight: 3,
          opacity: 1,
          fillOpacity: 0.4,
          fillColor: "#ef4444"
        }}
      />
      
      {selectedCounty && (
        <div style={{ padding: "1rem" }}>
          <h3>Selected: {selectedCounty}</h3>
          <button onClick={() => setSelectedCounty(null)}>Clear</button>
        </div>
      )}
    </div>
  );
}
```

## Example 2: Synced Dropdown and Map

```jsx
import { HwcMap } from "@hwc/map";
import { useState } from "react";
import countyBoundaries from "./data/County Boundaries (2023).geojson";
import indianaCounties from "./data/Indiana.json";

function CountySelector() {
  const [selectedCounty, setSelectedCounty] = useState("");

  const handleCountyChange = (e) => {
    setSelectedCounty(e.target.value);
  };

  const handleMapClick = (feature) => {
    const countyName = feature.properties.name.replace(" County", "");
    setSelectedCounty(countyName);
  };

  return (
    <div>
      {/* Dropdown */}
      <select value={selectedCounty} onChange={handleCountyChange}>
        <option value="">Select a county...</option>
        {indianaCounties.map((county) => (
          <option key={county.county} value={county.county}>
            {county.county}
          </option>
        ))}
      </select>

      {/* Map */}
      <div style={{ height: "500px", marginTop: "1rem" }}>
        <HwcMap
          items={[]}
          initialCenter={[39.8, -86.15]}
          initialZoom={7}
          geoJsonData={countyBoundaries}
          selectedPolygonId={selectedCounty ? `${selectedCounty} County` : null}
          onPolygonClick={handleMapClick}
          getPolygonId={(feature) => feature.properties.name.replace(" County", "")}
        />
      </div>
    </div>
  );
}
```

## Example 3: Multiple Layers with Composition API

```jsx
import { HwcMap, GeoJsonPolygonLayer } from "@hwc/map";
import { useState } from "react";

function MultiLayerMap() {
  const [selectedCounty, setSelectedCounty] = useState(null);
  const [selectedParcel, setSelectedParcel] = useState(null);

  return (
    <HwcMap
      items={[]}
      initialCenter={[39.8, -86.15]}
      initialZoom={7}
    >
      {/* County boundaries layer */}
      <GeoJsonPolygonLayer
        data={countyBoundaries}
        selectedId={selectedCounty}
        onPolygonClick={(feature) => {
          setSelectedCounty(feature.properties.name);
          setSelectedParcel(null); // Clear parcel selection
        }}
        defaultStyle={{
          color: "#3b82f6",
          weight: 2,
          fillOpacity: 0.1
        }}
        selectedStyle={{
          color: "#dc2626",
          weight: 3,
          fillOpacity: 0.3
        }}
      />

      {/* Parcel boundaries layer (only show if county selected) */}
      {selectedCounty && parcelData && (
        <GeoJsonPolygonLayer
          data={parcelData}
          selectedId={selectedParcel}
          onPolygonClick={(feature) => {
            setSelectedParcel(feature.properties.parcel_id);
          }}
          getFeatureId={(feature) => feature.properties.parcel_id}
          defaultStyle={{
            color: "#10b981",
            weight: 1,
            fillOpacity: 0.2
          }}
          selectedStyle={{
            color: "#f59e0b",
            weight: 2,
            fillOpacity: 0.5
          }}
        />
      )}
    </HwcMap>
  );
}
```

## Example 4: Custom Tooltips

```jsx
<HwcMap
  items={[]}
  geoJsonData={countyBoundaries}
  getPolygonTooltip={(feature) => {
    const props = feature.properties;
    return `${props.name}\nFIPS: ${props.county_fips}\nArea: ${props.shape_Area.toFixed(2)} sq mi`;
  }}
/>
```

## Example 5: Restrict Map Bounds to Indiana

Based on MapTiler example: [Restrict map panning to an area](https://docs.maptiler.com/sdk-js/examples/restrict-bounds/)

```jsx
<HwcMap
  items={[]}
  initialCenter={[39.8, -86.15]}
  initialZoom={7}
  minZoom={6}
  maxZoom={18}
  geoJsonData={countyBoundaries}
  // Note: HwcMap already has maxBounds set globally
  // For Indiana-specific bounds, you could add a prop:
  // restrictBounds={[[37.5, -88.5], [42.0, -84.5]]}
/>
```

## Styling Reference

### Default Style (Blue)
```js
{
  color: "#3388ff",
  weight: 2,
  opacity: 0.8,
  fillOpacity: 0.2,
  fillColor: "#3388ff"
}
```

### Hover Style (Brighter)
```js
{
  weight: 3,
  opacity: 1,
  fillOpacity: 0.4
}
```

### Selected Style (Orange/Red)
```js
{
  color: "#ff6b35",
  weight: 3,
  opacity: 1,
  fillOpacity: 0.5,
  fillColor: "#ff6b35"
}
```

## Tips

1. **Performance**: For large GeoJSON files, consider simplifying geometries or using vector tiles
2. **ID Extraction**: Use `getPolygonId` to match your data structure (e.g., FIPS codes, names)
3. **Controlled Selection**: Always manage `selectedPolygonId` in parent component state
4. **Multiple Layers**: Use composition API for complex scenarios with multiple polygon layers
5. **Tooltips**: Customize with `getPolygonTooltip` for rich hover information
