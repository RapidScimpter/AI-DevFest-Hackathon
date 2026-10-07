from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import ROOT, settings

_sqlite = settings.database_url.startswith('sqlite')
if _sqlite:
    (ROOT / 'data').mkdir(exist_ok=True)
engine = create_engine(settings.database_url, connect_args={'check_same_thread': False, 'timeout': 15} if _sqlite else {}, pool_pre_ping=True)
if _sqlite:
    @event.listens_for(engine, 'connect')
    def _pragmas(conn, _):
        conn.execute('PRAGMA journal_mode=WAL'); conn.execute('PRAGMA foreign_keys=ON')
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401
    Base.metadata.create_all(engine)
