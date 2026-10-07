"""
services/resume_analyzer.py
---------------------------
AI-powered resume analysis using Ollama.

Public API:
    - analyze_resume(resume_text) -> dict
    - extract_skills(resume_text) -> dict
    - ats_keyword_analysis(resume_text) -> dict
    - build_builder_seed(analysis, resume_text) -> dict

All functions return validated, safe dictionaries (never raise on bad AI JSON —
they normalize and fill defaults).
"""

from __future__ import annotations

from typing import Any


from services import llm_service as ollama_service


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
ANALYSIS_SYSTEM = """You are a senior technical recruiter, ATS specialist, and
resume coach. You evaluate resumes honestly and constructively.

STRICT RULES:
- Respond ONLY with a single valid JSON object. No prose. No markdown fences.
- Never invent facts not present in the resume.
- All scores are integers between 0 and 100.
- Feedback must be concrete and actionable.
"""

ANALYSIS_PROMPT_TEMPLATE = """Analyze the resume below and return a JSON object with EXACTLY this schema:

{{
  "scores": {{
    "overall": <int 0-100>,
    "ats": <int 0-100>,
    "content": <int 0-100>,
    "skills": <int 0-100>,
    "experience": <int 0-100>,
    "projects": <int 0-100>,
    "formatting": <int 0-100>
  }},
  "strengths": ["<3-6 concise strengths>"],
  "weaknesses": ["<3-6 concise weaknesses>"],
  "recommendations": ["<3-6 actionable recommendations>"],
  "summary": "<2-3 sentence overall assessment>"
}}

Scoring guidance:
- overall: weighted average of the others.
- ats: keyword usage, standard section headings, parseability.
- content: clarity, impact, measurable outcomes.
- skills: breadth and relevance of technical + soft skills.
- experience: quality of work experience / internships.
- projects: depth, complexity, and description quality.
- formatting: consistency, readability, professional structure.

RESUME:
---
{resume_text}
---

Return ONLY the JSON object.
"""


SKILLS_SYSTEM = """You are an expert resume skill extractor.
Respond ONLY with a single valid JSON object. No markdown. No prose.
Only include skills that actually appear (or are clearly implied) in the resume.
"""

SKILLS_PROMPT_TEMPLATE = """Extract skills from the resume and categorize them.

Return JSON with EXACTLY this schema:

{{
  "programming_languages": ["..."],
  "frameworks": ["..."],
  "databases": ["..."],
  "cloud": ["..."],
  "tools": ["..."],
  "technical_skills": ["..."],
  "soft_skills": ["..."]
}}

Rules:
- Each category is an array of short strings (1-3 words each).
- No duplicates across categories.
- Use canonical names ("Python", not "python programming").
- If a category has nothing, return an empty array [].

RESUME:
---
{resume_text}
---

Return ONLY the JSON object.
"""


ATS_SYSTEM = """You are an ATS (Applicant Tracking System) simulation expert.
Respond ONLY with a single valid JSON object. No markdown. No prose.
"""

ATS_PROMPT_TEMPLATE = """Perform an ATS-style keyword analysis on this resume.

Return JSON with EXACTLY this schema:

{{
  "matched_keywords": ["<keywords present and ATS-relevant>"],
  "missing_keywords": ["<keywords commonly expected but absent>"],
  "important_keywords": ["<top 8-12 most impactful keywords for this resume's target field>"],
  "keyword_density": {{"<keyword>": <int occurrence count>}},
  "suggestions": ["<2-5 concrete ways to improve ATS performance>"]
}}

Rules:
- 8-20 items per keyword list.
- density should only include the 10 most frequent meaningful keywords.
- Do not include stop-words (and, the, of, etc).

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


def _safe_str_list(value: Any, max_items: int = 30) -> list[str]:
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
    return text[:limit] + "\n\n[...truncated for analysis...]"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def analyze_resume(resume_text: str) -> dict:
    """
    Return a normalized dict:
    {
      scores: {overall, ats, content, skills, experience, projects, formatting},
      strengths: [...],
      weaknesses: [...],
      recommendations: [...],
      summary: str,
    }
    """
    text = _truncate(resume_text)
    if len(text) < 100:
        raise ValueError("Resume text is too short to analyze meaningfully.")

    prompt = ANALYSIS_PROMPT_TEMPLATE.format(resume_text=text)
    raw = ollama_service.generate_json(prompt, system=ANALYSIS_SYSTEM, timeout=300)

    scores_in = raw.get("scores") or {}
    scores = {
        "overall": _safe_int(scores_in.get("overall"), 0),
        "ats": _safe_int(scores_in.get("ats"), 0),
        "content": _safe_int(scores_in.get("content"), 0),
        "skills": _safe_int(scores_in.get("skills"), 0),
        "experience": _safe_int(scores_in.get("experience"), 0),
        "projects": _safe_int(scores_in.get("projects"), 0),
        "formatting": _safe_int(scores_in.get("formatting"), 0),
    }

    # Fallback: compute overall if the model forgot
    if scores["overall"] == 0:
        parts = [
            scores["ats"], scores["content"], scores["skills"],
            scores["experience"], scores["projects"], scores["formatting"],
        ]
        scores["overall"] = int(sum(parts) / len(parts))

    return {
        "scores": scores,
        "strengths": _safe_str_list(raw.get("strengths"), 8),
        "weaknesses": _safe_str_list(raw.get("weaknesses"), 8),
        "recommendations": _safe_str_list(raw.get("recommendations"), 8),
        "summary": str(raw.get("summary") or "").strip(),
    }


def extract_skills(resume_text: str) -> dict:
    """Return categorized skills. Never raises on bad AI output."""
    text = _truncate(resume_text)
    if len(text) < 50:
        return {
            "programming_languages": [], "frameworks": [], "databases": [],
            "cloud": [], "tools": [], "technical_skills": [], "soft_skills": [],
            "total": 0,
        }

    prompt = SKILLS_PROMPT_TEMPLATE.format(resume_text=text)
    raw = ollama_service.generate_json(prompt, system=SKILLS_SYSTEM, timeout=240)

    categories = [
        "programming_languages", "frameworks", "databases",
        "cloud", "tools", "technical_skills", "soft_skills",
    ]
    result: dict[str, Any] = {}
    total = 0
    for cat in categories:
        items = _safe_str_list(raw.get(cat), 40)
        result[cat] = items
        total += len(items)

    result["total"] = total
    return result


def ats_keyword_analysis(resume_text: str) -> dict:
    """Return ATS-style keyword breakdown. Never raises on bad AI output."""
    text = _truncate(resume_text)
    if len(text) < 50:
        return {
            "matched_keywords": [], "missing_keywords": [],
            "important_keywords": [], "keyword_density": {},
            "suggestions": [],
        }

    prompt = ATS_PROMPT_TEMPLATE.format(resume_text=text)
    raw = ollama_service.generate_json(prompt, system=ATS_SYSTEM, timeout=240)

    density_in = raw.get("keyword_density") or {}
    density: dict[str, int] = {}
    if isinstance(density_in, dict):
        for k, v in density_in.items():
            try:
                density[str(k)] = int(v)
            except (TypeError, ValueError):
                continue

    return {
        "matched_keywords": _safe_str_list(raw.get("matched_keywords"), 30),
        "missing_keywords": _safe_str_list(raw.get("missing_keywords"), 30),
        "important_keywords": _safe_str_list(raw.get("important_keywords"), 20),
        "keyword_density": density,
        "suggestions": _safe_str_list(raw.get("suggestions"), 10),
    }


def build_builder_seed(analysis: dict, resume_text: str) -> dict:
    """
    Create a builder-friendly seed dict from an analysis result.
    Phase 3 (Builder) will consume this to prefill fields.
    """
    return {
        "source_resume_text": resume_text,
        "scores": (analysis or {}).get("scores", {}),
        "recommendations": (analysis or {}).get("recommendations", []),
        # Phase 3 will fill in actual fields after parsing
    }