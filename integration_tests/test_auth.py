import os
import unittest
import uuid

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


class AuthIntegrationTest(unittest.TestCase):
    def setUp(self):
        self._saved_env = {
            key: os.environ.get(key)
            for key in (
                'AUTH_DISABLED',
                'AUTH_TRUSTED_EMAIL_HEADER',
                'ADMIN_EMAILS',
            )
        }

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _make_app(self):
        import api.auth as auth

        # Reload config so the env tweaks take effect inside the app.
        import importlib

        importlib.reload(auth)
        app = create_app(initialize=True, testing=True)
        app.config['TESTING'] = True
        return app

    def _unique_email(self):
        return f'user-{uuid.uuid4().hex[:8]}@ncc.edu'

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
            response = client.get(
                '/api/auth/me',
                headers={'Cf-Access-Authenticated-User-Email': email},
            )
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
            response = client.get(
                '/api/auth/me',
                headers={'Cf-Access-Authenticated-User-Email': email},
            )
            self.assertEqual(response.get_json()['role'], 'admin')

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
                headers={'Cf-Access-Authenticated-User-Email': email},
            )
            self.assertEqual(response.status_code, 403)

    def test_admin_can_write(self):
        email = self._unique_email()
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ['ADMIN_EMAILS'] = email
        app = self._make_app()
        with app.test_client() as client:
            headers = {'Cf-Access-Authenticated-User-Email': email}
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
            users = [
                item['user']
                for item in history_response.get_json()
            ]
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
                headers={'Cf-Access-Authenticated-User-Email': email},
            )
            self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()