import React, { useState, useEffect } from 'react';
import { Combobox } from '@hwc/ui';

/**
 * CrsSelect - Coordinate Reference System selector for Indiana
 * Wraps the generic Combobox with CRS-specific data and search logic
 * 
 * @param {Object} props
 * @param {number} props.value - Selected CRS EPSG code
 * @param {Function} props.onChange - Callback when CRS is selected (crsId, crsData) => void
 * @param {string} props.placeholder - Placeholder text
 * @param {boolean} props.disabled - Whether the component is disabled
 */
export function CrsSelect({ value, onChange, placeholder = 'Select coordinate system...', disabled = false }) {
  const [crsOptions, setCrsOptions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load CRS data
    const loadCrsData = async () => {
      try {
        const module = await import('../data/epsg/Indiana.json');
        const data = module.default;
        
        // Transform CRS data for combobox
        // Display name only, but search by both name and EPSG code
        const options = data.map(crs => ({
          value: crs._id,
          label: crs.name,
          searchText: `${crs.name} ${crs._id}`, // For searching by name or EPSG
          data: crs // Store full CRS data
        }));
        
        setCrsOptions(options);
        setLoading(false);
      } catch (error) {
        console.error('Failed to load CRS data:', error);
        setLoading(false);
      }
    };

    loadCrsData();
  }, []);

  const handleChange = (selectedValue) => {
    const selectedOption = crsOptions.find(opt => opt.value === selectedValue);
    if (selectedOption && onChange) {
      onChange(selectedOption.value, selectedOption.data);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '12px', color: '#64748b', fontSize: '14px' }}>
        Loading coordinate systems...
      </div>
    );
  }

  return (
    <Combobox
      options={crsOptions}
      value={value}
      onChange={handleChange}
      placeholder={placeholder}
      disabled={disabled}
      searchBy="searchText" // Search by both name and EPSG code
    />
  );
}
