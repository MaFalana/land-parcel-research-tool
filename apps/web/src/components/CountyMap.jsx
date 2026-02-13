import React, { useState, useEffect } from "react";
import { CountySelect } from "./CountySelect";
import "./county-map.css";

/**
 * CountyMap Component
 * 
 * Indiana-specific map component with county selection.
 * Syncs between dropdown and map polygon selection.
 */
export function CountyMap({ mapTilerKey, basePath, onCountySelect = null }) {
  const [selectedCounty, setSelectedCounty] = useState("");
  const [isClient, setIsClient] = useState(false);
  const [countyBoundaries, setCountyBoundaries] = useState(null);
  const [indianaCounties, setIndianaCounties] = useState(null);
  const [HwcMap, setHwcMap] = useState(null);
  
  // Load components and data only on client
  useEffect(() => {
    setIsClient(true);
    
    // Dynamic imports to avoid SSR issues
    Promise.all([
      import("@hwc/map").then(m => { 
        setHwcMap(() => m.HwcMap);
        return m;
      }),
      // Fetch GeoJSON (it's imported as a URL in dev mode)
      import("../data/gis/County Boundaries (2023).geojson").then(async (m) => {
        // If it's a URL, fetch it
        if (typeof m.default === 'string') {
          const response = await fetch(m.default);
          const data = await response.json();
          setCountyBoundaries(data);
        } else {
          // If it's already the data
          setCountyBoundaries(m.default);
        }
        return m;
      }),
      import("../data/gis/Indiana.json").then(m => {
        setIndianaCounties(m.default);
        return m;
      })
    ]).catch(err => {
      console.error("CountyMap: Failed to load modules", err);
    });
  }, []);
  
  // Show loading state until client-side
  if (!isClient || !HwcMap || !countyBoundaries || !indianaCounties) {
    return (
      <div className="county-map-container" style={{ padding: "2rem", textAlign: "center" }}>
        <p>Loading map...</p>
      </div>
    );
  }

  // Handle county selection from dropdown
  const handleDropdownChange = (countyName, countyData) => {
    setSelectedCounty(countyName);
    if (onCountySelect) {
      onCountySelect(countyName, countyData);
    }
  };

  // Handle county selection from map click
  const handleMapClick = (feature) => {
    // Extract county name from GeoJSON (e.g., "Allen County" -> "Allen")
    const fullName = feature.properties.name;
    const countyName = fullName.replace(" County", "");
    
    // Toggle selection - if clicking the same county, deselect it
    if (countyName === selectedCounty) {
      setSelectedCounty("");
      if (onCountySelect) {
        onCountySelect("", null);
      }
    } else {
      // Find matching county data
      const countyData = indianaCounties.find(c => c.county === countyName);
      
      setSelectedCounty(countyName);
      if (onCountySelect) {
        onCountySelect(countyName, countyData);
      }
    }
  };

  // Convert county name to full name for polygon selection
  const selectedPolygonId = selectedCounty ? `${selectedCounty} County` : null;

  return (
    <div className="county-map-container">
      {/* County Selector Panel */}
      <div className="county-map-panel">
        <div className="county-map-panel-content">
          <h2 className="county-map-title">Select County</h2>
          
          <CountySelect
            value={selectedCounty}
            onChange={handleDropdownChange}
            counties={indianaCounties}
            label="Indiana County"
            required
          />

          {selectedCounty && (
            <div className="county-map-info">
              <h3>{selectedCounty} County</h3>
              {indianaCounties.find(c => c.county === selectedCounty)?.url && (
                <p className="county-map-url">
                  <strong>GIS Portal:</strong>
                  <br />
                  <a 
                    href={indianaCounties.find(c => c.county === selectedCounty).url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View Portal
                  </a>
                </p>
              )}
              <button 
                className="county-map-clear-btn"
                onClick={() => {
                  setSelectedCounty("");
                  if (onCountySelect) {
                    onCountySelect("", null);
                  }
                }}
              >
                Clear Selection
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Map */}
      <div className="county-map-wrapper">
        <HwcMap
          items={[]}
          initialCenter={[39.8, -86.15]}
          initialZoom={7}
          minZoom={6}
          maxZoom={18}
          fitBoundsOnLoad={false}
          baseLayer="streets"
          showControls={false}
          basePath={basePath}
          
          // GeoJSON polygon configuration
          geoJsonData={countyBoundaries}
          selectedPolygonId={selectedPolygonId}
          onPolygonClick={handleMapClick}
          
          // Custom ID extraction (match dropdown format)
          getPolygonId={(feature) => feature.properties.name}
          
          // Styling
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
      </div>
    </div>
  );
}

export default CountyMap;
