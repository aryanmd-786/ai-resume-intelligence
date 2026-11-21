# services/auth_service.py
import hashlib
import re
import secrets
from datetime import datetime

# 🔐 database.py ke context manager ko import kiya
from database.database import _get_conn

PASSWORD_MIN_LEN = 6

# ---------------- Hashing ----------------
def _hash_password(password: str, salt: str | None = None):
    if salt is None:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000
    ).hex()
    return pwd_hash, salt

def _verify_password(password: str, stored_hash: str, salt: str) -> bool:
    computed, _ = _hash_password(password, salt)
    return secrets.compare_digest(computed, stored_hash)

# ---------------- Validation ----------------
def _is_valid_email(email: str) -> bool:
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None

# ---------------- Signup ----------------
def signup(username: str, email: str, password: str, full_name: str = "") -> dict:
    username = username.strip().lower()
    email = email.strip().lower()
    full_name = full_name.strip()

    if len(username) < 3:
        return {"ok": False, "message": "Username kam se kam 3 characters ka hona chahiye."}
    if not re.match(r"^[a-z0-9_]+$", username):
        return {"ok": False, "message": "Username me sirf a-z, 0-9 aur _ allowed hai."}
    if not _is_valid_email(email):
        return {"ok": False, "message": "Valid email daaliye."}
    if len(password) < PASSWORD_MIN_LEN:
        return {"ok": False, "message": f"Password kam se kam {PASSWORD_MIN_LEN} characters ka hona chahiye."}

    try:
        with _get_conn() as conn:
            c = conn.cursor()
            # duplicate check
            row = c.execute(
                "SELECT id FROM users WHERE username = ? OR email = ?", (username, email)
            ).fetchone()
            if row:
                return {"ok": False, "message": "Username ya email pehle se registered hai."}

            pwd_hash, salt = _hash_password(password)
            c.execute(
                """INSERT INTO users (username, email, password_hash, salt, full_name, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (username, email, pwd_hash, salt, full_name, datetime.now().isoformat()),
            )
            return {"ok": True, "message": "Account ban gaya! Ab login karo."}
    except Exception as e:
        return {"ok": False, "message": f"Database error: {e}"}

# ---------------- Login ----------------
def login(username_or_email: str, password: str) -> dict:
    ident = username_or_email.strip().lower()
    if not ident or not password:
        return {"ok": False, "message": "Dono fields bharo."}

    try:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? OR email = ?", (ident, ident)
            ).fetchone()
            if not row:
                return {"ok": False, "message": "User nahi mila."}
            if not _verify_password(password, row["password_hash"], row["salt"]):
                return {"ok": False, "message": "Password galat hai."}
            return {
                "ok": True,
                "user_id": row["id"],
                "username": row["username"],
                "full_name": row["full_name"] or row["username"],
            }
    except Exception as e:
        return {"ok": False, "message": f"Database error: {e}"}