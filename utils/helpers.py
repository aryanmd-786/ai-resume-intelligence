"""
utils/helpers.py
----------------
Small, reusable helpers used across the UI.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

import config


def load_css(relative_path: str) -> None:
    """Inject a CSS file into the Streamlit page."""
    css_path: Path = config.BASE_DIR / relative_path
    if css_path.exists():
        st.markdown(
            f"<style>{css_path.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )


def goto(page_label: str) -> None:
    """Navigate to another page and rerun the app."""
    st.session_state.page = page_label
    st.rerun()


def metric_card(label: str, value: str, sub: str = "", accent: str = "primary") -> str:
    """Return HTML for a modern metric card."""
    return f"""
    <div class="metric-card accent-{accent}">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{sub}</div>
    </div>
    """


def section_header(title: str, subtitle: str = "") -> str:
    """Return HTML for a section header."""
    sub_html = f'<p class="section-sub">{subtitle}</p>' if subtitle else ""
    return f"""
    <div class="section-header">
        <h3 class="section-title">{title}</h3>
        {sub_html}
    </div>
    """


def safe_str(value, default: str = "—") -> str:
    """Return a printable string, never None."""
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def safe_int(value, default: int = 0) -> int:
    """Best-effort conversion to int."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default