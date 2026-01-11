"""
SQLite persistence layer for Trap CRM.

Provides CRUD operations for:
- Customers
- Sites
- Jobs
- Documents

Plus analytics/KPI queries for the dashboard.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import UUID

from .models import (
    Customer,
    DashboardKPIs,
    Document,
    DocumentType,
    Job,
    JobStatus,
    ServiceFrequency,
    Site,
    TimeSeriesPoint,
)

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "trap.db"
DOCUMENTS_DIR = Path(__file__).parent.parent.parent / "data" / "documents"


def get_db_path() -> Path:
    """Get the database path, creating the directory if needed."""
    db_path = DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_documents_dir() -> Path:
    """Get documents directory, creating if needed."""
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    return DOCUMENTS_DIR


@contextmanager
def get_connection(db_path: Path | None = None):
    """Context manager for database connections."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# =============================================================================
# DATABASE MIGRATIONS
# =============================================================================


def _migrate_sites_table(conn: sqlite3.Connection) -> None:
    """Add new columns to sites table if they don't exist."""
    cursor = conn.execute("PRAGMA table_info(sites)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    migrations = [
        ("municipality", "TEXT"),
        ("sewer_authority", "TEXT"),
        ("permit_number", "TEXT"),
        ("access_notes", "TEXT"),
    ]

    for col_name, col_type in migrations:
        if col_name not in existing_columns:
            conn.execute(f"ALTER TABLE sites ADD COLUMN {col_name} {col_type}")


def _migrate_jobs_table(conn: sqlite3.Connection) -> None:
    """Add new columns to jobs table if they don't exist."""
    cursor = conn.execute("PRAGMA table_info(jobs)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    migrations = [
        ("asset_id", "TEXT"),
        ("gallons_pumped_float", "REAL"),
        ("invoice_total_cents", "INTEGER"),
        ("service_date_typed", "TEXT"),
    ]

    for col_name, col_type in migrations:
        if col_name not in existing_columns:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}")


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================


def init_db(db_path: Path | None = None) -> None:
    """Initialize the database schema with all tables."""
    with get_connection(db_path) as conn:
        # Customers table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                legal_name TEXT,
                phone TEXT,
                email TEXT,
                billing_address TEXT,
                service_address TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                notes TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Sites table (enhanced with regulatory/compliance fields)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sites (
                site_id TEXT PRIMARY KEY,
                customer_id TEXT,
                name TEXT NOT NULL,
                address TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                municipality TEXT,
                sewer_authority TEXT,
                permit_number TEXT,
                service_frequency TEXT,
                service_frequency_days INTEGER,
                last_service_date TEXT,
                next_service_date TEXT,
                access_notes TEXT,
                notes TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            )
        """)

        # Add new columns if they don't exist (migration)
        _migrate_sites_table(conn)

        # Jobs table (extended from original)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                customer_id TEXT,
                site_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                scheduled_date TEXT,
                source_filename TEXT,
                confidence_score INTEGER DEFAULT 0,
                extracted_fields TEXT,
                missing_fields TEXT,
                status TEXT NOT NULL DEFAULT 'Draft',
                invoice_number TEXT,
                manifest_number TEXT,
                service_date TEXT,
                customer_name TEXT,
                customer_address TEXT,
                phone TEXT,
                trap_size TEXT,
                gallons_pumped TEXT,
                technician TEXT,
                truck_id TEXT,
                disposal_facility TEXT,
                invoice_total TEXT,
                notes TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (site_id) REFERENCES sites(site_id)
            )
        """)

        # Add new columns if they don't exist (migration)
        _migrate_jobs_table(conn)

        # Documents table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                job_id TEXT,
                doc_type TEXT NOT NULL DEFAULT 'other',
                filename TEXT NOT NULL,
                original_filename TEXT,
                file_size INTEGER DEFAULT 0,
                mime_type TEXT,
                stored_path TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            )
        """)

        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_customers_active ON customers(is_active)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sites_customer ON sites(customer_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sites_next_service ON sites(next_service_date)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_customer ON jobs(customer_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_service_date ON jobs(service_date)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_job ON documents(job_id)")


def reset_db(db_path: Path | None = None) -> None:
    """Drop and recreate all tables. WARNING: Destroys all data."""
    path = db_path or get_db_path()
    if path.exists():
        path.unlink()
    init_db(db_path)


# =============================================================================
# CUSTOMER OPERATIONS
# =============================================================================


def _row_to_customer(row: sqlite3.Row) -> Customer:
    """Convert a database row to a Customer object."""
    return Customer(
        customer_id=UUID(row["customer_id"]),
        name=row["name"],
        legal_name=row["legal_name"],
        phone=row["phone"],
        email=row["email"],
        billing_address=row["billing_address"],
        service_address=row["service_address"],
        city=row["city"],
        state=row["state"],
        zip_code=row["zip_code"],
        notes=row["notes"],
        is_active=bool(row["is_active"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def save_customer(customer: Customer, db_path: Path | None = None) -> Customer:
    """Save a customer (insert or update)."""
    customer.updated_at = datetime.now()

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO customers (
                customer_id, name, legal_name, phone, email,
                billing_address, service_address, city, state, zip_code,
                notes, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(customer.customer_id),
                customer.name,
                customer.legal_name,
                customer.phone,
                customer.email,
                customer.billing_address,
                customer.service_address,
                customer.city,
                customer.state,
                customer.zip_code,
                customer.notes,
                1 if customer.is_active else 0,
                customer.created_at.isoformat(),
                customer.updated_at.isoformat(),
            ),
        )
    return customer


def get_customer(
    customer_id: UUID | str, db_path: Path | None = None
) -> Customer | None:
    """Get a customer by ID."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE customer_id = ?", (str(customer_id),)
        ).fetchone()
        if row:
            return _row_to_customer(row)
    return None


def list_customers(
    search: str | None = None,
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
    db_path: Path | None = None,
) -> list[Customer]:
    """List customers with optional filtering."""
    with get_connection(db_path) as conn:
        query = "SELECT * FROM customers WHERE 1=1"
        params: list = []

        if active_only:
            query += " AND is_active = 1"

        if search:
            query += " AND (name LIKE ? OR legal_name LIKE ? OR email LIKE ?)"
            pattern = f"%{search}%"
            params.extend([pattern, pattern, pattern])

        query += " ORDER BY name ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [_row_to_customer(row) for row in rows]


def update_customer(
    customer_id: UUID | str, updates: dict, db_path: Path | None = None
) -> Customer | None:
    """Update specific fields on a customer."""
    customer = get_customer(customer_id, db_path)
    if not customer:
        return None

    for key, value in updates.items():
        if hasattr(customer, key):
            setattr(customer, key, value)

    return save_customer(customer, db_path)


def delete_customer(customer_id: UUID | str, db_path: Path | None = None) -> bool:
    """Soft-delete a customer (set is_active=False)."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE customers SET is_active = 0, updated_at = ? WHERE customer_id = ?",
            (datetime.now().isoformat(), str(customer_id)),
        )
        return cursor.rowcount > 0


def count_customers(active_only: bool = True, db_path: Path | None = None) -> int:
    """Count customers."""
    with get_connection(db_path) as conn:
        if active_only:
            row = conn.execute(
                "SELECT COUNT(*) FROM customers WHERE is_active = 1"
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) FROM customers").fetchone()
        return row[0] if row else 0


# =============================================================================
# SITE OPERATIONS
# =============================================================================


def _row_to_site(row: sqlite3.Row) -> Site:
    """Convert a database row to a Site object."""
    from datetime import date as date_type

    freq = None
    if row["service_frequency"]:
        try:
            freq = ServiceFrequency(row["service_frequency"])
        except ValueError:
            pass

    # Helper to safely get column (for migration compatibility)
    def safe_get(col: str) -> str | None:
        try:
            return row[col]
        except (IndexError, KeyError):
            return None

    # Parse dates as date objects
    last_service = None
    if row["last_service_date"]:
        dt = datetime.fromisoformat(row["last_service_date"])
        last_service = dt.date() if hasattr(dt, "date") else dt

    next_service = None
    if row["next_service_date"]:
        dt = datetime.fromisoformat(row["next_service_date"])
        next_service = dt.date() if hasattr(dt, "date") else dt

    return Site(
        site_id=UUID(row["site_id"]),
        customer_id=UUID(row["customer_id"]) if row["customer_id"] else None,
        name=row["name"],
        address=row["address"],
        city=row["city"],
        state=row["state"],
        zip_code=row["zip_code"],
        municipality=safe_get("municipality"),
        sewer_authority=safe_get("sewer_authority"),
        permit_number=safe_get("permit_number"),
        service_frequency=freq,
        service_frequency_days=row["service_frequency_days"],
        last_service_date=last_service,
        next_service_date=next_service,
        access_notes=safe_get("access_notes"),
        notes=row["notes"],
        is_active=bool(row["is_active"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def save_site(site: Site, db_path: Path | None = None) -> Site:
    """Save a site (insert or update)."""
    site.updated_at = datetime.now()

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO sites (
                site_id, customer_id, name, address, city, state, zip_code,
                municipality, sewer_authority, permit_number,
                service_frequency, service_frequency_days,
                last_service_date, next_service_date,
                access_notes, notes, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(site.site_id),
                str(site.customer_id) if site.customer_id else None,
                site.name,
                site.address,
                site.city,
                site.state,
                site.zip_code,
                site.municipality,
                site.sewer_authority,
                site.permit_number,
                site.service_frequency.value if site.service_frequency else None,
                site.service_frequency_days,
                site.last_service_date.isoformat() if site.last_service_date else None,
                site.next_service_date.isoformat() if site.next_service_date else None,
                site.access_notes,
                site.notes,
                1 if site.is_active else 0,
                site.created_at.isoformat(),
                site.updated_at.isoformat(),
            ),
        )
    return site


def get_site(site_id: UUID | str, db_path: Path | None = None) -> Site | None:
    """Get a site by ID."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM sites WHERE site_id = ?", (str(site_id),)
        ).fetchone()
        if row:
            return _row_to_site(row)
    return None


def list_sites(
    customer_id: UUID | str | None = None,
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
    db_path: Path | None = None,
) -> list[Site]:
    """List sites with optional filtering."""
    with get_connection(db_path) as conn:
        query = "SELECT * FROM sites WHERE 1=1"
        params: list = []

        if active_only:
            query += " AND is_active = 1"

        if customer_id:
            query += " AND customer_id = ?"
            params.append(str(customer_id))

        query += " ORDER BY name ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [_row_to_site(row) for row in rows]


def list_overdue_sites(db_path: Path | None = None) -> list[Site]:
    """List sites that are overdue for service."""
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM sites
            WHERE is_active = 1
              AND next_service_date IS NOT NULL
              AND next_service_date < ?
            ORDER BY next_service_date ASC
            """,
            (now,),
        ).fetchall()
        return [_row_to_site(row) for row in rows]


def count_sites(active_only: bool = True, db_path: Path | None = None) -> int:
    """Count sites."""
    with get_connection(db_path) as conn:
        if active_only:
            row = conn.execute(
                "SELECT COUNT(*) FROM sites WHERE is_active = 1"
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) FROM sites").fetchone()
        return row[0] if row else 0


# =============================================================================
# JOB OPERATIONS
# =============================================================================


def _row_to_job(row: sqlite3.Row) -> Job:
    """Convert a database row to a Job object."""
    from datetime import date as date_type

    # Helper to safely get column (for migration compatibility)
    def safe_get(col: str):
        try:
            return row[col]
        except (IndexError, KeyError):
            return None

    # Parse scheduled_date as date
    scheduled = None
    if row["scheduled_date"]:
        dt = datetime.fromisoformat(row["scheduled_date"])
        scheduled = dt.date() if hasattr(dt, "date") else dt

    # Parse service_date as date
    service_dt = None
    service_str = row["service_date"]
    if service_str:
        try:
            dt = datetime.fromisoformat(service_str)
            service_dt = dt.date() if hasattr(dt, "date") else dt
        except ValueError:
            # Keep as string in service_date_str
            pass

    # Parse gallons
    gallons_str = row["gallons_pumped"]
    gallons_float = None
    if gallons_str:
        try:
            val = gallons_str.lower().replace("gallons", "").replace("gal", "")
            val = val.replace(",", "").strip()
            gallons_float = float(val)
        except (ValueError, AttributeError):
            pass

    # Parse invoice total
    invoice_str = row["invoice_total"]
    invoice_cents = None
    if invoice_str:
        try:
            val = invoice_str.replace("$", "").replace(",", "").strip()
            invoice_cents = int(float(val) * 100)
        except (ValueError, AttributeError):
            pass

    return Job(
        job_id=UUID(row["job_id"]),
        customer_id=UUID(row["customer_id"]) if row["customer_id"] else None,
        site_id=UUID(row["site_id"]) if row["site_id"] else None,
        asset_id=UUID(safe_get("asset_id")) if safe_get("asset_id") else None,
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        scheduled_date=scheduled,
        service_date=service_dt,
        service_date_str=service_str,
        source_filename=row["source_filename"],
        confidence_score=row["confidence_score"] or 0,
        extracted_fields=(
            json.loads(row["extracted_fields"]) if row["extracted_fields"] else []
        ),
        missing_fields=(
            json.loads(row["missing_fields"]) if row["missing_fields"] else []
        ),
        status=JobStatus(row["status"]),
        invoice_number=row["invoice_number"],
        manifest_number=row["manifest_number"],
        customer_name=row["customer_name"],
        customer_address=row["customer_address"],
        phone=row["phone"],
        trap_size=row["trap_size"],
        gallons_pumped=gallons_float,
        gallons_pumped_str=gallons_str,
        invoice_total_cents=invoice_cents,
        invoice_total_str=invoice_str,
        technician=row["technician"],
        truck_id=row["truck_id"],
        disposal_facility=row["disposal_facility"],
        notes=row["notes"],
    )


def save_job(job: Job, db_path: Path | None = None) -> Job:
    """Save a job (insert or update)."""
    job.updated_at = datetime.now()

    # Convert typed values to strings for database storage
    # Prefer typed value, fall back to string value
    service_date_db = None
    if job.service_date:
        service_date_db = job.service_date.isoformat()
    elif job.service_date_str:
        service_date_db = job.service_date_str

    gallons_db = None
    if job.gallons_pumped is not None:
        gallons_db = f"{job.gallons_pumped:,.0f} gallons"
    elif job.gallons_pumped_str:
        gallons_db = job.gallons_pumped_str

    invoice_db = None
    if job.invoice_total_cents is not None:
        invoice_db = f"${job.invoice_total_cents / 100:,.2f}"
    elif job.invoice_total_str:
        invoice_db = job.invoice_total_str

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO jobs (
                job_id, customer_id, site_id, created_at, updated_at,
                scheduled_date, source_filename, confidence_score,
                extracted_fields, missing_fields, status,
                invoice_number, manifest_number, service_date, customer_name,
                customer_address, phone, trap_size, gallons_pumped,
                technician, truck_id, disposal_facility, invoice_total, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(job.job_id),
                str(job.customer_id) if job.customer_id else None,
                str(job.site_id) if job.site_id else None,
                job.created_at.isoformat(),
                job.updated_at.isoformat(),
                job.scheduled_date.isoformat() if job.scheduled_date else None,
                job.source_filename,
                job.confidence_score,
                json.dumps(job.extracted_fields),
                json.dumps(job.missing_fields),
                job.status.value,
                job.invoice_number,
                job.manifest_number,
                service_date_db,
                job.customer_name,
                job.customer_address,
                job.phone,
                job.trap_size,
                gallons_db,
                job.technician,
                job.truck_id,
                job.disposal_facility,
                invoice_db,
                job.notes,
            ),
        )
    return job


def load_job(job_id: UUID | str, db_path: Path | None = None) -> Job | None:
    """Load a job by ID."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (str(job_id),)
        ).fetchone()
        if row:
            return _row_to_job(row)
    return None


def list_jobs(
    status: JobStatus | None = None,
    customer_id: UUID | str | None = None,
    technician: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db_path: Path | None = None,
) -> list[Job]:
    """List jobs with optional filtering."""
    with get_connection(db_path) as conn:
        query = "SELECT * FROM jobs WHERE 1=1"
        params: list = []

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if customer_id:
            query += " AND customer_id = ?"
            params.append(str(customer_id))

        if technician:
            query += " AND technician LIKE ?"
            params.append(f"%{technician}%")

        if search:
            query += " AND (customer_name LIKE ? OR invoice_number LIKE ?)"
            pattern = f"%{search}%"
            params.extend([pattern, pattern])

        if date_from:
            query += " AND service_date >= ?"
            params.append(date_from)

        if date_to:
            query += " AND service_date <= ?"
            params.append(date_to)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [_row_to_job(row) for row in rows]


def update_job(
    job_id: UUID | str, updates: dict, db_path: Path | None = None
) -> Job | None:
    """Update specific fields on a job."""
    job = load_job(job_id, db_path)
    if not job:
        return None

    for key, value in updates.items():
        if hasattr(job, key):
            if key == "status" and isinstance(value, str):
                value = JobStatus(value)
            setattr(job, key, value)

    return save_job(job, db_path)


def delete_job(job_id: UUID | str, db_path: Path | None = None) -> bool:
    """Delete a job."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM jobs WHERE job_id = ?", (str(job_id),))
        return cursor.rowcount > 0


def count_jobs(
    status: JobStatus | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db_path: Path | None = None,
) -> int:
    """Count jobs with optional filtering."""
    with get_connection(db_path) as conn:
        query = "SELECT COUNT(*) FROM jobs WHERE 1=1"
        params: list = []

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if date_from:
            query += " AND service_date >= ?"
            params.append(date_from)

        if date_to:
            query += " AND service_date <= ?"
            params.append(date_to)

        row = conn.execute(query, params).fetchone()
        return row[0] if row else 0


def get_unique_technicians(db_path: Path | None = None) -> list[str]:
    """Get list of unique technician names."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT technician FROM jobs
            WHERE technician IS NOT NULL AND technician != ''
            ORDER BY technician
            """
        ).fetchall()
        return [row["technician"] for row in rows]


# =============================================================================
# DOCUMENT OPERATIONS
# =============================================================================


def _row_to_document(row: sqlite3.Row) -> Document:
    """Convert a database row to a Document object."""
    return Document(
        doc_id=UUID(row["doc_id"]),
        job_id=UUID(row["job_id"]) if row["job_id"] else None,
        doc_type=DocumentType(row["doc_type"]),
        filename=row["filename"],
        original_filename=row["original_filename"],
        file_size=row["file_size"] or 0,
        mime_type=row["mime_type"],
        stored_path=row["stored_path"],
        notes=row["notes"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def save_document(
    job_id: UUID | str,
    doc_type: DocumentType,
    file_bytes: bytes,
    filename: str,
    mime_type: str | None = None,
    db_path: Path | None = None,
) -> Document:
    """Save a document file and create database record."""
    doc = Document(
        job_id=UUID(str(job_id)),
        doc_type=doc_type,
        filename=filename,
        original_filename=filename,
        file_size=len(file_bytes),
        mime_type=mime_type,
        created_at=datetime.now(),
    )

    # Save file to disk
    docs_dir = get_documents_dir()
    stored_filename = f"{doc.doc_id}_{filename}"
    stored_path = docs_dir / stored_filename
    stored_path.write_bytes(file_bytes)
    doc.stored_path = str(stored_path)

    # Save to database
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO documents (
                doc_id, job_id, doc_type, filename, original_filename,
                file_size, mime_type, stored_path, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(doc.doc_id),
                str(doc.job_id),
                doc.doc_type.value,
                doc.filename,
                doc.original_filename,
                doc.file_size,
                doc.mime_type,
                doc.stored_path,
                doc.notes,
                doc.created_at.isoformat(),
            ),
        )

    return doc


def list_documents(
    job_id: UUID | str | None = None,
    doc_type: DocumentType | None = None,
    db_path: Path | None = None,
) -> list[Document]:
    """List documents with optional filtering."""
    with get_connection(db_path) as conn:
        query = "SELECT * FROM documents WHERE 1=1"
        params: list = []

        if job_id:
            query += " AND job_id = ?"
            params.append(str(job_id))

        if doc_type:
            query += " AND doc_type = ?"
            params.append(doc_type.value)

        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [_row_to_document(row) for row in rows]


def get_document(doc_id: UUID | str, db_path: Path | None = None) -> Document | None:
    """Get a document by ID."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE doc_id = ?", (str(doc_id),)
        ).fetchone()
        if row:
            return _row_to_document(row)
    return None


def delete_document(doc_id: UUID | str, db_path: Path | None = None) -> bool:
    """Delete a document (file and record)."""
    doc = get_document(doc_id, db_path)
    if not doc:
        return False

    # Delete file if exists
    if doc.stored_path:
        path = Path(doc.stored_path)
        if path.exists():
            path.unlink()

    # Delete record
    with get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM documents WHERE doc_id = ?", (str(doc_id),))
        return cursor.rowcount > 0


# =============================================================================
# ANALYTICS / KPI QUERIES
# =============================================================================


def get_dashboard_kpis(
    date_from: str | None = None,
    date_to: str | None = None,
    customer_id: UUID | str | None = None,
    technician: str | None = None,
    db_path: Path | None = None,
) -> DashboardKPIs:
    """Compute dashboard KPIs with optional filters."""
    kpis = DashboardKPIs()

    with get_connection(db_path) as conn:
        # Build base WHERE clause
        where = "WHERE 1=1"
        params: list = []

        if date_from:
            where += " AND service_date >= ?"
            params.append(date_from)
        if date_to:
            where += " AND service_date <= ?"
            params.append(date_to)
        if customer_id:
            where += " AND customer_id = ?"
            params.append(str(customer_id))
        if technician:
            where += " AND technician LIKE ?"
            params.append(f"%{technician}%")

        # Jobs completed
        row = conn.execute(
            f"SELECT COUNT(*) FROM jobs {where} AND status IN ('Completed', 'Verified', 'Invoiced', 'Exported')",
            params,
        ).fetchone()
        kpis.jobs_completed = row[0] if row else 0

        # Jobs scheduled
        row = conn.execute(
            f"SELECT COUNT(*) FROM jobs {where} AND status = 'Scheduled'", params
        ).fetchone()
        kpis.jobs_scheduled = row[0] if row else 0

        # Jobs in progress
        row = conn.execute(
            f"SELECT COUNT(*) FROM jobs {where} AND status = 'In Progress'", params
        ).fetchone()
        kpis.jobs_in_progress = row[0] if row else 0

        # Revenue and gallons (need to parse string values)
        rows = conn.execute(
            f"SELECT invoice_total, gallons_pumped FROM jobs {where}", params
        ).fetchall()

        total_revenue = 0.0
        total_gallons = 0.0
        job_count = 0

        for row in rows:
            job_count += 1
            # Parse invoice_total
            if row["invoice_total"]:
                val = row["invoice_total"].replace("$", "").replace(",", "").strip()
                try:
                    total_revenue += float(val)
                except ValueError:
                    pass
            # Parse gallons_pumped
            if row["gallons_pumped"]:
                val = (
                    row["gallons_pumped"]
                    .lower()
                    .replace("gallons", "")
                    .replace("gal", "")
                    .replace(",", "")
                    .strip()
                )
                try:
                    total_gallons += float(val)
                except ValueError:
                    pass

        kpis.total_revenue_cents = int(total_revenue * 100)
        kpis.total_gallons = total_gallons

        if job_count > 0:
            kpis.avg_revenue_per_job_cents = int((total_revenue / job_count) * 100)
            kpis.avg_gallons_per_job = total_gallons / job_count

        # Docs missing (jobs without invoice or manifest document)
        row = conn.execute(
            f"""
            SELECT COUNT(*) FROM jobs j {where}
            AND NOT EXISTS (
                SELECT 1 FROM documents d
                WHERE d.job_id = j.job_id
                AND d.doc_type IN ('invoice', 'manifest')
            )
            """,
            params,
        ).fetchone()
        kpis.docs_missing_count = row[0] if row else 0

        # Overdue services
        now = datetime.now().isoformat()
        row = conn.execute(
            """
            SELECT COUNT(*) FROM sites
            WHERE is_active = 1
              AND next_service_date IS NOT NULL
              AND next_service_date < ?
            """,
            (now,),
        ).fetchone()
        kpis.overdue_services = row[0] if row else 0

        # Customer and site counts
        row = conn.execute(
            "SELECT COUNT(*) FROM customers WHERE is_active = 1"
        ).fetchone()
        kpis.customer_count = row[0] if row else 0

        row = conn.execute("SELECT COUNT(*) FROM sites WHERE is_active = 1").fetchone()
        kpis.site_count = row[0] if row else 0

    return kpis


def get_jobs_by_date(
    date_from: str,
    date_to: str,
    group_by: str = "day",  # day, week, month
    db_path: Path | None = None,
) -> list[TimeSeriesPoint]:
    """Get job counts grouped by date."""
    with get_connection(db_path) as conn:
        if group_by == "month":
            date_expr = "substr(service_date, 1, 7)"  # YYYY-MM
        elif group_by == "week":
            date_expr = "strftime('%Y-W%W', service_date)"
        else:
            date_expr = "substr(service_date, 1, 10)"  # YYYY-MM-DD

        rows = conn.execute(
            f"""
            SELECT {date_expr} as period, COUNT(*) as count
            FROM jobs
            WHERE service_date >= ? AND service_date <= ?
            GROUP BY period
            ORDER BY period
            """,
            (date_from, date_to),
        ).fetchall()

        return [TimeSeriesPoint(date=row["period"], value=row["count"]) for row in rows]


def get_revenue_by_date(
    date_from: str,
    date_to: str,
    group_by: str = "day",
    db_path: Path | None = None,
) -> list[TimeSeriesPoint]:
    """Get revenue totals grouped by date."""
    with get_connection(db_path) as conn:
        if group_by == "month":
            date_expr = "substr(service_date, 1, 7)"
        elif group_by == "week":
            date_expr = "strftime('%Y-W%W', service_date)"
        else:
            date_expr = "substr(service_date, 1, 10)"

        rows = conn.execute(
            f"""
            SELECT {date_expr} as period, invoice_total
            FROM jobs
            WHERE service_date >= ? AND service_date <= ?
            ORDER BY period
            """,
            (date_from, date_to),
        ).fetchall()

        # Aggregate by period
        aggregates: dict[str, float] = {}
        for row in rows:
            period = row["period"]
            if period not in aggregates:
                aggregates[period] = 0.0
            if row["invoice_total"]:
                val = row["invoice_total"].replace("$", "").replace(",", "").strip()
                try:
                    aggregates[period] += float(val)
                except ValueError:
                    pass

        return [
            TimeSeriesPoint(date=period, value=value)
            for period, value in sorted(aggregates.items())
        ]


def get_gallons_by_date(
    date_from: str,
    date_to: str,
    group_by: str = "day",
    db_path: Path | None = None,
) -> list[TimeSeriesPoint]:
    """Get gallons pumped totals grouped by date."""
    with get_connection(db_path) as conn:
        if group_by == "month":
            date_expr = "substr(service_date, 1, 7)"
        elif group_by == "week":
            date_expr = "strftime('%Y-W%W', service_date)"
        else:
            date_expr = "substr(service_date, 1, 10)"

        rows = conn.execute(
            f"""
            SELECT {date_expr} as period, gallons_pumped
            FROM jobs
            WHERE service_date >= ? AND service_date <= ?
            ORDER BY period
            """,
            (date_from, date_to),
        ).fetchall()

        # Aggregate by period
        aggregates: dict[str, float] = {}
        for row in rows:
            period = row["period"]
            if period not in aggregates:
                aggregates[period] = 0.0
            if row["gallons_pumped"]:
                val = (
                    row["gallons_pumped"]
                    .lower()
                    .replace("gallons", "")
                    .replace("gal", "")
                    .replace(",", "")
                    .strip()
                )
                try:
                    aggregates[period] += float(val)
                except ValueError:
                    pass

        return [
            TimeSeriesPoint(date=period, value=value)
            for period, value in sorted(aggregates.items())
        ]


def get_jobs_by_status(
    date_from: str | None = None,
    date_to: str | None = None,
    db_path: Path | None = None,
) -> dict[str, int]:
    """Get job counts by status."""
    with get_connection(db_path) as conn:
        where = "WHERE 1=1"
        params: list = []

        if date_from:
            where += " AND service_date >= ?"
            params.append(date_from)
        if date_to:
            where += " AND service_date <= ?"
            params.append(date_to)

        rows = conn.execute(
            f"""
            SELECT status, COUNT(*) as count
            FROM jobs {where}
            GROUP BY status
            """,
            params,
        ).fetchall()

        return {row["status"]: row["count"] for row in rows}


def get_jobs_by_technician(
    date_from: str | None = None,
    date_to: str | None = None,
    db_path: Path | None = None,
) -> dict[str, int]:
    """Get job counts by technician."""
    with get_connection(db_path) as conn:
        where = "WHERE technician IS NOT NULL AND technician != ''"
        params: list = []

        if date_from:
            where += " AND service_date >= ?"
            params.append(date_from)
        if date_to:
            where += " AND service_date <= ?"
            params.append(date_to)

        rows = conn.execute(
            f"""
            SELECT technician, COUNT(*) as count
            FROM jobs {where}
            GROUP BY technician
            ORDER BY count DESC
            """,
            params,
        ).fetchall()

        return {row["technician"]: row["count"] for row in rows}


def get_top_customers_by_revenue(
    limit: int = 10,
    date_from: str | None = None,
    date_to: str | None = None,
    db_path: Path | None = None,
) -> list[tuple[str, float]]:
    """Get top customers by revenue."""
    with get_connection(db_path) as conn:
        where = "WHERE customer_name IS NOT NULL"
        params: list = []

        if date_from:
            where += " AND service_date >= ?"
            params.append(date_from)
        if date_to:
            where += " AND service_date <= ?"
            params.append(date_to)

        rows = conn.execute(
            f"""
            SELECT customer_name, invoice_total
            FROM jobs {where}
            """,
            params,
        ).fetchall()

        # Aggregate by customer
        aggregates: dict[str, float] = {}
        for row in rows:
            name = row["customer_name"]
            if name not in aggregates:
                aggregates[name] = 0.0
            if row["invoice_total"]:
                val = row["invoice_total"].replace("$", "").replace(",", "").strip()
                try:
                    aggregates[name] += float(val)
                except ValueError:
                    pass

        # Sort and limit
        sorted_customers = sorted(aggregates.items(), key=lambda x: x[1], reverse=True)
        return sorted_customers[:limit]
