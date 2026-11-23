from datetime import datetime,timezone
import unittest
from unittest.mock import patch
import domain_expiry as expiry

class RegistrableDomainExpiryTests(unittest.TestCase):
    def test_plain_com_subdomain(self): self.assertEqual(expiry.registrable_domain('akl.example.com'),'example.com')
    def test_multilabel_public_suffixes(self):
        self.assertEqual(expiry.registrable_domain('mail.example.co.nz'),'example.co.nz')
        self.assertEqual(expiry.registrable_domain('service.example.com.au'),'example.com.au')
        self.assertEqual(expiry.registrable_domain('host.example.co.uk'),'example.co.uk')
    def test_apex_domain_is_unchanged(self): self.assertEqual(expiry.registrable_domain('example.com'),'example.com')
    def test_public_suffix_only_is_rejected(self):
        with self.assertRaises(ValueError): expiry.registrable_domain('co.nz')
    def test_lookup_queries_registration_domain_and_records_mapping(self):
        now=datetime(2026,11,23,tzinfo=timezone.utc)
        result=expiry._result('ok',now,datetime(2027,3,8,tzinfo=timezone.utc),source='Authoritative RDAP')
        with patch('domain_expiry._rdap',return_value=result) as rdap: item=expiry.lookup('akl.example.com')
        self.assertEqual(rdap.call_args.args[0],'example.com')
        self.assertEqual(item['requested_domain'],'akl.example.com')
        self.assertEqual(item['registration_domain'],'example.com')
        self.assertTrue(item['subdomain_lookup'])
        self.assertIn('Registration domain: example.com',expiry.source_label({'domain_expiry':item}))
if __name__=='__main__': unittest.main(verbosity=2)
