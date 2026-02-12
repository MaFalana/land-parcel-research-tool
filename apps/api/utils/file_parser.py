"""
Utility module for parsing parcel ID files in various formats (TXT, CSV, XLSX)
"""
import csv
import io
from typing import List
from fastapi import UploadFile, HTTPException


async def parse_parcel_file(file: UploadFile) -> List[str]:
    """
    Parse uploaded file and extract parcel IDs
    
    Supports:
    - TXT: One parcel ID per line
    - CSV: First column or column named "Parcel ID"
    - XLSX: First column or column named "Parcel ID"
    
    Args:
        file: Uploaded file object
        
    Returns:
        List of parcel ID strings
        
    Raises:
        HTTPException: If file format is invalid or parsing fails
    """
    file_ext = file.filename.split('.')[-1].lower()
    
    try:
        content = await file.read()
        
        if file_ext == 'txt':
            return parse_txt(content)
        elif file_ext == 'csv':
            return parse_csv(content)
        elif file_ext == 'xlsx':
            return parse_xlsx(content)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {file_ext}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse file: {str(e)}"
        )


def parse_txt(content: bytes) -> List[str]:
    """
    Parse TXT file - one parcel ID per line
    
    Args:
        content: File content as bytes
        
    Returns:
        List of parcel IDs
    """
    text = content.decode('utf-8')
    lines = text.strip().split('\n')
    
    # Filter out empty lines and strip whitespace
    parcel_ids = [line.strip() for line in lines if line.strip()]
    
    return parcel_ids


def parse_csv(content: bytes) -> List[str]:
    """
    Parse CSV file - first column or column named "Parcel ID"
    
    Args:
        content: File content as bytes
        
    Returns:
        List of parcel IDs
    """
    text = content.decode('utf-8')
    csv_file = io.StringIO(text)
    reader = csv.DictReader(csv_file)
    
    parcel_ids = []
    
    # Check if there's a "Parcel ID" column
    if reader.fieldnames and 'Parcel ID' in reader.fieldnames:
        for row in reader:
            parcel_id = row.get('Parcel ID', '').strip()
            if parcel_id:
                parcel_ids.append(parcel_id)
    else:
        # Fall back to first column
        csv_file.seek(0)
        reader = csv.reader(csv_file)
        
        # Skip header if it exists
        first_row = next(reader, None)
        if first_row and not is_parcel_id(first_row[0]):
            # First row is likely a header, skip it
            pass
        else:
            # First row is data, include it
            if first_row and first_row[0].strip():
                parcel_ids.append(first_row[0].strip())
        
        # Read remaining rows
        for row in reader:
            if row and row[0].strip():
                parcel_ids.append(row[0].strip())
    
    return parcel_ids


def parse_xlsx(content: bytes) -> List[str]:
    """
    Parse XLSX file - first column or column named "Parcel ID"
    
    Args:
        content: File content as bytes
        
    Returns:
        List of parcel IDs
    """
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="openpyxl library not installed. Cannot parse XLSX files."
        )
    
    # Load workbook from bytes
    workbook = openpyxl.load_workbook(io.BytesIO(content))
    sheet = workbook.active
    
    parcel_ids = []
    
    # Check if first row contains "Parcel ID" header
    first_row = [cell.value for cell in sheet[1]]
    parcel_col_idx = None
    
    if 'Parcel ID' in first_row:
        parcel_col_idx = first_row.index('Parcel ID')
        start_row = 2  # Skip header
    else:
        parcel_col_idx = 0  # Use first column
        start_row = 1
    
    # Extract parcel IDs
    for row in sheet.iter_rows(min_row=start_row, values_only=True):
        if row and len(row) > parcel_col_idx:
            parcel_id = str(row[parcel_col_idx]).strip() if row[parcel_col_idx] else ''
            if parcel_id and parcel_id != 'None':
                parcel_ids.append(parcel_id)
    
    return parcel_ids


def is_parcel_id(value: str) -> bool:
    """
    Heuristic to determine if a value looks like a parcel ID
    
    Parcel IDs typically contain numbers and may contain dashes or dots
    
    Args:
        value: String to check
        
    Returns:
        True if value looks like a parcel ID
    """
    if not value:
        return False
    
    # Check if it contains at least one digit
    has_digit = any(c.isdigit() for c in value)
    
    # Check if it's not a common header word
    common_headers = ['parcel', 'id', 'number', 'pin', 'property']
    is_header = value.lower().strip() in common_headers
    
    return has_digit and not is_header


def validate_parcel_ids(parcel_ids: List[str], max_count: int = 1000) -> List[str]:
    """
    Validate and clean parcel IDs
    
    Args:
        parcel_ids: List of parcel IDs to validate
        max_count: Maximum number of parcels allowed
        
    Returns:
        Cleaned list of parcel IDs
        
    Raises:
        HTTPException: If validation fails
    """
    if not parcel_ids:
        raise HTTPException(
            status_code=400,
            detail="No parcel IDs found in file"
        )
    
    if len(parcel_ids) > max_count:
        raise HTTPException(
            status_code=400,
            detail=f"Too many parcel IDs. Maximum allowed: {max_count}, found: {len(parcel_ids)}"
        )
    
    # Remove duplicates while preserving order
    seen = set()
    unique_parcels = []
    for parcel_id in parcel_ids:
        if parcel_id not in seen:
            seen.add(parcel_id)
            unique_parcels.append(parcel_id)
    
    return unique_parcels
