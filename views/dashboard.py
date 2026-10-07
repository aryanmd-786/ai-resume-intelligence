"""
views/dashboard.py
------------------
Main dashboard — the first thing the user sees.
Shows metrics from SQLite history and quick actions.
"""

from __future__ import annotations

import streamlit as st

import config
from database import database
from utils.helpers import goto, metric_card, section_header


def _quick_action(label: str, target_page: str, key: str) -> None:
    if st.button(label, key=key, use_container_width=True):
        goto(target_page)


def render() -> None:
    st.markdown('<h1 class="page-title">Dashboard</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-sub">Your AI resume intelligence workspace at a glance.</p>',
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # Session + DB data
    # ------------------------------------------------------------------
    analysis = st.session_state.get("last_analysis") or {}
    job_match_dict = st.session_state.get("last_job_match") or {}

    stats = database.get_dashboard_stats()

    overall_score = stats.get("latest_overall_score") or analysis.get("overall_score") or 0
    ats_score = stats.get("latest_ats_score") or analysis.get("ats_score") or 0
    skills_count = stats.get("latest_skills_count") or analysis.get("skills_count") or 0
    job_match = stats.get("latest_match_score") or job_match_dict.get("match_score") or 0
    total_resumes = stats.get("total_resumes", 0)
    avg_score = stats.get("avg_overall_score", 0)

    # ------------------------------------------------------------------
    # Metric cards row
    # ------------------------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            metric_card(
                "LATEST OVERALL",
                f"{overall_score}/100" if overall_score else "—",
                "Composite resume quality",
                "primary",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            metric_card(
                "LATEST ATS",
                f"{ats_score}/100" if ats_score else "—",
                "AI-based ATS-style analysis",
                "success",
            ),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            metric_card(
                "SKILLS DETECTED",
                f"{skills_count}",
                "Across all categories",
                "warning",
            ),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            metric_card(
                "JOB MATCH",
                f"{job_match}%" if job_match else "—",
                "Latest job description",
                "accent",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Quick actions
    # ------------------------------------------------------------------
    st.markdown(section_header("Quick Actions"), unsafe_allow_html=True)

    q1, q2, q3, q4, q5 = st.columns(5)
    with q1:
        _quick_action("📄 Analyze Resume", "📄 Resume Analyzer", "qa_analyze")
    with q2:
        _quick_action("✨ Build Resume", "✨ Resume Builder", "qa_build")
    with q3:
        _quick_action("🎯 Match Job", "🎯 Job Matcher", "qa_match")
    with q4:
        _quick_action("🧠 Skill Gap", "🧠 Skill Gap", "qa_gap")
    with q5:
        _quick_action("🤖 AI Assistant", "🤖 AI Career Assistant", "qa_chat")

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Status panel
    # ------------------------------------------------------------------
    left, right = st.columns([2, 1])

    with left:
        st.markdown(section_header("Welcome to Your Workspace"), unsafe_allow_html=True)

        if total_resumes == 0:
            st.info(
                "**No resume analyzed yet.** Head over to the **Resume Analyzer** "
                "to upload a PDF or DOCX and get AI-powered insights."
            )
        else:
            st.success(
                f"📚 You've analyzed **{total_resumes}** resume(s) · "
                f"Average score: **{avg_score}/100**"
            )

        st.markdown(
            """
            **How this platform works**

            1. **Upload** your existing resume (PDF / DOCX) in the Analyzer.
            2. The local AI (**Ollama**) scores it across ATS, content, skills, experience, projects and formatting.
            3. Hit **Improve Resume** to auto-fill the Builder with cleaned-up content.
            4. Paste a **Job Description** to see your match % and missing skills.
            5. Export a polished resume as **PDF** or **DOCX**.

            All processing happens **locally** on your machine.
            """
        )

    with right:
        st.markdown(section_header("System Status"), unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="info-panel">
                <div class="info-row"><span>Application</span><b>v{config.APP_VERSION}</b></div>
                <div class="info-row"><span>AI Engine</span><b>Ollama (local)</b></div>
                <div class="info-row"><span>Model</span><b>{config.OLLAMA_MODEL}</b></div>
                <div class="info-row"><span>Resumes Saved</span><b>{total_resumes}</b></div>
                <div class="info-row"><span>Privacy</span><b>100% Local</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )