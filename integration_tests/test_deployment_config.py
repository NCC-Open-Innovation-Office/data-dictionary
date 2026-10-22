"""Tests that the tracked deployment config is free of site-specific values.

The repository is published, but the production deployment at
Northampton Community College has its own registry, host port, admin
allow-list, and database. Those values live in an untracked override
file; the tracked compose file must stay generic.
"""

import os
import re
import unittest

import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACKED_COMPOSE = os.path.join(PROJECT_ROOT, 'docker-compose.prod.yml')
LOCAL_COMPOSE = os.path.join(PROJECT_ROOT, 'docker-compose.prod.local.yml')

# Values that identify a specific deployment and must never be committed.
SITE_SPECIFIC = [
    'wfulmer',
    'mmiller',
    'scarefloor',
    'sully',
    'NEXUS',
]


def read_tracked():
    with open(TRACKED_COMPOSE) as handle:
        return handle.read()


class TrackedComposeIsGenericTest(unittest.TestCase):
    def setUp(self):
        self.text = read_tracked()
        self.doc = yaml.safe_load(self.text)

    def test_parses(self):
        self.assertIn('services', self.doc)
        self.assertIn('data_dictionary', self.doc['services'])

    def test_no_site_specific_values(self):
        for needle in SITE_SPECIFIC:
            with self.subTest(value=needle):
                self.assertNotIn(
                    needle, self.text,
                    f'{needle!r} is deployment-specific and must not be tracked',
                )

    def test_no_inline_password(self):
        """A credential must never appear in the tracked compose file."""
        pattern = re.compile(
            r'(DATABASE_URL|ADMIN_EMAILS|PROXY_SHARED_SECRET)='
            r'(?!\$\{|\s*$)',  # a bare value, not a variable reference
        )
        for raw in self.text.splitlines():
            line = raw.strip()
            if not line or line.startswith('#'):
                # Commented examples are documentation, not configuration.
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
