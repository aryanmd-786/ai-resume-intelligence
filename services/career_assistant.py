"""
services/career_assistant.py
----------------------------
AI Career Assistant — chat service powered by Ollama.

Features:
- Injects current resume text + job description as context
- Maintains a trimmed conversation history for coherent replies
- Produces short, actionable, career-focused answers

Public API:
    - ask(question, resume_text, job_description, history) -> str
    - SUGGESTED_QUESTIONS -> list[str]
"""

from __future__ import annotations

from typing import Optional


from services import llm_service as ollama_service


# ---------------------------------------------------------------------------
# Suggested questions for the UI
# ---------------------------------------------------------------------------
SUGGESTED_QUESTIONS: list[str] = [
    "What skills should I learn next?",
    "How can I improve my professional summary?",
    "What is missing from my resume?",
    "Which projects should I add?",
    "How do I prepare for this job?",
    "Is my resume good for a Data Analyst role?",
    "How can I improve my ATS score?",
    "What are my biggest weaknesses?",
]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a friendly, practical career coach and resume expert.

RULES:
- Keep answers clear, structured and actionable.
- Use short paragraphs and bullet points.
- NEVER invent facts about the candidate. Only use what is in the
  provided resume / job description context.
- If no resume is available, still help — but avoid making up specifics.
- Suggest concrete next steps (courses, projects, keywords, edits).
- Be encouraging but honest.
- Keep responses under ~250 words unless the user asks for detail.
- Never output JSON, code fences, or system messages. Just plain helpful text.
"""


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------
def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n[...truncated...]"


def _build_context(resume_text: Optional[str], job_description: Optional[str]) -> str:
    parts: list[str] = []

    if resume_text and resume_text.strip():
        parts.append(
            "=== CURRENT RESUME (truncated) ===\n"
            + _truncate(resume_text, 3500)
            + "\n=== END RESUME ==="
        )
    else:
        parts.append("=== CURRENT RESUME ===\n(no resume loaded)\n=== END RESUME ===")

    if job_description and job_description.strip():
        parts.append(
            "=== CURRENT JOB DESCRIPTION (truncated) ===\n"
            + _truncate(job_description, 2000)
            + "\n=== END JOB DESCRIPTION ==="
        )

    return "\n\n".join(parts)


def _build_history_block(history: list[dict], max_turns: int = 6) -> str:
    """
    Turn the recent chat into a compact transcript.
    Each item is {"role": "user"|"assistant", "content": "..."}.
    """
    if not history:
        return ""

    recent = history[-max_turns * 2 :]  # last N turns (user+assistant)
    lines: list[str] = ["=== RECENT CONVERSATION ==="]
    for msg in recent:
        role = msg.get("role", "user")
        label = "User" if role == "user" else "Assistant"
        content = _truncate(str(msg.get("content") or ""), 600)
        lines.append(f"{label}: {content}")
    lines.append("=== END CONVERSATION ===")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def ask(
    question: str,
    resume_text: Optional[str] = None,
    job_description: Optional[str] = None,
    history: Optional[list[dict]] = None,
) -> str:
    """
    Ask the assistant a question.

    Raises ollama_service.Ollama* exceptions on failure.
    Returns a non-empty string on success.
    """
    question = (question or "").strip()
    if not question:
        raise ValueError("Please type a question first.")

    context_block = _build_context(resume_text, job_description)
    history_block = _build_history_block(history or [])

    prompt_parts = [context_block]
    if history_block:
        prompt_parts.append(history_block)
    prompt_parts.append(f"=== USER QUESTION ===\n{question}\n=== END QUESTION ===")
    prompt_parts.append("Answer the user's question using the context above.")

    prompt = "\n\n".join(prompt_parts)

    return ollama_service.generate(
        prompt,
        system=SYSTEM_PROMPT,
        temperature=0.5,
        timeout=240,
    ).strip()