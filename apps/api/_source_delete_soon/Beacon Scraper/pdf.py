import pdfplumber
import re
from datetime import datetime

PDF_file = './references/90-08-04-539-402.001-004_0 copy.pdf'  # Path to your PDF file

def main():
    data = parse_pdf(PDF_file)
    print("\nExtracted Data:")
    print(f"Legal Description: {data['legal_description']}")
    print(f"Latest Deed Date: {data['latest_deed_date']}")
    print(f"Document Number: {data['document_number']}")
    print(f"Book/Page: {data['book_page']}")

def parse_pdf(file):
    """Parse PDF to extract Legal Description and Transfer of Ownership information"""
    
    extracted_data = {
        'legal_description': '',
        'latest_deed_date': '',
        'document_number': '',
        'book_page': ''
    }
    
    full_text = ""
    
    with pdfplumber.open(file) as pdf:
        # Extract text from all pages
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"
    
    # Debug: Print full text to understand structure
    print("=== FULL PDF TEXT ===")
    print(full_text[:2000])  # First 2000 chars
    print("=== END SAMPLE ===\n")
    
    # Extract Legal Description
    # Look for patterns like "Legal Desc:" or "Legal Description" 
    legal_patterns = [
        r'Legal\s+Desc(?:ription)?[:\s]+([^\n]+(?:\n(?!\w+:)[^\n]+)*)',
        r'LEGAL\s+DESCRIPTION[:\s]+([^\n]+(?:\n(?!\w+:)[^\n]+)*)',
        r'Legal[:\s]+([^\n]+(?:\n(?!\w+:)[^\n]+)*)'
    ]
    
    for pattern in legal_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE)
        if match:
            extracted_data['legal_description'] = match.group(1).strip()
            break
    
    # Extract Transfer/Deed information
    # Look for transfer history section or deed date patterns
    transfer_patterns = [
        r'Transfer\s+Date[:\s]+(\d{1,2}/\d{1,2}/\d{4})',
        r'Deed\s+Date[:\s]+(\d{1,2}/\d{1,2}/\d{4})',
        r'Sale\s+Date[:\s]+(\d{1,2}/\d{1,2}/\d{4})',
        r'Recording\s+Date[:\s]+(\d{1,2}/\d{1,2}/\d{4})'
    ]
    
    # Find all dates and get the most recent
    deed_dates = []
    for pattern in transfer_patterns:
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        deed_dates.extend(matches)
    
    if deed_dates:
        # Convert to datetime objects and find the latest
        date_objects = []
        for date_str in deed_dates:
            try:
                date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                date_objects.append((date_obj, date_str))
            except:
                pass
        
        if date_objects:
            latest_date = max(date_objects, key=lambda x: x[0])
            extracted_data['latest_deed_date'] = latest_date[1]
    
    # Extract Document Number
    doc_patterns = [
        r'Document\s+(?:Number|#)[:\s]+(\d+[-\d]*)',
        r'Doc\s+(?:Number|#)[:\s]+(\d+[-\d]*)',
        r'Instrument\s+(?:Number|#)[:\s]+(\d+[-\d]*)'
    ]
    
    for pattern in doc_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            extracted_data['document_number'] = match.group(1).strip()
            break
    
    # Extract Book/Page if no document number found
    if not extracted_data['document_number']:
        book_page_pattern = r'Book[:\s]+(\d+)[,\s]+Page[:\s]+(\d+)'
        match = re.search(book_page_pattern, full_text, re.IGNORECASE)
        if match:
            extracted_data['book_page'] = f"{match.group(1)}/{match.group(2)}"
    
    return extracted_data

if __name__ == "__main__":
    main()