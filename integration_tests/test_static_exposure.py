"""Tests that the web server never serves files outside the asset list.

The application used to hand Flask the project root as its static
folder, which meant any URL mapped straight onto a file on disk --
including the SQLite database, the Python sources and the .git
directory. These tests lock that down.
"""

import os
import tempfile
import unittest

from api.app import create_app


# Paths that must never be downloadable. Each entry is (path, marker)
# where the marker is a byte sequence that would appear in the file.
FORBIDDEN_PATHS = [
    ('/data/dictionary.db', b'SQLite format 3'),
    ('/api/dictionary.db', b'SQLite format 3'),
    ('/api/app.py', b'def create_app'),
    ('/api/auth.py', b'current_email'),
    ('/api/models.py', b'declarative_base'),
    ('/api/users.py', b'provision_or_merge_user'),
    ('/api/db.py', b'create_engine'),
    ('/api/models.py', b'class User'),
    ('/import_pdf_data.py', b'import'),
    ('/Dockerfile', b'FROM python'),
    ('/docker-compose.yml', b'services:'),
    ('/docker-compose.prod.yml', b'services:'),
    ('/api/requirements.txt', b'Flask'),
]

# Dotfile paths that must not be served or turned into an SPA page.
DOTFILE_PATHS = [
    '/.git/config',
    '/.git/HEAD',
    '/.env',
    '/.gitignore',
]


class StaticExposureTest(unittest.TestCase):
    def setUp(self):
        self._saved_auth_disabled = os.environ.get('AUTH_DISABLED')
        os.environ['AUTH_DISABLED'] = 'true'
        self.sqlite_file = tempfile.NamedTemporaryFile(
            suffix='.db',
            prefix='dd-static-test-',
            delete=False,
        )
        self.sqlite_file.close()
        self.app = create_app(
            database_url=f'sqlite:///{self.sqlite_file.name}',
            initialize=True,
            testing=True,
        )
        self.app.config['TESTING'] = True
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

    def test_database_is_not_downloadable(self):
        """The live database must not be reachable over HTTP."""
        for path in ('/data/dictionary.db', '/api/dictionary.db'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertNotEqual(response.status_code, 200)
                self.assertNotIn(
                    b'SQLite format 3',
                    response.get_data(),
                )

    def test_source_files_are_not_downloadable(self):
        """Python sources must not be reachable over HTTP."""
        for path, marker in FORBIDDEN_PATHS:
            with self.subTest(path=path):
                response = self.client.get(path)
                if response.status_code == 200:
                    self.fail(
                        f'{path} was served with status 200; '
                        'it must not be reachable'
                    )
                self.assertNotIn(marker, response.get_data())

    def test_dotfiles_are_not_served(self):
        """Dotfiles get a 404, not the SPA shell."""
        for path in DOTFILE_PATHS:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)

    def test_path_traversal_is_blocked(self):
        """A crafted path cannot escape the asset list."""
        for path in (
            '/../api/app.py',
            '/data/../api/app.py',
            '/%2e%2e/api/app.py',
            '/..%2fapi%2fapp.py',
            '/./../.git/config',
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertNotEqual(response.status_code, 200)
                self.assertNotIn(b'def create_app', response.get_data())

    def test_legitimate_assets_are_served(self):
        """The allow-list must not break the front end."""
        expected_types = {
            '/': 'text/html',
            '/index.html': 'text/html',
            '/styles.css': 'text/css',
            '/public-api.js': 'javascript',
            '/logo-header.png': 'image/png',
            '/admin/': 'text/html',
            '/admin/index.html': 'text/html',
            '/admin/admin-api.js': 'javascript',
        }
        for path, content_type in expected_types.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(content_type, response.content_type)

    def test_spa_fallback_still_works(self):
        """Unknown application routes return the shell, not a 404."""
        response = self.client.get('/some/random/path')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response.content_type)

    def test_missing_asset_is_a_real_404(self):
        """A path that looks like a file is a genuine 404."""
        response = self.client.get('/missing-asset.js')
        self.assertEqual(response.status_code, 404)

    def test_api_404_is_still_json(self):
        response = self.client.get('/api/nonexistent')
        self.assertEqual(response.status_code, 404)
        self.assertIn('application/json', response.content_type)


if __name__ == '__main__':
    unittest.main()
