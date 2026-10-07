"""
database/database.py
--------------------
Local SQLite persistence for the AI Resume Intelligence Platform.

Design principles:
- No ORM — plain sqlite3 (stdlib). Simple, easy to understand.
- Every public function is safe to call even if the DB doesn't exist yet.
- Never raises on schema issues — always initializes first.

Tables:
    resumes            — every uploaded/analyzed resume
    analyses           — one row per AI analysis (each is a "version")
    job_matches        — one row per resume↔JD match
    generated_resumes  — one row per exported PDF/DOCX
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Optional

import config


# ---------------------------------------------------------------------------
# Connection & schema
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS resumes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    file_type     TEXT,
    resume_text   TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyses (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_id          INTEGER NOT NULL,
    overall_score      INTEGER NOT NULL DEFAULT 0,
    ats_score          INTEGER NOT NULL DEFAULT 0,
    content_score      INTEGER NOT NULL DEFAULT 0,
    skills_score       INTEGER NOT NULL DEFAULT 0,
    experience_score   INTEGER NOT NULL DEFAULT 0,
    projects_score     INTEGER NOT NULL DEFAULT 0,
    formatting_score   INTEGER NOT NULL DEFAULT 0,
    skills_count       INTEGER NOT NULL DEFAULT 0,
    analysis_json      TEXT,
    skills_json        TEXT,
    ats_json           TEXT,
    created_at         TEXT NOT NULL,
    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS job_matches (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_id      INTEGER,
    jd_snippet     TEXT,
    match_score    INTEGER NOT NULL DEFAULT 0,
    exp_relevance  INTEGER NOT NULL DEFAULT 0,
    edu_relevance  INTEGER NOT NULL DEFAULT 0,
    result_json    TEXT,
    created_at     TEXT NOT NULL,
    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS generated_resumes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name   TEXT,
    template    TEXT,
    file_path   TEXT,
    data_json   TEXT,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_analyses_resume ON analyses(resume_id);
CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at);
CREATE INDEX IF NOT EXISTS idx_matches_created ON job_matches(created_at);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.DATABASE_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def _get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db() -> None:
    """Create tables if they don't exist. Safe to call repeatedly."""
    try:
        with _get_conn() as conn:
            conn.executescript(SCHEMA)
    except Exception:
        # Never crash the app because of DB errors
        pass


# Ensure the schema exists as soon as this module is imported
init_db()


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------
def save_analysis(
    *,
    filename: str,
    file_type: str,
    resume_text: str,
    analysis: dict,
    skills: dict,
    ats: dict,
) -> Optional[int]:
    """
    Persist one analysis run. Returns the new analysis id, or None on error.
    Also creates a `resumes` row (each analysis becomes a version of that resume).
    """
    try:
        scores = analysis.get("scores", {}) or {}
        with _get_conn() as conn:
            # 1. Insert the resume row
            cur = conn.execute(
                "INSERT INTO resumes (name, file_type, resume_text, created_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    filename,
                    file_type,
                    (resume_text or "")[:50000],  # cap storage
                    _now(),
                ),
            )
            resume_id = cur.lastrowid

            # 2. Insert the analysis row
            cur2 = conn.execute(
                """
                INSERT INTO analyses (
                    resume_id, overall_score, ats_score, content_score,
                    skills_score, experience_score, projects_score, formatting_score,
                    skills_count, analysis_json, skills_json, ats_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    resume_id,
                    int(scores.get("overall", 0)),
                    int(scores.get("ats", 0)),
                    int(scores.get("content", 0)),
                    int(scores.get("skills", 0)),
                    int(scores.get("experience", 0)),
                    int(scores.get("projects", 0)),
                    int(scores.get("formatting", 0)),
                    int((skills or {}).get("total", 0)),
                    json.dumps(analysis or {}),
                    json.dumps(skills or {}),
                    json.dumps(ats or {}),
                    _now(),
                ),
            )
            return cur2.lastrowid
    except Exception:
        return None


def save_job_match(
    *,
    resume_id: Optional[int],
    jd_text: str,
    result: dict,
) -> Optional[int]:
    """Persist a resume↔JD match. Returns new id or None."""
    try:
        with _get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO job_matches (
                    resume_id, jd_snippet, match_score,
                    exp_relevance, edu_relevance, result_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    resume_id,
                    (jd_text or "")[:2000],
                    int(result.get("match_score", 0)),
                    int(result.get("experience_relevance", 0)),
                    int(result.get("education_relevance", 0)),
                    json.dumps(result or {}),
                    _now(),
                ),
            )
            return cur.lastrowid
    except Exception:
        return None


def save_generated_resume(
    *,
    full_name: str,
    template: str,
    file_path: str,
    data: dict,
) -> Optional[int]:
    """Persist a generated resume (PDF/DOCX). Returns new id or None."""
    try:
        with _get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO generated_resumes
                    (full_name, template, file_path, data_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    full_name or "",
                    template or "",
                    file_path or "",
                    json.dumps(data or {}),
                    _now(),
                ),
            )
            return cur.lastrowid
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------
def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def get_all_resumes(limit: int = 100) -> list[dict]:
    """Latest-first list of resumes, each with its most recent analysis."""
    try:
        with _get_conn() as conn:
            rows = conn.execute(
                """
                SELECT r.id, r.name, r.file_type, r.created_at,
                       a.id AS analysis_id,
                       a.overall_score, a.ats_score, a.skills_count
                FROM resumes r
                LEFT JOIN analyses a ON a.id = (
                    SELECT id FROM analyses
                    WHERE resume_id = r.id
                    ORDER BY id DESC LIMIT 1
                )
                ORDER BY r.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [_row_to_dict(r) for r in rows]
    except Exception:
        return []


def get_analyses_for_resume(resume_name: str) -> list[dict]:
    """
    All analyses for resumes with a given name — used for version comparison.
    Returns oldest → newest.
    """
    try:
        with _get_conn() as conn:
            rows = conn.execute(
                """
                SELECT a.*
                FROM analyses a
                JOIN resumes r ON r.id = a.resume_id
                WHERE r.name = ?
                ORDER BY a.id ASC
                """,
                (resume_name,),
            ).fetchall()
            return [_row_to_dict(r) for r in rows]
    except Exception:
        return []


def get_all_analyses(limit: int = 200) -> list[dict]:
    """Oldest → newest list of all analyses (for trend charts)."""
    try:
        with _get_conn() as conn:
            rows = conn.execute(
                """
                SELECT a.*, r.name AS resume_name
                FROM analyses a
                LEFT JOIN resumes r ON r.id = a.resume_id
                ORDER BY a.id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [_row_to_dict(r) for r in rows]
    except Exception:
        return []


def get_all_job_matches(limit: int = 200) -> list[dict]:
    """Oldest → newest list of all job matches (for trend charts)."""
    try:
        with _get_conn() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM job_matches
                ORDER BY id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [_row_to_dict(r) for r in rows]
    except Exception:
        return []


def get_dashboard_stats() -> dict:
    """Return high-level counts for the dashboard."""
    default = {
        "total_resumes": 0,
        "total_analyses": 0,
        "total_matches": 0,
        "avg_overall_score": 0,
        "latest_overall_score": 0,
        "latest_ats_score": 0,
        "latest_skills_count": 0,
        "latest_match_score": 0,
    }
    try:
        with _get_conn() as conn:
            total_resumes = conn.execute("SELECT COUNT(*) AS c FROM resumes").fetchone()["c"]
            total_analyses = conn.execute("SELECT COUNT(*) AS c FROM analyses").fetchone()["c"]
            total_matches = conn.execute("SELECT COUNT(*) AS c FROM job_matches").fetchone()["c"]

            avg_row = conn.execute(
                "SELECT AVG(overall_score) AS a FROM analyses"
            ).fetchone()
            avg_score = int(round(avg_row["a"])) if avg_row and avg_row["a"] is not None else 0

            latest_a = conn.execute(
                "SELECT overall_score, ats_score, skills_count FROM analyses ORDER BY id DESC LIMIT 1"
            ).fetchone()

            latest_m = conn.execute(
                "SELECT match_score FROM job_matches ORDER BY id DESC LIMIT 1"
            ).fetchone()

            return {
                "total_resumes": total_resumes,
                "total_analyses": total_analyses,
                "total_matches": total_matches,
                "avg_overall_score": avg_score,
                "latest_overall_score": latest_a["overall_score"] if latest_a else 0,
                "latest_ats_score": latest_a["ats_score"] if latest_a else 0,
                "latest_skills_count": latest_a["skills_count"] if latest_a else 0,
                "latest_match_score": latest_m["match_score"] if latest_m else 0,
            }
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Deleters
# ---------------------------------------------------------------------------
def delete_resume(resume_id: int) -> bool:
    try:
        with _get_conn() as conn:
            conn.execute("DELETE FROM analyses WHERE resume_id = ?", (resume_id,))
            conn.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))
        return True
    except Exception:
        return False


def clear_all() -> bool:
    try:
        with _get_conn() as conn:
            conn.executescript(
                "DELETE FROM analyses;"
                "DELETE FROM job_matches;"
                "DELETE FROM generated_resumes;"
                "DELETE FROM resumes;"
            )
        return True
    except Exception:
        return False