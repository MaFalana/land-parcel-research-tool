# Dependencies Guide

## Installation Methods

### Method 1: Using pyproject.toml (Recommended)

```bash
# Install in editable mode
pip install -e .

# Or install from pyproject.toml
pip install .
```

### Method 2: Direct pip install

```bash
pip install fastapi uvicorn pymongo azure-storage-blob pydantic python-multipart \
    openpyxl pandas geopandas shapely pyproj ezdxf playwright beautifulsoup4 \
    requests "pyjwt[crypto]" cryptography
```

### Method 3: Using requirements.txt (if needed)

Generate from pyproject.toml:
```bash
pip install pip-tools
pip-compile pyproject.toml
pip install -r requirements.txt
```

## Core Dependencies

### Web Framework
- **fastapi** (>=0.110) - Modern web framework
- **uvicorn[standard]** (>=0.27) - ASGI server
- **pydantic-settings** (>=2.0) - Settings management
- **python-multipart** (>=0.0.6) - File upload support

### Database & Storage
- **pymongo** (>=4.5.0) - MongoDB driver
- **azure-storage-blob** (>=12.19.0) - Azure Blob Storage

### Data Processing
- **pandas** (>=2.1.0) - Data manipulation
- **openpyxl** (>=3.1.2) - Excel file handling

### GIS & Spatial
- **geopandas** (>=0.14.0) - Geospatial data processing
- **fiona** (>=1.9.6) - Shapefile I/O
- **shapely** (>=2.0.0) - Geometric operations
- **pyproj** (>=3.6.0) - Coordinate transformations
- **ezdxf** (>=1.1.0) - DXF file generation

### Web Scraping
- **playwright** (>=1.40.0) - Browser automation
- **beautifulsoup4** (>=4.12.0) - HTML parsing
- **requests** (>=2.31.0) - HTTP client

### Authentication
- **pyjwt[crypto]** (>=2.8.0) - JWT token handling
- **cryptography** (>=41.0.0) - Cryptographic operations

## Post-Installation

### Install Playwright Browser

```bash
python -m playwright install chromium
```

This downloads the Chromium browser (~100MB) needed for web scraping.

### Verify Installation

```bash
# Check Python version
python --version  # Should be >= 3.11

# Check installed packages
pip list | grep fastapi
pip list | grep playwright
pip list | grep geopandas

# Test Playwright
python -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"

# Test imports
python -c "import fastapi, pymongo, geopandas, ezdxf; print('All imports OK')"
```

## Development Dependencies (Optional)

For development and testing:

```bash
pip install pytest pytest-asyncio httpx black ruff mypy
```

Add to pyproject.toml:
```toml
[project.optional-dependencies]
dev = [
  "pytest>=7.4.0",
  "pytest-asyncio>=0.21.0",
  "httpx>=0.24.0",
  "black>=23.0.0",
  "ruff>=0.0.280",
  "mypy>=1.4.0"
]
```

Install with:
```bash
pip install -e ".[dev]"
```

## Platform-Specific Notes

### Windows
- Install Visual C++ Build Tools if you encounter compilation errors
- Use PowerShell or CMD (not Git Bash) for Playwright installation

### macOS
- May need to install Xcode Command Line Tools: `xcode-select --install`
- Use Homebrew for system dependencies if needed

### Linux
- Install system dependencies for GeoPandas:
  ```bash
  sudo apt-get install libgeos-dev libproj-dev
  ```
- Install Playwright system dependencies:
  ```bash
  playwright install-deps chromium
  ```

## Docker

If using Docker, dependencies are installed automatically:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY pyproject.toml .
RUN pip install -e .

# Install Playwright
RUN playwright install chromium
RUN playwright install-deps chromium
```

## Troubleshooting

### "No module named 'playwright'"
```bash
pip install playwright
python -m playwright install chromium
```

### "Could not find a version that satisfies the requirement"
- Update pip: `pip install --upgrade pip`
- Check Python version: `python --version` (must be >= 3.11)

### "Microsoft Visual C++ 14.0 or greater is required" (Windows)
- Install Visual C++ Build Tools from Microsoft

### "ImportError: cannot import name 'CRS' from 'pyproj'"
```bash
pip install --upgrade pyproj
```

### Playwright browser not found
```bash
# Reinstall browser
python -m playwright install chromium --force
```

## Version Compatibility

| Python | FastAPI | Playwright | GeoPandas |
|--------|---------|------------|-----------|
| 3.11   | ✅      | ✅         | ✅        |
| 3.12   | ✅      | ✅         | ✅        |
| 3.10   | ✅      | ✅         | ⚠️        |
| 3.9    | ⚠️      | ✅         | ⚠️        |

✅ Fully supported
⚠️ May work but not tested

## Updating Dependencies

```bash
# Update all packages
pip install --upgrade -e .

# Update specific package
pip install --upgrade fastapi

# Check for outdated packages
pip list --outdated
```

## Production Recommendations

1. **Pin versions** in pyproject.toml for reproducibility
2. **Use virtual environment** to isolate dependencies
3. **Cache Playwright browser** in Docker builds
4. **Monitor security updates** for dependencies
5. **Test after updates** before deploying

## Size Considerations

Approximate sizes:
- Base Python packages: ~200MB
- GeoPandas + dependencies: ~150MB
- Playwright + Chromium: ~300MB
- **Total**: ~650MB

For smaller deployments, consider:
- Using Alpine Linux base image
- Removing unused dependencies
- Using slim Python images
