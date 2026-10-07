"""
utils/health_check.py
---------------------
System health diagnostics for the Settings page.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import config
from database import database
from services import ollama_service


def run_all_checks() -> list[dict]:
    """
    Return a list of dicts:
    {
      "name": str,
      "status": "ok" | "warn" | "fail",
      "message": str,
      "fix": str (optional)
    }
    """
    results: list[dict] = []

    # --- Ollama connection ---
    ok, msg = ollama_service.check_connection()
    results.append({
        "name": "Ollama Connection",
        "status": "ok" if ok else "fail",
        "message": msg,
        "fix": "" if ok else "Run: ollama serve",
    })

    # --- Ollama model installed ---
    if ok:
        models = ollama_service.list_models()
        base = config.OLLAMA_MODEL.split(":")[0]
        found = any(m == config.OLLAMA_MODEL or m.split(":")[0] == base for m in models)
        results.append({
            "name": "AI Model Available",
            "status": "ok" if found else "fail",
            "message": (
                f"Model '{config.OLLAMA_MODEL}' is installed."
                if found else f"Model '{config.OLLAMA_MODEL}' not found."
            ),
            "fix": "" if found else f"Run: ollama pull {config.OLLAMA_MODEL}",
        })
    else:
        results.append({
            "name": "AI Model Available",
            "status": "warn",
            "message": "Skipped — Ollama is not running.",
            "fix": "",
        })

    # --- Data folder ---
    try:
        config.DATA_DIR.mkdir(exist_ok=True)
        results.append({
            "name": "Data Folder",
            "status": "ok",
            "message": f"Writable at {config.DATA_DIR}",
            "fix": "",
        })
    except Exception as exc:
        results.append({
            "name": "Data Folder",
            "status": "fail",
            "message": f"Cannot write to data folder: {exc}",
            "fix": "Check folder permissions.",
        })

    # --- Database ---
    try:
        database.init_db()
        stats = database.get_dashboard_stats()
        results.append({
            "name": "SQLite Database",
            "status": "ok",
            "message": (
                f"OK — {stats.get('total_resumes', 0)} resumes, "
                f"{stats.get('total_analyses', 0)} analyses, "
                f"{stats.get('total_matches', 0)} matches."
            ),
            "fix": "",
        })
    except Exception as exc:
        results.append({
            "name": "SQLite Database",
            "status": "fail",
            "message": f"Database error: {exc}",
            "fix": "Delete data/resume_ai.db and restart the app.",
        })

    # --- Outputs folder ---
    try:
        config.OUTPUTS_DIR.mkdir(exist_ok=True)
        results.append({
            "name": "Outputs Folder",
            "status": "ok",
            "message": f"Writable at {config.OUTPUTS_DIR}",
            "fix": "",
        })
    except Exception as exc:
        results.append({
            "name": "Outputs Folder",
            "status": "fail",
            "message": f"Cannot write to outputs folder: {exc}",
            "fix": "Check folder permissions.",
        })

    # --- Disk space ---
    try:
        usage = shutil.disk_usage(str(config.BASE_DIR))
        free_mb = usage.free / (1024 * 1024)
        if free_mb < 200:
            results.append({
                "name": "Disk Space",
                "status": "warn",
                "message": f"Only {free_mb:.0f} MB free.",
                "fix": "Free up disk space.",
            })
        else:
            results.append({
                "name": "Disk Space",
                "status": "ok",
                "message": f"{free_mb:.0f} MB free.",
                "fix": "",
            })
    except Exception:
        results.append({
            "name": "Disk Space",
            "status": "warn",
            "message": "Could not check disk usage.",
            "fix": "",
        })

    # --- CSS file present ---
    css = config.ASSETS_DIR / "style.css"
    results.append({
        "name": "Stylesheet",
        "status": "ok" if css.exists() else "warn",
        "message": f"Found at {css}" if css.exists() else "assets/style.css missing.",
        "fix": "" if css.exists() else "Create assets/style.css.",
    })

    return results