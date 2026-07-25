import os
import tempfile
import time
import unittest
import uuid

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.engine import make_url

from api.app import create_app


DEFAULT_MSSQL_TEST_URL = (
    'mssql+pymssql://sa:DataDictionary!234@127.0.0.1:14333/'
    'data_dictionary_test'
)


def build_targets():
    sqlite_file = tempfile.NamedTemporaryFile(
        suffix='.db',
        prefix='data-dictionary-test-',
        delete=False,
    )
    sqlite_file.close()
    targets = [
        {
            'name': 'sqlite',
            'url': f'sqlite:///{sqlite_file.name}',
            'cleanup': sqlite_file.name,
        }
    ]

    if os.environ.get('RUN_MSSQL_TESTS', '').lower() == 'true':
        targets.append(
            {
                'name': 'mssql',
                'url': os.environ.get(
                    'MSSQL_TEST_URL',
                    DEFAULT_MSSQL_TEST_URL,
                ),
                'cleanup': None,
            }
        )

    return targets


def ensure_mssql_database(database_url):
    url = make_url(database_url)
    admin_url = url.set(database='master')
    engine = create_engine(
        admin_url.render_as_string(hide_password=False),
        future=True,
        pool_pre_ping=True,
        isolation_level='AUTOCOMMIT',
    )
    database_name = url.database
    safe_database_name = database_name.replace(']', ']]')
    try:
        with engine.connect() as connection:
            connection.execute(
                text(
                    'IF DB_ID(:database_name) IS NULL '
                    f'CREATE DATABASE [{safe_database_name}]'
                ),
                {'database_name': database_name},
            )
    finally:
        engine.dispose()


def wait_for_mssql_server(database_url, attempts=30, delay_seconds=2):
    url = make_url(database_url)
    admin_url = url.set(database='master')

    last_error = None
    for _ in range(attempts):
        engine = create_engine(
            admin_url.render_as_string(hide_password=False),
            future=True,
            pool_pre_ping=True,
        )
        try:
            with engine.connect() as connection:
                connection.execute(text('SELECT 1'))
                return
        except Exception as exc:
            last_error = exc
            time.sleep(delay_seconds)
        finally:
            engine.dispose()

    raise RuntimeError(
        'Timed out waiting for MSSQL test server'
    ) from last_error


def drop_mssql_database(database_url):
    url = make_url(database_url)
    admin_url = url.set(database='master')
    engine = create_engine(
        admin_url.render_as_string(hide_password=False),
        future=True,
        pool_pre_ping=True,
        isolation_level='AUTOCOMMIT',
    )
    database_name = url.database
    safe_database_name = database_name.replace(']', ']]')
    try:
        with engine.connect() as connection:
            connection.execute(
                text(
                    'IF DB_ID(:database_name) IS NOT NULL '
                    f'BEGIN '
                    f'ALTER DATABASE [{safe_database_name}] '
                    'SET SINGLE_USER WITH ROLLBACK IMMEDIATE; '
                    f'DROP DATABASE [{safe_database_name}]; '
                    'END'
                ),
                {'database_name': database_name},
            )
    finally:
        engine.dispose()


class ApiIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.targets = build_targets()

    def tearDown(self):
        for target in self.targets:
            cleanup_path = target.get('cleanup')
            if cleanup_path and os.path.exists(cleanup_path):
                os.unlink(cleanup_path)

    def test_entry_lifecycle_and_backup(self):
        for target in self.targets:
            with self.subTest(database=target['name']):
                self.run_lifecycle_case(target)

    def test_restore_round_trip(self):
        for target in self.targets:
            with self.subTest(database=target['name']):
                self.run_restore_case(target)

    def run_lifecycle_case(self, target):
        app = self.create_test_app(target)
        try:
            with app.test_client() as client:
                create_response = client.post(
                    '/api/entries',
                    json={
                        'term': f"Lifecycle {uuid.uuid4().hex[:8]}",
                        'definition': 'Initial definition',
                        'owner': 'Quality',
                    },
                )
                self.assertEqual(create_response.status_code, 201)

                list_response = client.get('/api/entries')
                self.assertEqual(list_response.status_code, 200)
                entries = list_response.get_json()
                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0]['owner'], 'Quality')

                backup_response = client.get('/api/backup')
                self.assertEqual(backup_response.status_code, 200)
                backup = backup_response.get_json()
                self.assertEqual(len(backup['entries']), 1)
                self.assertEqual(
                    backup['entries'][0]['term'],
                    entries[0]['term'],
                )
        finally:
            self.cleanup_app(app, target)

    def run_restore_case(self, target):
        app = self.create_test_app(target)
        try:
            with app.test_client() as client:
                create_tag_response = client.post(
                    '/api/tags',
                    json={'name': 'Report A', 'color': '#112233'},
                )
                self.assertEqual(create_tag_response.status_code, 201)
                tag_id = create_tag_response.get_json()['id']

                create_entry_response = client.post(
                    '/api/entries',
                    json={
                        'term': f"Restore {uuid.uuid4().hex[:8]}",
                        'definition': 'Restore definition',
                    },
                )
                self.assertEqual(create_entry_response.status_code, 201)
                entry_id = create_entry_response.get_json()['id']

                add_tag_response = client.post(
                    f'/api/entries/{entry_id}/tags',
                    json={'tag_id': tag_id},
                )
                self.assertEqual(add_tag_response.status_code, 200)

                definition_response = client.post(
                    f'/api/entries/{entry_id}/definitions',
                    json={
                        'tag_id': tag_id,
                        'definition': 'Report specific definition',
                    },
                )
                self.assertEqual(definition_response.status_code, 201)

                backup_response = client.get('/api/backup')
                self.assertEqual(backup_response.status_code, 200)
                backup = backup_response.get_json()

                restore_response = client.post('/api/restore', json=backup)
                self.assertEqual(restore_response.status_code, 200)

                reloaded_entries = client.get('/api/entries').get_json()
                self.assertEqual(len(reloaded_entries), 1)
                self.assertEqual(len(reloaded_entries[0]['tags']), 1)
                self.assertEqual(
                    len(reloaded_entries[0]['report_definitions']),
                    1,
                )
        finally:
            self.cleanup_app(app, target)

    def create_test_app(self, target):
        database_url = target['url']
        if target['name'] == 'mssql':
            wait_for_mssql_server(database_url)
            ensure_mssql_database(database_url)

        app = create_app(
            database_url=database_url,
            initialize=True,
            testing=True,
        )
        return app

    def cleanup_app(self, app, target):
        database = app.extensions['dd_db']
        database.drop_all()
        database.dispose()
        if target['name'] == 'mssql':
            drop_mssql_database(target['url'])


if __name__ == '__main__':
    unittest.main()