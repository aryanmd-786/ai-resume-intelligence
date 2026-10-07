"""
services/job_matcher.py
-----------------------
AI-powered Resume ↔ Job Description matching.

Public API:
    - match_job_description(resume_text, job_description) -> dict
    - analyze_skill_gap(resume_text, job_description) -> dict
"""

from __future__ import annotations

from typing import Any

from services import llm_service as ollama_service


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------
MATCH_SYSTEM = """You are a senior technical recruiter and ATS specialist.
Compare a candidate's resume against a job description and return an
honest, structured evaluation.

STRICT RULES:
- Respond ONLY with a single valid JSON object. No prose. No markdown fences.
- Base your analysis STRICTLY on the given resume and job description.
- Do not invent skills, experience, or keywords.
- All scores are integers between 0 and 100.
"""

MATCH_PROMPT_TEMPLATE = """Compare the RESUME against the JOB DESCRIPTION.

Return a JSON object with EXACTLY this schema:

{{
  "match_score": <int 0-100>,
  "matched_skills": ["<skills the candidate has that the job requires>"],
  "missing_skills": ["<skills the job requires that are absent from the resume>"],
  "matched_keywords": ["<important JD keywords present in the resume>"],
  "missing_keywords": ["<important JD keywords absent from the resume>"],
  "experience_relevance": <int 0-100>,
  "education_relevance": <int 0-100>,
  "recommendations": ["<3-6 tailored recommendations to improve the match>"],
  "summary": "<2-3 sentence assessment>"
}}

Scoring guidance:
- match_score: weighted overall fit (skills 50%, experience 25%, education 15%, keywords 10%).
- experience_relevance: how well the resume's experience aligns with the role.
- education_relevance: how well the resume's education aligns with the role.

JOB DESCRIPTION:
---
{job_description}
---

RESUME:
---
{resume_text}
---

Return ONLY the JSON object.
"""


SKILL_GAP_SYSTEM = """You are a career coach analyzing a skill gap.

Respond ONLY with a single valid JSON object. No prose. No markdown.

STRICT RULES:
- Only reason about skills that appear in either the resume or job description.
- Do not invent skills.
- If the resume shows a skill but weakly, put it under "need_improvement".
- If the resume clearly shows strong skill, put it under "already_have".
- If the JD requires a skill not present in the resume, put it under "missing".
"""

SKILL_GAP_PROMPT_TEMPLATE = """Analyze the skill gap between a RESUME and a JOB DESCRIPTION.

Return a JSON object with EXACTLY this schema:

{{
  "already_have": [
    {{"skill": "<name>", "level": "Strong"}}
  ],
  "need_improvement": [
    {{"skill": "<name>", "level": "Basic"}}
  ],
  "missing": ["<skill>"],
  "roadmap": [
    {{
      "phase": "Week 1-2",
      "focus": "<theme>",
      "actions": ["<concrete action>", "<another action>"]
    }}
  ],
  "summary": "<2-3 sentence overview of the gap>"
}}

Rules:
- level must be one of: "Strong", "Intermediate", "Basic".
- already_have: skills that clearly appear in the resume.
- need_improvement: skills mentioned but weakly / without depth.
- missing: required by JD, absent from resume.
- roadmap: 3-5 phases, each with 2-4 concrete actions.
- Max 20 skills total across all buckets.

JOB DESCRIPTION:
---
{job_description}
---

RESUME:
---
{resume_text}
---

Return ONLY the JSON object.
"""


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def _safe_int(value: Any, default: int = 0) -> int:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(0, min(100, n))


def _safe_str_list(value: Any, max_items: int = 40) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if item is None:
            continue
        text = str(item).strip()
        if text and text not in out:
            out.append(text)
        if len(out) >= max_items:
            break
    return out


def _truncate(text: str, limit: int = 6000) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[...truncated...]"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def match_job_description(resume_text: str, job_description: str) -> dict:
    """
    Return a normalized match dict.
    Never raises on bad AI JSON — always returns a safe structure.
    """
    resume = _truncate(resume_text)
    jd = _truncate(job_description, 4000)

    if len(resume) < 50:
        raise ValueError("Resume text is too short. Upload a resume first.")
    if len(jd) < 40:
        raise ValueError("Job description is too short. Paste a proper JD.")

    prompt = MATCH_PROMPT_TEMPLATE.format(job_description=jd, resume_text=resume)
    raw = ollama_service.generate_json(prompt, system=MATCH_SYSTEM, timeout=300)

    return {
        "match_score": _safe_int(raw.get("match_score")),
        "matched_skills": _safe_str_list(raw.get("matched_skills"), 30),
        "missing_skills": _safe_str_list(raw.get("missing_skills"), 30),
        "matched_keywords": _safe_str_list(raw.get("matched_keywords"), 30),
        "missing_keywords": _safe_str_list(raw.get("missing_keywords"), 30),
        "experience_relevance": _safe_int(raw.get("experience_relevance")),
        "education_relevance": _safe_int(raw.get("education_relevance")),
        "recommendations": _safe_str_list(raw.get("recommendations"), 10),
        "summary": str(raw.get("summary") or "").strip(),
    }


def _normalize_skill_list(value: Any) -> list[dict]:
    """Normalize already_have / need_improvement buckets."""
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    valid_levels = {"Strong", "Intermediate", "Basic"}
    for item in value[:25]:
        if isinstance(item, dict):
            skill = str(item.get("skill") or "").strip()
            level = str(item.get("level") or "Intermediate").strip()
            if level not in valid_levels:
                level = "Intermediate"
            if skill:
                out.append({"skill": skill, "level": level})
        elif isinstance(item, str) and item.strip():
            out.append({"skill": item.strip(), "level": "Intermediate"})
    return out


def _normalize_roadmap(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    for item in value[:6]:
        if not isinstance(item, dict):
            continue
        phase = str(item.get("phase") or "").strip()
        focus = str(item.get("focus") or "").strip()
        actions = _safe_str_list(item.get("actions"), 6)
        if phase or focus:
            out.append({"phase": phase or "Next", "focus": focus, "actions": actions})
    return out


def analyze_skill_gap(resume_text: str, job_description: str) -> dict:
    """Return categorized skill gap + learning roadmap."""
    resume = _truncate(resume_text)
    jd = _truncate(job_description, 4000)

    if len(resume) < 50:
        raise ValueError("Resume text is too short.")
    if len(jd) < 40:
        raise ValueError("Job description is too short.")

    prompt = SKILL_GAP_PROMPT_TEMPLATE.format(job_description=jd, resume_text=resume)
    raw = ollama_service.generate_json(prompt, system=SKILL_GAP_SYSTEM, timeout=300)

    return {
        "already_have": _normalize_skill_list(raw.get("already_have")),
        "need_improvement": _normalize_skill_list(raw.get("need_improvement")),
        "missing": _safe_str_list(raw.get("missing"), 30),
        "roadmap": _normalize_roadmap(raw.get("roadmap")),
        "summary": str(raw.get("summary") or "").strip(),
    }