"""
utils/validators.py
-------------------
File upload validation (type, size, emptiness).
"""

from __future__ import annotations

from pathlib import Path

import config


def validate_upload(uploaded_file) -> tuple[bool, str]:
    """
    Validate a Streamlit UploadedFile.

    Returns (ok: bool, message: str).
    Never raises.
    """
    if uploaded_file is None:
        return False, "No file uploaded."

    name = getattr(uploaded_file, "name", "") or ""
    if not name:
        return False, "Uploaded file has no name."

    ext = Path(name).suffix.lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(config.ALLOWED_EXTENSIONS))
        return False, f"Unsupported file type '{ext}'. Allowed: {allowed}"

    size = getattr(uploaded_file, "size", 0) or 0
    if size == 0:
        return False, "Uploaded file is empty (0 bytes)."
    if size > config.MAX_UPLOAD_SIZE_BYTES:
        mb = size / 1024 / 1024
        return False, (
            f"File too large ({mb:.1f} MB). "
            f"Maximum allowed: {config.MAX_UPLOAD_SIZE_MB} MB."
        )

    return True, "OK"