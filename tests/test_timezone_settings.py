import json,time,unittest
from pathlib import Path
from zoneinfo import ZoneInfo
from test_app import Tests
import app as m

class TimezoneSettingsTests(Tests):
    def test_default_timezone(self):
        with m.db() as c: self.assertEqual(m.get_timezone(c),'Pacific/Auckland')
    def test_settings_dropdown_and_save(self):
        self.auth()
        page=self.client.get('/settings')
        self.assertIn(b'Pacific/Auckland',page.data)
        self.assertIn(b'Australia/Sydney',page.data)
        response=self.post('/settings',daily_time='07:15',timezone='Australia/Sydney')
        self.assertEqual(response.status_code,302)
        with m.db() as c:
            self.assertEqual(m.get_timezone(c),'Australia/Sydney')
            self.assertEqual(m.get_clock(c),'07:15')
    def test_invalid_timezone_rejected(self):
        self.auth()
        response=self.post('/settings',daily_time='07:15',timezone='../../etc/passwd')
        self.assertIn(b'Select a supported timezone',response.data)
        with m.db() as c: self.assertEqual(m.get_timezone(c),'Pacific/Auckland')
    def test_next_run_uses_selected_zone(self):
        now=m.datetime(2026,11,10,6,0,tzinfo=ZoneInfo('Australia/Sydney')).timestamp()
        due=m.next_run(now,'07:15',ZoneInfo('Australia/Sydney'))
        local=m.datetime.fromtimestamp(due,ZoneInfo('Australia/Sydney'))
        self.assertEqual((local.hour,local.minute),(7,15))
    def test_version_and_changelog(self):
        self.assertEqual(self.client.get('/health').json['version'],'0.9.3')
        self.assertIn('## 0.9.3 - 2026-11-10',Path('/app/CHANGELOG.md').read_text())
if __name__=='__main__': unittest.main(verbosity=2)
