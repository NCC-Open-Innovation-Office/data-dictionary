"""Tests for the entries CRUD endpoints and related behaviours."""

import integration_tests.base as base

from integration_tests.base import BaseApiTest


class TestEntriesCrud(BaseApiTest):
    def test_create_entry_returns_id(self):
        body = self.create_entry(term='Alpha', definition='First')
        self.assertIn('id', body)
        self.assertIsInstance(body['id'], int)

    def test_list_entries_is_sorted_by_term(self):
        self.create_entry(term='Zebra', definition='z')
        self.create_entry(term='Apple', definition='a')
        self.create_entry(term='Mango', definition='m')
        response = self.client.get('/api/entries')
        self.assertEqual(response.status_code, 200)
        terms = [entry['term'] for entry in response.get_json()]
        self.assertEqual(terms, ['Apple', 'Mango', 'Zebra'])

    def test_list_entries_includes_related_data(self):
        entry = self.create_entry(term='Linked', definition='d')
        tag = self.create_tag(name='ReportX')
        self.client.post(
            f'/api/entries/{entry["id"]}/tags',
            json={'tag_id': tag['id']},
        )
        response = self.client.get('/api/entries')
        entry_data = response.get_json()[0]
        self.assertIn('tags', entry_data)
        self.assertIn('links', entry_data)
        self.assertIn('report_definitions', entry_data)
        self.assertEqual(len(entry_data['tags']), 1)

    def test_get_single_entry(self):
        entry = self.create_entry(term='Solo', definition='one')
        response = self.client.get(f'/api/entries/{entry["id"]}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['term'], 'Solo')

    def test_get_single_entry_404(self):
        response = self.client.get('/api/entries/9999')
        self.assertEqual(response.status_code, 404)

    def test_update_entry(self):
        entry = self.create_entry(term='Original', definition='v1')
        response = self.client.put(
            f'/api/entries/{entry["id"]}',
            json={'term': 'Updated', 'definition': 'v2'},
        )
        self.assertEqual(response.status_code, 200)
        fetched = self.client.get(f'/api/entries/{entry["id"]}').get_json()
        self.assertEqual(fetched['term'], 'Updated')
        self.assertEqual(fetched['definition'], 'v2')

    def test_update_entry_404(self):
        response = self.client.put(
            '/api/entries/9999',
            json={'term': 'X', 'definition': 'Y'},
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_entry(self):
        entry = self.create_entry(term='Doomed', definition='bye')
        response = self.client.delete(
            f'/api/entries/{entry["id"]}',
            json={},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.get(f'/api/entries/{entry["id"]}').status_code,
            404,
        )

    def test_delete_entry_404(self):
        response = self.client.delete('/api/entries/9999', json={})
        self.assertEqual(response.status_code, 404)

    def test_create_entry_missing_term_returns_400(self):
        response = self.client.post(
            '/api/entries',
            json={'definition': 'no term'},
        )
        self.assertEqual(response.status_code, 400)

    def test_create_entry_missing_definition_returns_400(self):
        response = self.client.post(
            '/api/entries',
            json={'term': 'NoDef'},
        )
        self.assertEqual(response.status_code, 400)


class TestEntryClassification(BaseApiTest):
    def test_default_classification_is_public(self):
        entry = self.create_entry(term='C1', definition='d')
        fetched = self.client.get(f'/api/entries/{entry["id"]}').get_json()
        self.assertEqual(fetched['classification'], 'public')

    def test_private_classification_normalized_to_internal(self):
        entry = self.create_entry(
            term='C2',
            definition='d',
            classification='private',
        )
        fetched = self.client.get(f'/api/entries/{entry["id"]}').get_json()
        self.assertEqual(fetched['classification'], 'internal')

    def test_internal_classification_preserved(self):
        entry = self.create_entry(
            term='C3',
            definition='d',
            classification='internal',
        )
        fetched = self.client.get(f'/api/entries/{entry["id"]}').get_json()
        self.assertEqual(fetched['classification'], 'internal')

    def test_blank_classification_defaults_to_public(self):
        entry = self.create_entry(
            term='C4',
            definition='d',
            classification='',
        )
        fetched = self.client.get(f'/api/entries/{entry["id"]}').get_json()
        self.assertEqual(fetched['classification'], 'public')


class TestChangeHistory(BaseApiTest):
    def test_create_records_history(self):
        self.create_entry(term='Hist1', definition='d')
        response = self.client.get('/api/history')
        self.assertEqual(response.status_code, 200)
        actions = [item['action'] for item in response.get_json()]
        self.assertIn('create', actions)

    def test_update_records_history(self):
        entry = self.create_entry(term='Hist2', definition='d')
        self.client.put(
            f'/api/entries/{entry["id"]}',
            json={'term': 'Hist2', 'definition': 'updated'},
        )
        response = self.client.get('/api/history')
        actions = [item['action'] for item in response.get_json()]
        self.assertIn('update', actions)

    def test_delete_records_history(self):
        entry = self.create_entry(term='Hist3', definition='d')
        self.client.delete(f'/api/entries/{entry["id"]}', json={})
        response = self.client.get('/api/history')
        actions = [item['action'] for item in response.get_json()]
        self.assertIn('delete', actions)

    def test_history_is_sorted_newest_first(self):
        entry = self.create_entry(term='Sort', definition='d')
        self.client.put(
            f'/api/entries/{entry["id"]}',
            json={'term': 'Sort', 'definition': 'v2'},
        )
        response = self.client.get('/api/history')
        history = response.get_json()
        self.assertGreaterEqual(len(history), 2)
        # The most recent action should be the update.
        self.assertEqual(history[0]['action'], 'update')


class TestHealthAndConfig(BaseApiTest):
    def test_health_check(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['status'], 'ok')

    def test_config_returns_allowDdIdEdit(self):
        response = self.client.get('/api/config')
        self.assertEqual(response.status_code, 200)
        self.assertIn('allowDdIdEdit', response.get_json())


class TestOwnersAndStewards(BaseApiTest):
    def test_owners_returns_unique_values(self):
        self.create_entry(term='O1', definition='d', owner='Quality')
        self.create_entry(term='O2', definition='d', owner='Quality')
        self.create_entry(term='O3', definition='d', owner='Security')
        response = self.client.get('/api/owners')
        self.assertEqual(response.status_code, 200)
        owners = response.get_json()
        self.assertIn('Quality', owners)
        self.assertIn('Security', owners)
        # No duplicates.
        self.assertEqual(len(owners), len(set(owners)))

    def test_stewards_returns_unique_values(self):
        self.create_entry(term='S1', definition='d', stewards='Alice')
        self.create_entry(term='S2', definition='d', stewards='Bob')
        response = self.client.get('/api/stewards')
        self.assertEqual(response.status_code, 200)
        stewards = response.get_json()
        self.assertIn('Alice', stewards)
        self.assertIn('Bob', stewards)

    def test_owners_empty_when_no_entries(self):
        response = self.client.get('/api/owners')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])


if __name__ == '__main__':
    unittest.main()