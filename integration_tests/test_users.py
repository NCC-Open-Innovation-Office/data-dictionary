"""Tests for SSO user provisioning, merging, and group management.

Covers the lifecycle the admin interface drives:

* a first sign-in creates a user record automatically
* a pre-seeded record is merged into, never duplicated
* group membership decides the role
* deactivating a user revokes access
* the user list is only visible to administrators
"""

import importlib
import os
import tempfile
import unittest
import uuid

from api.app import create_app


AUTH_ENV_VARS = (
    'AUTH_DISABLED',
    'ADMIN_EMAILS',
    'VIEWER_EMAILS',
    'PROXY_SHARED_SECRET',
    'SSO_AUTO_PROVISION',
)


class UserManagementTest(unittest.TestCase):
    def setUp(self):
        self._saved_env = {
            key: os.environ.get(key) for key in AUTH_ENV_VARS
        }
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ.pop('PROXY_SHARED_SECRET', None)
        os.environ.pop('SSO_AUTO_PROVISION', None)
        self.admin_email = f'admin-{uuid.uuid4().hex[:8]}@ncc.edu'
        os.environ['ADMIN_EMAILS'] = self.admin_email

        self.sqlite_file = tempfile.NamedTemporaryFile(
            suffix='.db',
            prefix='dd-users-test-',
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

    def _make_app(self):
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

    def _email(self):
        return f'user-{uuid.uuid4().hex[:8]}@ncc.edu'

    def _admin_headers(self):
        return {'SSOUSER': self.admin_email}

    # ------------------------------------------------------------------
    # Auto-provisioning on first sign-in
    # ------------------------------------------------------------------
    def test_first_login_creates_user(self):
        app = self._make_app()
        email = self._email()
        with app.test_client() as client:
            response = client.get('/api/auth/me', headers={'SSOUSER': email})
            self.assertEqual(response.status_code, 200)
            body = response.get_json()
            self.assertTrue(body['authenticated'])
            self.assertEqual(body['role'], 'viewer')
            self.assertIsNotNone(body['user'])
            self.assertEqual(body['user']['email'], email)
            self.assertIn('viewers', body['user']['groups'])

    def test_second_login_does_not_duplicate(self):
        app = self._make_app()
        email = self._email()
        with app.test_client() as client:
            client.get('/api/auth/me', headers={'SSOUSER': email})
            client.get('/api/auth/me', headers={'SSOUSER': email})
            response = client.get('/api/users', headers=self._admin_headers())
        users = response.get_json()['users']
        matching = [u for u in users if u['email'] == email]
        self.assertEqual(len(matching), 1)

    def test_login_is_case_insensitive(self):
        app = self._make_app()
        email = self._email()
        with app.test_client() as client:
            client.get('/api/auth/me', headers={'SSOUSER': email})
            response = client.get(
                '/api/auth/me',
                headers={'SSOUSER': email.upper()},
            )
        self.assertEqual(response.get_json()['email'], email.lower())

    # ------------------------------------------------------------------
    # Merging a pre-seeded record
    # ------------------------------------------------------------------
    def test_seeded_user_is_merged_not_duplicated(self):
        app = self._make_app()
        email = self._email()
        with app.test_client() as client:
            # An administrator seeds the user before the first sign-in.
            created = client.post(
                '/api/users',
                json={
                    'email': email,
                    'displayName': 'Seeded Person',
                    'groups': ['viewers'],
                },
                headers=self._admin_headers(),
            )
            self.assertEqual(created.status_code, 201)
            seeded_id = created.get_json()['user']['id']

            # The first sign-in merges into that record.
            response = client.get('/api/auth/me', headers={'SSOUSER': email})
            body = response.get_json()
            self.assertEqual(body['user']['id'], seeded_id)
            self.assertEqual(body['user']['displayName'], 'Seeded Person')

            listing = client.get('/api/users', headers=self._admin_headers())
            users = listing.get_json()['users']
            matching = [u for u in users if u['email'] == email]
            self.assertEqual(len(matching), 1)

    def test_seeding_existing_user_updates_groups(self):
        app = self._make_app()
        email = self._email()
        with app.test_client() as client:
            client.get('/api/auth/me', headers={'SSOUSER': email})
            response = client.post(
                '/api/users',
                json={'email': email, 'groups': ['viewers', 'admins']},
                headers=self._admin_headers(),
            )
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.get_json()['created'])
            self.assertEqual(
                response.get_json()['user']['role'],
                'admin',
            )

    # ------------------------------------------------------------------
    # Group membership drives the role
    # ------------------------------------------------------------------
    def test_promotion_grants_admin(self):
        app = self._make_app()
        email = self._email()
        with app.test_client() as client:
            client.get('/api/auth/me', headers={'SSOUSER': email})
            listing = client.get('/api/users', headers=self._admin_headers())
            user_id = [
                u for u in listing.get_json()['users']
                if u['email'] == email
            ][0]['id']

            updated = client.put(
                f'/api/users/{user_id}',
                json={'groups': ['viewers', 'admins']},
                headers=self._admin_headers(),
            )
            self.assertEqual(updated.status_code, 200)

            # The promoted user can now write.
            write = client.post(
                '/api/tags',
                json={'name': f'tag-{uuid.uuid4().hex[:8]}', 'color': '#000'},
                headers={'SSOUSER': email},
            )
            self.assertEqual(write.status_code, 201)

    def test_demotion_revokes_admin(self):
        app = self._make_app()
        email = self._email()
        with app.test_client() as client:
            client.get('/api/auth/me', headers={'SSOUSER': email})
            listing = client.get('/api/users', headers=self._admin_headers())
            user_id = [
                u for u in listing.get_json()['users']
                if u['email'] == email
            ][0]['id']

            client.put(
                f'/api/users/{user_id}',
                json={'groups': ['viewers', 'admins']},
                headers=self._admin_headers(),
            )
            client.put(
                f'/api/users/{user_id}',
                json={'groups': ['viewers']},
                headers=self._admin_headers(),
            )

            write = client.post(
                '/api/tags',
                json={'name': 'nope', 'color': '#000'},
                headers={'SSOUSER': email},
            )
            self.assertEqual(write.status_code, 403)

    def test_deactivated_user_loses_access(self):
        app = self._make_app()
        email = self._email()
        with app.test_client() as client:
            client.get('/api/auth/me', headers={'SSOUSER': email})
            listing = client.get('/api/users', headers=self._admin_headers())
            user_id = [
                u for u in listing.get_json()['users']
                if u['email'] == email
            ][0]['id']

            client.put(
                f'/api/users/{user_id}',
                json={'active': False},
                headers=self._admin_headers(),
            )

            response = client.get('/api/auth/me', headers={'SSOUSER': email})
            self.assertEqual(response.get_json()['role'], 'public')

            write = client.post(
                '/api/tags',
                json={'name': 'nope', 'color': '#000'},
                headers={'SSOUSER': email},
            )
            self.assertEqual(write.status_code, 401)

    def test_admin_env_override_survives_deactivation(self):
        """A deactivated record is refused even if the env list names it.

        The environment lists are a bootstrap and break-glass path, but
        they must not be able to resurrect a person an administrator
        has explicitly deactivated.
        """
        email = self._email()
        os.environ['ADMIN_EMAILS'] = f'{self.admin_email},{email}'
        app = self._make_app()
        with app.test_client() as client:
            client.get('/api/auth/me', headers={'SSOUSER': email})
            listing = client.get('/api/users', headers=self._admin_headers())
            user_id = [
                u for u in listing.get_json()['users']
                if u['email'] == email
            ][0]['id']

            client.put(
                f'/api/users/{user_id}',
                json={'active': False},
                headers=self._admin_headers(),
            )

            response = client.get('/api/auth/me', headers={'SSOUSER': email})
            self.assertEqual(response.get_json()['role'], 'public')

    # ------------------------------------------------------------------
    # Access control on the user endpoints
    # ------------------------------------------------------------------
    def test_anonymous_cannot_list_users(self):
        app = self._make_app()
        with app.test_client() as client:
            response = client.get('/api/users')
            self.assertEqual(response.status_code, 401)

    def test_viewer_cannot_list_users(self):
        app = self._make_app()
        email = self._email()
        with app.test_client() as client:
            client.get('/api/auth/me', headers={'SSOUSER': email})
            response = client.get('/api/users', headers={'SSOUSER': email})
            self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_create_user(self):
        app = self._make_app()
        email = self._email()
        with app.test_client() as client:
            client.get('/api/auth/me', headers={'SSOUSER': email})
            response = client.post(
                '/api/users',
                json={'email': self._email()},
                headers={'SSOUSER': email},
            )
            self.assertEqual(response.status_code, 403)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def test_invalid_email_rejected(self):
        app = self._make_app()
        with app.test_client() as client:
            response = client.post(
                '/api/users',
                json={'email': 'not-an-email'},
                headers=self._admin_headers(),
            )
            self.assertEqual(response.status_code, 400)

    def test_unknown_group_rejected(self):
        app = self._make_app()
        with app.test_client() as client:
            response = client.post(
                '/api/users',
                json={'email': self._email(), 'groups': ['superusers']},
                headers=self._admin_headers(),
            )
            self.assertEqual(response.status_code, 400)

    def test_unknown_user_update_is_404(self):
        app = self._make_app()
        with app.test_client() as client:
            response = client.put(
                '/api/users/999999',
                json={'active': False},
                headers=self._admin_headers(),
            )
            self.assertEqual(response.status_code, 404)

    def test_last_admin_cannot_be_removed(self):
        app = self._make_app()
        with app.test_client() as client:
            client.get('/api/auth/me', headers=self._admin_headers())
            listing = client.get('/api/users', headers=self._admin_headers())
            admin_id = [
                u for u in listing.get_json()['users']
                if u['email'] == self.admin_email
            ][0]['id']
            response = client.delete(
                f'/api/users/{admin_id}',
                headers=self._admin_headers(),
            )
            self.assertEqual(response.status_code, 400)

    def test_reported_role_matches_enforced_role(self):
        """The role shown in the API is the role the API enforces.

        A user named by ADMIN_EMAILS but not in the 'admins' group is
        still an administrator. Both the top-level role and the role
        on the user record must say so, or the admin interface would
        disagree with the access control.
        """
        app = self._make_app()
        email = self._email()
        os.environ['ADMIN_EMAILS'] = f'{self.admin_email},{email}'
        app = self._make_app()
        with app.test_client() as client:
            response = client.get('/api/auth/me', headers={'SSOUSER': email})
            body = response.get_json()
            self.assertEqual(body['role'], 'admin')
            self.assertEqual(body['user']['role'], 'admin')

    def test_deactivated_user_reports_no_access(self):
        app = self._make_app()
        email = self._email()
        with app.test_client() as client:
            client.get('/api/auth/me', headers={'SSOUSER': email})
            listing = client.get('/api/users', headers=self._admin_headers())
            user_id = [
                u for u in listing.get_json()['users']
                if u['email'] == email
            ][0]['id']

            client.put(
                f'/api/users/{user_id}',
                json={'active': False},
                headers=self._admin_headers(),
            )
            response = client.get('/api/auth/me', headers={'SSOUSER': email})
            self.assertEqual(response.get_json()['user']['role'], 'none')

    def test_other_admin_can_be_removed(self):
        app = self._make_app()
        email = self._email()
        with app.test_client() as client:
            client.get('/api/auth/me', headers={'SSOUSER': email})
            listing = client.get('/api/users', headers=self._admin_headers())
            user_id = [
                u for u in listing.get_json()['users']
                if u['email'] == email
            ][0]['id']
            response = client.delete(
                f'/api/users/{user_id}',
                headers=self._admin_headers(),
            )
            self.assertEqual(response.status_code, 200)

    def test_last_admin_cannot_be_demoted(self):
        app = self._make_app()
        with app.test_client() as client:
            client.get('/api/auth/me', headers=self._admin_headers())
            listing = client.get('/api/users', headers=self._admin_headers())
            admin_id = [
                u for u in listing.get_json()['users']
                if u['email'] == self.admin_email
            ][0]['id']
            response = client.put(
                f'/api/users/{admin_id}',
                json={'groups': ['viewers']},
                headers=self._admin_headers(),
            )
            self.assertEqual(response.status_code, 400)

    def test_last_admin_cannot_be_deactivated(self):
        app = self._make_app()
        with app.test_client() as client:
            client.get('/api/auth/me', headers=self._admin_headers())
            listing = client.get('/api/users', headers=self._admin_headers())
            admin_id = [
                u for u in listing.get_json()['users']
                if u['email'] == self.admin_email
            ][0]['id']
            response = client.put(
                f'/api/users/{admin_id}',
                json={'active': False},
                headers=self._admin_headers(),
            )
            self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
