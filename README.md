# PDF Document Parser

A Databricks App that uses `ai_parse_document` to extract text and tables from PDF documents, lets users review and correct the output side-by-side with the original PDF, and writes validated content to a bronze Delta table for downstream processing.

## Features

- **Upload**: Upload PDF files directly through the web UI to a Unity Catalog Volume
- **Parse**: Automatically parse documents using `ai_parse_document` (powered by Foundation Model APIs)
- **Review side-by-side**: Original PDF rendered next to parsed blocks. Click 📍 on any block to highlight its bounding box on the PDF.
- **Edit**: Text blocks edit as plain text; tables edit as a spreadsheet (`st.data_editor`) so the column/row structure is preserved
- **Submit**: Write validated content to a bronze Delta table — both as human-readable markdown (`reviewed_text`) AND as typed JSON (`reviewed_blocks`) for deterministic downstream extraction

## Architecture

```
User uploads PDF
    → Stored in UC Volume (/Volumes/<catalog>/pdf_parser/uploads/)
    → Parsed via ai_parse_document (SQL warehouse)
    → Text blocks + tables displayed for review (with PDF preview + bbox highlights)
    → Validated content written to Delta table (<catalog>.pdf_parser.parsed_documents)
```

## Authentication

The app runs in **on-behalf-of-user (OBO) mode**. Each request executes as the logged-in user, so all SQL and UC Volume access is governed by that user's permissions — no service-principal grants required. The app reads the user's OAuth token from the `X-Forwarded-Access-Token` request header and passes it explicitly to the SQL connector and `WorkspaceClient`.

OAuth scopes required (configured in the app's UI Settings):
- `sql` — query the SQL warehouse, run `ai_parse_document`, write to bronze
- `files.files` — upload PDFs to UC Volumes

## Prerequisites

- Databricks workspace with a serverless SQL warehouse (DBR 17.1+ for `ai_parse_document`)
- Unity Catalog enabled
- Databricks Apps with **user authorization (OBO) preview** enabled at the workspace level

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

### 4. Bind the SQL warehouse resource

In the Databricks Apps UI (or via `apps update --json`), add:
- **SQL warehouse** resource with key `sql-warehouse` — used for `ai_parse_document` and table operations

### 5. Enable user authorization

In the app's UI Settings page, add OAuth scopes: `sql`, `files.files`. Save.

## Infrastructure Setup

The app expects the following Unity Catalog objects (replace `<catalog>` with your target catalog):

```sql
-- Schema
CREATE SCHEMA IF NOT EXISTS <catalog>.pdf_parser;

-- Volume for uploads
CREATE VOLUME IF NOT EXISTS <catalog>.pdf_parser.uploads;

-- Bronze table — stores the original parser JSON, the human-readable markdown,
-- AND the typed JSON of validated blocks (used by downstream notebooks).
CREATE TABLE IF NOT EXISTS <catalog>.pdf_parser.parsed_documents (
  id              STRING NOT NULL,
  filename        STRING NOT NULL,
  upload_ts       TIMESTAMP NOT NULL,
  raw_parsed      STRING,         -- original ai_parse_document JSON
  reviewed_text   STRING,         -- markdown rendering of validated blocks
  reviewed_blocks STRING,         -- JSON: [{type, content?, columns?, rows?}]
  submitted_by    STRING,
  submitted_ts    TIMESTAMP
);
```

The catalog name is configured at the top of `app.py`:

```python
CATALOG = "<catalog>"   # change to your target catalog
SCHEMA  = "pdf_parser"
VOLUME  = "uploads"
```

## Bronze schema details

| Column | Purpose |
|---|---|
| `raw_parsed` | The full JSON returned by `ai_parse_document`, kept for provenance. |
| `reviewed_text` | A markdown-formatted rendering of the validated blocks (`[TITLE]…`, `[TABLE] \| col \| col \|`, etc). Useful for humans, debugging, or quick LLM ingestion. |
| `reviewed_blocks` | Typed JSON array of validated blocks. Tables include `columns: array<string>` + `rows: array<map<string,string>>` so downstream notebooks can `from_json` and `EXPLODE` directly without re-parsing through an LLM. |

Downstream silver/gold pipelines should read `reviewed_blocks` for tabular data (deterministic) and reserve `ai_query` only for fields that genuinely require semantic extraction (header narrative, dates phrased multiple ways, etc.).

## Sample PDFs

The `sample_pdfs/` directory contains sample PDF documents for testing:

- `field_inspection_notes.pdf` — Building inspection field notes
- `patient_intake_form.pdf` — Patient intake form
- `meeting_notes.pdf` — Meeting minutes
- `inventory_count_sheet.pdf` — Warehouse inventory count
- `expense_report.pdf` — Expense report

## Tech Stack

- **Framework**: Streamlit
- **PDF rendering / annotations**: `streamlit-pdf-viewer`
- **Backend**: Databricks SQL Connector + SDK
- **AI**: `ai_parse_document` (built-in Databricks AI Function)
- **Storage**: Unity Catalog Volumes + Delta Lake
