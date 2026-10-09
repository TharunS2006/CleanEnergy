import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.bootstrap import bootstrap
from app.config import settings
from app.database import SessionLocal, init_db
from app.routers.admin import router as admin_router
from app.routers.api import router as api_router
from app.routers.auth import router as auth_router
from app.security import COOKIE_NAME, user_for_token
from app import jobs

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
for noisy in ("azure", "azure.identity", "azure.core.pipeline.policies.http_logging_policy", "apscheduler"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
log = logging.getLogger("cloudpulse")
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

init_db()
with SessionLocal() as _db:
    bootstrap(_db)
if settings.APP_SECRET_KEY_IS_RANDOM:
    log.warning("APP_SECRET_KEY is not set: stored Azure secrets won't be readable after a restart.")

jobs.mark_interrupted()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # First sync a few seconds after startup, then on the interval. All syncs
    # run in the background, so the server answers straight away.
    jobs.scheduler.add_job(jobs.sync_everything, "interval", minutes=settings.COLLECT_INTERVAL_MINUTES,
                           id="sync-all", next_run_time=datetime.now() + timedelta(seconds=3),
                           replace_existing=True)
    jobs.scheduler.start()
    yield
    if jobs.scheduler.running:
        jobs.scheduler.shutdown(wait=False)


app = FastAPI(title="CloudPulse", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(api_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'; frame-ancestors 'none'",
    )
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


def _signed_in(request: Request) -> bool:
    with SessionLocal() as db:
        return user_for_token(db, request.cookies.get(COOKIE_NAME)) is not None


@app.get("/", include_in_schema=False)
def dashboard(request: Request):
    if not _signed_in(request):
        return RedirectResponse("/login", status_code=303)
    return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/login", include_in_schema=False)
def login_page(request: Request):
    if _signed_in(request):
        return RedirectResponse("/", status_code=303)
    return FileResponse(STATIC_DIR / "login.html")
