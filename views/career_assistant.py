"""
views/career_assistant.py
-------------------------
AI Career Assistant — Phase 6.

Chat UI that uses the current resume + JD as context.
"""

from __future__ import annotations

import streamlit as st

from services import career_assistant, ollama_service


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------
def _init_chat() -> None:
    if "chat_history" not in st.session_state or st.session_state.chat_history is None:
        st.session_state.chat_history = []


def _clear_chat() -> None:
    st.session_state.chat_history = []


def _context_status() -> tuple[bool, bool]:
    """Return (has_resume, has_jd)."""
    has_resume = bool((st.session_state.get("last_resume_text") or "").strip())
    has_jd = bool((st.session_state.get("last_job_description") or "").strip())
    return has_resume, has_jd


# ---------------------------------------------------------------------------
# Message rendering
# ---------------------------------------------------------------------------
def _render_message(role: str, content: str) -> None:
    if role == "user":
        with st.chat_message("user", avatar="🧑"):
            st.markdown(content)
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(content)


def _render_history() -> None:
    for msg in st.session_state.chat_history:
        _render_message(msg.get("role", "user"), msg.get("content", ""))


# ---------------------------------------------------------------------------
# Core question handler
# ---------------------------------------------------------------------------
def _handle_question(question: str) -> None:
    question = (question or "").strip()
    if not question:
        return

    # 1. Show user message
    st.session_state.chat_history.append({"role": "user", "content": question})
    _render_message("user", question)

    # 2. Call AI
    resume_text = st.session_state.get("last_resume_text")
    jd_text = st.session_state.get("last_job_description")

    with st.chat_message("assistant", avatar="🤖"):
        placeholder = st.empty()
        placeholder.markdown("_Thinking..._")

        try:
            answer = career_assistant.ask(
                question=question,
                resume_text=resume_text,
                job_description=jd_text,
                history=st.session_state.chat_history[:-1],
            )
            placeholder.markdown(answer)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": answer}
            )

        except ollama_service.OllamaNotRunningError:
            placeholder.error(
                "Ollama is not running. Start it with `ollama serve` in a separate terminal."
            )
        except ollama_service.OllamaModelNotFoundError as exc:
            placeholder.error(f"Model missing: {exc}")
        except ollama_service.OllamaTimeoutError:
            placeholder.error("AI timed out. Try a shorter question.")
        except ollama_service.OllamaInvalidResponseError as exc:
            placeholder.error(f"AI returned an invalid response. Try again. ({exc})")
        except ollama_service.OllamaError as exc:
            placeholder.error(f"AI error: {exc}")
        except ValueError as exc:
            placeholder.error(str(exc))
        except Exception as exc:
            placeholder.error(f"Something went wrong: {exc}")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def render() -> None:
    st.markdown('<h1 class="page-title">🤖 AI Career Assistant</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-sub">Chat with a local AI that knows your resume and job description.</p>',
        unsafe_allow_html=True,
    )

    _init_chat()

    # ------------------------------------------------------------------
    # Context status
    # ------------------------------------------------------------------
    has_resume, has_jd = _context_status()

    cols = st.columns([1, 1, 1])
    with cols[0]:
        if has_resume:
            st.markdown(
                '<div class="status-badge ok">📄 Resume loaded</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="status-badge err">📄 No resume in context</div>',
                unsafe_allow_html=True,
            )
    with cols[1]:
        if has_jd:
            st.markdown(
                '<div class="status-badge ok">🎯 Job description loaded</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="status-badge">🎯 No JD in context</div>',
                unsafe_allow_html=True,
            )
    with cols[2]:
        if st.button("🗑️ Clear chat", use_container_width=True):
            _clear_chat()
            st.rerun()

    if not has_resume and not has_jd:
        st.info(
            "💡 **Tip:** Analyze a resume and/or run a job match first — "
            "the assistant will use that context to give personalized answers."
        )

    st.markdown("---")

    # ------------------------------------------------------------------
    # Suggested questions
    # ------------------------------------------------------------------
    with st.expander("💡 Suggested questions", expanded=(len(st.session_state.chat_history) == 0)):
        suggestions = career_assistant.SUGGESTED_QUESTIONS
        cols = st.columns(2)
        for i, q in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(q, key=f"sugg_{i}", use_container_width=True):
                    _handle_question(q)
                    st.rerun()

    # ------------------------------------------------------------------
    # Chat area
    # ------------------------------------------------------------------
    if not st.session_state.chat_history:
        st.markdown(
            """
            <div class="info-panel" style="text-align:center; padding:2rem;">
                <div style="font-size:2.4rem;">🤖</div>
                <div style="font-weight:600; margin-top:0.5rem;">Ask me anything about your resume or career</div>
                <div style="color:#64748b; font-size:0.9rem; margin-top:0.5rem;">
                    Try: "What skills should I learn?" or "How can I improve my summary?"
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        _render_history()

    # ------------------------------------------------------------------
    # Input box (pinned to bottom conceptually)
    # ------------------------------------------------------------------
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    user_input = st.chat_input("Type your question...")
    if user_input:
        _handle_question(user_input)
        st.rerun()