"""Local SQLite persistence layer."""

from database.database import (
    init_db,
    save_analysis,
    save_job_match,
    save_generated_resume,
    get_all_resumes,
    get_analyses_for_resume,
    get_all_analyses,
    get_all_job_matches,
    get_dashboard_stats,
    delete_resume,
    clear_all,
)

__all__ = [
    "init_db",
    "save_analysis",
    "save_job_match",
    "save_generated_resume",
    "get_all_resumes",
    "get_analyses_for_resume",
    "get_all_analyses",
    "get_all_job_matches",
    "get_dashboard_stats",
    "delete_resume",
    "clear_all",
]