import unittest
from unittest.mock import patch
import dns_host as h
class DnsProviderLabelTests(unittest.TestCase):
 def test_microsoft(self):
  self.assertEqual(h.provider_for([f'ns{i}.bdm.microsoftonline.com' for i in range(1,5)]),'Microsoft')
  self.assertEqual(h.provider_for(['NS1.BDM.MICROSOFTONLINE.COM.']),'Microsoft')
 def test_boundary_and_mixed(self):
  self.assertIsNone(h.provider_for(['ns1.bdm.microsoftonline.com.evil.invalid']))
  self.assertIsNone(h.provider_for(['notbdm.microsoftonline.com']))
  self.assertIsNone(h.provider_for(['ns1.bdm.microsoftonline.com','a.ns.cloudflare.com']))
 def test_cached_without_network(self):
  data={'dns_host':{'lookup_status':'ok','provider':None,'nameservers':['ns1.bdm.microsoftonline.com','ns2.bdm.microsoftonline.com']}}
  with patch('dns.resolver.Resolver',side_effect=AssertionError('No page-load DNS')):
   self.assertEqual(h.label(data),'Microsoft')
  self.assertIsNone(data['dns_host']['provider'])
 def test_fallback(self):
  self.assertEqual(h.label({'dns_host':{'lookup_status':'unknown'}}),'Unknown')
  self.assertEqual(h.label({'dns_host':{'lookup_status':'ok','provider':None,'nameservers':['ns.example.net']}}),'ns.example.net')
if __name__=='__main__': unittest.main()
