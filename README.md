# Bank Statement Analyzer
**SOP-Compliant: Comprehensive Bank Statement Analysis**

## Overview
Analyzes UOB bank statement PDFs and generates structured PDF reports following the SOP:
1. **Ingest & Verify** — OCR or native text extraction + balance validation
2. **Normalize & Structure** — Schema mapping, merchant cleaning, debit/credit resolution
3. **Analyse** — Category breakdown, anomaly detection
4. **Report** — Clean PDF with 6 sections

## Requirements
```bash
pip install pdfplumber pandas reportlab pdf2image pytesseract pymupdf
# Also requires: tesseract-ocr poppler-utils (system packages)
sudo apt install tesseract-ocr poppler-utils
```

## Usage
```bash
python main.py <path_to_bank_statement.pdf>
```

**Examples:**
```bash
python main.py statements/uob_feb2025.pdf
python main.py statements/fernandez_may2025.pdf
```

Reports are saved to the `output/` folder automatically.

## Output Report Sections
| Section | Content |
|---------|---------|
| Cover   | Account info, period, generation timestamp |
| §1      | Balance verification (Opening → Closing reconciliation) |
| §2      | Financial summary (total credits, debits, averages) |
| §3      | Spending breakdown by category |
| §4      | Full transaction ledger with clean merchant names |
| §5      | Anomaly flags (duplicates, large debits, subscription spikes) |
| §6      | Quality gate pass/fail |

## Project Structure
```
bank_analyzer/
├── main.py                  # Entry point (CLI)
├── config.py                # Category rules & thresholds
├── modules/
│   ├── ingestion.py         # Phase 1: PDF extraction + OCR + validation
│   ├── normalizer.py        # Phase 2: Schema mapping + merchant cleaning
│   ├── analyzer.py          # Phase 3: Categorisation + anomaly detection
│   └── report_generator.py  # Phase 4: PDF report builder
├── statements/              # Place input PDFs here
└── output/                  # Generated reports saved here
```

## Configuration (`config.py`)
- `ANOMALY_THRESHOLD_PCT` — % of monthly spend to flag large debits (default: 20%)
- `DUPLICATE_WINDOW_HOURS` — Window for duplicate detection (default: 24h)
- `CATEGORY_RULES` — Keyword-based category assignment rules
- `NOISE_PATTERNS` — Regex patterns to strip from merchant descriptions

## Supported PDF Types
- **Scanned / Image PDFs** → Automatically detected, OCR applied via Tesseract
- **Digital / Native PDFs** → Text extracted directly via pdfplumber
