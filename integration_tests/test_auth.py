"""Tests for the SSO authentication and role-resolution layer.

The app trusts the SSOUSER header, which the reverse proxy sets after
authenticating the person. These tests cover role resolution, the
shared-secret guard against header spoofing, and the fail-closed policy
for endpoints that are not on the public list.
"""

import importlib
import os
import tempfile
import unittest
import uuid

from flask import jsonify

from api.app import create_app


PUBLIC_ENDPOINTS = [
    ('/api/health', 'GET'),
    ('/api/config', 'GET'),
    ('/api/entries', 'GET'),
    ('/api/history', 'GET'),
    ('/api/tags', 'GET'),
    ('/api/owners', 'GET'),
    ('/api/stewards', 'GET'),
]

# Environment variables the auth layer reads. Each test restores them.
AUTH_ENV_VARS = (
    'AUTH_DISABLED',
    'SSOUSER_HEADER',
    'AUTH_TRUSTED_SECRET_HEADER',
    'PROXY_SHARED_SECRET',
    'ADMIN_EMAILS',
    'VIEWER_EMAILS',
    'SSO_AUTO_PROVISION',
)


class AuthIntegrationTest(unittest.TestCase):
    """Role resolution and access control with auth enabled."""

    def setUp(self):
        self._saved_env = {
            key: os.environ.get(key) for key in AUTH_ENV_VARS
        }
        self.sqlite_file = tempfile.NamedTemporaryFile(
            suffix='.db',
            prefix='dd-auth-test-',
            delete=False,
        )
        self.sqlite_file.close()

        # Every app built by this test class must be backed by a throwaway
        # database. Without an explicit database_url, create_app() falls back
        # to the DATABASE env var (default 'dictionary.db') and would write
        # straight into the repository's real database file.
        self.sqlite_file = tempfile.NamedTemporaryFile(
            suffix='.db',
            prefix='dd-auth-test-',
            delete=False,
        )
        self.sqlite_file.close()

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        if os.path.exists(self.sqlite_file.name):
            os.unlink(self.sqlite_file.name)

        if os.path.exists(self.sqlite_file.name):
            os.unlink(self.sqlite_file.name)

    def _make_app(self):
        # Reload the modules so the env tweaks take effect.
        import api.auth as auth
        import api.users as users

        importlib.reload(auth)
        importlib.reload(users)
        app = create_app(
            database_url=f'sqlite:///{self.sqlite_file.name}',
            initialize=True,
            testing=True,
        )
        app.config['TESTING'] = True
        return app

    def _unique_email(self):
        return f'user-{uuid.uuid4().hex[:8]}@ncc.edu'

    def _admin_headers(self, email=None):
        return {'SSOUSER': email or self._unique_email()}

    def _viewer_headers(self, email=None):
        return {'SSOUSER': email or self._unique_email()}

    # ------------------------------------------------------------------
    # Role resolution
    # ------------------------------------------------------------------
    def test_auth_disabled_anonymous_public(self):
        os.environ['AUTH_DISABLED'] = 'true'
        app = self._make_app()
        with app.test_client() as client:
            response = client.get('/api/auth/me')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()['role'], 'public')
            self.assertFalse(response.get_json()['authenticated'])

    def test_authenticated_viewer(self):
        email = self._unique_email()
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ['ADMIN_EMAILS'] = 'nobody@ncc.edu'
        app = self._make_app()
        with app.test_client() as client:
            response = client.get('/api/auth/me', headers=self._viewer_headers(email))
            self.assertEqual(response.status_code, 200)
            body = response.get_json()
            self.assertEqual(body['role'], 'viewer')
            self.assertEqual(body['email'], email)
            self.assertTrue(body['authenticated'])

    def test_authenticated_admin(self):
        email = self._unique_email()
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ['ADMIN_EMAILS'] = email
        app = self._make_app()
        with app.test_client() as client:
            response = client.get('/api/auth/me', headers=self._admin_headers(email))
            self.assertEqual(response.get_json()['role'], 'admin')

    def test_viewer_emails_env_grants_viewer(self):
        email = self._unique_email()
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ['VIEWER_EMAILS'] = email
        app = self._make_app()
        with app.test_client() as client:
            response = client.get('/api/auth/me', headers=self._viewer_headers(email))
            self.assertEqual(response.get_json()['role'], 'viewer')

    def test_email_is_normalized_to_lowercase(self):
        email = self._unique_email()
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ['ADMIN_EMAILS'] = email
        app = self._make_app()
        with app.test_client() as client:
            response = client.get(
                '/api/auth/me',
                headers={'SSOUSER': email.upper()},
            )
            body = response.get_json()
            self.assertEqual(body['role'], 'admin')
            self.assertEqual(body['email'], email.lower())

    # ------------------------------------------------------------------
    # Public read access (anonymous allowed)
    # ------------------------------------------------------------------
    def test_public_can_read(self):
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ['ADMIN_EMAILS'] = 'nobody@ncc.edu'
        app = self._make_app()
        with app.test_client() as client:
            for path, method in PUBLIC_ENDPOINTS:
                with self.subTest(path=path):
                    response = client.open(path, method=method)
                    self.assertEqual(
                        response.status_code,
                        200,
                        f'{method} {path} failed: {response.status_code}',
                    )

    def test_front_end_assets_are_public(self):
        """The public page must load for anonymous visitors."""
        os.environ['AUTH_DISABLED'] = 'false'
        app = self._make_app()
        with app.test_client() as client:
            for path in (
                '/',
                '/index.html',
                '/styles.css',
                '/public-api.js',
                '/logo-header.png',
                '/admin/',
                '/admin/admin-api.js',
            ):
                with self.subTest(path=path):
                    response = client.get(path)
                    self.assertEqual(
                        response.status_code,
                        200,
                        f'{path} failed: {response.status_code}',
                    )

    # ------------------------------------------------------------------
    # Write protection
    # ------------------------------------------------------------------
    def test_anonymous_cannot_write(self):
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ['ADMIN_EMAILS'] = 'nobody@ncc.edu'
        app = self._make_app()
        with app.test_client() as client:
            response = client.post('/api/entries', json={'term': 'X'})
            self.assertEqual(response.status_code, 401)

    def test_viewer_cannot_write(self):
        email = self._unique_email()
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ['ADMIN_EMAILS'] = 'nobody@ncc.edu'
        app = self._make_app()
        with app.test_client() as client:
            response = client.post(
                '/api/entries',
                json={'term': 'X'},
                headers=self._viewer_headers(email),
            )
            self.assertEqual(response.status_code, 403)

    def test_admin_can_write(self):
        email = self._unique_email()
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ['ADMIN_EMAILS'] = email
        app = self._make_app()
        with app.test_client() as client:
            headers = self._admin_headers(email)
            create_response = client.post(
                '/api/entries',
                json={
                    'term': f'Auth {uuid.uuid4().hex[:8]}',
                    'definition': 'created by admin',
                },
                headers=headers,
            )
            self.assertEqual(create_response.status_code, 201)

            # The authenticated email should be recorded in change history.
            history_response = client.get('/api/history', headers=headers)
            self.assertEqual(history_response.status_code, 200)
            users = [item['user'] for item in history_response.get_json()]
            self.assertIn(email, users)

    # ------------------------------------------------------------------
    # Backup requires viewer+
    # ------------------------------------------------------------------
    def test_anonymous_cannot_backup(self):
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ['ADMIN_EMAILS'] = 'nobody@ncc.edu'
        app = self._make_app()
        with app.test_client() as client:
            response = client.get('/api/backup')
            self.assertEqual(response.status_code, 401)

    def test_viewer_can_backup(self):
        email = self._unique_email()
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ['ADMIN_EMAILS'] = 'nobody@ncc.edu'
        app = self._make_app()
        with app.test_client() as client:
            response = client.get(
                '/api/backup',
                headers=self._viewer_headers(email),
            )
            self.assertEqual(response.status_code, 200)

    # ------------------------------------------------------------------
    # Shared secret guards against header spoofing
    # ------------------------------------------------------------------
    def test_identity_header_ignored_without_secret(self):
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ['ADMIN_EMAILS'] = 'boss@ncc.edu'
        os.environ['PROXY_SHARED_SECRET'] = 'expected-secret'
        app = self._make_app()
        with app.test_client() as client:
            response = client.get(
                '/api/auth/me',
                headers={'SSOUSER': 'boss@ncc.edu'},
            )
            body = response.get_json()
            self.assertEqual(body['role'], 'public')
            self.assertFalse(body['authenticated'])

    def test_identity_header_ignored_with_wrong_secret(self):
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ['ADMIN_EMAILS'] = 'boss@ncc.edu'
        os.environ['PROXY_SHARED_SECRET'] = 'expected-secret'
        app = self._make_app()
        with app.test_client() as client:
            response = client.get(
                '/api/auth/me',
                headers={
                    'SSOUSER': 'boss@ncc.edu',
                    'X-Proxy-Secret': 'wrong-secret',
                },
            )
            self.assertEqual(response.get_json()['role'], 'public')

    def test_identity_header_trusted_with_correct_secret(self):
        email = self._unique_email()
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ['ADMIN_EMAILS'] = email
        os.environ['PROXY_SHARED_SECRET'] = 'expected-secret'
        app = self._make_app()
        with app.test_client() as client:
            response = client.get(
                '/api/auth/me',
                headers={
                    'SSOUSER': email,
                    'X-Proxy-Secret': 'expected-secret',
                },
            )
            self.assertEqual(response.get_json()['role'], 'admin')

    def test_spoofed_admin_cannot_write(self):
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ['ADMIN_EMAILS'] = 'boss@ncc.edu'
        os.environ['PROXY_SHARED_SECRET'] = 'expected-secret'
        app = self._make_app()
        with app.test_client() as client:
            response = client.post(
                '/api/entries',
                json={'term': 'Spoofed', 'definition': 'nope'},
                headers={'SSOUSER': 'boss@ncc.edu'},
            )
            self.assertEqual(response.status_code, 401)

    # ------------------------------------------------------------------
    # Fail-closed policy for unregistered endpoints
    # ------------------------------------------------------------------
    def test_unregistered_get_requires_viewer(self):
        """A GET endpoint that is not on the public list must fail closed."""
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ['ADMIN_EMAILS'] = 'nobody@ncc.edu'
        app = self._make_app()

        @app.route('/api/brand-new-feature')
        def brand_new_feature():
            return jsonify({'secret': 'should not be public'})

        with app.test_client() as client:
            response = client.get('/api/brand-new-feature')
            self.assertEqual(response.status_code, 401)

            email = self._unique_email()
            response = client.get(
                '/api/brand-new-feature',
                headers=self._viewer_headers(email),
            )
            self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
