import unittest,json,time
from unittest.mock import patch
from types import SimpleNamespace
from test_app import Tests
import app as m
import dns_host as h
class DnsHostTests(Tests):
    def test_matching(self):
        self.assertEqual(h.provider_for(['a.ns.cloudflare.com','b.ns.cloudflare.com']),'Cloudflare')
        self.assertIsNone(h.provider_for(['cloudflare.com.evil.invalid']))
        self.assertIsNone(h.provider_for(['a.ns.cloudflare.com','ns.example.net']))
    def test_lookup(self):
        with patch('dns.resolver.Resolver') as r:
            r.return_value.resolve.return_value=[SimpleNamespace(target='A.NS.CLOUDFLARE.COM.')]
            self.assertEqual(h.lookup('example.com')['provider'],'Cloudflare')
        with patch('dns.resolver.Resolver',side_effect=RuntimeError('fixture')):
            self.assertEqual(h.lookup('example.com')['lookup_status'],'unknown')
    def test_fallback(self):
        self.assertEqual(h.label(None),'Not checked yet')
        self.assertEqual(h.label({'dns_host':{'lookup_status':'unknown'}}),'Unknown')
        self.assertEqual(h.label({'dns_host':{'lookup_status':'ok','nameservers':['ns.example.net']}}),'ns.example.net')
    def test_render_and_legacy(self):
        self.auth(); self.add()
        self.assertIn(b'Not checked yet',self.client.get('/').data)
        data={k:m.res('pass','fixture') for k in ('spf','dkim','dmarc')}; data['status']='pass'
        data['dns_host']={'lookup_status':'ok','provider':'Cloudflare','nameservers':['a.ns.cloudflare.com']}
        with m.db() as c:
            ident=c.execute('SELECT id FROM domains').fetchone()[0]
            c.execute('UPDATE domains SET result=?,checked=? WHERE id=?',(json.dumps(data),time.time(),ident))
            c.execute('INSERT INTO history(domain_id,checked,result) VALUES(?,?,?)',(ident,time.time(),json.dumps(data)))
        with patch('dns.resolver.Resolver',side_effect=AssertionError('No page-load DNS')):
            self.assertIn(b'Cloudflare',self.client.get('/').data)
            self.assertIn(b'a.ns.cloudflare.com',self.client.get(f'/domain/{ident}').data)
        data['dns_host']['provider']='<script>alert(1)</script>'
        with m.db() as c: c.execute('UPDATE domains SET result=? WHERE id=?',(json.dumps(data),ident))
        self.assertNotIn(b'<script>alert(1)</script>',self.client.get('/').data)
if __name__=='__main__': unittest.main(verbosity=2)
