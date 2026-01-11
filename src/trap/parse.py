"""
Grease trap invoice/manifest parser.

This module extracts structured data from unstructured invoice text.
It uses regex patterns to find common fields like customer name,
service date, gallons pumped, etc.

WHY THIS FILE EXISTS:
- Keeps parsing logic separate from the UI (app.py)
- Makes it easy to test the parser independently
- Allows reuse in CLI, web app, or future API
"""

import re
from dataclasses import asdict, dataclass, field

# All the fields we try to extract from an invoice
EXPECTED_FIELDS = [
    "invoice_number",
    "service_date",
    "customer_name",
    "customer_address",
    "phone",
    "trap_size",
    "gallons_pumped",
    "technician",
    "disposal_facility",
    "invoice_total",
]


@dataclass
class ServiceRecord:
    """
    A structured representation of a grease trap service invoice.

    WHY A DATACLASS:
    - Gives us a clear schema (what fields exist)
    - Easy to convert to dict/JSON
    - IDE autocomplete and type hints
    """

    invoice_number: str | None = None
    service_date: str | None = None
    customer_name: str | None = None
    customer_address: str | None = None
    phone: str | None = None
    trap_size: str | None = None
    gallons_pumped: str | None = None
    technician: str | None = None
    disposal_facility: str | None = None
    invoice_total: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class ParseResult:
    """
    The full result of parsing an invoice.

    Contains the extracted record plus metadata about
    what was found/missing and a confidence score.
    """

    record: ServiceRecord
    extracted_fields: list = field(default_factory=list)
    missing_fields: list = field(default_factory=list)
    confidence_score: int = 0  # 0-100

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dictionary."""
        return {
            "record": self.record.to_dict(),
            "extracted_fields": self.extracted_fields,
            "missing_fields": self.missing_fields,
            "confidence_score": self.confidence_score,
        }


def parse_text_to_record(text: str) -> ParseResult:
    """
    Parse invoice/manifest text and extract structured fields.

    HOW IT WORKS:
    1. Run regex patterns against the text for each field
    2. Track which fields we found vs. missed
    3. Calculate a confidence score based on coverage

    Args:
        text: Raw invoice text (can be messy, multi-line)

    Returns:
        ParseResult with the extracted record and metadata
    """
    if not text or not text.strip():
        return ParseResult(
            record=ServiceRecord(),
            extracted_fields=[],
            missing_fields=EXPECTED_FIELDS.copy(),
            confidence_score=0,
        )

    # Normalize text: handle encoding issues, normalize whitespace
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    record = ServiceRecord()
    extracted = []

    # --- INVOICE NUMBER ---
    # Patterns: "INVOICE #: XXX", "Invoice No: XXX", "Inv #XXX"
    invoice_match = re.search(
        r"(?:INVOICE|INV)(?:\s*(?:NO|#|\.)|:|\s)+[:\s]*([A-Z0-9\-]+)",
        text,
        re.IGNORECASE,
    )
    if invoice_match:
        record.invoice_number = invoice_match.group(1).strip()
        extracted.append("invoice_number")

    # --- SERVICE DATE ---
    # Patterns: "Service Date: XXX", "DATE: XXX", dates like "January 8, 2026"
    date_pattern = (
        r"(?:Service Date|DATE)[\s:]+"
        r"([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
    )
    date_match = re.search(date_pattern, text, re.IGNORECASE)
    if date_match:
        record.service_date = date_match.group(1).strip()
        extracted.append("service_date")

    # --- CUSTOMER NAME ---
    # Look for "BILL TO:" section, grab first non-empty line after
    bill_to_match = re.search(r"BILL TO[:\s]*\n\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    if bill_to_match:
        name = bill_to_match.group(1).strip()
        # Skip if it's "Attn:" line
        if not name.lower().startswith("attn"):
            record.customer_name = name
            extracted.append("customer_name")

    # --- CUSTOMER ADDRESS ---
    # Look for address pattern (number + street name + city/state/zip)
    address_match = re.search(
        r"(\d+\s+[\w\s]+(?:Avenue|Ave|Street|St|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Parkway|Pkwy)[\s,]+[\w\s]+,?\s*[A-Z]{2}\s*\d{5})",
        text,
        re.IGNORECASE,
    )
    if address_match:
        record.customer_address = address_match.group(1).strip()
        extracted.append("customer_address")

    # --- PHONE ---
    # Pattern: (XXX) XXX-XXXX or XXX-XXX-XXXX
    phone_match = re.search(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", text)
    if phone_match:
        record.phone = phone_match.group(0).strip()
        extracted.append("phone")

    # --- TRAP SIZE ---
    # Patterns: "Trap Size: 1,500 gallons", "1500 gal trap"
    trap_match = re.search(
        r"(?:Trap Size|Trap Capacity)[\s:]+([0-9,]+\s*(?:gallons?|gal))",
        text,
        re.IGNORECASE,
    )
    if trap_match:
        record.trap_size = trap_match.group(1).strip()
        extracted.append("trap_size")

    # --- GALLONS PUMPED ---
    # Patterns: "Gallons Pumped: 1,320", "pumped 1320 gallons"
    gallons_match = re.search(
        r"(?:Gallons? Pumped|Pumped)[\s:]+([0-9,]+)\s*(?:gallons?|gal)?",
        text,
        re.IGNORECASE,
    )
    if gallons_match:
        record.gallons_pumped = gallons_match.group(1).strip() + " gallons"
        extracted.append("gallons_pumped")

    # --- TECHNICIAN ---
    # Patterns: "Technician: John Smith", "Tech: J. Smith"
    tech_match = re.search(
        r"(?:Technician|Tech)[\s:]+([A-Za-z\s.]+?)(?:\n|$|Truck)", text, re.IGNORECASE
    )
    if tech_match:
        record.technician = tech_match.group(1).strip()
        extracted.append("technician")

    # --- DISPOSAL FACILITY ---
    # Patterns: "Disposal Facility: XXX", look for treatment/facility names
    disposal_match = re.search(
        r"(?:Disposal (?:Facility|Site)|Disposed at)[\s:]+(.+?)(?:\n|$)",
        text,
        re.IGNORECASE,
    )
    if disposal_match:
        record.disposal_facility = disposal_match.group(1).strip()
        extracted.append("disposal_facility")

    # --- INVOICE TOTAL ---
    # Patterns: "TOTAL: $XXX", "TOTAL DUE: $XXX", "Amount Due: $XXX"
    total_match = re.search(
        r"(?:TOTAL(?: DUE)?|Amount Due|Grand Total)[\s:]+\$?([\d,]+\.?\d*)",
        text,
        re.IGNORECASE,
    )
    if total_match:
        record.invoice_total = "$" + total_match.group(1).strip()
        extracted.append("invoice_total")

    # Calculate missing fields
    missing = [f for f in EXPECTED_FIELDS if f not in extracted]

    # Calculate confidence score (0-100)
    # Based on percentage of expected fields found
    confidence = int((len(extracted) / len(EXPECTED_FIELDS)) * 100)

    return ParseResult(
        record=record,
        extracted_fields=extracted,
        missing_fields=missing,
        confidence_score=confidence,
    )
