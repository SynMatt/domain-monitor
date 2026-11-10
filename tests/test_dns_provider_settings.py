import json,time,unittest
from unittest.mock import patch
from test_app import Tests
import app as m
from dns_providers import KEY,provider,display,BUILTINS
class ProviderSettingsTests(Tests):
    def setUp(self):
        super().setUp()
        with m.db() as c: c.execute('DELETE FROM state WHERE key=?',(KEY,))
    def tearDown(self):
        with m.db() as c: c.execute('DELETE FROM state WHERE key=?',(KEY,))
    def test_auth_and_csrf(self):
        self.assertEqual(self.client.get('/settings/dns-providers').status_code,302)
        self.auth()
        self.assertEqual(self.client.post('/settings/dns-providers',data={}).status_code,400)
    def test_crud(self):
        self.auth()
        path='/settings/dns-providers'
        self.assertEqual(self.post(path,action='add',suffix='DNS.EXAMPLE.NET.',name='Example DNS').status_code,302)
        self.assertIn(b'Example DNS',self.client.get(path).data)
        self.assertEqual(self.post(path,action='edit',suffix='dns.example.net',name='Renamed DNS').status_code,302)
        self.assertIn(b'Renamed DNS',self.client.get(path).data)
        self.assertEqual(self.post(path,action='delete',suffix='dns.example.net',confirm='DELETE').status_code,302)
        with m.db() as c: self.assertEqual(json.loads(c.execute('SELECT value FROM state WHERE key=?',(KEY,)).fetchone()[0]),{})
    def test_validation(self):
        self.auth()
        for suffix,name in [('com','Bad'),('https://example.net','Bad'),('example.net','<script>'),('example.net','')]:
            self.post('/settings/dns-providers',action='add',suffix=suffix,name=name)
        with m.db() as c: self.assertIsNone(c.execute('SELECT value FROM state WHERE key=?',(KEY,)).fetchone())
    def test_matching(self):
        self.assertEqual(provider('NS1.DNS.EXAMPLE.NET.',{'dns.example.net':'Custom'},{'example.net':'Built-in'}),'Custom')
        self.assertIsNone(provider('notdns.example.net',{'dns.example.net':'Custom'},{}))
        self.assertIsNone(provider('ns.dns.example.net.evil.invalid',{'dns.example.net':'Custom'},{}))
        self.assertEqual(provider('ns1.hosting-cloud.net',{},BUILTINS),'DreamIT Host')
        self.assertEqual(provider('ns1.dnspackage.com',{},BUILTINS),'Crazy Domains')
    def test_multiple_and_fallback(self):
        data={'dns_host':{'lookup_status':'ok','nameservers':['ns1.dns.example.net','ns2.dns.example.net']}}
        self.assertEqual(display(data,{}, {},lambda d:'Unknown'),'dns.example.net')
        self.assertEqual(display(data,{'ns1.dns.example.net':'One','ns2.dns.example.net':'Two'}, {},lambda d:'Unknown'),'Multiple providers')
    def test_cached_cards_and_schedule(self):
        self.auth(); self.add()
        data={k:m.res('pass','fixture') for k in ('spf','dkim','dmarc')}; data['status']='pass'
        data['dns_host']={'lookup_status':'ok','nameservers':['ns1.dns.example.net']}
        with m.db() as c:
            c.execute('UPDATE domains SET result=?,checked=?',(json.dumps(data),time.time()))
            before=tuple(c.execute('SELECT due,revision,result FROM domains').fetchone())
        with patch('dns.resolver.Resolver',side_effect=AssertionError('No page-load DNS')):
            self.assertIn(b'dns.example.net',self.client.get('/').data)
            self.post('/settings/dns-providers',action='add',suffix='dns.example.net',name='Example DNS')
            self.assertIn(b'Example DNS',self.client.get('/').data)
            self.assertNotIn(b'ns1.dns.example.net</strong>',self.client.get('/settings/dns-providers').data)
        with m.db() as c: self.assertEqual(tuple(c.execute('SELECT due,revision,result FROM domains').fetchone()),before)
    def test_settings_link(self):
        self.auth(); self.assertIn(b'/settings/dns-providers',self.client.get('/settings').data)
if __name__=='__main__': unittest.main(verbosity=2)
