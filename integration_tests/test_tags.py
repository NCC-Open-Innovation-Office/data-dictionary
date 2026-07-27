"""Tests for tags and entry-tag associations."""

from integration_tests.base import BaseApiTest


class TestTagsCrud(BaseApiTest):
    def test_create_tag_returns_id(self):
        body = self.create_tag(name='Finance', color='#00FF00')
        self.assertIn('id', body)

    def test_list_tags_sorted_by_name(self):
        self.create_tag(name='Zebra')
        self.create_tag(name='Apple')
        self.create_tag(name='Mango')
        response = self.client.get('/api/tags')
        self.assertEqual(response.status_code, 200)
        names = [tag['name'] for tag in response.get_json()]
        self.assertEqual(names, ['Apple', 'Mango', 'Zebra'])

    def test_create_tag_default_color(self):
        response = self.client.post('/api/tags', json={'name': 'NoColor'})
        self.assertEqual(response.status_code, 201)
        fetched = self.client.get('/api/tags').get_json()
        self.assertEqual(fetched[0]['color'], '#004C8E')

    def test_create_tag_missing_name_returns_400(self):
        response = self.client.post('/api/tags', json={'color': '#000'})
        self.assertEqual(response.status_code, 400)

    def test_delete_tag(self):
        tag = self.create_tag(name='Doomed')
        response = self.client.delete(f'/api/tags/{tag["id"]}')
        self.assertEqual(response.status_code, 200)
        tags = self.client.get('/api/tags').get_json()
        self.assertEqual(len(tags), 0)

    def test_delete_tag_404(self):
        response = self.client.delete('/api/tags/9999')
        self.assertEqual(response.status_code, 404)

    def test_tag_includes_created_at(self):
        self.create_tag(name='Timestamped')
        tag = self.client.get('/api/tags').get_json()[0]
        self.assertIn('createdAt', tag)
        self.assertTrue(tag['createdAt'])


class TestEntryTagAssociations(BaseApiTest):
    def test_add_tag_to_entry(self):
        entry = self.create_entry(term='Tagged', definition='d')
        tag = self.create_tag(name='ReportA')
        response = self.client.post(
            f'/api/entries/{entry["id"]}/tags',
            json={'tag_id': tag['id']},
        )
        self.assertEqual(response.status_code, 200)
        entry_data = self.client.get('/api/entries').get_json()[0]
        self.assertEqual(len(entry_data['tags']), 1)
        self.assertEqual(entry_data['tags'][0]['name'], 'ReportA')

    def test_add_tag_to_nonexistent_entry_404(self):
        tag = self.create_tag(name='Orphan')
        response = self.client.post(
            '/api/entries/9999/tags',
            json={'tag_id': tag['id']},
        )
        self.assertEqual(response.status_code, 404)

    def test_add_nonexistent_tag_to_entry_404(self):
        entry = self.create_entry(term='NoTag', definition='d')
        response = self.client.post(
            f'/api/entries/{entry["id"]}/tags',
            json={'tag_id': 9999},
        )
        self.assertEqual(response.status_code, 404)

    def test_add_same_tag_twice_is_idempotent(self):
        entry = self.create_entry(term='Double', definition='d')
        tag = self.create_tag(name='Dup')
        self.client.post(
            f'/api/entries/{entry["id"]}/tags',
            json={'tag_id': tag['id']},
        )
        self.client.post(
            f'/api/entries/{entry["id"]}/tags',
            json={'tag_id': tag['id']},
        )
        entry_data = self.client.get('/api/entries').get_json()[0]
        self.assertEqual(len(entry_data['tags']), 1)

    def test_remove_tag_from_entry(self):
        entry = self.create_entry(term='Removable', definition='d')
        tag = self.create_tag(name='ToRemove')
        self.client.post(
            f'/api/entries/{entry["id"]}/tags',
            json={'tag_id': tag['id']},
        )
        response = self.client.delete(
            f'/api/entries/{entry["id"]}/tags/{tag["id"]}',
        )
        self.assertEqual(response.status_code, 200)
        entry_data = self.client.get('/api/entries').get_json()[0]
        self.assertEqual(len(entry_data['tags']), 0)

    def test_remove_tag_records_history(self):
        entry = self.create_entry(term='HistTag', definition='d')
        tag = self.create_tag(name='HistReport')
        self.client.post(
            f'/api/entries/{entry["id"]}/tags',
            json={'tag_id': tag['id']},
        )
        self.client.delete(
            f'/api/entries/{entry["id"]}/tags/{tag["id"]}',
        )
        history = self.client.get('/api/history').get_json()
        actions = [item['action'] for item in history]
        self.assertIn('tag_removed', actions)

    def test_add_tag_missing_tag_id_returns_400(self):
        entry = self.create_entry(term='BadReq', definition='d')
        response = self.client.post(
            f'/api/entries/{entry["id"]}/tags',
            json={},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()