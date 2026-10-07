"""
services/resume_pdf.py
----------------------
Generate a professional PDF resume using ReportLab.
Template is driven by a theme dict.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


def _safe(value: Any) -> str:
    return str(value or "").strip()


def _escape(text: str) -> str:
    # ReportLab Paragraph uses XML-ish markup; escape user input.
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


def _bullet_lines(text: str) -> list[str]:
    """Split a multi-line text into bullet lines, dropping empty ones."""
    lines: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip().lstrip("•-*").strip()
        if line:
            lines.append(line)
    return lines


def _build_styles(theme: dict) -> dict:
    primary = HexColor(theme["primary"])
    text_col = HexColor(theme["text"])
    muted = HexColor(theme["muted"])

    name_align = TA_CENTER if theme.get("header_align") == "center" else TA_LEFT

    return {
        "name": ParagraphStyle(
            "name",
            fontName=theme["pdf_font_bold"],
            fontSize=theme["name_size"],
            leading=theme["name_size"] + 2,
            textColor=text_col,
            alignment=name_align,
            spaceAfter=2,
        ),
        "contact": ParagraphStyle(
            "contact",
            fontName=theme["pdf_font_body"],
            fontSize=theme["body_size"] - 0.5,
            leading=theme["body_size"] + 3,
            textColor=muted,
            alignment=name_align,
            spaceAfter=8,
        ),
        "section": ParagraphStyle(
            "section",
            fontName=theme["pdf_font_bold"],
            fontSize=theme["section_size"],
            leading=theme["section_size"] + 2,
            textColor=primary,
            alignment=TA_LEFT,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            fontName=theme["pdf_font_body"],
            fontSize=theme["body_size"],
            leading=theme["body_size"] + 3,
            textColor=text_col,
            spaceAfter=2,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            fontName=theme["pdf_font_body"],
            fontSize=theme["body_size"],
            leading=theme["body_size"] + 3,
            textColor=text_col,
            leftIndent=10,
            bulletIndent=2,
            spaceAfter=1,
        ),
        "entry_title": ParagraphStyle(
            "entry_title",
            fontName=theme["pdf_font_bold"],
            fontSize=theme["body_size"] + 1,
            leading=theme["body_size"] + 3,
            textColor=text_col,
            spaceAfter=1,
        ),
        "entry_meta": ParagraphStyle(
            "entry_meta",
            fontName=theme["pdf_font_italic"],
            fontSize=theme["body_size"] - 0.5,
            leading=theme["body_size"] + 2,
            textColor=muted,
            spaceAfter=3,
        ),
    }


def _section_heading(text: str, theme: dict, styles: dict) -> list:
    """Return flowables for a section heading (with optional colored bar)."""
    label = text.upper() if theme.get("section_uppercase") else text
    flow = [Paragraph(_escape(label), styles["section"])]

    if theme.get("section_bar"):
        flow.append(
            HRFlowable(
                width="100%",
                thickness=1.2,
                color=HexColor(theme["primary"]),
                spaceBefore=0,
                spaceAfter=6,
            )
        )
    else:
        flow.append(
            HRFlowable(
                width="100%",
                thickness=0.5,
                color=HexColor(theme["divider"]),
                spaceBefore=0,
                spaceAfter=6,
            )
        )
    return flow


def _bullets(text: str, styles: dict) -> list:
    lines = _bullet_lines(text)
    return [Paragraph(f"•&nbsp;&nbsp;{_escape(l)}", styles["bullet"]) for l in lines]


def generate_pdf(data: dict, theme: dict, output_path: Path) -> Path:
    """Write a PDF resume to output_path and return it."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = _build_styles(theme)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=_safe(data.get("personal", {}).get("full_name")) or "Resume",
    )

    flow: list = []

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    personal = data.get("personal", {}) or {}
    name = _safe(personal.get("full_name")) or "Your Name"
    flow.append(Paragraph(_escape(name), styles["name"]))

    contact_parts: list[str] = []
    for key in ("email", "phone", "location"):
        v = _safe(personal.get(key))
        if v:
            contact_parts.append(v)

    links: list[str] = []
    for key in ("linkedin", "github", "portfolio"):
        v = _safe(personal.get(key))
        if v:
            links.append(v)

    contact_line = "  •  ".join(contact_parts)
    if contact_line:
        flow.append(Paragraph(_escape(contact_line), styles["contact"]))
    if links:
        flow.append(Paragraph(_escape("  |  ".join(links)), styles["contact"]))

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    summary = _safe(data.get("summary"))
    if summary:
        flow += _section_heading("Professional Summary", theme, styles)
        flow.append(Paragraph(_escape(summary), styles["body"]))

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------
    skills = data.get("skills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    skills = [str(s).strip() for s in skills if str(s).strip()]
    if skills:
        flow += _section_heading("Skills", theme, styles)
        flow.append(Paragraph(_escape(", ".join(skills)), styles["body"]))

    # ------------------------------------------------------------------
    # Experience
    # ------------------------------------------------------------------
    experience = data.get("experience") or []
    valid_exp = [
        e for e in experience
        if any(_safe(e.get(k)) for k in ("role", "company", "responsibilities"))
    ]
    if valid_exp:
        flow += _section_heading("Experience", theme, styles)
        for e in valid_exp:
            role = _safe(e.get("role"))
            company = _safe(e.get("company"))
            duration = _safe(e.get("duration"))

            title = " — ".join(x for x in (role, company) if x) or "Experience"
            flow.append(Paragraph(_escape(title), styles["entry_title"]))
            if duration:
                flow.append(Paragraph(_escape(duration), styles["entry_meta"]))

            for b in _bullets(e.get("responsibilities", ""), styles):
                flow.append(b)
            flow.append(Spacer(1, 4))

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------
    projects = data.get("projects") or []
    valid_prj = [
        p for p in projects
        if any(_safe(p.get(k)) for k in ("name", "description"))
    ]
    if valid_prj:
        flow += _section_heading("Projects", theme, styles)
        for p in valid_prj:
            name_p = _safe(p.get("name")) or "Project"
            tech = _safe(p.get("technologies"))
            url = _safe(p.get("url"))

            flow.append(Paragraph(_escape(name_p), styles["entry_title"]))
            meta_parts = []
            if tech:
                meta_parts.append(f"Tech: {tech}")
            if url:
                meta_parts.append(url)
            if meta_parts:
                flow.append(Paragraph(_escape("  •  ".join(meta_parts)), styles["entry_meta"]))

            for b in _bullets(p.get("description", ""), styles):
                flow.append(b)
            flow.append(Spacer(1, 4))

    # ------------------------------------------------------------------
    # Education
    # ------------------------------------------------------------------
    education = data.get("education") or []
    valid_edu = [
        e for e in education
        if any(_safe(e.get(k)) for k in ("degree", "institution"))
    ]
    if valid_edu:
        flow += _section_heading("Education", theme, styles)
        for e in valid_edu:
            degree = _safe(e.get("degree"))
            inst = _safe(e.get("institution"))
            year = _safe(e.get("year"))
            score = _safe(e.get("score"))

            title = " — ".join(x for x in (degree, inst) if x) or "Education"
            flow.append(Paragraph(_escape(title), styles["entry_title"]))

            meta_parts = []
            if year:
                meta_parts.append(year)
            if score:
                meta_parts.append(f"Score: {score}")
            if meta_parts:
                flow.append(Paragraph(_escape("  •  ".join(meta_parts)), styles["entry_meta"]))
            flow.append(Spacer(1, 3))

    # ------------------------------------------------------------------
    # Certifications / Achievements
    # ------------------------------------------------------------------
    certs = [c for c in (data.get("certifications") or []) if _safe(c)]
    if certs:
        flow += _section_heading("Certifications", theme, styles)
        for c in certs:
            flow.append(Paragraph(f"•&nbsp;&nbsp;{_escape(_safe(c))}", styles["bullet"]))

    achievements = [a for a in (data.get("achievements") or []) if _safe(a)]
    if achievements:
        flow += _section_heading("Achievements", theme, styles)
        for a in achievements:
            flow.append(Paragraph(f"•&nbsp;&nbsp;{_escape(_safe(a))}", styles["bullet"]))

    # ------------------------------------------------------------------
    # Languages / Interests
    # ------------------------------------------------------------------
    languages = data.get("languages") or []
    if isinstance(languages, str):
        languages = [s.strip() for s in languages.split(",") if s.strip()]
    languages = [str(x).strip() for x in languages if str(x).strip()]
    if languages:
        flow += _section_heading("Languages", theme, styles)
        flow.append(Paragraph(_escape(", ".join(languages)), styles["body"]))

    interests = data.get("interests") or []
    if isinstance(interests, str):
        interests = [s.strip() for s in interests.split(",") if s.strip()]
    interests = [str(x).strip() for x in interests if str(x).strip()]
    if interests:
        flow += _section_heading("Interests", theme, styles)
        flow.append(Paragraph(_escape(", ".join(interests)), styles["body"]))

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    doc.build(flow)
    return output_path