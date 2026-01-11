"""
Reusable UI components for Trap CRM.
"""

from datetime import datetime, timedelta

import streamlit as st


def format_currency(cents: int | None) -> str:
    """Format cents as currency string."""
    if cents is None:
        return "$0.00"
    return f"${cents / 100:,.2f}"


def format_currency_input(value: str | None) -> int:
    """Parse currency input string to cents."""
    if not value:
        return 0
    cleaned = value.replace("$", "").replace(",", "").strip()
    try:
        return int(float(cleaned) * 100)
    except ValueError:
        return 0


def format_number(value: float | int | None) -> str:
    """Format number with commas."""
    if value is None:
        return "0"
    if value >= 1000:
        return f"{value:,.0f}"
    return f"{value:.1f}"


def format_gallons(gallons: float | None) -> str:
    """Format gallons with unit."""
    if gallons is None or gallons == 0:
        return "—"
    return f"{gallons:,.0f} gal"


def format_date(date_val: datetime | str | None) -> str:
    """Format date for display."""
    if date_val is None:
        return "—"
    if isinstance(date_val, str):
        try:
            date_val = datetime.fromisoformat(date_val)
        except ValueError:
            return date_val
    return date_val.strftime("%b %d, %Y")


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
        "Needs Docs": "needs-docs",
    }
    return f"status-{status_map.get(status, 'draft')}"


def kpi_card(value: str, label: str, color_class: str = "") -> None:
    """Render a KPI card."""
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-value {color_class}">{value}</div>
            <div class="kpi-label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> None:
    """Render a status badge."""
    status_class = get_status_class(status)
    st.markdown(
        f'<span class="status-badge {status_class}">{status}</span>',
        unsafe_allow_html=True,
    )


def completeness_bar(percentage: int) -> None:
    """Render a completeness progress bar."""
    if percentage >= 100:
        fill_class = "completeness-100"
    elif percentage >= 75:
        fill_class = "completeness-75"
    elif percentage >= 50:
        fill_class = "completeness-50"
    else:
        fill_class = "completeness-25"

    st.markdown(
        f"""
        <div class="completeness-bar">
            <div class="completeness-fill {fill_class}" style="width: {percentage}%"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str | None = None) -> None:
    """Render a page header with optional subtitle."""
    st.markdown(f'<h1 class="page-header">{title}</h1>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(
            f'<p class="page-subtitle">{subtitle}</p>', unsafe_allow_html=True
        )


def render_job_fields(job, editable: bool = True) -> dict:
    """
    Render job fields in a form and return edited values.

    This centralizes job field rendering to prevent drift between
    New Job, Parse Edit, and Job Edit forms.
    """
    from trap.models import SERVICE_RECORD_FIELDS

    edited_values = {}
    col1, col2 = st.columns(2)

    fields_left = SERVICE_RECORD_FIELDS[: len(SERVICE_RECORD_FIELDS) // 2]
    fields_right = SERVICE_RECORD_FIELDS[len(SERVICE_RECORD_FIELDS) // 2 :]

    with col1:
        for field_name, label, input_type, required in fields_left:
            current_value = getattr(job, field_name, "") or ""
            display_label = f"{label} *" if required else label

            if input_type == "textarea":
                if editable:
                    new_value = st.text_area(display_label, value=current_value)
                else:
                    st.write(f"**{label}:** {current_value or '—'}")
                    new_value = current_value
            elif input_type == "date":
                if editable:
                    new_value = st.text_input(display_label, value=current_value)
                else:
                    st.write(f"**{label}:** {format_date(current_value)}")
                    new_value = current_value
            elif input_type == "currency":
                if editable:
                    new_value = st.text_input(display_label, value=current_value)
                else:
                    st.write(f"**{label}:** {current_value or '—'}")
                    new_value = current_value
            else:
                if editable:
                    new_value = st.text_input(display_label, value=current_value)
                else:
                    st.write(f"**{label}:** {current_value or '—'}")
                    new_value = current_value

            if editable:
                edited_values[field_name] = new_value if new_value.strip() else None
            else:
                edited_values[field_name] = current_value if current_value else None

    with col2:
        for field_name, label, input_type, required in fields_right:
            current_value = getattr(job, field_name, "") or ""
            display_label = f"{label} *" if required else label

            if input_type == "textarea":
                if editable:
                    new_value = st.text_area(display_label, value=current_value)
                else:
                    st.write(f"**{label}:** {current_value or '—'}")
                    new_value = current_value
            else:
                if editable:
                    new_value = st.text_input(display_label, value=current_value)
                else:
                    st.write(f"**{label}:** {current_value or '—'}")
                    new_value = current_value

            if editable:
                edited_values[field_name] = new_value if new_value.strip() else None
            else:
                edited_values[field_name] = current_value if current_value else None

    return edited_values


def confirm_dialog(
    key: str,
    message: str = "Are you sure?",
    confirm_label: str = "Yes, Delete",
    cancel_label: str = "Cancel",
) -> bool | None:
    """
    Render a confirmation dialog.

    Returns:
        True if confirmed, False if cancelled, None if not yet answered.
    """
    if not st.session_state.get(key):
        return None

    st.warning(message)
    col1, col2 = st.columns(2)

    with col1:
        if st.button(confirm_label, use_container_width=True):
            st.session_state[key] = False
            return True

    with col2:
        if st.button(cancel_label, use_container_width=True):
            st.session_state[key] = False
            st.rerun()

    return None
