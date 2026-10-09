"""Command-line account management.

    python -m app.manage list
    python -m app.manage create-admin you@example.com
    python -m app.manage create-user person@company.com --workspace my-cloud --role owner
    python -m app.manage reset-password person@company.com
    python -m app.manage workspaces
    python -m app.manage check-azure     # test the Azure settings in .env
"""
import argparse
import sys

from app.database import SessionLocal, init_db
from app.models import Membership, User, Workspace
from app.services.connections import azure_env_problems  # noqa: E402
from app.security import end_all_sessions, generate_password, hash_password


def check_azure():
    from app.config import settings
    from app.services import azure_collector
    from app.services.connections import AZURE_AUTH_LABELS, AzureTarget, _azure_factory, env_azure_auth

    problems = azure_env_problems()
    if problems:
        sys.exit("Azure is not configured:\n  - " + "\n  - ".join(problems))
    auth = env_azure_auth()
    print(f"Signing in with: {AZURE_AUTH_LABELS[auth]}")
    target = AzureTarget(settings.AZURE_SUBSCRIPTION_ID, auth,
                         _azure_factory(auth, settings.AZURE_TENANT_ID, settings.AZURE_CLIENT_ID,
                                        settings.AZURE_CLIENT_SECRET))
    ok, info = azure_collector.check_connection(target)
    print(("Connected: " if ok else "FAILED: ") + info)
    sys.exit(0 if ok else 1)


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m app.manage")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list users")
    sub.add_parser("workspaces", help="list workspaces")
    sub.add_parser("check-azure", help="test the Azure sign-in configured in .env")
    a = sub.add_parser("create-admin")
    a.add_argument("email")
    u = sub.add_parser("create-user")
    u.add_argument("email")
    u.add_argument("--workspace", required=True, help="workspace slug")
    u.add_argument("--role", choices=["owner", "viewer"], default="viewer")
    r = sub.add_parser("reset-password")
    r.add_argument("email")
    args = p.parse_args(argv)

    if args.cmd == "check-azure":
        return check_azure()

    init_db()
    db = SessionLocal()
    try:
        if args.cmd == "list":
            for x in db.query(User).order_by(User.email):
                kind = "admin" if x.is_admin else "demo" if x.is_demo else "customer"
                print(f"{x.email:40} {kind:9} {'disabled' if x.disabled else ''}")
        elif args.cmd == "workspaces":
            for w in db.query(Workspace).order_by(Workspace.name):
                print(f"{w.slug:30} {w.kind:9} {w.name}")
        elif args.cmd in ("create-admin", "create-user"):
            email = args.email.strip().lower()
            if db.query(User).filter_by(email=email).first():
                sys.exit(f"{email} already exists.")
            ws = None
            if args.cmd == "create-user":
                ws = db.query(Workspace).filter_by(slug=args.workspace).first()
                if not ws or ws.kind == "demo":
                    sys.exit(f"No customer workspace called '{args.workspace}'. Try: python -m app.manage workspaces")
            pw = generate_password()
            user = User(email=email, name=email.split("@")[0], password_hash=hash_password(pw),
                        is_admin=args.cmd == "create-admin", must_change_password=True)
            db.add(user)
            db.commit()
            if ws:
                db.add(Membership(user_id=user.id, workspace_id=ws.id, role=args.role))
                db.commit()
            print(f"Created {email}\nTemporary password: {pw}\n(They'll be asked to change it at first sign-in.)")
        elif args.cmd == "reset-password":
            user = db.query(User).filter_by(email=args.email.strip().lower()).first()
            if not user or user.is_demo:
                sys.exit("No such user.")
            pw = generate_password()
            user.password_hash = hash_password(pw)
            user.must_change_password = True
            db.commit()
            end_all_sessions(db, user.id)
            print(f"Temporary password for {user.email}: {pw}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
