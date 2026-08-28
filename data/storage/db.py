from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .models import Base

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = REPO_ROOT / "data" / "db" / "brawlbot.sqlite3"


def get_engine(db_path: Path = DEFAULT_DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    return engine


def get_session(engine=None) -> Session:
    return Session(engine or get_engine())
