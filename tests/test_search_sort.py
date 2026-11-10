import json,time,unittest
from pathlib import Path
from test_app import Tests
import app as m

class SearchSortTests(Tests):
    def add_result(self,domain,label,spf='pass',dkim='pass',dmarc='pass',checked=None,due=None):
        data={k:m.res(v,'test') for k,v in {'spf':spf,'dkim':dkim,'dmarc':dmarc}.items()}; data['status']='pass'
        with m.db() as c:
            c.execute('INSERT INTO domains(domain,label,selectors,policy,due,checked,result,manual_pending) VALUES(?,?,?,?,?,?,?,0)',(domain,label,'','none',due or time.time()+3600,checked or time.time(),json.dumps(data)))
    def test_search_domain_and_label(self):
        self.auth(); self.add_result('example-company.co.nz','example-company IT'); self.add_result('example.net','Other Client')
        page=self.client.get('/?q=example-company&sort=domain')
        self.assertIn(b'example-company.co.nz',page.data); self.assertNotIn(b'example.net',page.data); self.assertIn(b'Showing 1 of 2 domains',page.data)
        page=self.client.get('/?q=other')
        self.assertIn(b'example.net',page.data); self.assertNotIn(b'example-company.co.nz',page.data)
    def test_severity_sort(self):
        self.auth(); self.add_result('pass.example','',spf='pass'); self.add_result('fail.example','',spf='fail'); self.add_result('warn.example','',spf='warn')
        data=self.client.get('/?sort=severity').data
        self.assertLess(data.index(b'fail.example'),data.index(b'warn.example')); self.assertLess(data.index(b'warn.example'),data.index(b'pass.example'))
    def test_search_combines_with_filter(self):
        self.auth(); self.add_result('one.example','Target',dkim='warn'); self.add_result('two.example','Target',dkim='pass'); self.add_result('three.example','Other',dkim='warn')
        data=self.client.get('/?kind=dkim&status=warn&q=target&sort=domain').data
        self.assertIn(b'one.example',data); self.assertNotIn(b'two.example',data); self.assertNotIn(b'three.example',data)
    def test_invalid_sort_defaults_safely(self):
        self.auth(); self.add_result('one.example','')
        page=self.client.get('/?sort=bad')
        self.assertEqual(page.status_code,200); self.assertIn(b'one.example',page.data)
    def test_version_and_changelog(self):
        self.assertEqual(self.client.get('/health').json['version'],'0.11.4')
        self.assertIn('## 0.11.4 - 2026-11-11',Path('/app/CHANGELOG.md').read_text())
if __name__=='__main__': unittest.main(verbosity=2)
