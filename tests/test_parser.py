"""
Tests for the grease trap invoice parser.

WHY THIS FILE EXISTS:
- Ensures the parser extracts expected fields correctly
- Catches regressions when we improve patterns
- Validates JSON serialization works
"""

import json
from pathlib import Path

from trap.parse import parse_text_to_record

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_result_is_json_serializable():
    """The parse result must convert to JSON without errors."""
    text = "INVOICE #: TEST-001\nTOTAL DUE: $100.00"
    result = parse_text_to_record(text)

    # This should not raise
    json_str = json.dumps(result.to_dict())
    assert isinstance(json_str, str)

    # Round-trip: parse the JSON back
    parsed = json.loads(json_str)
    assert parsed["record"]["invoice_number"] == "TEST-001"
    assert parsed["record"]["invoice_total"] == "$100.00"


def test_parse_sample_invoice_1():
    """Parse the first sample invoice (Garden State Grease Services)."""
    text = (FIXTURES_DIR / "sample_invoice_1.txt").read_text()
    result = parse_text_to_record(text)

    record = result.record

    # Check key fields were extracted
    assert record.invoice_number == "GS-2024-003471"
    assert record.service_date == "January 8, 2026"
    assert record.customer_name == "Tony's Ristorante"
    assert record.trap_size == "1,500 gallons"
    assert record.gallons_pumped == "1,320 gallons"
    assert record.technician == "Marcus Williams"
    assert record.invoice_total == "$568.40"

    # Should have good confidence (most fields found)
    assert result.confidence_score >= 70


def test_parse_sample_invoice_2():
    """Parse the second sample invoice (Jersey Shore Pumping)."""
    text = (FIXTURES_DIR / "sample_invoice_2.txt").read_text()
    result = parse_text_to_record(text)

    record = result.record

    # Check key fields
    assert record.invoice_number == "JSP-10294"
    assert "03/15/2026" in record.service_date or "2026" in (record.service_date or "")
    assert record.customer_name == "Seaside Diner"
    assert record.trap_size == "1,000 gallons"
    assert record.gallons_pumped == "850 gallons"
    assert record.invoice_total == "$377.00"

    # Should still have decent confidence
    assert result.confidence_score >= 50


def test_parse_empty_text():
    """Empty input should return empty result, not crash."""
    result = parse_text_to_record("")

    assert result.record.invoice_number is None
    assert result.confidence_score == 0
    assert len(result.missing_fields) > 0
    assert len(result.extracted_fields) == 0


def test_parse_garbage_text():
    """Random garbage should return empty result, not crash."""
    result = parse_text_to_record("asdfghjkl 12345 !!@#$%")

    assert result.confidence_score < 20
    # Should still be serializable
    json.dumps(result.to_dict())


def test_extracted_and_missing_fields_are_disjoint():
    """A field should be in extracted OR missing, never both."""
    text = (FIXTURES_DIR / "sample_invoice_1.txt").read_text()
    result = parse_text_to_record(text)

    extracted_set = set(result.extracted_fields)
    missing_set = set(result.missing_fields)

    # No overlap
    assert extracted_set.isdisjoint(missing_set)

    # Together they should cover all expected fields
    from trap.parse import EXPECTED_FIELDS

    assert extracted_set | missing_set == set(EXPECTED_FIELDS)
