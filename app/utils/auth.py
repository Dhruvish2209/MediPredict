"""Password hashing, validation, login/register logic."""
import re
from datetime import datetime, timezone

import bcrypt

from app.utils import db
from app.utils.config import DOCTOR_INVITE_CODE

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match((email or "").strip()))


def password_issues(password: str) -> list:
    """Human-readable list of what is wrong with a password (empty list = OK)."""
    issues = []
    if len(password) < 8:
        issues.append("at least 8 characters")
    if not re.search(r"[A-Za-z]", password):
        issues.append("a letter")
    if not re.search(r"\d", password):
        issues.append("a number")
    return issues


def password_strength(password: str) -> tuple:
    """Returns (score 0-4, label)."""
    score = 0
    score += len(password) >= 8
    score += len(password) >= 12
    score += bool(re.search(r"[A-Z]", password) and re.search(r"[a-z]", password))
    score += bool(re.search(r"\d", password)) and bool(re.search(r"[^A-Za-z0-9]", password))
    return score, ["Too weak", "Weak", "Fair", "Good", "Strong"][score]


def register(name, email, password, role="patient", doctor_code="", age=None, sex=None):
    """Returns (user_id | None, error_message | None)."""
    name, email = (name or "").strip(), (email or "").strip().lower()
    if not (name and email and password):
        return None, "Please fill in all required fields."
    if not valid_email(email):
        return None, "Please enter a valid email address."
    issues = password_issues(password)
    if issues:
        return None, "Password needs " + ", ".join(issues) + "."
    if role == "doctor" and doctor_code.strip() != DOCTOR_INVITE_CODE:
        return None, "Invalid doctor invitation code."
    uid = db.create_user(name, email, hash_password(password), role, age, sex)
    if uid is None:
        return None, "That email is already registered."
    return uid, None


def login(email, password):
    """Returns (user_dict | None, error_message | None). Includes brute-force lockout."""
    email = (email or "").strip().lower()
    if not email or not password:
        return None, "Enter your email and password."
    locked = db.minutes_locked(email)
    if locked:
        return None, f"Too many failed attempts. Try again in about {locked} minute(s)."
    user = db.get_user_by_email(email)
    if user and verify_password(password, user["password_hash"]):
        db.record_login_attempt(email, True)
        db.update_user(user["user_id"], last_login=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        return user, None
    db.record_login_attempt(email, False)
    return None, "Invalid email or password."


def change_password(user_id, current, new):
    user = db.get_user(user_id)
    if not user or not verify_password(current, user["password_hash"]):
        return "Current password is incorrect."
    issues = password_issues(new)
    if issues:
        return "New password needs " + ", ".join(issues) + "."
    db.update_user(user_id, password_hash=hash_password(new))
    return None
