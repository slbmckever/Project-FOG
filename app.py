"""
Trap CRM - FOG / Grease Trap Service Management System
A Salesforce-style dashboard built with Streamlit.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

import pandas as pd
import streamlit as st

# Add src/ to path for engine imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from trap.models import (
    SERVICE_RECORD_FIELDS,
    Customer,
    Job,
    JobStatus,
)
from trap.parse import parse_text_to_record
from trap.storage import (
    count_customers,
    count_jobs,
    count_sites,
    delete_job,
    get_customer,
    get_dashboard_kpis,
    get_gallons_by_date,
    get_jobs_by_date,
    get_jobs_by_status,
    get_jobs_by_technician,
    get_revenue_by_date,
    get_top_customers_by_revenue,
    get_unique_technicians,
    init_db,
    list_customers,
    list_jobs,
    load_job,
    save_customer,
    save_job,
    update_customer,
    update_job,
)

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Trap CRM",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database
init_db()

# --- PATHS ---
ASSETS_DIR = Path(__file__).parent / "assets"
VIDEO_PATH = ASSETS_DIR / "bg.mp4"
FIXTURES_DIR = Path(__file__).parent / "tests" / "fixtures"


# =============================================================================
# STYLES
# =============================================================================


def inject_styles():
    st.markdown(
        """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        :root {
            --primary: #6366f1;
            --accent: #22d3ee;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --bg-dark: #0f172a;
            --bg-card: rgba(30, 41, 59, 0.8);
            --bg-glass: rgba(30, 41, 59, 0.7);
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --border: rgba(148, 163, 184, 0.2);
        }

        .stApp { font-family: 'Inter', sans-serif; }

        #MainMenu, footer, header { visibility: hidden; }
        .stDeployButton { display: none; }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
            border-right: 1px solid var(--border);
        }

        .nav-logo {
            font-size: 1.75rem;
            font-weight: 800;
            background: linear-gradient(135deg, #fff 0%, var(--accent) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-bottom: 1rem;
        }

        .page-header {
            font-size: 2rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 0.5rem;
        }

        .page-subtitle {
            color: var(--text-secondary);
            margin-bottom: 1.5rem;
        }

        .kpi-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.25rem;
            text-align: center;
        }

        .kpi-value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--text-primary);
        }

        .kpi-label {
            font-size: 0.75rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .kpi-success { color: var(--success); }
        .kpi-warning { color: var(--warning); }
        .kpi-danger { color: var(--danger); }
        .kpi-primary { color: var(--primary); }
        .kpi-accent { color: var(--accent); }

        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .status-scheduled { background: rgba(99, 102, 241, 0.2); color: #6366f1; }
        .status-in-progress { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
        .status-completed { background: rgba(16, 185, 129, 0.2); color: #10b981; }
        .status-verified { background: rgba(34, 211, 238, 0.2); color: #22d3ee; }
        .status-invoiced { background: rgba(168, 85, 247, 0.2); color: #a855f7; }
        .status-draft { background: rgba(148, 163, 184, 0.2); color: #94a3b8; }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }

        .card-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 1rem;
        }

        .stButton > button {
            background: linear-gradient(135deg, var(--primary) 0%, #4f46e5 100%);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
            border-radius: 10px;
        }

        .stTextInput input, .stTextArea textarea, .stSelectbox select {
            background: rgba(30, 41, 59, 0.8) !important;
            border: 1px solid var(--border) !important;
            color: var(--text-primary) !important;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_date_range(preset: str) -> tuple[str, str]:
    """Get date range from preset."""
    today = datetime.now()
    if preset == "Last 7 Days":
        start = today - timedelta(days=7)
    elif preset == "Last 30 Days":
        start = today - timedelta(days=30)
    elif preset == "Last 90 Days":
        start = today - timedelta(days=90)
    elif preset == "Year to Date":
        start = datetime(today.year, 1, 1)
    else:
        start = today - timedelta(days=30)

    return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


def format_currency(value: float) -> str:
    """Format number as currency."""
    return f"${value:,.2f}"


def format_number(value: float) -> str:
    """Format number with commas."""
    if value >= 1000:
        return f"{value:,.0f}"
    return f"{value:.1f}"


def get_status_class(status: str) -> str:
    """Get CSS class for status badge."""
    status_map = {
        "Scheduled": "scheduled",
        "In Progress": "in-progress",
        "Completed": "completed",
        "Verified": "verified",
        "Invoiced": "invoiced",
        "Draft": "draft",
        "Exported": "verified",
    }
    return f"status-{status_map.get(status, 'draft')}"


# =============================================================================
# DASHBOARD PAGE
# =============================================================================


def page_dashboard():
    st.markdown('<h1 class="page-header">Dashboard</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-subtitle">Overview of your service operations</p>',
        unsafe_allow_html=True,
    )

    # Filters row
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

    with col1:
        date_preset = st.selectbox(
            "Date Range",
            ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Year to Date"],
            index=1,
            key="dash_date",
        )
    with col2:
        customers = list_customers(limit=100)
        customer_options = ["All Customers"] + [c.name for c in customers]
        selected_customer = st.selectbox(
            "Customer", customer_options, key="dash_customer"
        )
    with col3:
        technicians = ["All Technicians"] + get_unique_technicians()
        selected_tech = st.selectbox("Technician", technicians, key="dash_tech")
    with col4:
        st.write("")  # Spacer

    # Get date range
    date_from, date_to = get_date_range(date_preset)

    # Get filter values
    customer_id = None
    if selected_customer != "All Customers":
        for c in customers:
            if c.name == selected_customer:
                customer_id = c.customer_id
                break

    technician = None if selected_tech == "All Technicians" else selected_tech

    # Get KPIs
    kpis = get_dashboard_kpis(
        date_from=date_from,
        date_to=date_to,
        customer_id=customer_id,
        technician=technician,
    )

    # KPI Cards - Row 1
    st.markdown("### Key Metrics")
    k1, k2, k3, k4, k5, k6 = st.columns(6)

    with k1:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-value kpi-success">{kpis.jobs_completed}</div>
                <div class="kpi-label">Jobs Completed</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k2:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-value kpi-primary">{kpis.jobs_scheduled}</div>
                <div class="kpi-label">Jobs Scheduled</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k3:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-value kpi-accent">{format_currency(kpis.total_revenue)}</div>
                <div class="kpi-label">Total Revenue</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k4:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-value">{format_number(kpis.total_gallons)}</div>
                <div class="kpi-label">Gallons Pumped</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k5:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-value">{format_currency(kpis.avg_revenue_per_job)}</div>
                <div class="kpi-label">Avg Revenue/Job</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k6:
        color = "kpi-danger" if kpis.overdue_services > 0 else "kpi-success"
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-value {color}">{kpis.overdue_services}</div>
                <div class="kpi-label">Overdue Services</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # KPI Cards - Row 2
    k7, k8, k9, k10 = st.columns(4)

    with k7:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-value">{kpis.customer_count}</div>
                <div class="kpi-label">Active Customers</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k8:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-value">{kpis.site_count}</div>
                <div class="kpi-label">Active Sites</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k9:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-value">{format_number(kpis.avg_gallons_per_job)}</div>
                <div class="kpi-label">Avg Gallons/Job</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k10:
        color = "kpi-warning" if kpis.docs_missing_count > 0 else "kpi-success"
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-value {color}">{kpis.docs_missing_count}</div>
                <div class="kpi-label">Missing Docs</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Charts
    chart1, chart2 = st.columns(2)

    with chart1:
        st.markdown("### Jobs Over Time")
        jobs_data = get_jobs_by_date(date_from, date_to, group_by="day")
        if jobs_data:
            df = pd.DataFrame([{"Date": p.date, "Jobs": p.value} for p in jobs_data])
            st.line_chart(df.set_index("Date"))
        else:
            st.info("No job data for selected period")

    with chart2:
        st.markdown("### Revenue Over Time")
        revenue_data = get_revenue_by_date(date_from, date_to, group_by="day")
        if revenue_data:
            df = pd.DataFrame(
                [{"Date": p.date, "Revenue": p.value} for p in revenue_data]
            )
            st.line_chart(df.set_index("Date"))
        else:
            st.info("No revenue data for selected period")

    chart3, chart4 = st.columns(2)

    with chart3:
        st.markdown("### Jobs by Status")
        status_data = get_jobs_by_status(date_from, date_to)
        if status_data:
            df = pd.DataFrame(
                [{"Status": k, "Count": v} for k, v in status_data.items()]
            )
            st.bar_chart(df.set_index("Status"))
        else:
            st.info("No status data for selected period")

    with chart4:
        st.markdown("### Top Customers by Revenue")
        top_customers = get_top_customers_by_revenue(
            limit=5, date_from=date_from, date_to=date_to
        )
        if top_customers:
            df = pd.DataFrame(
                [{"Customer": name, "Revenue": rev} for name, rev in top_customers]
            )
            st.bar_chart(df.set_index("Customer"))
        else:
            st.info("No customer data for selected period")

    # Recent activity
    st.markdown("---")
    st.markdown("### Recent Jobs")

    recent_jobs = list_jobs(limit=10)
    if recent_jobs:
        for job in recent_jobs:
            status_class = get_status_class(job.status.value)
            col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 1.5, 1.5])
            with col1:
                st.write(job.invoice_number or "—")
            with col2:
                st.write(job.customer_name or "—")
            with col3:
                st.write(job.service_date or "—")
            with col4:
                st.markdown(
                    f'<span class="status-badge {status_class}">{job.status.value}</span>',
                    unsafe_allow_html=True,
                )
            with col5:
                if st.button("View", key=f"dash_job_{job.job_id}"):
                    st.session_state.current_job_id = str(job.job_id)
                    st.session_state.current_page = "Job Detail"
                    st.rerun()
    else:
        st.info("No recent jobs")


# =============================================================================
# CUSTOMERS PAGE
# =============================================================================


def page_customers():
    st.markdown('<h1 class="page-header">Customers</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-subtitle">Manage your customer accounts</p>',
        unsafe_allow_html=True,
    )

    # Action buttons
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("+ New Customer", use_container_width=True):
            st.session_state.current_page = "New Customer"
            st.rerun()

    # Search
    search = st.text_input(
        "Search customers", placeholder="Name, email...", key="cust_search"
    )

    # List customers
    customers = list_customers(search=search if search else None, limit=50)

    if not customers:
        st.info("No customers found. Create your first customer!")
        return

    # Customer table
    for customer in customers:
        col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])

        with col1:
            st.write(f"**{customer.name}**")
        with col2:
            st.write(customer.phone or "—")
        with col3:
            st.write(customer.email or "—")
        with col4:
            st.write(customer.city or "—")
        with col5:
            if st.button("View", key=f"cust_{customer.customer_id}"):
                st.session_state.current_customer_id = str(customer.customer_id)
                st.session_state.current_page = "Customer Detail"
                st.rerun()


def page_new_customer():
    st.markdown('<h1 class="page-header">New Customer</h1>', unsafe_allow_html=True)

    with st.form("new_customer_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Business Name *")
            legal_name = st.text_input("Legal Name")
            phone = st.text_input("Phone")
            email = st.text_input("Email")

        with col2:
            service_address = st.text_input("Service Address")
            city = st.text_input("City")
            state = st.text_input("State")
            zip_code = st.text_input("ZIP Code")

        billing_address = st.text_input("Billing Address")
        notes = st.text_area("Notes")

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Save Customer", use_container_width=True)
        with col2:
            if st.form_submit_button("Cancel", use_container_width=True):
                st.session_state.current_page = "Customers"
                st.rerun()

        if submitted:
            if not name:
                st.error("Business name is required")
            else:
                customer = Customer(
                    name=name,
                    legal_name=legal_name or None,
                    phone=phone or None,
                    email=email or None,
                    service_address=service_address or None,
                    city=city or None,
                    state=state or None,
                    zip_code=zip_code or None,
                    billing_address=billing_address or None,
                    notes=notes or None,
                )
                save_customer(customer)
                st.success(f"Customer '{name}' created!")
                st.session_state.current_page = "Customers"
                st.rerun()


def page_customer_detail():
    customer_id = st.session_state.get("current_customer_id")
    if not customer_id:
        st.warning("No customer selected")
        return

    customer = get_customer(customer_id)
    if not customer:
        st.error("Customer not found")
        return

    # Header
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(
            f'<h1 class="page-header">{customer.name}</h1>', unsafe_allow_html=True
        )
    with col2:
        if st.button("Back to Customers"):
            st.session_state.current_page = "Customers"
            st.rerun()

    # Edit mode toggle
    if "customer_edit_mode" not in st.session_state:
        st.session_state.customer_edit_mode = False

    if st.button("Edit" if not st.session_state.customer_edit_mode else "Cancel Edit"):
        st.session_state.customer_edit_mode = not st.session_state.customer_edit_mode
        st.rerun()

    if st.session_state.customer_edit_mode:
        with st.form("edit_customer_form"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Business Name *", value=customer.name)
                legal_name = st.text_input(
                    "Legal Name", value=customer.legal_name or ""
                )
                phone = st.text_input("Phone", value=customer.phone or "")
                email = st.text_input("Email", value=customer.email or "")

            with col2:
                service_address = st.text_input(
                    "Service Address", value=customer.service_address or ""
                )
                city = st.text_input("City", value=customer.city or "")
                state = st.text_input("State", value=customer.state or "")
                zip_code = st.text_input("ZIP Code", value=customer.zip_code or "")

            billing_address = st.text_input(
                "Billing Address", value=customer.billing_address or ""
            )
            notes = st.text_area("Notes", value=customer.notes or "")

            if st.form_submit_button("Save Changes", use_container_width=True):
                update_customer(
                    customer_id,
                    {
                        "name": name,
                        "legal_name": legal_name or None,
                        "phone": phone or None,
                        "email": email or None,
                        "service_address": service_address or None,
                        "city": city or None,
                        "state": state or None,
                        "zip_code": zip_code or None,
                        "billing_address": billing_address or None,
                        "notes": notes or None,
                    },
                )
                st.success("Customer updated!")
                st.session_state.customer_edit_mode = False
                st.rerun()
    else:
        # Display customer info
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Contact Information**")
            st.write(f"Phone: {customer.phone or '—'}")
            st.write(f"Email: {customer.email or '—'}")

        with col2:
            st.markdown("**Address**")
            st.write(f"{customer.service_address or '—'}")
            st.write(
                f"{customer.city or ''}, {customer.state or ''} {customer.zip_code or ''}"
            )

        if customer.notes:
            st.markdown("**Notes**")
            st.write(customer.notes)

    # Customer's jobs
    st.markdown("---")
    st.markdown("### Recent Jobs")

    jobs = list_jobs(customer_id=customer_id, limit=20)
    if jobs:
        for job in jobs:
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            with col1:
                st.write(job.invoice_number or "—")
            with col2:
                st.write(job.service_date or "—")
            with col3:
                status_class = get_status_class(job.status.value)
                st.markdown(
                    f'<span class="status-badge {status_class}">{job.status.value}</span>',
                    unsafe_allow_html=True,
                )
            with col4:
                if st.button("View", key=f"cust_job_{job.job_id}"):
                    st.session_state.current_job_id = str(job.job_id)
                    st.session_state.current_page = "Job Detail"
                    st.rerun()
    else:
        st.info("No jobs for this customer yet")


# =============================================================================
# JOBS PAGE
# =============================================================================


def page_jobs():
    st.markdown('<h1 class="page-header">Jobs</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-subtitle">Manage service jobs and work orders</p>',
        unsafe_allow_html=True,
    )

    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("+ New Job", use_container_width=True):
            st.session_state.current_page = "New Job"
            st.rerun()
    with col2:
        if st.button("Parse Invoice", use_container_width=True):
            st.session_state.current_page = "Parse Job"
            st.rerun()

    # Filters
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        search = st.text_input(
            "Search", placeholder="Invoice # or customer...", key="jobs_search"
        )

    with col2:
        status_options = ["All"] + [s.value for s in JobStatus]
        status_filter = st.selectbox("Status", status_options, key="jobs_status")

    with col3:
        technicians = ["All"] + get_unique_technicians()
        tech_filter = st.selectbox("Technician", technicians, key="jobs_tech")

    with col4:
        date_preset = st.selectbox(
            "Date Range",
            ["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days"],
            key="jobs_date",
        )

    # Build filters
    status = JobStatus(status_filter) if status_filter != "All" else None
    technician = tech_filter if tech_filter != "All" else None
    date_from, date_to = None, None
    if date_preset != "All Time":
        date_from, date_to = get_date_range(date_preset)

    # List jobs
    jobs = list_jobs(
        status=status,
        technician=technician,
        search=search if search else None,
        date_from=date_from,
        date_to=date_to,
        limit=50,
    )

    if not jobs:
        st.info("No jobs found")
        return

    # Jobs table header
    hcol1, hcol2, hcol3, hcol4, hcol5, hcol6 = st.columns([1.5, 2.5, 1.5, 1.5, 1, 1])
    with hcol1:
        st.markdown("**Invoice #**")
    with hcol2:
        st.markdown("**Customer**")
    with hcol3:
        st.markdown("**Date**")
    with hcol4:
        st.markdown("**Total**")
    with hcol5:
        st.markdown("**Status**")
    with hcol6:
        st.markdown("**Action**")

    for job in jobs:
        col1, col2, col3, col4, col5, col6 = st.columns([1.5, 2.5, 1.5, 1.5, 1, 1])

        with col1:
            st.write(job.invoice_number or "—")
        with col2:
            st.write(job.customer_name or "—")
        with col3:
            st.write(job.get_service_date_display())
        with col4:
            st.write(job.get_invoice_total_display())
        with col5:
            status_class = get_status_class(job.status.value)
            st.markdown(
                f'<span class="status-badge {status_class}">{job.status.value}</span>',
                unsafe_allow_html=True,
            )
        with col6:
            if st.button("View", key=f"job_{job.job_id}"):
                st.session_state.current_job_id = str(job.job_id)
                st.session_state.current_page = "Job Detail"
                st.rerun()


def page_new_job():
    st.markdown('<h1 class="page-header">New Job</h1>', unsafe_allow_html=True)

    with st.form("new_job_form"):
        # Customer selection
        customers = list_customers(limit=100)
        customer_options = {str(c.customer_id): c.name for c in customers}
        customer_options = {"": "Select Customer..."} | customer_options
        selected_customer = st.selectbox(
            "Customer",
            options=list(customer_options.keys()),
            format_func=lambda x: customer_options[x],
        )

        col1, col2 = st.columns(2)

        with col1:
            invoice_number = st.text_input("Invoice Number *")
            service_date = st.date_input("Service Date *")
            customer_name = st.text_input("Customer Name (override)")
            technician = st.text_input("Technician")
            truck_id = st.text_input("Truck ID")

        with col2:
            gallons_pumped = st.text_input("Gallons Pumped")
            trap_size = st.text_input("Trap Size")
            disposal_facility = st.text_input("Disposal Facility")
            invoice_total = st.text_input("Invoice Total")
            manifest_number = st.text_input("Manifest Number")

        customer_address = st.text_input("Customer Address")
        notes = st.text_area("Notes")

        status_options = [s.value for s in JobStatus]
        status = st.selectbox("Status", status_options, index=0)

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Save Job", use_container_width=True)
        with col2:
            if st.form_submit_button("Cancel", use_container_width=True):
                st.session_state.current_page = "Jobs"
                st.rerun()

        if submitted:
            if not invoice_number:
                st.error("Invoice number is required")
            else:
                # Parse typed values from string inputs
                gallons_float = None
                if gallons_pumped:
                    try:
                        val = gallons_pumped.lower().replace("gallons", "").replace("gal", "").replace(",", "").strip()
                        gallons_float = float(val)
                    except ValueError:
                        pass

                invoice_cents = None
                if invoice_total:
                    try:
                        val = invoice_total.replace("$", "").replace(",", "").strip()
                        invoice_cents = int(float(val) * 100)
                    except ValueError:
                        pass

                job = Job(
                    customer_id=UUID(selected_customer) if selected_customer else None,
                    invoice_number=invoice_number,
                    service_date=service_date,  # date object from st.date_input
                    service_date_str=str(service_date),
                    customer_name=customer_name or None,
                    customer_address=customer_address or None,
                    technician=technician or None,
                    truck_id=truck_id or None,
                    gallons_pumped=gallons_float,
                    gallons_pumped_str=gallons_pumped or None,
                    trap_size=trap_size or None,
                    disposal_facility=disposal_facility or None,
                    invoice_total_cents=invoice_cents,
                    invoice_total_str=invoice_total or None,
                    manifest_number=manifest_number or None,
                    notes=notes or None,
                    status=JobStatus(status),
                )
                save_job(job)
                st.success(f"Job '{invoice_number}' created!")
                st.session_state.current_page = "Jobs"
                st.rerun()


def page_parse_job():
    """Parse invoice and create job."""
    st.markdown('<h1 class="page-header">Parse Invoice</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-subtitle">Upload or paste invoice text to extract data</p>',
        unsafe_allow_html=True,
    )

    # Initialize session state
    if "parse_stage" not in st.session_state:
        st.session_state.parse_stage = "input"
    if "parsed_job" not in st.session_state:
        st.session_state.parsed_job = None

    if st.session_state.parse_stage == "input":
        _render_parse_input()
    else:
        _render_parse_edit()


def _render_parse_input():
    """Render parse input stage."""
    sample_files = sorted(FIXTURES_DIR.glob("*.txt")) if FIXTURES_DIR.exists() else []
    sample_options = {"": "Select sample..."} | {f.stem: f.stem for f in sample_files}

    sample_choice = st.selectbox(
        "Load sample invoice",
        options=list(sample_options.keys()),
        format_func=lambda x: sample_options[x] if x else "Select sample...",
    )

    default_text = ""
    if sample_choice:
        sample_path = FIXTURES_DIR / f"{sample_choice}.txt"
        if sample_path.exists():
            default_text = sample_path.read_text(errors="replace")

    input_text = st.text_area(
        "Invoice text",
        value=default_text,
        height=300,
        placeholder="Paste invoice text here...",
    )

    uploaded = st.file_uploader("Or upload a file", type=["txt"])
    source_filename = None
    if uploaded:
        input_text = uploaded.read().decode("utf-8", errors="replace")
        source_filename = uploaded.name

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Parse & Continue", use_container_width=True):
            if input_text.strip():
                result = parse_text_to_record(input_text)
                job = Job.from_parse_result(result, source_filename=source_filename)
                st.session_state.parsed_job = job
                st.session_state.parse_stage = "edit"
                st.rerun()
            else:
                st.warning("Please enter text to parse")
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.session_state.current_page = "Jobs"
            st.rerun()


def _render_parse_edit():
    """Render parse edit stage."""
    job = st.session_state.parsed_job

    # Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        color = (
            "kpi-success"
            if job.confidence_score >= 70
            else "kpi-warning"
            if job.confidence_score >= 40
            else "kpi-danger"
        )
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-value {color}">{job.confidence_score}%</div>
                <div class="kpi-label">Confidence</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-value">{len(job.extracted_fields)}</div>
                <div class="kpi-label">Fields Found</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-value">{len(job.missing_fields)}</div>
                <div class="kpi-label">Fields Missing</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Review & Edit")

    with st.form("parse_edit_form"):
        edited_values = {}

        col1, col2 = st.columns(2)
        fields_left = SERVICE_RECORD_FIELDS[: len(SERVICE_RECORD_FIELDS) // 2]
        fields_right = SERVICE_RECORD_FIELDS[len(SERVICE_RECORD_FIELDS) // 2 :]

        with col1:
            for field_name, label, input_type, required in fields_left:
                current_value = getattr(job, field_name) or ""
                is_missing = field_name in job.missing_fields
                display_label = f"{label} *" if required else label
                if is_missing and required:
                    display_label = f"⚠️ {display_label}"

                if input_type == "textarea":
                    new_value = st.text_area(display_label, value=current_value)
                else:
                    new_value = st.text_input(display_label, value=current_value)
                edited_values[field_name] = new_value if new_value.strip() else None

        with col2:
            for field_name, label, input_type, required in fields_right:
                current_value = getattr(job, field_name) or ""
                is_missing = field_name in job.missing_fields
                display_label = f"{label} *" if required else label
                if is_missing and required:
                    display_label = f"⚠️ {display_label}"

                if input_type == "textarea":
                    new_value = st.text_area(display_label, value=current_value)
                else:
                    new_value = st.text_input(display_label, value=current_value)
                edited_values[field_name] = new_value if new_value.strip() else None

        col1, col2, col3 = st.columns(3)
        with col1:
            save_draft = st.form_submit_button("Save Draft", use_container_width=True)
        with col2:
            save_verify = st.form_submit_button(
                "Save & Verify", use_container_width=True
            )
        with col3:
            go_back = st.form_submit_button("Back", use_container_width=True)

    if go_back:
        st.session_state.parse_stage = "input"
        st.session_state.parsed_job = None
        st.rerun()

    if save_draft or save_verify:
        for field_name, value in edited_values.items():
            setattr(job, field_name, value)

        if save_verify:
            missing = job.get_missing_required_fields()
            if missing:
                labels = [
                    lbl for name, lbl, _, _ in SERVICE_RECORD_FIELDS if name in missing
                ]
                st.error(f"Missing required fields: {', '.join(labels)}")
                return
            job.status = JobStatus.VERIFIED
        else:
            job.status = JobStatus.DRAFT

        save_job(job)
        st.success(f"Job saved as {job.status.value}!")
        st.session_state.parse_stage = "input"
        st.session_state.parsed_job = None
        st.session_state.current_page = "Jobs"
        st.rerun()


def page_job_detail():
    """Job detail page."""
    job_id = st.session_state.get("current_job_id")
    if not job_id:
        st.warning("No job selected")
        return

    job = load_job(job_id)
    if not job:
        st.error("Job not found")
        return

    # Header
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(
            f'<h1 class="page-header">{job.invoice_number or "Job Details"}</h1>',
            unsafe_allow_html=True,
        )
        status_class = get_status_class(job.status.value)
        st.markdown(
            f'<span class="status-badge {status_class}">{job.status.value}</span>',
            unsafe_allow_html=True,
        )
    with col2:
        if st.button("Back to Jobs"):
            st.session_state.current_page = "Jobs"
            st.rerun()

    # Edit mode
    if "job_edit_mode" not in st.session_state:
        st.session_state.job_edit_mode = False

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button(
            "Edit" if not st.session_state.job_edit_mode else "Cancel",
            use_container_width=True,
        ):
            st.session_state.job_edit_mode = not st.session_state.job_edit_mode
            st.rerun()

    if st.session_state.job_edit_mode:
        _render_job_edit_form(job)
    else:
        _render_job_view(job)


def _render_job_view(job: Job):
    """Render job view."""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Service Information**")
        st.write(f"Date: {job.get_service_date_display()}")
        st.write(f"Customer: {job.customer_name or '—'}")
        st.write(f"Address: {job.customer_address or '—'}")
        st.write(f"Phone: {job.phone or '—'}")
        st.write(f"Technician: {job.technician or '—'}")
        st.write(f"Truck: {job.truck_id or '—'}")

    with col2:
        st.markdown("**Job Details**")
        st.write(f"Trap Size: {job.trap_size or '—'}")
        st.write(f"Gallons Pumped: {job.get_gallons_display()}")
        st.write(f"Disposal Facility: {job.disposal_facility or '—'}")
        st.write(f"Invoice Total: {job.get_invoice_total_display()}")
        st.write(f"Manifest #: {job.manifest_number or '—'}")

    if job.notes:
        st.markdown("**Notes**")
        st.write(job.notes)

    st.markdown("---")

    # Actions
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if job.status == JobStatus.DRAFT:
            if st.button("Mark Verified", use_container_width=True):
                if job.can_verify():
                    update_job(job.job_id, {"status": JobStatus.VERIFIED})
                    st.success("Job verified!")
                    st.rerun()
                else:
                    st.error("Missing required fields")

    with col2:
        st.download_button(
            "Export JSON",
            data=json.dumps(job.to_dict(), indent=2),
            file_name=f"{job.invoice_number or 'job'}.json",
            mime="application/json",
            use_container_width=True,
        )

    with col3:
        csv_data = pd.DataFrame([job.get_record_dict()]).to_csv(index=False)
        st.download_button(
            "Export CSV",
            data=csv_data,
            file_name=f"{job.invoice_number or 'job'}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col4:
        if st.button("Delete Job", use_container_width=True):
            st.session_state.confirm_delete = True

    if st.session_state.get("confirm_delete"):
        st.warning("Are you sure?")
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            if st.button("Yes, Delete", use_container_width=True):
                delete_job(job.job_id)
                st.session_state.confirm_delete = False
                st.session_state.current_page = "Jobs"
                st.rerun()
        with dcol2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_delete = False
                st.rerun()


def _render_job_edit_form(job: Job):
    """Render job edit form."""
    # Get string values for display in form
    service_date_val = job.service_date_str or (job.service_date.isoformat() if job.service_date else "")
    gallons_val = job.gallons_pumped_str or (f"{job.gallons_pumped:,.0f}" if job.gallons_pumped else "")
    invoice_val = job.invoice_total_str or (f"${job.invoice_total_cents/100:,.2f}" if job.invoice_total_cents else "")

    with st.form("edit_job_form"):
        col1, col2 = st.columns(2)

        with col1:
            invoice_number = st.text_input(
                "Invoice Number *", value=job.invoice_number or ""
            )
            service_date = st.text_input("Service Date *", value=service_date_val)
            customer_name = st.text_input(
                "Customer Name *", value=job.customer_name or ""
            )
            customer_address = st.text_input(
                "Address", value=job.customer_address or ""
            )
            phone = st.text_input("Phone", value=job.phone or "")
            technician = st.text_input("Technician", value=job.technician or "")

        with col2:
            trap_size = st.text_input("Trap Size", value=job.trap_size or "")
            gallons_pumped = st.text_input("Gallons Pumped", value=gallons_val)
            disposal_facility = st.text_input(
                "Disposal Facility", value=job.disposal_facility or ""
            )
            invoice_total = st.text_input("Invoice Total", value=invoice_val)
            manifest_number = st.text_input(
                "Manifest #", value=job.manifest_number or ""
            )
            truck_id = st.text_input("Truck ID", value=job.truck_id or "")

        notes = st.text_area("Notes", value=job.notes or "")

        status_options = [s.value for s in JobStatus]
        current_idx = status_options.index(job.status.value)
        status = st.selectbox("Status", status_options, index=current_idx)

        if st.form_submit_button("Save Changes", use_container_width=True):
            # The update_job function will handle string values in the database
            # which will be parsed back to typed values on load
            update_job(
                job.job_id,
                {
                    "invoice_number": invoice_number or None,
                    "service_date": service_date or None,
                    "customer_name": customer_name or None,
                    "customer_address": customer_address or None,
                    "phone": phone or None,
                    "technician": technician or None,
                    "trap_size": trap_size or None,
                    "gallons_pumped": gallons_pumped or None,
                    "disposal_facility": disposal_facility or None,
                    "invoice_total": invoice_total or None,
                    "manifest_number": manifest_number or None,
                    "truck_id": truck_id or None,
                    "notes": notes or None,
                    "status": status,
                },
            )
            st.success("Job updated!")
            st.session_state.job_edit_mode = False
            st.rerun()


# =============================================================================
# REPORTS PAGE
# =============================================================================


def page_reports():
    st.markdown('<h1 class="page-header">Reports</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-subtitle">Analytics and performance reports</p>',
        unsafe_allow_html=True,
    )

    # Date range
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        date_preset = st.selectbox(
            "Date Range",
            ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Year to Date"],
            index=2,
        )

    date_from, date_to = get_date_range(date_preset)

    # Summary stats
    kpis = get_dashboard_kpis(date_from=date_from, date_to=date_to)

    st.markdown("### Summary")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Jobs", kpis.jobs_completed + kpis.jobs_scheduled)
    with col2:
        st.metric("Total Revenue", format_currency(kpis.total_revenue))
    with col3:
        st.metric("Total Gallons", format_number(kpis.total_gallons))
    with col4:
        st.metric("Avg per Job", format_currency(kpis.avg_revenue_per_job))

    st.markdown("---")

    # Charts
    tab1, tab2, tab3 = st.tabs(["Jobs", "Revenue", "Technicians"])

    with tab1:
        st.markdown("### Jobs by Status")
        status_data = get_jobs_by_status(date_from, date_to)
        if status_data:
            df = pd.DataFrame(
                [{"Status": k, "Count": v} for k, v in status_data.items()]
            )
            st.bar_chart(df.set_index("Status"))

        st.markdown("### Jobs Over Time")
        jobs_data = get_jobs_by_date(date_from, date_to, group_by="day")
        if jobs_data:
            df = pd.DataFrame([{"Date": p.date, "Jobs": p.value} for p in jobs_data])
            st.line_chart(df.set_index("Date"))

    with tab2:
        st.markdown("### Revenue Over Time")
        revenue_data = get_revenue_by_date(date_from, date_to, group_by="day")
        if revenue_data:
            df = pd.DataFrame(
                [{"Date": p.date, "Revenue": p.value} for p in revenue_data]
            )
            st.line_chart(df.set_index("Date"))

        st.markdown("### Gallons Over Time")
        gallons_data = get_gallons_by_date(date_from, date_to, group_by="day")
        if gallons_data:
            df = pd.DataFrame(
                [{"Date": p.date, "Gallons": p.value} for p in gallons_data]
            )
            st.line_chart(df.set_index("Date"))

    with tab3:
        st.markdown("### Jobs by Technician")
        tech_data = get_jobs_by_technician(date_from, date_to)
        if tech_data:
            df = pd.DataFrame(
                [{"Technician": k, "Jobs": v} for k, v in tech_data.items()]
            )
            st.bar_chart(df.set_index("Technician"))

        st.markdown("### Top Customers")
        top_customers = get_top_customers_by_revenue(
            limit=10, date_from=date_from, date_to=date_to
        )
        if top_customers:
            df = pd.DataFrame(
                [{"Customer": name, "Revenue": rev} for name, rev in top_customers]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)

    # Export
    st.markdown("---")
    st.markdown("### Export Data")

    col1, col2 = st.columns(2)
    with col1:
        jobs = list_jobs(date_from=date_from, date_to=date_to, limit=1000)
        if jobs:
            jobs_df = pd.DataFrame([j.to_dict() for j in jobs])
            st.download_button(
                "Export Jobs CSV",
                data=jobs_df.to_csv(index=False),
                file_name=f"jobs_{date_from}_{date_to}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    with col2:
        customers = list_customers(limit=1000)
        if customers:
            cust_df = pd.DataFrame([c.to_dict() for c in customers])
            st.download_button(
                "Export Customers CSV",
                data=cust_df.to_csv(index=False),
                file_name="customers.csv",
                mime="text/csv",
                use_container_width=True,
            )


# =============================================================================
# SETTINGS PAGE
# =============================================================================


def page_settings():
    st.markdown('<h1 class="page-header">Settings</h1>', unsafe_allow_html=True)

    st.markdown("### Database")
    col1, col2 = st.columns(2)

    with col1:
        st.write(f"Customers: {count_customers()}")
        st.write(f"Sites: {count_sites()}")
        st.write(f"Jobs: {count_jobs()}")

    with col2:
        if st.button("Reset Database", type="secondary"):
            st.session_state.confirm_reset = True

        if st.session_state.get("confirm_reset"):
            st.warning("This will DELETE ALL DATA. Are you sure?")
            dcol1, dcol2 = st.columns(2)
            with dcol1:
                if st.button("Yes, Reset Everything"):
                    from trap.storage import reset_db

                    reset_db()
                    st.session_state.confirm_reset = False
                    st.success("Database reset!")
                    st.rerun()
            with dcol2:
                if st.button("Cancel Reset"):
                    st.session_state.confirm_reset = False
                    st.rerun()

    st.markdown("---")
    st.markdown("### About")
    st.write("Trap CRM v0.3.0")
    st.write("FOG Service Management System")


# =============================================================================
# MAIN APP
# =============================================================================


def main():
    inject_styles()

    # Initialize page state
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Dashboard"

    # Sidebar navigation
    with st.sidebar:
        st.markdown('<div class="nav-logo">TRAP CRM</div>', unsafe_allow_html=True)

        nav_options = [
            "Dashboard",
            "Customers",
            "Jobs",
            "Reports",
            "Settings",
        ]

        for nav in nav_options:
            if st.button(nav, key=f"nav_{nav}", use_container_width=True):
                st.session_state.current_page = nav
                st.rerun()

        st.markdown("---")
        st.markdown(
            '<div style="text-align: center; color: #94a3b8; font-size: 0.75rem;">v0.3.0</div>',
            unsafe_allow_html=True,
        )

    # Page routing
    pages = {
        "Dashboard": page_dashboard,
        "Customers": page_customers,
        "New Customer": page_new_customer,
        "Customer Detail": page_customer_detail,
        "Jobs": page_jobs,
        "New Job": page_new_job,
        "Parse Job": page_parse_job,
        "Job Detail": page_job_detail,
        "Reports": page_reports,
        "Settings": page_settings,
    }

    current = st.session_state.current_page
    if current in pages:
        pages[current]()
    else:
        page_dashboard()


if __name__ == "__main__":
    main()
