"""Tests for entry-to-entry links."""

from integration_tests.base import BaseApiTest


class TestEntryLinks(BaseApiTest):
    def test_create_link(self):
        source = self.create_entry(term='Source', definition='d')
        target = self.create_entry(term='Target', definition='d')
        response = self.client.post(
            f'/api/entries/{source["id"]}/links',
            json={'target_entry_id': target['id']},
        )
        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertEqual(body['target_entry_id'], target['id'])
        self.assertEqual(body['target_term'], 'Target')
        self.assertEqual(body['link_type'], 'see_also')

    def test_create_link_with_custom_type(self):
        source = self.create_entry(term='Src', definition='d')
        target = self.create_entry(term='Tgt', definition='d')
        response = self.client.post(
            f'/api/entries/{source["id"]}/links',
            json={
                'target_entry_id': target['id'],
                'link_type': 'depends_on',
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()['link_type'], 'depends_on')

    def test_create_link_to_nonexistent_target_404(self):
        source = self.create_entry(term='Src', definition='d')
        response = self.client.post(
            f'/api/entries/{source["id"]}/links',
            json={'target_entry_id': 9999},
        )
        self.assertEqual(response.status_code, 404)

    def test_create_link_missing_target_returns_400(self):
        source = self.create_entry(term='Src', definition='d')
        response = self.client.post(
            f'/api/entries/{source["id"]}/links',
            json={},
        )
        self.assertEqual(response.status_code, 400)

    def test_get_entry_links(self):
        source = self.create_entry(term='Hub', definition='d')
        t1 = self.create_entry(term='Spoke1', definition='d')
        t2 = self.create_entry(term='Spoke2', definition='d')
        self.client.post(
            f'/api/entries/{source["id"]}/links',
            json={'target_entry_id': t1['id']},
        )
        self.client.post(
            f'/api/entries/{source["id"]}/links',
            json={'target_entry_id': t2['id']},
        )
        response = self.client.get(f'/api/entries/{source["id"]}/links')
        self.assertEqual(response.status_code, 200)
        links = response.get_json()
        self.assertEqual(len(links), 2)

    def test_get_links_for_entry_with_no_links(self):
        entry = self.create_entry(term='Lonely', definition='d')
        response = self.client.get(f'/api/entries/{entry["id"]}/links')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])

    def test_remove_link(self):
        source = self.create_entry(term='Src', definition='d')
        target = self.create_entry(term='Tgt', definition='d')
        link = self.client.post(
            f'/api/entries/{source["id"]}/links',
            json={'target_entry_id': target['id']},
        ).get_json()
        response = self.client.delete(
            f'/api/entries/{source["id"]}/links/{link["link_id"]}',
        )
        self.assertEqual(response.status_code, 200)
        links = self.client.get(
            f'/api/entries/{source["id"]}/links',
        ).get_json()
        self.assertEqual(len(links), 0)

    def test_links_appear_in_entry_list(self):
        source = self.create_entry(term='Linked', definition='d')
        target = self.create_entry(term='Other', definition='d')
        self.client.post(
            f'/api/entries/{source["id"]}/links',
            json={'target_entry_id': target['id']},
        )
        entries = self.client.get('/api/entries').get_json()
        source_entry = next(
            e for e in entries if e['term'] == 'Linked'
        )
        self.assertEqual(len(source_entry['links']), 1)
        self.assertEqual(source_entry['links'][0]['target_term'], 'Other')

    def test_delete_entry_cascades_to_links(self):
        source = self.create_entry(term='Src', definition='d')
        target = self.create_entry(term='Tgt', definition='d')
        self.client.post(
            f'/api/entries/{source["id"]}/links',
            json={'target_entry_id': target['id']},
        )
        # Deleting the source should remove its outgoing links.
        self.client.delete(f'/api/entries/{source["id"]}', json={})
        # The target entry still exists and has no links.
        target_entry = self.client.get(
            f'/api/entries/{target["id"]}',
        ).get_json()
        self.assertEqual(target_entry['term'], 'Tgt')


if __name__ == '__main__':
    unittest.main()