import unittest
from pathlib import Path
from test_app import Tests
import app as m

class SchedulerVisibilityTests(Tests):
    def test_healthy_scheduler_is_hidden(self):
        self.auth()
        with m.db() as c:
            c.execute("INSERT OR REPLACE INTO state VALUES('heartbeat',?)",(str(m.time.time()),))
        page=self.client.get('/')
        self.assertEqual(page.status_code,200)
        self.assertNotIn(b'Scheduler: running',page.data)
        self.assertNotIn(b'Scheduler not reporting',page.data)
    def test_unhealthy_scheduler_warning_is_visible(self):
        self.auth()
        with m.db() as c:
            c.execute("DELETE FROM state WHERE key='heartbeat'")
        page=self.client.get('/')
        self.assertIn(b'Scheduler not reporting',page.data)
        self.assertIn(b'worker heartbeat',page.data)
    def test_version_and_changelog(self):
        self.assertEqual(self.client.get('/health').json['version'],'0.13.1')
        self.assertIn('## 0.13.1 - 2026-11-11',Path('/app/CHANGELOG.md').read_text())
if __name__=='__main__': unittest.main(verbosity=2)
