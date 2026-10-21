"""Tests for optional JSON request bodies.

The API accepts a JSON body on most write endpoints, but the body is
optional metadata (`user`, `discussion`) for several of them. Flask's
`request.json` raises a 415 when the Content-Type is not JSON and a 400
when the body is not valid JSON, so it cannot express "the body is
optional". These tests pin the tolerant behaviour.
"""

import unittest

import integration_tests.base as base

from integration_tests.base import BaseApiTest


class TestOptionalJsonBody(BaseApiTest):
    # ------------------------------------------------------------------
    # DELETE without a body
    # ------------------------------------------------------------------
    def test_delete_entry_without_content_type(self):
        entry = self.create_entry(term='Deletable', definition='d')
        response = self.client.delete(f'/api/entries/{entry["id"]}')
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.get_json())

    def test_delete_entry_with_json_content_type_but_no_body(self):
        entry = self.create_entry(term='Deletable', definition='d')
        response = self.client.delete(
            f'/api/entries/{entry["id"]}',
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(response.status_code, 200)

    def test_delete_entry_with_empty_json_object(self):
        entry = self.create_entry(term='Deletable', definition='d')
        response = self.client.delete(
            f'/api/entries/{entry["id"]}',
            json={},
        )
        self.assertEqual(response.status_code, 200)

    def test_delete_entry_records_history(self):
        entry = self.create_entry(term='Deletable', definition='d')
        self.client.delete(f'/api/entries/{entry["id"]}')
        response = self.client.get('/api/history')
        actions = [item['action'] for item in response.get_json()]
        self.assertIn('delete', actions)

    def test_delete_missing_entry_still_404(self):
        response = self.client.delete('/api/entries/9999')
        self.assertEqual(response.status_code, 404)

    # ------------------------------------------------------------------
    # Other body-optional endpoints
    # ------------------------------------------------------------------
    def test_delete_tag_without_body(self):
        tag = self.create_tag(name='Removable')
        response = self.client.delete(f'/api/tags/{tag["id"]}')
        self.assertEqual(response.status_code, 200)

    def test_remove_entry_link_without_body(self):
        source = self.create_entry(term='Source', definition='s')
        target = self.create_entry(term='Target', definition='t')
        self.client.post(
            f'/api/entries/{source["id"]}/links',
            json={'target_entry_id': target['id']},
        )
        links = self.client.get(
            f'/api/entries/{source["id"]}/links'
        ).get_json()
        link_id = links[0]['link_id']
        response = self.client.delete(
            f'/api/entries/{source["id"]}/links/{link_id}'
        )
        self.assertEqual(response.status_code, 200)

    def test_restore_without_body_returns_400(self):
        response = self.client.post('/api/restore')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.get_json())

    def test_bulk_import_without_body_returns_400(self):
        response = self.client.post('/api/entries/bulk-import')
        self.assertEqual(response.status_code, 400)

    # ------------------------------------------------------------------
    # Required fields still fail loudly
    # ------------------------------------------------------------------
    def test_create_entry_without_body_returns_400(self):
        response = self.client.post('/api/entries')
        self.assertEqual(response.status_code, 400)

    def test_create_entry_with_malformed_body_returns_400(self):
        response = self.client.post(
            '/api/entries',
            data='not json at all',
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(response.status_code, 400)

    def test_create_entry_missing_required_field_returns_400(self):
        response = self.client.post('/api/entries', json={'definition': 'x'})
        self.assertEqual(response.status_code, 400)

    def test_create_tag_without_body_returns_400(self):
        response = self.client.post('/api/tags')
        self.assertEqual(response.status_code, 400)

    def test_add_entry_tag_without_body_returns_400(self):
        entry = self.create_entry(term='Tagged', definition='d')
        response = self.client.post(f'/api/entries/{entry["id"]}/tags')
        self.assertEqual(response.status_code, 400)

    # ------------------------------------------------------------------
    # A body sent without a Content-Type is still honoured
    # ------------------------------------------------------------------
    def test_json_body_without_content_type_is_ignored_not_fatal(self):
        """A body that Flask cannot parse is treated as absent.

        Clients that omit the Content-Type header do not get a 415; the
        endpoint behaves as if no body was sent.
        """
        response = self.client.post(
            '/api/entries',
            data='{"term": "T", "definition": "D"}',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.get_json())


if __name__ == '__main__':
    unittest.main()
