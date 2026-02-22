import { useState, useEffect } from 'react';
import { MdClose, MdDownload, MdCancel, MdDelete, MdRefresh, MdReplay } from 'react-icons/md';
import './job-detail-modal.css';

/**
 * JobDetailModal - Detailed view of a job with actions
 * 
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether the modal is open
 * @param {Function} props.onClose - Callback when modal is closed
 * @param {string} props.jobId - The job ID to display
 */
export function JobDetailModal({ isOpen, onClose, jobId }) {
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (isOpen && jobId) {
      fetchJobDetails();
    }
  }, [isOpen, jobId]);

  const fetchJobDetails = async () => {
    setLoading(true);
    setError('');

    try {
      const apiBaseUrl = import.meta.env.PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${apiBaseUrl}/jobs/${jobId}`);

      if (!response.ok) {
        throw new Error('Failed to fetch job details');
      }

      const data = await response.json();
      setJob(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (fileType) => {
    try {
      const apiBaseUrl = import.meta.env.PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${apiBaseUrl}/jobs/${jobId}/download/${fileType}`);

      if (!response.ok) {
        throw new Error('Download failed');
      }

      // Get filename from Content-Disposition header or use default
      const contentDisposition = response.headers.get('Content-Disposition');
      let defaultExtension = 'dxf';
      if (fileType === 'excel') defaultExtension = 'xlsx';
      if (fileType === 'prc') defaultExtension = 'zip';
      
      let filename = `${job.county}_${fileType}.${defaultExtension}`;
      
      if (contentDisposition) {
        const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
        if (matches && matches[1]) {
          filename = matches[1].replace(/['"]/g, '');
        }
      }

      // Download the file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert(`Download failed: ${err.message}`);
    }
  };

  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel this job?')) return;

    setActionLoading(true);
    try {
      const apiBaseUrl = import.meta.env.PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${apiBaseUrl}/jobs/${jobId}/cancel`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to cancel job');
      }

      await fetchJobDetails(); // Refresh
    } catch (err) {
      alert(`Cancel failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this job? This cannot be undone.')) return;

    setActionLoading(true);
    try {
      const apiBaseUrl = import.meta.env.PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${apiBaseUrl}/jobs/${jobId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete job');
      }

      onClose(); // Close modal after successful delete
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRetry = async () => {
    if (!confirm('Retry this job with the same configuration?')) return;

    setActionLoading(true);
    try {
      const apiBaseUrl = import.meta.env.PUBLIC_API_BASE_URL || 'http://localhost:8000';
      
      const response = await fetch(`${apiBaseUrl}/jobs/${jobId}/retry`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to retry job');
      }

      const result = await response.json();
      alert(`New job created: ${result.job_id}`);
      onClose(); // Close modal
      window.location.reload(); // Refresh to show new job
    } catch (err) {
      console.error('Retry error:', err);
      alert(`Retry failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  if (!isOpen) return null;

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return 'status-pending';
      case 'processing': return 'status-processing';
      case 'completed': return 'status-completed';
      case 'failed': return 'status-failed';
      case 'cancelled': return 'status-cancelled';
      default: return '';
    }
  };

  const formatDate = (timestamp) => {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    // Check if date is valid
    if (isNaN(date.getTime())) return 'Invalid Date';
    // Format in user's local timezone
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: 'numeric',
      minute: 'numeric',
      second: 'numeric',
      hour12: true
    });
  };

  return (
    <div className="job-modal-overlay" onClick={onClose}>
      <div className="job-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="job-modal-header">
          <h2>Job Details</h2>
          <button className="job-modal-close" onClick={onClose}>
            <MdClose />
          </button>
        </div>

        <div className="job-modal-body">
          {loading ? (
            <div className="job-modal-loading">Loading job details...</div>
          ) : error ? (
            <div className="job-modal-error">{error}</div>
          ) : job ? (
            <>
              {/* Status Section */}
              <div className="job-detail-section">
                <div className="job-detail-status-header">
                  <h3>{job.county} County</h3>
                  <span className={`job-detail-status ${getStatusColor(job.status)}`}>
                    {job.status}
                  </span>
                </div>
              </div>

              {/* Info Grid */}
              <div className="job-detail-grid">
                <div className="job-detail-item">
                  <span className="job-detail-label">Job ID</span>
                  <span className="job-detail-value job-detail-mono">{job.id}</span>
                </div>
                <div className="job-detail-item">
                  <span className="job-detail-label">Parcel Count</span>
                  <span className="job-detail-value">{job.parcel_count}</span>
                </div>
                <div className="job-detail-item">
                  <span className="job-detail-label">Platform</span>
                  <span className="job-detail-value job-detail-mono">{job.platform}</span>
                </div>
                <div className="job-detail-item">
                  <span className="job-detail-label">CRS (EPSG)</span>
                  <span className="job-detail-value">{job.crs_id}</span>
                </div>
                <div className="job-detail-item">
                  <span className="job-detail-label">Created</span>
                  <span className="job-detail-value">{formatDate(job.created_at)}</span>
                </div>
                <div className="job-detail-item">
                  <span className="job-detail-label">Updated</span>
                  <span className="job-detail-value">{formatDate(job.updated_at)}</span>
                </div>
              </div>

              {/* Error Message */}
              {job.error_message && (
                <div className="job-detail-error-box">
                  <strong>Error:</strong> {job.error_message}
                </div>
              )}

              {/* Downloads Section */}
              {job.status === 'completed' && (
                <div className="job-detail-section">
                  <h3>Downloads</h3>
                  <div className="job-detail-downloads">
                    <button
                      className="job-detail-download-btn"
                      onClick={() => handleDownload('excel')}
                    >
                      <MdDownload />
                      Excel Data
                    </button>
                    <button
                      className="job-detail-download-btn"
                      onClick={() => handleDownload('labels')}
                    >
                      <MdDownload />
                      Labels (DXF)
                    </button>
                    <button
                      className="job-detail-download-btn"
                      onClick={() => handleDownload('prc')}
                    >
                      <MdDownload />
                      Property Cards
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>

        <div className="job-modal-footer">
          <button
            className="job-modal-btn job-modal-btn-secondary"
            onClick={fetchJobDetails}
            disabled={loading || actionLoading}
          >
            <MdRefresh />
            Refresh
          </button>

          {job && (job.status === 'pending' || job.status === 'processing') && (
            <button
              className="job-modal-btn job-modal-btn-warning"
              onClick={handleCancel}
              disabled={actionLoading}
            >
              <MdCancel />
              Cancel Job
            </button>
          )}

          {job && (job.status === 'failed' || job.status === 'cancelled') && (
            <>
              <button
                className="job-modal-btn job-modal-btn-primary"
                onClick={handleRetry}
                disabled={actionLoading}
              >
                <MdReplay />
                Retry Job
              </button>
              <button
                className="job-modal-btn job-modal-btn-danger"
                onClick={handleDelete}
                disabled={actionLoading}
              >
                <MdDelete />
                Delete Job
              </button>
            </>
          )}

          {job && job.status === 'completed' && (
            <button
              className="job-modal-btn job-modal-btn-danger"
              onClick={handleDelete}
              disabled={actionLoading}
            >
              <MdDelete />
              Delete Job
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
