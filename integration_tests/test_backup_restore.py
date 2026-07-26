"""Tests for the backup/restore endpoints and their edge cases."""

from integration_tests.base import BaseApiTest


class TestBackup(BaseApiTest):
    def test_backup_empty_database(self):
        response = self.client.get('/api/backup')
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body['entries'], [])
        self.assertEqual(body['tags'], [])
        self.assertEqual(body['version'], 2)
        self.assertIn('exportedAt', body)

    def test_backup_includes_all_data(self):
        entry = self.create_entry(term='BakEntry', definition='d')
        tag = self.create_tag(name='BakTag')
        self.client.post(
            f'/api/entries/{entry["id"]}/tags',
            json={'tag_id': tag['id']},
        )
        backup = self.client.get('/api/backup').get_json()
        self.assertEqual(len(backup['entries']), 1)
        self.assertEqual(len(backup['tags']), 1)
        self.assertEqual(len(backup['entry_tags']), 1)
        self.assertEqual(backup['entry_tags'][0]['entry_id'], entry['id'])
        self.assertEqual(backup['entry_tags'][0]['tag_id'], tag['id'])

    def test_backup_includes_links_and_definitions(self):
        source = self.create_entry(term='Source', definition='d')
        target = self.create_entry(term='Target', definition='d')
        tag = self.create_tag(name='ReportB')
        self.client.post(
            f'/api/entries/{source["id"]}/links',
            json={'target_entry_id': target['id']},
        )
        self.client.post(
            f'/api/entries/{source["id"]}/definitions',
            json={'tag_id': tag['id'], 'definition': 'report-def'},
        )
        backup = self.client.get('/api/backup').get_json()
        self.assertEqual(len(backup['entry_links']), 1)
        self.assertEqual(len(backup['entry_definitions']), 1)


class TestRestore(BaseApiTest):
    def test_restore_empty_backup(self):
        response = self.client.post(
            '/api/restore',
            json={
                'entries': [],
                'tags': [],
                'entry_tags': [],
                'entry_links': [],
                'entry_definitions': [],
                'change_history': [],
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_restore_invalid_format_returns_400(self):
        response = self.client.post('/api/restore', json={'wrong': 'key'})
        self.assertEqual(response.status_code, 400)

    def test_restore_missing_entries_key_returns_400(self):
        response = self.client.post('/api/restore', json={})
        self.assertEqual(response.status_code, 400)

    def test_restore_replaces_existing_data(self):
        # Pre-populate with data.
        self.create_entry(term='OldEntry', definition='old')
        self.create_tag(name='OldTag')

        # Restore with completely different data.
        response = self.client.post(
            '/api/restore',
            json={
                'entries': [
                    {
                        'id': 1,
                        'term': 'NewEntry',
                        'definition': 'new',
                        'abbreviation': '',
                        'dataType': '',
                        'inputFormat': '',
                        'variations': '',
                        'owner': '',
                        'stewards': '',
                        'classification': 'public',
                        'discussion': '',
                        'ddId': '',
                    },
                ],
                'tags': [],
                'entry_tags': [],
                'entry_links': [],
                'entry_definitions': [],
                'change_history': [],
            },
        )
        self.assertEqual(response.status_code, 200)
        entries = self.client.get('/api/entries').get_json()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['term'], 'NewEntry')
        # Old tag should be gone.
        tags = self.client.get('/api/tags').get_json()
        self.assertEqual(len(tags), 0)

    def test_backup_then_restore_is_lossless(self):
        entry = self.create_entry(term='RoundTrip', definition='d')
        tag = self.create_tag(name='RTTag', color='#AABBCC')
        self.client.post(
            f'/api/entries/{entry["id"]}/tags',
            json={'tag_id': tag['id']},
        )
        self.client.post(
            f'/api/entries/{entry["id"]}/definitions',
            json={'tag_id': tag['id'], 'definition': 'rt-def'},
        )

        backup = self.client.get('/api/backup').get_json()

        # Wipe the database by restoring an empty set.
        self.client.post(
            '/api/restore',
            json={
                'entries': [],
                'tags': [],
                'entry_tags': [],
                'entry_links': [],
                'entry_definitions': [],
                'change_history': [],
            },
        )
        self.assertEqual(len(self.client.get('/api/entries').get_json()), 0)

        # Restore the backup.
        self.client.post('/api/restore', json=backup)
        entries = self.client.get('/api/entries').get_json()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['term'], 'RoundTrip')
        self.assertEqual(len(entries[0]['tags']), 1)
        self.assertEqual(entries[0]['tags'][0]['name'], 'RTTag')
        self.assertEqual(entries[0]['tags'][0]['color'], '#AABBCC')
        self.assertEqual(len(entries[0]['report_definitions']), 1)

    def test_restore_preserves_entry_links(self):
        source = self.create_entry(term='Src', definition='d')
        target = self.create_entry(term='Tgt', definition='d')
        self.client.post(
            f'/api/entries/{source["id"]}/links',
            json={'target_entry_id': target['id']},
        )
        backup = self.client.get('/api/backup').get_json()

        # Wipe and restore.
        self.client.post(
            '/api/restore',
            json={
                'entries': [],
                'tags': [],
                'entry_tags': [],
                'entry_links': [],
                'entry_definitions': [],
                'change_history': [],
            },
        )
        self.client.post('/api/restore', json=backup)

        entries = self.client.get('/api/entries').get_json()
        src_entry = next(e for e in entries if e['term'] == 'Src')
        self.assertEqual(len(src_entry['links']), 1)
        self.assertEqual(src_entry['links'][0]['target_term'], 'Tgt')


if __name__ == '__main__':
    unittest.main()