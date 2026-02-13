import React, { useState, useCallback } from "react";
import { GeoJSON } from "react-leaflet";

/**
 * GeoJSON Polygon Layer Component
 * 
 * Renders GeoJSON polygons with hover, click, and selection support.
 * Based on MapTiler examples for polygon interactions.
 * 
 * @param {Object} data - GeoJSON FeatureCollection
 * @param {Function} getFeatureId - Extract ID from feature (default: feature.properties.name)
 * @param {string|number} selectedId - Currently selected feature ID
 * @param {Function} onPolygonClick - Callback when polygon is clicked (feature, layer)
 * @param {Function} onPolygonHover - Callback when polygon is hovered (feature, layer)
 * @param {Object} defaultStyle - Default polygon style
 * @param {Object} hoverStyle - Style when hovering
 * @param {Object} selectedStyle - Style when selected
 * @param {boolean} showTooltip - Show tooltip on hover (default: true)
 * @param {Function} getTooltipContent - Custom tooltip content (default: feature.properties.name)
 */
export function GeoJsonPolygonLayer({
  data,
  getFeatureId = (feature) => feature?.properties?.name,
  selectedId,
  onPolygonClick,
  onPolygonHover,
  defaultStyle = {
    color: "#3388ff",
    weight: 2,
    opacity: 0.8,
    fillOpacity: 0.2,
    fillColor: "#3388ff"
  },
  hoverStyle = {
    weight: 3,
    opacity: 1,
    fillOpacity: 0.4
  },
  selectedStyle = {
    color: "#ff6b35",
    weight: 3,
    opacity: 1,
    fillOpacity: 0.5,
    fillColor: "#ff6b35"
  },
  showTooltip = true,
  getTooltipContent = (feature) => feature?.properties?.name || "Unknown"
}) {
  const [hoveredId, setHoveredId] = useState(null);

  // Style function for each feature
  const styleFeature = useCallback((feature) => {
    const featureId = getFeatureId(feature);
    
    // Selected state takes priority
    if (selectedId != null && featureId === selectedId) {
      return { ...defaultStyle, ...selectedStyle };
    }
    
    // Hover state
    if (hoveredId != null && featureId === hoveredId) {
      return { ...defaultStyle, ...hoverStyle };
    }
    
    // Default state
    return defaultStyle;
  }, [selectedId, hoveredId, defaultStyle, hoverStyle, selectedStyle, getFeatureId]);

  // Attach event handlers to each feature
  const onEachFeature = useCallback((feature, layer) => {
    const featureId = getFeatureId(feature);

    // Tooltip
    if (showTooltip) {
      const tooltipContent = getTooltipContent(feature);
      if (tooltipContent) {
        layer.bindTooltip(tooltipContent, {
          permanent: false,
          direction: "top",
          className: "hwc-map-polygon-tooltip"
        });
      }
    }

    // Mouse events
    layer.on({
      mouseover: (e) => {
        setHoveredId(featureId);
        if (onPolygonHover) {
          onPolygonHover(feature, layer);
        }
      },
      mouseout: (e) => {
        setHoveredId(null);
        if (onPolygonHover) {
          onPolygonHover(null, layer);
        }
      },
      click: (e) => {
        if (onPolygonClick) {
          onPolygonClick(feature, layer);
        }
      }
    });
  }, [getFeatureId, showTooltip, getTooltipContent, onPolygonClick, onPolygonHover]);

  if (!data) return null;

  return (
    <GeoJSON
      data={data}
      style={styleFeature}
      onEachFeature={onEachFeature}
      key={`geojson-${selectedId}-${hoveredId}`} // Force re-render on selection change
    />
  );
}

export default GeoJsonPolygonLayer;
