"""
services/llm_service.py
-----------------------
Smart LLM wrapper — supports BOTH:
  1. Ollama (local)  — for local development
  2. Groq (cloud)    — for Streamlit Cloud deployment

Choose backend automatically based on environment or config.
All other services use THIS module, so switching backends is transparent.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from services import ollama_service


# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------
def _detect_backend() -> str:
    """
    Return "groq" if GROQ_API_KEY is set, else "ollama".
    Also allows forcing via LLM_BACKEND env var.
    """
    forced = (os.getenv("LLM_BACKEND") or "").strip().lower()
    if forced in ("groq", "ollama"):
        return forced

    if (os.getenv("GROQ_API_KEY") or "").strip():
        return "groq"

    return "ollama"


# ---------------------------------------------------------------------------
# Groq backend
# ---------------------------------------------------------------------------
_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
# Available free models:
#   llama-3.1-8b-instant       (fastest, good quality)
#   llama-3.3-70b-versatile    (best quality, slightly slower)
#   mixtral-8x7b-32768         (long context)


def _groq_generate(
    prompt: str,
    system: Optional[str],
    *,
    json_mode: bool,
    temperature: float,
    timeout: int,
) -> str:
    """Call Groq API. Raises ollama_service.Ollama* errors on failure."""
    try:
        from groq import Groq
    except ImportError:
        raise ollama_service.OllamaError(
            "Groq SDK not installed. Run: pip install groq"
        )

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ollama_service.OllamaNotRunningError(
            "GROQ_API_KEY not set. Cloud AI is unavailable."
        )

    try:
        client = Groq(api_key=api_key, timeout=timeout)
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": _GROQ_MODEL,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        content = (response.choices[0].message.content or "").strip()
        if not content:
            raise ollama_service.OllamaInvalidResponseError("Groq returned empty response.")
        return content

    except ollama_service.OllamaError:
        raise
    except Exception as exc:
        err = str(exc).lower()
        if "timeout" in err or "timed out" in err:
            raise ollama_service.OllamaTimeoutError(f"Groq timed out: {exc}")
        if "api key" in err or "unauthorized" in err or "401" in err:
            raise ollama_service.OllamaError(
                "Invalid Groq API key. Check GROQ_API_KEY."
            )
        raise ollama_service.OllamaError(f"Groq error: {exc}")


# ---------------------------------------------------------------------------
# Unified public API — same as ollama_service
# ---------------------------------------------------------------------------
def generate(
    prompt: str,
    system: Optional[str] = None,
    *,
    json_mode: bool = False,
    temperature: Optional[float] = None,
    timeout: Optional[int] = None,
) -> str:
    """Unified generate — routes to Groq or Ollama."""
    backend = _detect_backend()

    if backend == "groq":
        return _groq_generate(
            prompt,
            system,
            json_mode=json_mode,
            temperature=temperature if temperature is not None else 0.3,
            timeout=timeout or 60,
        )

    # Fallback to Ollama
    return ollama_service.generate(
        prompt,
        system=system,
        json_mode=json_mode,
        temperature=temperature,
        timeout=timeout,
    )


def generate_json(
    prompt: str,
    system: Optional[str] = None,
    *,
    temperature: Optional[float] = None,
    timeout: Optional[int] = None,
) -> dict:
    """Unified JSON generate — routes to Groq or Ollama."""
    raw = generate(
        prompt,
        system=system,
        json_mode=True,
        temperature=temperature if temperature is not None else 0.2,
        timeout=timeout,
    )

    # Reuse the same JSON extraction logic from ollama_service
    from services.ollama_service import _extract_json_block

    candidate = _extract_json_block(raw)
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ollama_service.OllamaInvalidResponseError(
            f"AI returned invalid JSON. Preview: {raw[:200]}"
        ) from exc

    if not isinstance(data, dict):
        raise ollama_service.OllamaInvalidResponseError("AI JSON was not an object.")
    return data


def check_connection() -> tuple[bool, str]:
    """Unified connection check."""
    backend = _detect_backend()

    if backend == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return False, "GROQ_API_KEY not set."
        try:
            from groq import Groq
            client = Groq(api_key=api_key, timeout=10)
            client.chat.completions.create(
                model=_GROQ_MODEL,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return True, f"Groq connected ({_GROQ_MODEL})"
        except Exception as exc:
            return False, f"Groq error: {exc}"

    return ollama_service.check_connection()


def current_backend() -> str:
    """Return 'groq' or 'ollama' — useful for UI display."""
    return _detect_backend()


def backend_label() -> str:
    """Human-readable label for the current backend."""
    b = _detect_backend()
    if b == "groq":
        return f"Groq Cloud ({_GROQ_MODEL})"
    return f"Ollama Local ({ollama_service.config.OLLAMA_MODEL})"