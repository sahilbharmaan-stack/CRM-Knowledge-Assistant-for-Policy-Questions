"""Create schema, optionally seed classroom demo users, and index policy files."""
from backend import auth, config, db
from backend.indexer import index_policies


DEMO_ACCOUNTS = (
    ("counsellor1", "counsellor"),
    ("reviewer1", "reviewer"),
)


def bootstrap(conn) -> None:
    db.init_schema(conn)
    db.migrate(conn)
    # Provision one initial administrator automatically. Override these values in .env
    # before first launch in any real deployment, then rotate the password after login.
    admin_username = config.get("ADMIN_USERNAME", "admin")
    admin_password = config.get("ADMIN_PASSWORD", "Admin@CRM2026!")
    admin_name = config.get("ADMIN_DISPLAY_NAME", "CRM Administrator")
    admin = db.get_user_by_username(conn, admin_username)
    if not admin:
        from backend.accounts import password_problem
        problem = password_problem(admin_password, admin_username)
        if problem:
            raise RuntimeError(f"Invalid ADMIN_PASSWORD: {problem}")
        db.create_user(conn, admin_username, auth.hash_password(admin_password),
                       "administrator", admin_name)
        db.audit(conn, "system", "initial_admin_created", "users", detail=admin_username)
    elif config.get("ADMIN_PASSWORD_RESET", "0") == "1":
        from backend.accounts import password_problem
        problem = password_problem(admin_password, admin_username)
        if problem:
            raise RuntimeError(f"Invalid ADMIN_PASSWORD: {problem}")
        db.set_password(conn, admin["id"], auth.hash_password(admin_password))
        db.update_user(conn, admin["id"], role="administrator", active=1, display_name=admin_name)
        db.audit(conn, "system", "initial_admin_reset", "users", admin["id"], detail=admin_username)
    if config.get("SEED_DEMO_USERS", "0") == "1":
        password = config.get("DEMO_PASSWORD")
        if not password:
            raise RuntimeError("DEMO_PASSWORD must be set when SEED_DEMO_USERS=1")
        for username, role in DEMO_ACCOUNTS:
            if not db.get_user_by_username(conn, username):
                db.create_user(conn, username, auth.hash_password(password), role)
    if not conn.execute("SELECT 1 FROM policy_documents LIMIT 1").fetchone():
        n = index_policies(conn, config.POLICY_DIR)
        db.audit(conn, "system", "policies_indexed", detail=f"{n} chunks")
    if config.get("SEED_DEMO_DATA", "0") == "1":
        from backend.demo_seed import seed_demo_activity
        seed_demo_activity(conn)


if __name__ == "__main__":
    c = db.connect()
    bootstrap(c)
    print("Database ready at", db.db_path())
    print("Users:", db.count_users(c))
