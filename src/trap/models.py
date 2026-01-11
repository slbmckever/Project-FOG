"""
Data models for the Trap CRM system.

Entities:
- Customer: Business/restaurant customer
- Site: Service location (trap location)
- Job: Service event record
- Document: Uploaded artifacts (invoices, manifests, photos)
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
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
    # Legacy statuses for backward compatibility
    DRAFT = "Draft"
    EXPORTED = "Exported"


class DocumentType(str, Enum):
    """Types of documents that can be attached to jobs."""

    INVOICE = "invoice"
    MANIFEST = "manifest"
    INSPECTION = "inspection"
    PHOTO = "photo"
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
    trap_type: str | None = None  # e.g., "Interior", "Exterior", "Interceptor"
    trap_size: str | None = None  # e.g., "1,500 gallons"
    trap_location: str | None = None  # e.g., "Behind building", "Kitchen floor"
    service_frequency: ServiceFrequency | None = None
    service_frequency_days: int | None = None  # Override for custom frequency
    last_service_date: datetime | None = None
    next_service_date: datetime | None = None
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
        return datetime.now() > self.next_service_date


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

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    scheduled_date: datetime | None = None

    # Source/parsing metadata
    source_filename: str | None = None
    confidence_score: int = 0
    extracted_fields: list = field(default_factory=list)
    missing_fields: list = field(default_factory=list)

    # Status
    status: JobStatus = JobStatus.DRAFT

    # Service record fields
    invoice_number: str | None = None
    manifest_number: str | None = None
    service_date: str | None = None
    customer_name: str | None = None
    customer_address: str | None = None
    phone: str | None = None
    trap_size: str | None = None
    gallons_pumped: str | None = None
    technician: str | None = None
    truck_id: str | None = None
    disposal_facility: str | None = None
    invoice_total: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        d = asdict(self)
        d["job_id"] = str(self.job_id)
        d["customer_id"] = str(self.customer_id) if self.customer_id else None
        d["site_id"] = str(self.site_id) if self.site_id else None
        d["created_at"] = self.created_at.isoformat()
        d["updated_at"] = self.updated_at.isoformat()
        if self.scheduled_date:
            d["scheduled_date"] = self.scheduled_date.isoformat()
        d["status"] = self.status.value
        return d

    @classmethod
    def from_parse_result(
        cls, result: ParseResult, source_filename: str | None = None
    ) -> "Job":
        """Create a Job from a ParseResult."""
        record = result.record
        return cls(
            source_filename=source_filename,
            confidence_score=result.confidence_score,
            extracted_fields=result.extracted_fields.copy(),
            missing_fields=result.missing_fields.copy(),
            invoice_number=record.invoice_number,
            service_date=record.service_date,
            customer_name=record.customer_name,
            customer_address=record.customer_address,
            phone=record.phone,
            trap_size=record.trap_size,
            gallons_pumped=record.gallons_pumped,
            technician=record.technician,
            disposal_facility=record.disposal_facility,
            invoice_total=record.invoice_total,
            notes=record.notes,
        )

    def can_verify(self) -> bool:
        """Check if job has all required fields filled to be verified."""
        required = [
            self.invoice_number,
            self.service_date,
            self.customer_name,
        ]
        return all(f is not None and str(f).strip() for f in required)

    def get_missing_required_fields(self) -> list[str]:
        """Return list of required fields that are missing."""
        missing = []
        if not self.invoice_number or not str(self.invoice_number).strip():
            missing.append("invoice_number")
        if not self.service_date or not str(self.service_date).strip():
            missing.append("service_date")
        if not self.customer_name or not str(self.customer_name).strip():
            missing.append("customer_name")
        return missing

    def get_record_dict(self) -> dict:
        """Get just the service record fields as a dict."""
        return {name: getattr(self, name) for name in RECORD_FIELD_NAMES}

    def get_gallons_numeric(self) -> float:
        """Parse gallons_pumped to numeric value."""
        if not self.gallons_pumped:
            return 0.0
        # Remove common suffixes and parse
        val = self.gallons_pumped.lower().replace("gallons", "").replace("gal", "")
        val = val.replace(",", "").strip()
        try:
            return float(val)
        except ValueError:
            return 0.0

    def get_total_numeric(self) -> float:
        """Parse invoice_total to numeric value."""
        if not self.invoice_total:
            return 0.0
        # Remove currency symbols and parse
        val = self.invoice_total.replace("$", "").replace(",", "").strip()
        try:
            return float(val)
        except ValueError:
            return 0.0


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
# ANALYTICS / KPI TYPES
# =============================================================================


@dataclass
class DashboardKPIs:
    """Container for dashboard KPI metrics."""

    jobs_completed: int = 0
    jobs_scheduled: int = 0
    jobs_in_progress: int = 0
    total_revenue: float = 0.0
    total_gallons: float = 0.0
    avg_revenue_per_job: float = 0.0
    avg_gallons_per_job: float = 0.0
    docs_missing_count: int = 0  # Jobs without manifest or invoice doc
    overdue_services: int = 0  # Sites past their next_service_date
    customer_count: int = 0
    site_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TimeSeriesPoint:
    """A single data point for time series charts."""

    date: str  # YYYY-MM-DD
    value: float
    label: str | None = None
