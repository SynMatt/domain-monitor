import unittest
from pathlib import Path
from test_app import Tests

class UpdaterRollbackTests(Tests):
    def test_version(self):
        self.assertEqual(self.client.get('/health').json['version'],'0.12.1')

    def test_rollback_clears_temporary_environment(self):
        text=Path('/app/scripts/update.sh').read_text()
        block=text[text.index('rollback(){'):text.index('trap rollback ERR')]
        self.assertIn('cp -a "$BACKUP/environment.env" .env',block)
        self.assertIn('unset DOMAIN_MONITOR_VERSION HOST_BIND_IP HOST_PORT',block)
        self.assertLess(block.index('cp -a "$BACKUP/environment.env" .env'),block.index('compose build'))

    def test_named_verification_steps(self):
        text=Path('/app/scripts/update.sh').read_text()
        for step in (
            'verify running application version',
            'verify configured image tag',
            'verify published binding',
            'verify database integrity',
            'verify domain count',
            'verify history count',
        ):
            self.assertIn(step,text)

    def test_rollback_reports_restored_state(self):
        text=Path('/app/scripts/update.sh').read_text()
        for label in ('Rollback source version','Rollback running version','Rollback image','Rollback binding'):
            self.assertIn(label,text)

if __name__=='__main__': unittest.main(verbosity=2)
