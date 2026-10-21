#!/usr/bin/env python
"""
Start the Data Dictionary for local development.

The Flask app serves both the API and the static front-end from one
process, so this script simply launches it on port 8000.
"""
import os
import subprocess
import sys


PORT = 8000


def main():
    # Use the SQLite database under <project root>/data for development.
    # The path is absolute because the app is launched with the api
    # directory as its working directory.
    project_root = os.path.dirname(os.path.abspath(__file__))
    database_path = os.path.join(project_root, 'data', 'dictionary.db')

    os.environ.setdefault('DATABASE', database_path)
    os.environ.setdefault('AUTH_DISABLED', 'true')

    print("=" * 60)
    print("Data Dictionary - Local Development")
    print("=" * 60)
    print()
    print(f"Starting Flask on port {PORT}...")
    print()
    print("Public view:  http://localhost:8000/")
    print("Admin view:   http://localhost:8000/admin/")
    print("API:          http://localhost:8000/api")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)

    env = os.environ.copy()
    env['PORT'] = str(PORT)
    subprocess.call([sys.executable, 'wsgi.py'], cwd='api', env=env)


if __name__ == '__main__':
    main()
