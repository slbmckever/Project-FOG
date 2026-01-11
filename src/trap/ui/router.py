"""
Navigation router for Trap CRM.

Provides safe page navigation with state management.
"""

import streamlit as st


def go(page: str, **kwargs) -> None:
    """
    Navigate to a page with optional state variables.

    Usage:
        go("Job Detail", current_job_id=str(job.job_id))
        go("Site Detail", current_site_id=str(site.site_id))
    """
    # Clear any stale confirmation flags
    clear_confirmations()

    st.session_state.current_page = page
    for key, value in kwargs.items():
        st.session_state[key] = value
    st.rerun()


def get_current_page() -> str:
    """Get the current page, defaulting to Dashboard."""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Dashboard"
    return st.session_state.current_page


def clear_page_state(*keys: str) -> None:
    """Clear specific session state keys."""
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]


def clear_confirmations() -> None:
    """Clear all confirmation dialogs on page change."""
    confirmation_keys = [
        "confirm_delete",
        "confirm_reset",
        "confirm_delete_job_id",
        "confirm_delete_customer_id",
        "confirm_delete_site_id",
    ]
    for key in confirmation_keys:
        if key in st.session_state:
            del st.session_state[key]


def init_edit_mode(entity: str) -> bool:
    """Initialize and return edit mode state for an entity."""
    key = f"{entity}_edit_mode"
    if key not in st.session_state:
        st.session_state[key] = False
    return st.session_state[key]


def toggle_edit_mode(entity: str) -> None:
    """Toggle edit mode for an entity."""
    key = f"{entity}_edit_mode"
    st.session_state[key] = not st.session_state.get(key, False)
    st.rerun()
