import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from .db import Base, engine, SessionLocal
from .seed import seed_catalog
from .routers import categories, budget, transactions, summary, agent

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
    _wait_for_db()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_catalog(db)
        log.info("Database ready and catalog seeded.")
    finally:
        db.close()
    yield


app = FastAPI(title="Family Budget API", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # trusted in-cluster / home-network use; tighten if exposed publicly
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categories.router)
app.include_router(budget.router)
app.include_router(transactions.router)
app.include_router(summary.router)
app.include_router(agent.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
