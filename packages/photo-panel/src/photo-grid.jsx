import { useState, useEffect, useRef, forwardRef } from 'react';
import { FiCheck, FiSquare, FiDownload, FiTrash2, FiEdit3 } from 'react-icons/fi';
import { PhotoLightbox } from './photo-lightbox.jsx';

export function PhotoGrid({
  apiBaseUrl,
  selectedPhotoIds = [],
  onSelectionChange,
  highlightedPhotoId,
  onPhotoClick,
  refreshTrigger,
  onPhotosChange, // Add callback for when photos are deleted/updated
  filters = {}, // Filter options: { year, month, tags }
  hideActions = false, // Hide batch actions (for split panel layout)
  hideLightbox = false // Don't render lightbox in grid (for app-level lightbox)
}) {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0); // Total photos matching filters
  const [hasMore, setHasMore] = useState(false);
  const [lightboxPhoto, setLightboxPhoto] = useState(null);
  const [isLightboxOpen, setIsLightboxOpen] = useState(false);
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const exportMenuRef = useRef(null);
  const photoRefs = useRef({}); // Store refs to photo items for scrolling

  // Scroll to highlighted photo when it changes
  useEffect(() => {
    if (highlightedPhotoId && photoRefs.current[highlightedPhotoId]) {
      photoRefs.current[highlightedPhotoId].scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });
    } else if (highlightedPhotoId && photos.length > 0) {
      // Photo not in current view - try loading more if available
      const photoExists = photos.some(p => p._id === highlightedPhotoId);

      if (!photoExists && hasMore && !loading) {
        // Load next page and check again
        fetchPhotos(page + 1, true);
      }
    }
  }, [highlightedPhotoId, photos, hasMore, loading, page]);

  // Close export menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(event.target)) {
        setShowExportMenu(false);
      }
    };

    if (showExportMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showExportMenu]);

  // Fetch photos from API
  const fetchPhotos = async (pageNum = 1, append = false) => {
    try {
      setLoading(true);

      // Build query parameters
      const params = new URLSearchParams({
        page: pageNum.toString(),
        limit: '20',
        sort_by: 'timestamp',
        order: 'desc'
      });

      // Add filter parameters if they exist
      if (filters.startDate) {
        params.append('start_date', filters.startDate);
      }
      if (filters.endDate) {
        params.append('end_date', filters.endDate);
      }
      if (filters.tags && filters.tags.length > 0) {
        params.append('tags', filters.tags.join(','));
      }

      const url = `${apiBaseUrl}/photos?${params.toString()}`;

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Failed to fetch photos: ${response.statusText}`);
      }

      const data = await response.json();

      if (append) {
        setPhotos(prev => [...prev, ...data.Photos]);
      } else {
        setPhotos(data.Photos);
      }

      setTotalPages(data.pagination.pages);
      setTotalCount(data.pagination.total || data.Photos.length);
      setHasMore(data.pagination.has_next);
      setPage(pageNum);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching photos:', err);
    } finally {
      setLoading(false);
    }
  };

  // Initial load and refresh trigger
  useEffect(() => {
    if (apiBaseUrl) {
      fetchPhotos(1, false);
    }
  }, [apiBaseUrl, refreshTrigger, filters.startDate, filters.endDate, filters.tags]);

  // Load more photos
  const loadMore = () => {
    if (hasMore && !loading) {
      fetchPhotos(page + 1, true);
    }
  };

  // Selection handlers
  const isSelected = (photoId) => selectedPhotoIds.includes(photoId);

  const toggleSelection = (photoId) => {
    const newSelection = isSelected(photoId)
      ? selectedPhotoIds.filter(id => id !== photoId)
      : [...selectedPhotoIds, photoId];

    onSelectionChange?.(newSelection);
  };

  const selectAll = () => {
    const allIds = photos.map(photo => photo._id);
    onSelectionChange?.(allIds);
  };

  const clearSelection = () => {
    onSelectionChange?.([]);
  };

  const handlePhotoClick = (photo) => {
    const photoIndex = photos.findIndex(p => p._id === photo._id);

    if (hideLightbox && onPhotoClick) {
      // Pass photo, all photos, and index to parent handler
      onPhotoClick(photo, photos, photoIndex);
    } else {
      // Use internal lightbox
      setLightboxPhoto(photo);
      setCurrentPhotoIndex(photoIndex);
      setIsLightboxOpen(true);
    }
  };

  const handleLightboxNavigate = (newIndex) => {
    if (newIndex >= 0 && newIndex < photos.length) {
      setCurrentPhotoIndex(newIndex);
      setLightboxPhoto(photos[newIndex]);
    }
  };

  const closeLightbox = () => {
    setIsLightboxOpen(false);
    setLightboxPhoto(null);
    setCurrentPhotoIndex(0);
  };

  const handleLightboxEdit = (updatedPhoto) => {
    // Update the photo in the local state
    setPhotos(prev => prev.map(p =>
      p._id === updatedPhoto._id ? updatedPhoto : p
    ));
    onPhotosChange?.(); // Refresh map
  };

  const handleLightboxDelete = (deletedPhoto) => {
    // Remove photo from local state
    setPhotos(prev => prev.filter(p => p._id !== deletedPhoto._id));
    // Remove from selection if selected
    if (selectedPhotoIds.includes(deletedPhoto._id)) {
      onSelectionChange?.(selectedPhotoIds.filter(id => id !== deletedPhoto._id));
    }

    // Handle navigation after delete
    const newPhotos = photos.filter(p => p._id !== deletedPhoto._id);
    if (newPhotos.length === 0) {
      // No more photos, close lightbox
      closeLightbox();
    } else if (currentPhotoIndex >= newPhotos.length) {
      // Current index is out of bounds, go to last photo
      const newIndex = newPhotos.length - 1;
      setCurrentPhotoIndex(newIndex);
      setLightboxPhoto(newPhotos[newIndex]);
    } else {
      // Stay at current index, but update photo
      setLightboxPhoto(newPhotos[currentPhotoIndex]);
    }

    onPhotosChange?.(); // Refresh map
  };

  // Batch action handlers
  const handleBatchDelete = async () => {
    if (selectedPhotoIds.length === 0) return;

    const confirmDelete = window.confirm(
      `Are you sure you want to delete ${selectedPhotoIds.length} photo(s)? This action cannot be undone.`
    );

    if (!confirmDelete) return;

    try {
      // Delete each selected photo
      const deletePromises = selectedPhotoIds.map(async (photoId) => {
        const response = await fetch(`${apiBaseUrl}/photos/${photoId}/delete`, {
          method: 'DELETE'
        });

        if (!response.ok) {
          throw new Error(`Failed to delete photo ${photoId}: ${response.statusText}`);
        }

        return response.json();
      });

      const results = await Promise.all(deletePromises);

      // Remove deleted photos from local state immediately
      const deletedIds = selectedPhotoIds.filter((_, index) => {
        // Only remove if the delete was successful
        try {
          return results[index] && results[index].Message;
        } catch {
          return false;
        }
      });

      setPhotos(prev => prev.filter(photo => !deletedIds.includes(photo._id)));

      // Clear selection and refresh
      onSelectionChange?.([]);
      onPhotosChange?.(); // Notify parent to refresh map

      if (deletedIds.length === selectedPhotoIds.length) {
        alert(`Successfully deleted ${deletedIds.length} photo(s)`);
      } else {
        alert(`Deleted ${deletedIds.length} of ${selectedPhotoIds.length} photo(s). Some deletions may have failed.`);
        // Refresh to get current state
        fetchPhotos(1, false);
      }
    } catch (error) {
      console.error('Error deleting photos:', error);
      alert(`Error deleting photos: ${error.message}`);
      // Refresh the photo list to get current state
      fetchPhotos(1, false);
    }
  };

  const handleBatchExport = async () => {
    if (selectedPhotoIds.length === 0) return;

    // Create export URL with selected photo IDs
    const exportUrl = `${apiBaseUrl}/export/zip?${selectedPhotoIds.map(id => `payload=${id}`).join('&')}`;

    // Use fetch to get the file with proper filename
    try {
      const response = await fetch(exportUrl);
      const blob = await response.blob();

      // Get filename from Content-Disposition header or generate with timestamp
      const contentDisposition = response.headers.get('content-disposition');
      let filename = `photos_${new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)}.zip`;

      if (contentDisposition) {
        // Try to extract filename from header
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Export failed. Please try again.');
    }
  };

  const handleBatchExportKML = async () => {
    if (selectedPhotoIds.length === 0) return;

    // Create KML export URL with selected photo IDs
    const exportUrl = `${apiBaseUrl}/export/kml?${selectedPhotoIds.map(id => `payload=${id}`).join('&')}`;

    try {
      const response = await fetch(exportUrl);
      const blob = await response.blob();

      // Get filename from Content-Disposition header or generate with timestamp
      const contentDisposition = response.headers.get('content-disposition');
      let filename = `photos_${new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)}.kml`;

      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Export failed. Please try again.');
    }
  };

  const handleBatchExportKMZ = async () => {
    if (selectedPhotoIds.length === 0) return;

    // Create KMZ export URL with selected photo IDs
    const exportUrl = `${apiBaseUrl}/export/kmz?${selectedPhotoIds.map(id => `payload=${id}`).join('&')}`;

    try {
      const response = await fetch(exportUrl);
      const blob = await response.blob();

      // Get filename from Content-Disposition header or generate with timestamp
      const contentDisposition = response.headers.get('content-disposition');
      let filename = `photos_${new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)}.kmz`;

      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Export failed. Please try again.');
    }
  };

  const handleBatchEditTags = () => {
    if (selectedPhotoIds.length === 0) return;

    const newTags = prompt(
      `Enter tags for ${selectedPhotoIds.length} photo(s) (comma-separated):`,
      ''
    );

    if (newTags === null) return; // User cancelled

    // TODO: Implement batch tag editing
    // This would require a new API endpoint for batch updates
    alert('Batch tag editing coming soon!');
  };

  if (loading && photos.length === 0) {
    return (
      <div className="photo-grid-loading">
        <div className="loading-spinner" />
        <p>Loading photos...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="photo-grid-error">
        <p>Error loading photos: {error}</p>
        <button
          className="panel-button"
          onClick={() => fetchPhotos(1, false)}
        >
          Retry
        </button>
      </div>
    );
  }

  if (photos.length === 0) {
    return (
      <div className="photo-grid-empty">
        <p className="empty-message">No photos found. Upload some photos to get started!</p>
      </div>
    );
  }

  return (
    <div className="photo-grid-container">
      {/* Selection Controls */}
      <div className="photo-grid-controls">
        <div className="selection-info">
          <span>
            {selectedPhotoIds.length} of {photos.length} selected
            {totalCount > photos.length && (
              <span className="total-count"> • Showing {photos.length} of {totalCount}</span>
            )}
            {(filters.startDate || filters.endDate || (filters.tags && filters.tags.length > 0)) && (
              <span className="filtered-indicator"> (filtered)</span>
            )}
          </span>
        </div>

        <div className="selection-buttons">
          <button
            className="control-btn-small"
            onClick={selectAll}
            disabled={selectedPhotoIds.length === photos.length}
          >
            Select All
          </button>
          <button
            className="control-btn-small"
            onClick={clearSelection}
            disabled={selectedPhotoIds.length === 0}
          >
            Clear
          </button>
        </div>
      </div>

      {/* Batch Actions */}
      {!hideActions && selectedPhotoIds.length > 0 && (
        <div className="batch-actions">
          <div className="export-dropdown" ref={exportMenuRef}>
            <button
              className="batch-btn export-btn"
              onClick={() => setShowExportMenu(!showExportMenu)}
              title="Export selected photos"
            >
              <FiDownload />
              Export ({selectedPhotoIds.length})
            </button>
            {showExportMenu && (
              <div className="export-menu">
                <button
                  className="export-menu-item"
                  onClick={() => {
                    handleBatchExport();
                    setShowExportMenu(false);
                  }}
                >
                  <FiDownload />
                  ZIP Archive
                </button>
                <button
                  className="export-menu-item"
                  onClick={() => {
                    handleBatchExportKML();
                    setShowExportMenu(false);
                  }}
                >
                  <FiDownload />
                  KML (Google Earth)
                </button>
                <button
                  className="export-menu-item"
                  onClick={() => {
                    handleBatchExportKMZ();
                    setShowExportMenu(false);
                  }}
                >
                  <FiDownload />
                  KMZ (Compressed)
                </button>
              </div>
            )}
          </div>
          <button
            className="batch-btn edit-btn"
            onClick={handleBatchEditTags}
            title="Edit tags for selected photos"
          >
            <FiEdit3 />
            Edit Tags
          </button>
          <button
            className="batch-btn delete-btn"
            onClick={handleBatchDelete}
            title="Delete selected photos"
          >
            <FiTrash2 />
            Delete
          </button>
        </div>
      )}

      {/* Photo Grid */}
      <div className="photo-grid">
        {photos.map(photo => (
          <PhotoGridItem
            key={photo._id}
            photo={photo}
            isSelected={isSelected(photo._id)}
            isHighlighted={photo._id === highlightedPhotoId}
            onToggleSelection={() => toggleSelection(photo._id)}
            onClick={() => handlePhotoClick(photo)}
            ref={(el) => {
              if (el) photoRefs.current[photo._id] = el;
            }}
          />
        ))}
      </div>

      {/* Load More */}
      {hasMore && (
        <div className="load-more-container">
          <button
            className="panel-button load-more-btn"
            onClick={loadMore}
            disabled={loading}
          >
            {loading ? 'Loading...' : `Load More (${totalPages - page} pages remaining)`}
          </button>
        </div>
      )}

      {/* Photo Lightbox - only render if not hidden */}
      {!hideLightbox && (
        <PhotoLightbox
          photo={lightboxPhoto}
          isOpen={isLightboxOpen}
          onClose={closeLightbox}
          onDelete={handleLightboxDelete}
          onEdit={handleLightboxEdit}
          apiBaseUrl={apiBaseUrl}
          photos={photos}
          currentIndex={currentPhotoIndex}
          onNavigate={handleLightboxNavigate}
        />
      )}
    </div>
  );
}

const PhotoGridItem = forwardRef(({ photo, isSelected, isHighlighted, onToggleSelection, onClick }, ref) => {
  const thumbnailUrl = photo.thumbnail || photo.url || '/placeholder-image.jpg';

  return (
    <div
      ref={ref}
      className={`photo-grid-item ${isSelected ? 'selected' : ''} ${isHighlighted ? 'highlighted' : ''}`}
    >
      {/* Selection Checkbox */}
      <button
        className="photo-checkbox"
        onClick={(e) => {
          e.stopPropagation();
          onToggleSelection();
        }}
      >
        {isSelected ? <FiCheck /> : <FiSquare />}
      </button>

      {/* Photo Thumbnail */}
      <div
        className="photo-thumbnail"
        onClick={onClick}
      >
        <img
          src={thumbnailUrl}
          alt={photo.filename || 'Photo'}
          loading="lazy"
        />

        {/* Selection Overlay */}
        {isSelected && <div className="selection-overlay" />}

        {/* Highlight Border */}
        {isHighlighted && <div className="highlight-border" />}
      </div>

      {/* Photo Info */}
      <div className="photo-info">
        <span className="photo-filename">{photo.filename}</span>
        {photo.timestamp && (
          <span className="photo-date">
            {new Date(photo.timestamp).toLocaleDateString()}
          </span>
        )}
        {photo.tags && photo.tags.length > 0 && (
          <div className="photo-tags">
            {photo.tags.slice(0, 2).map(tag => (
              <span key={tag} className="photo-tag">{tag}</span>
            ))}
            {photo.tags.length > 2 && (
              <span className="photo-tag-more">+{photo.tags.length - 2}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
});

PhotoGridItem.displayName = 'PhotoGridItem';