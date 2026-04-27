from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# F-077: dual-path engine. Default DATABASE_URL is PostgreSQL; the
# SQLite-only `check_same_thread` arg stays conditional so anyone
# pointing a script at the legacy tcf_oral.db file (kept on disk as
# historical reference) still works. `pool_pre_ping=True` adds a
# trivial health check before each checkout — catches stale
# connections after a Postgres restart, harmless on SQLite.
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
