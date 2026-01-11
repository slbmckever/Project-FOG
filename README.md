# Trap CRM

A Salesforce-style CRM for FOG (Fats, Oils, Grease) service operators. Manage customers, sites, jobs, and documents with a modern dashboard interface.

## Features

- **Dashboard** - KPI tiles, charts, and recent activity overview
- **Customer Management** - Full CRUD for customer accounts
- **Job Tracking** - Parse invoices, manage service jobs, track status
- **Reports** - Revenue analytics, technician performance, customer insights
- **Invoice Parser** - Extract structured data from unstructured invoice text

## Quick Start

```bash
# 1. Create and activate virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the web app
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Pages

| Page | Description |
|------|-------------|
| **Dashboard** | KPIs (jobs, revenue, gallons), charts, recent jobs |
| **Customers** | Customer list, create/edit/view customers |
| **Jobs** | Job list with filters, create new jobs, parse invoices |
| **Reports** | Analytics tabs: Jobs, Revenue, Technicians |
| **Settings** | Database stats, reset database |

## Data Model

### Entities

| Entity | Description |
|--------|-------------|
| **Customer** | Business account (name, contact, address) |
| **Site** | Service location with trap specs |
| **Job** | Service event with parsed invoice data |
| **Document** | Attached files (invoices, manifests, photos) |

### Job Status Workflow

| Status | Description |
|--------|-------------|
| **Scheduled** | Future service appointment |
| **In Progress** | Technician currently on-site |
| **Completed** | Service finished, pending verification |
| **Verified** | All required fields confirmed |
| **Invoiced** | Invoice sent to customer |

## Data Storage

All data is stored in a local SQLite database at `data/trap.db`. This file is automatically created on first run.

**Note:** The database file is excluded from git.

### Reset Database

To clear all data and start fresh:

```bash
# Option 1: Delete the database file
rm data/trap.db

# Option 2: Use the Settings page in the app

# Option 3: Use Python
python -c "from trap.storage import reset_db; reset_db()"
```

### Backup

```bash
cp data/trap.db data/trap_backup_$(date +%Y%m%d).db
```

## Project Structure

```
Trap/
├── app.py                    # Streamlit CRM application
├── data/
│   ├── trap.db               # SQLite database (auto-created)
│   └── documents/            # Uploaded document storage
├── assets/
│   └── bg.mp4                # Background video (optional)
├── .streamlit/
│   └── config.toml           # Streamlit theme config
├── src/trap/
│   ├── __init__.py
│   ├── main.py               # CLI entrypoint
│   ├── models.py             # Data models (Customer, Site, Job, Document)
│   ├── parse.py              # Invoice parsing engine
│   └── storage.py            # SQLite persistence layer
├── tests/
│   ├── fixtures/             # Sample invoice files
│   ├── test_parser.py
│   ├── test_storage.py       # 58 tests for persistence layer
│   └── test_smoke.py
├── requirements.txt
└── pyproject.toml
```

## Run Tests

```bash
# Install test dependencies
pip install pytest ruff

# Run all tests (58 tests)
pytest

# Lint code
ruff check .

# Format code
ruff format .
```

## Dashboard KPIs

The dashboard displays these metrics:

| KPI | Description |
|-----|-------------|
| Jobs Completed | Count of completed/verified/invoiced jobs |
| Jobs Scheduled | Count of pending scheduled jobs |
| Total Revenue | Sum of all invoice totals |
| Gallons Pumped | Sum of all gallons serviced |
| Avg Revenue/Job | Average invoice amount |
| Overdue Services | Sites past their next service date |
| Active Customers | Total customer accounts |
| Active Sites | Total service locations |
| Avg Gallons/Job | Average gallons per service |
| Missing Docs | Jobs without attached invoice/manifest |

## Video Background (Optional)

For the full visual experience, add a background video:

1. Place your video file at `assets/bg.mp4`
2. Recommended: Industrial / blue-collar operations footage
3. Requirements: MP4 format, 1080p, 10-30 seconds loop

**Free video sources:**
- [Pexels](https://www.pexels.com/search/videos/industrial/)
- [Pixabay](https://pixabay.com/videos/search/industrial/)

If no video is present, the app displays an animated gradient background.

## CLI Usage

```bash
pip install -e .
python -m trap.main --input tests/fixtures/sample_invoice_1.txt
```

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app"
4. Select your repo, branch `main`, and main file `app.py`
5. Click "Deploy"

**Note:** The video background works locally but may not work on Streamlit Cloud due to file size limits.
