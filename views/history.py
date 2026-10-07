"""
views/history.py
----------------
Resume History — Phase 5.

- Lists all past resumes with their latest analysis.
- Lets the user drill into a single resume and see all its versions.
- Side-by-side version comparison.
"""

from __future__ import annotations

import json

import streamlit as st
import plotly.graph_objects as go

from database import database


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _score_color(score: int) -> str:
    if score >= 75:
        return "#16a34a"
    if score >= 50:
        return "#d97706"
    return "#dc2626"


def _score_pill(score: int) -> str:
    color = _score_color(score)
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:999px;'
        f'background:{color}1a;color:{color};font-weight:650;font-size:0.85rem;">'
        f'{score}/100</span>'
    )


def _version_chart(versions: list[dict]) -> go.Figure:
    labels = [f"v{i+1}" for i in range(len(versions))]
    overall = [v["overall_score"] for v in versions]
    ats = [v["ats_score"] for v in versions]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=overall, mode="lines+markers",
        name="Overall", line=dict(color="#4f46e5", width=3),
        marker=dict(size=9),
    ))
    fig.add_trace(go.Scatter(
        x=labels, y=ats, mode="lines+markers",
        name="ATS", line=dict(color="#0891b2", width=3, dash="dot"),
        marker=dict(size=9),
    ))
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis=dict(range=[0, 105], title="Score", gridcolor="#f1f5f9"),
        xaxis=dict(title=""),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color="#0f172a"),
    )
    return fig


def _comparison_table(versions: list[dict]) -> None:
    """Side-by-side comparison of all versions."""
    if not versions:
        return

    dimensions = [
        ("Overall", "overall_score"),
        ("ATS", "ats_score"),
        ("Content", "content_score"),
        ("Skills", "skills_score"),
        ("Experience", "experience_score"),
        ("Projects", "projects_score"),
        ("Formatting", "formatting_score"),
    ]

    header = ["Dimension"] + [f"v{i+1}" for i in range(len(versions))]
    rows = [header]
    for label, key in dimensions:
        row = [label] + [str(v.get(key, 0)) for v in versions]
        rows.append(row)

    # Build HTML table
    html = '<table class="compare-table"><thead><tr>'
    for h in rows[0]:
        html += f"<th>{h}</th>"
    html += "</tr></thead><tbody>"
    for row in rows[1:]:
        html += "<tr>"
        html += f"<td><b>{row[0]}</b></td>"
        for val in row[1:]:
            try:
                n = int(val)
                color = _score_color(n)
                html += f'<td style="color:{color};font-weight:600;">{val}</td>'
            except ValueError:
                html += f"<td>{val}</td>"
        html += "</tr>"
    html += "</tbody></table>"

    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def render() -> None:
    st.markdown('<h1 class="page-title">🕒 Resume History</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-sub">All your analyzed resumes with score history and version comparison.</p>',
        unsafe_allow_html=True,
    )

    resumes = database.get_all_resumes()

    if not resumes:
        st.info(
            "📭 **No history yet.**\n\n"
            "Go to the **📄 Resume Analyzer** and analyze a resume to start building history."
        )
        return

    # ---- Top summary -------------------------------------------------
    total = len(resumes)
    avg_score = int(round(sum(r.get("overall_score") or 0 for r in resumes) / total)) if total else 0
    best = max((r.get("overall_score") or 0 for r in resumes), default=0)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("📄 Total Resumes", total)
    with c2:
        st.metric("📊 Average Score", f"{avg_score}/100")
    with c3:
        st.metric("🏆 Best Score", f"{best}/100")

    st.markdown("---")

    # ---- Filters -----------------------------------------------------
    st.markdown("### 📋 Resume List")

    all_names = sorted({r["name"] for r in resumes if r.get("name")})

    selected_name = st.selectbox(
        "Select a resume to view its versions",
        options=["— All —"] + all_names,
        index=0,
    )

    # ---- List view ---------------------------------------------------
    if selected_name == "— All —":
        for r in resumes:
            with st.container():
                cols = st.columns([3, 1, 1, 1, 1])
                with cols[0]:
                    st.markdown(f"**{r['name']}**")
                    st.caption(f"📅 {r.get('created_at', '')}")
                with cols[1]:
                    st.markdown(_score_pill(r.get("overall_score") or 0), unsafe_allow_html=True)
                with cols[2]:
                    st.caption(f"ATS: {r.get('ats_score') or 0}")
                with cols[3]:
                    st.caption(f"Skills: {r.get('skills_count') or 0}")
                with cols[4]:
                    if st.button("🗑️", key=f"del_resume_{r['id']}", help="Delete this resume"):
                        if database.delete_resume(r["id"]):
                            st.success("Deleted.")
                            st.rerun()
                st.markdown("---")
        return

    # ---- Single resume view ------------------------------------------
    versions = database.get_analyses_for_resume(selected_name)
    if not versions:
        st.warning(f"No analyses found for **{selected_name}**.")
        return

    st.success(f"Showing **{len(versions)} version(s)** of **{selected_name}**")

    # Trend chart
    st.markdown("### 📈 Score Trend")
    st.plotly_chart(_version_chart(versions), use_container_width=True)

    # Version comparison table
    st.markdown("### 📊 Version Comparison")
    _comparison_table(versions)

    # ---- Version details ---------------------------------------------
    st.markdown("### 🔍 Version Details")
    version_labels = [f"v{i+1} — {v['created_at']} — Score {v['overall_score']}"
                      for i, v in enumerate(versions)]
    chosen_label = st.selectbox("Pick a version to inspect", options=version_labels, index=len(versions)-1)
    idx = version_labels.index(chosen_label)
    chosen = versions[idx]

    try:
        analysis_data = json.loads(chosen.get("analysis_json") or "{}")
        skills_data = json.loads(chosen.get("skills_json") or "{}")
    except (ValueError, TypeError):
        analysis_data = {}
        skills_data = {}

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**✅ Strengths**")
        for s in analysis_data.get("strengths", []) or ["— none —"]:
            st.markdown(f"- {s}")

        st.markdown("**⚠️ Weaknesses**")
        for w in analysis_data.get("weaknesses", []) or ["— none —"]:
            st.markdown(f"- {w}")

    with c2:
        st.markdown("**💡 Recommendations**")
        for r in analysis_data.get("recommendations", []) or ["— none —"]:
            st.markdown(f"- {r}")

        st.markdown("**🧩 Skills Detected**")
        st.metric("Total", skills_data.get("total", 0))

    # ---- Actions -----------------------------------------------------
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("➡️ Analyze a new version", use_container_width=True):
            st.session_state.page = "📄 Resume Analyzer"
            st.rerun()
    with c2:
        if st.button("🎯 Match with a job", use_container_width=True):
            st.session_state.page = "🎯 Job Matcher"
            st.rerun()
    with c3:
        if st.button("🗑️ Delete ALL history", use_container_width=True, type="secondary"):
            if database.clear_all():
                st.success("All history cleared.")
                st.rerun()