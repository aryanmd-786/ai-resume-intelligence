"""
AI Resume Intelligence Platform
-------------------------------
Main Streamlit entry point.

Run with:
    python -m streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

import config
from database import database
from services import ollama_service
from utils.error_handlers import safe_render
from utils.helpers import load_css
from views import (
    analytics,
    analyzer,
    builder,
    career_assistant,
    dashboard,
    feedback,          # 👈 Feedback module import kiya
    history,
    job_matcher,
    skill_gap,
)
from views import auth as auth_view          # 🔐 ADDED
from views import settings as settings_view


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=config.APP_NAME,
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------
load_css("assets/style.css")

# ---------------------------------------------------------------------------
# Ensure SQLite schema exists (also creates users table + user_id migration)
# ---------------------------------------------------------------------------
database.init_db()

# ---------------------------------------------------------------------------
# Session state defaults (ALL keys — keeps pages from crashing)
# ---------------------------------------------------------------------------
_DEFAULTS = {
    "page": "🏠 Dashboard",

    # 🔐 Auth
    "logged_in": False,
    "user_id": None,
    "username": None,
    "full_name": None,

    # Analyzer / shared resume data
    "last_analysis": None,
    "last_analysis_id": None,
    "last_resume_text": None,
    "last_resume_name": None,
    "analysis_result": None,
    "skills_result": None,
    "ats_result": None,

    # Job matcher / skill gap
    "last_job_match": None,
    "last_job_description": None,
    "job_match_result": None,
    "skill_gap_result": None,

    # Builder
    "builder_data": {},
    "builder_seed": None,
    "_builder_seed_notice": None,

    # Career assistant
    "chat_history": [],

    # Misc
    "resume_version": 0,

    # Builder export paths (used by download buttons)
    "_pdf_path": None,
    "_pdf_name": None,
    "_docx_path": None,
    "_docx_name": None,
}
for _key, _value in _DEFAULTS.items():
    st.session_state.setdefault(_key, _value)


# ---------------------------------------------------------------------------
# 🔐 AUTH GATE — must run BEFORE any sidebar/page render
# ---------------------------------------------------------------------------
def _logout() -> None:
    """Clear session and send user back to login page."""
    for key in (
        "logged_in",
        "user_id",
        "username",
        "full_name",
        # also reset user-scoped state so next login starts fresh
        "page",
        "last_analysis",
        "last_analysis_id",
        "last_resume_text",
        "last_resume_name",
        "analysis_result",
        "skills_result",
        "ats_result",
        "last_job_match",
        "last_job_description",
        "job_match_result",
        "skill_gap_result",
        "builder_data",
        "builder_seed",
        "chat_history",
        "resume_version",
        "_pdf_path",
        "_pdf_name",
        "_docx_path",
        "_docx_name",
    ):
        st.session_state.pop(key, None)
    st.rerun()


if not st.session_state.get("logged_in") or not st.session_state.get("user_id"):
    # Show only the login/signup screen. Everything below is skipped.
    auth_view.render_auth_page()
    st.stop()


# ---------------------------------------------------------------------------
# Page registry
# ---------------------------------------------------------------------------
PAGES: dict[str, callable] = {
    "🏠 Dashboard": dashboard.render,
    "📄 Resume Analyzer": analyzer.render,
    "✨ Resume Builder": builder.render,
    "🎯 Job Matcher": job_matcher.render,
    "🧠 Skill Gap": skill_gap.render,
    "📊 Resume Analytics": analytics.render,
    "🕒 Resume History": history.render,
    "🤖 AI Career Assistant": career_assistant.render,
    "💬 Feedback": feedback.render,          # 👈 Feedback page add kiya
    "⚙️ Settings": settings_view.render,
}


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f"""
        <div class="app-brand">
            <div class="app-logo">🧠</div>
            <div>
                <div class="app-title">{config.APP_NAME}</div>
                <div class="app-subtitle">{config.APP_TAGLINE} · v{config.APP_VERSION}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # 🔐 User greeting + logout
    st.markdown(
        f"**👋 Hi, {st.session_state.get('full_name') or st.session_state.get('username')}**"
    )
    st.caption(f"@{st.session_state.get('username')}")
    if st.button("🚪 Logout", key="nav::logout", use_container_width=True):
        _logout()
    st.markdown("---")

    # Navigation buttons
    for label in PAGES:
        is_active = st.session_state.page == label
        if st.button(
            label,
            key=f"nav::{label}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.page = label
            st.rerun()

    st.markdown("---")

    # Ollama status indicator — cached for 30s to avoid hammering the server
    @st.cache_data(ttl=30, show_spinner=False)
    def _cached_ollama_status():
        return ollama_service.check_connection()

    _ok, _msg = _cached_ollama_status()
    if _ok:
        st.markdown(
            '<div class="status-badge ok">● Ollama Connected</div>',
            unsafe_allow_html=True,
        )
        st.caption(f"Model: `{config.OLLAMA_MODEL}`")
    else:
        st.markdown(
            '<div class="status-badge err">● Ollama Offline</div>',
            unsafe_allow_html=True,
        )
        st.caption(_msg)

    st.markdown("---")
    st.caption("🔒 Processed locally via Ollama. No third-party AI calls.")

# ---------------------------------------------------------------------------
# Route to selected page — with top-level crash protection
# ---------------------------------------------------------------------------
_page_fn = PAGES.get(st.session_state.page, dashboard.render)
_page_name = st.session_state.page
safe_render(_page_fn, page_name=_page_name)