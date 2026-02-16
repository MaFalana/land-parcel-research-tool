import React, { useState, useEffect } from 'react';
import { FileDropZone } from '@hwc/ui';
import { CrsSelect } from './CrsSelect';
import './job-submission-modal.css';

/**
 * JobSubmissionModal - Multi-step modal for submitting parcel research jobs
 * 
 * Steps:
 * 1. CRS Selection
 * 2. File Uploads (Parcel IDs + Shapefiles)
 * 3. Review & Submit
 * 4. Job Status Display
 * 
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether the modal is open
 * @param {Function} props.onClose - Callback when modal is closed
 * @param {string} props.selectedCounty - The selected county name
 * @param {string} props.gisUrl - The GIS portal URL for the county
 */
export function JobSubmissionModal({ isOpen, onClose, selectedCounty, gisUrl }) {
  const [step, setStep] = useState(1); // 1: CRS, 2: Files, 3: Review, 4: Status
  const [crsId, setCrsId] = useState(null);
  const [crsData, setCrsData] = useState(null);
  const [parcelFile, setParcelFile] = useState(null);
  const [parcelText, setParcelText] = useState('');
  const [shapefileZip, setShapefileZip] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [jobResult, setJobResult] = useState(null);
  const [error, setError] = useState('');

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setCrsId(null);
      setCrsData(null);
      setParcelFile(null);
      setParcelText('');
      setShapefileZip(null);
      setIsSubmitting(false);
      setJobResult(null);
      setError('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleCrsSelect = (selectedCrsId, selectedCrsData) => {
    setCrsId(selectedCrsId);
    setCrsData(selectedCrsData);
  };

  const handleParcelFileSelect = (file) => {
    setParcelFile(file);
    setParcelText('');
  };

  const handleParcelTextPaste = (text) => {
    setParcelText(text);
    setParcelFile(null);
  };

  const handleShapefileSelect = (file) => {
    setShapefileZip(file);
  };

  const handleNext = () => {
    setError('');
    
    if (step === 1) {
      if (!crsId) {
        setError('Please select a coordinate reference system');
        return;
      }
      setStep(2);
    } else if (step === 2) {
      if (!parcelFile && !parcelText.trim()) {
        setError('Please provide parcel IDs (file or text)');
        return;
      }
      if (!shapefileZip) {
        setError('Please upload a shapefile ZIP');
        return;
      }
      setStep(3);
    }
  };

  const handleBack = () => {
    setError('');
    if (step > 1 && step < 4) {
      setStep(step - 1);
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError('');

    try {
      const formData = new FormData();
      
      // Add parcel file or create one from text
      if (parcelFile) {
        formData.append('parcel_file', parcelFile);
      } else {
        // Create a text file from pasted content
        const blob = new Blob([parcelText], { type: 'text/plain' });
        formData.append('parcel_file', blob, 'parcels.txt');
      }

      // Add shapefile
      formData.append('shapefile_zip', shapefileZip);
      
      // Add metadata
      formData.append('county', selectedCounty);
      formData.append('crs_id', crsId);
      formData.append('gis_url', gisUrl);

      // Get API base URL from env
      const apiBaseUrl = import.meta.env.PUBLIC_API_BASE_URL || 'http://localhost:8000';
      
      const response = await fetch(`${apiBaseUrl}/jobs/create`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create job');
      }

      const result = await response.json();
      setJobResult(result);
      setStep(4);
    } catch (err) {
      setError(err.message || 'Failed to submit job');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      onClose();
    }
  };

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Submit Parcel Research Job</h2>
          <p className="county-name">{selectedCounty} County</p>
          <button className="close-button" onClick={handleClose} disabled={isSubmitting}>
            ×
          </button>
        </div>

        <div className="modal-body">
          {/* Step 1: CRS Selection */}
          {step === 1 && (
            <div className="step-content">
              <h3>Step 1: Select Coordinate Reference System</h3>
              <p className="step-description">
                Choose the coordinate system for your DXF output (state plane or county coordinates)
              </p>
              <CrsSelect
                value={crsId}
                onChange={handleCrsSelect}
                placeholder="Search by name or EPSG code..."
              />
            </div>
          )}

          {/* Step 2: File Uploads */}
          {step === 2 && (
            <div className="step-content">
              <h3>Step 2: Upload Files</h3>
              
              <div className="file-section">
                <label>Parcel IDs</label>
                <p className="file-description">
                  Paste parcel IDs or drop a file (.txt, .csv, .xlsx)
                </p>
                <FileDropZone
                  acceptedFormats={['.txt', '.csv', '.xlsx']}
                  maxSizeMB={5}
                  onFileSelect={handleParcelFileSelect}
                  onTextPaste={handleParcelTextPaste}
                  placeholder="Paste parcel IDs (one per line) or drop a file..."
                />
              </div>

              <div className="file-section">
                <label>Shapefiles</label>
                <p className="file-description">
                  Upload a ZIP file containing your shapefiles
                </p>
                <FileDropZone
                  acceptedFormats={['.zip']}
                  maxSizeMB={5}
                  onFileSelect={handleShapefileSelect}
                  placeholder="Drop shapefile ZIP here..."
                />
              </div>
            </div>
          )}

          {/* Step 3: Review */}
          {step === 3 && (
            <div className="step-content">
              <h3>Step 3: Review & Submit</h3>
              <div className="review-section">
                <div className="review-item">
                  <span className="review-label">County:</span>
                  <span className="review-value">{selectedCounty}</span>
                </div>
                <div className="review-item">
                  <span className="review-label">Coordinate System:</span>
                  <span className="review-value">{crsData?.name} (EPSG: {crsId})</span>
                </div>
                <div className="review-item">
                  <span className="review-label">Parcel IDs:</span>
                  <span className="review-value">
                    {parcelFile ? parcelFile.name : 'Pasted text'}
                  </span>
                </div>
                <div className="review-item">
                  <span className="review-label">Shapefiles:</span>
                  <span className="review-value">{shapefileZip?.name}</span>
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Job Status */}
          {step === 4 && jobResult && (
            <div className="step-content">
              <h3>Job Submitted Successfully!</h3>
              <div className="job-status">
                <div className="status-item">
                  <span className="status-label">Job ID:</span>
                  <span className="status-value">{jobResult.job_id}</span>
                </div>
                <div className="status-item">
                  <span className="status-label">Status:</span>
                  <span className={`status-badge ${jobResult.status}`}>
                    {jobResult.status}
                  </span>
                </div>
                <div className="status-item">
                  <span className="status-label">Parcel Count:</span>
                  <span className="status-value">{jobResult.parcel_count}</span>
                </div>
                <div className="status-item">
                  <span className="status-label">Platform:</span>
                  <span className="status-value">{jobResult.platform}</span>
                </div>
                <p className="status-message">{jobResult.message}</p>
              </div>
            </div>
          )}

          {error && (
            <div className="error-banner">
              {error}
            </div>
          )}
        </div>

        <div className="modal-footer">
          {step < 4 && (
            <>
              {step > 1 && (
                <button
                  className="button button-secondary"
                  onClick={handleBack}
                  disabled={isSubmitting}
                >
                  Back
                </button>
              )}
              {step < 3 ? (
                <button
                  className="button button-primary"
                  onClick={handleNext}
                  disabled={isSubmitting}
                >
                  Next
                </button>
              ) : (
                <button
                  className="button button-primary"
                  onClick={handleSubmit}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'Submitting...' : 'Submit Job'}
                </button>
              )}
            </>
          )}
          {step === 4 && (
            <button
              className="button button-primary"
              onClick={handleClose}
            >
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
