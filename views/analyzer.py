"""
views/analyzer.py
-----------------
Resume Analyzer page — Phase 2 complete.

Flow:
  Upload → Validate → Extract → Preview → Analyze (AI) → Display results.
"""

from __future__ import annotations


import streamlit as st
import plotly.graph_objects as go

from database import database
from services import ollama_service
from services import resume_analyzer, resume_parser
from utils import validators


# ---------------------------------------------------------------------------
# Small UI helpers
# ---------------------------------------------------------------------------
def _score_card(label: str, value: int, accent: str = "primary") -> str:
    bar_width = max(0, min(100, value))
    return f"""
    <div class="score-card accent-{accent}">
        <div class="score-label">{label}</div>
        <div class="score-value">{value}<span>/100</span></div>
        <div class="score-bar"><div class="score-bar-fill" style="width:{bar_width}%"></div></div>
    </div>
    """


def _chips(items: list[str], kind: str = "default") -> str:
    if not items:
        return '<span class="chip chip-muted">None</span>'
    return "".join(f'<span class="chip chip-{kind}">{i}</span>' for i in items)


def _bullet_list(items: list[str], icon: str) -> str:
    if not items:
        return '<p class="muted-text">No items.</p>'
    lis = "".join(f"<li>{icon} {i}</li>" for i in items)
    return f'<ul class="bullet-list">{lis}</ul>'


def _score_radar(scores: dict) -> go.Figure:
    labels = ["ATS", "Content", "Skills", "Experience", "Projects", "Formatting"]
    keys = ["ats", "content", "skills", "experience", "projects", "formatting"]
    values = [scores.get(k, 0) for k in keys]

    fig = go.Figure(
        data=go.Scatterpolar(
            r=values + [values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            line=dict(color="#4f46e5", width=2),
            fillcolor="rgba(79, 70, 229, 0.25)",
            name="Score",
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], showline=False, gridcolor="#e2e8f0"),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=False,
        margin=dict(l=40, r=40, t=20, b=20),
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", size=12, color="#0f172a"),
    )
    return fig


def _keyword_bar(density: dict) -> go.Figure:
    if not density:
        return None
    items = sorted(density.items(), key=lambda x: x[1], reverse=True)[:10]
    words = [k for k, _ in items]
    counts = [v for _, v in items]

    fig = go.Figure(
        data=[go.Bar(
            x=counts, y=words, orientation="h",
            marker=dict(color="#4f46e5"),
            text=counts, textposition="outside",
        )]
    )
    fig.update_layout(
        height=max(240, 28 * len(words)),
        margin=dict(l=10, r=20, t=10, b=10),
        xaxis=dict(title="Occurrences", gridcolor="#f1f5f9"),
        yaxis=dict(autorange="reversed"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", size=12, color="#0f172a"),
    )
    return fig


def _skills_pie(skills: dict) -> go.Figure:
    labels = {
        "programming_languages": "Programming Languages",
        "frameworks": "Frameworks",
        "databases": "Databases",
        "cloud": "Cloud",
        "tools": "Tools",
        "technical_skills": "Technical Skills",
        "soft_skills": "Soft Skills",
    }
    cats = [(labels[k], len(skills.get(k, []))) for k in labels]
    cats = [(l, c) for l, c in cats if c > 0]

    if not cats:
        return None

    fig = go.Figure(
        data=[go.Pie(
            labels=[c[0] for c in cats],
            values=[c[1] for c in cats],
            hole=0.55,
            marker=dict(colors=[
                "#4f46e5", "#0891b2", "#16a34a", "#d97706",
                "#dc2626", "#7c3aed", "#0ea5e9",
            ]),
            textinfo="label+value",
        )]
    )
    fig.update_layout(
        height=340,
        margin=dict(l=10, r=10, t=20, b=10),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", size=12, color="#0f172a"),
    )
    return fig


# ---------------------------------------------------------------------------
# Analysis runner
# ---------------------------------------------------------------------------
def _run_analysis(resume_text: str, filename: str) -> None:
    """Run the full AI analysis pipeline and store results in session_state."""
    status = st.status("🤖 AI is analyzing your resume...", expanded=True)

    try:
        status.write("📊 Scoring resume...")
        analysis = resume_analyzer.analyze_resume(resume_text)
        st.session_state["analysis_result"] = analysis

        status.write("🧩 Extracting skills...")
        skills = resume_analyzer.extract_skills(resume_text)
        st.session_state["skills_result"] = skills

        status.write("🎯 Running ATS-style keyword analysis...")
        ats = resume_analyzer.ats_keyword_analysis(resume_text)
        st.session_state["ats_result"] = ats

        # Store for Phase 3 handoff
        st.session_state["last_analysis"] = {
            "overall_score": analysis["scores"]["overall"],
            "ats_score": analysis["scores"]["ats"],
            "skills_count": skills.get("total", 0),
        }
        st.session_state["last_resume_text"] = resume_text
                # Truncate for storage — huge resumes bloat session state
        st.session_state["last_resume_text"] = resume_text[:20000]
        st.session_state["last_resume_name"] = filename

        status.update(label="✅ Analysis complete", state="complete", expanded=False)
                # ---- Persist to SQLite --------------------------------------
        try:
            file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
            new_id = database.save_analysis(
                filename=filename,
                file_type=file_type,
                resume_text=resume_text,
                analysis=analysis,
                skills=skills,
                ats=ats,
            )
            if new_id:
                st.session_state["last_analysis_id"] = new_id
                st.session_state["resume_version"] = (
                    st.session_state.get("resume_version", 0) + 1
                )
        except Exception:
            # Never fail the whole analysis because of a DB write error
            pass

    except ollama_service.OllamaNotRunningError:
        status.update(label="❌ Ollama is not running", state="error", expanded=False)
        st.error("Start Ollama with `ollama serve` in a separate terminal, then try again.")
    except ollama_service.OllamaModelNotFoundError as exc:
        status.update(label="❌ Model missing", state="error", expanded=False)
        st.error(f"{exc}")
    except ollama_service.OllamaTimeoutError:
        status.update(label="⏱️ AI timed out", state="error", expanded=False)
        st.error("The model took too long. Try again, or use a shorter resume.")
    except ollama_service.OllamaInvalidResponseError as exc:
        status.update(label="⚠️ Invalid AI response", state="error", expanded=False)
        st.error(f"The AI returned an unexpected response. Try again.\n\nDetails: {exc}")
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
    analysis = st.session_state.get("analysis_result")
    skills = st.session_state.get("skills_result")
    ats = st.session_state.get("ats_result")

    if not analysis:
        return

    st.markdown("---")
    st.markdown('<h2 class="page-title" style="font-size:1.4rem">📊 Analysis Results</h2>',
                unsafe_allow_html=True)

    scores = analysis["scores"]

    # ---- Scores row --------------------------------------------------
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    with r1c1:
        st.markdown(_score_card("OVERALL", scores["overall"], "primary"), unsafe_allow_html=True)
    with r1c2:
        st.markdown(_score_card("ATS-STYLE", scores["ats"], "success"), unsafe_allow_html=True)
    with r1c3:
        st.markdown(_score_card("CONTENT", scores["content"], "warning"), unsafe_allow_html=True)
    with r1c4:
        st.markdown(_score_card("SKILLS", scores["skills"], "accent"), unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        st.markdown(_score_card("EXPERIENCE", scores["experience"], "primary"), unsafe_allow_html=True)
    with r2c2:
        st.markdown(_score_card("PROJECTS", scores["projects"], "success"), unsafe_allow_html=True)
    with r2c3:
        st.markdown(_score_card("FORMATTING", scores["formatting"], "accent"), unsafe_allow_html=True)

    st.caption(
        "ℹ️ Scores are generated by a local AI model. They are an "
        "**AI-based ATS-style analysis**, not an official ATS result."
    )

    # ---- Summary -----------------------------------------------------
    if analysis.get("summary"):
        st.markdown("### 📝 Overall Assessment")
        st.info(analysis["summary"])

    # ---- Radar + Strengths -------------------------------------------
    left, right = st.columns([1, 1])
    with left:
        st.markdown("### 🎯 Score Breakdown")
        st.plotly_chart(_score_radar(scores), use_container_width=True)

    with right:
        st.markdown("### ✅ Strengths")
        st.markdown(_bullet_list(analysis["strengths"], "✓"), unsafe_allow_html=True)
        st.markdown("### ⚠️ Weaknesses")
        st.markdown(_bullet_list(analysis["weaknesses"], "⚠"), unsafe_allow_html=True)

    # ---- Recommendations ---------------------------------------------
    st.markdown("### 💡 Recommendations")
    recs = analysis.get("recommendations", [])
    if recs:
        for i, rec in enumerate(recs, 1):
            st.markdown(f"**{i}.** {rec}")
    else:
        st.write("No recommendations.")

    # ---- Skills ------------------------------------------------------
    if skills:
        st.markdown("---")
        st.markdown("### 🧩 Skills Detected")
        c1, c2 = st.columns([1, 1])
        with c1:
            st.metric("Total Skills", skills.get("total", 0))
            st.markdown(
                f"""<div class="skills-chips">
                <b>Programming Languages</b><br>{_chips(skills.get('programming_languages', []))}
                <br><br><b>Frameworks</b><br>{_chips(skills.get('frameworks', []))}
                <br><br><b>Databases</b><br>{_chips(skills.get('databases', []))}
                <br><br><b>Cloud</b><br>{_chips(skills.get('cloud', []))}
                <br><br><b>Tools</b><br>{_chips(skills.get('tools', []))}
                <br><br><b>Technical Skills</b><br>{_chips(skills.get('technical_skills', []))}
                <br><br><b>Soft Skills</b><br>{_chips(skills.get('soft_skills', []))}
                </div>""",
                unsafe_allow_html=True,
            )
        with c2:
            fig = _skills_pie(skills)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No skills detected to visualize.")

    # ---- ATS Keywords ------------------------------------------------
    if ats:
        st.markdown("---")
        st.markdown("### 🎯 ATS-Style Keyword Analysis")
        st.caption("AI-based ATS-style analysis — not an official ATS result.")

        k1, k2 = st.columns(2)
        with k1:
            st.markdown("**✅ Matched Keywords**")
            st.markdown(_chips(ats["matched_keywords"], "green"), unsafe_allow_html=True)
        with k2:
            st.markdown("**❌ Missing Keywords**")
            st.markdown(_chips(ats["missing_keywords"], "red"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**⭐ Important Keywords for Your Target Field**")
        st.markdown(_chips(ats["important_keywords"], "blue"), unsafe_allow_html=True)

        if ats.get("keyword_density"):
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**📈 Keyword Density (Top 10)**")
            fig = _keyword_bar(ats["keyword_density"])
            if fig:
                st.plotly_chart(fig, use_container_width=True)

        if ats.get("suggestions"):
            st.markdown("**🛠️ ATS Improvement Suggestions**")
            for s in ats["suggestions"]:
                st.markdown(f"- {s}")
    # ---- Handoff to Builder -----------------------------------------
    st.markdown("---")
    st.markdown("### ✨ Next Step")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown(
            "Send the analysis to the **Resume Builder** to start with an "
            "AI-suggested summary and pre-extracted skills."
        )
    with c2:
        if st.button("➡️ Send to Builder", type="primary", use_container_width=True):
            st.session_state["builder_seed"] = {
                "analysis": analysis,
                "skills": skills or {},
            }
            st.session_state["_builder_seed_notice"] = (
                "✅ Resume data imported. Go to **✨ Resume Builder** to continue."
            )
            st.session_state.page = "✨ Resume Builder"
            st.rerun()

# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def render() -> None:
    st.markdown('<h1 class="page-title">📄 Resume Analyzer</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-sub">Upload your resume (PDF or DOCX) and let the local AI '
        'score it, extract skills, and simulate an ATS-style keyword review.</p>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="privacy-note">🔒 Your resume is processed locally using Ollama. '
        'Content is not intentionally sent to any third-party AI service.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload your resume",
        type=["pdf", "docx"],
        accept_multiple_files=False,
        help="PDF or DOCX · Max 10 MB",
    )

    if uploaded is not None:
        current_name = st.session_state.get("_analyzer_current_file")
        if current_name != uploaded.name:
            st.session_state["_analyzer_current_file"] = uploaded.name
            for key in ("analysis_result", "skills_result", "ats_result"):
                st.session_state.pop(key, None)

    # ---- Validate ----------------------------------------------------
    ok, msg = validators.validate_upload(uploaded)
    if not ok:
        st.error(f"❌ {msg}")
        return

    # ---- Extract -----------------------------------------------------
    file_bytes = uploaded.read()
    try:
        resume_text = resume_parser.parse_resume(file_bytes, uploaded.name)
    except resume_parser.ResumeParserError as exc:
        st.error(f"❌ {exc}")
        return

    st.success(
        f"✅ Loaded **{uploaded.name}** · "
        f"{len(resume_text):,} characters extracted"
    )

    # ---- Preview -----------------------------------------------------
    with st.expander("👁️ Preview extracted text", expanded=False):
        st.text_area(
            "Extracted text",
            value=resume_text[:6000] + ("\n\n[...truncated...]" if len(resume_text) > 6000 else ""),
            height=280,
            label_visibility="collapsed",
            disabled=True,
        )

    # ---- Analyze button ---------------------------------------------
    col_a, col_b = st.columns([1, 3])
    with col_a:
        run = st.button("🚀 Analyze with AI", type="primary", use_container_width=True)
    with col_b:
        clear = st.button("🗑️ Clear results", use_container_width=False)

    if clear:
        for key in ("analysis_result", "skills_result", "ats_result"):
            st.session_state.pop(key, None)
        st.rerun()

    if run:
        _run_analysis(resume_text, uploaded.name)

    # ---- Results -----------------------------------------------------
    _render_results()
    
        