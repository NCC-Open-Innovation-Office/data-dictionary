"""Tests for static-file serving and SPA fallback routes."""

import os

from integration_tests.base import BaseApiTest


class TestStaticServing(BaseApiTest):
    def test_index_html_served(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_styles_css_served(self):
        response = self.client.get('/styles.css')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/css', response.content_type)

    def test_public_api_js_served(self):
        response = self.client.get('/public-api.js')
        self.assertEqual(response.status_code, 200)
        self.assertIn('javascript', response.content_type)

    def test_admin_index_served(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)

    def test_admin_api_js_served(self):
        response = self.client.get('/admin/admin-api.js')
        self.assertEqual(response.status_code, 200)
        self.assertIn('javascript', response.content_type)

    def test_logo_served(self):
        response = self.client.get('/logo-header.png')
        self.assertEqual(response.status_code, 200)

    def test_unknown_path_falls_back_to_index(self):
        response = self.client.get('/some/random/path')
        self.assertEqual(response.status_code, 200)

    def test_admin_subpath_falls_back_to_admin_shell(self):
        response = self.client.get('/admin/some/deep/path')
        self.assertEqual(response.status_code, 200)

    def test_api_404_is_real_404(self):
        response = self.client.get('/api/nonexistent')
        self.assertEqual(response.status_code, 404)

    def test_admin_without_trailing_slash(self):
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 200)

    def test_admin_shell_references_its_script_by_absolute_path(self):
        """The admin shell must load its script from either admin URL.

        The shell is served at both '/admin' and '/admin/'. A relative
        script src resolves differently for the two: from '/admin' it
        becomes '/admin-api.js' (404), which leaves the admin table
        empty with no error on the page. An absolute path resolves the
        same way from both URLs.
        """
        for path in ('/admin', '/admin/'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                body = response.get_data(as_text=True)
                self.assertIn('src="/admin/admin-api.js', body)
                self.assertNotIn('src="admin-api.js', body)


if __name__ == '__main__':
    unittest.main()
