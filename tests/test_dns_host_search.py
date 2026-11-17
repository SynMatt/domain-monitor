import json,time,unittest
from test_app import Base as Tests
import app as m

class DnsHostSearchTests(Tests):
 def add_result(self,domain,label,nameservers):
  data={k:m.res('pass','test') for k in ('spf','dkim','dmarc')}
  data['status']='pass'; data['dns_host']={'lookup_status':'ok','nameservers':nameservers,'provider':None}
  with m.db() as c:
   c.execute('INSERT INTO domains(domain,label,selectors,policy,due,checked,result,manual_pending) VALUES(?,?,?,?,?,?,?,0)',(domain,label,'','none',time.time()+3600,time.time(),json.dumps(data)))
 def test_search_by_builtin_provider_and_raw_nameserver(self):
  self.auth(); self.add_result('cloud.example','Client A',['melissa.ns.cloudflare.com','newt.ns.cloudflare.com']); self.add_result('other.example','Client B',['ns1.example.net'])
  page=self.client.get('/?q=cloudflare&sort=domain')
  self.assertIn(b'cloud.example',page.data); self.assertNotIn(b'other.example',page.data)
  page=self.client.get('/?q=melissa.ns.cloudflare.com&sort=domain')
  self.assertIn(b'cloud.example',page.data); self.assertNotIn(b'other.example',page.data)
 def test_search_by_custom_provider_mapping(self):
  self.auth(); self.add_result('impact.example','Client C',['ns1.dns.example.net','ns2.dns.example.net'])
  with m.db() as c:
   c.execute('INSERT OR REPLACE INTO state(key,value) VALUES(?,?)',('dns_provider_mappings_v1',json.dumps({'dns.example.net':'Example DNS'})))
  page=self.client.get('/?q=Example DNS&sort=domain')
  self.assertIn(b'impact.example',page.data)
 def test_search_wording_and_no_live_dns(self):
  self.auth(); self.add_result('cached.example','Client D',['ns1.dnspackage.com'])
  page=self.client.get('/')
  self.assertIn(b'Search domain, client label or DNS host',page.data)
  self.assertIn(b'client name or Cloudflare',page.data)

if __name__=='__main__': unittest.main(verbosity=2)
