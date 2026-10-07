"""
views/builder.py
----------------
AI Resume Builder — Phase 3.

Features:
- Multi-section form
- AI assistance (Summary, Experience, Project, Skills)
- Template selection (Modern / Minimal / Professional)
- HTML live preview
- PDF + DOCX export
- Auto-prefill from an analyzed resume (via session_state.builder_seed)
"""

from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

import config
from database import database
from services import ollama_service, resume_generator
from services.resume_docx import generate_docx
from services.resume_pdf import generate_pdf
from templates import get_theme, template_names


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
def _blank_state() -> dict:
    return {
        "personal": {
            "full_name": "", "email": "", "phone": "", "location": "",
            "linkedin": "", "github": "", "portfolio": "",
        },
        "summary": "",
        "education": [{"degree": "", "institution": "", "year": "", "score": ""}],
        "skills": [],
        "experience": [{"company": "", "role": "", "duration": "", "responsibilities": ""}],
        "projects": [{"name": "", "description": "", "technologies": "", "url": ""}],
        "certifications": [],
        "achievements": [],
        "languages": [],
        "interests": [],
    }


def _init_state() -> None:
    if "builder_data" not in st.session_state or not st.session_state.builder_data:
        st.session_state.builder_data = _blank_state()


def _seed_from_analyzer() -> None:
    seed = st.session_state.get("builder_seed")
    if not seed:
        return

    data = st.session_state.builder_data

    if not data.get("summary") and seed.get("analysis", {}).get("summary"):
        data["summary"] = seed["analysis"]["summary"]

    skills_seed = seed.get("skills") or {}
    if skills_seed and not data.get("skills"):
        flat: list[str] = []
        for key in ("programming_languages", "frameworks", "databases",
                    "cloud", "tools", "technical_skills"):
            flat.extend(skills_seed.get(key, []) or [])
        data["skills"] = list(dict.fromkeys(flat))

    st.session_state.builder_seed = None


def _to_list(text: str) -> list[str]:
    if not text:
        return []
    parts = re.split(r"[,\n;]+", text)
    return [p.strip() for p in parts if p.strip()]


def _safe_ai_call(label: str, fn, *args, **kwargs):
    with st.spinner(f"🤖 {label}..."):
        try:
            return fn(*args, **kwargs)
        except ollama_service.OllamaNotRunningError:
            st.error("Ollama is not running. Start it with `ollama serve`.")
        except ollama_service.OllamaModelNotFoundError as exc:
            st.error(f"Model missing: {exc}")
        except ollama_service.OllamaTimeoutError:
            st.error("AI timed out. Try again with a shorter input.")
        except ollama_service.OllamaInvalidResponseError as exc:
            st.error(f"AI returned invalid output. Try again. ({exc})")
        except ollama_service.OllamaError as exc:
            st.error(f"AI error: {exc}")
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
    return None


# ---------------------------------------------------------------------------
# HTML preview — FIXED version (no code-block rendering)
# ---------------------------------------------------------------------------
def _html_preview(data: dict, theme: dict) -> str:
    p = data.get("personal", {}) or {}
    primary = theme["primary"]
    text_col = theme["text"]
    muted = theme["muted"]
    divider = theme["divider"]
    align = theme.get("header_align", "left")
    uppercase = theme.get("section_uppercase", True)
    bar = theme.get("section_bar", False)

    def esc(s):
        return (str(s or "")
                .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    def section(title: str, body_html: str) -> str:
        t = title.upper() if uppercase else title
        bar_style = (
            f"background:{primary};color:#fff;padding:3px 8px;border-radius:4px;display:inline-block;"
            if bar else
            f"color:{primary};border-bottom:1.5px solid {primary};display:block;padding-bottom:2px;"
        )
        return (
            f'<div style="margin-top:14px;">'
            f'<div style="font-weight:700;font-size:11px;letter-spacing:0.06em;{bar_style}">{esc(t)}</div>'
            f'<div style="margin-top:8px;">{body_html}</div>'
            f'</div>'
        )

    name = esc(p.get("full_name")) or "Your Name"
    contact = " &nbsp;•&nbsp; ".join(esc(p.get(k)) for k in ("email", "phone", "location") if p.get(k))
    links = " &nbsp;|&nbsp; ".join(esc(p.get(k)) for k in ("linkedin", "github", "portfolio") if p.get(k))

    header = (
        f'<div style="text-align:{align};">'
        f'<div style="font-size:22px;font-weight:800;color:{text_col};letter-spacing:-0.01em;">{name}</div>'
        + (f'<div style="font-size:11px;color:{muted};margin-top:4px;">{contact}</div>' if contact else '')
        + (f'<div style="font-size:11px;color:{muted};margin-top:2px;">{links}</div>' if links else '')
        + '</div>'
    )

    parts = [header]

    if data.get("summary"):
        parts.append(section(
            "Professional Summary",
            f'<div style="font-size:12px;color:{text_col};line-height:1.5;">{esc(data["summary"])}</div>'
        ))

    skills = data.get("skills") or []
    if skills:
        chips = " ".join(
            f'<span style="display:inline-block;padding:2px 8px;margin:2px 3px 2px 0;border-radius:999px;'
            f'font-size:11px;background:{theme.get("primary_soft", "#EEF2FF")};color:{primary};'
            f'border:1px solid {primary}22;">{esc(s)}</span>' for s in skills
        )
        parts.append(section("Skills", chips))

    exp = [e for e in (data.get("experience") or [])
           if any(str(e.get(k) or "").strip() for k in ("role", "company", "responsibilities"))]
    if exp:
        html = []
        for e in exp:
            title = " — ".join(x for x in (esc(e.get("role")), esc(e.get("company"))) if x)
            meta = esc(e.get("duration"))
            bullets = ""
            for line in (e.get("responsibilities") or "").splitlines():
                line = line.strip().lstrip("•-*").strip()
                if line:
                    bullets += f'<li style="margin:2px 0;">{esc(line)}</li>'
            html.append(
                f'<div style="margin-bottom:10px;">'
                f'<div style="font-size:12px;font-weight:700;color:{text_col};">{title or "Experience"}</div>'
                + (f'<div style="font-size:11px;color:{muted};font-style:italic;margin-bottom:3px;">{meta}</div>' if meta else '')
                + (f'<ul style="margin:4px 0 0 18px;padding:0;font-size:11.5px;color:{text_col};line-height:1.5;">{bullets}</ul>' if bullets else '')
                + '</div>'
            )
        parts.append(section("Experience", "".join(html)))

    prj = [p_ for p_ in (data.get("projects") or [])
           if any(str(p_.get(k) or "").strip() for k in ("name", "description"))]
    if prj:
        html = []
        for p_ in prj:
            meta_parts = []
            if p_.get("technologies"):
                meta_parts.append(f"Tech: {esc(p_['technologies'])}")
            if p_.get("url"):
                meta_parts.append(esc(p_["url"]))
            bullets = ""
            for line in (p_.get("description") or "").splitlines():
                line = line.strip().lstrip("•-*").strip()
                if line:
                    bullets += f'<li style="margin:2px 0;">{esc(line)}</li>'
            html.append(
                f'<div style="margin-bottom:10px;">'
                f'<div style="font-size:12px;font-weight:700;color:{text_col};">{esc(p_.get("name")) or "Project"}</div>'
                + (f'<div style="font-size:11px;color:{muted};font-style:italic;margin-bottom:3px;">{" • ".join(meta_parts)}</div>' if meta_parts else '')
                + (f'<ul style="margin:4px 0 0 18px;padding:0;font-size:11.5px;color:{text_col};line-height:1.5;">{bullets}</ul>' if bullets else '')
                + '</div>'
            )
        parts.append(section("Projects", "".join(html)))

    edu = [e for e in (data.get("education") or [])
           if any(str(e.get(k) or "").strip() for k in ("degree", "institution"))]
    if edu:
        html = []
        for e in edu:
            title = " — ".join(x for x in (esc(e.get("degree")), esc(e.get("institution"))) if x)
            meta_parts = []
            if e.get("year"):
                meta_parts.append(esc(e["year"]))
            if e.get("score"):
                meta_parts.append(f"Score: {esc(e['score'])}")
            html.append(
                f'<div style="margin-bottom:8px;">'
                f'<div style="font-size:12px;font-weight:700;color:{text_col};">{title or "Education"}</div>'
                + (f'<div style="font-size:11px;color:{muted};font-style:italic;">{" • ".join(meta_parts)}</div>' if meta_parts else '')
                + '</div>'
            )
        parts.append(section("Education", "".join(html)))

    certs = [c for c in (data.get("certifications") or []) if str(c).strip()]
    if certs:
        items = "".join(f'<li style="margin:2px 0;">{esc(c)}</li>' for c in certs)
        parts.append(section(
            "Certifications",
            f'<ul style="margin:4px 0 0 18px;padding:0;font-size:11.5px;color:{text_col};line-height:1.5;">{items}</ul>'
        ))

    ach = [a for a in (data.get("achievements") or []) if str(a).strip()]
    if ach:
        items = "".join(f'<li style="margin:2px 0;">{esc(a)}</li>' for a in ach)
        parts.append(section(
            "Achievements",
            f'<ul style="margin:4px 0 0 18px;padding:0;font-size:11.5px;color:{text_col};line-height:1.5;">{items}</ul>'
        ))

    langs = data.get("languages") or []
    if isinstance(langs, str):
        langs = _to_list(langs)
    if langs:
        parts.append(section(
            "Languages",
            f'<div style="font-size:11.5px;color:{text_col};">{esc(", ".join(langs))}</div>'
        ))

    ints = data.get("interests") or []
    if isinstance(ints, str):
        ints = _to_list(ints)
    if ints:
        parts.append(section(
            "Interests",
            f'<div style="font-size:11.5px;color:{text_col};">{esc(", ".join(ints))}</div>'
        ))

    # Build as ONE single line — no leading spaces anywhere.
    # This prevents Streamlit's markdown parser from treating it as a code block.
    inner = "".join(parts)
    return (
        f'<div style="background:#fff;border:1px solid {divider};border-radius:12px;'
        f'padding:26px 30px;max-width:780px;margin:0 auto;'
        f'box-shadow:0 8px 24px rgba(15,23,42,0.06);">{inner}</div>'
    )


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------
def _render_personal(data: dict) -> None:
    p = data["personal"]
    st.markdown("### 👤 Personal Information")
    c1, c2 = st.columns(2)
    with c1:
        p["full_name"] = st.text_input("Full Name", value=p.get("full_name", ""), key="bd_p_name")
        p["email"] = st.text_input("Email", value=p.get("email", ""), key="bd_p_email")
        p["phone"] = st.text_input("Phone", value=p.get("phone", ""), key="bd_p_phone")
        p["location"] = st.text_input("Location", value=p.get("location", ""), key="bd_p_loc")
    with c2:
        p["linkedin"] = st.text_input("LinkedIn", value=p.get("linkedin", ""), key="bd_p_li")
        p["github"] = st.text_input("GitHub", value=p.get("github", ""), key="bd_p_gh")
        p["portfolio"] = st.text_input("Portfolio", value=p.get("portfolio", ""), key="bd_p_pf")


def _render_summary(data: dict) -> None:
    st.markdown("### 📝 Professional Summary")
    c1, c2 = st.columns([4, 1])
    with c2:
        if st.button("✨ Generate with AI", use_container_width=True, key="ai_summary"):
            result = _safe_ai_call(
                "Generating summary",
                resume_generator.generate_summary,
                data["personal"], data.get("skills", []),
                data.get("experience", []), data.get("education", []),
            )
            if result:
                data["summary"] = result
                st.rerun()

    data["summary"] = st.text_area(
        "Summary",
        value=data.get("summary", ""),
        height=140,
        key="bd_summary",
        label_visibility="collapsed",
        placeholder="2-4 sentences about your strengths, focus areas, and value.",
    )
    st.caption("💡 Tip: Click **Generate with AI** after filling Personal, Skills, and Experience.")


def _render_education(data: dict) -> None:
    st.markdown("### 🎓 Education")
    rows = data.get("education", [])
    if not rows:
        rows = [{"degree": "", "institution": "", "year": "", "score": ""}]
        data["education"] = rows

    for i, row in enumerate(rows):
        with st.expander(f"Education #{i + 1}", expanded=(i == 0)):
            c1, c2 = st.columns(2)
            with c1:
                row["degree"] = st.text_input("Degree", value=row.get("degree", ""), key=f"bd_edu_deg_{i}")
                row["institution"] = st.text_input("Institution", value=row.get("institution", ""), key=f"bd_edu_inst_{i}")
            with c2:
                row["year"] = st.text_input("Year", value=row.get("year", ""), key=f"bd_edu_year_{i}")
                row["score"] = st.text_input("CGPA / %", value=row.get("score", ""), key=f"bd_edu_score_{i}")

            if len(rows) > 1:
                if st.button(f"🗑️ Remove Education #{i + 1}", key=f"bd_edu_del_{i}"):
                    rows.pop(i)
                    st.rerun()

    if st.button("➕ Add Education", key="bd_edu_add"):
        rows.append({"degree": "", "institution": "", "year": "", "score": ""})
        st.rerun()


def _render_skills(data: dict) -> None:
    st.markdown("### 🧩 Skills")
    current = data.get("skills") or []
    text = ", ".join(current) if isinstance(current, list) else str(current)

    c1, c2 = st.columns([4, 1])
    with c2:
        if st.button("💡 Suggest Skills", use_container_width=True, key="ai_skills"):
            role = st.session_state.get("bd_skills_target_role", "")
            if not role:
                st.warning("Enter a target role in the box below first.")
            else:
                suggestions = _safe_ai_call(
                    "Suggesting skills",
                    resume_generator.suggest_skills,
                    role, current,
                )
                if suggestions:
                    st.session_state["bd_skills_suggestions"] = suggestions

    target_role = st.text_input(
        "Target role (for AI suggestions)",
        value=st.session_state.get("bd_skills_target_role", ""),
        key="bd_skills_target_role",
        placeholder="e.g., Data Analyst, Backend Developer",
    )

    new_text = st.text_area(
        "Skills (comma-separated)",
        value=text,
        height=90,
        key="bd_skills_text",
        placeholder="Python, SQL, Pandas, Streamlit, Git",
    )
    data["skills"] = _to_list(new_text)

    suggestions = st.session_state.pop("bd_skills_suggestions", None)
    if suggestions:
        st.info("**AI suggestions** (click to add):")
        cols = st.columns(min(len(suggestions), 4))
        for idx, s in enumerate(suggestions):
            with cols[idx % len(cols)]:
                if st.button(f"➕ {s}", key=f"bd_skill_add_{idx}"):
                    if s not in data["skills"]:
                        data["skills"].append(s)
                        st.session_state["bd_skills_text"] = ", ".join(data["skills"])
                    st.rerun()


def _render_experience(data: dict) -> None:
    st.markdown("### 💼 Experience")
    rows = data.get("experience", [])
    if not rows:
        rows = [{"company": "", "role": "", "duration": "", "responsibilities": ""}]
        data["experience"] = rows

    for i, row in enumerate(rows):
        with st.expander(f"Experience #{i + 1}", expanded=(i == 0)):
            c1, c2 = st.columns(2)
            with c1:
                row["role"] = st.text_input("Role", value=row.get("role", ""), key=f"bd_exp_role_{i}")
            with c2:
                row["company"] = st.text_input("Company", value=row.get("company", ""), key=f"bd_exp_comp_{i}")

            row["duration"] = st.text_input(
                "Duration", value=row.get("duration", ""),
                key=f"bd_exp_dur_{i}", placeholder="e.g., Jun 2023 – Aug 2024",
            )

            row["responsibilities"] = st.text_area(
                "Responsibilities (one per line)",
                value=row.get("responsibilities", ""),
                height=110,
                key=f"bd_exp_resp_{i}",
            )

            c_a, c_b = st.columns([1, 1])
            with c_a:
                if st.button(f"✨ Improve with AI", key=f"bd_exp_ai_{i}", use_container_width=True):
                    result = _safe_ai_call(
                        "Improving experience",
                        resume_generator.improve_experience,
                        row.get("company", ""), row.get("role", ""),
                        row.get("responsibilities", ""),
                    )
                    if result:
                        row["responsibilities"] = result
                        st.session_state[f"bd_exp_resp_{i}"] = result
                        st.rerun()
            with c_b:
                if len(rows) > 1:
                    if st.button(f"🗑️ Remove", key=f"bd_exp_del_{i}", use_container_width=True):
                        rows.pop(i)
                        st.rerun()

    if st.button("➕ Add Experience", key="bd_exp_add"):
        rows.append({"company": "", "role": "", "duration": "", "responsibilities": ""})
        st.rerun()


def _render_projects(data: dict) -> None:
    st.markdown("### 🚀 Projects")
    rows = data.get("projects", [])
    if not rows:
        rows = [{"name": "", "description": "", "technologies": "", "url": ""}]
        data["projects"] = rows

    for i, row in enumerate(rows):
        with st.expander(f"Project #{i + 1}", expanded=(i == 0)):
            row["name"] = st.text_input("Project Name", value=row.get("name", ""), key=f"bd_prj_name_{i}")
            row["technologies"] = st.text_input(
                "Technologies", value=row.get("technologies", ""),
                key=f"bd_prj_tech_{i}", placeholder="e.g., Python, Streamlit, SQLite",
            )
            row["url"] = st.text_input("GitHub / Live URL", value=row.get("url", ""), key=f"bd_prj_url_{i}")
            row["description"] = st.text_area(
                "Description", value=row.get("description", ""),
                height=110, key=f"bd_prj_desc_{i}",
                placeholder="What does it do? What problem does it solve?",
            )

            c_a, c_b = st.columns([1, 1])
            with c_a:
                if st.button(f"✨ Improve with AI", key=f"bd_prj_ai_{i}", use_container_width=True):
                    result = _safe_ai_call(
                        "Improving project",
                        resume_generator.improve_project,
                        row.get("name", ""), row.get("description", ""),
                        row.get("technologies", ""),
                    )
                    if result:
                        row["description"] = result
                        st.session_state[f"bd_prj_desc_{i}"] = result
                        st.rerun()
            with c_b:
                if len(rows) > 1:
                    if st.button(f"🗑️ Remove", key=f"bd_prj_del_{i}", use_container_width=True):
                        rows.pop(i)
                        st.rerun()

    if st.button("➕ Add Project", key="bd_prj_add"):
        rows.append({"name": "", "description": "", "technologies": "", "url": ""})
        st.rerun()


def _render_extras(data: dict) -> None:
    st.markdown("### 🏆 Certifications & Achievements")

    c1, c2 = st.columns(2)
    with c1:
        certs_text = "\n".join(data.get("certifications", []) or [])
        new_certs = st.text_area(
            "Certifications (one per line)",
            value=certs_text, height=110, key="bd_certs",
            placeholder="AWS Cloud Practitioner\nGoogle Data Analytics",
        )
        data["certifications"] = [l.strip() for l in new_certs.splitlines() if l.strip()]
    with c2:
        ach_text = "\n".join(data.get("achievements", []) or [])
        new_ach = st.text_area(
            "Achievements (one per line)",
            value=ach_text, height=110, key="bd_ach",
            placeholder="Winner — Smart India Hackathon 2024\nTop 5% in class",
        )
        data["achievements"] = [l.strip() for l in new_ach.splitlines() if l.strip()]

    st.markdown("### 🌐 Languages & Interests")
    c3, c4 = st.columns(2)
    with c3:
        langs = data.get("languages") or []
        langs_text = ", ".join(langs) if isinstance(langs, list) else str(langs)
        new_langs = st.text_input("Languages", value=langs_text, key="bd_langs",
                                  placeholder="English, Hindi, Spanish")
        data["languages"] = _to_list(new_langs)
    with c4:
        ints = data.get("interests") or []
        ints_text = ", ".join(ints) if isinstance(ints, list) else str(ints)
        new_ints = st.text_input("Interests", value=ints_text, key="bd_ints",
                                 placeholder="Open Source, Chess, Writing")
        data["interests"] = _to_list(new_ints)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def render() -> None:
    st.markdown('<h1 class="page-title">✨ Resume Builder</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-sub">Fill in your details (or import from the Analyzer), let AI polish '
        'the wording, pick a template, and export a polished PDF/DOCX.</p>',
        unsafe_allow_html=True,
    )

    _init_state()
    _seed_from_analyzer()
    data = st.session_state.builder_data

    if st.session_state.get("_builder_seed_notice"):
        st.success(st.session_state.pop("_builder_seed_notice"))

    top_left, top_right = st.columns([3, 1])
    with top_right:
        if st.button("🗑️ Reset Builder", use_container_width=True):
            st.session_state.builder_data = _blank_state()
            st.success("Builder reset.")
            st.rerun()

    tabs = st.tabs([
        "👤 Personal", "📝 Summary", "🎓 Education", "🧩 Skills",
        "💼 Experience", "🚀 Projects", "🏆 Extras", "🎨 Template & Export",
    ])

    with tabs[0]:
        _render_personal(data)
    with tabs[1]:
        _render_summary(data)
    with tabs[2]:
        _render_education(data)
    with tabs[3]:
        _render_skills(data)
    with tabs[4]:
        _render_experience(data)
    with tabs[5]:
        _render_projects(data)
    with tabs[6]:
        _render_extras(data)

    with tabs[7]:
        st.markdown("### 🎨 Choose a Template")

        chosen_template = st.selectbox(
            "Template",
            options=template_names(),
            index=0,
            key="bd_template",
        )
        theme = get_theme(chosen_template)

        st.caption(
            f"**{theme['name']}** — Primary color: `{theme['primary']}` · "
            f"Font: {theme['pdf_font_body']} · "
            f"{'Uppercase headers' if theme.get('section_uppercase') else 'Mixed-case headers'}"
        )

        st.markdown("### 👁️ Preview")
        st.markdown(_html_preview(data, theme), unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📥 Export")

        if not (data.get("personal", {}).get("full_name") or "").strip():
            st.warning("Please enter your **Full Name** in the Personal tab before exporting.")

        base_name = (data["personal"].get("full_name") or "resume").strip().replace(" ", "_") or "resume"

        c1, c2 = st.columns(2)

        with c1:
            if st.button("📄 Generate PDF", use_container_width=True, type="primary"):
                if not (data["personal"].get("full_name") or "").strip():
                    st.error("Full Name is required.")
                else:
                    try:
                        out_path = config.OUTPUTS_DIR / f"{base_name}_{theme['name']}_resume.pdf"
                        generate_pdf(data, theme, out_path)
                        st.session_state["_pdf_path"] = str(out_path)
                        st.session_state["_pdf_name"] = f"{base_name}_{theme['name']}_resume.pdf"
                        try:
                            database.save_generated_resume(
                                full_name=data["personal"].get("full_name", ""),
                                template=theme["name"],
                                file_path=str(out_path),
                                data=data,
                            )
                        except Exception:
                            pass
                        st.success("PDF generated!")
                    except Exception as exc:
                        st.error(f"Could not generate PDF: {exc}")

        with c2:
            if st.button("📝 Generate DOCX", use_container_width=True):
                if not (data["personal"].get("full_name") or "").strip():
                    st.error("Full Name is required.")
                else:
                    try:
                        out_path = config.OUTPUTS_DIR / f"{base_name}_{theme['name']}_resume.docx"
                        generate_docx(data, theme, out_path)
                        st.session_state["_docx_path"] = str(out_path)
                        st.session_state["_docx_name"] = f"{base_name}_{theme['name']}_resume.docx"
                        try:
                            database.save_generated_resume(
                                full_name=data["personal"].get("full_name", ""),
                                template=theme["name"],
                                file_path=str(out_path),
                                data=data,
                            )
                        except Exception:
                            pass
                        st.success("DOCX generated!")
                    except Exception as exc:
                        st.error(f"Could not generate DOCX: {exc}")

        if st.session_state.get("_pdf_path") and Path(st.session_state["_pdf_path"]).exists():
            with open(st.session_state["_pdf_path"], "rb") as f:
                st.download_button(
                    "⬇️ Download PDF",
                    data=f.read(),
                    file_name=st.session_state["_pdf_name"],
                    mime="application/pdf",
                    use_container_width=True,
                )

        if st.session_state.get("_docx_path") and Path(st.session_state["_docx_path"]).exists():
            with open(st.session_state["_docx_path"], "rb") as f:
                st.download_button(
                    "⬇️ Download DOCX",
                    data=f.read(),
                    file_name=st.session_state["_docx_name"],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )

        st.caption(f"Generated files are also saved to: `{config.OUTPUTS_DIR}`")