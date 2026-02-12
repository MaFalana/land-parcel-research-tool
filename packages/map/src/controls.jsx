import './map.css';
import { FaPlus, FaMinus } from "react-icons/fa6";
import { MdCenterFocusStrong } from "react-icons/md";
import React from 'react';

export function LayerToggle({ baseLayer, setBaseLayer, basePath = "", options = [] }) {
  // If no options provided, use default two
  const defaultOptions = [
    { key: 'streets', label: 'Street view' },
    { key: 'satellite', label: 'Satellite view' }
  ];

  const layerOptions = options.length > 0 ? options : defaultOptions;

  return (
    <div className='layer-toggles'>
      {layerOptions.map((option) => (
        <button
          key={option.key}
          onClick={() => setBaseLayer(option.key)}
          className="layer-btn"
          aria-label={option.label}
          aria-checked={baseLayer === option.key}
          title={option.label}
        >
          {/* Use thumbnail if available, otherwise show first letter */}
          {option.key === 'streets' || option.key === 'satellite' ? (
            <img
              src={`${basePath}/assets/${option.key === 'streets' ? 'streets' : 'satellite'}.png`}
              alt={option.label}
            />
          ) : (
            <div className="layer-btn-text">
              {option.label.charAt(0)}
            </div>
          )}
          <span className="active-dot" />
        </button>
      ))}
    </div>
  );
}

export function ZoomControls({ onZoomIn, onZoomOut, onZoomToAll }) {
  return (
    <div className="zoom-controls">
      <button
        onClick={onZoomOut}
        className="zoom-btn"
        aria-label="Zoom out"
      >
        <FaMinus />
      </button>

      <button
        onClick={onZoomToAll}
        className="zoom-btn"
        aria-label="Zoom to all markers"
      >
        <MdCenterFocusStrong />
      </button>

      <button
        onClick={onZoomIn}
        className="zoom-btn"
        aria-label="Zoom in"
      >
        <FaPlus />
      </button>
    </div>
  );
}
