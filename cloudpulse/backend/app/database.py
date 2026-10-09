import logging
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

log = logging.getLogger("cloudpulse")

url = settings.DATABASE_URL
connect_args = {}
if url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    db_path = url.split("sqlite:///", 1)[-1]
    if db_path and db_path != ":memory:":
        Path(db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Tables that only hold data CloudPulse can fetch again.
CACHE_TABLES = ("cost_snapshots", "leaked_resources", "collection_runs", "settings")
SCHEMA_VERSION = "5"


def init_db():
    from app import models  # noqa: F401  (registers the tables)

    insp = inspect(engine)
    # Databases from before workspaces existed: their cached rows have no
    # owner, so drop and refetch them rather than guess.
    if insp.has_table("cost_snapshots"):
        cols = {c["name"] for c in insp.get_columns("cost_snapshots")}
        if "workspace_id" not in cols:
            log.warning("Old database layout found; clearing cached cloud data.")
            with engine.begin() as conn:
                for t in CACHE_TABLES:
                    if insp.has_table(t):
                        conn.exec_driver_sql(f"DROP TABLE {t}")
    # v4 -> v5: collection runs gained columns and idle resources became findings.
    insp = inspect(engine)
    if insp.has_table("collection_runs"):
        cols = {c["name"] for c in insp.get_columns("collection_runs")}
        if "step" not in cols:
            log.warning("Upgrading database to v5; cached cloud data will be fetched again.")
            with engine.begin() as conn:
                for t in ("cost_snapshots", "leaked_resources", "collection_runs"):
                    if insp.has_table(t):
                        conn.exec_driver_sql(f"DROP TABLE {t}")
    if insp.has_table("users"):
        cols = {c["name"] for c in insp.get_columns("users")}
        if "is_placeholder" not in cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN is_placeholder BOOLEAN DEFAULT FALSE")
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
