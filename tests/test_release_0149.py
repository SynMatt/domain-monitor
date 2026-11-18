import unittest
from pathlib import Path
import app as m
ROOT=Path('/app')
class Release0149Tests(unittest.TestCase):
    def test_readme_current_and_not_duplicated(self):
        text=(ROOT/'README.md').read_text()
        self.assertIn('<!-- README reviewed for release: '+m.APP_VERSION+' -->',text)
        self.assertNotIn('<a href=',text)
        self.assertNotIn('fai-ChatInputEntity',text)
        self.assertNotIn('mx5' + 'matt',text.lower())
        for heading in ('## 🔄 Updating','## 💾 Backups and restore','## 🚀 Quick start','## 🧪 Development and releases'):
            self.assertEqual(text.count(heading),1,heading)
    def test_generated_block_is_compact(self):
        text=(ROOT/'README.md').read_text()
        block=text[text.index('<!-- BEGIN UPDATE COMMANDS -->'):text.index('<!-- END UPDATE COMMANDS -->')]
        self.assertIn('### Current release commands',block)
        self.assertNotIn('## Updating Domain Monitor',block)
        self.assertNotIn('Manual backup',block)
    def test_required_guidance_survives(self):
        text=(ROOT/'README.md').read_text()
        for value in ('Example for a larger host','Set automatically by the tuner','Summary tiles','side by side','change list'):
            self.assertIn(value,text)
if __name__=='__main__': unittest.main(verbosity=2)
