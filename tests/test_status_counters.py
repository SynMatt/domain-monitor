import json, time, unittest
from test_app import Tests
import app as m

class StatusCounterTests(Tests):
    def add_result(self, domain, spf, dkim, dmarc, age=0):
        data={
            'spf':m.res(spf,'test'),
            'dkim':m.res(dkim,'test'),
            'dmarc':m.res(dmarc,'test'),
            'status':'fail' if 'fail' in (spf,dkim,dmarc) else 'pass'
        }
        now=time.time()-age
        with m.db() as c:
            c.execute('INSERT INTO domains(domain,label,selectors,policy,due,checked,result,manual_pending) VALUES(?,?,?,?,?,?,?,0)',
                      (domain,'','','none',time.time()+3600,now,json.dumps(data)))

    def test_counts_and_stale_becomes_unknown(self):
        self.auth()
        self.add_result('pass.example','pass','warn','fail')
        self.add_result('unknown.example','unknown','pass','warn')
        self.add_result('stale.example','pass','pass','pass',age=27*3600)
        page=self.client.get('/')
        self.assertEqual(page.status_code,200)
        for expected in (b'SPF',b'Pass: 1',b'Warn: 0',b'Fail: 0',b'Unknown: 2',b'DKIM',b'DMARC'):
            self.assertIn(expected,page.data)

    def test_empty_dashboard_zeroes(self):
        self.auth()
        page=self.client.get('/')
        self.assertEqual(page.status_code,200)
        self.assertGreaterEqual(page.data.count(b'Pass: 0'),3)
        self.assertGreaterEqual(page.data.count(b'Unknown: 0'),3)

if __name__=='__main__': unittest.main(verbosity=2)
