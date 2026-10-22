"""Tests that the tracked deployment config is free of site-specific values.

The repository is published, but the production deployment at
Northampton Community College has its own registry, host port, admin
allow-list, and database. Those values live in an untracked override
file; the tracked compose file must stay generic.

The checks below are pattern based rather than a list of known
internal names, so that this test file does not itself publish the
names it is meant to keep out of the repository.
"""

import os
import re
import unittest

import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACKED_COMPOSE = os.path.join(PROJECT_ROOT, 'docker-compose.prod.yml')
LOCAL_COMPOSE = os.path.join(PROJECT_ROOT, 'docker-compose.prod.local.yml')

# A personal address at a real institution, e.g. someone@northampton.edu.
PERSONAL_ADDRESS = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')

# An internal host name, e.g. something.admin.example.edu.
INTERNAL_HOST = re.compile(r'\b[\w-]+\.(?:admin\.|internal\.)[\w-]+\.\w+\b')

# Environment variables that carry a secret and must never be a literal.
SECRET_VARS = ('DATABASE_URL', 'ADMIN_EMAILS', 'PROXY_SHARED_SECRET')


def read_tracked():
    with open(TRACKED_COMPOSE) as handle:
        return handle.read()


def active_lines(text):
    """The lines that are configuration rather than documentation."""
    for raw in text.splitlines():
        line = raw.strip()
        if line and not line.startswith('#'):
            yield line


class TrackedComposeIsGenericTest(unittest.TestCase):
    def setUp(self):
        self.text = read_tracked()
        self.doc = yaml.safe_load(self.text)

    def test_parses(self):
        self.assertIn('services', self.doc)
        self.assertIn('data_dictionary', self.doc['services'])

    def test_no_personal_email_addresses(self):
        """An allow-list belongs in the untracked override, not here."""
        for line in active_lines(self.text):
            for match in PERSONAL_ADDRESS.finditer(line):
                with self.subTest(line=line):
                    self.fail(
                        f'tracked compose file contains an email address: {line}'
                    )

    def test_no_internal_host_names(self):
        for line in active_lines(self.text):
            for match in INTERNAL_HOST.finditer(line):
                with self.subTest(line=line):
                    self.fail(
                        f'tracked compose file contains an internal host: {line}'
                    )

    def test_no_internal_registry_variable(self):
        """The image comes from IMAGE, not a site-specific registry variable."""
        self.assertNotIn('NEXUS', self.text)

    def test_no_inline_password(self):
        """A credential must never appear in the tracked compose file."""
        pattern = re.compile(
            r'(DATABASE_URL|ADMIN_EMAILS|PROXY_SHARED_SECRET)='
            r'(?!\$\{|\s*$)',  # a bare value, not a variable reference
        )
        for line in active_lines(self.text):
            match = pattern.search(line)
            if match:
                with self.subTest(line=line):
                    self.fail(
                        f'tracked compose file sets a literal value: {line}'
                    )
                continue
            match = pattern.search(line)
            if match:
                with self.subTest(line=line):
                    self.fail(
                        f'tracked compose file sets a literal value: {line}'
                    )

    def test_host_port_is_parameterised(self):
        """The host port comes from the environment, not a literal.

        Redeclaring 'ports' in an override file would append to the
        generic entry rather than replace it, which would publish the
        container on two ports at once.
        """
        ports = self.doc['services']['data_dictionary']['ports']
        self.assertEqual(len(ports), 1)
        self.assertIn('${HOST_PORT', ports[0])

    def test_image_is_parameterised(self):
        image = self.doc['services']['data_dictionary']['image']
        self.assertIn('${IMAGE', image)


class LocalOverrideIsUntrackedTest(unittest.TestCase):
    def setUp(self):
        self.exists = os.path.exists(LOCAL_COMPOSE)
        if self.exists:
            with open(LOCAL_COMPOSE) as handle:
                self.text = handle.read()
            self.doc = yaml.safe_load(self.text)

    def test_not_tracked_by_git(self):
        """The override must be ignored, whatever it contains."""
        gitignore = os.path.join(PROJECT_ROOT, '.gitignore')
        with open(gitignore) as handle:
            patterns = handle.read()
        self.assertIn('docker-compose.*.local.yml', patterns)

    def test_uses_variables_not_literals(self):
        """If the override exists, it must not hard-code secrets."""
        if not self.exists:
            self.skipTest('no local override file in this checkout')
        for line in self.text.splitlines():
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            for key in ('DATABASE_URL', 'ADMIN_EMAILS', 'PROXY_SHARED_SECRET'):
                if f'- {key}=' in stripped:
                    with self.subTest(line=stripped):
                        self.assertIn(
                            '${', stripped,
                            f'{key} must be read from the environment',
                        )


if __name__ == '__main__':
    unittest.main()
