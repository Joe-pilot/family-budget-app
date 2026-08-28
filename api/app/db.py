import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Postgres by default — set DATABASE_URL to override (e.g. for local testing
# with SQLite: "sqlite:////tmp/budget.db"). Nothing else in the app needs to
# change if you swap the backend; all queries go through SQLAlchemy.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://budget:budget@postgres:5432/budget",
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    hide_parameters=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
