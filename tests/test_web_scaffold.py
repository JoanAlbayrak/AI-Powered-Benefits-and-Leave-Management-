"""Frontend files must stay inside the dedicated asset directory."""
import unittest
from benefits_leave.web import frontend_asset


class FrontendAssets(unittest.TestCase):
    def test_root_and_modules_have_browser_content_types(self):
        content_type, page = frontend_asset('/')
        self.assertEqual(content_type, 'text/html; charset=utf-8')
        self.assertIn(b'type="module"', page)
        content_type, script = frontend_asset('/assets/js/app.js?v=1')
        self.assertEqual(content_type, 'text/javascript; charset=utf-8')
        self.assertIn(b'api.overview', script)
        self.assertTrue(frontend_asset('/assets/styles/app.css')[0].startswith('text/css'))

    def test_repository_and_data_paths_are_not_served(self):
        for path in ('/data/benefits_demo.json', '/assets/../web.py',
                     '/assets/%2e%2e/web.py', '/assets/../../.env',
                     '/assets/missing.js', '/assets/'):
            with self.subTest(path=path):
                self.assertIsNone(frontend_asset(path))


if __name__ == '__main__':
    unittest.main()
