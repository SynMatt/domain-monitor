import unittest
from pathlib import Path
from test_app import Tests
import app as m

class GenericPlaceholderTests(Tests):
    def test_placeholder_is_generic(self):
        self.auth()
        page=self.client.get('/')
        self.assertIn(b'e.g. example.com or client name',page.data)
        self.assertNotIn(b'example-company',page.data.lower())
    def test_version_and_changelog(self):
        self.assertEqual(self.client.get('/health').json['version'],'0.12.3')
        self.assertIn('## 0.12.3 - 2026-11-11',Path('/app/CHANGELOG.md').read_text())
if __name__=='__main__': unittest.main(verbosity=2)
