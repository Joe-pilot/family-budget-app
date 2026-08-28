import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from .db import Base, engine, SessionLocal
from .seed import seed_catalog
from .routers import categories, budget, transactions, summary, agent
from .auth import require_api_key, validate_auth_configuration

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("budget-api")


def _wait_for_db(max_attempts: int = 30, delay_seconds: float = 2.0):
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect():
                return
        except OperationalError as e:
            log.warning("Database not ready (attempt %d/%d): %s", attempt, max_attempts, e)
            time.sleep(delay_seconds)
    raise RuntimeError("Database never became available")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_auth_configuration()
    _wait_for_db()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_catalog(db)
        log.info("Database ready and catalog seeded.")
    finally:
        db.close()
    yield


app = FastAPI(title="Family Budget API", version="1.1", lifespan=lifespan)

allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)

protected = [Depends(require_api_key)]
app.include_router(categories.router, dependencies=protected)
app.include_router(budget.router, dependencies=protected)
app.include_router(transactions.router, dependencies=protected)
app.include_router(summary.router, dependencies=protected)
app.include_router(agent.router, dependencies=protected)


@app.middleware("http")
async def security_controls(request: Request, call_next):
    max_body_bytes = int(os.environ.get("MAX_REQUEST_BODY_BYTES", "16384"))
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > max_body_bytes:
                return JSONResponse(status_code=413, content={"detail": "Request body too large"})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})

    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.get("/api/health")
def health():
    return {"status": "ok"}
