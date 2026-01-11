"""
Tests for the SQLite persistence layer.

Uses a temporary database for isolation.
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from trap.models import Customer, Job, JobStatus, ServiceFrequency, Site
from trap.storage import (
    count_customers,
    count_jobs,
    count_sites,
    delete_customer,
    delete_job,
    get_customer,
    get_dashboard_kpis,
    get_jobs_by_date,
    get_jobs_by_status,
    get_jobs_by_technician,
    get_revenue_by_date,
    get_site,
    get_top_customers_by_revenue,
    get_unique_technicians,
    init_db,
    list_customers,
    list_jobs,
    list_overdue_sites,
    list_sites,
    load_job,
    reset_db,
    save_customer,
    save_job,
    save_site,
    update_customer,
    update_job,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_jobs.db"
        init_db(db_path)
        yield db_path


class TestSaveAndLoadJob:
    def test_save_and_load_job(self, temp_db):
        """Save a job and load it back."""
        job = Job(
            invoice_number="TEST-001",
            customer_name="Test Customer",
            status=JobStatus.DRAFT,
        )

        saved = save_job(job, temp_db)
        assert saved.job_id == job.job_id

        loaded = load_job(job.job_id, temp_db)
        assert loaded is not None
        assert loaded.invoice_number == "TEST-001"
        assert loaded.customer_name == "Test Customer"
        assert loaded.status == JobStatus.DRAFT

    def test_load_nonexistent_job(self, temp_db):
        """Loading a non-existent job returns None."""
        result = load_job(uuid4(), temp_db)
        assert result is None

    def test_save_updates_updated_at(self, temp_db):
        """Saving updates the updated_at timestamp."""
        job = Job(invoice_number="TEST-002")
        original_updated = job.updated_at

        save_job(job, temp_db)
        loaded = load_job(job.job_id, temp_db)

        assert loaded.updated_at >= original_updated

    def test_save_preserves_all_fields(self, temp_db):
        """All job fields are saved and loaded correctly."""
        job = Job(
            invoice_number="FULL-001",
            service_date="2026-01-15",
            customer_name="Full Test Co",
            customer_address="123 Main St, City, ST 12345",
            phone="555-123-4567",
            trap_size="1,500 gallons",
            gallons_pumped="1,200 gallons",
            technician="John Smith",
            disposal_facility="City Treatment Plant",
            invoice_total="$500.00",
            notes="Test notes",
            source_filename="test.txt",
            confidence_score=85,
            extracted_fields=["invoice_number", "customer_name"],
            missing_fields=["phone"],
        )

        save_job(job, temp_db)
        loaded = load_job(job.job_id, temp_db)

        assert loaded.invoice_number == "FULL-001"
        assert loaded.service_date == "2026-01-15"
        assert loaded.customer_name == "Full Test Co"
        assert loaded.customer_address == "123 Main St, City, ST 12345"
        assert loaded.phone == "555-123-4567"
        assert loaded.trap_size == "1,500 gallons"
        assert loaded.gallons_pumped == "1,200 gallons"
        assert loaded.technician == "John Smith"
        assert loaded.disposal_facility == "City Treatment Plant"
        assert loaded.invoice_total == "$500.00"
        assert loaded.notes == "Test notes"
        assert loaded.source_filename == "test.txt"
        assert loaded.confidence_score == 85
        assert loaded.extracted_fields == ["invoice_number", "customer_name"]
        assert loaded.missing_fields == ["phone"]


class TestListJobs:
    def test_list_empty_db(self, temp_db):
        """Listing an empty database returns empty list."""
        jobs = list_jobs(db_path=temp_db)
        assert jobs == []

    def test_list_jobs_ordered_by_created_at(self, temp_db):
        """Jobs are returned newest first."""
        job1 = Job(invoice_number="FIRST")
        job2 = Job(invoice_number="SECOND")

        save_job(job1, temp_db)
        save_job(job2, temp_db)

        jobs = list_jobs(db_path=temp_db)
        assert len(jobs) == 2
        # Newest first (job2 saved last)
        assert jobs[0].invoice_number == "SECOND"

    def test_filter_by_status(self, temp_db):
        """Filter jobs by status."""
        save_job(Job(invoice_number="DRAFT-1", status=JobStatus.DRAFT), temp_db)
        save_job(Job(invoice_number="VERIFIED-1", status=JobStatus.VERIFIED), temp_db)

        drafts = list_jobs(status=JobStatus.DRAFT, db_path=temp_db)
        assert len(drafts) == 1
        assert drafts[0].invoice_number == "DRAFT-1"

        verified = list_jobs(status=JobStatus.VERIFIED, db_path=temp_db)
        assert len(verified) == 1
        assert verified[0].invoice_number == "VERIFIED-1"

    def test_search_by_customer_name(self, temp_db):
        """Search jobs by customer name."""
        save_job(Job(invoice_number="A", customer_name="Tony's Restaurant"), temp_db)
        save_job(Job(invoice_number="B", customer_name="Joe's Diner"), temp_db)

        results = list_jobs(search="Tony", db_path=temp_db)
        assert len(results) == 1
        assert results[0].invoice_number == "A"

    def test_search_by_invoice_number(self, temp_db):
        """Search jobs by invoice number."""
        save_job(Job(invoice_number="INV-001", customer_name="Customer A"), temp_db)
        save_job(Job(invoice_number="INV-002", customer_name="Customer B"), temp_db)

        results = list_jobs(search="001", db_path=temp_db)
        assert len(results) == 1
        assert results[0].invoice_number == "INV-001"

    def test_limit_and_offset(self, temp_db):
        """Pagination with limit and offset works."""
        for i in range(5):
            save_job(Job(invoice_number=f"JOB-{i:03d}"), temp_db)

        # Get first 2
        page1 = list_jobs(limit=2, offset=0, db_path=temp_db)
        assert len(page1) == 2

        # Get next 2
        page2 = list_jobs(limit=2, offset=2, db_path=temp_db)
        assert len(page2) == 2

        # Ensure no overlap
        page1_ids = {j.job_id for j in page1}
        page2_ids = {j.job_id for j in page2}
        assert page1_ids.isdisjoint(page2_ids)


class TestUpdateJob:
    def test_update_single_field(self, temp_db):
        """Update a single field on a job."""
        job = Job(invoice_number="UPDATE-001")
        save_job(job, temp_db)

        updated = update_job(job.job_id, {"customer_name": "New Customer"}, temp_db)
        assert updated.customer_name == "New Customer"

        reloaded = load_job(job.job_id, temp_db)
        assert reloaded.customer_name == "New Customer"

    def test_update_multiple_fields(self, temp_db):
        """Update multiple fields at once."""
        job = Job(invoice_number="MULTI-001")
        save_job(job, temp_db)

        updated = update_job(
            job.job_id,
            {
                "customer_name": "Updated Customer",
                "phone": "555-999-8888",
                "notes": "Updated notes",
            },
            temp_db,
        )

        assert updated.customer_name == "Updated Customer"
        assert updated.phone == "555-999-8888"
        assert updated.notes == "Updated notes"

    def test_update_status(self, temp_db):
        """Update job status."""
        job = Job(invoice_number="STATUS-001", status=JobStatus.DRAFT)
        save_job(job, temp_db)

        updated = update_job(job.job_id, {"status": "Verified"}, temp_db)
        assert updated.status == JobStatus.VERIFIED

    def test_update_nonexistent_job(self, temp_db):
        """Updating a non-existent job returns None."""
        result = update_job(uuid4(), {"customer_name": "Test"}, temp_db)
        assert result is None


class TestDeleteJob:
    def test_delete_existing_job(self, temp_db):
        """Delete an existing job."""
        job = Job(invoice_number="DELETE-001")
        save_job(job, temp_db)

        result = delete_job(job.job_id, temp_db)
        assert result is True

        loaded = load_job(job.job_id, temp_db)
        assert loaded is None

    def test_delete_nonexistent_job(self, temp_db):
        """Deleting a non-existent job returns False."""
        result = delete_job(uuid4(), temp_db)
        assert result is False


class TestCountJobs:
    def test_count_all_jobs(self, temp_db):
        """Count all jobs."""
        save_job(Job(invoice_number="A"), temp_db)
        save_job(Job(invoice_number="B"), temp_db)

        assert count_jobs(db_path=temp_db) == 2

    def test_count_by_status(self, temp_db):
        """Count jobs by status."""
        save_job(Job(status=JobStatus.DRAFT), temp_db)
        save_job(Job(status=JobStatus.DRAFT), temp_db)
        save_job(Job(status=JobStatus.VERIFIED), temp_db)

        assert count_jobs(status=JobStatus.DRAFT, db_path=temp_db) == 2
        assert count_jobs(status=JobStatus.VERIFIED, db_path=temp_db) == 1
        assert count_jobs(status=JobStatus.EXPORTED, db_path=temp_db) == 0


class TestResetDb:
    def test_reset_clears_data(self, temp_db):
        """Reset clears all job data."""
        save_job(Job(invoice_number="A"), temp_db)
        save_job(Job(invoice_number="B"), temp_db)

        assert count_jobs(db_path=temp_db) == 2

        reset_db(temp_db)

        assert count_jobs(db_path=temp_db) == 0


class TestJobModel:
    def test_job_from_parse_result(self):
        """Create a Job from a ParseResult."""
        from trap.parse import parse_text_to_record

        text = "INVOICE #: TEST-001\nTOTAL DUE: $100.00"
        result = parse_text_to_record(text)

        job = Job.from_parse_result(result, source_filename="test.txt")

        assert job.invoice_number == "TEST-001"
        assert job.invoice_total == "$100.00"
        assert job.source_filename == "test.txt"
        assert job.status == JobStatus.DRAFT

    def test_can_verify_with_required_fields(self):
        """Job can be verified when required fields are present."""
        job = Job(
            invoice_number="TEST-001",
            service_date="2026-01-01",
            customer_name="Test Customer",
        )
        assert job.can_verify() is True

    def test_cannot_verify_without_required_fields(self):
        """Job cannot be verified when required fields are missing."""
        job = Job(invoice_number="TEST-001")
        assert job.can_verify() is False
        assert "service_date" in job.get_missing_required_fields()
        assert "customer_name" in job.get_missing_required_fields()

    def test_to_dict_serialization(self):
        """Job can be serialized to a dictionary."""
        import json

        job = Job(
            invoice_number="SERIAL-001",
            customer_name="Test Co",
            status=JobStatus.VERIFIED,
        )

        d = job.to_dict()

        # Should be JSON-serializable
        json_str = json.dumps(d)
        parsed = json.loads(json_str)

        assert parsed["invoice_number"] == "SERIAL-001"
        assert parsed["customer_name"] == "Test Co"
        assert parsed["status"] == "Verified"
        assert isinstance(parsed["job_id"], str)
        assert isinstance(parsed["created_at"], str)


# =============================================================================
# CUSTOMER TESTS
# =============================================================================


class TestCustomerCRUD:
    def test_save_and_get_customer(self, temp_db):
        """Save a customer and retrieve it by ID."""
        customer = Customer(
            name="Tony's Pizza",
            legal_name="Tony's Pizza LLC",
            phone="555-123-4567",
            email="tony@pizza.com",
            city="Chicago",
            state="IL",
        )

        saved = save_customer(customer, temp_db)
        assert saved.customer_id == customer.customer_id

        loaded = get_customer(customer.customer_id, temp_db)
        assert loaded is not None
        assert loaded.name == "Tony's Pizza"
        assert loaded.legal_name == "Tony's Pizza LLC"
        assert loaded.phone == "555-123-4567"
        assert loaded.email == "tony@pizza.com"
        assert loaded.city == "Chicago"
        assert loaded.state == "IL"
        assert loaded.is_active is True

    def test_get_nonexistent_customer(self, temp_db):
        """Getting a non-existent customer returns None."""
        result = get_customer(uuid4(), temp_db)
        assert result is None

    def test_list_customers_empty(self, temp_db):
        """Listing empty database returns empty list."""
        customers = list_customers(db_path=temp_db)
        assert customers == []

    def test_list_customers_sorted_by_name(self, temp_db):
        """Customers are sorted alphabetically by name."""
        save_customer(Customer(name="Zoe's Diner"), temp_db)
        save_customer(Customer(name="Alice's Cafe"), temp_db)
        save_customer(Customer(name="Mike's Grill"), temp_db)

        customers = list_customers(db_path=temp_db)
        assert len(customers) == 3
        assert customers[0].name == "Alice's Cafe"
        assert customers[1].name == "Mike's Grill"
        assert customers[2].name == "Zoe's Diner"

    def test_list_customers_search(self, temp_db):
        """Search customers by name."""
        save_customer(Customer(name="Tony's Pizza"), temp_db)
        save_customer(Customer(name="Joe's Diner"), temp_db)

        results = list_customers(search="Tony", db_path=temp_db)
        assert len(results) == 1
        assert results[0].name == "Tony's Pizza"

    def test_list_customers_active_only(self, temp_db):
        """Filter for active customers only."""
        c1 = Customer(name="Active Customer", is_active=True)
        c2 = Customer(name="Inactive Customer", is_active=False)
        save_customer(c1, temp_db)
        save_customer(c2, temp_db)

        active = list_customers(active_only=True, db_path=temp_db)
        assert len(active) == 1
        assert active[0].name == "Active Customer"

        all_customers = list_customers(active_only=False, db_path=temp_db)
        assert len(all_customers) == 2

    def test_update_customer(self, temp_db):
        """Update customer fields."""
        customer = Customer(name="Original Name")
        save_customer(customer, temp_db)

        updated = update_customer(
            customer.customer_id,
            {"name": "Updated Name", "phone": "555-999-0000"},
            temp_db,
        )

        assert updated.name == "Updated Name"
        assert updated.phone == "555-999-0000"

        reloaded = get_customer(customer.customer_id, temp_db)
        assert reloaded.name == "Updated Name"

    def test_update_nonexistent_customer(self, temp_db):
        """Updating non-existent customer returns None."""
        result = update_customer(uuid4(), {"name": "Test"}, temp_db)
        assert result is None

    def test_delete_customer_soft_delete(self, temp_db):
        """Delete marks customer as inactive."""
        customer = Customer(name="To Delete")
        save_customer(customer, temp_db)

        result = delete_customer(customer.customer_id, temp_db)
        assert result is True

        # Should not appear in active list
        active = list_customers(active_only=True, db_path=temp_db)
        assert len(active) == 0

        # Should still exist when including inactive
        all_customers = list_customers(active_only=False, db_path=temp_db)
        assert len(all_customers) == 1
        assert all_customers[0].is_active is False

    def test_count_customers(self, temp_db):
        """Count customers."""
        save_customer(Customer(name="A", is_active=True), temp_db)
        save_customer(Customer(name="B", is_active=True), temp_db)
        save_customer(Customer(name="C", is_active=False), temp_db)

        assert count_customers(active_only=True, db_path=temp_db) == 2
        assert count_customers(active_only=False, db_path=temp_db) == 3


# =============================================================================
# SITE TESTS
# =============================================================================


class TestSiteCRUD:
    def test_save_and_get_site(self, temp_db):
        """Save a site and retrieve it."""
        customer = Customer(name="Test Customer")
        save_customer(customer, temp_db)

        site = Site(
            customer_id=customer.customer_id,
            name="Main Kitchen",
            address="123 Main St",
            city="Chicago",
            state="IL",
            trap_type="Interior",
            trap_size="1,500 gallons",
            service_frequency=ServiceFrequency.MONTHLY,
        )

        saved = save_site(site, temp_db)
        assert saved.site_id == site.site_id

        loaded = get_site(site.site_id, temp_db)
        assert loaded is not None
        assert loaded.name == "Main Kitchen"
        assert loaded.trap_type == "Interior"
        assert loaded.trap_size == "1,500 gallons"
        assert loaded.service_frequency == ServiceFrequency.MONTHLY

    def test_get_nonexistent_site(self, temp_db):
        """Getting a non-existent site returns None."""
        result = get_site(uuid4(), temp_db)
        assert result is None

    def test_list_sites_by_customer(self, temp_db):
        """List sites filtered by customer."""
        c1 = Customer(name="Customer 1")
        c2 = Customer(name="Customer 2")
        save_customer(c1, temp_db)
        save_customer(c2, temp_db)

        save_site(Site(customer_id=c1.customer_id, name="Site A"), temp_db)
        save_site(Site(customer_id=c1.customer_id, name="Site B"), temp_db)
        save_site(Site(customer_id=c2.customer_id, name="Site C"), temp_db)

        c1_sites = list_sites(customer_id=c1.customer_id, db_path=temp_db)
        assert len(c1_sites) == 2

        c2_sites = list_sites(customer_id=c2.customer_id, db_path=temp_db)
        assert len(c2_sites) == 1

    def test_list_overdue_sites(self, temp_db):
        """List sites that are overdue for service."""
        yesterday = datetime.now() - timedelta(days=1)
        tomorrow = datetime.now() + timedelta(days=1)

        save_site(Site(name="Overdue", next_service_date=yesterday), temp_db)
        save_site(Site(name="Upcoming", next_service_date=tomorrow), temp_db)
        save_site(Site(name="No Date"), temp_db)

        overdue = list_overdue_sites(db_path=temp_db)
        assert len(overdue) == 1
        assert overdue[0].name == "Overdue"

    def test_count_sites(self, temp_db):
        """Count sites."""
        save_site(Site(name="A", is_active=True), temp_db)
        save_site(Site(name="B", is_active=True), temp_db)
        save_site(Site(name="C", is_active=False), temp_db)

        assert count_sites(active_only=True, db_path=temp_db) == 2
        assert count_sites(active_only=False, db_path=temp_db) == 3


# =============================================================================
# ANALYTICS TESTS
# =============================================================================


class TestAnalytics:
    def test_get_dashboard_kpis(self, temp_db):
        """Get dashboard KPIs."""
        # Create test data
        save_job(
            Job(
                invoice_number="A",
                status=JobStatus.COMPLETED,
                invoice_total="$500.00",
                gallons_pumped="1,200 gallons",
                service_date="2026-01-10",
            ),
            temp_db,
        )
        save_job(
            Job(
                invoice_number="B",
                status=JobStatus.SCHEDULED,
                service_date="2026-01-15",
            ),
            temp_db,
        )
        save_customer(Customer(name="Test Customer"), temp_db)
        save_site(Site(name="Test Site"), temp_db)

        kpis = get_dashboard_kpis(db_path=temp_db)

        assert kpis.jobs_completed == 1
        assert kpis.jobs_scheduled == 1
        assert kpis.total_revenue == 500.0
        assert kpis.total_gallons == 1200.0
        assert kpis.customer_count == 1
        assert kpis.site_count == 1

    def test_get_dashboard_kpis_with_date_filter(self, temp_db):
        """KPIs can be filtered by date range."""
        save_job(
            Job(
                invoice_number="A",
                status=JobStatus.COMPLETED,
                invoice_total="$100.00",
                service_date="2026-01-01",
            ),
            temp_db,
        )
        save_job(
            Job(
                invoice_number="B",
                status=JobStatus.COMPLETED,
                invoice_total="$200.00",
                service_date="2026-01-15",
            ),
            temp_db,
        )

        # Filter to only include first job
        kpis = get_dashboard_kpis(
            date_from="2026-01-01", date_to="2026-01-10", db_path=temp_db
        )

        assert kpis.total_revenue == 100.0

    def test_get_jobs_by_date(self, temp_db):
        """Get job counts by date."""
        save_job(Job(invoice_number="A", service_date="2026-01-10"), temp_db)
        save_job(Job(invoice_number="B", service_date="2026-01-10"), temp_db)
        save_job(Job(invoice_number="C", service_date="2026-01-11"), temp_db)

        result = get_jobs_by_date("2026-01-01", "2026-01-31", db_path=temp_db)

        assert len(result) == 2
        # Find the 01-10 entry
        jan10 = next(p for p in result if p.date == "2026-01-10")
        assert jan10.value == 2

    def test_get_jobs_by_status(self, temp_db):
        """Get job counts by status."""
        save_job(Job(invoice_number="A", status=JobStatus.DRAFT), temp_db)
        save_job(Job(invoice_number="B", status=JobStatus.DRAFT), temp_db)
        save_job(Job(invoice_number="C", status=JobStatus.VERIFIED), temp_db)

        result = get_jobs_by_status(db_path=temp_db)

        assert result["Draft"] == 2
        assert result["Verified"] == 1

    def test_get_jobs_by_technician(self, temp_db):
        """Get job counts by technician."""
        save_job(Job(invoice_number="A", technician="John Smith"), temp_db)
        save_job(Job(invoice_number="B", technician="John Smith"), temp_db)
        save_job(Job(invoice_number="C", technician="Jane Doe"), temp_db)
        save_job(Job(invoice_number="D", technician=None), temp_db)

        result = get_jobs_by_technician(db_path=temp_db)

        assert result["John Smith"] == 2
        assert result["Jane Doe"] == 1
        assert None not in result

    def test_get_unique_technicians(self, temp_db):
        """Get unique technician names."""
        save_job(Job(invoice_number="A", technician="John"), temp_db)
        save_job(Job(invoice_number="B", technician="Jane"), temp_db)
        save_job(Job(invoice_number="C", technician="John"), temp_db)
        save_job(Job(invoice_number="D", technician=None), temp_db)

        techs = get_unique_technicians(db_path=temp_db)

        assert sorted(techs) == ["Jane", "John"]

    def test_get_revenue_by_date(self, temp_db):
        """Get revenue totals by date."""
        save_job(
            Job(
                invoice_number="A",
                service_date="2026-01-10",
                invoice_total="$100.00",
            ),
            temp_db,
        )
        save_job(
            Job(
                invoice_number="B",
                service_date="2026-01-10",
                invoice_total="$200.00",
            ),
            temp_db,
        )

        result = get_revenue_by_date("2026-01-01", "2026-01-31", db_path=temp_db)

        assert len(result) == 1
        assert result[0].date == "2026-01-10"
        assert result[0].value == 300.0

    def test_get_top_customers_by_revenue(self, temp_db):
        """Get top customers by revenue."""
        save_job(
            Job(
                invoice_number="A",
                customer_name="Big Spender",
                invoice_total="$1,000.00",
            ),
            temp_db,
        )
        save_job(
            Job(
                invoice_number="B",
                customer_name="Big Spender",
                invoice_total="$500.00",
            ),
            temp_db,
        )
        save_job(
            Job(
                invoice_number="C",
                customer_name="Small Customer",
                invoice_total="$100.00",
            ),
            temp_db,
        )

        result = get_top_customers_by_revenue(limit=10, db_path=temp_db)

        assert len(result) == 2
        assert result[0][0] == "Big Spender"
        assert result[0][1] == 1500.0
        assert result[1][0] == "Small Customer"
        assert result[1][1] == 100.0


class TestJobsExtended:
    def test_list_jobs_by_technician(self, temp_db):
        """Filter jobs by technician."""
        save_job(Job(invoice_number="A", technician="John"), temp_db)
        save_job(Job(invoice_number="B", technician="Jane"), temp_db)

        john_jobs = list_jobs(technician="John", db_path=temp_db)
        assert len(john_jobs) == 1
        assert john_jobs[0].invoice_number == "A"

    def test_list_jobs_by_date_range(self, temp_db):
        """Filter jobs by date range."""
        save_job(Job(invoice_number="A", service_date="2026-01-05"), temp_db)
        save_job(Job(invoice_number="B", service_date="2026-01-15"), temp_db)
        save_job(Job(invoice_number="C", service_date="2026-01-25"), temp_db)

        mid_jobs = list_jobs(
            date_from="2026-01-10", date_to="2026-01-20", db_path=temp_db
        )
        assert len(mid_jobs) == 1
        assert mid_jobs[0].invoice_number == "B"

    def test_list_jobs_by_customer_id(self, temp_db):
        """Filter jobs by customer ID."""
        customer = Customer(name="Test")
        save_customer(customer, temp_db)

        save_job(Job(invoice_number="A", customer_id=customer.customer_id), temp_db)
        save_job(Job(invoice_number="B"), temp_db)

        cust_jobs = list_jobs(customer_id=customer.customer_id, db_path=temp_db)
        assert len(cust_jobs) == 1
        assert cust_jobs[0].invoice_number == "A"
