from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from holdings_tracker_desktop.config import config

# SQLite requires check_same_thread=False in GUI applications.
engine = create_engine(
    config.database_url,
    echo=config.sql_echo,
    connect_args=(
        {"check_same_thread": False}
        if config.database_url.startswith("sqlite")
        else {}
    ),
)

if config.database_url.startswith("sqlite"):
    # SQLite ignores foreign keys unless enabled on every connection.
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()
