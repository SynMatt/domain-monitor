import unittest
from pathlib import Path
from test_app import Tests
import app as m

class AiDisclaimerTests(Tests):
    def test_disclaimer_is_visible(self):
        self.auth()
        page=self.client.get('/')
        self.assertEqual(page.status_code,200)
        self.assertIn(b'AI-assisted project disclaimer',page.data)
        self.assertIn(b'may not be actively maintained',page.data)
        self.assertIn(b'independently validate results',page.data)
    def test_version_and_changelog(self):
        self.assertEqual(self.client.get('/health').json['version'],'0.13.2')
        self.assertIn('## 0.13.2 - 2026-11-11',Path('/app/CHANGELOG.md').read_text())
if __name__=='__main__': unittest.main(verbosity=2)
