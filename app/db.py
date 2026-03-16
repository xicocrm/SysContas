from threading import Lock

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

_engine_lock = Lock()
_current_database_url = settings.database_url


def _build_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, echo=False)


engine = _build_engine(_current_database_url)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_current_database_url() -> str:
    return _current_database_url


def reconfigure_database(database_url: str) -> None:
    global engine, _current_database_url
    with _engine_lock:
        engine.dispose()
        engine = _build_engine(database_url)
        _current_database_url = database_url
        SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
