"""
Data models for the Trap CRM system.

Entities:
- Customer: Business/restaurant customer
- Site: Service location (trap location)
- Asset: The trap/interceptor itself
- Job: Service event record
- Document: Uploaded artifacts (invoices, manifests, photos)

Data Typing:
- Money stored as cents (int) for precision
- Dates stored as datetime objects
- Gallons stored as float
"""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from .parse import ParseResult


# =============================================================================
# ENUMS
# =============================================================================


class JobStatus(str, Enum):
    """Workflow status for a job."""

    SCHEDULED = "Scheduled"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    VERIFIED = "Verified"
    INVOICED = "Invoiced"
    NEEDS_DOCS = "Needs Docs"
    REJECTED = "Rejected"
    # Legacy statuses for backward compatibility
    DRAFT = "Draft"
    EXPORTED = "Exported"


class DocumentType(str, Enum):
    """Types of documents that can be attached to jobs."""

    INVOICE = "invoice"
    MANIFEST = "manifest"
    INSPECTION = "inspection"
    PHOTO = "photo"
    SIGNATURE = "signature"
    OTHER = "other"


class ServiceFrequency(str, Enum):
    """Common service frequencies."""

    WEEKLY = "Weekly"
    BIWEEKLY = "Bi-Weekly"
    MONTHLY = "Monthly"
    QUARTERLY = "Quarterly"
    SEMIANNUAL = "Semi-Annual"
    ANNUAL = "Annual"
    ON_CALL = "On Call"


class TrapType(str, Enum):
    """Types of grease traps/interceptors."""

    INTERIOR = "Interior"
    EXTERIOR = "Exterior"
    INTERCEPTOR = "Interceptor"
    UNDERGROUND = "Underground"


class PaymentStatus(str, Enum):
    """Payment status for invoices."""

    DRAFT = "Draft"
    SENT = "Sent"
    PAID = "Paid"
    OVERDUE = "Overdue"


# =============================================================================
# CUSTOMER
# =============================================================================


@dataclass
class Customer:
    """
    A customer/business that receives grease trap services.

    Customers can have multiple sites (service locations).
    """

    customer_id: UUID = field(default_factory=uuid4)
    name: str = ""  # Display name / DBA
    legal_name: str | None = None  # Legal business name
    phone: str | None = None
    email: str | None = None
    billing_address: str | None = None
    service_address: str | None = None  # Default service address
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    notes: str | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        d = asdict(self)
        d["customer_id"] = str(self.customer_id)
        d["created_at"] = self.created_at.isoformat()
        d["updated_at"] = self.updated_at.isoformat()
        return d

    @property
    def display_name(self) -> str:
        """Get display name for UI."""
        return self.name or self.legal_name or "Unnamed Customer"

    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = []
        if self.service_address:
            parts.append(self.service_address)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.zip_code:
            parts.append(self.zip_code)
        return ", ".join(parts) if parts else ""


# =============================================================================
# SITE / LOCATION
# =============================================================================


@dataclass
class Site:
    """
    A specific service location for a customer.

    A customer may have multiple sites (e.g., multiple restaurant locations).
    Each site has its own trap specifications and service schedule.
    """

    site_id: UUID = field(default_factory=uuid4)
    customer_id: UUID | None = None
    name: str = ""  # Location nickname (e.g., "Main Kitchen", "Store #42")
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    # Regulatory info
    municipality: str | None = None
    sewer_authority: str | None = None
    permit_number: str | None = None
    # Service scheduling
    service_frequency: ServiceFrequency | None = None
    service_frequency_days: int | None = None  # Override for custom frequency
    last_service_date: date | None = None
    next_service_date: date | None = None
    # Notes
    access_notes: str | None = None  # How to access the trap
    notes: str | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        d = asdict(self)
        d["site_id"] = str(self.site_id)
        d["customer_id"] = str(self.customer_id) if self.customer_id else None
        d["created_at"] = self.created_at.isoformat()
        d["updated_at"] = self.updated_at.isoformat()
        if self.last_service_date:
            d["last_service_date"] = self.last_service_date.isoformat()
        if self.next_service_date:
            d["next_service_date"] = self.next_service_date.isoformat()
        if self.service_frequency:
            d["service_frequency"] = self.service_frequency.value
        return d

    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = []
        if self.address:
            parts.append(self.address)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.zip_code:
            parts.append(self.zip_code)
        return ", ".join(parts) if parts else ""

    def is_service_overdue(self) -> bool:
        """Check if site is overdue for service."""
        if not self.next_service_date:
            return False
        return date.today() > self.next_service_date


# =============================================================================
# ASSET (TRAP/INTERCEPTOR)
# =============================================================================


@dataclass
class Asset:
    """
    A grease trap or interceptor at a site.

    A site can have multiple assets (e.g., indoor + outdoor traps).
    """

    asset_id: UUID = field(default_factory=uuid4)
    site_id: UUID | None = None
    name: str = ""  # e.g., "Main Trap", "Kitchen #1"
    trap_type: TrapType | None = None
    trap_size_gallons: int | None = None  # Capacity in gallons
    trap_location: str | None = None  # e.g., "Behind building", "Kitchen floor"
    serial_number: str | None = None
    install_date: date | None = None
    manufacturer: str | None = None
    # Service requirements
    required_frequency_days: int | None = None
    last_service_date: date | None = None
    next_service_date: date | None = None
    notes: str | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        d = asdict(self)
        d["asset_id"] = str(self.asset_id)
        d["site_id"] = str(self.site_id) if self.site_id else None
        d["created_at"] = self.created_at.isoformat()
        d["updated_at"] = self.updated_at.isoformat()
        if self.trap_type:
            d["trap_type"] = self.trap_type.value
        if self.install_date:
            d["install_date"] = self.install_date.isoformat()
        if self.last_service_date:
            d["last_service_date"] = self.last_service_date.isoformat()
        if self.next_service_date:
            d["next_service_date"] = self.next_service_date.isoformat()
        return d

    def is_service_overdue(self) -> bool:
        """Check if asset is overdue for service."""
        if not self.next_service_date:
            return False
        return date.today() > self.next_service_date


# =============================================================================
# JOB / SERVICE EVENT
# =============================================================================

# Field definitions for UI rendering: (field_name, label, input_type, required)
SERVICE_RECORD_FIELDS = [
    ("invoice_number", "Invoice Number", "text", True),
    ("service_date", "Service Date", "date", True),
    ("customer_name", "Customer Name", "text", True),
    ("customer_address", "Customer Address", "text", False),
    ("phone", "Phone", "text", False),
    ("trap_size", "Trap Size", "text", False),
    ("gallons_pumped", "Gallons Pumped", "number", False),
    ("technician", "Technician", "text", False),
    ("disposal_facility", "Disposal Facility", "text", False),
    ("invoice_total", "Invoice Total", "currency", False),
    ("manifest_number", "Manifest Number", "text", False),
    ("truck_id", "Truck ID", "text", False),
    ("notes", "Notes", "textarea", False),
]

# Just the field names for convenience
RECORD_FIELD_NAMES = [f[0] for f in SERVICE_RECORD_FIELDS]


@dataclass
class Job:
    """
    A service event / job record.

    Represents a single grease trap service visit including
    all captured data from invoices/manifests.
    """

    # Identifiers
    job_id: UUID = field(default_factory=uuid4)
    customer_id: UUID | None = None
    site_id: UUID | None = None
    asset_id: UUID | None = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    scheduled_date: date | None = None
    service_date: date | None = None  # Actual service date (typed)

    # Source/parsing metadata
    source_filename: str | None = None
    confidence_score: int = 0
    extracted_fields: list = field(default_factory=list)
    missing_fields: list = field(default_factory=list)

    # Status
    status: JobStatus = JobStatus.DRAFT

    # Service record fields (legacy string fields for backward compat)
    invoice_number: str | None = None
    manifest_number: str | None = None
    service_date_str: str | None = None  # Original string from parsing
    customer_name: str | None = None
    customer_address: str | None = None
    phone: str | None = None
    trap_size: str | None = None

    # Typed fields
    gallons_pumped: float | None = None  # Gallons as float
    invoice_total_cents: int | None = None  # Money as cents

    # Legacy string fields (for parsing/display)
    gallons_pumped_str: str | None = None
    invoice_total_str: str | None = None

    technician: str | None = None
    truck_id: str | None = None
    disposal_facility: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        d = asdict(self)
        d["job_id"] = str(self.job_id)
        d["customer_id"] = str(self.customer_id) if self.customer_id else None
        d["site_id"] = str(self.site_id) if self.site_id else None
        d["asset_id"] = str(self.asset_id) if self.asset_id else None
        d["created_at"] = self.created_at.isoformat()
        d["updated_at"] = self.updated_at.isoformat()
        if self.scheduled_date:
            d["scheduled_date"] = self.scheduled_date.isoformat()
        if self.service_date:
            d["service_date"] = self.service_date.isoformat()
        d["status"] = self.status.value
        # Include formatted values for convenience
        d["invoice_total"] = self.get_invoice_total_display()
        d["gallons_display"] = self.get_gallons_display()
        return d

    @classmethod
    def from_parse_result(
        cls, result: ParseResult, source_filename: str | None = None
    ) -> "Job":
        """Create a Job from a ParseResult."""
        record = result.record
        job = cls(
            source_filename=source_filename,
            confidence_score=result.confidence_score,
            extracted_fields=result.extracted_fields.copy(),
            missing_fields=result.missing_fields.copy(),
            invoice_number=record.invoice_number,
            service_date_str=record.service_date,
            customer_name=record.customer_name,
            customer_address=record.customer_address,
            phone=record.phone,
            trap_size=record.trap_size,
            gallons_pumped_str=record.gallons_pumped,
            invoice_total_str=record.invoice_total,
            technician=record.technician,
            disposal_facility=record.disposal_facility,
            notes=record.notes,
        )
        # Parse typed values
        job.gallons_pumped = job._parse_gallons(record.gallons_pumped)
        job.invoice_total_cents = job._parse_money(record.invoice_total)
        job.service_date = job._parse_date(record.service_date)
        return job

    @staticmethod
    def _parse_gallons(value: str | None) -> float | None:
        """Parse gallons string to float."""
        if not value:
            return None
        val = value.lower().replace("gallons", "").replace("gal", "")
        val = val.replace(",", "").strip()
        try:
            return float(val)
        except ValueError:
            return None

    @staticmethod
    def _parse_money(value: str | None) -> int | None:
        """Parse money string to cents."""
        if not value:
            return None
        val = value.replace("$", "").replace(",", "").strip()
        try:
            return int(float(val) * 100)
        except ValueError:
            return None

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        """Parse date string to date object."""
        if not value:
            return None
        # Try common formats
        formats = ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%B %d, %Y", "%b %d, %Y"]
        for fmt in formats:
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def can_verify(self) -> bool:
        """Check if job has all required fields filled to be verified."""
        required = [
            self.invoice_number,
            self.service_date or self.service_date_str,
            self.customer_name,
        ]
        return all(f is not None and str(f).strip() for f in required)

    def get_missing_required_fields(self) -> list[str]:
        """Return list of required fields that are missing."""
        missing = []
        if not self.invoice_number or not str(self.invoice_number).strip():
            missing.append("invoice_number")
        if not (self.service_date or self.service_date_str):
            missing.append("service_date")
        if not self.customer_name or not str(self.customer_name).strip():
            missing.append("customer_name")
        return missing

    def get_record_dict(self) -> dict:
        """Get just the service record fields as a dict."""
        return {name: getattr(self, name, None) for name in RECORD_FIELD_NAMES}

    def get_gallons_display(self) -> str:
        """Get formatted gallons for display."""
        if self.gallons_pumped:
            return f"{self.gallons_pumped:,.0f} gal"
        return self.gallons_pumped_str or "—"

    def get_invoice_total_display(self) -> str:
        """Get formatted invoice total for display."""
        if self.invoice_total_cents:
            return f"${self.invoice_total_cents / 100:,.2f}"
        return self.invoice_total_str or "—"

    def get_service_date_display(self) -> str:
        """Get formatted service date for display."""
        if self.service_date:
            return self.service_date.strftime("%b %d, %Y")
        return self.service_date_str or "—"


# =============================================================================
# DOCUMENT / ARTIFACT
# =============================================================================


@dataclass
class Document:
    """
    A document or file attached to a job.

    Examples: scanned invoices, manifests, inspection reports, photos.
    """

    doc_id: UUID = field(default_factory=uuid4)
    job_id: UUID | None = None
    doc_type: DocumentType = DocumentType.OTHER
    filename: str = ""
    original_filename: str | None = None
    file_size: int = 0
    mime_type: str | None = None
    stored_path: str | None = None  # Path in data/documents/
    # Parsing results (if parsed)
    parsed_fields: dict = field(default_factory=dict)
    confidence: int = 0
    notes: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        d = asdict(self)
        d["doc_id"] = str(self.doc_id)
        d["job_id"] = str(self.job_id) if self.job_id else None
        d["doc_type"] = self.doc_type.value
        d["created_at"] = self.created_at.isoformat()
        return d


# =============================================================================
# JOB PACKET (COMPLETENESS TRACKING)
# =============================================================================


@dataclass
class JobPacket:
    """
    Tracks completeness of a job's document packet.

    A complete packet typically requires: invoice + manifest + inspection.
    """

    job_id: UUID
    has_invoice: bool = False
    has_manifest: bool = False
    has_inspection: bool = False
    has_photos: bool = False
    has_signature: bool = False

    @property
    def completeness_percentage(self) -> int:
        """Calculate packet completeness (invoice + manifest = 100%)."""
        required = [self.has_invoice, self.has_manifest]
        complete = sum(required)
        return int((complete / len(required)) * 100)

    @property
    def is_complete(self) -> bool:
        """Check if packet has all required documents."""
        return self.has_invoice and self.has_manifest

    def to_dict(self) -> dict:
        return {
            "job_id": str(self.job_id),
            "has_invoice": self.has_invoice,
            "has_manifest": self.has_manifest,
            "has_inspection": self.has_inspection,
            "has_photos": self.has_photos,
            "has_signature": self.has_signature,
            "completeness_percentage": self.completeness_percentage,
            "is_complete": self.is_complete,
        }


# =============================================================================
# ANALYTICS / KPI TYPES
# =============================================================================


@dataclass
class DashboardKPIs:
    """Container for dashboard KPI metrics."""

    jobs_completed: int = 0
    jobs_scheduled: int = 0
    jobs_in_progress: int = 0
    total_revenue_cents: int = 0  # Money as cents
    total_gallons: float = 0.0
    avg_revenue_per_job_cents: int = 0
    avg_gallons_per_job: float = 0.0
    docs_missing_count: int = 0  # Jobs without manifest or invoice doc
    overdue_services: int = 0  # Sites past their next_service_date
    customer_count: int = 0
    site_count: int = 0

    # Legacy properties for backward compat
    @property
    def total_revenue(self) -> float:
        return self.total_revenue_cents / 100

    @property
    def avg_revenue_per_job(self) -> float:
        return self.avg_revenue_per_job_cents / 100

    def to_dict(self) -> dict:
        d = asdict(self)
        d["total_revenue"] = self.total_revenue
        d["avg_revenue_per_job"] = self.avg_revenue_per_job
        return d


@dataclass
class TimeSeriesPoint:
    """A single data point for time series charts."""

    date: str  # YYYY-MM-DD
    value: float
    label: str | None = None
