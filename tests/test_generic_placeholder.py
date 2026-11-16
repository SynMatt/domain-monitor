import unittest
from pathlib import Path
from test_app import Tests
import app as m

class GenericPlaceholderTests(Tests):
    def test_placeholder_is_generic(self):
        self.auth()
        page=self.client.get('/')
        self.assertIn(b'e.g. example.com, client name or Cloudflare',page.data)
        self.assertNotIn(b'example-company',page.data.lower())
    def test_version_and_changelog(self):
        self.assertEqual(self.client.get('/health').json['version'],'0.14.0')
        self.assertIn('## 0.14.0 - 2026-11-17',Path('/app/CHANGELOG.md').read_text())
if __name__=='__main__': unittest.main(verbosity=2)
