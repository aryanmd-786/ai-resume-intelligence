"""
utils/error_handlers.py
-----------------------
Centralized error handling for the entire app.

Every page can wrap risky code with `safe_render(fn)` or use `show_error(exc)`
to display consistent, user-friendly errors instead of raw Python tracebacks.
"""

from __future__ import annotations

import streamlit as st

from services import ollama_service
from services.resume_parser import ResumeParserError


def show_error(exc: Exception, *, context: str = "Something went wrong") -> None:
    """
    Display a user-friendly error message based on the exception type.
    Never raises.
    """
    # Ollama-specific errors
    if isinstance(exc, ollama_service.OllamaNotRunningError):
        st.error(
            f"**{context}** — Ollama is not running.\n\n"
            "Open a new terminal and run:\n```\nollama serve\n```"
        )
        return

    if isinstance(exc, ollama_service.OllamaModelNotFoundError):
        st.error(
            f"**{context}** — The AI model is not installed.\n\n"
            f"Details: {exc}"
        )
        return

    if isinstance(exc, ollama_service.OllamaTimeoutError):
        st.error(
            f"**{context}** — The AI took too long to respond.\n\n"
            "Tips:\n"
            "- Use a shorter resume or job description\n"
            "- Close other heavy apps to free RAM\n"
            "- Try again in a moment"
        )
        return

    if isinstance(exc, ollama_service.OllamaInvalidResponseError):
        st.error(
            f"**{context}** — The AI returned unexpected output.\n\n"
            "This happens occasionally with smaller models. Just click the "
            "action button again to retry."
        )
        return

    if isinstance(exc, ollama_service.OllamaError):
        st.error(f"**{context}** — AI error.\n\nDetails: {exc}")
        return

    # Resume parsing errors
    if isinstance(exc, ResumeParserError):
        st.error(f"**{context}** — Could not read the resume.\n\n{exc}")
        return

    # Input errors
    if isinstance(exc, ValueError):
        st.warning(f"**{context}** — {exc}")
        return

    # Fallback: unexpected errors
    st.error(f"**{context}** — Unexpected error.")
    with st.expander("🔧 Technical details"):
        st.exception(exc)


def safe_render(render_fn, *, page_name: str = "page") -> None:
    """
    Render a page function with top-level error protection.
    Usage: safe_render(dashboard.render, page_name="Dashboard")
    """
    try:
        render_fn()
    except Exception as exc:
        show_error(exc, context=f"Failed to render {page_name}")