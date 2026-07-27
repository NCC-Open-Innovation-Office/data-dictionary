"""Tests for the bulk-import endpoint."""

from integration_tests.base import BaseApiTest


class TestBulkImport(BaseApiTest):
    def test_import_new_entries(self):
        response = self.client.post(
            '/api/entries/bulk-import',
            json={
                'entries': [
                    {'term': 'Bulk A', 'definition': 'a'},
                    {'term': 'Bulk B', 'definition': 'b'},
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body['imported'], 2)
        self.assertEqual(body['updated'], 0)
        self.assertEqual(body['skipped'], 0)
        entries = self.client.get('/api/entries').get_json()
        self.assertEqual(len(entries), 2)

    def test_import_updates_existing_entry(self):
        self.create_entry(term='Existing', definition='old')
        response = self.client.post(
            '/api/entries/bulk-import',
            json={
                'entries': [
                    {'term': 'Existing', 'definition': 'new'},
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['updated'], 1)
        self.assertEqual(response.get_json()['imported'], 0)
        entry = self.client.get('/api/entries').get_json()[0]
        self.assertEqual(entry['definition'], 'new')

    def test_import_skips_empty_term(self):
        response = self.client.post(
            '/api/entries/bulk-import',
            json={
                'entries': [
                    {'term': '', 'definition': 'skip me'},
                    {'term': 'Valid', 'definition': 'keep me'},
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body['imported'], 1)
        self.assertEqual(body['skipped'], 1)

    def test_import_empty_list_returns_400(self):
        response = self.client.post(
            '/api/entries/bulk-import',
            json={'entries': []},
        )
        self.assertEqual(response.status_code, 400)

    def test_import_no_entries_key_returns_400(self):
        response = self.client.post(
            '/api/entries/bulk-import',
            json={},
        )
        self.assertEqual(response.status_code, 400)

    def test_import_creates_tags_from_reports_field(self):
        response = self.client.post(
            '/api/entries/bulk-import',
            json={
                'entries': [
                    {
                        'term': 'Tagged',
                        'definition': 'd',
                        'reports': 'Finance, HR',
                    },
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        tags = self.client.get('/api/tags').get_json()
        tag_names = [tag['name'] for tag in tags]
        self.assertIn('Finance', tag_names)
        self.assertIn('HR', tag_names)
        entry = self.client.get('/api/entries').get_json()[0]
        self.assertEqual(len(entry['tags']), 2)

    def test_import_reuses_existing_tag(self):
        self.create_tag(name='ExistingTag')
        self.client.post(
            '/api/entries/bulk-import',
            json={
                'entries': [
                    {
                        'term': 'Reuse',
                        'definition': 'd',
                        'reports': 'ExistingTag',
                    },
                ],
            },
        )
        tags = self.client.get('/api/tags').get_json()
        # Should not duplicate the tag.
        finance_tags = [t for t in tags if t['name'] == 'ExistingTag']
        self.assertEqual(len(finance_tags), 1)

    def test_import_normalizes_classification(self):
        self.client.post(
            '/api/entries/bulk-import',
            json={
                'entries': [
                    {
                        'term': 'Classified',
                        'definition': 'd',
                        'classification': 'private',
                    },
                ],
            },
        )
        entry = self.client.get('/api/entries').get_json()[0]
        self.assertEqual(entry['classification'], 'internal')

    def test_import_mixed_batch(self):
        self.create_entry(term='UpdateMe', definition='old')
        response = self.client.post(
            '/api/entries/bulk-import',
            json={
                'entries': [
                    {'term': 'UpdateMe', 'definition': 'updated'},
                    {'term': 'NewOne', 'definition': 'new'},
                    {'term': '', 'definition': 'skip'},
                ],
            },
        )
        body = response.get_json()
        self.assertEqual(body['imported'], 1)
        self.assertEqual(body['updated'], 1)
        self.assertEqual(body['skipped'], 1)


if __name__ == '__main__':
    unittest.main()