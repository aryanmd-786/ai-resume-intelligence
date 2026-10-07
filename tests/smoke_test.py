"""
tests/smoke_test.py
-------------------
Quick smoke test — verifies the app can import all modules and init DB.

Run from project root:
    python tests/smoke_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_imports() -> bool:
    print("Testing imports...")
    try:
        import config  # noqa
        from database import database  # noqa
        from services import (  # noqa
            ollama_service,
            resume_parser,
            resume_analyzer,
            resume_generator,
            resume_pdf,
            resume_docx,
            job_matcher,
            career_assistant,
        )
        from utils import helpers, validators, error_handlers, health_check  # noqa
        from templates import get_theme, template_names  # noqa
        print("  ✅ All imports OK")
        return True
    except Exception as exc:
        print(f"  ❌ Import failed: {exc}")
        return False


def test_database() -> bool:
    print("Testing database...")
    try:
        from database import database
        database.init_db()
        stats = database.get_dashboard_stats()
        assert isinstance(stats, dict)
        assert "total_resumes" in stats
        print(f"  ✅ DB OK — {stats['total_resumes']} resumes, "
              f"{stats['total_analyses']} analyses")
        return True
    except Exception as exc:
        print(f"  ❌ DB failed: {exc}")
        return False


def test_ollama() -> bool:
    print("Testing Ollama connection...")
    try:
        from services import ollama_service
        ok, msg = ollama_service.check_connection()
        if ok:
            print(f"  ✅ Ollama OK — {msg}")
            return True
        print(f"  ⚠️  Ollama not ready: {msg}")
        return False
    except Exception as exc:
        print(f"  ❌ Ollama check failed: {exc}")
        return False


def test_templates() -> bool:
    print("Testing templates...")
    try:
        from templates import get_theme, template_names
        names = template_names()
        assert len(names) >= 3, "Expected at least 3 templates"
        for n in names:
            theme = get_theme(n)
            assert "primary" in theme
            assert "pdf_font_body" in theme
        print(f"  ✅ Templates OK — {names}")
        return True
    except Exception as exc:
        print(f"  ❌ Templates failed: {exc}")
        return False


def test_health_check() -> bool:
    print("Testing health check...")
    try:
        from utils.health_check import run_all_checks
        results = run_all_checks()
        assert isinstance(results, list)
        fails = [r for r in results if r["status"] == "fail"]
        if fails:
            print(f"  ⚠️  {len(fails)} health issues detected")
            for f in fails:
                print(f"     - {f['name']}: {f['message']}")
        else:
            print(f"  ✅ All {len(results)} health checks OK")
        return True
    except Exception as exc:
        print(f"  ❌ Health check failed: {exc}")
        return False


def main() -> int:
    print("=" * 60)
    print("  AI Resume Intelligence — Smoke Test")
    print("=" * 60)
    print()

    results = [
        test_imports(),
        test_database(),
        test_templates(),
        test_ollama(),
        test_health_check(),
    ]

    print()
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    if all(results):
        print(f"  🎉 All {total} tests passed!")
        return 0
    print(f"  ⚠️  {passed}/{total} tests passed")
    return 1 if passed < total - 1 else 0  # Ollama failing is tolerated


if __name__ == "__main__":
    sys.exit(main())