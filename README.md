# Trap

A grease trap invoice/manifest parser with a Streamlit web interface.

Upload or paste invoice text → get structured JSON/CSV data.

## Quick Start (Local)

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

## Run Tests

```bash
# Install test dependencies
pip install pytest ruff

# Run all tests
pytest

# Run with verbose output
pytest -v

# Lint code
ruff check .

# Format code
ruff format .
```

## Project Structure

```
Trap/
├── app.py                 # Streamlit web UI
├── src/trap/
│   ├── __init__.py
│   ├── main.py            # CLI entrypoint
│   └── parse.py           # Parsing engine (regex extraction)
├── tests/
│   ├── fixtures/          # Sample invoice files
│   │   ├── sample_invoice_1.txt
│   │   └── sample_invoice_2.txt
│   ├── test_parser.py     # Parser tests
│   └── test_smoke.py      # Basic smoke tests
├── requirements.txt       # Deployment dependencies
└── pyproject.toml         # Project config
```

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app"
4. Select your repo, branch `main`, and main file `app.py`
5. Click "Deploy"

The app will be live at `https://<your-app>.streamlit.app`

## CLI Usage

```bash
# Install package
pip install -e .

# Parse a file from command line
python -m trap.main --input tests/fixtures/sample_invoice_1.txt
```
