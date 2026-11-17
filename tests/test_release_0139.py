import json,time,unittest
from pathlib import Path
from unittest.mock import patch
from test_app import Base as Tests
from app import APP_VERSION
import app as m
import dns_evidence as ev

class Release0139Tests(Tests):
    def ident(self):
        self.add()
        with m.db() as c:
            return c.execute("SELECT id FROM domains WHERE domain='example.com'").fetchone()['id']

    def result_with_expiry(self,checked_at,status='ok'):
        data={k:m.res('pass','fixture') for k in ('spf','dkim','dmarc')}; data['status']='pass'
        data['domain_expiry']={'status':status,'checked_at':checked_at,
            'expires_at':checked_at+200*86400 if status=='ok' else None,
            'days_remaining':200 if status=='ok' else None,'source':'RDAP','error':None}
        return json.dumps(data)

    def test_cached_expiry_rules(self):
        now=time.time()
        fresh=m.cached_expiry({'result':self.result_with_expiry(now-3600)},now)
        self.assertTrue(fresh['cached']); self.assertEqual(fresh['status'],'ok')
        self.assertIsNone(m.cached_expiry({'result':self.result_with_expiry(now-25*3600)},now))
        self.assertIsNone(m.cached_expiry({'result':self.result_with_expiry(now-60,'temporary_error')},now))
        self.assertEqual(m.cached_expiry({'result':self.result_with_expiry(now-60,'not_published')},now)['status'],'not_published')
        self.assertIsNone(m.cached_expiry({'result':None},now))
        self.assertIsNone(m.cached_expiry({'result':'not json'},now))

    def run_check(self,age):
        self.auth(); ident=self.ident()
        with m.db() as c:
            c.execute('UPDATE domains SET result=?,manual_pending=1 WHERE id=?',(self.result_with_expiry(time.time()-age),ident))
            row=dict(c.execute('SELECT * FROM domains WHERE id=?',(ident,)).fetchone())
        called=[]
        def fake(row,include_expiry=True):
            kinds=['spf','dkim','dmarc','dns_evidence','dns_host']+(['domain_expiry'] if include_expiry else [])
            called.extend(kinds); return {k:m.res('pass','fixture') for k in kinds}
        with patch.object(m,'isolated_domain',side_effect=fake):
            m.run_domain_check(row,None,False)
        with m.db() as c:
            saved=json.loads(c.execute('SELECT result FROM domains WHERE id=?',(ident,)).fetchone()['result'])
        return called,saved

    def test_worker_reuses_recent_expiry(self):
        called,saved=self.run_check(60)
        self.assertNotIn('domain_expiry',called)
        self.assertTrue(saved['domain_expiry']['cached'])
        for kind in ('spf','dkim','dmarc','dns_evidence','dns_host'):
            self.assertIn(kind,called)

    def test_worker_refreshes_old_expiry(self):
        called,saved=self.run_check(25*3600)
        self.assertIn('domain_expiry',called)

    def collect(self,recursive,direct):
        with patch.object(ev,'_recursive',return_value=recursive), \
             patch.object(ev,'_authoritative_servers',return_value=['ns1.example.net','ns2.example.net']), \
             patch.object(ev,'_addresses',return_value=['192.0.2.53']), \
             patch.object(ev,'_direct',return_value=direct):
            return ev.query_evidence('example.com','selector2._domainkey.example.com','TXT')

    def test_matching_nxdomain_is_not_a_difference(self):
        r=self.collect({'status':'nxdomain','records':[]},{'rcode':'NXDOMAIN','records':[],'ttl':None})
        self.assertTrue(r['recursive_matches_authoritative'])

    def test_nxdomain_versus_record_is_a_difference(self):
        r=self.collect({'status':'nxdomain','records':[]},{'rcode':'NOERROR','records':['v=DKIM1; p=abc'],'ttl':60})
        self.assertFalse(r['recursive_matches_authoritative'])

    def test_resolver_error_is_unavailable_not_mismatch(self):
        r=self.collect({'status':'timeout','records':[]},{'rcode':'NOERROR','records':['x'],'ttl':60})
        self.assertIsNone(r['recursive_matches_authoritative'])

    def test_status_endpoint(self):
        self.assertEqual(self.client.get('/domains/status?ids=1').status_code,302)
        self.auth(); ident=self.ident()
        data=self.client.get(f'/domains/status?ids={ident},abc').get_json()
        self.assertTrue(data['domains'][str(ident)]['pending'])
        self.assertEqual(self.client.get('/domains/status?ids=').get_json(),{'domains':{}})

    def test_dashboard_card_status(self):
        self.auth(); ident=self.ident()
        page=self.client.get('/')
        self.assertIn(b'/static/card-status.js',page.data)
        self.assertIn(b'data-pending="1"',page.data)
        with m.db() as c:
            c.execute('UPDATE domains SET manual_pending=0,checked=?,result=? WHERE id=?',(time.time(),self.result_with_expiry(time.time()),ident))
        page=self.client.get('/')
        self.assertIn(b'Updated just now',page.data)
        self.assertIn(b'data-pending="0"',page.data)
        script=Path('/app/static/card-status.js').read_text()
        self.assertIn('/domains/status',script)
        self.assertNotIn('innerHTML',script)

    def test_version(self):
        self.assertEqual(self.client.get('/health').json['version'],APP_VERSION)

if __name__=='__main__': unittest.main(verbosity=2)
