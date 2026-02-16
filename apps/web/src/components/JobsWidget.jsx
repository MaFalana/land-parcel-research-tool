import React, { useState, useEffect } from 'react';
import { MdExpandLess, MdExpandMore, MdRefresh, MdWork } from 'react-icons/md';
import './jobs-widget.css';

/**
 * JobsWidget - Collapsible widget showing active jobs
 * Positioned at bottom of screen
 * 
 * @param {Object} props
 * @param {Function} props.onJobClick - Callback when a job is clicked (jobId) => void
 */
export function JobsWidget({ onJobClick }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Fetch jobs on mount and when expanded
  useEffect(() => {
    if (isExpanded) {
      fetchJobs();
    }
  }, [isExpanded]);

  // Auto-refresh every 10 seconds when expanded
  useEffect(() => {
    if (!isExpanded) return;

    const interval = setInterval(() => {
      fetchJobs();
    }, 10000);

    return () => clearInterval(interval);
  }, [isExpanded]);

  const fetchJobs = async () => {
    setLoading(true);
    setError('');

    try {
      const apiBaseUrl = import.meta.env.PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${apiBaseUrl}/jobs/?limit=10`);

      if (!response.ok) {
        throw new Error('Failed to fetch jobs');
      }

      const data = await response.json();
      setJobs(data.jobs || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const activeJobsCount = jobs.filter(job => 
    job.status === 'pending' || job.status === 'processing'
  ).length;

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

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  return (
    <div className={`jobs-widget ${isExpanded ? 'expanded' : ''}`}>
      {/* Collapsed Header */}
      <div className="jobs-widget-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="jobs-widget-title">
          <MdWork className="jobs-widget-icon" />
          <span>Jobs</span>
          {activeJobsCount > 0 && (
            <span className="jobs-widget-badge">{activeJobsCount}</span>
          )}
        </div>
        <div className="jobs-widget-actions">
          {isExpanded && (
            <button
              className="jobs-widget-refresh"
              onClick={(e) => {
                e.stopPropagation();
                fetchJobs();
              }}
              disabled={loading}
            >
              <MdRefresh className={loading ? 'spinning' : ''} />
            </button>
          )}
          <button className="jobs-widget-toggle">
            {isExpanded ? <MdExpandMore /> : <MdExpandLess />}
          </button>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="jobs-widget-content">
          {error && (
            <div className="jobs-widget-error">
              {error}
            </div>
          )}

          {loading && jobs.length === 0 ? (
            <div className="jobs-widget-loading">
              Loading jobs...
            </div>
          ) : jobs.length === 0 ? (
            <div className="jobs-widget-empty">
              No jobs yet. Submit a job to get started!
            </div>
          ) : (
            <div className="jobs-widget-list">
              {jobs.map((job) => {
                const jobId = job.id || job._id; // Handle both id and _id
                return (
                  <div
                    key={jobId}
                    className="job-item"
                    onClick={() => onJobClick && onJobClick(jobId)}
                  >
                  <div className="job-item-header">
                    <span className="job-item-county">{job.county} County</span>
                    <span className={`job-item-status ${getStatusColor(job.status)}`}>
                      {job.status}
                    </span>
                  </div>
                  <div className="job-item-details">
                    <span className="job-item-parcels">
                      {job.parcel_count} parcels
                    </span>
                    <span className="job-item-time">
                      {formatTime(job.created_at)}
                    </span>
                  </div>
                  {job.platform && (
                    <div className="job-item-platform">
                      Platform: {job.platform}
                    </div>
                  )}
                </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
