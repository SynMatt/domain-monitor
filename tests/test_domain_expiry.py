import unittest
from datetime import datetime,timezone
from unittest.mock import patch
from test_app import Tests
import domain_expiry as expiry

class DomainExpiryTests(Tests):
    def test_rdap_expiration_and_thresholds(self):
        now=datetime(2026,11,11,tzinfo=timezone.utc)
        item=expiry.parse({'events':[{'eventAction':'registration','eventDate':'2020-01-01T00:00:00Z'},{'eventAction':'expiration','eventDate':'2027-03-18T00:00:00Z'}]},now)
        data={'domain_expiry':item}
        self.assertEqual(item['status'],'ok')
        self.assertEqual(item['days_remaining'],127)
        self.assertEqual(expiry.label(data),'18 Mar 2027 · 127 days')
        self.assertEqual(expiry.css_class(data),'pass')
        self.assertEqual(expiry.css_class({'domain_expiry':{'status':'ok','days_remaining':90}}),'warn')
        self.assertEqual(expiry.css_class({'domain_expiry':{'status':'ok','days_remaining':30}}),'fail')

    def test_missing_and_failed_expiry_are_neutral(self):
        self.assertEqual(expiry.label({}),'Not checked yet')
        self.assertEqual(expiry.label({'domain_expiry':{'status':'unavailable'}}),'Unavailable')
        self.assertEqual(expiry.css_class({'domain_expiry':{'status':'unavailable'}}),'muted')

    def test_network_failure_is_isolated(self):
        with patch('domain_expiry.urlopen',side_effect=TimeoutError()):
            self.assertEqual(expiry.lookup('example.com')['status'],'temporary_error')

    def test_dashboard_load_does_not_query_rdap(self):
        self.auth(); self.add()
        with patch('domain_expiry.urlopen',side_effect=AssertionError('No page-load RDAP')):
            page=self.client.get('/')
        self.assertEqual(page.status_code,200)
        self.assertIn(b'Domain expiry:',page.data)
        self.assertIn(b'Not checked yet',page.data)

if __name__=='__main__': unittest.main(verbosity=2)
