import unittest
from pathlib import Path
from test_app import Tests
class UpdateScriptTests(Tests):
    def test_version(self): self.assertEqual(self.client.get('/health').json['version'],'0.13.0')
    def test_backup_uses_host_database(self):
        s=Path('/app/scripts/backup.sh').read_text(); self.assertIn('source.backup(target)',s); self.assertIn('mode=ro',s)
    def test_restore_numeric_ownership(self):
        s=Path('/app/scripts/restore.sh').read_text(); self.assertIn('chown +10001:+10001',s); self.assertNotIn('install -m 0600 -o 10001',s)
    def test_rollback_stops_services_first(self):
        s=Path('/app/scripts/update.sh').read_text(); block=s[s.index('rollback(){'):s.index('trap rollback ERR')]
        self.assertLess(block.index('compose stop web worker'),block.index('mv -f'))
if __name__=='__main__': unittest.main(verbosity=2)
