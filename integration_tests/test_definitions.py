"""Tests for report-specific (per-tag) entry definitions."""

from integration_tests.base import BaseApiTest


class TestEntryDefinitions(BaseApiTest):
    def test_add_definition(self):
        entry = self.create_entry(term='DefEntry', definition='base')
        tag = self.create_tag(name='ReportD')
        response = self.client.post(
            f'/api/entries/{entry["id"]}/definitions',
            json={
                'tag_id': tag['id'],
                'definition': 'Report-specific text',
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn('id', response.get_json())

    def test_add_definition_to_nonexistent_entry_404(self):
        tag = self.create_tag(name='Orphan')
        response = self.client.post(
            '/api/entries/9999/definitions',
            json={'tag_id': tag['id'], 'definition': 'x'},
        )
        self.assertEqual(response.status_code, 404)

    def test_add_definition_with_nonexistent_tag_404(self):
        entry = self.create_entry(term='DefEntry', definition='base')
        response = self.client.post(
            f'/api/entries/{entry["id"]}/definitions',
            json={'tag_id': 9999, 'definition': 'x'},
        )
        self.assertEqual(response.status_code, 404)

    def test_add_definition_missing_fields_returns_400(self):
        entry = self.create_entry(term='DefEntry', definition='base')
        response = self.client.post(
            f'/api/entries/{entry["id"]}/definitions',
            json={},
        )
        self.assertEqual(response.status_code, 400)

    def test_update_existing_definition_upserts(self):
        entry = self.create_entry(term='DefEntry', definition='base')
        tag = self.create_tag(name='ReportU')
        self.client.post(
            f'/api/entries/{entry["id"]}/definitions',
            json={'tag_id': tag['id'], 'definition': 'v1'},
        )
        # Posting again for the same entry+tag should update, not duplicate.
        response = self.client.post(
            f'/api/entries/{entry["id"]}/definitions',
            json={'tag_id': tag['id'], 'definition': 'v2'},
        )
        self.assertEqual(response.status_code, 201)
        defs = self.client.get(
            f'/api/entries/{entry["id"]}/definitions',
        ).get_json()
        self.assertEqual(len(defs), 1)
        self.assertEqual(defs[0]['definition'], 'v2')

    def test_get_definitions_sorted_by_tag_name(self):
        entry = self.create_entry(term='DefEntry', definition='base')
        tag_z = self.create_tag(name='Zebra')
        tag_a = self.create_tag(name='Apple')
        self.client.post(
            f'/api/entries/{entry["id"]}/definitions',
            json={'tag_id': tag_z['id'], 'definition': 'z-def'},
        )
        self.client.post(
            f'/api/entries/{entry["id"]}/definitions',
            json={'tag_id': tag_a['id'], 'definition': 'a-def'},
        )
        defs = self.client.get(
            f'/api/entries/{entry["id"]}/definitions',
        ).get_json()
        self.assertEqual(defs[0]['tag_name'], 'Apple')
        self.assertEqual(defs[1]['tag_name'], 'Zebra')

    def test_definitions_appear_in_entry_list(self):
        entry = self.create_entry(term='DefEntry', definition='base')
        tag = self.create_tag(name='ReportL')
        self.client.post(
            f'/api/entries/{entry["id"]}/definitions',
            json={'tag_id': tag['id'], 'definition': 'report-specific'},
        )
        entries = self.client.get('/api/entries').get_json()
        self.assertEqual(len(entries[0]['report_definitions']), 1)
        self.assertEqual(
            entries[0]['report_definitions'][0]['definition'],
            'report-specific',
        )

    def test_update_definition_by_id(self):
        entry = self.create_entry(term='DefEntry', definition='base')
        tag = self.create_tag(name='ReportUp')
        def_body = self.client.post(
            f'/api/entries/{entry["id"]}/definitions',
            json={'tag_id': tag['id'], 'definition': 'original'},
        ).get_json()
        response = self.client.put(
            f'/api/entries/{entry["id"]}/definitions/{def_body["id"]}',
            json={'definition': 'edited'},
        )
        self.assertEqual(response.status_code, 200)
        defs = self.client.get(
            f'/api/entries/{entry["id"]}/definitions',
        ).get_json()
        self.assertEqual(defs[0]['definition'], 'edited')

    def test_update_definition_wrong_entry_404(self):
        entry = self.create_entry(term='DefEntry', definition='base')
        tag = self.create_tag(name='Report404')
        def_body = self.client.post(
            f'/api/entries/{entry["id"]}/definitions',
            json={'tag_id': tag['id'], 'definition': 'x'},
        ).get_json()
        # Use a wrong entry_id.
        response = self.client.put(
            f'/api/entries/9999/definitions/{def_body["id"]}',
            json={'definition': 'edited'},
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_definition(self):
        entry = self.create_entry(term='DefEntry', definition='base')
        tag = self.create_tag(name='ReportDel')
        def_body = self.client.post(
            f'/api/entries/{entry["id"]}/definitions',
            json={'tag_id': tag['id'], 'definition': 'gone'},
        ).get_json()
        response = self.client.delete(
            f'/api/entries/{entry["id"]}/definitions/{def_body["id"]}',
        )
        self.assertEqual(response.status_code, 200)
        defs = self.client.get(
            f'/api/entries/{entry["id"]}/definitions',
        ).get_json()
        self.assertEqual(len(defs), 0)

    def test_delete_definition_records_history(self):
        entry = self.create_entry(term='DefEntry', definition='base')
        tag = self.create_tag(name='ReportHist')
        def_body = self.client.post(
            f'/api/entries/{entry["id"]}/definitions',
            json={'tag_id': tag['id'], 'definition': 'gone'},
        ).get_json()
        self.client.delete(
            f'/api/entries/{entry["id"]}/definitions/{def_body["id"]}',
        )
        history = self.client.get('/api/history').get_json()
        actions = [item['action'] for item in history]
        self.assertIn('report_def_removed', actions)


if __name__ == '__main__':
    unittest.main()