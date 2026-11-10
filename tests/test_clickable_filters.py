import json, time, unittest
from test_app import Tests
import app as m

class ClickableFilterTests(Tests):
    def add_result(self, domain, spf, dkim, dmarc, age=0):
        data={k:m.res(v,'test') for k,v in {'spf':spf,'dkim':dkim,'dmarc':dmarc}.items()}
        data['status']='fail' if 'fail' in (spf,dkim,dmarc) else 'pass'
        checked=time.time()-age
        with m.db() as c:
            c.execute('INSERT INTO domains(domain,label,selectors,policy,due,checked,result,manual_pending) VALUES(?,?,?,?,?,?,?,0)',
                      (domain,'','','none',time.time()+3600,checked,json.dumps(data)))

    def test_dkim_warn_filter(self):
        self.auth()
        self.add_result('warn.example','pass','warn','pass')
        self.add_result('pass.example','pass','pass','pass')
        page=self.client.get('/?kind=dkim&status=warn')
        self.assertEqual(page.status_code,200)
        self.assertIn(b'warn.example',page.data)
        self.assertNotIn(b'pass.example',page.data)
        self.assertIn(b'Showing 1 of 2 domains',page.data)
        self.assertIn(b'Clear filter',page.data)

    def test_stale_matches_unknown(self):
        self.auth()
        self.add_result('stale.example','pass','pass','pass',age=27*3600)
        page=self.client.get('/?kind=spf&status=unknown')
        self.assertIn(b'stale.example',page.data)

    def test_invalid_filter_shows_all(self):
        self.auth()
        self.add_result('one.example','pass','pass','pass')
        page=self.client.get('/?kind=bad&status=warn')
        self.assertIn(b'one.example',page.data)
        self.assertNotIn(b'<div class="active-filter-banner">',page.data)

    def test_zero_result(self):
        self.auth()
        self.add_result('one.example','pass','pass','pass')
        page=self.client.get('/?kind=dkim&status=fail')
        self.assertIn(b'No matching domains',page.data)

if __name__=='__main__': unittest.main(verbosity=2)
