import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import domain_expiry
import metaname_expiry


class Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, size=-1): return self.payload


class MetanameExpiryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_cache = metaname_expiry.CACHE_FILE
        self.old_lock = metaname_expiry.LOCK_FILE
        metaname_expiry.CACHE_FILE = Path(self.temp.name) / 'cache.json'
        metaname_expiry.LOCK_FILE = Path(self.temp.name) / 'cache.lock'
        self.env = patch.dict(os.environ, {
            'METANAME_REFERENCE': 'a1b2',
            'METANAME_API_KEY': 'secret-test-key',
        }, clear=False)
        self.env.start()
    def tearDown(self):
        self.env.stop()
        metaname_expiry.CACHE_FILE = self.old_cache
        metaname_expiry.LOCK_FILE = self.old_lock
        self.temp.cleanup()

    @patch('metaname_expiry.urlopen')
    def test_matching_domain_uses_paid_up_date(self, opened):
        opened.return_value = Response({'jsonrpc':'2.0','id':'domain-monitor','result':[
            {'name':'example.com','when_paid_up_to':'2027-03-08T11:49:46+13:00'},
            {'name':'example.net','when_paid_up_to':'2028-04-01T00:00:00+13:00'},
        ]})
        item = metaname_expiry.lookup('example.com', now=1700000000)
        self.assertEqual(item['source'], 'Metaname')
        self.assertEqual(item['expires_at'], 1804464000.0)
        request = opened.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(body['method'], 'domain_names')
        self.assertEqual(body['params'], ['a1b2', 'secret-test-key'])

    @patch('metaname_expiry.urlopen')
    def test_account_response_is_cached_once(self, opened):
        opened.return_value = Response({'result':[{'name':'example.com','when_paid_up_to':'2027-03-08T00:00:00'}]})
        self.assertIsNotNone(metaname_expiry.lookup('example.com', now=1700000000))
        self.assertIsNotNone(metaname_expiry.lookup('example.com', now=1700000100))
        self.assertEqual(opened.call_count, 1)

    @patch('metaname_expiry.urlopen')
    def test_non_matching_domain_falls_back(self, opened):
        opened.return_value = Response({'result':[{'name':'example.net','when_paid_up_to':'2027-03-08T00:00:00'}]})
        self.assertIsNone(metaname_expiry.lookup('example.com', now=1700000000))

    def test_missing_credentials_disables_integration(self):
        with patch.dict(os.environ, {'METANAME_REFERENCE':'', 'METANAME_API_KEY':''}):
            self.assertIsNone(metaname_expiry.lookup('example.com'))

    @patch('domain_expiry._rdap')
    @patch('domain_expiry.metaname_expiry.lookup')
    def test_domain_lookup_prefers_metaname(self, meta, rdap):
        meta.return_value = {'status':'ok','checked_at':1700000000,'expires_at':1804464000,
                             'source':'Metaname','registration_domain':'example.com'}
        item = domain_expiry.lookup('mail.example.com')
        self.assertEqual(item['source'], 'Metaname')
        rdap.assert_not_called()


if __name__ == '__main__': unittest.main()
