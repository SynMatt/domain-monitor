import unittest
from pathlib import Path
from test_app import Tests
import app as m

class CounterLayoutTests(Tests):
    def test_version_and_layout(self):
        self.assertEqual(self.client.get('/health').json['version'],'0.9.1')
        css=Path('/app/templates/base.html').read_text()
        self.assertIn('grid-template-columns:repeat(3,minmax(0,1fr))',css)
        self.assertIn('padding:12px 14px',css)
        self.assertIn('@media(max-width:1100px)',css)
        self.assertIn('white-space:nowrap',css)
        self.assertIn('@media(max-width:700px)',css)
    def test_changelog_entry(self):
        text=Path('/app/CHANGELOG.md').read_text()
        self.assertIn('## 0.9.1 - 2026-11-10',text)
        self.assertIn('### Fixed',text)

if __name__=='__main__': unittest.main(verbosity=2)
