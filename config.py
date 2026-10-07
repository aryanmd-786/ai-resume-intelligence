"""
config.py
---------
Central configuration for the AI Resume Intelligence Platform.
Change values here instead of hardcoding them across the project.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = BASE_DIR / "data"
OUTPUTS_DIR: Path = BASE_DIR / "outputs"
ASSETS_DIR: Path = BASE_DIR / "assets"

DATA_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Ollama configuration
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "180"))  # seconds
OLLAMA_TEMPERATURE: float = 0.3  # lower = more deterministic

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_PATH: Path = DATA_DIR / "resume_ai.db"

# ---------------------------------------------------------------------------
# File upload limits
# ---------------------------------------------------------------------------
MAX_UPLOAD_SIZE_MB: int = 10
MAX_UPLOAD_SIZE_BYTES: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS: set[str] = {".pdf", ".docx"}

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------
APP_NAME: str = "AI Resume Intelligence"
APP_TAGLINE: str = "Analyze • Improve • Build • Match"
APP_VERSION: str = "1.0.0"

# ---------------------------------------------------------------------------
# Runtime model override (used by the Settings page)
# ---------------------------------------------------------------------------
def set_model(name: str) -> None:
    """Allow the user to change the active Ollama model at runtime."""
    global OLLAMA_MODEL
    cleaned = (name or "").strip()
    if cleaned:
        OLLAMA_MODEL = cleaned