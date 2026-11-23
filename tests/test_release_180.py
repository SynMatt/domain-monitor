import time, unittest
from datetime import datetime, timezone
from unittest.mock import patch
import domain_expiry as de

class ExpiryFallback180Tests(unittest.TestCase):
    def test_whois_expiry_fields(self):
        now=datetime(2026,11,23,tzinfo=timezone.utc)
        for line in (
            'Registry Expiry Date: 2028-12-17T09:52:43Z',
            'Registrar Registration Expiration Date: 2028-12-17T09:52:43Z',
            'Expiry Date: 2028-12-17T09:52:43Z',
            'paid-till: 2028-12-17T09:52:43Z',
        ):
            item=de.parse_whois(line,now)
            self.assertEqual(item['status'],'ok')
            self.assertEqual(datetime.fromtimestamp(item['expires_at'],timezone.utc).date().isoformat(),'2028-12-17')

    def test_temporary_failure_keeps_last_confirmed_date(self):
        now=1795386000
        previous={'status':'ok','checked_at':now-3600,'expires_at':1860630763.0,'days_remaining':755,'source':'Authoritative RDAP','error':None}
        current={'status':'temporary_error','checked_at':now,'expires_at':None,'days_remaining':None,'source':'Authoritative RDAP','error':'HTTP 429','retry_after':900}
        merged=de.merge_with_previous(current,previous,now)
        self.assertTrue(merged['last_known'])
        self.assertEqual(merged['expires_at'],previous['expires_at'])
        self.assertEqual(merged['latest_error'],'HTTP 429')
        self.assertEqual(merged['retry_at'],now+900)
        data={'domain_expiry':merged}
        self.assertIn('Last known',de.label(data))
        self.assertIn('HTTP 429',de.source_label(data))

    def test_success_replaces_last_known_state(self):
        previous={'status':'ok','expires_at':1000,'source':'WHOIS fallback','last_known':True,'latest_error':'HTTP 429'}
        current={'status':'ok','expires_at':2000,'source':'Authoritative RDAP'}
        self.assertIs(de.merge_with_previous(current,previous),current)

    def test_rdap_429_uses_whois_fallback(self):
        from urllib.error import HTTPError
        error=HTTPError('https://registry.example/domain/example.com',429,'rate',{'Retry-After':'600'},None)
        fallback={'status':'ok','expires_at':1860630763.0,'source':'WHOIS fallback (whois.example)'}
        with patch.object(de,'_rdap',side_effect=error), patch.object(de,'_whois',return_value=fallback):
            item=de.lookup('example.com')
        self.assertEqual(item['status'],'ok')
        self.assertEqual(item['rdap_error'],'HTTP 429')

    def test_bootstrap_selects_registry(self):
        payload={'services':[[['com'],['https://rdap.registry.example/']]]}
        with patch.object(de,'_load_bootstrap',return_value=payload):
            self.assertEqual(de._rdap_base('example.com'),'https://rdap.registry.example/')

if __name__=='__main__': unittest.main(verbosity=2)
