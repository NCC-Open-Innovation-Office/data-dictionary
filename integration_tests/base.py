"""Shared test helpers for the integration test suite."""

import os
import tempfile
import unittest

from api.app import create_app


class BaseApiTest(unittest.TestCase):
    """Base class for API tests that need a fresh SQLite-backed app.

    Subclasses get a ready-to-use ``self.client`` (Flask test client)
    backed by a throwaway SQLite file. AUTH_DISABLED defaults to true so
    the auth layer is bypassed, which is what feature tests want.
    """

    def setUp(self):
        self._saved_auth_disabled = os.environ.get('AUTH_DISABLED')
        os.environ['AUTH_DISABLED'] = 'true'

        self.sqlite_file = tempfile.NamedTemporaryFile(
            suffix='.db',
            prefix='dd-feature-test-',
            delete=False,
        )
        self.sqlite_file.close()

        self.app = create_app(
            database_url=f'sqlite:///{self.sqlite_file.name}',
            initialize=True,
            testing=True,
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.app.extensions['dd_db'].drop_all()
        self.app.extensions['dd_db'].dispose()
        if os.path.exists(self.sqlite_file.name):
            os.unlink(self.sqlite_file.name)

        if self._saved_auth_disabled is None:
            os.environ.pop('AUTH_DISABLED', None)
        else:
            os.environ['AUTH_DISABLED'] = self._saved_auth_disabled

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    def create_entry(self, **overrides):
        payload = {
            'term': overrides.pop('term', 'Test Term'),
            'definition': overrides.pop('definition', 'Test definition'),
        }
        payload.update(overrides)
        response = self.client.post('/api/entries', json=payload)
        self.assertEqual(
            response.status_code,
            201,
            f'Failed to create entry: {response.get_data(as_text=True)}',
        )
        return response.get_json()

    def create_tag(self, name='Test Tag', color='#FF0000'):
        response = self.client.post(
            '/api/tags',
            json={'name': name, 'color': color},
        )
        self.assertEqual(response.status_code, 201)
        return response.get_json()