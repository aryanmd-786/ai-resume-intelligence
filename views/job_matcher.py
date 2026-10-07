"""
views/job_matcher.py
--------------------
Job Description Matcher — Phase 4.

Flow:
  Resume (from Analyzer or upload) + Job Description → AI Match → Results.
"""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go

from database import database
from services import job_matcher, ollama_service, resume_parser
from utils import validators


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def _chips(items: list[str], kind: str) -> str:
    if not items:
        return '<span class="chip chip-muted">None</span>'
    return "".join(f'<span class="chip chip-{kind}">{i}</span>' for i in items)


def _match_gauge(score: int) -> go.Figure:
    color = "#16a34a" if score >= 75 else "#d97706" if score >= 50 else "#dc2626"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "%", "font": {"size": 40, "color": "#0f172a"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#94a3b8"},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "#f1f5f9",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 50], "color": "#fee2e2"},
                {"range": [50, 75], "color": "#fef3c7"},
                {"range": [75, 100], "color": "#dcfce7"},
            ],
            "threshold": {
                "line": {"color": "#0f172a", "width": 2},
                "thickness": 0.75,
                "value": score,
            },
        },
    ))
    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color="#0f172a"),
    )
    return fig


def _relevance_bar(exp: int, edu: int) -> go.Figure:
    fig = go.Figure(data=[
        go.Bar(
            x=[exp, edu],
            y=["Experience", "Education"],
            orientation="h",
            marker=dict(color=["#4f46e5", "#0891b2"]),
            text=[f"{exp}%", f"{edu}%"],
            textposition="outside",
        )
    ])
    fig.update_layout(
        height=180,
        margin=dict(l=10, r=40, t=10, b=10),
        xaxis=dict(range=[0, 105], showgrid=True, gridcolor="#f1f5f9", title=""),
        yaxis=dict(autorange="reversed"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color="#0f172a"),
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Analysis runner
# ---------------------------------------------------------------------------
def _run_match(resume_text: str, jd: str) -> None:
    status = st.status("🤖 AI is matching your resume against the JD...", expanded=True)
    try:
        status.write("🎯 Computing match score...")
        result = job_matcher.match_job_description(resume_text, jd)
        st.session_state["job_match_result"] = result
        st.session_state["last_job_match"] = {"match_score": result["match_score"]}
        st.session_state["last_job_description"] = jd

        status.write("🧠 Analyzing skill gap...")
        gap = job_matcher.analyze_skill_gap(resume_text, jd)
        st.session_state["skill_gap_result"] = gap

        # ---- Persist to SQLite --------------------------------------
        try:
            resume_id = st.session_state.get("last_analysis_id")
            database.save_job_match(
                resume_id=resume_id,
                jd_text=jd,
                result=result,
            )
        except Exception:
            pass

        status.update(label="✅ Match complete", state="complete", expanded=False)

    except ollama_service.OllamaNotRunningError:
        status.update(label="❌ Ollama not running", state="error", expanded=False)
        st.error("Start Ollama with `ollama serve` in a separate terminal.")
    except ollama_service.OllamaModelNotFoundError as exc:
        status.update(label="❌ Model missing", state="error", expanded=False)
        st.error(str(exc))
    except ollama_service.OllamaTimeoutError:
        status.update(label="⏱️ Timed out", state="error", expanded=False)
        st.error("The model took too long. Try again with a shorter JD.")
    except ollama_service.OllamaInvalidResponseError as exc:
        status.update(label="⚠️ Invalid AI response", state="error", expanded=False)
        st.error(f"AI returned unexpected output. Try again. ({exc})")
    except ollama_service.OllamaError as exc:
        status.update(label="❌ AI error", state="error", expanded=False)
        st.error(f"AI error: {exc}")
    except ValueError as exc:
        status.update(label="❌ Invalid input", state="error", expanded=False)
        st.error(str(exc))
    except Exception as exc:
        status.update(label="❌ Unexpected error", state="error", expanded=False)
        st.error(f"Something went wrong: {exc}")


# ---------------------------------------------------------------------------
# Result renderer
# ---------------------------------------------------------------------------
def _render_results() -> None:
    result = st.session_state.get("job_match_result")
    if not result:
        return

    st.markdown("---")
    st.markdown('<h2 class="page-title" style="font-size:1.4rem">🎯 Match Results</h2>',
                unsafe_allow_html=True)

    # ---- Gauge + Summary ---------------------------------------------
    c1, c2 = st.columns([1, 1])
    with c1:
        st.plotly_chart(_match_gauge(result["match_score"]), use_container_width=True)
    with c2:
        st.markdown("### 📝 Assessment")
        st.info(result.get("summary") or "No summary provided.")
        st.markdown("### 📊 Relevance Scores")
        st.plotly_chart(
            _relevance_bar(result["experience_relevance"], result["education_relevance"]),
            use_container_width=True,
        )

    # ---- Matched / Missing Skills ------------------------------------
    st.markdown("---")
    st.markdown("### 🧩 Skills Comparison")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**✅ Matched Skills**")
        st.markdown(_chips(result["matched_skills"], "green"), unsafe_allow_html=True)
    with c2:
        st.markdown("**❌ Missing Skills**")
        st.markdown(_chips(result["missing_skills"], "red"), unsafe_allow_html=True)

    # ---- Keywords ----------------------------------------------------
    st.markdown("---")
    st.markdown("### 🔑 Keyword Comparison")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**✅ Matched Keywords**")
        st.markdown(_chips(result["matched_keywords"], "green"), unsafe_allow_html=True)
    with c2:
        st.markdown("**❌ Missing Keywords**")
        st.markdown(_chips(result["missing_keywords"], "red"), unsafe_allow_html=True)

    # ---- Recommendations ---------------------------------------------
    st.markdown("---")
    st.markdown("### 💡 Recommendations")
    recs = result.get("recommendations", [])
    if recs:
        for i, rec in enumerate(recs, 1):
            st.markdown(f"**{i}.** {rec}")
    else:
        st.write("No recommendations.")

    # ---- Skill Gap CTA -----------------------------------------------
    st.markdown("---")
    if st.session_state.get("skill_gap_result"):
        if st.button("🧠 View Skill Gap Analysis →", type="primary"):
            st.session_state.page = "🧠 Skill Gap"
            st.rerun()


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def render() -> None:
    st.markdown('<h1 class="page-title">🎯 Job Description Matcher</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-sub">Paste a job description and see how well your resume matches — '
        'skills, keywords, experience, and education relevance.</p>',
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # Resume source
    # ------------------------------------------------------------------
    st.markdown("### 1️⃣ Resume")
    last_name = st.session_state.get("last_resume_name")
    last_text = st.session_state.get("last_resume_text")

    source = st.radio(
        "Resume source",
        options=["Use last analyzed resume", "Upload a new resume"],
        index=0 if last_text else 1,
        horizontal=True,
        key="jm_source",
    )

    resume_text: str | None = None

    if source == "Use last analyzed resume":
        if last_text:
            st.success(f"✅ Using: **{last_name or 'previous resume'}**")
            resume_text = last_text
        else:
            st.warning("No previous resume found. Please upload one below.")

    if source == "Upload a new resume" or not resume_text:
        uploaded = st.file_uploader(
            "Upload resume (PDF or DOCX)",
            type=["pdf", "docx"],
            key="jm_upload",
        )
        if uploaded is not None:
            ok, msg = validators.validate_upload(uploaded)
            if not ok:
                st.error(f"❌ {msg}")
            else:
                try:
                    resume_text = resume_parser.parse_resume(uploaded.read(), uploaded.name)
                    st.success(f"✅ Loaded **{uploaded.name}** ({len(resume_text):,} chars)")
                except resume_parser.ResumeParserError as exc:
                    st.error(f"❌ {exc}")

    # ------------------------------------------------------------------
    # Job description
    # ------------------------------------------------------------------
    st.markdown("### 2️⃣ Job Description")
    jd = st.text_area(
        "Paste the job description",
        value=st.session_state.get("last_job_description", ""),
        height=240,
        key="jm_jd",
        label_visibility="collapsed",
        placeholder="Paste the full job description here — responsibilities, requirements, preferred skills...",
    )
     # ---- Character count feedback ------------------------------------
    jd_len = len((jd or "").strip())
    if jd_len == 0:
        st.caption("ℹ️ Paste a job description to begin.")
    elif jd_len < 40:
        st.caption(f"⚠️ Job description is very short ({jd_len} chars). Add more detail.")
    else:
        st.caption(f"✅ {jd_len:,} characters — ready to match.")
    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    st.markdown("---")
    c1, c2 = st.columns([1, 4])
    with c1:
        run = st.button("🚀 Match with AI", type="primary", use_container_width=True)
    with c2:
        if st.button("🗑️ Clear results"):
            for key in ("job_match_result", "skill_gap_result", "last_job_match"):
                st.session_state.pop(key, None)
            st.rerun()

    if run:
        if not resume_text:
            st.error("Please provide a resume first.")
        elif len((jd or "").strip()) < 40:
            st.error("Please paste a longer job description (at least 40 characters).")
        else:
            _run_match(resume_text, jd)

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------
    _render_results()
