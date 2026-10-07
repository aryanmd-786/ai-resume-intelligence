"""
views/skill_gap.py
------------------
Skill Gap Analysis — Phase 4.

Consumes the skill gap result computed by the Job Matcher.
"""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def _chips(items: list[str], kind: str) -> str:
    if not items:
        return '<span class="chip chip-muted">None</span>'
    return "".join(f'<span class="chip chip-{kind}">{i}</span>' for i in items)


def _level_to_score(level: str) -> int:
    return {"Strong": 90, "Intermediate": 65, "Basic": 35}.get(level, 50)


def _gap_bar(skills: list[dict]) -> go.Figure:
    """Horizontal bar chart of skill proficiency."""
    if not skills:
        return None

    # Sort: Strong first (highest), then down
    items = sorted(skills, key=lambda x: _level_to_score(x.get("level", "")), reverse=True)
    names = [s["skill"] for s in items]
    scores = [_level_to_score(s.get("level", "")) for s in items]

    colors = []
    for s in scores:
        if s >= 80:
            colors.append("#16a34a")
        elif s >= 55:
            colors.append("#d97706")
        else:
            colors.append("#dc2626")

    fig = go.Figure(go.Bar(
        x=scores,
        y=names,
        orientation="h",
        marker=dict(color=colors),
        text=[f"{s}%" for s in scores],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Proficiency: %{x}%<extra></extra>",
    ))
    fig.update_layout(
        height=max(240, 32 * len(names)),
        margin=dict(l=10, r=40, t=10, b=10),
        xaxis=dict(range=[0, 105], showgrid=True, gridcolor="#f1f5f9", title="Proficiency"),
        yaxis=dict(autorange="reversed"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color="#0f172a"),
        showlegend=False,
    )
    return fig


def _donut(have: int, improve: int, missing: int) -> go.Figure:
    total = have + improve + missing
    if total == 0:
        return None

    fig = go.Figure(go.Pie(
        labels=["Already Have", "Need Improvement", "Missing"],
        values=[have, improve, missing],
        hole=0.62,
        marker=dict(colors=["#16a34a", "#d97706", "#dc2626"]),
        textinfo="label+value",
    ))
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=20, b=10),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color="#0f172a"),
    )
    return fig


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def render() -> None:
    st.markdown('<h1 class="page-title">🧠 Skill Gap Analysis</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-sub">See which skills you already have, which need improvement, '
        'and which are missing for your target role — plus an AI learning roadmap.</p>',
        unsafe_allow_html=True,
    )

    gap = st.session_state.get("skill_gap_result")
    if not gap:
        st.warning(
            "🚧 **No skill gap analysis yet.**\n\n"
            "Go to **🎯 Job Matcher**, paste a job description, and run the match. "
            "The skill gap analysis runs automatically."
        )
        if st.button("➡️ Go to Job Matcher", type="primary"):
            st.session_state.page = "🎯 Job Matcher"
            st.rerun()
        return

    have_list = gap.get("already_have", [])
    improve_list = gap.get("need_improvement", [])
    missing_list = gap.get("missing", [])
    roadmap = gap.get("roadmap", [])

    # ---- Summary -----------------------------------------------------
    if gap.get("summary"):
        st.info(gap["summary"])

    # ---- Metrics -----------------------------------------------------
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("✅ Already Have", len(have_list))
    with m2:
        st.metric("🟡 Need Improvement", len(improve_list))
    with m3:
        st.metric("❌ Missing", len(missing_list))
    with m4:
        total = len(have_list) + len(improve_list) + len(missing_list)
        readiness = int(round((len(have_list) / total) * 100)) if total else 0
        st.metric("📈 Role Readiness", f"{readiness}%")

    st.markdown("---")

    # ---- Donut + Bar -------------------------------------------------
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown("### 📊 Distribution")
        fig = _donut(len(have_list), len(improve_list), len(missing_list))
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("### 📈 Skill Proficiency")
        all_skills = list(have_list) + list(improve_list)
        fig = _gap_bar(all_skills)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No skills detected in the resume.")

    # ---- Skill buckets -----------------------------------------------
    st.markdown("---")
    st.markdown("### 🗂️ Skill Buckets")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**✅ Already Have**")
        items = [f"{s['skill']} · {s['level']}" for s in have_list]
        st.markdown(_chips(items, "green"), unsafe_allow_html=True)
    with c2:
        st.markdown("**🟡 Need Improvement**")
        items = [f"{s['skill']} · {s['level']}" for s in improve_list]
        st.markdown(_chips(items, "warning"), unsafe_allow_html=True)
    with c3:
        st.markdown("**❌ Missing**")
        st.markdown(_chips(missing_list, "red"), unsafe_allow_html=True)

    # ---- Learning Roadmap --------------------------------------------
    st.markdown("---")
    st.markdown("### 🗺️ AI Learning Roadmap")

    if not roadmap:
        st.info("No roadmap was generated. Try running the Job Matcher again.")
    else:
        for i, phase in enumerate(roadmap, 1):
            with st.expander(f"**{phase.get('phase', f'Phase {i}')}** — {phase.get('focus', '')}",
                             expanded=(i == 1)):
                actions = phase.get("actions", [])
                if actions:
                    for a in actions:
                        st.markdown(f"- {a}")
                else:
                    st.write("No actions specified.")

    # ---- Actions -----------------------------------------------------
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Re-run Job Matcher", use_container_width=True):
            st.session_state.page = "🎯 Job Matcher"
            st.rerun()
    with c2:
        if st.button("✨ Open Resume Builder", use_container_width=True):
            st.session_state.page = "✨ Resume Builder"
            st.rerun()