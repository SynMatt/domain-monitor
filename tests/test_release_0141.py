import os,stat,unittest
from pathlib import Path
from test_app import Tests

class Release0141Tests(Tests):
    def test_maintenance_scripts_present_and_executable(self):
        for name in ('monitor-check-all.sh','cleanup-images.sh'):
            p=Path('/app/scripts')/name
            self.assertTrue(p.is_file(),name)
            self.assertTrue(p.stat().st_mode & stat.S_IXOTH,f'{name} not executable')
            self.assertTrue(p.read_text().startswith('#!/usr/bin/env bash'))

    def test_monitor_is_read_only_and_uses_real_check_path(self):
        text=Path('/app/scripts/monitor-check-all.sh').read_text()
        self.assertIn('check-domain',text)
        self.assertIn('mode=ro',text)
        self.assertNotIn('\\"complete\\"',text)
        for word in ('UPDATE ','DELETE ','INSERT '):
            self.assertNotIn(word,text)

    def test_cleanup_is_guarded(self):
        text=Path('/app/scripts/cleanup-images.sh').read_text()
        self.assertIn('CLEANUP',text)
        self.assertIn('KEEP_OLDER=2',text)
        self.assertIn('used by a container',text)
        self.assertNotIn('--force',text)
        self.assertNotIn('volume rm',text)

    def test_docs_and_version(self):
        self.assertIn('cleanup-images.sh',Path('/app/docs/maintenance.md').read_text())
        self.assertEqual(self.client.get('/health').json['version'],'0.14.1')

if __name__=='__main__': unittest.main(verbosity=2)
