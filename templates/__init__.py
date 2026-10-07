"""Resume template themes."""

from templates import modern, minimal, professional

TEMPLATES = {
    "Modern": modern.THEME,
    "Minimal": minimal.THEME,
    "Professional": professional.THEME,
}


def get_theme(name: str) -> dict:
    return TEMPLATES.get(name, modern.THEME)


def template_names() -> list[str]:
    return list(TEMPLATES.keys())