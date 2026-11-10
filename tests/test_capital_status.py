import json,time,unittest
from pathlib import Path
from test_app import Tests
import app as m

class CapitalStatusTests(Tests):
    def add_result(self,domain,spf,dkim,dmarc):
        data={k:m.res(v,'test') for k,v in {'spf':spf,'dkim':dkim,'dmarc':dmarc}.items()}
        data['status']='fail'
        with m.db() as c:
            c.execute('INSERT INTO domains(domain,label,selectors,policy,due,checked,result,manual_pending) VALUES(?,?,?,?,?,?,?,0)',
                      (domain,'','','none',time.time()+3600,time.time(),json.dumps(data)))
    def test_card_statuses_are_capitalised(self):
        self.auth(); self.add_result('capital.example','fail','warn','pass')
        page=self.client.get('/')
        self.assertEqual(page.status_code,200)
        self.assertIn(b'SPF: Fail',page.data)
        self.assertIn(b'DKIM: Warn',page.data)
        self.assertIn(b'DMARC: Pass',page.data)
        self.assertNotIn(b'SPF: fail',page.data)
    def test_version_and_changelog(self):
        self.assertEqual(self.client.get('/health').json['version'],'0.11.4')
        self.assertIn('## 0.11.4 - 2026-11-11',Path('/app/CHANGELOG.md').read_text())
if __name__=='__main__': unittest.main(verbosity=2)
