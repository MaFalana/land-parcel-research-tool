# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Wells County Beacon property record scraper that automates downloading Property Record Cards (PRCs) from the Wells County Beacon website. The tool processes Excel workbooks containing parcel information, downloads corresponding PDF property records, extracts key data (legal description, latest deed date, document numbers), and updates the Excel file with this information.

## Architecture

### Core Components
- **main.py**: Primary script that orchestrates the workflow - reads Excel data, searches Beacon site using Playwright, downloads PDFs
- **ocr.py**: OCR functionality using Tesseract for extracting text from PDF images  
- **pdf.py**: PDF parsing utilities using pdfplumber for extracting table data
- **play.py**: Development/testing file

### Key Dependencies
- **playwright**: Browser automation for navigating Beacon site
- **openpyxl**: Excel file manipulation
- **requests**: HTTP requests for downloading PDFs
- **beautifulsoup4**: HTML parsing
- **pytesseract/pdf2image**: OCR capabilities
- **pdfplumber/pypdf**: PDF parsing

## Common Commands

```bash
# Install dependencies
python3 -m venv .beaconV2
source .beaconV2/bin/activate
pip install -r requirements.txt
python -m playwright install

# Run the main scraper
python main.py
```

## Development Guidelines

### From spec/Coding Preferences.md:
- Start every response with a random emoji
- Follow KISS, DRY, YAGNI, and SOLID principles
- Keep files under 200-300 lines
- After major features, generate docs in /docs/[feature].md
- Never overwrite .env without explicit confirmation

### From spec/Communication Preferences.md:
- Provide brief summaries after each component
- Classify changes as Small/Medium/Large
- For Large changes, outline plan and wait for approval
- Track completed vs pending features

### From spec/Workflow Preferences.md:
- Reference and update /docs/TASKS.md and /docs/PLAN.md throughout session
- Break complex tasks into stages with review checkpoints
- Write thorough tests for major functionality
- If context exceeds 100k tokens, summarize to Context-Summary.md

## Key Requirements

1. **Excel Processing**: 
   - Data starts from row 3, spans columns A-R
   - Column A: Parcel ID, Column B: Owner name
   - Preserve formatting of first two rows
   - Update "Downloaded" column checkbox after processing

2. **PDF Processing**:
   - Download newest Property Record Card (not Tax Statements)
   - Extract: legal description, latest deed date (MM/DD/YYYY format), document number
   - For document numbers: prefer document # over book/page, use what's available
   - Rename PDFs: replace "_0" suffix with owner's last name (ignore business suffixes like LLC/INC)
   - Save to PRC directory

3. **Beacon Navigation**:
   - URL: `https://beacon.schneidercorp.com/Application.aspx?AppID=173&LayerID=2165&PageTypeID=2&PageID=1119`
   - Find "Property Record Cards" section (not Tax Statements)
   - Select newest year available (2025, or latest if 2025 not available)

## Tech Stack (from spec/Technical Stack.md)
- Backend: Python
- Version Control: Github  
- CI/CD: Github Actions