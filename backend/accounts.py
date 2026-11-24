"""Account rules: password policy, roles, and the last-administrator guard."""
from backend import db

ROLES = ("administrator", "policy_manager", "counsellor", "reviewer")
ANSWER_REVIEWERS = ("administrator", "policy_manager", "reviewer")
POLICY_EDITORS = ("administrator", "policy_manager", "reviewer")
BLOCKED_PASSWORDS = {"demo-pass-123", "password", "password123", "change-me", "admin", "administrator"}


def password_problem(password: str, username: str) -> str | None:
    """Return an error message, or None when the password is acceptable."""
    if len(password) < 10:
        return "Password must be at least 10 characters."
    if password.lower() == username.lower():
        return "Password must not match the username."
    if password.lower() in BLOCKED_PASSWORDS:
        return "Choose a password that is not a shared default."
    return None


def assert_keeps_an_admin(conn, target_id: int, next_role: str | None = None,
                          next_active: bool | None = None) -> None:
    """Refuse a change that would leave the system with no active administrator."""
    target = db.get_user(conn, target_id)
    if not target or target["role"] != "administrator":
        return
    stays_admin = next_role in (None, "administrator")
    stays_active = True if next_active is None else bool(next_active)
    if stays_admin and stays_active:
        return
    others = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE role='administrator' AND active=1 AND id!=?",
        (target_id,),
    ).fetchone()["c"]
    if others < 1:
        raise ValueError("The last active administrator cannot be deactivated or demoted.")
