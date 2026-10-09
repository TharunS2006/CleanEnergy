"""First-run setup: the admin account, the demo workspace, and a customer
workspace for the cloud account configured in the server's settings."""
import json
import logging
import re
import secrets

from sqlalchemy.orm import Session

from app.config import settings
from app.models import CloudConnection, Membership, User, Workspace
from app.security import generate_password, hash_password
from app.services.connections import env_aws_configured, env_azure_auth

log = logging.getLogger("cloudpulse")


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:40] or "workspace"


def unique_slug(db: Session, name: str) -> str:
    base = slugify(name)
    slug, n = base, 2
    while db.query(Workspace).filter_by(slug=slug).first():
        slug, n = f"{base}-{n}", n + 1
    return slug


def ensure_admin(db: Session):
    if db.query(User).filter_by(is_admin=True, is_placeholder=False).first():
        return
    password = settings.ADMIN_PASSWORD
    generated = not password
    if generated:
        password = generate_password()
    db.add(User(
        email=settings.ADMIN_EMAIL, name="Administrator", password_hash=hash_password(password),
        is_admin=True, must_change_password=generated,
    ))
    db.commit()
    if generated:
        bar = "=" * 64
        log.warning("\n%s\n  CloudPulse admin account created\n  Email:    %s\n  Password: %s\n"
                    "  You'll be asked to change it after signing in.\n%s",
                    bar, settings.ADMIN_EMAIL, password, bar)
    else:
        log.info("Admin account created for %s", settings.ADMIN_EMAIL)


def ensure_demo(db: Session):
    if not settings.DEMO_ENABLED:
        return
    ws = db.query(Workspace).filter_by(kind="demo").first()
    if ws is None:
        ws = Workspace(slug="demo", name="Demo company", kind="demo")
        db.add(ws)
        db.commit()
    user = db.query(User).filter_by(is_demo=True, is_placeholder=False).first()
    if user is None:
        user = User(email=settings.DEMO_EMAIL, name="Demo visitor",
                    password_hash=hash_password(secrets.token_urlsafe(24)), is_demo=True)
        db.add(user)
        db.commit()
    if not db.query(Membership).filter_by(user_id=user.id, workspace_id=ws.id).first():
        db.add(Membership(user_id=user.id, workspace_id=ws.id, role="viewer"))
        db.commit()


def ensure_env_workspace(db: Session):
    """If the server is configured with cloud credentials, make sure a
    customer workspace exists that uses them."""
    wants_azure = env_azure_auth() is not None
    wants_aws = env_aws_configured()
    existing = db.query(CloudConnection).filter_by(auth="env").all()
    if not (wants_azure or wants_aws) and not existing:
        return

    ws = None
    if existing:
        ws = db.get(Workspace, existing[0].workspace_id)
    if ws is None:
        ws = Workspace(slug=unique_slug(db, settings.WORKSPACE_NAME), name=settings.WORKSPACE_NAME)
        db.add(ws)
        db.commit()
        log.info("Created workspace %s from server settings", ws.slug)

    def upsert(provider: str, wanted: bool, label: str):
        conn = db.query(CloudConnection).filter_by(workspace_id=ws.id, provider=provider, auth="env").first()
        if wanted and conn is None:
            db.add(CloudConnection(workspace_id=ws.id, provider=provider, auth="env",
                                   label=label, config=json.dumps({})))
        elif conn is not None:
            conn.enabled = wanted
    upsert("azure", wants_azure, "Azure subscription")
    upsert("aws", wants_aws, "AWS account")
    db.commit()


def bootstrap(db: Session):
    ensure_admin(db)
    ensure_demo(db)
    ensure_env_workspace(db)
    # Fill the demo workspace now so it's ready on first sign-in.
    from app.models import Finding
    from app.services.collection_orchestrator import sync_workspace

    demo = db.query(Workspace).filter_by(kind="demo").first()
    if demo and not db.query(Finding).filter_by(workspace_id=demo.id).first():
        sync_workspace(db, demo)
