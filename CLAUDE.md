# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Trap is a grease trap invoice/manifest parser. It extracts structured data from unstructured invoice text using regex patterns, with a Streamlit web interface.

## Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the web app
streamlit run app.py

# Run all tests
pytest

# Lint and format
ruff check .
ruff format .
```

## Architecture

```
app.py              # Streamlit web UI (imports from src/trap/)
src/trap/
  parse.py          # Parsing engine: parse_text_to_record() -> ParseResult
  main.py           # CLI entrypoint
tests/
  fixtures/         # Sample invoices for testing and demo
  test_parser.py    # Parser unit tests
```

**Key design principle:** Parsing logic lives in `src/trap/parse.py`, UI lives in `app.py`. They are kept separate so the parser can be reused (CLI, API, etc.) and tested independently.

## Parser API

```python
from trap.parse import parse_text_to_record

result = parse_text_to_record(invoice_text)
result.record           # ServiceRecord dataclass
result.extracted_fields # list of field names found
result.missing_fields   # list of field names not found
result.confidence_score # 0-100 based on coverage
result.to_dict()        # JSON-serializable dict
```
