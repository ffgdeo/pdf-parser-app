# Handwritten PDF Document Parser

A Databricks App that uses `ai_parse_document` to extract text from handwritten PDF documents, allowing users to review, correct, and submit the parsed content to a Delta table.

## Features

- **Upload**: Upload PDF files directly through the web UI
- **Parse**: Automatically parse documents using Databricks `ai_parse_document` (powered by Foundation Model APIs)
- **Review**: View parsed text blocks, correct OCR errors (e.g., misread numbers), and approve content
- **Submit**: Write approved content to a bronze Delta table for downstream processing

## Architecture

```
User uploads PDF
    → Stored in UC Volume (/Volumes/fd_demo_workspace_catalog/pdf_parser/uploads/)
    → Parsed via ai_parse_document (SQL warehouse)
    → Text blocks displayed for review
    → Corrected content written to Delta table (fd_demo_workspace_catalog.pdf_parser.parsed_documents)
```

## Prerequisites

- Databricks workspace with serverless SQL warehouse
- Unity Catalog enabled
- DBR 17.1+ (required for `ai_parse_document`)

## Deployment

### 1. Create the app

```bash
databricks apps create pdf-parser-app --profile <your-profile>
```

### 2. Upload source code

```bash
databricks workspace mkdirs /Workspace/Users/<your-email>/apps/pdf-parser-app --profile <your-profile>
databricks workspace import-dir . /Workspace/Users/<your-email>/apps/pdf-parser-app --profile <your-profile>
```

### 3. Deploy

```bash
databricks apps deploy pdf-parser-app \
  --source-code-path /Workspace/Users/<your-email>/apps/pdf-parser-app \
  --profile <your-profile>
```

### 4. Add resources

In the Databricks Apps UI, add:
- **SQL warehouse** (key: `sql-warehouse`) — used for `ai_parse_document` and table operations

## Infrastructure Setup

The app expects the following Unity Catalog objects:

```sql
-- Schema
CREATE SCHEMA IF NOT EXISTS fd_demo_workspace_catalog.pdf_parser;

-- Volume for uploads
CREATE VOLUME IF NOT EXISTS fd_demo_workspace_catalog.pdf_parser.uploads;

-- Bronze table
CREATE TABLE IF NOT EXISTS fd_demo_workspace_catalog.pdf_parser.parsed_documents (
  id STRING NOT NULL,
  filename STRING NOT NULL,
  upload_ts TIMESTAMP NOT NULL,
  raw_parsed STRING,
  reviewed_text STRING,
  submitted_by STRING,
  submitted_ts TIMESTAMP
);
```

## Sample PDFs

The `sample_pdfs/` directory contains sample handwritten-style PDF documents for testing:

- `field_inspection_notes.pdf` — Building inspection field notes
- `patient_intake_form.pdf` — Doctor's office intake form
- `meeting_notes.pdf` — Handwritten meeting minutes
- `inventory_count_sheet.pdf` — Warehouse inventory count
- `expense_report.pdf` — Handwritten expense report

## Tech Stack

- **Framework**: Streamlit
- **Backend**: Databricks SQL Connector + SDK
- **AI**: `ai_parse_document` (built-in Databricks AI Function)
- **Storage**: Unity Catalog Volumes + Delta Lake
