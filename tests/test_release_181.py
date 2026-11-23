import json,time,unittest
from unittest.mock import patch
import app as m

class RegistrableExpiryCacheReliabilityTests(unittest.TestCase):
    def row(self,domain,item):
        return {'domain':domain,'result':json.dumps({'domain_expiry':item})}
    def test_legacy_subdomain_not_published_cache_is_rejected(self):
        item={'status':'not_published','checked_at':time.time(),'source':'RDAP'}
        self.assertIsNone(m.cached_expiry(self.row('akl.example.com',item)))
    def test_matching_subdomain_registration_cache_is_reused(self):
        item={'status':'ok','checked_at':time.time(),'source':'Authoritative RDAP','expires_at':time.time()+86400,
              'registration_domain':'example.com','requested_domain':'akl.example.com'}
        cached=m.cached_expiry(self.row('akl.example.com',item))
        self.assertIsNotNone(cached)
        self.assertTrue(cached['cached'])
    def test_apex_legacy_cache_remains_valid(self):
        item={'status':'ok','checked_at':time.time(),'source':'RDAP','expires_at':time.time()+86400}
        self.assertIsNotNone(m.cached_expiry(self.row('example.com',item)))
    def test_wrong_registration_domain_is_rejected(self):
        item={'status':'ok','checked_at':time.time(),'expires_at':time.time()+86400,'registration_domain':'wrong.example'}
        self.assertIsNone(m.cached_expiry(self.row('mail.example.co.nz',item)))
