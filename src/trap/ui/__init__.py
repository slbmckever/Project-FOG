"""
Trap CRM UI module.

Provides modular page components, styles, and routing.
"""

from .router import go, get_current_page, clear_page_state
from .styles import inject_styles
from .components import (
    kpi_card,
    status_badge,
    render_job_fields,
    format_currency,
    format_number,
    format_gallons,
)

__all__ = [
    "go",
    "get_current_page",
    "clear_page_state",
    "inject_styles",
    "kpi_card",
    "status_badge",
    "render_job_fields",
    "format_currency",
    "format_number",
    "format_gallons",
]
