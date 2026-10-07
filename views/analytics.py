"""
views/analytics.py
------------------
Resume Analytics — Phase 5.

Charts built from SQLite history:
- Overall score trend
- ATS score trend
- Skills count trend
- Job match trend
- Skill category distribution (from latest analysis)
"""

from __future__ import annotations

import json

import streamlit as st
import plotly.graph_objects as go

from database import database


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------
def _empty_state(msg: str) -> None:
    st.info(msg)


def _multi_score_trend(analyses: list[dict]) -> go.Figure:
    labels = [f"#{i+1}" for i in range(len(analyses))]
    fig = go.Figure()

    series = [
        ("Overall", "overall_score", "#4f46e5", "solid"),
        ("ATS", "ats_score", "#0891b2", "solid"),
        ("Content", "content_score", "#16a34a", "dot"),
        ("Skills", "skills_score", "#d97706", "dot"),
        ("Experience", "experience_score", "#7c3aed", "dash"),
        ("Projects", "projects_score", "#dc2626", "dash"),
        ("Formatting", "formatting_score", "#0ea5e9", "dashdot"),
    ]

    for name, key, color, dash in series:
        fig.add_trace(go.Scatter(
            x=labels,
            y=[a.get(key, 0) for a in analyses],
            mode="lines+markers",
            name=name,
            line=dict(color=color, width=2, dash=dash),
            marker=dict(size=6),
        ))

    fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis=dict(range=[0, 105], title="Score", gridcolor="#f1f5f9"),
        xaxis=dict(title="Analysis #"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color="#0f172a"),
        hovermode="x unified",
    )
    return fig


def _job_match_trend(matches: list[dict]) -> go.Figure:
    labels = [f"#{i+1}" for i in range(len(matches))]
    scores = [m.get("match_score", 0) for m in matches]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=scores,
        mode="lines+markers",
        line=dict(color="#16a34a", width=3),
        marker=dict(size=9, color="#16a34a"),
        fill="tozeroy",
        fillcolor="rgba(22, 163, 74, 0.12)",
        name="Match Score",
    ))
    fig.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis=dict(range=[0, 105], title="Match %", gridcolor="#f1f5f9"),
        xaxis=dict(title="Match #"),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color="#0f172a"),
    )
    return fig


def _skills_count_trend(analyses: list[dict]) -> go.Figure:
    labels = [f"#{i+1}" for i in range(len(analyses))]
    counts = [a.get("skills_count", 0) for a in analyses]

    fig = go.Figure(data=[
        go.Bar(
            x=labels, y=counts,
            marker=dict(color="#4f46e5"),
            text=counts, textposition="outside",
        )
    ])
    fig.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis=dict(title="Skills Detected", gridcolor="#f1f5f9"),
        xaxis=dict(title="Analysis #"),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color="#0f172a"),
    )
    return fig


def _latest_skills_pie(latest_analysis: dict) -> go.Figure | None:
    try:
        skills = json.loads(latest_analysis.get("skills_json") or "{}")
    except (ValueError, TypeError):
        skills = {}

    if not skills:
        return None

    labels = {
        "programming_languages": "Programming",
        "frameworks": "Frameworks",
        "databases": "Databases",
        "cloud": "Cloud",
        "tools": "Tools",
        "technical_skills": "Technical",
        "soft_skills": "Soft Skills",
    }
    cats = [(v, len(skills.get(k, []) or [])) for k, v in labels.items()]
    cats = [(l, c) for l, c in cats if c > 0]

    if not cats:
        return None

    fig = go.Figure(go.Pie(
        labels=[c[0] for c in cats],
        values=[c[1] for c in cats],
        hole=0.55,
        marker=dict(colors=[
            "#4f46e5", "#0891b2", "#16a34a", "#d97706",
            "#dc2626", "#7c3aed", "#0ea5e9",
        ]),
        textinfo="label+value",
    ))
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color="#0f172a"),
    )
    return fig


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def render() -> None:
    st.markdown('<h1 class="page-title">📊 Resume Analytics</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-sub">Track your resume improvement over time across every metric.</p>',
        unsafe_allow_html=True,
    )

    analyses = database.get_all_analyses()
    matches = database.get_all_job_matches()

    if not analyses and not matches:
        st.info(
            "📭 **No analytics data yet.**\n\n"
            "Analyze at least one resume to see charts here."
        )
        return

    # ---- KPI row -----------------------------------------------------
    stats = database.get_dashboard_stats()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("📄 Resumes Analyzed", stats["total_resumes"])
    with c2:
        st.metric("📈 Avg Overall Score", f"{stats['avg_overall_score']}/100")
    with c3:
        st.metric("🎯 Job Matches", stats["total_matches"])
    with c4:
        st.metric("⭐ Latest Match", f"{stats['latest_match_score']}%" if stats["latest_match_score"] else "—")

    st.markdown("---")

    # ---- Score trend -------------------------------------------------
    if analyses:
        st.markdown("### 📈 Score Trend Over Time")
        st.caption("Every analysis is a version. Watch each metric improve.")
        st.plotly_chart(_multi_score_trend(analyses), use_container_width=True)

        # ---- Skills count + pie -------------------------------------
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("### 🧩 Skills Detected Per Version")
            st.plotly_chart(_skills_count_trend(analyses), use_container_width=True)
        with c2:
            st.markdown("### 🥧 Latest Skills Distribution")
            fig = _latest_skills_pie(analyses[-1])
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No skills data for the latest analysis.")

    # ---- Job match trend --------------------------------------------
    st.markdown("---")
    if matches:
        st.markdown("### 🎯 Job Match Trend")
        st.caption("How well your resume matched the job descriptions you tested.")
        st.plotly_chart(_job_match_trend(matches), use_container_width=True)

        # Match stats
        best = max(m.get("match_score", 0) for m in matches)
        avg = int(round(sum(m.get("match_score", 0) for m in matches) / len(matches)))
        latest = matches[-1].get("match_score", 0)

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Best Match", f"{best}%")
        with m2:
            st.metric("Average Match", f"{avg}%")
        with m3:
            st.metric("Latest Match", f"{latest}%")
    else:
        st.markdown("### 🎯 Job Match Trend")
        _empty_state("No job matches yet. Run the 🎯 Job Matcher to populate this chart.")

    # ---- Actions -----------------------------------------------------
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📄 Analyze a new resume", use_container_width=True, type="primary"):
            st.session_state.page = "📄 Resume Analyzer"
            st.rerun()
    with c2:
        if st.button("🎯 Run a job match", use_container_width=True):
            st.session_state.page = "🎯 Job Matcher"
            st.rerun()