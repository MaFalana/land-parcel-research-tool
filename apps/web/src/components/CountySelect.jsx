import React from "react";
import { Combobox } from "@hwc/ui";
import { MdClear } from "react-icons/md";

/**
 * CountySelect Component
 * 
 * Indiana-specific county selector built on top of generic Combobox component.
 * 
 * @param {string} value - Currently selected county name
 * @param {Function} onChange - Callback when selection changes (countyName, countyData)
 * @param {Array} counties - Array of county objects with { county, url }
 * @param {string} label - Optional label text
 * @param {boolean} required - Mark as required field
 * @param {string} error - Error message to display
 */
export function CountySelect({
  value = "",
  onChange,
  counties = [],
  label = "County",
  required = false,
  error
}) {
  // Transform counties array to options format
  const options = counties.map(county => ({
    value: county.county,
    label: `${county.county} County`
  }));

  const handleChange = (selectedValue, selectedOption) => {
    // Find the full county data
    const countyData = counties.find(c => c.county === selectedValue);
    
    if (onChange) {
      onChange(selectedValue, countyData);
    }
  };

  return (
    <Combobox
      value={value}
      onChange={handleChange}
      options={options}
      placeholder="Search counties..."
      label={label}
      required={required}
      error={error}
      name="county"
      ClearIcon={MdClear}
    />
  );
}

export default CountySelect;
