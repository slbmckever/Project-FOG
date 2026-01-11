"""Smoke tests to verify basic functionality."""

import sys
from pathlib import Path

from trap import __version__
from trap.main import main

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_version() -> None:
    """Verify version is defined."""
    assert __version__ == "0.1.0"


def test_main_runs(capsys, monkeypatch) -> None:
    """Verify main function executes without error."""
    monkeypatch.setattr(sys, "argv", ["trap"])
    main()
    captured = capsys.readouterr()
    assert "Hello from Trap!" in captured.out


def test_main_with_input_file(capsys, monkeypatch) -> None:
    """Verify main reads input file correctly."""
    invoice_path = FIXTURES_DIR / "sample_invoice_1.txt"
    monkeypatch.setattr(sys, "argv", ["trap", "--input", str(invoice_path)])
    main()
    captured = capsys.readouterr()
    assert "GARDEN STATE GREASE SERVICES" in captured.out
    assert "Tony's Ristorante" in captured.out
    assert "1,320 gallons" in captured.out
