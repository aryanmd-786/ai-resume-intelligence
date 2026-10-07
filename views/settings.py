"""
views/settings.py
-----------------
Fully functional in Phase 1.
Shows Ollama status, installed models, active model, and a live test prompt.
"""

from __future__ import annotations

import streamlit as st

import config
from services import llm_service as ollama_service
from utils.health_check import run_all_checks
from utils.helpers import section_header


def render() -> None:
    st.markdown('<h1 class="page-title">⚙️ Settings</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-sub">Configure the local AI engine and inspect system status.</p>',
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # Ollama connection
    # ------------------------------------------------------------------
    st.markdown(section_header("Ollama Connection"), unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.text_input(
            "Ollama Base URL",
            value=config.OLLAMA_BASE_URL,
            disabled=True,
            help="Change this in config.py (OLLAMA_BASE_URL).",
        )
    with col2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Test Connection", use_container_width=True):
            st.session_state["_force_recheck"] = True

    ok, message = ollama_service.check_connection()
    if ok:
        st.success(f"✅ Ollama is reachable — {message}")
    else:
        st.error(f"❌ {message}")
        st.info(
            "**Fix:** Open PowerShell and run `ollama serve`, then pull the model with "
            f"`ollama pull {config.OLLAMA_MODEL}`."
        )

    # ------------------------------------------------------------------
    # Model selection
    # ------------------------------------------------------------------
    st.markdown(section_header("AI Model"), unsafe_allow_html=True)

    installed = ollama_service.list_models()

    if installed:
        current_index = (
            installed.index(config.OLLAMA_MODEL)
            if config.OLLAMA_MODEL in installed
            else 0
        )
        chosen = st.selectbox(
            "Active model",
            options=installed,
            index=current_index,
            help="Select any locally installed Ollama model.",
        )
        if chosen != config.OLLAMA_MODEL:
            config.set_model(chosen)
            st.success(f"Active model switched to **{chosen}**.")
            st.rerun()
    else:
        st.warning(
            "No models detected. Install one with:\n\n"
            f"```\nollama pull {config.OLLAMA_MODEL}\n```"
        )

    st.caption(
        "To make a model permanent across restarts, edit `OLLAMA_MODEL` in `config.py`."
    )

    # ------------------------------------------------------------------
    # Live test prompt
    # ------------------------------------------------------------------
    st.markdown(section_header("Live AI Test"), unsafe_allow_html=True)

    prompt = st.text_area(
        "Send a test prompt to Ollama",
        value="Reply with a single word: OK",
        height=80,
    )

    if st.button("▶️ Run Test", type="primary"):
        with st.spinner("Calling Ollama..."):
            try:
                reply = ollama_service.generate(prompt, timeout=60)
                st.success("Response received")
                st.code(reply, language="text")
            except ollama_service.OllamaNotRunningError as exc:
                st.error(f"Ollama is not running. {exc}")
            except ollama_service.OllamaModelNotFoundError as exc:
                st.error(f"Model missing. {exc}")
            except ollama_service.OllamaTimeoutError as exc:
                st.error(f"Timeout. {exc}")
            except ollama_service.OllamaInvalidResponseError as exc:
                st.error(f"Invalid response. {exc}")
            except ollama_service.OllamaError as exc:
                st.error(f"Ollama error: {exc}")
            except Exception as exc:  # never crash the app
                st.error(f"Unexpected error: {exc}")

        # ------------------------------------------------------------------
    # System health
    # ------------------------------------------------------------------
    st.markdown(section_header("System Health"), unsafe_allow_html=True)

    if st.button("🔄 Run Diagnostics", use_container_width=False):
        st.session_state["_health_ran"] = True

    if st.session_state.get("_health_ran"):
        with st.spinner("Running diagnostics..."):
            results = run_all_checks()

        for item in results:
            status = item["status"]
            name = item["name"]
            msg = item["message"]
            fix = item.get("fix", "")

            if status == "ok":
                st.success(f"✅ **{name}** — {msg}")
            elif status == "warn":
                st.warning(f"⚠️ **{name}** — {msg}")
                if fix:
                    st.caption(f"Fix: {fix}")
            else:
                st.error(f"❌ **{name}** — {msg}")
                if fix:
                    st.caption(f"Fix: {fix}")
    # ------------------------------------------------------------------
    # Privacy
    # ------------------------------------------------------------------
    st.markdown(section_header("Privacy"), unsafe_allow_html=True)
    st.markdown(
        """
        <div class="privacy-note">
            🔒 Your resume is processed <b>locally</b> using Ollama.
            Your resume content is not intentionally sent to any third-party AI service.
        </div>
        """,
        unsafe_allow_html=True,
    )