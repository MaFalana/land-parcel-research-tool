import { useState, useEffect } from 'react';
import { FiX, FiCalendar, FiTag, FiMap } from 'react-icons/fi';

export function FilterSection({ apiBaseUrl, filters, onFiltersChange }) {
    const [availableTags, setAvailableTags] = useState([]);
    const [loadingTags, setLoadingTags] = useState(false);
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');

    // Fetch available tags from API
    useEffect(() => {
        const fetchTags = async () => {
            if (!apiBaseUrl) return;

            try {
                setLoadingTags(true);
                const response = await fetch(`${apiBaseUrl}/photos/tags`);
                if (response.ok) {
                    const data = await response.json();
                    setAvailableTags(data.tags || []);
                }
            } catch (error) {
                console.error('Error fetching tags:', error);
            } finally {
                setLoadingTags(false);
            }
        };

        fetchTags();
    }, [apiBaseUrl]);

    // Convert date range to filters for API
    const handleDateRangeChange = (start, end) => {
        setStartDate(start);
        setEndDate(end);

        // Simply pass the dates to the API - no need to calculate year/month
        onFiltersChange({
            ...filters,
            startDate: start || null,
            endDate: end || null
        });
    };

    const handleTagToggle = (tag) => {
        const currentTags = filters.tags || [];
        const newTags = currentTags.includes(tag)
            ? currentTags.filter(t => t !== tag)
            : [...currentTags, tag];
        onFiltersChange({ ...filters, tags: newTags.length > 0 ? newTags : null });
    };

    const handleClearFilters = () => {
        setStartDate('');
        setEndDate('');
        onFiltersChange({ startDate: null, endDate: null, tags: null });
    };

    const hasActiveFilters = filters.startDate || filters.endDate || (filters.tags && filters.tags.length > 0);

    // Format date for display
    const formatDateDisplay = (dateStr) => {
        if (!dateStr) return '';
        // Parse date string as local date to avoid timezone issues
        const [year, month, day] = dateStr.split('-').map(Number);
        const date = new Date(year, month - 1, day);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    };

    return (
        <div className="filter-section">
            {/* Date Range Filter */}
            <div className="filter-group">
                <label className="filter-label">
                    <FiCalendar />
                    <span>Date Range</span>
                </label>

                <div className="filter-date-range">
                    <div className="filter-date-input-group">
                        <label className="filter-date-label">From</label>
                        <input
                            type="date"
                            className="panel-date-input"
                            value={startDate}
                            onChange={(e) => handleDateRangeChange(e.target.value, endDate)}
                            max={endDate || undefined}
                        />
                    </div>

                    <div className="filter-date-input-group">
                        <label className="filter-date-label">To</label>
                        <input
                            type="date"
                            className="panel-date-input"
                            value={endDate}
                            onChange={(e) => handleDateRangeChange(startDate, e.target.value)}
                            min={startDate || undefined}
                        />
                    </div>
                </div>
            </div>

            {/* Tag Filters */}
            <div className="filter-group">
                <label className="filter-label">
                    <FiTag />
                    <span>Tags</span>
                </label>

                {loadingTags ? (
                    <div className="filter-tags-loading">Loading tags...</div>
                ) : availableTags.length === 0 ? (
                    <div className="filter-tags-empty">No tags available</div>
                ) : (
                    <div className="filter-tags">
                        {availableTags.map(tag => (
                            <button
                                key={tag}
                                className={`filter-tag ${filters.tags?.includes(tag) ? 'active' : ''}`}
                                onClick={() => handleTagToggle(tag)}
                            >
                                {tag}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Clear Filters */}
            {hasActiveFilters && (
                <button
                    className="panel-button filter-clear-btn"
                    onClick={handleClearFilters}
                >
                    <FiX />
                    Clear All Filters
                </button>
            )}

            {/* Active Filters Summary */}
            {hasActiveFilters && (
                <div className="filter-summary">
                    <span className="filter-summary-label">Active filters:</span>
                    {(filters.startDate || filters.endDate) && (
                        <span className="filter-badge">
                            {filters.startDate ? formatDateDisplay(filters.startDate) : 'Start'}
                            {' → '}
                            {filters.endDate ? formatDateDisplay(filters.endDate) : 'End'}
                        </span>
                    )}
                    {filters.tags?.map(tag => (
                        <span key={tag} className="filter-badge">
                            {tag}
                            <button
                                className="filter-badge-remove"
                                onClick={() => handleTagToggle(tag)}
                            >
                                ×
                            </button>
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
}
