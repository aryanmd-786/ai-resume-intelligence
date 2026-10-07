"""
services/resume_generator.py
----------------------------
AI helpers for the Resume Builder.

STRICT RULE: The AI must never invent facts. It only *rephrases* and
*professionally reorganizes* what the user already provided.

Public API:
    - generate_summary(personal, skills, experience, education) -> str
    - improve_experience(company, role, responsibilities) -> str
    - improve_project(name, description, technologies) -> str
    - suggest_skills(target_role, existing_skills) -> list[str]
"""

from __future__ import annotations

import json
from typing import Any

from services import llm_service as ollama_service


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------
_NO_FABRICATION_RULE = """STRICT RULES:
- NEVER invent companies, job titles, dates, degrees, certifications, metrics,
  technologies, or achievements that the user did not provide.
- Do NOT add fake numbers (%, $, counts) unless the user already stated them.
- Only rephrase, tighten, and professionally format what the user gave you.
- Use active voice, strong action verbs, and concise business English.
- Output plain text only (no markdown, no headings, no extra commentary).
"""

SUMMARY_SYSTEM = f"""You are a professional resume writer.
{_NO_FABRICATION_RULE}
Write a 2-4 sentence professional summary in third-person-implied style."""


EXPERIENCE_SYSTEM = f"""You are a professional resume writer.
{_NO_FABRICATION_RULE}
Rewrite the responsibilities as 3-5 crisp resume bullet points,
each starting with a strong action verb (e.g., Developed, Led, Designed).
Return each bullet on its own line, prefixed with "• "."""


PROJECT_SYSTEM = f"""You are a professional resume writer.
{_NO_FABRICATION_RULE}
Rewrite the project description into 2-4 impactful resume bullets.
Return each bullet on its own line, prefixed with "• "."""


SKILLS_SYSTEM = """You are a career coach helping a candidate identify relevant skills.
Respond ONLY with a valid JSON object. No prose.

STRICT RULES:
- Only suggest skills that are commonly expected for the given role.
- Do NOT claim the candidate already has them.
- Return skills the candidate is MISSING compared to the role.
- Max 8 skills. Short names (1-3 words)."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _join(items: list[str], limit: int = 8) -> str:
    clean = [str(x).strip() for x in (items or []) if str(x).strip()]
    return ", ".join(clean[:limit])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_summary(
    personal: dict,
    skills: list[str],
    experience: list[dict],
    education: list[dict],
) -> str:
    """Generate a professional summary from existing user data."""
    name = _safe_text(personal.get("full_name")) or "the candidate"
    location = _safe_text(personal.get("location"))
    skill_str = _join(skills, 10)

    exp_lines = []
    for e in (experience or [])[:4]:
        role = _safe_text(e.get("role"))
        company = _safe_text(e.get("company"))
        if role or company:
            exp_lines.append(f"- {role} at {company}".strip(" at"))

    edu_lines = []
    for ed in (education or [])[:2]:
        degree = _safe_text(ed.get("degree"))
        inst = _safe_text(ed.get("institution"))
        if degree or inst:
            edu_lines.append(f"- {degree} — {inst}".strip(" —"))

    prompt = f"""Write a professional resume summary for the following candidate.

Name: {name}
Location: {location or 'not specified'}

Skills: {skill_str or 'not specified'}

Experience:
{chr(10).join(exp_lines) if exp_lines else '- no experience listed'}

Education:
{chr(10).join(edu_lines) if edu_lines else '- no education listed'}

Write 2-4 sentences. Focus on strengths, domain, and value.
Do not invent facts. Do not include the name in the summary.
Return plain text only."""

    return ollama_service.generate(prompt, system=SUMMARY_SYSTEM, timeout=180).strip()


def improve_experience(company: str, role: str, responsibilities: str) -> str:
    """Rewrite responsibilities as professional resume bullets."""
    company = _safe_text(company) or "the company"
    role = _safe_text(role) or "the role"
    resp = _safe_text(responsibilities)

    if not resp:
        raise ValueError("Please enter the responsibilities first.")

    prompt = f"""Role: {role}
Company: {company}
Raw responsibilities provided by the candidate:
---
{resp}
---

Rewrite these as 3-5 professional resume bullet points.
Preserve every fact. Do not add anything new.
Start each bullet with a strong action verb. Prefix each bullet with "• ".
Return only the bullet points."""

    return ollama_service.generate(prompt, system=EXPERIENCE_SYSTEM, timeout=180).strip()


def improve_project(name: str, description: str, technologies: str) -> str:
    """Rewrite a project description as professional resume bullets."""
    name = _safe_text(name) or "the project"
    desc = _safe_text(description)
    tech = _safe_text(technologies)

    if not desc:
        raise ValueError("Please enter a project description first.")

    prompt = f"""Project: {name}
Technologies: {tech or 'not specified'}
Raw description:
---
{desc}
---

Rewrite this as 2-4 professional resume bullet points.
Preserve every fact. Do not add anything new.
Start each bullet with a strong action verb. Prefix each bullet with "• ".
Return only the bullet points."""

    return ollama_service.generate(prompt, system=PROJECT_SYSTEM, timeout=180).strip()


def suggest_skills(target_role: str, existing_skills: list[str]) -> list[str]:
    """Suggest commonly-expected skills for a role (excluding ones already listed)."""
    role = _safe_text(target_role)
    if not role:
        raise ValueError("Please enter a target role first.")

    existing = _join(existing_skills, 40)

    prompt = f"""Target role: {role}
Candidate already lists: {existing or 'nothing'}

Return JSON: {{"skills": ["skill1", "skill2", ...]}}
Only suggest skills the candidate is likely MISSING for this role.
Max 8 skills. Short names only. No duplicates with existing."""

    data = ollama_service.generate_json(prompt, system=SKILLS_SYSTEM, timeout=180)
    skills = data.get("skills", [])
    if not isinstance(skills, list):
        return []

    existing_lower = {s.lower() for s in (existing_skills or [])}
    out: list[str] = []
    for s in skills:
        text = _safe_text(s)
        if text and text.lower() not in existing_lower:
            out.append(text)
    return out[:8]