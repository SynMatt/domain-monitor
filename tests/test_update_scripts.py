import unittest
from pathlib import Path
from test_app import Tests
import app as m
class UpdateScriptTests(Tests):
    def test_version(self): self.assertEqual(self.client.get('/health').json['version'],'0.10.0')
    def test_scripts_present(self):
        for name in ('common.sh','backup.sh','restore.sh','update.sh'):
            self.assertTrue((Path('/app/scripts')/name).exists(),name)
    def test_update_safety_controls(self):
        text=Path('/app/scripts/update.sh').read_text()
        for expected in ('git status --porcelain','PRAGMA integrity_check','rollback','SELECT COUNT(*) FROM domains'):
            self.assertIn(expected,text)
if __name__=='__main__': unittest.main(verbosity=2)
