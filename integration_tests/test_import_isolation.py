"""Regression tests for import-time side effects.

`api/__init__.py` used to eagerly import `api.wsgi`, whose module-level
`create_app()` call resolved the database from the DATABASE environment
variable and created/migrated it on disk. Any import of the `api` package
therefore wrote to a real database file, and the eagerly created Flask
instance shadowed the `api.app` submodule.

These tests pin both behaviours so they cannot silently regress.
"""

import os
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ImportIsolationTest(unittest.TestCase):
    def _run_python(self, snippet, database_path):
        """Run a snippet in a fresh interpreter with DATABASE pointed at
        a throwaway path, and report whether the database file was created.
        """
        env = os.environ.copy()
        env['DATABASE'] = database_path
        env['PYTHONPATH'] = PROJECT_ROOT
        completed = subprocess.run(
            [sys.executable, '-c', snippet],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            f'snippet failed:\n{completed.stdout}\n{completed.stderr}',
        )
        return completed

    def test_importing_api_app_does_not_create_database(self):
        with tempfile.TemporaryDirectory() as workdir:
            database_path = os.path.join(workdir, 'should-not-exist.db')
            self._run_python(
                'import api.app',
                database_path,
            )
            self.assertFalse(
                os.path.exists(database_path),
                'Importing api.app must not create or migrate a database file.',
            )

    def test_importing_api_package_does_not_create_database(self):
        with tempfile.TemporaryDirectory() as workdir:
            database_path = os.path.join(workdir, 'should-not-exist.db')
            self._run_python(
                'import api',
                database_path,
            )
            self.assertFalse(
                os.path.exists(database_path),
                'Importing the api package must not create a database file.',
            )

    def test_api_app_submodule_is_not_shadowed(self):
        """`api.app` must stay the module, so api.app.create_app works."""
        with tempfile.TemporaryDirectory() as workdir:
            self._run_python(
                'import api.app; assert callable(api.app.create_app)',
                os.path.join(workdir, 'should-not-exist.db'),
            )

    def test_package_exposes_create_app_and_application(self):
        with tempfile.TemporaryDirectory() as workdir:
            self._run_python(
                'from api import create_app, application; '
                'assert callable(create_app); '
                'assert application.name',
                os.path.join(workdir, 'should-not-exist.db'),
            )


if __name__ == '__main__':
    unittest.main()
