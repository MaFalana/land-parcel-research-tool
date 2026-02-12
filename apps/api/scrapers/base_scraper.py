"""
Base scraper class for GIS platforms
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Callable, Optional
import pandas as pd


class BaseScraper(ABC):
    """Abstract base class for GIS platform scrapers"""
    
    def __init__(self):
        self.platform_name = "Unknown"
    
    @abstractmethod
    def scrape_parcels(
        self,
        parcel_file_path: str,
        base_url: str,
        county: str,
        job_id: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict:
        """
        Scrape parcel data from GIS portal
        
        Args:
            parcel_file_path: Path to file containing parcel IDs
            base_url: GIS portal base URL
            county: County name
            job_id: Job ID for organizing output files
            progress_callback: Optional callback function(completed, total)
            
        Returns:
            Dict with:
                - excel_path: Path to enriched Excel file
                - pdfs_dir: Directory containing downloaded PDFs
                - parcel_count: Number of parcels processed
                - failed_count: Number of parcels that failed
        """
        pass
    
    def read_parcel_ids(self, file_path: str) -> List[str]:
        """
        Read parcel IDs from file (TXT, CSV, or XLSX)
        
        Args:
            file_path: Path to parcel file
            
        Returns:
            List of parcel ID strings
        """
        ext = file_path.split('.')[-1].lower()
        
        if ext == 'txt':
            with open(file_path, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        
        elif ext == 'csv':
            df = pd.read_csv(file_path)
            # Try to find parcel ID column
            for col in df.columns:
                if 'parcel' in col.lower() and 'id' in col.lower():
                    return df[col].dropna().astype(str).str.strip().tolist()
            # Use first column
            return df.iloc[:, 0].dropna().astype(str).str.strip().tolist()
        
        elif ext in ['xlsx', 'xls']:
            df = pd.read_excel(file_path)
            # Try to find parcel ID column
            for col in df.columns:
                if 'parcel' in str(col).lower() and 'id' in str(col).lower():
                    return df[col].dropna().astype(str).str.strip().tolist()
            # Use first column
            return df.iloc[:, 0].dropna().astype(str).str.strip().tolist()
        
        else:
            raise ValueError(f"Unsupported file format: {ext}")
