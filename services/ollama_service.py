"""
services/ollama_service.py
--------------------------
Single point of contact with the local Ollama server.

Every other module MUST use these functions instead of calling Ollama directly.

Public API (Phase 1):
    - check_connection() -> (ok, message)
    - list_models() -> list[str]
    - generate(prompt, system, ...) -> str
    - generate_json(prompt, system, ...) -> dict

Future phases will add:
    - analyze_resume()
    - extract_skills()
    - match_job_description()
    - generate_summary()
    - improve_experience()
    - improve_project()
    - career_assistant()
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

import requests

import config


# ---------------------------------------------------------------------------
# Custom exceptions (so UI can show friendly messages)
# ---------------------------------------------------------------------------
class OllamaError(Exception):
    """Base class for all Ollama related errors."""


class OllamaNotRunningError(OllamaError):
    """Ollama server is not reachable."""


class OllamaModelNotFoundError(OllamaError):
    """Requested model is not installed in Ollama."""


class OllamaTimeoutError(OllamaError):
    """Ollama took too long to respond."""


class OllamaInvalidResponseError(OllamaError):
    """Ollama returned an empty or unparseable response."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _url(path: str) -> str:
    return f"{config.OLLAMA_BASE_URL.rstrip('/')}{path}"


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _extract_json_block(text: str) -> str:
    """
    Best-effort extraction of a JSON object from an LLM response.
    Handles fenced ```json ...``` blocks and raw { ... } blobs.
    """
    match = _JSON_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]

    return text.strip()


# ---------------------------------------------------------------------------
# Connection utilities
# ---------------------------------------------------------------------------
def check_connection() -> tuple[bool, str]:
    """
    Returns (ok: bool, message: str).
    Never raises — safe to call from the UI on every rerun.
    """
    try:
        response = requests.get(_url("/api/tags"), timeout=5)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        return False, "Ollama is not running. Start it with: ollama serve"
    except requests.exceptions.Timeout:
        return False, "Ollama connection timed out."
    except requests.exceptions.RequestException as exc:
        return False, f"Could not reach Ollama: {exc}"

    try:
        payload = response.json()
    except ValueError:
        return False, "Ollama returned an invalid response."

    models = [m.get("name", "") for m in payload.get("models", [])]
    if not models:
        return False, "Ollama is running but no models are installed."

    # Ollama sometimes returns "llama3.2:latest" vs "llama3.2" — compare loosely
    base_requested = config.OLLAMA_MODEL.split(":")[0]
    if not any(m == config.OLLAMA_MODEL or m.split(":")[0] == base_requested for m in models):
        return False, (
            f"Model '{config.OLLAMA_MODEL}' not found. "
            f"Run: ollama pull {config.OLLAMA_MODEL}"
        )

    return True, "Connected"


def list_models() -> list[str]:
    """Return the names of all locally installed Ollama models."""
    try:
        response = requests.get(_url("/api/tags"), timeout=5)
        response.raise_for_status()
        return [m.get("name", "") for m in response.json().get("models", [])]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Core generation
# ---------------------------------------------------------------------------
def generate(
    prompt: str,
    system: Optional[str] = None,
    *,
    json_mode: bool = False,
    temperature: Optional[float] = None,
    timeout: Optional[int] = None,
) -> str:
    """
    Send a prompt to Ollama and return the raw text response.

    Raises:
        OllamaNotRunningError, OllamaModelNotFoundError,
        OllamaTimeoutError, OllamaInvalidResponseError, OllamaError
    """
    if not prompt or not prompt.strip():
        raise OllamaInvalidResponseError("Prompt cannot be empty.")

    payload: dict[str, Any] = {
        "model": config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": (
                temperature if temperature is not None else config.OLLAMA_TEMPERATURE
            )
        },
    }
    if system:
        payload["system"] = system
    if json_mode:
        # Ollama will force the model to output valid JSON
        payload["format"] = "json"

    try:
        response = requests.post(
            _url("/api/generate"),
            json=payload,
            timeout=timeout or config.OLLAMA_TIMEOUT,
        )
    except requests.exceptions.ConnectionError as exc:
        raise OllamaNotRunningError(
            "Cannot connect to Ollama. Make sure 'ollama serve' is running."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise OllamaTimeoutError(
            "Ollama took too long to respond. Try a shorter prompt or a smaller model."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise OllamaError(f"Network error while calling Ollama: {exc}") from exc

    if response.status_code == 404:
        raise OllamaModelNotFoundError(
            f"Model '{config.OLLAMA_MODEL}' is not installed. "
            f"Run: ollama pull {config.OLLAMA_MODEL}"
        )
    if response.status_code >= 400:
        raise OllamaError(
            f"Ollama returned HTTP {response.status_code}: {response.text[:200]}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise OllamaInvalidResponseError(
            "Ollama returned a non-JSON envelope."
        ) from exc

    text = (data.get("response") or "").strip()
    if not text:
        raise OllamaInvalidResponseError("Ollama returned an empty response.")

    return text


def generate_json(
    prompt: str,
    system: Optional[str] = None,
    *,
    temperature: Optional[float] = None,
    timeout: Optional[int] = None,
) -> dict:
    """
    Ask Ollama for JSON and return a validated dict.

    Raises OllamaInvalidResponseError if the model still returns garbage.
    """
    raw = generate(
        prompt,
        system=system,
        json_mode=True,
        temperature=temperature if temperature is not None else 0.2,
        timeout=timeout,
    )

    candidate = _extract_json_block(raw)
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise OllamaInvalidResponseError(
            f"AI returned invalid JSON. Preview: {raw[:200]}"
        ) from exc

    if not isinstance(data, dict):
        raise OllamaInvalidResponseError("AI JSON response was not an object.")

    return data