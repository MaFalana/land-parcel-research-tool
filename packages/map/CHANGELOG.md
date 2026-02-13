# Changelog - @hwc/map

## [0.1.0] - 2025-02-13

### Added
- **GeoJSON Polygon Layer Support**
  - New `GeoJsonPolygonLayer` component for rendering interactive polygons
  - Prop-based API integrated into `HwcMap` for simple use cases
  - Composition API for advanced multi-layer scenarios
  - Hover, click, and selection interactions
  - Customizable styling (default, hover, selected states)
  - Tooltip support with custom content
  - Based on MapTiler polygon examples

### New Props on HwcMap
- `geoJsonData` - GeoJSON FeatureCollection to render
- `getPolygonId` - Function to extract feature ID (default: `feature.properties.name`)
- `selectedPolygonId` - Currently selected polygon ID
- `onPolygonClick` - Callback when polygon is clicked
- `onPolygonHover` - Callback when polygon is hovered
- `polygonDefaultStyle` - Default polygon style object
- `polygonHoverStyle` - Style when hovering
- `polygonSelectedStyle` - Style when selected
- `showPolygonTooltip` - Show tooltip on hover (default: true)
- `getPolygonTooltip` - Custom tooltip content function

### New Exports
- `GeoJsonPolygonLayer` - Standalone polygon layer component

### CSS Updates
- Added `.hwc-map-polygon-tooltip` styles
- Added `.leaflet-interactive` cursor pointer
- Polygon hover and selection visual feedback

### Documentation
- Updated README.md with GeoJSON polygon section
- Added POLYGON_EXAMPLE.md with usage examples
- Added CHANGELOG.md

### Use Cases
- County boundary selection (Indiana counties)
- Parcel visualization
- Zone/district mapping
- Any GeoJSON polygon data with interactions

---

## [0.0.1] - Previous

### Features
- Leaflet-based map component
- Marker clustering
- Multiple base layers (streets, satellite)
- Zoom controls
- Layer toggle
- Ortho overlays (GeoTIFF, image)
- Customizable item adapters
- Selection and hover interactions
