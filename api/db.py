from contextlib import contextmanager
import os

from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

try:
    from api.models import Base
except ImportError:
    from models import Base


def resolve_database_url(database_url=None):
    if database_url:
        return database_url

    env_database_url = os.environ.get('DATABASE_URL')
    if env_database_url:
        return env_database_url

    database = os.environ.get('DATABASE', 'dictionary.db')
    if '://' in database:
        return database

    database_path = os.path.abspath(database)
    return f'sqlite:///{database_path}'


class Database:
    def __init__(self, database_url=None, testing=False):
        self.database_url = resolve_database_url(database_url)
        engine_options = {
            'future': True,
            'pool_pre_ping': True,
        }
        if self.database_url.startswith('sqlite:///'):
            engine_options['connect_args'] = {'check_same_thread': False}
            if testing:
                engine_options['poolclass'] = NullPool

        self.engine = create_engine(self.database_url, **engine_options)
        self.SessionLocal = scoped_session(
            sessionmaker(
                bind=self.engine,
                autoflush=False,
                expire_on_commit=False,
            )
        )

        @event.listens_for(self.engine, 'connect')
        def _configure_sqlite(dbapi_connection, connection_record):
            del connection_record
            if self.engine.dialect.name == 'sqlite':
                cursor = dbapi_connection.cursor()
                cursor.execute('PRAGMA foreign_keys=ON')
                cursor.close()

    @contextmanager
    def session_scope(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def ensure_legacy_columns(self):
        inspector = inspect(self.engine)
        if 'entries' not in inspector.get_table_names():
            return

        columns = {column['name'] for column in inspector.get_columns('entries')}
        additions = []
        if 'owner' not in columns:
            additions.append(('owner', 'TEXT NULL'))
        if 'stewards' not in columns:
            additions.append(('stewards', 'TEXT NULL'))
        if 'classification' not in columns:
            additions.append(
                ('classification', "TEXT NOT NULL DEFAULT 'public'"),
            )
        if 'ddId' not in columns:
            additions.append(('ddId', 'TEXT NULL'))

        if not additions:
            return

        with self.engine.begin() as connection:
            for column_name, column_type in additions:
                statement = (
                    'ALTER TABLE entries '
                    f'ADD COLUMN {column_name} {column_type}'
                )
                connection.execute(text(statement))

    def init_db(self):
        Base.metadata.create_all(bind=self.engine)
        self.ensure_legacy_columns()
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE entries "
                    "SET classification = 'internal' "
                    "WHERE classification = 'private'"
                )
            )

    def drop_all(self):
        Base.metadata.drop_all(bind=self.engine)

    def remove(self):
        self.SessionLocal.remove()

    def dispose(self):
        self.remove()
        self.engine.dispose()
